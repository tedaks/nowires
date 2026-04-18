"""
Per-pixel ITM coverage with link-budget (dBm) output.

For each output pixel we extract a real terrain profile from TX to that pixel
(bilinear-sampled from a pre-fetched elevation grid) and call ITM. Path loss
is combined with TX power, antenna gains, cable loss, and optional antenna
pattern to produce received power in dBm, which is then colored by signal
level the way commercial radio planning tools do.
"""

import math
import os
import io
import base64
import hashlib
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
from PIL import Image

from .elevation_grid import ElevationGrid
from .itm_bridge import itm_p2p_loss
from .math_kernels import apply_coverage_colors


_png_cache: Dict[str, Dict[str, Any]] = {}

# Shared elevation grid for coverage worker pool
_cov_grid_data: Optional[np.ndarray] = None
_cov_grid_meta: dict = {}

# Shared elevation grid for radius worker pool
_radius_grid_data: Optional[np.ndarray] = None
_radius_grid_meta: dict = {}


SIGNAL_LEVELS = [
    (-60.0, (0, 110, 40, 210), "Excellent"),
    (-75.0, (0, 180, 80, 200), "Good"),
    (-85.0, (180, 220, 40, 195), "Fair"),
    (-95.0, (240, 180, 40, 190), "Marginal"),
    (-105.0, (230, 110, 40, 185), "Weak"),
    (-120.0, (200, 40, 40, 0), "No service"),
]

_THRESHOLDS = np.array([t for t, _, _ in SIGNAL_LEVELS], dtype=np.float64)
_COLORS = np.array(
    [list(c) for _, c, _ in SIGNAL_LEVELS] + [[90, 20, 20, 0]], dtype=np.uint8
)


def _prx_to_color(prx_dbm: float) -> Tuple[int, int, int, int]:
    if not math.isfinite(prx_dbm):
        return (0, 0, 0, 0)
    for thresh, rgba, _ in SIGNAL_LEVELS:
        if prx_dbm >= thresh:
            return rgba
    return (90, 20, 20, 0)


def _build_pfl(elevations: np.ndarray, step_m: float) -> List[float]:
    n = len(elevations) - 1
    return [float(n), float(step_m)] + [float(x) for x in elevations]


def _bearing_destination(
    lat: float, lon: float, bearing_deg: float, dist_m: float
) -> Tuple[float, float]:
    R = 6371000.0
    brng = math.radians(bearing_deg)
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    d_r = dist_m / R
    lat2 = math.asin(
        math.sin(lat_r) * math.cos(d_r)
        + math.cos(lat_r) * math.sin(d_r) * math.cos(brng)
    )
    lon2 = lon_r + math.atan2(
        math.sin(brng) * math.sin(d_r) * math.cos(lat_r),
        math.cos(d_r) - math.sin(lat_r) * math.sin(lat2),
    )
    return math.degrees(lat2), math.degrees(lon2)


def _antenna_gain_factor(
    bearing_from_tx_deg: float,
    az_deg: float | None,
    beamwidth_deg: float,
    front_back_db: float = 25.0,
) -> float:
    """Cosine-squared pattern within beamwidth, F/B attenuation outside."""
    if az_deg is None:
        return 0.0
    diff = (bearing_from_tx_deg - az_deg + 540.0) % 360.0 - 180.0
    if abs(diff) <= beamwidth_deg / 2.0:
        x = diff / (beamwidth_deg / 2.0)
        attn = 3.0 * x * x
        return -attn
    return -front_back_db


def _sample_line_from_grid(gd, gm, lat1, lon1, lat2, lon2, n_pts):
    """Bilinear sample from shared grid data (used by workers)."""
    min_lat = gm["min_lat"]
    max_lat = gm["max_lat"]
    min_lon = gm["min_lon"]
    max_lon = gm["max_lon"]
    n_lat = gm["n_lat"]
    n_lon = gm["n_lon"]
    d_lat = (max_lat - min_lat) / (n_lat - 1)
    d_lon = (max_lon - min_lon) / (n_lon - 1)

    ts = np.linspace(0.0, 1.0, n_pts)
    lats = lat1 + ts * (lat2 - lat1)
    lons = lon1 + ts * (lon2 - lon1)

    fy = np.clip((lats - min_lat) / d_lat, 0, n_lat - 1 - 1e-9)
    fx = np.clip((lons - min_lon) / d_lon, 0, n_lon - 1 - 1e-9)

    y0 = np.floor(fy).astype(np.int32)
    x0 = np.floor(fx).astype(np.int32)
    y1 = np.clip(y0 + 1, 0, n_lat - 1)
    x1 = np.clip(x0 + 1, 0, n_lon - 1)
    ty = (fy - y0).astype(np.float32)
    tx_ = (fx - x0).astype(np.float32)

    return (
        gd[y0, x0] * (1 - tx_) * (1 - ty)
        + gd[y0, x1] * tx_ * (1 - ty)
        + gd[y1, x0] * (1 - tx_) * ty
        + gd[y1, x1] * tx_ * ty
    )


def _itm_worker(args):
    """Compute ITM loss + received power for one grid pixel.

    Uses the shared elevation grid (set by _init_cov_pool) to sample
    terrain profiles in-process, avoiding ~1KB PFL serialization per task.

    args: (i, j, target_lat, target_lon, dist_m, bearing_deg,
            step_m, n_pts, tx_h_m, rx_h_m, climate, N0, f_mhz,
            polarization, epsilon, sigma, time_pct, location_pct, situation_pct,
            eirp_dbm, ant_gain_adj, rx_gain_dbi)

    Returns (i, j, loss_db, prx_dbm) or None on failure.
    """
    (
        i,
        j,
        target_lat,
        target_lon,
        dist_m,
        bearing_deg,
        step_m,
        n_pts,
        tx_h_m,
        rx_h_m,
        climate,
        N0,
        f_mhz,
        polarization,
        epsilon,
        sigma,
        time_pct,
        location_pct,
        situation_pct,
        eirp_dbm,
        ant_gain_adj,
        rx_gain_dbi,
    ) = args

    # Sample terrain profile from shared grid
    elevs = _sample_line_from_grid(
        _cov_grid_data,
        _cov_grid_meta,
        _cov_grid_meta["tx_lat"],
        _cov_grid_meta["tx_lon"],
        target_lat,
        target_lon,
        n_pts,
    )

    pfl = _build_pfl(elevs, step_m)

    try:
        res = itm_p2p_loss(
            h_tx__meter=tx_h_m,
            h_rx__meter=rx_h_m,
            profile=pfl,
            climate=climate,
            N0=N0,
            f__mhz=f_mhz,
            polarization=polarization,
            epsilon=epsilon,
            sigma=sigma,
            time_pct=time_pct,
            location_pct=location_pct,
            situation_pct=situation_pct,
        )
    except Exception:
        return None
    if not math.isfinite(res.loss_db) or res.loss_db > 400.0:
        return None
    prx = eirp_dbm + ant_gain_adj + rx_gain_dbi - res.loss_db
    return (i, j, res.loss_db, prx)


def _init_cov_pool(grid_data: np.ndarray, grid_meta: dict) -> None:
    """Pool initializer: share elevation grid with coverage workers."""
    global _cov_grid_data, _cov_grid_meta
    _cov_grid_data = grid_data
    _cov_grid_meta = grid_meta


def _init_radius_pool(grid_data: np.ndarray, grid_meta: dict) -> None:
    """Pool initializer: store the elevation grid in each worker process once."""
    global _radius_grid_data, _radius_grid_meta
    _radius_grid_data = grid_data
    _radius_grid_meta = grid_meta


def _radius_worker(args):
    """Binary-search the coverage radius for one bearing.

    Uses the elevation grid stored by _init_radius_pool.

    args: (bearing_deg, tx_lat, tx_lon, tx_h_m, rx_h_m, f_mhz,
           polarization, climate, N0, epsilon, sigma,
           time_pct, location_pct, situation_pct,
           eirp_dbm, rx_gain_dbi, rx_sensitivity_dbm,
           antenna_az_deg, antenna_beamwidth_deg)

    Returns (bearing_deg, radius_m).
    """
    (
        bearing_deg,
        tx_lat,
        tx_lon,
        tx_h_m,
        rx_h_m,
        f_mhz,
        polarization,
        climate,
        N0,
        epsilon,
        sigma,
        time_pct,
        location_pct,
        situation_pct,
        eirp_dbm,
        rx_gain_dbi,
        rx_sensitivity_dbm,
        antenna_az_deg,
        antenna_beamwidth_deg,
    ) = args

    gd = _radius_grid_data
    gm = _radius_grid_meta
    min_lat = gm["min_lat"]
    max_lat = gm["max_lat"]
    min_lon = gm["min_lon"]
    max_lon = gm["max_lon"]
    n_lat = gm["n_lat"]
    n_lon = gm["n_lon"]
    d_lat = (max_lat - min_lat) / (n_lat - 1)
    d_lon = (max_lon - min_lon) / (n_lon - 1)

    def _sample_line(lat1, lon1, lat2, lon2, n_pts):
        ts = np.linspace(0.0, 1.0, n_pts)
        lats = lat1 + ts * (lat2 - lat1)
        lons = lon1 + ts * (lon2 - lon1)
        fy = np.clip((lats - min_lat) / d_lat, 0, n_lat - 1 - 1e-9)
        fx = np.clip((lons - min_lon) / d_lon, 0, n_lon - 1 - 1e-9)
        y0 = np.floor(fy).astype(np.int32)
        x0 = np.floor(fx).astype(np.int32)
        y1 = np.clip(y0 + 1, 0, n_lat - 1)
        x1 = np.clip(x0 + 1, 0, n_lon - 1)
        ty = (fy - y0).astype(np.float32)
        tx_ = (fx - x0).astype(np.float32)
        return (
            gd[y0, x0] * (1 - tx_) * (1 - ty)
            + gd[y0, x1] * tx_ * (1 - ty)
            + gd[y1, x0] * (1 - tx_) * ty
            + gd[y1, x1] * tx_ * ty
        )

    d_min, d_max = 100.0, 100_000.0
    for _ in range(20):
        d_mid = (d_min + d_max) / 2.0
        lat_end, lon_end = _bearing_destination(tx_lat, tx_lon, bearing_deg, d_mid)
        n_pts = max(3, min(int(round(d_mid / 250.0)) + 1, 75))
        elevs = _sample_line(tx_lat, tx_lon, lat_end, lon_end, n_pts)
        step_m = d_mid / (n_pts - 1)
        pfl = _build_pfl(elevs, step_m)
        try:
            res = itm_p2p_loss(
                h_tx__meter=tx_h_m,
                h_rx__meter=rx_h_m,
                profile=pfl,
                climate=climate,
                N0=N0,
                f__mhz=f_mhz,
                polarization=polarization,
                epsilon=epsilon,
                sigma=sigma,
                time_pct=time_pct,
                location_pct=location_pct,
                situation_pct=situation_pct,
            )
        except Exception:
            d_min = d_mid
            continue
        if not math.isfinite(res.loss_db):
            d_min = d_mid
            continue
        ant_gain_adj = _antenna_gain_factor(
            bearing_deg, antenna_az_deg, antenna_beamwidth_deg
        )
        prx = eirp_dbm + ant_gain_adj + rx_gain_dbi - res.loss_db
        if prx >= rx_sensitivity_dbm:
            d_min = d_mid
        else:
            d_max = d_mid

    return (bearing_deg, (d_min + d_max) / 2.0)


def compute_coverage_radius(
    tx_lat: float,
    tx_lon: float,
    tx_h_m: float,
    rx_h_m: float,
    f_mhz: float,
    tx_power_dbm: float = 43.0,
    tx_gain_dbi: float = 8.0,
    rx_gain_dbi: float = 2.0,
    cable_loss_db: float = 2.0,
    rx_sensitivity_dbm: float = -100.0,
    antenna_az_deg: float | None = None,
    antenna_beamwidth_deg: float = 360.0,
    polarization: int = 0,
    climate: int = 1,
    N0: float = 301.0,
    epsilon: float = 15.0,
    sigma: float = 0.005,
    time_pct: float = 50.0,
    location_pct: float = 50.0,
    situation_pct: float = 50.0,
    terrain_spacing_m: float = 300.0,
    elev_grid_n: int | None = None,
) -> Dict[str, Any]:
    """Compute coverage radius per bearing via link-budget threshold crossing."""
    deg_per_m = 1.0 / 111320.0
    pad_deg = 2.0 * terrain_spacing_m * deg_per_m
    padded_bbox_m = 2.0 * 100.0 * 1000.0 + 4.0 * terrain_spacing_m
    if elev_grid_n is None:
        elev_grid_n = max(64, min(320, int(padded_bbox_m / terrain_spacing_m) + 1))

    lat_per_m = 1.0 / 111320.0
    lon_per_m = 1.0 / (111320.0 * max(math.cos(math.radians(tx_lat)), 0.01))
    half_lat = 100.0 * 1000.0 * lat_per_m
    half_lon = 100.0 * 1000.0 * lon_per_m

    elev = ElevationGrid.fetch(
        min_lat=tx_lat - half_lat - pad_deg,
        min_lon=tx_lon - half_lon - pad_deg,
        max_lat=tx_lat + half_lat + pad_deg,
        max_lon=tx_lon + half_lon + pad_deg,
        n=elev_grid_n,
    )

    eirp_dbm = tx_power_dbm + tx_gain_dbi - cable_loss_db

    grid_meta = {
        "min_lat": elev.min_lat,
        "max_lat": elev.max_lat,
        "min_lon": elev.min_lon,
        "max_lon": elev.max_lon,
        "n_lat": elev.n_lat,
        "n_lon": elev.n_lon,
    }

    worker_args = [
        (
            float(b),
            tx_lat,
            tx_lon,
            tx_h_m,
            rx_h_m,
            f_mhz,
            polarization,
            climate,
            N0,
            epsilon,
            sigma,
            time_pct,
            location_pct,
            situation_pct,
            eirp_dbm,
            rx_gain_dbi,
            rx_sensitivity_dbm,
            antenna_az_deg,
            antenna_beamwidth_deg,
        )
        for b in np.arange(0, 360, 1.0)
    ]

    n_workers = max(1, os.cpu_count() or 1)
    with ProcessPoolExecutor(
        max_workers=n_workers,
        initializer=_init_radius_pool,
        initargs=(elev.data, grid_meta),
    ) as radius_pool:
        radius_per_bearing = list(radius_pool.map(_radius_worker, worker_args))

    radii = [r for _, r in radius_per_bearing]
    max_radius_km = max(radii) / 1000.0 if radii else 0.0
    min_radius_km = min(radii) / 1000.0 if radii else 0.0
    avg_radius_km = float(np.mean(radii)) / 1000.0 if radii else 0.0

    return {
        "max_radius_km": round(max_radius_km, 2),
        "min_radius_km": round(min_radius_km, 2),
        "avg_radius_km": round(avg_radius_km, 2),
        "per_bearing": [
            (float(b), round(r / 1000.0, 2)) for b, r in radius_per_bearing
        ],
    }


def compute_coverage(
    tx_lat: float,
    tx_lon: float,
    tx_h_m: float,
    rx_h_m: float,
    f_mhz: float,
    radius_km: float = 50.0,
    grid_size: int = 192,
    profile_step_m: float = 250.0,
    max_profile_pts: int = 75,
    tx_power_dbm: float = 43.0,
    tx_gain_dbi: float = 8.0,
    rx_gain_dbi: float = 2.0,
    cable_loss_db: float = 2.0,
    rx_sensitivity_dbm: float = -100.0,
    antenna_az_deg: float | None = None,
    antenna_beamwidth_deg: float = 360.0,
    polarization: int = 0,
    climate: int = 1,
    N0: float = 301.0,
    epsilon: float = 15.0,
    sigma: float = 0.005,
    time_pct: float = 50.0,
    location_pct: float = 50.0,
    situation_pct: float = 50.0,
    terrain_spacing_m: float = 300.0,
    elev_grid_n: int | None = None,
    pool: ProcessPoolExecutor | None = None,
) -> Dict[str, Any]:
    deg_per_m = 1.0 / 111320.0
    pad_deg = 2.0 * terrain_spacing_m * deg_per_m
    padded_bbox_m = 2.0 * radius_km * 1000.0 + 4.0 * terrain_spacing_m
    if elev_grid_n is None:
        elev_grid_n = max(64, min(grid_size + 64, int(padded_bbox_m / terrain_spacing_m) + 1))

    cache_key_src = (
        f"{tx_lat:.5f},{tx_lon:.5f},{tx_h_m:.1f},{rx_h_m:.1f},{f_mhz:.1f},"
        f"{radius_km},{grid_size},{profile_step_m},{max_profile_pts},{elev_grid_n},"
        f"{tx_power_dbm},{tx_gain_dbi},"
        f"{rx_gain_dbi},{cable_loss_db},{antenna_az_deg},{antenna_beamwidth_deg},"
        f"{polarization},{climate},{time_pct},{location_pct},{situation_pct}"
    )
    cache_key = hashlib.md5(cache_key_src.encode()).hexdigest()
    if cache_key in _png_cache:
        return {**_png_cache[cache_key], "from_cache": True}

    radius_m = radius_km * 1000.0
    lat_per_m = 1.0 / 111320.0
    lon_per_m = 1.0 / (111320.0 * max(math.cos(math.radians(tx_lat)), 0.01))
    half_lat = radius_m * lat_per_m
    half_lon = radius_m * lon_per_m

    min_lat = tx_lat - half_lat
    max_lat = tx_lat + half_lat
    min_lon = tx_lon - half_lon
    max_lon = tx_lon + half_lon

    elev = ElevationGrid.fetch(
        min_lat=min_lat - pad_deg,
        min_lon=min_lon - pad_deg,
        max_lat=max_lat + pad_deg,
        max_lon=max_lon + pad_deg,
        n=elev_grid_n,
    )

    eirp_dbm = tx_power_dbm + tx_gain_dbi - cable_loss_db

    lats = np.linspace(min_lat, max_lat, grid_size)
    lons = np.linspace(min_lon, max_lon, grid_size)

    prx_grid = np.full((grid_size, grid_size), np.nan, dtype=np.float32)
    loss_grid = np.full((grid_size, grid_size), np.nan, dtype=np.float32)

    lat_grid_2d = lats.reshape(-1, 1).repeat(grid_size, axis=1)
    lon_grid_2d = lons.reshape(1, -1).repeat(grid_size, axis=0)
    dlat = (lat_grid_2d - tx_lat) / lat_per_m
    dlon = (lon_grid_2d - tx_lon) / lon_per_m
    dist_grid = np.sqrt(dlat * dlat + dlon * dlon)
    bearing_grid = (np.degrees(np.arctan2(dlon, dlat)) + 360.0) % 360.0

    # Build lightweight task args — coordinates only, no PFL serialization
    tasks = []
    for i in range(grid_size):
        for j in range(grid_size):
            d_m = float(dist_grid[i, j])
            if d_m < 50.0 or d_m > radius_m:
                continue
            bearing = float(bearing_grid[i, j])
            n_pts = max(3, min(int(round(d_m / profile_step_m)) + 1, max_profile_pts))
            step_m = d_m / (n_pts - 1)
            ant_gain_adj = _antenna_gain_factor(
                bearing, antenna_az_deg, antenna_beamwidth_deg
            )
            tasks.append(
                (
                    i,
                    j,
                    float(lats[i]),
                    float(lons[j]),
                    d_m,
                    bearing,
                    step_m,
                    n_pts,
                    tx_h_m,
                    rx_h_m,
                    climate,
                    N0,
                    f_mhz,
                    polarization,
                    epsilon,
                    sigma,
                    time_pct,
                    location_pct,
                    situation_pct,
                    eirp_dbm,
                    ant_gain_adj,
                    rx_gain_dbi,
                )
            )

    grid_meta = {
        "min_lat": elev.min_lat,
        "max_lat": elev.max_lat,
        "min_lon": elev.min_lon,
        "max_lon": elev.max_lon,
        "n_lat": elev.n_lat,
        "n_lon": elev.n_lon,
        "tx_lat": tx_lat,
        "tx_lon": tx_lon,
    }

    _own_pool = pool is None
    if _own_pool:
        pool = ProcessPoolExecutor(
            max_workers=max(1, os.cpu_count() or 1),
            initializer=_init_cov_pool,
            initargs=(elev.data, grid_meta),
        )
    else:
        # For shared pool, initialize grid data in this process too
        _init_cov_pool(elev.data, grid_meta)

    try:
        for result in pool.map(_itm_worker, tasks):
            if result is not None:
                i, j, loss_db, prx = result
                loss_grid[i, j] = loss_db
                prx_grid[i, j] = prx
    finally:
        if _own_pool:
            pool.shutdown(wait=True)

    rgba = np.zeros((grid_size, grid_size, 4), dtype=np.uint8)
    apply_coverage_colors(prx_grid, _THRESHOLDS, _COLORS, rgba)

    pil_img = Image.fromarray(rgba, mode="RGBA")
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    png_b64 = base64.b64encode(buf.getvalue()).decode()

    geo_bounds = [[min_lat, min_lon], [max_lat, max_lon]]

    valid = ~np.isnan(prx_grid)
    stats = {
        "pixels_total": int(grid_size * grid_size),
        "pixels_valid": int(valid.sum()),
        "prx_min_dbm": float(np.nanmin(prx_grid)) if valid.any() else None,
        "prx_max_dbm": float(np.nanmax(prx_grid)) if valid.any() else None,
        "pct_above_sensitivity": (
            float((prx_grid[valid] >= rx_sensitivity_dbm).sum())
            / max(valid.sum(), 1)
            * 100.0
            if valid.any()
            else 0.0
        ),
        "terrain_grid_n": int(elev_grid_n),
        "terrain_spacing_m": round(
            (elev.d_lat + elev.d_lon * math.cos(math.radians(tx_lat)))
            / 2.0
            / deg_per_m,
            1,
        ),
        "terrain_elev_min_m": float(np.nanmin(elev.data)),
        "terrain_elev_max_m": float(np.nanmax(elev.data)),
        "terrain_elev_std_m": round(float(np.nanstd(elev.data)), 1),
        "loss_min_db": float(np.nanmin(loss_grid)) if valid.any() else None,
        "loss_max_db": float(np.nanmax(loss_grid)) if valid.any() else None,
    }

    legend = [
        {"threshold_dbm": t, "rgba": list(c), "label": lbl}
        for t, c, lbl in SIGNAL_LEVELS
    ]

    out = {
        "png_base64": png_b64,
        "bounds": geo_bounds,
        "legend": legend,
        "eirp_dbm": round(eirp_dbm, 2),
        "rx_sensitivity_dbm": rx_sensitivity_dbm,
        "stats": stats,
        "from_cache": False,
    }
    _png_cache[cache_key] = {k: v for k, v in out.items() if k != "from_cache"}
    return out

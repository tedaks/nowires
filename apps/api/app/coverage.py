"""
Per-pixel ITM coverage with link-budget (dBm) output.

For each output pixel we extract a real terrain profile from TX to that pixel
(bilinear-sampled from a pre-fetched elevation grid) and call ITM. Path loss
is combined with TX power, antenna gains, cable loss, and optional antenna
pattern to produce received power in dBm, which is then colored by signal
level the way commercial radio planning tools do.
"""

import hashlib
import math
import os
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Dict

import numpy as np

from .coverage_render import build_coverage_tasks, render_coverage_result
from .coverage_workers import _init_cov_pool, _itm_worker
from .elevation_grid import ElevationGrid

_PNG_CACHE_MAX = 32
_png_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()


def _cache_get(key: str) -> Dict[str, Any] | None:
    if key in _png_cache:
        _png_cache.move_to_end(key)
        return _png_cache[key]
    return None


def _cache_put(key: str, value: Dict[str, Any]) -> None:
    if key in _png_cache:
        _png_cache.move_to_end(key)
    else:
        _png_cache[key] = value
    if len(_png_cache) > _PNG_CACHE_MAX:
        _png_cache.popitem(last=False)


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
    cache_key = hashlib.sha256(cache_key_src.encode()).hexdigest()
    cached = _cache_get(cache_key)
    if cached is not None:
        return {**cached, "from_cache": True}
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
        source="glo30",
    )
    eirp_dbm = tx_power_dbm + tx_gain_dbi - cable_loss_db
    lats = np.linspace(min_lat, max_lat, grid_size)
    lons = np.linspace(min_lon, max_lon, grid_size)
    prx_grid = np.full((grid_size, grid_size), np.nan, dtype=np.float32)
    loss_grid = np.full((grid_size, grid_size), np.nan, dtype=np.float32)
    tasks = build_coverage_tasks(
        tx_lat,
        tx_lon,
        radius_m,
        grid_size,
        profile_step_m,
        max_profile_pts,
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
        rx_gain_dbi,
        antenna_az_deg,
        antenna_beamwidth_deg,
        lats,
        lons,
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
    pool = ProcessPoolExecutor(
        max_workers=max(1, os.cpu_count() or 1),
        initializer=_init_cov_pool,
        initargs=(elev.data, grid_meta),
    )
    try:
        for result in pool.map(_itm_worker, tasks):
            if result is not None:
                i, j, loss_db, prx = result
                loss_grid[i, j] = loss_db
                prx_grid[i, j] = prx
    finally:
        pool.shutdown(wait=True)
    out = render_coverage_result(
        prx_grid,
        loss_grid,
        grid_size,
        elev,
        elev_grid_n,
        tx_lat,
        eirp_dbm,
        rx_sensitivity_dbm,
        deg_per_m,
        min_lat,
        max_lat,
        min_lon,
        max_lon,
    )
    _cache_put(cache_key, {k: v for k, v in out.items() if k != "from_cache"})
    return out

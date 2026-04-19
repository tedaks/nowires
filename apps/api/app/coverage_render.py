import math

import numpy as np

from .antenna import antenna_gain_factor as _antenna_gain_factor
from .signal_levels import COLORS as _COLORS
from .signal_levels import SIGNAL_LEVELS
from .signal_levels import THRESHOLDS as _THRESHOLDS


def build_coverage_tasks(
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
):
    lat_per_m = 1.0 / 111320.0
    lon_per_m = 1.0 / (111320.0 * max(math.cos(math.radians(tx_lat)), 0.01))
    lat_grid_2d = lats.reshape(-1, 1).repeat(grid_size, axis=1)
    lon_grid_2d = lons.reshape(1, -1).repeat(grid_size, axis=0)
    dlat = (lat_grid_2d - tx_lat) / lat_per_m
    dlon = (lon_grid_2d - tx_lon) / lon_per_m
    dist_grid = np.sqrt(dlat * dlat + dlon * dlon)
    bearing_grid = (np.degrees(np.arctan2(dlon, dlat)) + 360.0) % 360.0

    tasks = []
    for i in range(grid_size):
        for j in range(grid_size):
            d_m = float(dist_grid[i, j])
            if d_m < 50.0 or d_m > radius_m:
                continue
            bearing = float(bearing_grid[i, j])
            n_pts = max(3, min(int(round(d_m / profile_step_m)) + 1, max_profile_pts))
            step_m = d_m / (n_pts - 1)
            ant_gain_adj = _antenna_gain_factor(bearing, antenna_az_deg, antenna_beamwidth_deg)
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
    return tasks


def render_coverage_result(
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
    pixels_attempted=0,
    pixels_failed=0,
):
    import base64
    import io

    from PIL import Image

    from .math_kernels import apply_coverage_colors

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
        "pixels_attempted": int(pixels_attempted),
        "pixels_failed": int(pixels_failed),
        "prx_min_dbm": float(np.nanmin(prx_grid)) if valid.any() else None,
        "prx_max_dbm": float(np.nanmax(prx_grid)) if valid.any() else None,
        "pct_above_sensitivity": (
            float((prx_grid[valid] >= rx_sensitivity_dbm).sum()) / max(valid.sum(), 1) * 100.0
            if valid.any()
            else 0.0
        ),
        "terrain_grid_n": int(elev_grid_n),
        "terrain_spacing_m": round(
            (elev.d_lat + elev.d_lon * math.cos(math.radians(tx_lat))) / 2.0 / deg_per_m,
            1,
        ),
        "terrain_elev_min_m": float(np.nanmin(elev.data)),
        "terrain_elev_max_m": float(np.nanmax(elev.data)),
        "terrain_elev_std_m": round(float(np.nanstd(elev.data)), 1),
        "loss_min_db": float(np.nanmin(loss_grid)) if valid.any() else None,
        "loss_max_db": float(np.nanmax(loss_grid)) if valid.any() else None,
    }

    legend = [{"threshold_dbm": t, "rgba": list(c), "label": lbl} for t, c, lbl in SIGNAL_LEVELS]

    out = {
        "png_base64": png_b64,
        "bounds": geo_bounds,
        "legend": legend,
        "eirp_dbm": round(eirp_dbm, 2),
        "rx_sensitivity_dbm": rx_sensitivity_dbm,
        "stats": stats,
        "from_cache": False,
    }
    return out

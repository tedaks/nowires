import math
import numpy as np
import numba
from numba import prange


@numba.jit(nopython=True, cache=True)
def fresnel_profile_analysis(
    distances: np.ndarray,
    elevations: np.ndarray,
    tx_antenna_h: float,
    rx_antenna_h: float,
    dist_m: float,
    wavelength_m: float,
    k_factor: float,
):
    """Vectorised Fresnel/earth-bulge/LOS analysis over a terrain profile.

    Returns six arrays of length N:
        terrain_bulge  — terrain elevation + earth bulge (m)
        los_h          — LOS height at each point (m)
        fresnel_r      — 1st Fresnel zone radius (m)
        obstructs_los  — True where terrain_bulge > los_h
        violates_f1    — True where terrain_bulge > los_h - fresnel_r
        violates_f60   — True where terrain_bulge > los_h - 0.6*fresnel_r
    """
    n = len(distances)
    terrain_bulge = np.empty(n, dtype=np.float64)
    los_h = np.empty(n, dtype=np.float64)
    fresnel_r = np.empty(n, dtype=np.float64)
    obstructs_los = np.empty(n, dtype=np.bool_)
    violates_f1 = np.empty(n, dtype=np.bool_)
    violates_f60 = np.empty(n, dtype=np.bool_)

    a_eff = k_factor * 6371000.0

    for i in range(n):
        d = distances[i]
        t = d / dist_m if dist_m > 0.0 else 0.0
        bulge = (d * (dist_m - d)) / (2.0 * a_eff)
        tb = elevations[i] + bulge
        los = tx_antenna_h + t * (rx_antenna_h - tx_antenna_h)
        d2 = dist_m - d
        fr = (
            math.sqrt(wavelength_m * d * d2 / (d + d2)) if d > 0.0 and d2 > 0.0 else 0.0
        )

        terrain_bulge[i] = tb
        los_h[i] = los
        fresnel_r[i] = fr
        obstructs_los[i] = tb > los
        violates_f1[i] = tb > (los - fr)
        violates_f60[i] = tb > (los - 0.6 * fr)

    return terrain_bulge, los_h, fresnel_r, obstructs_los, violates_f1, violates_f60


@numba.jit(nopython=True, parallel=True, cache=True)
def apply_coverage_colors(
    prx_grid: np.ndarray,
    thresholds: np.ndarray,
    colors: np.ndarray,
    rgba_out: np.ndarray,
) -> None:
    """Map a float32 prx grid to RGBA pixels in-place with a y-axis flip.

    prx_grid  — float32 (rows, cols), NaN = no data
    thresholds — float64 (K,) descending threshold values
    colors    — uint8 (K+1, 4) RGBA per bucket; last row is the below-all-thresholds color
    rgba_out  — uint8 (rows, cols, 4) output, written in place
    """
    rows, cols = prx_grid.shape
    n_thresh = len(thresholds)
    for i in prange(rows):
        out_row = rows - 1 - i
        for j in range(cols):
            v = prx_grid[i, j]
            if np.isnan(v):
                rgba_out[out_row, j, 0] = 0
                rgba_out[out_row, j, 1] = 0
                rgba_out[out_row, j, 2] = 0
                rgba_out[out_row, j, 3] = 0
                continue
            k = n_thresh  # default: below all thresholds
            for t_idx in range(n_thresh):
                if v >= thresholds[t_idx]:
                    k = t_idx
                    break
            rgba_out[out_row, j, 0] = colors[k, 0]
            rgba_out[out_row, j, 1] = colors[k, 1]
            rgba_out[out_row, j, 2] = colors[k, 2]
            rgba_out[out_row, j, 3] = colors[k, 3]

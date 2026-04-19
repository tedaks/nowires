import math
from typing import List, Tuple

import numpy as np

SIGNAL_LEVELS: List[Tuple[float, Tuple[int, int, int, int], str]] = [
    (-60.0, (0, 110, 40, 210), "Excellent"),
    (-75.0, (0, 180, 80, 200), "Good"),
    (-85.0, (180, 220, 40, 195), "Fair"),
    (-95.0, (240, 180, 40, 190), "Marginal"),
    (-105.0, (230, 110, 40, 185), "Weak"),
    (-120.0, (200, 40, 40, 0), "No service"),
]

THRESHOLDS = np.array([t for t, _, _ in SIGNAL_LEVELS], dtype=np.float64)
COLORS = np.array([list(c) for _, c, _ in SIGNAL_LEVELS] + [[90, 20, 20, 0]], dtype=np.uint8)

_MISSING_SENTINEL = float("nan")


def _interpolate_nans(values: List[float]) -> List[float]:
    """Replace NaN values with linear interpolation from nearest numeric neighbours.

    NaN represents missing elevation data. This fills interior gaps by averaging
    the nearest numeric values on each side. Leading/trailing NaNs are replaced
    with the nearest available numeric value. If all values are NaN, returns the
    input unchanged.
    """
    if not values:
        return values
    filled = list(values)
    for i in range(len(filled)):
        if math.isnan(filled[i]):
            left = None
            for j in range(i - 1, -1, -1):
                if not math.isnan(filled[j]):
                    left = filled[j]
                    break
            right = None
            for j in range(i + 1, len(filled)):
                if not math.isnan(filled[j]):
                    right = filled[j]
                    break
            if left is not None and right is not None:
                filled[i] = (left + right) / 2.0
            elif left is not None:
                filled[i] = left
            elif right is not None:
                filled[i] = right
    return filled


def prx_to_color(prx_dbm: float) -> Tuple[int, int, int, int]:
    if not math.isfinite(prx_dbm):
        return (0, 0, 0, 0)
    for thresh, rgba, _ in SIGNAL_LEVELS:
        if prx_dbm >= thresh:
            return rgba
    return (90, 20, 20, 0)


def build_pfl(elevations: np.ndarray, step_m: float) -> List[float]:
    n = len(elevations) - 1
    return [float(n), float(step_m)] + [float(x) for x in elevations]


def bearing_destination(
    lat: float, lon: float, bearing_deg: float, dist_m: float
) -> Tuple[float, float]:
    R = 6371000.0
    brng = math.radians(bearing_deg)
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    d_r = dist_m / R
    lat2 = math.asin(
        math.sin(lat_r) * math.cos(d_r) + math.cos(lat_r) * math.sin(d_r) * math.cos(brng)
    )
    lon2 = lon_r + math.atan2(
        math.sin(brng) * math.sin(d_r) * math.cos(lat_r),
        math.cos(d_r) - math.sin(lat_r) * math.sin(lat2),
    )
    return math.degrees(lat2), math.degrees(lon2)


def sample_line_from_grid(gd, gm, lat1, lon1, lat2, lon2, n_pts):
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

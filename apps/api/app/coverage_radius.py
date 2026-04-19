import math
import os
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Dict

import numpy as np

from .coverage_workers import _init_radius_pool, _radius_worker
from .elevation_grid import ElevationGrid


def compute_coverage_radius(
    tx_lat: float,
    tx_lon: float,
    tx_h_m: float,
    rx_h_m: float,
    f_mhz: float,
    radius_km: float = 100.0,
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
    elevation_source: str = "glo30",
) -> Dict[str, Any]:
    deg_per_m = 1.0 / 111320.0
    pad_deg = 2.0 * terrain_spacing_m * deg_per_m
    search_max_m = radius_km * 1000.0
    padded_bbox_m = 2.0 * search_max_m + 4.0 * terrain_spacing_m
    if elev_grid_n is None:
        elev_grid_n = max(64, min(1024, int(padded_bbox_m / terrain_spacing_m) + 1))

    lat_per_m = 1.0 / 111320.0
    lon_per_m = 1.0 / (111320.0 * max(math.cos(math.radians(tx_lat)), 0.01))
    half_lat = search_max_m * lat_per_m
    half_lon = search_max_m * lon_per_m

    elev = ElevationGrid.fetch(
        min_lat=tx_lat - half_lat - pad_deg,
        min_lon=tx_lon - half_lon - pad_deg,
        max_lat=tx_lat + half_lat + pad_deg,
        max_lon=tx_lon + half_lon + pad_deg,
        n=elev_grid_n,
        source=elevation_source,
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

    sweep_step_m = max(500.0, terrain_spacing_m * 2.0)
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
            sweep_step_m,
            search_max_m,
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
        "per_bearing": [(float(b), round(r / 1000.0, 2)) for b, r in radius_per_bearing],
    }

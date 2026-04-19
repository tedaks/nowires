import logging
import math
from typing import Optional

import numpy as np

from .antenna import antenna_gain_factor as _antenna_gain_factor
from .itm_bridge import itm_p2p_loss
from .signal_levels import (
    bearing_destination as _bearing_destination,
)
from .signal_levels import (
    build_pfl as _build_pfl,
)
from .signal_levels import (
    sample_line_from_grid as _sample_line_from_grid,
)

logger = logging.getLogger(__name__)

ITM_LOSS_UPPER_BOUND = 400.0
RADIUS_CONSECUTIVE_MISS_LIMIT = 3

_cov_grid_data: Optional[np.ndarray] = None
_cov_grid_meta: dict = {}

_radius_grid_data: Optional[np.ndarray] = None
_radius_grid_meta: dict = {}


def _init_cov_pool(grid_data: np.ndarray, grid_meta: dict) -> None:
    global _cov_grid_data, _cov_grid_meta
    _cov_grid_data = grid_data
    _cov_grid_meta = grid_meta


def _init_radius_pool(grid_data: np.ndarray, grid_meta: dict) -> None:
    global _radius_grid_data, _radius_grid_meta
    _radius_grid_data = grid_data
    _radius_grid_meta = grid_meta


def _itm_worker(args):
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
    except Exception as e:
        logger.warning("ITM worker failed for pixel (%d,%d): %s", i, j, e)
        return None
    if not math.isfinite(res.loss_db) or res.loss_db > ITM_LOSS_UPPER_BOUND:
        logger.debug(
            "ITM returned non-finite or extreme loss for pixel (%d,%d): %s", i, j, res.loss_db
        )
        return None
    prx = eirp_dbm + ant_gain_adj + rx_gain_dbi - res.loss_db
    return (i, j, res.loss_db, prx)


def _radius_worker(args):
    """Sweep search along a bearing from TX to find maximum coverage distance.

    Increments distance by sweep_step_m at each step. When the received signal
    falls below rx_sensitivity_dbm for RADIUS_CONSECUTIVE_MISS_LIMIT consecutive
    steps, the search terminates. Returns the last distance where signal was
    above sensitivity, or 0.0 if never reached.
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
        sweep_step_m,
        search_max_m,
    ) = args
    gd = _radius_grid_data
    gm = _radius_grid_meta
    ant_gain_adj = _antenna_gain_factor(bearing_deg, antenna_az_deg, antenna_beamwidth_deg)
    profile_step_target = max(100.0, sweep_step_m * 0.5)

    consecutive_below = 0
    last_good = 0.0
    d = sweep_step_m
    while d <= search_max_m:
        lat_end, lon_end = _bearing_destination(tx_lat, tx_lon, bearing_deg, d)
        n_pts = max(3, min(int(round(d / profile_step_target)) + 1, 500))
        elevs = _sample_line_from_grid(gd, gm, tx_lat, tx_lon, lat_end, lon_end, n_pts)
        step_m = d / (n_pts - 1)
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
            loss_ok = math.isfinite(res.loss_db)
        except Exception as e:
            logger.warning("ITM radius worker at bearing %.1f d=%.0fm: %s", bearing_deg, d, e)
            loss_ok = False

        if loss_ok:
            prx = eirp_dbm + ant_gain_adj + rx_gain_dbi - res.loss_db
            if prx >= rx_sensitivity_dbm:
                last_good = d
                consecutive_below = 0
            else:
                consecutive_below += 1
        else:
            consecutive_below += 1

        if consecutive_below >= RADIUS_CONSECUTIVE_MISS_LIMIT:
            break
        d += sweep_step_m

    return (bearing_deg, last_good)

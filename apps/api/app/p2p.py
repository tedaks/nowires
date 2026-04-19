import math
from typing import Any, Dict, List

import numpy as np

from .itm_bridge import PROP_MODE_NAMES, itm_p2p_loss
from .math_kernels import fresnel_profile_analysis
from .terrain import haversine_m
from .terrain import profile as get_profile

C = 299792458.0
EARTH_RADIUS_M = 6371000.0


def fresnel_radius(d1_m: float, d2_m: float, f_mhz: float) -> float:
    if d1_m <= 0 or d2_m <= 0:
        return 0.0
    lambda_m = C / (f_mhz * 1e6)
    return math.sqrt(lambda_m * d1_m * d2_m / (d1_m + d2_m))


def earth_bulge(d_m: float, total_dist_m: float, k_factor: float) -> float:
    a_eff = k_factor * EARTH_RADIUS_M
    return (d_m * (total_dist_m - d_m)) / (2.0 * a_eff)


def build_pfl(elevations: List[float], step_m: float) -> List[float]:
    n = len(elevations) - 1
    return [float(n), step_m] + elevations


def analyze_p2p(
    tx_lat: float,
    tx_lon: float,
    tx_h_m: float,
    rx_lat: float,
    rx_lon: float,
    rx_h_m: float,
    f_mhz: float = 300.0,
    polarization: int = 0,
    climate: int = 1,
    N0: float = 301.0,
    epsilon: float = 15.0,
    sigma: float = 0.005,
    time_pct: float = 50.0,
    location_pct: float = 50.0,
    situation_pct: float = 50.0,
    k_factor: float = 4.0 / 3.0,
    tx_power_dbm: float = 43.0,
    tx_gain_dbi: float = 8.0,
    rx_gain_dbi: float = 2.0,
    cable_loss_db: float = 2.0,
    rx_sensitivity_dbm: float = -100.0,
) -> Dict[str, Any]:
    dist_m = haversine_m(tx_lat, tx_lon, rx_lat, rx_lon)
    points = get_profile(tx_lat, tx_lon, rx_lat, rx_lon, step_m=30.0)

    if len(points) < 2:
        return {"error": "Profile too short"}

    distances = [p[0] for p in points]
    elevations = [p[1] for p in points]
    step_m = distances[1] - distances[0] if len(distances) > 1 else 30.0

    pfl = build_pfl(elevations, step_m)

    result = itm_p2p_loss(
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

    tx_elev = elevations[0]
    rx_elev = elevations[-1]
    tx_antenna_h = tx_elev + tx_h_m
    rx_antenna_h = rx_elev + rx_h_m

    dist_arr = np.asarray(distances, dtype=np.float64)
    elev_arr = np.asarray(elevations, dtype=np.float64)
    wavelength_m = C / (f_mhz * 1e6)

    terrain_bulge, los_h_arr, fresnel_r_arr, obstructs_arr, vf1_arr, vf60_arr = (
        fresnel_profile_analysis(
            dist_arr,
            elev_arr,
            tx_antenna_h,
            rx_antenna_h,
            dist_m,
            wavelength_m,
            k_factor,
        )
    )

    any_blockage = bool(obstructs_arr.any())
    any_fresnel_violation = bool(vf1_arr.any())
    any_fresnel60_violation = bool(vf60_arr.any())

    profile_data = []
    for i in range(len(distances)):
        d = distances[i]
        terrain = elevations[i]
        tb = float(terrain_bulge[i])
        los = float(los_h_arr[i])
        fr = float(fresnel_r_arr[i])
        profile_data.append(
            {
                "d": round(d, 1),
                "terrain": round(terrain, 1),
                "terrain_bulge": round(tb, 2),
                "los": round(los, 2),
                "fresnel_upper": round(los + fr, 2),
                "fresnel_lower": round(los - fr, 2),
                "fresnel_60": round(los - 0.6 * fr, 2),
                "blocked": bool(obstructs_arr[i]),
                "violates_f1": bool(vf1_arr[i]),
                "violates_f60": bool(vf60_arr[i]),
            }
        )

    max_chart_points = 400
    if len(profile_data) > max_chart_points:
        step = (len(profile_data) - 1) / (max_chart_points - 1)
        downsampled = [
            profile_data[min(int(i * step), len(profile_data) - 1)] for i in range(max_chart_points)
        ]
        profile_data = downsampled

    eirp_dbm = tx_power_dbm + tx_gain_dbi - cable_loss_db
    prx_dbm = eirp_dbm + rx_gain_dbi - result.loss_db
    margin_db = prx_dbm - rx_sensitivity_dbm
    fspl_db = (
        20.0 * math.log10(dist_m / 1000.0) + 20.0 * math.log10(f_mhz) + 32.44
        if dist_m > 0 and f_mhz > 0
        else 0.0
    )

    link_budget = {
        "tx_power_dbm": round(tx_power_dbm, 2),
        "tx_gain_dbi": round(tx_gain_dbi, 2),
        "rx_gain_dbi": round(rx_gain_dbi, 2),
        "cable_loss_db": round(cable_loss_db, 2),
        "eirp_dbm": round(eirp_dbm, 2),
        "fspl_db": round(fspl_db, 2),
        "itm_loss_db": round(result.loss_db, 2),
        "excess_loss_db": round(result.loss_db - fspl_db, 2),
        "prx_dbm": round(prx_dbm, 2),
        "rx_sensitivity_dbm": round(rx_sensitivity_dbm, 2),
        "margin_db": round(margin_db, 2),
    }

    horizons = []
    if 0 < result.d_hzn_tx_m < dist_m:
        horizons.append({"role": "tx_horizon", "d_m": round(result.d_hzn_tx_m, 1)})
    if 0 < result.d_hzn_rx_m < dist_m:
        horizons.append({"role": "rx_horizon", "d_m": round(dist_m - result.d_hzn_rx_m, 1)})

    return {
        "distance_m": round(dist_m, 1),
        "profile": profile_data,
        "loss_db": round(result.loss_db, 2),
        "mode": result.mode,
        "mode_name": PROP_MODE_NAMES.get(result.mode, "Unknown"),
        "warnings": result.warnings,
        "link_budget": link_budget,
        "horizons": horizons,
        "flags": {
            "los_blocked": any_blockage,
            "fresnel_f1_violated": any_fresnel_violation,
            "fresnel_60_violated": any_fresnel60_violation,
        },
        "k_factor": round(k_factor, 3),
        "intermediates": {
            "d_hzn_tx_m": round(result.d_hzn_tx_m, 1),
            "d_hzn_rx_m": round(result.d_hzn_rx_m, 1),
            "h_e_tx_m": round(result.h_e_tx_m, 2),
            "h_e_rx_m": round(result.h_e_rx_m, 2),
            "delta_h_m": round(result.delta_h_m, 2),
            "A_ref_db": round(result.A_ref_db, 2),
        },
    }

from dataclasses import dataclass

from itm import Climate, Polarization, TerrainProfile, predict_p2p

PROP_MODE_NAMES = {
    0: "Line-of-Sight",
    1: "Single Horizon Diffraction",
    2: "Double Horizon Diffraction",
    3: "Troposcatter",
    4: "Diffraction LOS Backward",
    5: "Mixed Path",
}


@dataclass
class ITMResult:
    loss_db: float
    mode: int
    warnings: int
    d_hzn_tx_m: float = 0.0
    d_hzn_rx_m: float = 0.0
    theta_hzn_tx: float = 0.0
    theta_hzn_rx: float = 0.0
    h_e_tx_m: float = 0.0
    h_e_rx_m: float = 0.0
    N_s: float = 0.0
    delta_h_m: float = 0.0
    A_ref_db: float = 0.0
    A_fs_db: float = 0.0
    d_km: float = 0.0


def itm_p2p_loss(
    h_tx__meter: float,
    h_rx__meter: float,
    profile: list,
    climate: int = 1,
    N0: float = 301.0,
    f__mhz: float = 300.0,
    polarization: int = 0,
    epsilon: float = 15.0,
    sigma: float = 0.005,
    mdvar: int = 0,
    time_pct: float = 50.0,
    location_pct: float = 50.0,
    situation_pct: float = 50.0,
) -> ITMResult:
    terrain = TerrainProfile.from_pfl(profile)

    climate_enum = Climate(int(climate) + 1)
    pol_enum = Polarization(int(polarization))

    try:
        result = predict_p2p(
            h_tx__meter=h_tx__meter,
            h_rx__meter=h_rx__meter,
            terrain=terrain,
            climate=climate_enum,
            N_0=N0,
            f__mhz=f__mhz,
            pol=pol_enum,
            epsilon=epsilon,
            sigma=sigma,
            mdvar=int(mdvar),
            time=time_pct,
            location=location_pct,
            situation=situation_pct,
            return_intermediate=True,
        )
    except (ValueError, RuntimeError, FloatingPointError):
        return ITMResult(loss_db=999.0, mode=0, warnings=1)

    inter = result.intermediate

    mode = 0
    if inter is not None:
        mode_val = inter.mode
        if mode_val is not None and not (isinstance(mode_val, float) and mode_val != mode_val):
            mode = int(mode_val)

    warnings_val = int(result.warnings)

    if inter is not None:
        return ITMResult(
            loss_db=result.A__db,
            mode=mode,
            warnings=warnings_val,
            d_hzn_tx_m=inter.d_hzn__meter[0],
            d_hzn_rx_m=inter.d_hzn__meter[1],
            theta_hzn_tx=inter.theta_hzn[0],
            theta_hzn_rx=inter.theta_hzn[1],
            h_e_tx_m=inter.h_e__meter[0],
            h_e_rx_m=inter.h_e__meter[1],
            N_s=inter.N_s,
            delta_h_m=inter.delta_h__meter,
            A_ref_db=inter.A_ref__db,
            A_fs_db=inter.A_fs__db,
            d_km=inter.d__km,
        )

    return ITMResult(
        loss_db=result.A__db,
        mode=mode,
        warnings=warnings_val,
    )

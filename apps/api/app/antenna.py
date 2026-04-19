def antenna_gain_factor(
    bearing_from_tx_deg: float,
    az_deg: float | None,
    beamwidth_deg: float,
    front_back_db: float = 25.0,
) -> float:
    if az_deg is None:
        return 0.0
    diff = (bearing_from_tx_deg - az_deg + 540.0) % 360.0 - 180.0
    if abs(diff) <= beamwidth_deg / 2.0:
        x = diff / (beamwidth_deg / 2.0)
        attn = 3.0 * x * x
        return -attn
    return -front_back_db

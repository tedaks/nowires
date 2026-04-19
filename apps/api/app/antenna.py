"""Antenna radiation pattern model.

Uses a simplified parabolic pattern within the main beam (3 dB roll-off at
beamwidth edges) and a fixed front-to-back ratio outside the beam. This is a
common first-order approximation used in coverage planning — not based on a
specific ITU-R pattern template.

The default front_back_db=25.0 is a typical value for panel antennas in the
UHF band. Adjust for specific antenna specifications.
"""


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

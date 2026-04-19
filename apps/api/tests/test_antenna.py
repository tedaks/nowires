import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.antenna import antenna_gain_factor


@pytest.mark.parametrize(
    "bearing,az,bw,expected",
    [
        (0, 0, 60, 0.0),
        (30, 0, 60, -3.0),
        (31, 0, 60, -25.0),
        (180, 0, 60, -25.0),
        (-30, 0, 60, -3.0),
        (0, None, 360, 0.0),
        (45, 0, 120, -1.6875),
        (90, 0, 60, -25.0),
        (60, 0, 120, -3.0),
    ],
)
def test_antenna_gain_factor(bearing, az, bw, expected):
    result = antenna_gain_factor(bearing, az, bw)
    assert abs(result - expected) < 0.01, f"Expected {expected}, got {result}"


def test_antenna_gain_factor_inside_beam_negative():
    result = antenna_gain_factor(bearing_from_tx_deg=15, az_deg=0, beamwidth_deg=60)
    assert result < 0
    assert result > -25.0


def test_antenna_gain_factor_omni_returns_zero():
    assert antenna_gain_factor(90, None, 360) == 0.0
    assert antenna_gain_factor(0, None, 60) == 0.0


def test_antenna_gain_factor_at_beam_edge():
    result = antenna_gain_factor(bearing_from_tx_deg=30, az_deg=0, beamwidth_deg=60)
    assert abs(result - (-3.0)) < 0.01


def test_antenna_gain_factor_custom_front_back():
    result = antenna_gain_factor(180, 0, 60, front_back_db=30.0)
    assert abs(result - (-30.0)) < 0.01

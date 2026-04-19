import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

C = 299792458.0


def test_build_pfl_converts_types():
    import numpy as np

    from app.signal_levels import build_pfl

    elevations = np.array([10.0, 20.0, 30.0])
    result = build_pfl(elevations, 100.0)
    assert result == [2.0, 100.0, 10.0, 20.0, 30.0]
    assert all(isinstance(x, float) for x in result)


def test_build_pfl_single_step():
    from app.signal_levels import build_pfl

    result = build_pfl([5.0, 10.0], 50.0)
    assert result == [1.0, 50.0, 5.0, 10.0]


def test_prx_to_color_excellent():
    from app.signal_levels import prx_to_color

    assert prx_to_color(-50.0) == (0, 110, 40, 210)


def test_prx_to_color_no_service():
    from app.signal_levels import prx_to_color

    result = prx_to_color(-110.0)
    assert result == (200, 40, 40, 0)


def test_prx_to_color_inf_returns_transparent():
    from app.signal_levels import prx_to_color

    assert prx_to_color(float("inf")) == (0, 0, 0, 0)
    assert prx_to_color(float("-inf")) == (0, 0, 0, 0)


def test_prx_to_color_threshold_boundaries():
    from app.signal_levels import SIGNAL_LEVELS, prx_to_color

    for threshold, rgba, label in SIGNAL_LEVELS:
        result = prx_to_color(threshold)
        assert result == rgba, f"At threshold {threshold}: got {result}, expected {rgba}"


def test_interpolate_nans_interior_gap():
    from app.signal_levels import _interpolate_nans

    result = _interpolate_nans([10.0, float("nan"), 20.0])
    assert result == [10.0, 15.0, 20.0]


def test_interpolate_nans_leading_nans():
    from app.signal_levels import _interpolate_nans

    result = _interpolate_nans([float("nan"), float("nan"), 10.0, 20.0])
    assert result == [10.0, 10.0, 10.0, 20.0]


def test_interpolate_nans_trailing_nans():
    from app.signal_levels import _interpolate_nans

    result = _interpolate_nans([10.0, 20.0, float("nan"), float("nan")])
    assert result == [10.0, 20.0, 20.0, 20.0]


def test_interpolate_nans_all_nans():
    from app.signal_levels import _interpolate_nans

    nan = float("nan")
    result = _interpolate_nans([nan, nan, nan])
    assert all(math.isnan(v) for v in result)


def test_interpolate_nans_empty():
    from app.signal_levels import _interpolate_nans

    assert _interpolate_nans([]) == []


def test_interpolate_nans_no_nans():
    from app.signal_levels import _interpolate_nans

    result = _interpolate_nans([10.0, 20.0, 30.0])
    assert result == [10.0, 20.0, 30.0]


def test_interpolate_nans_preserves_zero_elevation():
    from app.signal_levels import _interpolate_nans

    result = _interpolate_nans([5.0, 0.0, 10.0])
    assert result == [5.0, 0.0, 10.0]


def test_bearing_destination_short_distance():
    from app.signal_levels import bearing_destination

    lat2, lon2 = bearing_destination(14.5, 121.0, 0.0, 1000.0)
    assert abs(lat2 - 14.5) < 0.01
    assert abs(lon2 - 121.0) < 0.01


def test_bearing_destination_north():
    from app.signal_levels import bearing_destination

    lat2, lon2 = bearing_destination(0.0, 0.0, 0.0, 111320.0)
    assert abs(lat2 - 1.0) < 0.01
    assert abs(lon2) < 0.01

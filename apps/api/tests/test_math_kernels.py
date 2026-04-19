import math
import numpy as np
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

C = 299792458.0


def test_fresnel_arrays_have_correct_shape():
    from app.math_kernels import fresnel_profile_analysis

    n = 50
    distances = np.linspace(0, 5000.0, n)
    elevations = np.zeros(n, dtype=np.float64)
    tb, los, fr, obs, vf1, vf60 = fresnel_profile_analysis(
        distances, elevations, 30.0, 10.0, 5000.0, C / 300e6, 4.0 / 3.0
    )
    for arr in (tb, los, fr, obs, vf1, vf60):
        assert len(arr) == n


def test_fresnel_flat_terrain_no_blockage():
    from app.math_kernels import fresnel_profile_analysis

    n = 21
    dist_m = 2000.0
    distances = np.linspace(0, dist_m, n)
    elevations = np.zeros(n, dtype=np.float64)
    tb, los, fr, obs, vf1, vf60 = fresnel_profile_analysis(
        distances, elevations, 50.0, 50.0, dist_m, C / 300e6, 4.0 / 3.0
    )
    assert not obs.any(), "Flat terrain with high antennas must not block LOS"
    assert not vf60.any(), (
        "Flat terrain with high antennas must not violate 60% Fresnel"
    )


def test_fresnel_matches_scalar_functions():
    """fresnel_profile_analysis must reproduce the scalar loop in p2p.py exactly."""
    from app.math_kernels import fresnel_profile_analysis
    from app.p2p import fresnel_radius, earth_bulge

    n = 20
    dist_m = 3000.0
    f_mhz = 450.0
    k_factor = 4.0 / 3.0
    distances = np.linspace(0, dist_m, n)
    elevations = np.array(
        [10.0 * math.sin(i / n * math.pi) for i in range(n)], dtype=np.float64
    )
    tx_antenna_h = float(elevations[0]) + 20.0
    rx_antenna_h = float(elevations[-1]) + 5.0
    wavelength_m = C / (f_mhz * 1e6)

    tb, los, fr, obs, vf1, vf60 = fresnel_profile_analysis(
        distances,
        elevations,
        tx_antenna_h,
        rx_antenna_h,
        dist_m,
        wavelength_m,
        k_factor,
    )

    for i in range(n):
        d = float(distances[i])
        t = d / dist_m
        exp_bulge = earth_bulge(d, dist_m, k_factor)
        exp_tb = float(elevations[i]) + exp_bulge
        exp_los = tx_antenna_h + t * (rx_antenna_h - tx_antenna_h)
        exp_fr = fresnel_radius(d, dist_m - d, f_mhz)

        assert abs(float(tb[i]) - exp_tb) < 1e-6, f"terrain_bulge mismatch at i={i}"
        assert abs(float(los[i]) - exp_los) < 1e-6, f"los_h mismatch at i={i}"
        assert abs(float(fr[i]) - exp_fr) < 1e-6, f"fresnel_r mismatch at i={i}"
        assert bool(obs[i]) == (exp_tb > exp_los), f"obstructs_los mismatch at i={i}"
        assert bool(vf1[i]) == (exp_tb > (exp_los - exp_fr)), (
            f"violates_f1 mismatch at i={i}"
        )
        assert bool(vf60[i]) == (exp_tb > (exp_los - 0.6 * exp_fr)), (
            f"violates_f60 at i={i}"
        )


def test_apply_coverage_colors_excellent_signal():
    """Signal above highest threshold (-60 dBm) maps to Excellent color (0,110,40,210)."""
    from app.math_kernels import apply_coverage_colors
    from app.coverage import SIGNAL_LEVELS

    thresholds = np.array([t for t, _, _ in SIGNAL_LEVELS], dtype=np.float64)
    colors = np.array(
        [list(c) for _, c, _ in SIGNAL_LEVELS] + [[90, 20, 20, 0]], dtype=np.uint8
    )
    prx_grid = np.full((4, 4), -50.0, dtype=np.float32)
    rgba_out = np.zeros((4, 4, 4), dtype=np.uint8)

    apply_coverage_colors(prx_grid, thresholds, colors, rgba_out)

    np.testing.assert_array_equal(rgba_out[0, 0], [0, 110, 40, 210])


def test_apply_coverage_colors_below_all_thresholds():
    """Signal below all thresholds gets the fallback color with alpha=0 (transparent)."""
    from app.math_kernels import apply_coverage_colors
    from app.coverage import SIGNAL_LEVELS

    thresholds = np.array([t for t, _, _ in SIGNAL_LEVELS], dtype=np.float64)
    colors = np.array(
        [list(c) for _, c, _ in SIGNAL_LEVELS] + [[90, 20, 20, 0]], dtype=np.uint8
    )
    prx_grid = np.full((2, 2), -130.0, dtype=np.float32)
    rgba_out = np.zeros((2, 2, 4), dtype=np.uint8)

    apply_coverage_colors(prx_grid, thresholds, colors, rgba_out)

    np.testing.assert_array_equal(rgba_out[0, 0], [90, 20, 20, 0])


def test_apply_coverage_colors_no_service_is_transparent():
    """'No service' signals (>= -120 but < -105 dBm) must render with alpha=0."""
    from app.math_kernels import apply_coverage_colors
    from app.coverage import SIGNAL_LEVELS

    thresholds = np.array([t for t, _, _ in SIGNAL_LEVELS], dtype=np.float64)
    colors = np.array(
        [list(c) for _, c, _ in SIGNAL_LEVELS] + [[90, 20, 20, 0]], dtype=np.uint8
    )
    # -110 dBm falls in the "No service" bucket (>= -120, < -105)
    prx_grid = np.full((3, 3), -110.0, dtype=np.float32)
    rgba_out = np.zeros((3, 3, 4), dtype=np.uint8)

    apply_coverage_colors(prx_grid, thresholds, colors, rgba_out)

    assert rgba_out[:, :, 3].max() == 0, "No service pixels must have alpha=0"

def test_apply_coverage_colors_nan_is_transparent():
    """NaN pixels must produce alpha=0."""
    from app.math_kernels import apply_coverage_colors
    from app.coverage import SIGNAL_LEVELS

    thresholds = np.array([t for t, _, _ in SIGNAL_LEVELS], dtype=np.float64)
    colors = np.array(
        [list(c) for _, c, _ in SIGNAL_LEVELS] + [[90, 20, 20, 0]], dtype=np.uint8
    )
    prx_grid = np.full((3, 3), np.nan, dtype=np.float32)
    rgba_out = np.ones((3, 3, 4), dtype=np.uint8) * 255

    apply_coverage_colors(prx_grid, thresholds, colors, rgba_out)

    assert rgba_out[:, :, 3].max() == 0, "All NaN pixels must have alpha=0"


def test_apply_coverage_colors_y_flip():
    """prx_grid row 0 maps to rgba_out last row (image y-axis is flipped)."""
    from app.math_kernels import apply_coverage_colors
    from app.coverage import SIGNAL_LEVELS

    thresholds = np.array([t for t, _, _ in SIGNAL_LEVELS], dtype=np.float64)
    colors = np.array(
        [list(c) for _, c, _ in SIGNAL_LEVELS] + [[90, 20, 20, 0]], dtype=np.uint8
    )
    rows = 6
    prx_grid = np.full((rows, 4), np.nan, dtype=np.float32)
    prx_grid[0, :] = -50.0  # only row 0 has signal
    rgba_out = np.zeros((rows, 4, 4), dtype=np.uint8)

    apply_coverage_colors(prx_grid, thresholds, colors, rgba_out)

    assert rgba_out[rows - 1, 0, 3] > 0, "prx row 0 → image last row must be filled"
    assert rgba_out[0, 0, 3] == 0, "prx row 0 → image row 0 must be empty"


def test_apply_coverage_colors_matches_prx_to_color():
    """apply_coverage_colors must produce the same RGBA as the original _prx_to_color."""
    from app.math_kernels import apply_coverage_colors
    from app.coverage import SIGNAL_LEVELS, _prx_to_color

    thresholds = np.array([t for t, _, _ in SIGNAL_LEVELS], dtype=np.float64)
    colors = np.array(
        [list(c) for _, c, _ in SIGNAL_LEVELS] + [[90, 20, 20, 0]], dtype=np.uint8
    )
    test_values = [-50.0, -70.0, -80.0, -90.0, -100.0, -110.0, -130.0]
    rows = len(test_values)
    prx_grid = np.zeros((rows, 1), dtype=np.float32)
    for i, v in enumerate(test_values):
        prx_grid[i, 0] = v
    rgba_out = np.zeros((rows, 1, 4), dtype=np.uint8)

    apply_coverage_colors(prx_grid, thresholds, colors, rgba_out)

    for i, v in enumerate(test_values):
        img_row = rows - 1 - i
        expected = list(_prx_to_color(v))
        actual = list(rgba_out[img_row, 0])
        assert actual == expected, f"Mismatch at prx={v}: got {actual}, want {expected}"

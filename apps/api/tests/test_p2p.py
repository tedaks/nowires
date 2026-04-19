import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

C = 299792458.0


def test_fresnel_radius_basic():
    from app.p2p import fresnel_radius

    r = fresnel_radius(1000, 1000, 450)
    assert r > 0


def test_fresnel_radius_zero_distance():
    from app.p2p import fresnel_radius

    assert fresnel_radius(0, 1000, 450) == 0.0
    assert fresnel_radius(1000, 0, 450) == 0.0


def test_earth_bulge_basic():
    from app.p2p import earth_bulge

    b = earth_bulge(500, 1000, 4.0 / 3.0)
    assert b > 0


def test_earth_bulge_midpoint():
    from app.p2p import earth_bulge

    b_mid = earth_bulge(500, 1000, 4.0 / 3.0)
    b_end = earth_bulge(1000, 1000, 4.0 / 3.0)
    assert b_end < b_mid


def test_haversine():
    from app.p2p import haversine_m

    dist = haversine_m(14.5, 121.0, 14.6, 121.1)
    assert 10000 < dist < 20000


def test_analyze_p2p_returns_valid_structure():
    from app.p2p import analyze_p2p

    with patch("app.p2p.get_profile") as mock_profile:
        mock_profile.return_value = [(0, 50.0), (30, 55.0), (60, 52.0), (90, 48.0), (120, 50.0)]
        with patch("app.p2p.itm_p2p_loss") as mock_itm:
            mock_result = type(
                "R",
                (),
                {
                    "loss_db": 100.0,
                    "mode": 1,
                    "warnings": 0,
                    "d_hzn_tx_m": 50.0,
                    "d_hzn_rx_m": 50.0,
                    "h_e_tx_m": 30.0,
                    "h_e_rx_m": 10.0,
                    "delta_h_m": 5.0,
                    "A_ref_db": 20.0,
                },
            )()
            mock_itm.return_value = mock_result
            with patch("app.p2p.fresnel_profile_analysis") as mock_fresnel:
                import numpy as np

                n = 5
                mock_fresnel.return_value = (
                    np.zeros(n, dtype=np.float64),
                    np.full(n, 40.0, dtype=np.float64),
                    np.zeros(n, dtype=np.float64),
                    np.zeros(n, dtype=np.uint8),
                    np.zeros(n, dtype=np.uint8),
                    np.zeros(n, dtype=np.uint8),
                )
                result = analyze_p2p(
                    tx_lat=14.5,
                    tx_lon=121.0,
                    tx_h_m=30,
                    rx_lat=14.6,
                    rx_lon=121.1,
                    rx_h_m=10,
                    f_mhz=450,
                )
    assert "distance_m" in result
    assert "loss_db" in result
    assert "mode" in result
    assert "flags" in result
    assert "link_budget" in result
    assert "horizons" in result


def test_analyze_p2p_uses_signal_levels_build_pfl():
    from app.p2p import analyze_p2p

    with patch("app.p2p.get_profile") as mock_profile:
        mock_profile.return_value = [(0, 50.0), (30, 55.0), (60, 52.0), (90, 48.0), (120, 50.0)]
        with patch("app.p2p.itm_p2p_loss") as mock_itm:
            mock_result = type(
                "R",
                (),
                {
                    "loss_db": 100.0,
                    "mode": 1,
                    "warnings": 0,
                    "d_hzn_tx_m": 50.0,
                    "d_hzn_rx_m": 50.0,
                    "h_e_tx_m": 30.0,
                    "h_e_rx_m": 10.0,
                    "delta_h_m": 5.0,
                    "A_ref_db": 20.0,
                },
            )()
            mock_itm.return_value = mock_result
            with patch("app.p2p.fresnel_profile_analysis") as mock_fresnel:
                import numpy as np

                n = 5
                mock_fresnel.return_value = (
                    np.zeros(n, dtype=np.float64),
                    np.full(n, 40.0, dtype=np.float64),
                    np.zeros(n, dtype=np.float64),
                    np.zeros(n, dtype=np.uint8),
                    np.zeros(n, dtype=np.uint8),
                    np.zeros(n, dtype=np.uint8),
                )
                result = analyze_p2p(
                    tx_lat=14.5,
                    tx_lon=121.0,
                    tx_h_m=30,
                    rx_lat=14.6,
                    rx_lon=121.1,
                    rx_h_m=10,
                    f_mhz=450,
                )
    assert result["loss_db"] == 100.0

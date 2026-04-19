import math
import numpy as np
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _make_mock_itm_result(loss_db: float):
    r = MagicMock()
    r.loss_db = loss_db
    return r


def _setup_cov_grid():
    """Initialize _cov_grid_data and _cov_grid_meta for _itm_worker tests."""
    import app.coverage as cov
    cov._cov_grid_data = np.zeros((10, 10), dtype=np.float32)
    cov._cov_grid_meta = {
        "min_lat": 14.0,
        "max_lat": 15.0,
        "min_lon": 121.0,
        "max_lon": 122.0,
        "n_lat": 10,
        "n_lon": 10,
        "tx_lat": 14.5,
        "tx_lon": 121.5,
    }


def test_itm_worker_returns_tuple_on_success():
    import app.coverage as cov

    # New args format: (i, j, target_lat, target_lon, dist_m, bearing_deg,
    #   step_m, n_pts, tx_h_m, rx_h_m, climate, N0, f_mhz, polarization,
    #   epsilon, sigma, time_pct, location_pct, situation_pct,
    #   eirp_dbm, ant_gain_adj, rx_gain_dbi)
    args = (
        3,
        7,
        14.55,   # target_lat
        121.55,  # target_lon
        5000.0,  # dist_m
        45.0,    # bearing_deg
        500.0,   # step_m (dist_m / (n_pts - 1))
        11,      # n_pts
        30.0,    # tx_h_m
        10.0,    # rx_h_m
        1,       # climate
        301.0,   # N0
        300.0,   # f_mhz
        0,       # polarization
        15.0,    # epsilon
        0.005,   # sigma
        50.0,    # time_pct
        50.0,    # location_pct
        50.0,    # situation_pct
        49.0,    # eirp_dbm
        0.0,     # ant_gain_adj
        2.0,     # rx_gain_dbi
    )

    _setup_cov_grid()

    with patch.object(cov, "itm_p2p_loss", return_value=_make_mock_itm_result(100.0)):
        result = cov._itm_worker(args)

    assert result is not None
    i, j, loss_db, prx = result
    assert i == 3
    assert j == 7
    assert loss_db == 100.0
    assert abs(prx - (49.0 + 0.0 + 2.0 - 100.0)) < 1e-9


def test_itm_worker_returns_none_on_exception():
    import app.coverage as cov

    args = (
        0,
        0,
        14.55,
        121.55,
        5000.0,
        45.0,
        500.0,
        11,
        30.0,
        10.0,
        1,
        301.0,
        300.0,
        0,
        15.0,
        0.005,
        50.0,
        50.0,
        50.0,
        49.0,
        0.0,
        2.0,
    )

    _setup_cov_grid()

    with patch.object(cov, "itm_p2p_loss", side_effect=RuntimeError("ITM exploded")):
        result = cov._itm_worker(args)

    assert result is None


def test_itm_worker_returns_none_on_infinite_loss():
    import app.coverage as cov

    args = (
        0,
        0,
        14.55,
        121.55,
        5000.0,
        45.0,
        500.0,
        11,
        30.0,
        10.0,
        1,
        301.0,
        300.0,
        0,
        15.0,
        0.005,
        50.0,
        50.0,
        50.0,
        49.0,
        0.0,
        2.0,
    )

    _setup_cov_grid()

    with patch.object(
        cov, "itm_p2p_loss", return_value=_make_mock_itm_result(float("inf"))
    ):
        result = cov._itm_worker(args)

    assert result is None


def test_itm_worker_applies_antenna_gain_adjustment():
    import app.coverage as cov

    args = (
        1,
        2,
        14.55,
        121.55,
        5000.0,
        45.0,
        500.0,
        11,
        30.0,
        10.0,
        1,
        301.0,
        300.0,
        0,
        15.0,
        0.005,
        50.0,
        50.0,
        50.0,
        49.0,
        -5.0,
        2.0,
    )

    _setup_cov_grid()

    with patch.object(cov, "itm_p2p_loss", return_value=_make_mock_itm_result(80.0)):
        result = cov._itm_worker(args)

    assert result is not None
    _, _, loss_db, prx = result
    assert abs(prx - (49.0 + (-5.0) + 2.0 - 80.0)) < 1e-9


def test_radius_worker_returns_tuple():
    import app.coverage as cov

    cov._radius_grid_data = np.zeros((10, 10), dtype=np.float32)
    cov._radius_grid_meta = {
        "min_lat": 14.0,
        "max_lat": 15.0,
        "min_lon": 121.0,
        "max_lon": 122.0,
        "n_lat": 10,
        "n_lon": 10,
    }

    with patch.object(cov, "itm_p2p_loss", return_value=_make_mock_itm_result(300.0)):
        bearing, radius_m = cov._radius_worker(
            (
                45.0,
                14.5,
                121.5,
                30.0,
                10.0,
                300.0,
                0,
                1,
                301.0,
                15.0,
                0.005,
                50.0,
                50.0,
                50.0,
                49.0,
                2.0,
                -100.0,
                None,
                360.0,
            )
        )

    assert bearing == 45.0
    assert 100.0 <= radius_m <= 100_000.0


def test_radius_worker_low_loss_returns_large_radius():
    import app.coverage as cov

    cov._radius_grid_data = np.zeros((10, 10), dtype=np.float32)
    cov._radius_grid_meta = {
        "min_lat": 14.0,
        "max_lat": 15.0,
        "min_lon": 121.0,
        "max_lon": 122.0,
        "n_lat": 10,
        "n_lon": 10,
    }

    with patch.object(cov, "itm_p2p_loss", return_value=_make_mock_itm_result(10.0)):
        _, radius_m = cov._radius_worker(
            (
                90.0,
                14.5,
                121.5,
                30.0,
                10.0,
                300.0,
                0,
                1,
                301.0,
                15.0,
                0.005,
                50.0,
                50.0,
                50.0,
                49.0,
                2.0,
                -100.0,
                None,
                360.0,
            )
        )

    assert radius_m > 90_000.0, "Low loss should yield near-maximum radius"


def test_init_radius_pool_sets_globals():
    import app.coverage as cov

    data = np.ones((5, 5), dtype=np.float32)
    meta = {
        "min_lat": 1.0,
        "max_lat": 2.0,
        "min_lon": 3.0,
        "max_lon": 4.0,
        "n_lat": 5,
        "n_lon": 5,
    }

    cov._init_radius_pool(data, meta)

    np.testing.assert_array_equal(cov._radius_grid_data, data)
    assert cov._radius_grid_meta == meta


def test_init_cov_pool_sets_globals():
    import app.coverage as cov

    data = np.ones((5, 5), dtype=np.float32)
    meta = {
        "min_lat": 1.0,
        "max_lat": 2.0,
        "min_lon": 3.0,
        "max_lon": 4.0,
        "n_lat": 5,
        "n_lon": 5,
        "tx_lat": 1.5,
        "tx_lon": 3.5,
    }

    cov._init_cov_pool(data, meta)

    np.testing.assert_array_equal(cov._cov_grid_data, data)
    assert cov._cov_grid_meta == meta

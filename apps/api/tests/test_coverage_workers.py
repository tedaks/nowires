import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _make_mock_itm_result(loss_db: float):
    r = MagicMock()
    r.loss_db = loss_db
    return r


def _setup_cov_grid():
    import app.coverage_workers as cw

    cw._cov_grid_data = np.zeros((10, 10), dtype=np.float32)
    cw._cov_grid_meta = {
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
    import app.coverage_workers as cw

    args = (
        3,
        7,
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

    with patch.object(cw, "itm_p2p_loss", return_value=_make_mock_itm_result(100.0)):
        result = cw._itm_worker(args)

    assert result is not None
    i, j, loss_db, prx = result
    assert i == 3
    assert j == 7
    assert loss_db == 100.0
    assert abs(prx - (49.0 + 0.0 + 2.0 - 100.0)) < 1e-9


def test_itm_worker_returns_none_on_exception():
    import app.coverage_workers as cw

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

    with patch.object(cw, "itm_p2p_loss", side_effect=RuntimeError("ITM exploded")):
        result = cw._itm_worker(args)

    assert result is None


def test_itm_worker_returns_none_on_infinite_loss():
    import app.coverage_workers as cw

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

    with patch.object(cw, "itm_p2p_loss", return_value=_make_mock_itm_result(float("inf"))):
        result = cw._itm_worker(args)

    assert result is None


def test_itm_worker_applies_antenna_gain_adjustment():
    import app.coverage_workers as cw

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

    with patch.object(cw, "itm_p2p_loss", return_value=_make_mock_itm_result(80.0)):
        result = cw._itm_worker(args)

    assert result is not None
    _, _, loss_db, prx = result
    assert abs(prx - (49.0 + (-5.0) + 2.0 - 80.0)) < 1e-9


def test_radius_worker_returns_tuple():
    import app.coverage_workers as cw

    cw._radius_grid_data = np.zeros((10, 10), dtype=np.float32)
    cw._radius_grid_meta = {
        "min_lat": 14.0,
        "max_lat": 15.0,
        "min_lon": 121.0,
        "max_lon": 122.0,
        "n_lat": 10,
        "n_lon": 10,
    }

    with patch.object(cw, "itm_p2p_loss", return_value=_make_mock_itm_result(300.0)):
        bearing, radius_m = cw._radius_worker(
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
                500.0,
                100_000.0,
            )
        )

    assert bearing == 45.0
    assert radius_m == 0.0


def test_radius_worker_low_loss_returns_large_radius():
    import app.coverage_workers as cw

    cw._radius_grid_data = np.zeros((10, 10), dtype=np.float32)
    cw._radius_grid_meta = {
        "min_lat": 14.0,
        "max_lat": 15.0,
        "min_lon": 121.0,
        "max_lon": 122.0,
        "n_lat": 10,
        "n_lon": 10,
    }

    with patch.object(cw, "itm_p2p_loss", return_value=_make_mock_itm_result(10.0)):
        _, radius_m = cw._radius_worker(
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
                500.0,
                100_000.0,
            )
        )

    assert radius_m > 90_000.0, "Low loss should yield near-maximum radius"


def test_init_radius_pool_sets_globals():
    import app.coverage_workers as cw

    data = np.ones((5, 5), dtype=np.float32)
    meta = {
        "min_lat": 1.0,
        "max_lat": 2.0,
        "min_lon": 3.0,
        "max_lon": 4.0,
        "n_lat": 5,
        "n_lon": 5,
    }

    cw._init_radius_pool(data, meta)

    np.testing.assert_array_equal(cw._radius_grid_data, data)
    assert cw._radius_grid_meta == meta


def test_init_cov_pool_sets_globals():
    import app.coverage_workers as cw

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

    cw._init_cov_pool(data, meta)

    np.testing.assert_array_equal(cw._cov_grid_data, data)
    assert cw._cov_grid_meta == meta

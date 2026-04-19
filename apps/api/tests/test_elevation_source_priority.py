from unittest.mock import patch

import numpy as np

from app.elevation_grid import _fetch_grid


def test_fetch_grid_glo30_first():
    """When source='glo30', GLO30 should be tried before SRTM1."""
    lats = np.linspace(14.0, 15.0, 3)
    lons = np.linspace(120.0, 121.0, 3)

    with (
        patch("app.elevation_grid.fetch_glo30_grid") as mock_glo30,
        patch("app.elevation_grid.fetch_srtm1_grid") as mock_srtm1,
        patch("app.elevation_grid.fetch_local_hgt") as mock_local,
        patch("app.elevation_grid.fetch_api_batch") as mock_api,
    ):
        mock_glo30.return_value = np.ones((3, 3), dtype=np.float32)
        mock_srtm1.return_value = np.zeros((3, 3), dtype=np.float32)
        mock_local.return_value = []
        mock_api.return_value = [float("nan")] * 9

        result = _fetch_grid(14.0, 120.0, 15.0, 121.0, lats, lons, "glo30")

        mock_glo30.assert_called_once()
        mock_srtm1.assert_not_called()
        assert np.count_nonzero(result) > 0


def test_fetch_grid_fallback_to_srtm1():
    """When source='glo30' and GLO30 returns all-nan, should fall back to SRTM1."""
    lats = np.linspace(14.0, 15.0, 3)
    lons = np.linspace(120.0, 121.0, 3)

    with (
        patch("app.elevation_grid.fetch_glo30_grid") as mock_glo30,
        patch("app.elevation_grid.fetch_srtm1_grid") as mock_srtm1,
        patch("app.elevation_grid.fetch_local_hgt") as mock_local,
        patch("app.elevation_grid.fetch_api_batch") as mock_api,
    ):
        mock_glo30.return_value = np.full((3, 3), np.nan, dtype=np.float32)
        mock_srtm1.return_value = np.ones((3, 3), dtype=np.float32) * 2.0
        mock_local.return_value = []
        mock_api.return_value = [float("nan")] * 9

        result = _fetch_grid(14.0, 120.0, 15.0, 121.0, lats, lons, "glo30")

        mock_glo30.assert_called_once()
        mock_srtm1.assert_called_once()
        assert np.allclose(result, 2.0)


def test_fetch_grid_glo30_zero_elevation_valid():
    """When GLO30 returns all zeros (sea level), it should be accepted as valid data."""
    lats = np.linspace(14.0, 15.0, 3)
    lons = np.linspace(120.0, 121.0, 3)

    with (
        patch("app.elevation_grid.fetch_glo30_grid") as mock_glo30,
        patch("app.elevation_grid.fetch_srtm1_grid") as mock_srtm1,
        patch("app.elevation_grid.fetch_local_hgt") as mock_local,
        patch("app.elevation_grid.fetch_api_batch") as mock_api,
    ):
        mock_glo30.return_value = np.zeros((3, 3), dtype=np.float32)
        mock_srtm1.return_value = np.ones((3, 3), dtype=np.float32)
        mock_local.return_value = []
        mock_api.return_value = [float("nan")] * 9

        result = _fetch_grid(14.0, 120.0, 15.0, 121.0, lats, lons, "glo30")

        mock_glo30.assert_called_once()
        mock_srtm1.assert_not_called()
        assert np.allclose(result, 0.0)


def test_fetch_grid_srtm1_no_glo30_fallback():
    """When source='srtm1', should NOT fall back to GLO30."""
    lats = np.linspace(14.0, 15.0, 3)
    lons = np.linspace(120.0, 121.0, 3)

    with (
        patch("app.elevation_grid.fetch_glo30_grid") as mock_glo30,
        patch("app.elevation_grid.fetch_srtm1_grid") as mock_srtm1,
        patch("app.elevation_grid.fetch_local_hgt") as mock_local,
        patch("app.elevation_grid.fetch_api_batch") as mock_api,
    ):
        mock_srtm1.return_value = np.ones((3, 3), dtype=np.float32)
        mock_local.return_value = []
        mock_api.return_value = [float("nan")] * 9

        result = _fetch_grid(14.0, 120.0, 15.0, 121.0, lats, lons, "srtm1")

        mock_glo30.assert_not_called()
        mock_srtm1.assert_called_once()
        assert np.count_nonzero(result) > 0


def test_fetch_grid_api_only():
    """When source='api', should only call API."""
    lats = np.linspace(14.0, 15.0, 3)
    lons = np.linspace(120.0, 121.0, 3)

    with (
        patch("app.elevation_grid.fetch_glo30_grid") as mock_glo30,
        patch("app.elevation_grid.fetch_srtm1_grid") as mock_srtm1,
        patch("app.elevation_grid.fetch_local_hgt") as mock_local,
        patch("app.elevation_grid.fetch_api_batch") as mock_api,
    ):
        mock_api.return_value = [10.0] * 9

        result = _fetch_grid(14.0, 120.0, 15.0, 121.0, lats, lons, "api")

        mock_glo30.assert_not_called()
        mock_srtm1.assert_not_called()
        mock_local.assert_not_called()
        mock_api.assert_called_once()
        assert np.allclose(result, 10.0)


def test_fetch_grid_srtm1_falls_back_to_api():
    """When source='srtm1' and SRTM1 returns None, should fall back to API."""
    lats = np.linspace(14.0, 15.0, 3)
    lons = np.linspace(120.0, 121.0, 3)

    with (
        patch("app.elevation_grid.fetch_glo30_grid") as mock_glo30,
        patch("app.elevation_grid.fetch_srtm1_grid") as mock_srtm1,
        patch("app.elevation_grid.fetch_local_hgt") as mock_local,
        patch("app.elevation_grid.fetch_api_batch") as mock_api,
    ):
        mock_srtm1.return_value = None
        mock_local.return_value = [float("nan")] * 9
        mock_api.return_value = [5.0] * 9

        result = _fetch_grid(14.0, 120.0, 15.0, 121.0, lats, lons, "srtm1")

        mock_glo30.assert_not_called()
        mock_srtm1.assert_called_once()
        mock_api.assert_called_once()
        assert np.allclose(result, 5.0)

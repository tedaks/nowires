import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_haversine_same_point():
    from app.terrain import haversine_m

    assert haversine_m(14.5, 121.0, 14.5, 121.0) == 0.0


def test_haversine_known_distance():
    from app.terrain import haversine_m

    dist = haversine_m(14.5, 121.0, 14.6, 121.1)
    assert 10000 < dist < 20000, f"Expected ~15km, got {dist}m"


def test_haversine_antipodal():
    from app.terrain import haversine_m

    dist = haversine_m(0, 0, 0, 180)
    assert dist > 19000000


def test_profile_returns_distances_and_elevations():
    from app.terrain import profile

    with patch("app.terrain._get_hgt") as mock_hgt:
        mock_collection = MagicMock()
        mock_collection.get_altitude.return_value = 50.0
        mock_hgt.return_value = mock_collection
        pts = profile(14.5, 121.0, 14.6, 121.1, step_m=1000.0)
        assert len(pts) >= 2
        assert all(d >= 0 for d, _ in pts)
        assert all(isinstance(e, float) for _, e in pts)


def test_profile_handles_zero_elevation():
    from app.terrain import profile

    with patch("app.terrain._get_hgt") as mock_hgt:
        mock_collection = MagicMock()
        mock_collection.get_altitude.return_value = 0.0
        mock_hgt.return_value = mock_collection
        pts = profile(1.0, 104.0, 1.1, 104.1, step_m=1000.0)
        assert len(pts) >= 2


def test_profile_short_distance():
    from app.terrain import profile

    with patch("app.terrain._get_hgt") as mock_hgt:
        mock_collection = MagicMock()
        mock_collection.get_altitude.return_value = 100.0
        mock_hgt.return_value = mock_collection
        pts = profile(14.5, 121.0, 14.5001, 121.0001, step_m=1000.0)
        assert len(pts) >= 2


def test_get_elevation_returns_hgt_value():
    from app.terrain import get_elevation

    with patch("app.terrain._get_hgt") as mock_hgt:
        mock_collection = MagicMock()
        mock_collection.get_altitude.return_value = 123.5
        mock_hgt.return_value = mock_collection
        result = get_elevation(14.5, 121.0)
        assert result == 123.5


def test_get_elevation_falls_back_to_api():
    from app.terrain import get_elevation

    with patch("app.terrain._get_hgt", return_value=None):
        with patch("app.terrain._batch_api_elevations", return_value=[45.0]):
            result = get_elevation(14.5, 121.0)
            assert result == 45.0


def test_batch_api_elevations_interpolates_nans():
    from app.terrain import _batch_api_elevations

    coords = [(14.0, 121.0), (14.0, 121.1), (14.0, 121.2)]
    with patch("app.terrain._API_URL", "http://invalid"):
        with patch("app.terrain.urllib.request.urlopen") as mock_urlopen:
            import json

            response_data = json.dumps(
                {"results": [{"elevation": 10.0}, {"elevation": None}, {"elevation": 20.0}]}
            ).encode()
            mock_resp = MagicMock()
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_resp.read.return_value = response_data
            mock_urlopen.return_value = mock_resp

            result = _batch_api_elevations(coords)
            assert len(result) == 3
            assert result[0] == 10.0
            assert result[2] == 20.0

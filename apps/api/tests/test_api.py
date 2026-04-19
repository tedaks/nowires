import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


P2P_PAYLOAD = {
    "tx": {"lat": 14.5, "lon": 121.0, "h_m": 30},
    "rx": {"lat": 14.6, "lon": 121.1, "h_m": 10},
    "freq_mhz": 450,
    "polarization": 0,
    "climate": 1,
    "time_pct": 50,
    "location_pct": 50,
    "situation_pct": 50,
    "k_factor": 1.3333,
    "tx_power_dbm": 43,
    "tx_gain_dbi": 8,
    "rx_gain_dbi": 2,
    "cable_loss_db": 2,
    "rx_sensitivity_dbm": -100,
}


def _mock_p2p_result(**overrides):
    flags = overrides.pop("flags", None)
    result = {
        "distance_m": 15475.2,
        "profile": [],
        "loss_db": 120.5,
        "mode": 1,
        "mode_name": "Single Horizon Diffraction",
        "warnings": 0,
        "link_budget": {
            "tx_power_dbm": 43.0,
            "tx_gain_dbi": 8.0,
            "rx_gain_dbi": 2.0,
            "cable_loss_db": 2.0,
            "eirp_dbm": 49.0,
            "fspl_db": 100.0,
            "itm_loss_db": 120.5,
            "excess_loss_db": 20.5,
            "prx_dbm": -69.5,
            "rx_sensitivity_dbm": -100.0,
            "margin_db": 30.5,
        },
        "horizons": [],
        "flags": {
            "los_blocked": False,
            "fresnel_f1_violated": False,
            "fresnel_60_violated": False,
        },
        "k_factor": 1.333,
    }
    if flags is not None:
        result["flags"] = flags
    result.update(overrides)
    return result


def test_p2p_endpoint_success(client):
    with patch("app.main.analyze_p2p", return_value=_mock_p2p_result()) as mock:
        resp = client.post("/api/p2p", json=P2P_PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()
        assert "distance_m" in data
        assert "loss_db" in data
        assert "mode" in data
        assert "link_budget" in data
        assert "flags" in data
        mock.assert_called_once()


def test_p2p_endpoint_validates_coordinates(client):
    bad_payload = {
        "tx": {"lat": 91.0, "lon": 121.0, "h_m": 30},
        "rx": {"lat": 14.6, "lon": 121.1, "h_m": 10},
    }
    resp = client.post("/api/p2p", json=bad_payload)
    assert resp.status_code == 422


def test_p2p_endpoint_validates_freq(client):
    bad_payload = {**P2P_PAYLOAD, "freq_mhz": -1}
    resp = client.post("/api/p2p", json=bad_payload)
    assert resp.status_code == 422


def test_p2p_endpoint_validates_k_factor(client):
    bad_payload = {**P2P_PAYLOAD, "k_factor": 0}
    resp = client.post("/api/p2p", json=bad_payload)
    assert resp.status_code == 422


def test_p2p_endpoint_missing_tx(client):
    bad_payload = {
        "rx": {"lat": 14.6, "lon": 121.1, "h_m": 10},
    }
    resp = client.post("/api/p2p", json=bad_payload)
    assert resp.status_code == 422


def test_p2p_returns_flags(client):
    with patch(
        "app.main.analyze_p2p",
        return_value=_mock_p2p_result(
            flags={"los_blocked": True, "fresnel_f1_violated": True, "fresnel_60_violated": False}
        ),
    ):
        resp = client.post("/api/p2p", json=P2P_PAYLOAD)
        assert resp.status_code == 200
        data = resp.json()
        assert data["flags"]["los_blocked"] is True
        assert data["flags"]["fresnel_f1_violated"] is True


def test_coverage_radius_endpoint_success(client):
    mock_result = {
        "max_radius_km": 45.0,
        "min_radius_km": 10.0,
        "avg_radius_km": 25.0,
        "per_bearing": [(0.0, 25.0)],
    }
    with patch("app.main.compute_coverage_radius", return_value=mock_result) as mock:
        payload = {
            "tx": {"lat": 14.5, "lon": 121.0, "h_m": 30},
            "rx_h_m": 10,
            "freq_mhz": 450,
        }
        resp = client.post("/api/coverage-radius", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "avg_radius_km" in data
        assert "min_radius_km" in data
        assert "max_radius_km" in data
        mock.assert_called_once()


def test_coverage_endpoint_success(client):
    mock_result = {
        "png_base64": "iVBORw0KGgo=",
        "bounds": [[14.0, 121.0], [15.0, 122.0]],
        "legend": [],
        "eirp_dbm": 49.0,
        "rx_sensitivity_dbm": -100.0,
        "stats": {"pixels_total": 36864, "pixels_valid": 30000},
        "from_cache": False,
    }
    with patch("app.main.compute_coverage", return_value=mock_result) as mock:
        payload = {
            "tx": {"lat": 14.5, "lon": 121.0, "h_m": 30},
            "rx_h_m": 10,
            "freq_mhz": 450,
        }
        resp = client.post("/api/coverage", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "png_base64" in data
        assert "bounds" in data
        assert "legend" in data
        mock.assert_called_once()


def test_coverage_endpoint_validates_grid_size(client):
    mock_result = {
        "png_base64": "iVBORw0KGgo=",
        "bounds": [[14.0, 121.0], [15.0, 122.0]],
        "legend": [],
        "eirp_dbm": 49.0,
        "rx_sensitivity_dbm": -100.0,
        "stats": {},
        "from_cache": False,
    }
    with patch("app.main.compute_coverage", return_value=mock_result):
        payload = {
            "tx": {"lat": 14.5, "lon": 121.0, "h_m": 30},
            "rx_h_m": 10,
            "freq_mhz": 450,
            "grid_size": 5,
        }
        resp = client.post("/api/coverage", json=payload)
        assert resp.status_code == 422


def test_coverage_endpoint_error_returns_500(client):
    with patch("app.main.compute_coverage", side_effect=RuntimeError("ITM failed")):
        payload = {
            "tx": {"lat": 14.5, "lon": 121.0, "h_m": 30},
            "rx_h_m": 10,
            "freq_mhz": 450,
        }
        resp = client.post("/api/coverage", json=payload)
        assert resp.status_code == 500


def test_coverage_radius_endpoint_validates_radius(client):
    payload = {
        "tx": {"lat": 14.5, "lon": 121.0, "h_m": 30},
        "rx_h_m": 10,
        "freq_mhz": 450,
        "radius_km": 0,
    }
    resp = client.post("/api/coverage-radius", json=payload)
    assert resp.status_code == 422

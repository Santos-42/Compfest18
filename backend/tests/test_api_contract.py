import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.routes import AddressInput, SimulationRequest
from core.config import settings
from main import app
from services import geocoding_service


def test_normal_mode_requires_transaction_fields():
    with pytest.raises(ValidationError):
        SimulationRequest(
            demo_mode=False,
            addresses=[AddressInput(address="Alamat Jakarta")],
        )


def test_mock_geocoding_is_deterministic_and_not_origin():
    first = geocoding_service._fallback_coordinates("Alamat A Jakarta")
    second = geocoding_service._fallback_coordinates("Alamat A Jakarta")
    assert first == second
    assert (first["lat"], first["lng"]) != (settings.ORIGIN_LAT, settings.ORIGIN_LNG)
    assert first["source"] == "mock"
    assert first["confidence"] == 0.0


def test_real_geocoding_does_not_silently_fallback(monkeypatch):
    monkeypatch.setattr(settings, "USE_MOCK_MODE", False)
    monkeypatch.setattr(settings, "OPENCAGE_API_KEY", "")
    monkeypatch.setattr(geocoding_service, "_geocode_photon", lambda _address: None)
    with pytest.raises(RuntimeError, match="tidak dapat diverifikasi"):
        geocoding_service.geocode("Alamat Tidak Ditemukan", allow_mock=False)


def test_demo_request_returns_closed_route_and_is_reproducible(monkeypatch):
    monkeypatch.setattr(settings, "USE_MOCK_MODE", True)
    monkeypatch.setattr(settings, "ENABLE_FALLBACK", True)
    payload = {
        "demo_mode": True,
        "simulation_seed": 42,
        "addresses": [{"address": "Alamat A Jakarta"}, {"address": "Alamat B Jakarta"}],
        "traffic_condition": "normal",
        "optimization": "distance",
    }
    with TestClient(app) as client:
        first = client.post("/api/run-simulation", json=payload)
        second = client.post("/api/run-simulation", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    first_data = first.json()
    second_data = second.json()
    assert first_data["route"]["closed"] is True
    assert first_data["route"]["order"][0] == 0
    assert first_data["route"]["order"][-1] == 0
    assert first_data["return_leg"] is not None
    assert first_data["fraud_alerts"] == second_data["fraud_alerts"]

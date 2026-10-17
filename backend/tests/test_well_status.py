
from fastapi.testclient import TestClient

from app.main import app, calculate_production_status

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_well_status_returns_evidence():
    response = client.get("/api/wells/WELL-0001/status")

    assert response.status_code == 200

    data = response.json()
    assert data["asset_id"] == "WELL-0001"
    assert data["well_type"] == "T200"
    assert data["threshold_c"] == 15.0
    assert data["temperature_difference_c"] == 3.2
    assert data["computed_status"] == "not_producing"
    assert data["evidence"][0]["inspection_id"] == "INS-0001-0203"


def test_unknown_well_returns_404():
    response = client.get("/api/wells/WELL-999999/status")

    assert response.status_code == 404


def test_invalid_asset_id_returns_400():
    response = client.get("/api/wells/../secret/status")

    assert response.status_code in (400, 404, 422)


def test_production_status_below_threshold():
    # 14.9°C difference: not_producing
    result = calculate_production_status(
        wellhead_temp_c=34.9,
        ambient_temp_c=20.0,
        threshold_c=15.0,
    )
    assert result["temperature_difference_c"] == 14.9
    assert result["threshold_c"] == 15.0
    assert result["computed_status"] == "not_producing"


def test_production_status_at_threshold():
    # 15.0°C difference: producing
    result = calculate_production_status(
        wellhead_temp_c=35.0,
        ambient_temp_c=20.0,
        threshold_c=15.0,
    )
    assert result["temperature_difference_c"] == 15.0
    assert result["threshold_c"] == 15.0
    assert result["computed_status"] == "producing"


def test_production_status_above_threshold():
    # 15.1°C difference: producing
    result = calculate_production_status(
        wellhead_temp_c=35.1,
        ambient_temp_c=20.0,
        threshold_c=15.0,
    )
    assert result["temperature_difference_c"] == 15.1
    assert result["threshold_c"] == 15.0
    assert result["computed_status"] == "producing"


def test_production_status_raw_difference_14_999_is_not_producing():
    # A raw difference of 14.999°C is not_producing when threshold is 15.0°C
    result = calculate_production_status(
        wellhead_temp_c=14.999,
        ambient_temp_c=0.0,
        threshold_c=15.0,
    )
    assert result["computed_status"] == "not_producing"
    assert result["temperature_difference_c"] == 15.0
    assert result["threshold_c"] == 15.0

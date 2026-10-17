
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import (
    WELL_TYPE_THRESHOLDS,
    app,
    calculate_production_status,
    get_well_type_threshold,
)

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


def _setup_test_asset(
    tmp_path,
    asset_id="WELL-0001",
    metadata_content='{"asset_id": "WELL-0001", "name": "Test Well", "well_type": "T200"}',
    inspections_lines=None,
):
    asset_dir = tmp_path / "sample-data" / "assets" / asset_id
    asset_dir.mkdir(parents=True, exist_ok=True)
    if metadata_content is not None:
        (asset_dir / "metadata.json").write_text(metadata_content, encoding="utf-8")
    if inspections_lines is not None:
        (asset_dir / "inspections.jsonl").write_text(
            "\n".join(inspections_lines) + "\n", encoding="utf-8"
        )
    return asset_dir


def test_malformed_metadata_json_returns_500(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    _setup_test_asset(tmp_path, metadata_content="{invalid json content")

    response = client.get("/api/wells/WELL-0001/status")

    assert response.status_code == 500
    assert response.json()["detail"] == "Invalid JSON in dataset"


def test_non_dict_metadata_json_returns_500(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    _setup_test_asset(tmp_path, metadata_content='["WELL-0001"]')

    response = client.get("/api/wells/WELL-0001/status")

    assert response.status_code == 500
    assert response.json()["detail"] == "Invalid metadata format"


def test_metadata_asset_id_mismatch_returns_500(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    _setup_test_asset(
        tmp_path,
        metadata_content='{"asset_id": "WELL-OTHER", "well_type": "T200"}',
    )

    response = client.get("/api/wells/WELL-0001/status")

    assert response.status_code == 500
    assert response.json()["detail"] == "Asset ID mismatch"


def test_missing_inspections_file_returns_404(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    _setup_test_asset(tmp_path, inspections_lines=None)

    response = client.get("/api/wells/WELL-0001/status")

    assert response.status_code == 404
    assert response.json()["detail"] == "No valid inspection readings found for this well"


def test_malformed_jsonl_lines_skipped_safely(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    lines = [
        "{malformed json line",
        '"a standalone string line"',
        "[1, 2, 3]",
        "   ",
        (
            '{"inspection_id": "INS-VALID-01", "asset_id": "WELL-0001", '
            '"inspected_at": "2026-01-01T00:00:00Z", "ambient_temp_c": 20.0, '
            '"wellhead_temp_c": 36.0}'
        ),
    ]
    _setup_test_asset(tmp_path, inspections_lines=lines)

    response = client.get("/api/wells/WELL-0001/status")

    assert response.status_code == 200
    data = response.json()
    assert data["computed_status"] == "producing"
    assert data["evidence"][0]["inspection_id"] == "INS-VALID-01"


def test_invalid_temperature_records_skipped(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    lines = [
        # missing ambient
        '{"inspection_id": "INS-INV-01", "asset_id": "WELL-0001", "inspected_at": "2026-01-01T00:00:00Z", "wellhead_temp_c": 36.0}',
        # null ambient
        '{"inspection_id": "INS-INV-02", "asset_id": "WELL-0001", "inspected_at": "2026-01-02T00:00:00Z", "ambient_temp_c": null, "wellhead_temp_c": 36.0}',
        # string temperature
        '{"inspection_id": "INS-INV-03", "asset_id": "WELL-0001", "inspected_at": "2026-01-03T00:00:00Z", "ambient_temp_c": "hot", "wellhead_temp_c": 36.0}',
        # NaN temperature
        '{"inspection_id": "INS-INV-04", "asset_id": "WELL-0001", "inspected_at": "2026-01-04T00:00:00Z", "ambient_temp_c": "NaN", "wellhead_temp_c": 36.0}',
        # Infinity temperature
        '{"inspection_id": "INS-INV-05", "asset_id": "WELL-0001", "inspected_at": "2026-01-05T00:00:00Z", "ambient_temp_c": "Infinity", "wellhead_temp_c": 36.0}',
        # boolean temperature
        '{"inspection_id": "INS-INV-06", "asset_id": "WELL-0001", "inspected_at": "2026-01-06T00:00:00Z", "ambient_temp_c": true, "wellhead_temp_c": 36.0}',
        # valid record
        (
            '{"inspection_id": "INS-VALID-02", "asset_id": "WELL-0001", '
            '"inspected_at": "2026-01-07T00:00:00Z", "ambient_temp_c": 20.0, '
            '"wellhead_temp_c": 30.0}'
        ),
    ]
    _setup_test_asset(tmp_path, inspections_lines=lines)

    response = client.get("/api/wells/WELL-0001/status")

    assert response.status_code == 200
    data = response.json()
    assert data["computed_status"] == "not_producing"
    assert data["evidence"][0]["inspection_id"] == "INS-VALID-02"


def test_invalid_timestamp_and_inspection_id_skipped(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    lines = [
        # empty timestamp
        '{"inspection_id": "INS-INV-10", "asset_id": "WELL-0001", "inspected_at": "", "ambient_temp_c": 20.0, "wellhead_temp_c": 36.0}',
        # whitespace timestamp
        '{"inspection_id": "INS-INV-11", "asset_id": "WELL-0001", "inspected_at": "   ", "ambient_temp_c": 20.0, "wellhead_temp_c": 36.0}',
        # null timestamp
        '{"inspection_id": "INS-INV-12", "asset_id": "WELL-0001", "inspected_at": null, "ambient_temp_c": 20.0, "wellhead_temp_c": 36.0}',
        # non-string timestamp
        '{"inspection_id": "INS-INV-13", "asset_id": "WELL-0001", "inspected_at": 12345, "ambient_temp_c": 20.0, "wellhead_temp_c": 36.0}',
        # empty inspection_id
        '{"inspection_id": "", "asset_id": "WELL-0001", "inspected_at": "2026-01-01T00:00:00Z", "ambient_temp_c": 20.0, "wellhead_temp_c": 36.0}',
        # whitespace inspection_id
        '{"inspection_id": "   ", "asset_id": "WELL-0001", "inspected_at": "2026-01-01T00:00:00Z", "ambient_temp_c": 20.0, "wellhead_temp_c": 36.0}',
        # null inspection_id
        '{"inspection_id": null, "asset_id": "WELL-0001", "inspected_at": "2026-01-01T00:00:00Z", "ambient_temp_c": 20.0, "wellhead_temp_c": 36.0}',
        # non-string inspection_id
        '{"inspection_id": 999, "asset_id": "WELL-0001", "inspected_at": "2026-01-01T00:00:00Z", "ambient_temp_c": 20.0, "wellhead_temp_c": 36.0}',
        # valid record
        (
            '{"inspection_id": "INS-VALID-03", "asset_id": "WELL-0001", '
            '"inspected_at": "2026-01-02T00:00:00Z", "ambient_temp_c": 20.0, '
            '"wellhead_temp_c": 37.0}'
        ),
    ]
    _setup_test_asset(tmp_path, inspections_lines=lines)

    response = client.get("/api/wells/WELL-0001/status")

    assert response.status_code == 200
    data = response.json()
    assert data["computed_status"] == "producing"
    assert data["evidence"][0]["inspection_id"] == "INS-VALID-03"


def test_only_invalid_records_returns_404(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    lines = [
        '{"inspection_id": "", "asset_id": "WELL-0001", "inspected_at": "2026-01-01T00:00:00Z", "ambient_temp_c": 20.0, "wellhead_temp_c": 36.0}',
        '{"inspection_id": "INS-INV-99", "asset_id": "WELL-0001", "inspected_at": "2026-01-01T00:00:00Z", "ambient_temp_c": "NaN", "wellhead_temp_c": 36.0}',
    ]
    _setup_test_asset(tmp_path, inspections_lines=lines)

    response = client.get("/api/wells/WELL-0001/status")

    assert response.status_code == 404
    assert response.json()["detail"] == "No valid inspection readings found for this well"


def test_t350_production_status_below_threshold():
    # 19.9°C difference: not_producing for T350 (threshold 20.0°C)
    result = calculate_production_status(
        wellhead_temp_c=39.9,
        ambient_temp_c=20.0,
        threshold_c=20.0,
    )
    assert result["temperature_difference_c"] == 19.9
    assert result["threshold_c"] == 20.0
    assert result["computed_status"] == "not_producing"


def test_t350_production_status_raw_difference_19_999_is_not_producing():
    # Unrounded 19.999°C difference: not_producing for T350 (threshold 20.0°C)
    result = calculate_production_status(
        wellhead_temp_c=19.999,
        ambient_temp_c=0.0,
        threshold_c=20.0,
    )
    assert result["computed_status"] == "not_producing"
    assert result["temperature_difference_c"] == 20.0
    assert result["threshold_c"] == 20.0


def test_t350_production_status_at_threshold():
    # 20.0°C difference: producing for T350 (threshold 20.0°C)
    result = calculate_production_status(
        wellhead_temp_c=40.0,
        ambient_temp_c=20.0,
        threshold_c=20.0,
    )
    assert result["temperature_difference_c"] == 20.0
    assert result["threshold_c"] == 20.0
    assert result["computed_status"] == "producing"


def test_t350_production_status_above_threshold():
    # 20.1°C difference: producing for T350 (threshold 20.0°C)
    result = calculate_production_status(
        wellhead_temp_c=40.1,
        ambient_temp_c=20.0,
        threshold_c=20.0,
    )
    assert result["temperature_difference_c"] == 20.1
    assert result["threshold_c"] == 20.0
    assert result["computed_status"] == "producing"


def test_t350_well_status_real_dataset():
    response = client.get("/api/wells/WELL-0003/status")

    assert response.status_code == 200
    data = response.json()
    assert data["asset_id"] == "WELL-0003"
    assert data["well_type"] == "T350"
    assert data["threshold_c"] == 20.0
    assert data["temperature_difference_c"] == 37.4
    assert data["computed_status"] == "producing"
    assert data["evidence"][0]["inspection_id"] == "INS-0003-0203"


def test_t350_not_producing_at_t200_threshold(monkeypatch, tmp_path):
    # A difference of 16.0°C produces under T200 (15.0°C), but MUST NOT produce under T350 (20.0°C)
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    lines = [
        (
            '{"inspection_id": "INS-T350-01", "asset_id": "WELL-0003", '
            '"inspected_at": "2026-01-01T00:00:00Z", "ambient_temp_c": 20.0, '
            '"wellhead_temp_c": 36.0}'
        ),
    ]
    _setup_test_asset(
        tmp_path,
        asset_id="WELL-0003",
        metadata_content='{"asset_id": "WELL-0003", "name": "Deep Well", "well_type": "T350"}',
        inspections_lines=lines,
    )

    response = client.get("/api/wells/WELL-0003/status")

    assert response.status_code == 200
    data = response.json()
    assert data["well_type"] == "T350"
    assert data["threshold_c"] == 20.0
    assert data["temperature_difference_c"] == 16.0
    assert data["computed_status"] == "not_producing"


def test_unsupported_well_type_returns_422(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    _setup_test_asset(
        tmp_path,
        metadata_content='{"asset_id": "WELL-0001", "well_type": "T500"}',
        inspections_lines=[],
    )

    response = client.get("/api/wells/WELL-0001/status")

    assert response.status_code == 422
    assert "T500" in response.json()["detail"]


def test_missing_well_type_returns_422(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    _setup_test_asset(
        tmp_path,
        metadata_content='{"asset_id": "WELL-0001", "name": "No Type Well"}',
        inspections_lines=[],
    )

    response = client.get("/api/wells/WELL-0001/status")

    assert response.status_code == 422
    assert "None" in response.json()["detail"]


def test_invalid_well_type_type_returns_422(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    _setup_test_asset(
        tmp_path,
        metadata_content='{"asset_id": "WELL-0001", "well_type": 999}',
        inspections_lines=[],
    )

    response = client.get("/api/wells/WELL-0001/status")

    assert response.status_code == 422
    assert "999" in response.json()["detail"]


def test_get_well_type_threshold_helper():
    assert get_well_type_threshold("T200") == 15.0
    assert get_well_type_threshold("T350") == 20.0
    assert "T200" in WELL_TYPE_THRESHOLDS
    assert "T350" in WELL_TYPE_THRESHOLDS

    with pytest.raises(HTTPException) as exc_info:
        get_well_type_threshold("T500")
    assert exc_info.value.status_code == 422
    assert "T500" in exc_info.value.detail

    with pytest.raises(HTTPException) as exc_info:
        get_well_type_threshold(None)
    assert exc_info.value.status_code == 422
    assert "None" in exc_info.value.detail

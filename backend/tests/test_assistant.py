import json
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _setup_test_asset(
    tmp_path,
    asset_id="WELL-0001",
    well_type="T200",
    name="Test Well",
    inspections=None,
    context_notes=None,
    maintenance_records=None,
    regulatory_events=None,
):
    asset_dir = tmp_path / "sample-data" / "assets" / asset_id
    asset_dir.mkdir(parents=True, exist_ok=True)

    metadata = {"asset_id": asset_id, "name": name, "well_type": well_type}
    (asset_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    if inspections is not None:
        lines = [json.dumps(i) for i in inspections]
        (asset_dir / "inspections.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        (asset_dir / "inspections.jsonl").write_text("", encoding="utf-8")

    if context_notes is not None:
        lines = [json.dumps(c) for c in context_notes]
        (asset_dir / "context.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        (asset_dir / "context.jsonl").write_text("", encoding="utf-8")

    if maintenance_records is not None:
        lines = [json.dumps(m) for m in maintenance_records]
        (asset_dir / "maintenance.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        (asset_dir / "maintenance.jsonl").write_text("", encoding="utf-8")

    if regulatory_events is not None:
        lines = [json.dumps(r) for r in regulatory_events]
        (asset_dir / "regulatory-events.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        (asset_dir / "regulatory-events.jsonl").write_text("", encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Supported Questions: Production Status
# ---------------------------------------------------------------------------


def test_assistant_production_status_real_dataset():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "Is WELL-0001 producing?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert data["question_type"] == "production_status"
    assert data["asset_id"] == "WELL-0001"
    assert "not producing" in data["answer"].lower()
    assert "T200" in data["answer"]
    assert len(data["evidence"]) >= 1
    assert data["evidence"][0]["inspection_id"] == "INS-0001-0203"
    assert "threshold" in data["rule_or_calculation"].lower()


def test_assistant_production_status_explicit_asset_id():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "What is the current status of the well?", "asset_id": "WELL-0001"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert data["question_type"] == "production_status"
    assert data["asset_id"] == "WELL-0001"
    assert len(data["evidence"]) >= 1


def test_assistant_production_status_t350_real_dataset():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "Is WELL-0003 producing right now?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert data["question_type"] == "production_status"
    assert data["asset_id"] == "WELL-0003"
    assert "T350" in data["answer"]
    assert "20.0" in data["rule_or_calculation"]


# ---------------------------------------------------------------------------
# 2. Supported Questions: Estimated Downtime
# ---------------------------------------------------------------------------


def test_assistant_downtime_with_year():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "What was the estimated downtime for WELL-0001 in 2025?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert data["question_type"] == "downtime"
    assert data["asset_id"] == "WELL-0001"
    assert "21 days" in data["answer"]
    assert len(data["evidence"]) == 3


def test_assistant_downtime_total():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "How much cumulative downtime did WELL-0001 have?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert data["question_type"] == "downtime"
    assert data["asset_id"] == "WELL-0001"
    assert "70 days" in data["answer"]


# ---------------------------------------------------------------------------
# 3. Supported Questions: Consecutive Downtime
# ---------------------------------------------------------------------------


def test_assistant_consecutive_downtime_below_threshold():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "Has consecutive downtime for WELL-0001 exceeded the reporting threshold?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert data["question_type"] == "consecutive_downtime"
    assert data["asset_id"] == "WELL-0001"
    assert "has not exceeded" in data["answer"].lower()
    assert "not required" in data["answer"].lower()


def test_assistant_consecutive_downtime_exceeded(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    # 3 consecutive non-producing weekly inspections -> 21 days > 14 days
    inspections = [
        {"inspection_id": "INS-01", "asset_id": "WELL-0001", "inspected_at": "2026-01-01T08:00:00Z", "ambient_temp_c": 20.0, "wellhead_temp_c": 22.0},
        {"inspection_id": "INS-02", "asset_id": "WELL-0001", "inspected_at": "2026-01-08T08:00:00Z", "ambient_temp_c": 20.0, "wellhead_temp_c": 22.0},
        {"inspection_id": "INS-03", "asset_id": "WELL-0001", "inspected_at": "2026-01-15T08:00:00Z", "ambient_temp_c": 20.0, "wellhead_temp_c": 22.0},
    ]
    _setup_test_asset(tmp_path, inspections=inspections)

    response = client.post(
        "/api/assistant/ask",
        json={"question": "Does consecutive downtime for WELL-0001 require supervisor notification?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert data["question_type"] == "consecutive_downtime"
    assert "has exceeded" in data["answer"].lower()
    assert "supervisor" in data["answer"].lower()


# ---------------------------------------------------------------------------
# 4. Supported Questions: Maintenance Recurrence and RCA
# ---------------------------------------------------------------------------


def test_assistant_maintenance_recurrence_rca_required():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "Does WELL-0001 require a root-cause analysis for recurring maintenance?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert data["question_type"] == "maintenance_recurrence"
    assert data["asset_id"] == "WELL-0001"
    assert "requires a root-cause analysis (rca)" in data["answer"].lower()
    assert "flowline" in data["answer"].lower()
    assert len(data["evidence"]) >= 3


def test_assistant_maintenance_recurrence_not_required(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    # Only 2 corrective events on gearbox
    records = [
        {"maintenance_id": "MNT-01", "asset_id": "WELL-0001", "equipment_kind": "gearbox", "maintenance_type": "corrective", "started_at": "2026-01-01T08:00:00Z"},
        {"maintenance_id": "MNT-02", "asset_id": "WELL-0001", "equipment_kind": "gearbox", "maintenance_type": "corrective", "started_at": "2026-02-01T08:00:00Z"},
    ]
    _setup_test_asset(tmp_path, maintenance_records=records)

    response = client.post(
        "/api/assistant/ask",
        json={"question": "Check maintenance recurrence and RCA for WELL-0001"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert data["question_type"] == "maintenance_recurrence"
    assert "does not require" in data["answer"].lower()


# ---------------------------------------------------------------------------
# 5. Supported Questions: Safety and Regulatory Compliance
# ---------------------------------------------------------------------------


def test_assistant_safety_compliance_real_dataset():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "Are there any high-temperature alarms or reportable spills for WELL-0001?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert data["question_type"] == "safety_compliance"
    assert data["asset_id"] == "WELL-0001"
    assert "high-temperature alarms" in data["answer"].lower()
    assert "reportable spills" in data["answer"].lower()
    assert "reg-0001-002" in data["answer"].lower()


def test_assistant_high_temperature_alarm_triggered(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    # T200 wellhead temp 88.0°C exceeds 85.0°C limit
    inspections = [
        {"inspection_id": "INS-HOT-01", "asset_id": "WELL-0001", "inspected_at": "2026-07-01T12:00:00Z", "ambient_temp_c": 35.0, "wellhead_temp_c": 88.0},
    ]
    _setup_test_asset(tmp_path, inspections=inspections)

    response = client.post(
        "/api/assistant/ask",
        json={"question": "Were there any temperature alarms for WELL-0001?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert data["question_type"] == "safety_compliance"
    assert "88.0" in data["answer"]
    assert "shut in well and inspect stuffing box and rod string within 24 hours" in data["answer"].lower()


# ---------------------------------------------------------------------------
# 6. Missing Asset IDs (Clarification Needed)
# ---------------------------------------------------------------------------


def test_assistant_missing_asset_id_production():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "Is the well producing?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "clarification_needed"
    assert data["question_type"] == "production_status"
    assert data["asset_id"] is None
    assert "please specify the well asset id" in data["answer"].lower()


def test_assistant_missing_asset_id_downtime():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "How much downtime did the well have?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "clarification_needed"
    assert data["question_type"] == "downtime"
    assert "please specify the well asset id" in data["answer"].lower()


def test_assistant_missing_asset_id_maintenance():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "Does the well require a root-cause analysis?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "clarification_needed"
    assert data["question_type"] == "maintenance_recurrence"


def test_assistant_missing_asset_id_safety():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "Were there any reportable spills or high temp alarms?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "clarification_needed"
    assert data["question_type"] == "safety_compliance"


# ---------------------------------------------------------------------------
# 7. Unknown Wells & Invalid Inputs
# ---------------------------------------------------------------------------


def test_assistant_unknown_well_returns_404():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "Is WELL-9999 producing?"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Well not found"


def test_assistant_invalid_asset_id_format_returns_400():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "Is it producing?", "asset_id": "INVALID/NAME"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid asset ID"


def test_assistant_unsupported_well_type_returns_422(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    _setup_test_asset(tmp_path, asset_id="WELL-0099", well_type="T500")

    response = client.post(
        "/api/assistant/ask",
        json={"question": "Is WELL-0099 producing?"},
    )
    assert response.status_code == 422
    assert "No verified production threshold" in response.json()["detail"]


# ---------------------------------------------------------------------------
# 8. Ambiguous Questions
# ---------------------------------------------------------------------------


def test_assistant_ambiguous_generic_well_query():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "Tell me about WELL-0001"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ambiguous"
    assert data["question_type"] == "ambiguous"
    assert "ambiguous" in data["answer"].lower()
    assert "production status" in data["answer"].lower()


def test_assistant_ambiguous_multi_domain_query():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "What is the downtime and maintenance recurrence for WELL-0001?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ambiguous"
    assert data["question_type"] == "ambiguous"


def test_assistant_empty_question():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "   "},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ambiguous"


# ---------------------------------------------------------------------------
# 9. Unsupported Questions
# ---------------------------------------------------------------------------


def test_assistant_unsupported_general_knowledge():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "What is the capital of France?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unsupported"
    assert data["question_type"] == "unsupported"
    assert "outside the operational scope" in data["answer"].lower()


def test_assistant_unsupported_weather():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "What is the weather forecast for tomorrow?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unsupported"


# ---------------------------------------------------------------------------
# 10. Conflicting Evidence & Corrections
# ---------------------------------------------------------------------------


def test_assistant_conflicting_inspection_records_reported(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    # Two contradictory records at the same timestamp
    ts = "2026-05-01T10:00:00Z"
    inspections = [
        {"inspection_id": "INS-PROD", "asset_id": "WELL-0001", "inspected_at": ts, "ambient_temp_c": 20.0, "wellhead_temp_c": 38.0},
        {"inspection_id": "INS-COLD", "asset_id": "WELL-0001", "inspected_at": ts, "ambient_temp_c": 20.0, "wellhead_temp_c": 22.0},
    ]
    _setup_test_asset(tmp_path, inspections=inspections)

    response = client.post(
        "/api/assistant/ask",
        json={"question": "Is WELL-0001 producing?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert data["unresolved_conflicts"] is True
    assert len(data["conflicts"]) >= 1
    assert "conflict" in data["answer"].lower()


def test_assistant_operator_status_disagreement_reported():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "Is WELL-0001 producing?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert len(data["conflicts"]) >= 1
    conf = data["conflicts"][0]
    assert conf["field"] == "recorded_status"
    assert "active" in conf["value"]
    assert "conflict" in data["answer"].lower()


def test_assistant_explicit_correction_note_reported(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    inspections = [
        {"inspection_id": "INS-001", "asset_id": "WELL-0001", "inspected_at": "2026-05-01T10:00:00Z", "ambient_temp_c": 20.0, "wellhead_temp_c": 40.0},
    ]
    notes = [
        {"note_id": "CORR-01", "asset_id": "WELL-0001", "inspection_id": "INS-001", "note_type": "correction", "text": "Sensor calibrated; temp reading was 5C high."},
    ]
    _setup_test_asset(tmp_path, inspections=inspections, context_notes=notes)

    response = client.post(
        "/api/assistant/ask",
        json={"question": "What is the status of WELL-0001?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert "correction note" in data["answer"].lower()
    assert "sensor calibrated" in data["answer"].lower()

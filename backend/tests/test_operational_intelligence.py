import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.operational_intelligence import (
    calculate_well_downtime,
    check_consecutive_downtime,
    check_maintenance_recurrence,
    check_safety_and_compliance,
)

client = TestClient(app)


def _setup_op_asset(
    tmp_path,
    asset_id="WELL-0001",
    metadata_content='{"asset_id": "WELL-0001", "name": "Test Well", "well_type": "T200"}',
    inspections_lines=None,
    maintenance_lines=None,
    context_lines=None,
    regulatory_lines=None,
):
    asset_dir = tmp_path / "sample-data" / "assets" / asset_id
    asset_dir.mkdir(parents=True, exist_ok=True)
    if metadata_content is not None:
        (asset_dir / "metadata.json").write_text(metadata_content, encoding="utf-8")
    if inspections_lines is not None:
        (asset_dir / "inspections.jsonl").write_text(
            "\n".join(inspections_lines) + "\n", encoding="utf-8"
        )
    if maintenance_lines is not None:
        (asset_dir / "maintenance.jsonl").write_text(
            "\n".join(maintenance_lines) + "\n", encoding="utf-8"
        )
    if context_lines is not None:
        (asset_dir / "context.jsonl").write_text(
            "\n".join(context_lines) + "\n", encoding="utf-8"
        )
    if regulatory_lines is not None:
        (asset_dir / "regulatory-events.jsonl").write_text(
            "\n".join(regulatory_lines) + "\n", encoding="utf-8"
        )
    return asset_dir


# ==============================================================================
# 1. Downtime Estimation Tests
# ==============================================================================


def test_downtime_estimation_well_0001_2025():
    # Evaluation Query Q5: WELL-0001 had 3 non-producing inspections in 2025 -> 21 days downtime
    response = client.get("/api/wells/WELL-0001/downtime?year=2025")

    assert response.status_code == 200
    data = response.json()
    assert data["asset_id"] == "WELL-0001"
    assert data["well_type"] == "T200"
    assert data["downtime_days"] == 21
    assert data["non_producing_inspections_count"] == 3
    assert len(data["evidence"]) == 3

    # Check evidence dates
    timestamps = [e["timestamp"] for e in data["evidence"]]
    assert any("2025-07-24" in ts for ts in timestamps)
    assert any("2025-10-16" in ts for ts in timestamps)
    assert any("2025-10-23" in ts for ts in timestamps)


def test_downtime_estimation_date_range_well_0121():
    # Evaluation Query Q6: WELL-0121 in 4-month window (2026-06-16 to 2026-10-16) -> 49 days (7 inspections)
    response = client.get(
        "/api/wells/WELL-0121/downtime?start_date=2026-06-16&end_date=2026-10-16"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["asset_id"] == "WELL-0121"
    assert data["downtime_days"] == 49
    assert data["non_producing_inspections_count"] == 7


def test_downtime_missed_inspections_do_not_add_downtime(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    # 1 non-producing inspection on 2026-01-01, then missed weeks until 2026-01-22 (producing)
    lines = [
        '{"inspection_id": "INS-01", "asset_id": "WELL-0001", "inspected_at": "2026-01-01T10:00:00Z", "ambient_temp_c": 20.0, "wellhead_temp_c": 25.0}',
        '{"inspection_id": "INS-02", "asset_id": "WELL-0001", "inspected_at": "2026-01-22T10:00:00Z", "ambient_temp_c": 20.0, "wellhead_temp_c": 40.0}',
    ]
    _setup_op_asset(tmp_path, inspections_lines=lines)

    result = calculate_well_downtime(asset_id="WELL-0001", dataset_root=tmp_path)
    assert result["downtime_days"] == 7
    assert result["non_producing_inspections_count"] == 1


def test_downtime_all_producing_zero_days(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    lines = [
        '{"inspection_id": "INS-01", "asset_id": "WELL-0001", "inspected_at": "2026-01-01T10:00:00Z", "ambient_temp_c": 20.0, "wellhead_temp_c": 40.0}',
        '{"inspection_id": "INS-02", "asset_id": "WELL-0001", "inspected_at": "2026-01-08T10:00:00Z", "ambient_temp_c": 20.0, "wellhead_temp_c": 42.0}',
    ]
    _setup_op_asset(tmp_path, inspections_lines=lines)

    result = calculate_well_downtime(asset_id="WELL-0001", dataset_root=tmp_path)
    assert result["downtime_days"] == 0
    assert result["non_producing_inspections_count"] == 0


# ==============================================================================
# 2. Long Downtime Tests
# ==============================================================================


def test_consecutive_downtime_well_0001():
    # WELL-0001 max consecutive non-producing inspections is 2 (14 days); does not exceed >14 threshold
    response = client.get("/api/wells/WELL-0001/consecutive-downtime")

    assert response.status_code == 200
    data = response.json()
    assert data["asset_id"] == "WELL-0001"
    assert data["consecutive_days_threshold"] == 14
    assert data["max_consecutive_days"] == 14
    assert data["exceeds_threshold"] is False
    assert data["reporting_required"] is False
    assert len(data["episodes"]) == 0


def test_consecutive_downtime_well_0002():
    # WELL-0002 has 6 consecutive non-producing inspections (42 days); exceeds >14 threshold
    response = client.get("/api/wells/WELL-0002/consecutive-downtime")

    assert response.status_code == 200
    data = response.json()
    assert data["asset_id"] == "WELL-0002"
    assert data["exceeds_threshold"] is True
    assert data["reporting_required"] is True
    assert data["max_consecutive_days"] >= 42
    assert len(data["episodes"]) >= 1


def test_consecutive_downtime_missed_inspection_breaks_streak(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    # 2 consecutive non-producing inspections, then 14-day gap (missed inspection), then 1 non-producing inspection
    lines = [
        '{"inspection_id": "INS-01", "asset_id": "WELL-0001", "inspected_at": "2026-01-01T10:00:00Z", "ambient_temp_c": 20.0, "wellhead_temp_c": 25.0}',
        '{"inspection_id": "INS-02", "asset_id": "WELL-0001", "inspected_at": "2026-01-08T10:00:00Z", "ambient_temp_c": 20.0, "wellhead_temp_c": 25.0}',
        # 14 days later (missed scheduled inspection on 2026-01-15)
        '{"inspection_id": "INS-03", "asset_id": "WELL-0001", "inspected_at": "2026-01-22T10:00:00Z", "ambient_temp_c": 20.0, "wellhead_temp_c": 25.0}',
    ]
    _setup_op_asset(tmp_path, inspections_lines=lines)

    result = check_consecutive_downtime(
        asset_id="WELL-0001",
        consecutive_days_threshold=14,
        dataset_root=tmp_path,
    )
    # Longest consecutive streak is 2 inspections (14 days); 14 is not > 14
    assert result["max_consecutive_inspections"] == 2
    assert result["max_consecutive_days"] == 14
    assert result["exceeds_threshold"] is False


def test_consecutive_downtime_three_in_a_row_triggers_threshold(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    # 3 consecutive non-producing inspections (21 days) -> exceeds 14 days
    lines = [
        '{"inspection_id": "INS-01", "asset_id": "WELL-0001", "inspected_at": "2026-01-01T10:00:00Z", "ambient_temp_c": 20.0, "wellhead_temp_c": 25.0}',
        '{"inspection_id": "INS-02", "asset_id": "WELL-0001", "inspected_at": "2026-01-08T10:00:00Z", "ambient_temp_c": 20.0, "wellhead_temp_c": 25.0}',
        '{"inspection_id": "INS-03", "asset_id": "WELL-0001", "inspected_at": "2026-01-15T10:00:00Z", "ambient_temp_c": 20.0, "wellhead_temp_c": 25.0}',
    ]
    _setup_op_asset(tmp_path, inspections_lines=lines)

    result = check_consecutive_downtime(
        asset_id="WELL-0001",
        consecutive_days_threshold=14,
        dataset_root=tmp_path,
    )
    assert result["max_consecutive_inspections"] == 3
    assert result["max_consecutive_days"] == 21
    assert result["exceeds_threshold"] is True
    assert result["reporting_required"] is True
    assert len(result["episodes"]) == 1


# ==============================================================================
# 3. Maintenance Recurrence Tests
# ==============================================================================


def test_maintenance_recurrence_well_0001():
    # WELL-0001 has 5 corrective events on flowline within 12m -> RCA required
    response = client.get("/api/wells/WELL-0001/maintenance-recurrence")

    assert response.status_code == 200
    data = response.json()
    assert data["asset_id"] == "WELL-0001"
    assert data["rca_required"] is True
    assert len(data["recurrent_groups"]) >= 1

    group = [g for g in data["recurrent_groups"] if g["equipment_kind"] == "flowline"][0]
    assert group["event_count"] >= 3
    assert group["rca_required"] is True
    assert len(data["evidence"]) >= 3


def test_maintenance_recurrence_scheduled_maintenance_ignored(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    # 4 scheduled maintenance events on pump_jack do not trigger RCA
    maintenance = [
        '{"maintenance_id": "MNT-01", "asset_id": "WELL-0001", "started_at": "2026-01-01T08:00:00Z", "maintenance_type": "scheduled", "equipment_kind": "pump_jack", "issue": "Scheduled lubrication"}',
        '{"maintenance_id": "MNT-02", "asset_id": "WELL-0001", "started_at": "2026-03-01T08:00:00Z", "maintenance_type": "scheduled", "equipment_kind": "pump_jack", "issue": "Scheduled lubrication"}',
        '{"maintenance_id": "MNT-03", "asset_id": "WELL-0001", "started_at": "2026-06-01T08:00:00Z", "maintenance_type": "scheduled", "equipment_kind": "pump_jack", "issue": "Scheduled lubrication"}',
        '{"maintenance_id": "MNT-04", "asset_id": "WELL-0001", "started_at": "2026-09-01T08:00:00Z", "maintenance_type": "scheduled", "equipment_kind": "pump_jack", "issue": "Scheduled lubrication"}',
    ]
    _setup_op_asset(tmp_path, maintenance_lines=maintenance)

    result = check_maintenance_recurrence(asset_id="WELL-0001", dataset_root=tmp_path)
    assert result["rca_required"] is False
    assert len(result["recurrent_groups"]) == 0


def test_maintenance_recurrence_different_equipment_does_not_trigger(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    # 2 on wellhead, 2 on pump_jack within 12 months -> neither reaches 3 -> False
    maintenance = [
        '{"maintenance_id": "MNT-01", "asset_id": "WELL-0001", "started_at": "2026-01-01T08:00:00Z", "maintenance_type": "corrective", "equipment_kind": "wellhead", "issue": "Valve packing leak"}',
        '{"maintenance_id": "MNT-02", "asset_id": "WELL-0001", "started_at": "2026-03-01T08:00:00Z", "maintenance_type": "corrective", "equipment_kind": "wellhead", "issue": "Valve packing leak"}',
        '{"maintenance_id": "MNT-03", "asset_id": "WELL-0001", "started_at": "2026-05-01T08:00:00Z", "maintenance_type": "corrective", "equipment_kind": "pump_jack", "issue": "Bearing wear"}',
        '{"maintenance_id": "MNT-04", "asset_id": "WELL-0001", "started_at": "2026-07-01T08:00:00Z", "maintenance_type": "corrective", "equipment_kind": "pump_jack", "issue": "Bearing wear"}',
    ]
    _setup_op_asset(tmp_path, maintenance_lines=maintenance)

    result = check_maintenance_recurrence(asset_id="WELL-0001", dataset_root=tmp_path)
    assert result["rca_required"] is False


def test_maintenance_recurrence_outside_12_months_does_not_trigger(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    # 3 corrective events spanning over 2 years (no 3 events within any 365-day window)
    maintenance = [
        '{"maintenance_id": "MNT-01", "asset_id": "WELL-0001", "started_at": "2023-01-01T08:00:00Z", "maintenance_type": "corrective", "equipment_kind": "flowline", "issue": "Leak"}',
        '{"maintenance_id": "MNT-02", "asset_id": "WELL-0001", "started_at": "2024-06-01T08:00:00Z", "maintenance_type": "corrective", "equipment_kind": "flowline", "issue": "Leak"}',
        '{"maintenance_id": "MNT-03", "asset_id": "WELL-0001", "started_at": "2025-12-01T08:00:00Z", "maintenance_type": "corrective", "equipment_kind": "flowline", "issue": "Leak"}',
    ]
    _setup_op_asset(tmp_path, maintenance_lines=maintenance)

    result = check_maintenance_recurrence(asset_id="WELL-0001", dataset_root=tmp_path)
    assert result["rca_required"] is False


# ==============================================================================
# 4. Safety and Regulatory Compliance Tests
# ==============================================================================


def test_safety_and_compliance_well_0001():
    response = client.get("/api/wells/WELL-0001/safety-compliance")

    assert response.status_code == 200
    data = response.json()
    assert data["asset_id"] == "WELL-0001"
    assert data["temperature_alarm_limit_c"] == 85.0
    assert len(data["high_temperature_alarms"]) == 0

    # Reportable spill check: INS-0001-0185 (6.8 bbl) was filed late (41h > 24h) and received NOV
    spills = data["reportable_spills"]
    assert any(s["inspection_id"] == "INS-0001-0185" for s in spills)

    spill_185 = [s for s in spills if s["inspection_id"] == "INS-0001-0185"][0]
    assert spill_185["spill_class"] == "reportable"
    assert spill_185["est_volume_bbl"] == 6.8
    assert spill_185["reporting_required"] is True
    assert spill_185["proof_of_submission"] is True
    assert spill_185["filed_on_time"] is False
    assert spill_185["hours_to_report"] == 41
    assert spill_185["notice_of_violation_issued"] is True
    assert "REG-0001-002" in spill_185["notice_of_violation_ids"]

    # False positive check: INS-0001-0070 was corrected as rainwater in context.jsonl and does not appear
    assert not any(s["inspection_id"] == "INS-0001-0070" for s in spills)


def test_high_temperature_alarm_triggered_t200(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    # T200 wellhead temperature 86.0 °C exceeds 85.0 °C limit
    lines = [
        '{"inspection_id": "INS-HOT-01", "asset_id": "WELL-0001", "inspected_at": "2026-07-01T12:00:00Z", "ambient_temp_c": 40.0, "wellhead_temp_c": 86.0}',
        '{"inspection_id": "INS-NORM-02", "asset_id": "WELL-0001", "inspected_at": "2026-07-08T12:00:00Z", "ambient_temp_c": 40.0, "wellhead_temp_c": 85.0}',
    ]
    _setup_op_asset(tmp_path, inspections_lines=lines)

    result = check_safety_and_compliance(asset_id="WELL-0001", dataset_root=tmp_path)
    alarms = result["high_temperature_alarms"]
    assert len(alarms) == 1
    assert alarms[0]["inspection_id"] == "INS-HOT-01"
    assert alarms[0]["wellhead_temp_c"] == 86.0
    assert (
        alarms[0]["action_required"]
        == "Shut in well and inspect stuffing box and rod string within 24 hours."
    )


def test_high_temperature_alarm_t350_threshold(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    # T350 wellhead limit is 95.0 °C
    metadata = '{"asset_id": "WELL-0003", "name": "T350 Well", "well_type": "T350"}'
    lines = [
        '{"inspection_id": "INS-T350-01", "asset_id": "WELL-0003", "inspected_at": "2026-07-01T12:00:00Z", "ambient_temp_c": 40.0, "wellhead_temp_c": 92.0}',
        '{"inspection_id": "INS-T350-02", "asset_id": "WELL-0003", "inspected_at": "2026-07-08T12:00:00Z", "ambient_temp_c": 40.0, "wellhead_temp_c": 96.0}',
    ]
    _setup_op_asset(
        tmp_path,
        asset_id="WELL-0003",
        metadata_content=metadata,
        inspections_lines=lines,
    )

    result = check_safety_and_compliance(asset_id="WELL-0003", dataset_root=tmp_path)
    alarms = result["high_temperature_alarms"]
    assert len(alarms) == 1
    assert alarms[0]["inspection_id"] == "INS-T350-02"
    assert alarms[0]["wellhead_temp_c"] == 96.0
    assert alarms[0]["action_required"] == "Shut in well and inspect within 24 hours."


def test_pad_spill_shut_in_triggered_over_5_percent(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    # Spill covering 6% pad area requires immediate shut-in
    lines = [
        '{"inspection_id": "INS-SPILL-01", "asset_id": "WELL-0001", "inspected_at": "2026-08-01T10:00:00Z", "ambient_temp_c": 20.0, "wellhead_temp_c": 40.0, "spill_detected": true, "spill_area_pct": 6.0, "spill_est_volume_bbl": 2.0}',
    ]
    _setup_op_asset(tmp_path, inspections_lines=lines)

    result = check_safety_and_compliance(asset_id="WELL-0001", dataset_root=tmp_path)
    shut_ins = result["pad_spill_shut_in_events"]
    assert len(shut_ins) == 1
    assert shut_ins[0]["inspection_id"] == "INS-SPILL-01"
    assert shut_ins[0]["spill_area_pct"] == 6.0


def test_pad_spill_corrected_does_not_trigger_shut_in(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    lines = [
        '{"inspection_id": "INS-SPILL-CORR", "asset_id": "WELL-0001", "inspected_at": "2026-08-01T10:00:00Z", "ambient_temp_c": 20.0, "wellhead_temp_c": 40.0, "spill_detected": true, "spill_area_pct": 8.0, "spill_est_volume_bbl": 4.0}',
    ]
    context = [
        '{"asset_id": "WELL-0001", "created_at": "2026-08-02T10:00:00Z", "author_user_id": "U-401", "note_type": "correction", "inspection_id": "INS-SPILL-CORR", "text": "Shadow pattern from workover rig, not oil spill.", "note_id": "CTX-01"}',
    ]
    _setup_op_asset(tmp_path, inspections_lines=lines, context_lines=context)

    result = check_safety_and_compliance(asset_id="WELL-0001", dataset_root=tmp_path)
    assert len(result["pad_spill_shut_in_events"]) == 0
    assert len(result["reportable_spills"]) == 0


def test_reportable_spill_unfiled_distinguished_from_filed(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    # A reportable spill with NO matching regulatory filing
    lines = [
        '{"inspection_id": "INS-UNFILED", "asset_id": "WELL-0001", "inspected_at": "2026-08-01T10:00:00Z", "ambient_temp_c": 20.0, "wellhead_temp_c": 40.0, "spill_detected": true, "spill_area_pct": 2.0, "spill_est_volume_bbl": 10.0}',
    ]
    _setup_op_asset(tmp_path, inspections_lines=lines)

    result = check_safety_and_compliance(asset_id="WELL-0001", dataset_root=tmp_path)
    spills = result["reportable_spills"]
    assert len(spills) == 1
    assert spills[0]["reporting_required"] is True
    assert spills[0]["proof_of_submission"] is False
    assert spills[0]["filed_on_time"] is False

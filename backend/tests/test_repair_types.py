import json
import pytest
from fastapi.testclient import TestClient

from app.main import app, DATASET_ROOT
from app.operational_intelligence import get_repair_types_summary
from app.assistant import classify_question, process_assistant_question


client = TestClient(app)


def test_get_repair_types_summary_fleet_real_dataset():
    """Verify fleet-wide repair type aggregation against authoritative dataset."""
    res = get_repair_types_summary(asset_id=None, dataset_root=DATASET_ROOT)

    assert res["scope"] == "fleet"
    assert res["asset_id"] is None
    assert res["total_records"] == 5665
    assert res["maintenance_type_count"] == 2
    assert res["maintenance_types"] == {"scheduled": 4156, "corrective": 1509}
    assert res["scheduled_count"] == 4156
    assert res["corrective_count"] == 1509
    assert res["corrective_equipment_kind_count"] == 6

    # Verify exact equipment subsystem categories and counts for corrective repairs
    corrective_kinds = res["corrective_equipment_kinds"]
    assert corrective_kinds["flowline"] == 832
    assert corrective_kinds["pump_jack"] == 400
    assert corrective_kinds["wellhead"] == 81
    assert corrective_kinds["downhole_pump"] == 80
    assert corrective_kinds["rod_string"] == 77
    assert corrective_kinds["separator"] == 39

    # Verify evidence citations
    assert len(res["evidence"]) > 0
    sources = [e.get("source") for e in res["evidence"]]
    assert "02-dataset-guide.md" in sources
    assert "sample-data/assets/*/maintenance.jsonl" in sources


def test_get_repair_types_summary_asset_scoped_real_dataset():
    """Verify asset-scoped repair type aggregation for WELL-0001."""
    res = get_repair_types_summary(asset_id="WELL-0001", dataset_root=DATASET_ROOT)

    assert res["scope"] == "asset"
    assert res["asset_id"] == "WELL-0001"
    assert res["total_records"] == 32
    assert res["maintenance_types"] == {"scheduled": 20, "corrective": 12}
    assert res["scheduled_count"] == 20
    assert res["corrective_count"] == 12

    # WELL-0001 has flowline, pump_jack, and wellhead maintenance
    assert "flowline" in res["corrective_equipment_kinds"]
    assert "wellhead" in res["corrective_equipment_kinds"]
    assert "pump_jack" in res["corrective_equipment_kinds"]

    # Verify evidence citations contain WELL-0001 maintenance IDs
    mnt_ids = [e.get("maintenance_id") for e in res["evidence"] if e.get("maintenance_id")]
    assert len(mnt_ids) > 0
    for mid in mnt_ids:
        assert mid.startswith("MNT-0001-")


def test_repair_types_assistant_routing_fleet():
    """The original failing query: 'How many types of repairs are there?'
    Must route to repair_types (not document_retrieval), return answered status,
    and ground the answer in both maintenance_type (scheduled vs corrective)
    and equipment_kind subsystems.
    """
    res = process_assistant_question(
        question="How many types of repairs are there?",
        asset_id=None,
        dataset_root=DATASET_ROOT,
    )

    assert res.question_type == "repair_types"
    assert res.status == "answered"
    assert res.asset_id is None

    # Verify response text distinguishes maintenance action types and equipment kinds
    assert "maintenance event" in res.answer.lower()
    assert "corrective" in res.answer.lower()
    assert "scheduled" in res.answer.lower()
    assert "flowline" in res.answer.lower()
    assert "pump_jack" in res.answer.lower()

    # Verify Markdown table structure is present in answer
    assert "| Equipment Subsystem |" in res.answer
    assert "| ------------------- |" in res.answer

    # Verify evidence citations
    assert len(res.evidence) > 0
    assert any("maintenance" in str(e.get("source", "")) for e in res.evidence)


def test_repair_types_assistant_routing_asset():
    """Verify asset-scoped question routing to repair_types."""
    res = process_assistant_question(
        question="What repair types does WELL-0001 have?",
        asset_id=None,
        dataset_root=DATASET_ROOT,
    )

    assert res.question_type == "repair_types"
    assert res.status == "answered"
    assert res.asset_id == "WELL-0001"
    assert "WELL-0001" in res.answer
    assert "32" in res.answer or "12" in res.answer


def test_repair_types_routing_precedence():
    """Verify that routing precedence is preserved:
    - Queries asking about manuals/SOPs still route to document retrieval.
    - Queries asking about RCA still route to maintenance recurrence.
    - Queries asking about downtime still route to downtime.
    - Queries asking about production still route to production status.
    """
    # 1. Manual / SOP queries -> document_retrieval
    sop_q = "What are the repair procedures according to the manual?"
    assert classify_question(sop_q, has_asset_id=False) != "repair_types"

    # 2. Maintenance recurrence / RCA -> maintenance_recurrence
    rca_q = "Does WELL-0001 require a root-cause analysis for recurring repairs?"
    assert classify_question(rca_q, has_asset_id=True) == "maintenance_recurrence"

    # 3. Consecutive downtime -> consecutive_downtime
    cd_q = "Has WELL-0001 had 14 consecutive days of downtime?"
    assert classify_question(cd_q, has_asset_id=True) == "consecutive_downtime"

    # 4. Downtime estimation -> downtime
    dt_q = "How many days of downtime did WELL-0001 have in 2025?"
    assert classify_question(dt_q, has_asset_id=True) == "downtime"

    # 5. Production status -> production_status
    ps_q = "Is WELL-0001 producing?"
    assert classify_question(ps_q, has_asset_id=True) == "production_status"

    # 6. Repair types -> repair_types
    assert classify_question("How many types of repairs are there?", has_asset_id=False) == "repair_types"
    assert classify_question("What types of repairs are there?", has_asset_id=False) == "repair_types"
    assert classify_question("What repair types exist?", has_asset_id=False) == "repair_types"
    assert classify_question("How many types of maintenance are there?", has_asset_id=False) == "repair_types"


def test_repair_types_empty_and_malformed_records(tmp_path):
    """Verify robustness when maintenance.jsonl is empty or contains malformed lines."""
    mock_asset = tmp_path / "sample-data" / "assets" / "WELL-0099"
    mock_asset.mkdir(parents=True)

    metadata = {"asset_id": "WELL-0099", "well_type": "T200"}
    (mock_asset / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    # 1. Empty maintenance file
    (mock_asset / "maintenance.jsonl").write_text("", encoding="utf-8")
    res_empty = get_repair_types_summary("WELL-0099", dataset_root=tmp_path)
    assert res_empty["total_records"] == 0
    assert res_empty["maintenance_type_count"] == 0
    assert res_empty["corrective_count"] == 0

    # 2. Malformed json lines mixed with valid lines
    lines = [
        "THIS IS INVALID JSON",
        json.dumps({"maintenance_id": "MNT-0099-001", "asset_id": "WELL-0099", "maintenance_type": "corrective", "equipment_kind": "flowline", "issue": "Corrosion leak"}),
        "{truncated",
        json.dumps({"maintenance_id": "MNT-0099-002", "asset_id": "WELL-0099", "maintenance_type": "scheduled", "equipment_kind": "wellhead"}),
        "   ",
    ]
    (mock_asset / "maintenance.jsonl").write_text("\n".join(lines), encoding="utf-8")
    res_malformed = get_repair_types_summary("WELL-0099", dataset_root=tmp_path)
    assert res_malformed["total_records"] == 2
    assert res_malformed["maintenance_types"] == {"corrective": 1, "scheduled": 1}
    assert res_malformed["corrective_equipment_kinds"] == {"flowline": 1}


def test_repair_types_unknown_well_and_invalid_id():
    """Verify error handling for nonexistent well and malformed asset ID."""
    with pytest.raises(Exception) as exc_info:
        get_repair_types_summary("WELL-9999", dataset_root=DATASET_ROOT)
    assert exc_info.value.status_code == 404

    with pytest.raises(Exception) as exc_info:
        get_repair_types_summary("WELL 0001", dataset_root=DATASET_ROOT)
    assert exc_info.value.status_code == 400


def test_repair_types_rest_endpoints():
    """Verify REST API endpoints for repair types."""
    # Fleet endpoint
    resp_fleet = client.get("/api/fleet/repair-types")
    assert resp_fleet.status_code == 200
    data_fleet = resp_fleet.json()
    assert data_fleet["scope"] == "fleet"
    assert data_fleet["total_records"] == 5665
    assert data_fleet["corrective_count"] == 1509

    # Well-specific endpoint
    resp_well = client.get("/api/wells/WELL-0001/repair-types")
    assert resp_well.status_code == 200
    data_well = resp_well.json()
    assert data_well["scope"] == "asset"
    assert data_well["asset_id"] == "WELL-0001"
    assert data_well["total_records"] == 32

    # Assistant POST endpoint
    resp_assistant = client.post(
        "/api/assistant/ask",
        json={"question": "How many types of repairs are there?"},
    )
    assert resp_assistant.status_code == 200
    data_asst = resp_assistant.json()
    assert data_asst["question_type"] == "repair_types"
    assert data_asst["status"] == "answered"
    assert data_asst["details"]["corrective_count"] == 1509

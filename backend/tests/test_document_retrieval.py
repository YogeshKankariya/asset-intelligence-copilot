import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.document_retrieval import (
    DocumentChunk,
    DocumentCorpus,
    BM25Retriever,
    retrieve_documents,
    load_and_chunk_markdown,
    load_context_jsonl_chunks,
    detect_documentary_conflicts,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Test Helper Fixtures
# ---------------------------------------------------------------------------


def _setup_retrieval_fixture(tmp_path: Path):
    fleet_dir = tmp_path / "sample-data" / "fleet"
    well_types_dir = fleet_dir / "well-types"
    sops_dir = fleet_dir / "sops"
    well_types_dir.mkdir(parents=True, exist_ok=True)
    sops_dir.mkdir(parents=True, exist_ok=True)

    t200_content = """# T200 Rod-Lift Oil Well — Operating & Maintenance Manual

## 9. Engineering limits

### 9.1 Pressure
Maximum allowable wellhead working pressure: 3,000 psi.

### 9.2 Stroke
Maximum stroke rate: 10 spm. Maximum polished-rod load: 22,800 lb.

### 9.3 Production temperature rule
A T200 well is considered producing when wellhead temperature is at least 15 °C above ambient.
"""
    (well_types_dir / "T200.md").write_text(t200_content, encoding="utf-8")

    t350_content = """# T350 Deep Rod-Lift Oil Well — Operating & Maintenance Manual

## 2. Differences from T200

| Item | T200 | T350 |
|---|---|---|
| Wellhead rating | 3,000 psi | 5,000 psi |
| Pump jack | PJ-228 | PJ-456 |

## 3. Production temperature rule
A T350 well is considered producing only when wellhead temperature is at least 20 °C above ambient.
"""
    (well_types_dir / "T350.md").write_text(t350_content, encoding="utf-8")

    sop_content = """# Field Work Safety and Maintenance SOP

## 3. Protocols

| Protocol ID | Requirement |
|---|---|
| **WS-04** | Hot work permit and gas test required. No hot work while flammable gas reads 10% LEL or more. |
| **WS-05** | Pressure-test the repaired section at at least 1.25 × MOP and hold for 4 hours with no drop. |
"""
    (sops_dir / "field-work-sop.md").write_text(sop_content, encoding="utf-8")

    # Asset WELL-0001
    asset_dir = tmp_path / "sample-data" / "assets" / "WELL-0001"
    mnt_dir = asset_dir / "maintenance-reports"
    mnt_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "asset_id": "WELL-0001",
        "name": "Alpha Well 01",
        "well_type": "T200",
        "equipment": [{"kind": "wellhead", "model": "WH-3000"}],
    }
    (asset_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    mnt_content = """# Maintenance Report — MNT-0001-002

**Asset:** WELL-0001
**Equipment:** flowline

## Root cause
Thread fatigue from pump jack vibration caused coupling failure.

## Work done
Replaced coupling and 4 m of flowline, and pressure-tested under WS-05.
"""
    (mnt_dir / "MNT-0001-002.md").write_text(mnt_content, encoding="utf-8")

    notes = [
        {"note_id": "NOTE-001", "asset_id": "WELL-0001", "note_type": "operator_note", "text": "Lubricated bearings on schedule.", "author": "U-101", "timestamp": "2026-03-01T08:00:00Z"},
        {"note_id": "NOTE-002", "asset_id": "WELL-0001", "inspection_id": "INS-0001-0021", "note_type": "correction", "text": "Staining was verified as rainwater; no crude released.", "author": "U-102", "timestamp": "2026-03-05T09:00:00Z"},
    ]
    (asset_dir / "context.jsonl").write_text("\n".join(json.dumps(n) for n in notes) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Question answered from T200 manual passage
# ---------------------------------------------------------------------------


def test_t200_manual_retrieval(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    monkeypatch.setattr("app.operational_intelligence.DATASET_ROOT", tmp_path)
    _setup_retrieval_fixture(tmp_path)

    response = client.post(
        "/api/assistant/ask",
        json={"question": "What is the maximum allowable wellhead working pressure for T200?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert data["question_type"] == "document_retrieval"
    assert "3,000 psi" in data["answer"]
    assert any("T200.md" in e["source"] for e in data["evidence"])
    assert any("### 9.1 Pressure" in e["section"] for e in data["evidence"])


# ---------------------------------------------------------------------------
# 2. Question answered from T350 manual passage
# ---------------------------------------------------------------------------


def test_t350_manual_retrieval(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    monkeypatch.setattr("app.operational_intelligence.DATASET_ROOT", tmp_path)
    _setup_retrieval_fixture(tmp_path)

    response = client.post(
        "/api/assistant/ask",
        json={"question": "What is the wellhead rating for T350 compared to T200?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert data["question_type"] == "document_retrieval"
    assert "5,000 psi" in data["answer"]
    assert any("T350.md" in e["source"] for e in data["evidence"])


# ---------------------------------------------------------------------------
# 3. Retrieval from global SOP
# ---------------------------------------------------------------------------


def test_global_sop_retrieval(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    monkeypatch.setattr("app.operational_intelligence.DATASET_ROOT", tmp_path)
    _setup_retrieval_fixture(tmp_path)

    response = client.post(
        "/api/assistant/ask",
        json={"question": "What are the pressure test requirements under protocol WS-05?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert data["question_type"] == "document_retrieval"
    assert "1.25 × MOP" in data["answer"] or "4 hours" in data["answer"]
    assert any("field-work-sop.md" in e["source"] for e in data["evidence"])


# ---------------------------------------------------------------------------
# 4. Retrieval of asset-specific report or note
# ---------------------------------------------------------------------------


def test_asset_specific_report_retrieval(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    monkeypatch.setattr("app.operational_intelligence.DATASET_ROOT", tmp_path)
    _setup_retrieval_fixture(tmp_path)

    response = client.post(
        "/api/assistant/ask",
        json={"question": "What was the root cause in maintenance report MNT-0001-002?", "asset_id": "WELL-0001"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert data["question_type"] == "document_retrieval"
    assert "Thread fatigue from pump jack vibration" in data["answer"]
    assert any("MNT-0001-002.md" in e["source"] for e in data["evidence"])


def test_asset_specific_context_note_retrieval(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    monkeypatch.setattr("app.operational_intelligence.DATASET_ROOT", tmp_path)
    _setup_retrieval_fixture(tmp_path)

    response = client.post(
        "/api/assistant/ask",
        json={"question": "What context notes exist for WELL-0001 regarding lubrication?", "asset_id": "WELL-0001"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert "Lubricated bearings" in data["answer"]
    assert any("context.jsonl" in e["source"] for e in data["evidence"])


# ---------------------------------------------------------------------------
# 5. Exact ID matching
# ---------------------------------------------------------------------------


def test_exact_id_matching(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    monkeypatch.setattr("app.operational_intelligence.DATASET_ROOT", tmp_path)
    _setup_retrieval_fixture(tmp_path)

    response = client.post(
        "/api/assistant/ask",
        json={"question": "Tell me about WS-04"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert "WS-04" in data["answer"]
    assert "10% LEL" in data["answer"]


# ---------------------------------------------------------------------------
# 6. Asset-specific retrieval while still finding relevant global guidance
# ---------------------------------------------------------------------------


def test_asset_specific_with_global_guidance(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    monkeypatch.setattr("app.operational_intelligence.DATASET_ROOT", tmp_path)
    _setup_retrieval_fixture(tmp_path)

    # When querying with asset_id="WELL-0001" about pressure testing under WS-05:
    # Both the asset maintenance report mentioning WS-05 and the global field-work-sop.md should be in evidence!
    response = client.post(
        "/api/assistant/ask",
        json={"question": "How did WELL-0001 perform pressure testing under WS-05?", "asset_id": "WELL-0001"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    evidence_sources = [e["source"] for e in data["evidence"]]
    assert any("MNT-0001-002.md" in s for s in evidence_sources)
    assert any("field-work-sop.md" in s for s in evidence_sources)


# ---------------------------------------------------------------------------
# 7. Long-document chunking and metadata preservation
# ---------------------------------------------------------------------------


def test_long_document_chunking(tmp_path):
    # Create a markdown file with multiple sections and a long section
    long_doc = tmp_path / "long_doc.md"
    long_text = [f"Paragraph {i}: This is long operational guidance text explaining oilfield details." for i in range(40)]
    content = f"# Master Operating Guide\n\n## Section 1\nShort text.\n\n## Section 2\n" + "\n\n".join(long_text)
    long_doc.write_text(content, encoding="utf-8")

    chunks = load_and_chunk_markdown(long_doc, tmp_path, doc_type="manual")
    assert len(chunks) > 2  # Proves long section was divided into manageable chunks
    for c in chunks:
        assert c.source_path == "long_doc.md"
        assert c.title == "Master Operating Guide"
        assert c.section in ["## Section 1", "## Section 2"]
        assert len(c.content) <= 1500


# ---------------------------------------------------------------------------
# 8. Empty corpus and unreadable / malformed files
# ---------------------------------------------------------------------------


def test_empty_corpus(tmp_path):
    empty_dir = tmp_path / "empty_dataset"
    empty_dir.mkdir(parents=True, exist_ok=True)
    results = retrieve_documents(query="What is WS-05?", dataset_root=empty_dir)
    assert results == []


def test_malformed_and_unreadable_files(tmp_path):
    sample_dir = tmp_path / "sample-data" / "assets" / "WELL-0001"
    sample_dir.mkdir(parents=True, exist_ok=True)

    # Malformed JSON in context.jsonl
    (sample_dir / "context.jsonl").write_text("NOT_JSON\n{\"bad\":\n", encoding="utf-8")
    # Empty markdown
    (sample_dir / "empty.md").write_text("", encoding="utf-8")

    chunks = load_context_jsonl_chunks(sample_dir / "context.jsonl", tmp_path, asset_id="WELL-0001")
    assert chunks == []

    md_chunks = load_and_chunk_markdown(sample_dir / "empty.md", tmp_path)
    assert md_chunks == []


# ---------------------------------------------------------------------------
# 9. Low-relevance query returns insufficient evidence
# ---------------------------------------------------------------------------


def test_low_relevance_query_insufficient_evidence(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    monkeypatch.setattr("app.operational_intelligence.DATASET_ROOT", tmp_path)
    _setup_retrieval_fixture(tmp_path)

    response = client.post(
        "/api/assistant/ask",
        json={"question": "What is the capital of Australia?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unsupported"
    assert data["evidence"] == []
    assert "insufficient documentary evidence" in data["answer"].lower()


# ---------------------------------------------------------------------------
# 10. Conflicting retrieved sources are disclosed
# ---------------------------------------------------------------------------


def test_conflicting_retrieved_sources_disclosed(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.DATASET_ROOT", tmp_path)
    monkeypatch.setattr("app.operational_intelligence.DATASET_ROOT", tmp_path)
    _setup_retrieval_fixture(tmp_path)

    # Query comparing wellhead ratings retrieved from both T200 and T350 manuals
    response = client.post(
        "/api/assistant/ask",
        json={"question": "What is the wellhead rating difference between T200 and T350?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert len(data["conflicts"]) >= 1
    assert "T200 and T350" in data["conflicts"][0]["description"]


# ---------------------------------------------------------------------------
# 11. Existing deterministic assistant handlers remain unchanged
# ---------------------------------------------------------------------------


def test_deterministic_handler_unchanged_production_status():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "Is WELL-0001 producing?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert data["question_type"] == "production_status"
    assert "not producing" in data["answer"].lower()
    assert len(data["evidence"]) >= 1
    assert data["evidence"][0]["inspection_id"] == "INS-0001-0203"


def test_deterministic_handler_unchanged_downtime():
    response = client.post(
        "/api/assistant/ask",
        json={"question": "What was the estimated downtime for WELL-0001 in 2025?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert data["question_type"] == "downtime"
    assert "21 days" in data["answer"]


# ---------------------------------------------------------------------------
# 12. Existing corrections are not accidentally applied to unrelated fields
# ---------------------------------------------------------------------------


def test_corrections_not_applied_to_unrelated_fields(monkeypatch, tmp_path):
    monkeypatch.setattr("app.operational_intelligence.DATASET_ROOT", tmp_path)
    _setup_retrieval_fixture(tmp_path)

    # In our fixture, NOTE-002 is a correction for INS-0001-0021 (staining was rainwater).
    # It must NOT affect pressure test requirements under WS-05 or MNT-0001-002.
    results = retrieve_documents(query="What is WS-05?", dataset_root=tmp_path)
    conflicts, _ = detect_documentary_conflicts(results)
    assert not any(c.get("field") == "documentary_evidence" for c in conflicts)

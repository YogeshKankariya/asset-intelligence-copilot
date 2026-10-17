
import json
import math
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Asset Intelligence Copilot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# This points to the dataset repository beside the application repository.
DATASET_ROOT = Path(
    r"C:\Users\Admin\flytbase-ahc-swe-asset-intelligence-dataset"
)

# Verified well-type production threshold rules:
# - T200: Section 9.3 of T200.md (at least 15.0°C above ambient)
# - T350: Section 3 of T350.md (at least 20.0°C above ambient)
WELL_TYPE_THRESHOLDS: dict[str, float] = {
    "T200": 15.0,
    "T350": 20.0,
}


def get_well_type_threshold(well_type: Any) -> float:
    """Retrieve the verified production threshold for a given well type.

    Raises HTTPException(422) if the well type is unsupported or unconfigured.
    """
    if not isinstance(well_type, str) or well_type not in WELL_TYPE_THRESHOLDS:
        raise HTTPException(
            status_code=422,
            detail=f"No verified production threshold configured for {well_type}",
        )
    return WELL_TYPE_THRESHOLDS[well_type]


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Dataset file not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON in dataset")

    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="Invalid metadata format")

    return data


def load_inspections(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []

    records = []
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as file:
            for line in file:
                line_str = line.strip()
                if line_str:
                    try:
                        record = json.loads(line_str)
                        if isinstance(record, dict):
                            records.append(record)
                    except json.JSONDecodeError:
                        continue
    except OSError:
        return []

    return records


def load_context(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []

    records = []
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as file:
            for line in file:
                line_str = line.strip()
                if line_str:
                    try:
                        record = json.loads(line_str)
                        if isinstance(record, dict):
                            records.append(record)
                    except json.JSONDecodeError:
                        continue
    except OSError:
        return []

    return records


def calculate_production_status(
    wellhead_temp_c: float,
    ambient_temp_c: float,
    threshold_c: float,
) -> dict[str, Any]:
    raw_difference = wellhead_temp_c - ambient_temp_c
    computed_status = (
        "producing" if raw_difference >= threshold_c else "not_producing"
    )
    return {
        "computed_status": computed_status,
        "temperature_difference_c": round(raw_difference, 2),
        "threshold_c": threshold_c,
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/wells")
def list_wells_endpoint(dataset_root: Path | None = None):
    from app.config import resolve_assets_root
    assets_dir = resolve_assets_root(dataset_root or DATASET_ROOT)
    if not assets_dir.is_dir():
        return {"wells": []}

    wells = []
    for d in sorted(assets_dir.iterdir()):
        if d.is_dir() and d.name.startswith("WELL-"):
            meta_path = d / "metadata.json"
            well_type = None
            name = None
            if meta_path.is_file():
                try:
                    with meta_path.open("r", encoding="utf-8-sig") as f:
                        meta = json.load(f)
                        if isinstance(meta, dict):
                            well_type = meta.get("well_type")
                            name = meta.get("name")
                except Exception:
                    pass
            wells.append({
                "asset_id": d.name,
                "well_type": well_type,
                "name": name,
            })
    return {"wells": wells}


@app.get("/api/wells/{asset_id}/status")
def get_well_status(asset_id: str, dataset_root: Path | None = None):
    # Prevent path traversal: accept only simple asset IDs.
    if not asset_id or any(
        character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz0123456789-_"
        for character in asset_id
    ):
        raise HTTPException(status_code=400, detail="Invalid asset ID")

    from app.config import resolve_asset_dir
    asset_dir = resolve_asset_dir(asset_id, dataset_root or DATASET_ROOT)
    metadata_path = asset_dir / "metadata.json"
    inspections_path = asset_dir / "inspections.jsonl"
    context_path = asset_dir / "context.jsonl"

    if not metadata_path.is_file():
        raise HTTPException(status_code=404, detail="Well not found")

    metadata = load_json(metadata_path)

    if metadata.get("asset_id") != asset_id:
        raise HTTPException(status_code=500, detail="Asset ID mismatch")

    well_type = metadata.get("well_type")
    threshold = get_well_type_threshold(well_type)

    inspections = load_inspections(inspections_path)
    context_records = load_context(context_path)

    # Filter context records belonging to this asset
    asset_notes = [
        note
        for note in context_records
        if isinstance(note, dict) and note.get("asset_id") == asset_id
    ]

    # Keep only records belonging to this asset and containing valid readings.
    valid_inspections = []
    for inspection in inspections:
        if not isinstance(inspection, dict):
            continue

        if inspection.get("asset_id") != asset_id:
            continue

        try:
            ambient_raw = inspection["ambient_temp_c"]
            wellhead_raw = inspection["wellhead_temp_c"]

            if isinstance(ambient_raw, bool) or isinstance(wellhead_raw, bool):
                continue

            ambient = float(ambient_raw)
            wellhead = float(wellhead_raw)

            if (
                math.isnan(ambient)
                or math.isinf(ambient)
                or math.isnan(wellhead)
                or math.isinf(wellhead)
            ):
                continue

            timestamp = inspection["inspected_at"]
            inspection_id = inspection["inspection_id"]

            if not isinstance(timestamp, str) or not timestamp.strip():
                continue
            if not isinstance(inspection_id, str) or not inspection_id.strip():
                continue
        except (KeyError, TypeError, ValueError):
            continue

        valid_inspections.append(
            {
                "inspection_id": inspection_id,
                "inspected_at": timestamp,
                "ambient_temp_c": ambient,
                "wellhead_temp_c": wellhead,
                "temperature_difference_c": round(wellhead - ambient, 2),
            }
        )

    if not valid_inspections:
        raise HTTPException(
            status_code=404,
            detail="No valid inspection readings found for this well",
        )

    # ISO 8601 UTC timestamps sort chronologically for this dataset.
    max_timestamp = max(record["inspected_at"] for record in valid_inspections)
    latest_candidates = [
        record
        for record in valid_inspections
        if record["inspected_at"] == max_timestamp
    ]

    candidate_statuses = {}
    for cand in latest_candidates:
        cand_status = calculate_production_status(
            wellhead_temp_c=cand["wellhead_temp_c"],
            ambient_temp_c=cand["ambient_temp_c"],
            threshold_c=threshold,
        )
        candidate_statuses[cand["inspection_id"]] = cand_status

    unique_statuses = {s["computed_status"] for s in candidate_statuses.values()}

    latest = latest_candidates[0]
    production = candidate_statuses[latest["inspection_id"]]

    conflicts = []
    has_unresolved_inspection_conflict = len(unique_statuses) > 1

    if has_unresolved_inspection_conflict:
        conflicts.append(
            {
                "source": f"assets/{asset_id}/inspections.jsonl",
                "field": "computed_status",
                "conflicting_records": [c["inspection_id"] for c in latest_candidates],
                "description": (
                    f"Multiple inspection records exist for timestamp '{max_timestamp}' "
                    "with contradictory production statuses."
                ),
                "resolution": None,
                "is_resolved": False,
            }
        )

    # Check for explicit valid corrections for the latest inspection
    # Per dataset guide: note_type == "correction" targets inspection_id
    corrections = []
    for note in asset_notes:
        if (
            note.get("note_type") == "correction"
            and note.get("inspection_id") == latest["inspection_id"]
        ):
            corrections.append(
                {
                    "note_id": note.get("note_id"),
                    "inspection_id": note.get("inspection_id"),
                    "note_type": "correction",
                    "text": note.get("text"),
                    "created_at": note.get("created_at"),
                    "author_user_id": note.get("author_user_id"),
                    "source": f"assets/{asset_id}/context.jsonl",
                }
            )

    # Check for conflict with metadata recorded_status
    recorded_status = metadata.get("recorded_status")
    if recorded_status and isinstance(recorded_status, str):
        recorded_as_producing = recorded_status.lower() == "active"
        is_producing = production["computed_status"] == "producing"
        if recorded_as_producing != is_producing:
            conflicts.append(
                {
                    "source": f"assets/{asset_id}/metadata.json",
                    "field": "recorded_status",
                    "value": recorded_status,
                    "conflicts_with": "computed_status",
                    "description": (
                        f"Recorded status '{recorded_status}' in metadata disagrees with "
                        f"computed status '{production['computed_status']}' from latest inspection."
                    ),
                    "resolution": "inspections_take_precedence",
                    "is_resolved": True,
                }
            )

    # Determine status and conflict resolution state
    if has_unresolved_inspection_conflict:
        computed_status = "conflict"
        status_basis = "conflicting_inspection_records"
        conflict_status = "unresolved"
    else:
        computed_status = production["computed_status"]
        status_basis = "latest_valid_inspection"
        conflict_status = (
            "resolved_by_inspection_precedence" if conflicts else "none"
        )

    # Build evidence records identifying source records and timestamps
    evidence = []
    for cand in latest_candidates:
        evidence.append(
            {
                "inspection_id": cand["inspection_id"],
                "record_id": cand["inspection_id"],
                "source": f"assets/{asset_id}/inspections.jsonl",
                "timestamp": cand["inspected_at"],
                "record_type": "inspection",
            }
        )

    for corr in corrections:
        evidence.append(
            {
                "record_id": corr["note_id"],
                "source": corr["source"],
                "timestamp": corr.get("created_at"),
                "record_type": "correction",
                "description": corr.get("text"),
            }
        )

    return {
        "asset_id": asset_id,
        "asset_name": metadata.get("name"),
        "well_type": well_type,
        "computed_status": computed_status,
        "status_basis": status_basis,
        "recorded_status": recorded_status,
        "inspection_timestamp": latest["inspected_at"],
        "ambient_temp_c": latest["ambient_temp_c"],
        "wellhead_temp_c": latest["wellhead_temp_c"],
        "temperature_difference_c": production["temperature_difference_c"],
        "threshold_c": production["threshold_c"],
        "evidence": evidence,
        "has_correction": len(corrections) > 0,
        "corrections": corrections,
        "conflicts": conflicts,
        "conflict_status": conflict_status,
        "note": (
            "This is the status inferred from the latest valid inspection, "
            "not a guarantee of the well's current physical state."
        ),
    }


@app.get("/api/wells/{asset_id}/downtime")
def get_well_downtime_endpoint(
    asset_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    year: int | None = None,
):
    from app.operational_intelligence import calculate_well_downtime

    return calculate_well_downtime(
        asset_id=asset_id,
        start_date=start_date,
        end_date=end_date,
        year=year,
        dataset_root=DATASET_ROOT,
    )


@app.get("/api/wells/{asset_id}/consecutive-downtime")
def get_consecutive_downtime_endpoint(
    asset_id: str,
    threshold_days: int = 14,
):
    from app.operational_intelligence import check_consecutive_downtime

    return check_consecutive_downtime(
        asset_id=asset_id,
        consecutive_days_threshold=threshold_days,
        dataset_root=DATASET_ROOT,
    )


@app.get("/api/wells/{asset_id}/maintenance-recurrence")
def get_maintenance_recurrence_endpoint(
    asset_id: str,
    window_days: int = 365,
    min_events: int = 3,
):
    from app.operational_intelligence import check_maintenance_recurrence

    return check_maintenance_recurrence(
        asset_id=asset_id,
        window_days=window_days,
        min_events=min_events,
        dataset_root=DATASET_ROOT,
    )


@app.get("/api/wells/{asset_id}/safety-compliance")
def get_safety_compliance_endpoint(
    asset_id: str,
):
    from app.operational_intelligence import check_safety_and_compliance

    return check_safety_and_compliance(
        asset_id=asset_id,
        dataset_root=DATASET_ROOT,
    )


@app.get("/api/fleet/repair-types")
def get_fleet_repair_types_endpoint():
    from app.operational_intelligence import get_repair_types_summary

    return get_repair_types_summary(
        asset_id=None,
        dataset_root=DATASET_ROOT,
    )


@app.get("/api/wells/{asset_id}/repair-types")
def get_well_repair_types_endpoint(asset_id: str):
    from app.operational_intelligence import get_repair_types_summary

    return get_repair_types_summary(
        asset_id=asset_id,
        dataset_root=DATASET_ROOT,
    )



class AssistantAskRequest(BaseModel):
    question: str = ""
    asset_id: str | None = None
    session_id: str | None = None
    user_id: str | None = None
    user_name: str | None = None


@app.post("/api/assistant/ask")
def assistant_ask_endpoint(request: AssistantAskRequest):
    from app.assistant import process_assistant_question

    return process_assistant_question(
        question=request.question,
        asset_id=request.asset_id,
        session_id=request.session_id,
        user_id=request.user_id,
        user_name=request.user_name,
        dataset_root=DATASET_ROOT,
    )



import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

app = FastAPI(title="Asset Intelligence Copilot")

# This points to the dataset repository beside the application repository.
DATASET_ROOT = Path(
    r"C:\Users\Admin\flytbase-ahc-swe-asset-intelligence-dataset"
)

# Confirmed T200 rule from Section 9.3 of T200.md.
# T350 is intentionally not configured until its rule is verified.
WELL_TYPE_THRESHOLDS = {
    "T200": 15.0,
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig") as file:
            return json.load(file)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Dataset file not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON in dataset")


def load_inspections(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    records = []
    with path.open("r", encoding="utf-8-sig") as file:
        for line in file:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

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


@app.get("/api/wells/{asset_id}/status")
def get_well_status(asset_id: str):
    # Prevent path traversal: accept only simple asset IDs.
    if not asset_id or any(
        character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz0123456789-_"
        for character in asset_id
    ):
        raise HTTPException(status_code=400, detail="Invalid asset ID")

    asset_dir = DATASET_ROOT / "sample-data" / "assets" / asset_id
    metadata_path = asset_dir / "metadata.json"
    inspections_path = asset_dir / "inspections.jsonl"

    if not metadata_path.is_file():
        raise HTTPException(status_code=404, detail="Well not found")

    metadata = load_json(metadata_path)

    if metadata.get("asset_id") != asset_id:
        raise HTTPException(status_code=500, detail="Asset ID mismatch")

    well_type = metadata.get("well_type")
    threshold = WELL_TYPE_THRESHOLDS.get(well_type)

    if threshold is None:
        raise HTTPException(
            status_code=422,
            detail=f"No verified production threshold configured for {well_type}",
        )

    inspections = load_inspections(inspections_path)

    # Keep only records belonging to this asset and containing valid readings.
    valid_inspections = []
    for inspection in inspections:
        if inspection.get("asset_id") != asset_id:
            continue

        try:
            ambient = float(inspection["ambient_temp_c"])
            wellhead = float(inspection["wellhead_temp_c"])
            timestamp = inspection["inspected_at"]
            inspection_id = inspection["inspection_id"]

            if not timestamp or not inspection_id:
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
    latest = max(
        valid_inspections,
        key=lambda record: record["inspected_at"],
    )

    production = calculate_production_status(
        wellhead_temp_c=latest["wellhead_temp_c"],
        ambient_temp_c=latest["ambient_temp_c"],
        threshold_c=threshold,
    )

    return {
        "asset_id": asset_id,
        "asset_name": metadata.get("name"),
        "well_type": well_type,
        "computed_status": production["computed_status"],
        "status_basis": "latest_valid_inspection",
        "inspection_timestamp": latest["inspected_at"],
        "ambient_temp_c": latest["ambient_temp_c"],
        "wellhead_temp_c": latest["wellhead_temp_c"],
        "temperature_difference_c": production["temperature_difference_c"],
        "threshold_c": production["threshold_c"],
        "evidence": [
            {
                "inspection_id": latest["inspection_id"],
                "source": f"assets/{asset_id}/inspections.jsonl",
            }
        ],
        "note": (
            "This is the status inferred from the latest valid inspection, "
            "not a guarantee of the well's current physical state."
        ),
    }

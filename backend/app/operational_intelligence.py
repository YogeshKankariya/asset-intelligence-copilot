import datetime
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.main import (
    DATASET_ROOT,
    calculate_production_status,
    get_well_type_threshold,
    load_context,
    load_inspections,
    load_json,
)


def load_maintenance(path: Path) -> list[dict[str, Any]]:
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


def load_regulatory_events(path: Path) -> list[dict[str, Any]]:
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


def _validate_asset_id(asset_id: str) -> None:
    if not asset_id or any(
        character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz0123456789-_"
        for character in asset_id
    ):
        raise HTTPException(status_code=400, detail="Invalid asset ID")


def _get_valid_inspections_for_asset(
    asset_id: str,
    asset_dir: Path,
) -> list[dict[str, Any]]:
    inspections_path = asset_dir / "inspections.jsonl"
    inspections = load_inspections(inspections_path)

    valid_inspections = []
    for inspection in inspections:
        if not isinstance(inspection, dict) or inspection.get("asset_id") != asset_id:
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
                "spill_detected": bool(inspection.get("spill_detected")),
                "spill_area_pct": (
                    float(inspection["spill_area_pct"])
                    if inspection.get("spill_area_pct") is not None
                    and not isinstance(inspection["spill_area_pct"], bool)
                    else None
                ),
                "spill_est_volume_bbl": (
                    float(inspection["spill_est_volume_bbl"])
                    if inspection.get("spill_est_volume_bbl") is not None
                    and not isinstance(inspection["spill_est_volume_bbl"], bool)
                    else None
                ),
                "notes": inspection.get("notes"),
            }
        )

    return valid_inspections


def calculate_well_downtime(
    asset_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    year: int | None = None,
    dataset_root: Path | None = None,
) -> dict[str, Any]:
    """Estimates well downtime using qualifying weekly non-producing inspections.

    Under challenge rules, each weekly inspection finding a well not producing
    contributes 7 days of downtime. Missed inspections add 0 downtime.
    Repair durations in maintenance records are not substituted for downtime.
    """
    _validate_asset_id(asset_id)
    root = dataset_root or DATASET_ROOT
    asset_dir = root / "sample-data" / "assets" / asset_id
    metadata_path = asset_dir / "metadata.json"

    if not metadata_path.is_file():
        raise HTTPException(status_code=404, detail="Well not found")

    metadata = load_json(metadata_path)
    if metadata.get("asset_id") != asset_id:
        raise HTTPException(status_code=500, detail="Asset ID mismatch")

    well_type = metadata.get("well_type")
    threshold = get_well_type_threshold(well_type)

    valid_inspections = _get_valid_inspections_for_asset(asset_id, asset_dir)
    if not valid_inspections:
        raise HTTPException(
            status_code=404,
            detail="No valid inspection readings found for this well",
        )

    # Filter by period
    filtered = []
    for r in valid_inspections:
        ts = r["inspected_at"]
        if year is not None and not ts.startswith(f"{year}-"):
            continue
        if start_date is not None and ts < start_date:
            continue
        if end_date is not None:
            # If end_date is YYYY-MM-DD format, include full day up to T23:59:59Z
            normalized_end = (
                f"{end_date}T23:59:59Z" if len(end_date) == 10 else end_date
            )
            if ts > normalized_end:
                continue
        filtered.append(r)

    filtered.sort(key=lambda x: x["inspected_at"])

    qualifying_non_producing = []
    for r in filtered:
        prod_calc = calculate_production_status(
            wellhead_temp_c=r["wellhead_temp_c"],
            ambient_temp_c=r["ambient_temp_c"],
            threshold_c=threshold,
        )
        if prod_calc["computed_status"] == "not_producing":
            qualifying_non_producing.append(
                {
                    "inspection_id": r["inspection_id"],
                    "record_id": r["inspection_id"],
                    "source": f"assets/{asset_id}/inspections.jsonl",
                    "timestamp": r["inspected_at"],
                    "temperature_difference_c": prod_calc["temperature_difference_c"],
                    "threshold_c": prod_calc["threshold_c"],
                    "computed_status": "not_producing",
                    "record_type": "inspection",
                }
            )

    downtime_days = len(qualifying_non_producing) * 7

    return {
        "asset_id": asset_id,
        "asset_name": metadata.get("name"),
        "well_type": well_type,
        "threshold_c": threshold,
        "downtime_days": downtime_days,
        "non_producing_inspections_count": len(qualifying_non_producing),
        "total_inspections_in_period": len(filtered),
        "period": {
            "year": year,
            "start_date": start_date,
            "end_date": end_date,
        },
        "evidence": qualifying_non_producing,
        "explanation": (
            f"Downtime is estimated based on weekly inspections where each non-producing "
            f"reading contributes 7 days of downtime under the challenge domain rules. "
            f"Found {len(qualifying_non_producing)} non-producing inspection(s) across "
            f"{len(filtered)} total inspection(s) in the period, yielding {downtime_days} days of downtime. "
            "Missed inspections add no downtime, and maintenance repair durations are not used."
        ),
    }


def check_consecutive_downtime(
    asset_id: str,
    consecutive_days_threshold: int = 14,
    dataset_root: Path | None = None,
) -> dict[str, Any]:
    """Identifies consecutive non-producing inspection streaks exceeding a threshold.

    Under challenge rules, each consecutive weekly inspection adds 7 days.
    If an inspection was missed (gap > 10 days between inspections), the streak
    resets because records cannot establish continuous downtime across missed weeks.
    """
    _validate_asset_id(asset_id)
    root = dataset_root or DATASET_ROOT
    asset_dir = root / "sample-data" / "assets" / asset_id
    metadata_path = asset_dir / "metadata.json"

    if not metadata_path.is_file():
        raise HTTPException(status_code=404, detail="Well not found")

    metadata = load_json(metadata_path)
    if metadata.get("asset_id") != asset_id:
        raise HTTPException(status_code=500, detail="Asset ID mismatch")

    well_type = metadata.get("well_type")
    threshold = get_well_type_threshold(well_type)

    valid_inspections = _get_valid_inspections_for_asset(asset_id, asset_dir)
    if not valid_inspections:
        raise HTTPException(
            status_code=404,
            detail="No valid inspection readings found for this well",
        )

    valid_inspections.sort(key=lambda x: x["inspected_at"])

    episodes = []
    current_streak: list[dict[str, Any]] = []
    prev_dt: datetime.datetime | None = None
    max_streak_length = 0

    for r in valid_inspections:
        prod_calc = calculate_production_status(
            wellhead_temp_c=r["wellhead_temp_c"],
            ambient_temp_c=r["ambient_temp_c"],
            threshold_c=threshold,
        )
        is_producing = prod_calc["computed_status"] == "producing"
        dt = datetime.datetime.fromisoformat(r["inspected_at"].replace("Z", "+00:00"))

        if not is_producing:
            # Check gap with previous inspection: if missed (> 10 days), streak breaks
            if prev_dt is not None and (dt - prev_dt).total_seconds() > 10 * 86400:
                if len(current_streak) * 7 > consecutive_days_threshold:
                    episodes.append(_build_consecutive_episode(asset_id, current_streak))
                current_streak = []

            current_streak.append(r)
            if len(current_streak) > max_streak_length:
                max_streak_length = len(current_streak)
        else:
            if len(current_streak) * 7 > consecutive_days_threshold:
                episodes.append(_build_consecutive_episode(asset_id, current_streak))
            current_streak = []

        prev_dt = dt

    if len(current_streak) * 7 > consecutive_days_threshold:
        episodes.append(_build_consecutive_episode(asset_id, current_streak))

    max_consecutive_days = max_streak_length * 7
    exceeds_threshold = len(episodes) > 0

    # Build flat evidence list of inspection records involved in long downtime episodes
    evidence = []
    seen_ids = set()
    for ep in episodes:
        for ins in ep["inspections"]:
            if ins["inspection_id"] not in seen_ids:
                seen_ids.add(ins["inspection_id"])
                evidence.append(
                    {
                        "inspection_id": ins["inspection_id"],
                        "record_id": ins["inspection_id"],
                        "source": f"assets/{asset_id}/inspections.jsonl",
                        "timestamp": ins["inspected_at"],
                        "record_type": "inspection",
                    }
                )

    return {
        "asset_id": asset_id,
        "well_type": well_type,
        "consecutive_days_threshold": consecutive_days_threshold,
        "exceeds_threshold": exceeds_threshold,
        "reporting_required": exceeds_threshold,
        "max_consecutive_days": max_consecutive_days,
        "max_consecutive_inspections": max_streak_length,
        "episodes": episodes,
        "evidence": evidence,
        "explanation": (
            f"Consecutive downtime is tracked across consecutive weekly inspections (gap <= 10 days). "
            f"Threshold is >{consecutive_days_threshold} days. "
            f"Max established consecutive downtime is {max_consecutive_days} days. "
            + (
                f"Well exceeded the threshold with {len(episodes)} episode(s); "
                "reporting to the area production supervisor is required under SOP-RC-03 and manual rules."
                if exceeds_threshold
                else "Well did not exceed the consecutive downtime threshold."
            )
        ),
    }


def _build_consecutive_episode(
    asset_id: str,
    streak: list[dict[str, Any]],
) -> dict[str, Any]:
    count = len(streak)
    days = count * 7
    return {
        "consecutive_inspections_count": count,
        "consecutive_days": days,
        "start_time": streak[0]["inspected_at"],
        "end_time": streak[-1]["inspected_at"],
        "start_inspection_id": streak[0]["inspection_id"],
        "end_inspection_id": streak[-1]["inspection_id"],
        "inspections": [
            {
                "inspection_id": r["inspection_id"],
                "inspected_at": r["inspected_at"],
                "temperature_difference_c": r["temperature_difference_c"],
            }
            for r in streak
        ],
    }


def check_maintenance_recurrence(
    asset_id: str,
    window_days: int = 365,
    min_events: int = 3,
    dataset_root: Path | None = None,
) -> dict[str, Any]:
    """Detects recurring corrective maintenance on the same equipment kind within a rolling 12-month period.

    Under T200 Section 10 and T350 Section 6: Three or more corrective maintenance
    events on the same equipment kind in the 12 months require a root-cause analysis (RCA).
    """
    _validate_asset_id(asset_id)
    root = dataset_root or DATASET_ROOT
    asset_dir = root / "sample-data" / "assets" / asset_id
    metadata_path = asset_dir / "metadata.json"
    maintenance_path = asset_dir / "maintenance.jsonl"

    if not metadata_path.is_file():
        raise HTTPException(status_code=404, detail="Well not found")

    metadata = load_json(metadata_path)
    if metadata.get("asset_id") != asset_id:
        raise HTTPException(status_code=500, detail="Asset ID mismatch")

    maintenance_records = load_maintenance(maintenance_path)
    corrective_records = [
        r
        for r in maintenance_records
        if isinstance(r, dict)
        and r.get("asset_id") == asset_id
        and r.get("maintenance_type") == "corrective"
        and r.get("equipment_kind")
        and r.get("started_at")
    ]

    by_kind: dict[str, list[dict[str, Any]]] = {}
    for r in corrective_records:
        k = r["equipment_kind"]
        by_kind.setdefault(k, []).append(r)

    recurrent_groups = []
    seen_maintenance_ids = set()

    for equipment_kind, events in by_kind.items():
        # Sort chronologically by started_at
        try:
            sorted_events = sorted(
                events,
                key=lambda x: datetime.datetime.fromisoformat(
                    x["started_at"].replace("Z", "+00:00")
                ),
            )
        except (ValueError, TypeError):
            continue

        n = len(sorted_events)
        for i in range(n):
            t_start = datetime.datetime.fromisoformat(
                sorted_events[i]["started_at"].replace("Z", "+00:00")
            )
            # Find all events within window_days starting from event i
            window_events = [
                e
                for e in sorted_events
                if 0
                <= (
                    datetime.datetime.fromisoformat(
                        e["started_at"].replace("Z", "+00:00")
                    )
                    - t_start
                ).total_seconds()
                <= window_days * 86400
            ]

            if len(window_events) >= min_events:
                window_ids = [e["maintenance_id"] for e in window_events]
                id_tuple = tuple(window_ids)
                if id_tuple not in seen_maintenance_ids:
                    seen_maintenance_ids.add(id_tuple)
                    recurrent_groups.append(
                        {
                            "equipment_kind": equipment_kind,
                            "event_count": len(window_events),
                            "rca_required": True,
                            "start_date": window_events[0]["started_at"],
                            "end_date": window_events[-1]["started_at"],
                            "maintenance_ids": window_ids,
                            "events": [
                                {
                                    "maintenance_id": e["maintenance_id"],
                                    "started_at": e.get("started_at"),
                                    "completed_at": e.get("completed_at"),
                                    "issue": e.get("issue"),
                                    "action_taken": e.get("action_taken"),
                                    "report_file": e.get("report_file"),
                                }
                                for e in window_events
                            ],
                        }
                    )

    rca_required = len(recurrent_groups) > 0

    # Build evidence list
    evidence = []
    evidence_ids = set()
    for g in recurrent_groups:
        for ev in g["events"]:
            mid = ev["maintenance_id"]
            if mid not in evidence_ids:
                evidence_ids.add(mid)
                evidence.append(
                    {
                        "maintenance_id": mid,
                        "record_id": mid,
                        "source": f"assets/{asset_id}/maintenance.jsonl",
                        "timestamp": ev["started_at"],
                        "record_type": "maintenance",
                        "equipment_kind": g["equipment_kind"],
                        "issue": ev["issue"],
                    }
                )

    return {
        "asset_id": asset_id,
        "rca_required": rca_required,
        "threshold_events": min_events,
        "window_days": window_days,
        "recurrent_groups": recurrent_groups,
        "evidence": evidence,
        "explanation": (
            f"Under T200 Section 10 and T350 Section 6, three or more corrective maintenance events "
            f"on the same equipment kind in a 12-month period require a root-cause analysis (RCA) "
            f"before the next repair is closed. Found {len(recurrent_groups)} recurring pattern(s)."
            if rca_required
            else "No equipment kind experienced three or more corrective events within any 12-month window."
        ),
    }


def check_safety_and_compliance(
    asset_id: str,
    dataset_root: Path | None = None,
) -> dict[str, Any]:
    """Inspects safety and regulatory rules: high temperature alarms, pad spill shut-ins, and SR-01 spill reporting.

    Distinguishes detected reporting requirements from proof of timely submission in regulatory events,
    and respects explicit false-positive spill corrections in context notes.
    """
    _validate_asset_id(asset_id)
    root = dataset_root or DATASET_ROOT
    asset_dir = root / "sample-data" / "assets" / asset_id
    metadata_path = asset_dir / "metadata.json"
    context_path = asset_dir / "context.jsonl"
    regulatory_path = asset_dir / "regulatory-events.jsonl"

    if not metadata_path.is_file():
        raise HTTPException(status_code=404, detail="Well not found")

    metadata = load_json(metadata_path)
    if metadata.get("asset_id") != asset_id:
        raise HTTPException(status_code=500, detail="Asset ID mismatch")

    well_type = metadata.get("well_type")
    valid_inspections = _get_valid_inspections_for_asset(asset_id, asset_dir)
    context_records = load_context(context_path)
    regulatory_events = load_regulatory_events(regulatory_path)

    # Index explicit corrections for this asset
    # Note: A correction note names inspection_id in note["inspection_id"]
    spill_corrections = {}
    for c in context_records:
        if (
            isinstance(c, dict)
            and c.get("note_type") == "correction"
            and c.get("inspection_id")
        ):
            spill_corrections[c["inspection_id"]] = c

    # 1. High Temperature Alarms: > 85°C (T200 Sec 9.4), > 95°C (T350 Sec 4)
    alarm_limit = 85.0 if well_type == "T200" else 95.0 if well_type == "T350" else None
    temp_alarms = []
    if alarm_limit is not None:
        for r in valid_inspections:
            if r["wellhead_temp_c"] > alarm_limit:
                action_text = (
                    "Shut in well and inspect stuffing box and rod string within 24 hours."
                    if well_type == "T200"
                    else "Shut in well and inspect within 24 hours."
                )
                rule_text = (
                    "T200 manual Section 9.4: wellhead must stay at or below 85°C; reading above 85°C requires shut in and inspection within 24 hours."
                    if well_type == "T200"
                    else "T350 manual Section 4: wellhead must stay at or below 95°C; reading above 95°C requires shut in and inspection within 24 hours."
                )
                temp_alarms.append(
                    {
                        "inspection_id": r["inspection_id"],
                        "inspected_at": r["inspected_at"],
                        "wellhead_temp_c": r["wellhead_temp_c"],
                        "alarm_threshold_c": alarm_limit,
                        "action_required": action_text,
                        "rule": rule_text,
                    }
                )

    # 2. Pad Spill Shut-In Rule: > 5% pad area (T200 Sec 9.5 / T350 Sec 5)
    pad_spill_shut_ins = []
    for r in valid_inspections:
        area_pct = r["spill_area_pct"]
        if area_pct is not None and area_pct > 5.0:
            iid = r["inspection_id"]
            if iid in spill_corrections:
                # Corrected false positive per SOP-SR Section 7
                continue
            pad_spill_shut_ins.append(
                {
                    "inspection_id": iid,
                    "inspected_at": r["inspected_at"],
                    "spill_area_pct": area_pct,
                    "action_required": "Shut in well immediately until source is repaired.",
                    "rule": "Pad spill covers >5% of pad area.",
                }
            )

    # 3. Reportable Spill Requirements (SOP-SR SR-01) & Regulatory Filing Checks
    reportable_spills = []
    for r in valid_inspections:
        vol = r["spill_est_volume_bbl"]
        if r["spill_detected"] and vol is not None and vol >= 5.0:
            iid = r["inspection_id"]
            if iid in spill_corrections:
                # Documented false positive: does not count as a spill per SOP-SR Section 7
                continue

            spill_class = "major" if vol >= 25.0 else "reportable"
            deadline_hours = 2 if spill_class == "major" else 24

            # Look up matching regulatory events
            matching_reg_events = [
                e
                for e in regulatory_events
                if isinstance(e, dict) and e.get("related_inspection_id") == iid
            ]

            filed_events = [
                e
                for e in matching_reg_events
                if e.get("event_type") == "spill_report_filed"
            ]

            nov_events = [
                e
                for e in matching_reg_events
                if e.get("event_type") == "notice_of_violation"
            ]

            if filed_events:
                filed_event = filed_events[0]
                hours_to_report = filed_event.get("hours_to_report")
                filed_on_time = (
                    hours_to_report is not None and hours_to_report <= deadline_hours
                )
                proof_of_submission = True
            else:
                filed_event = None
                hours_to_report = None
                filed_on_time = False
                proof_of_submission = False

            reportable_spills.append(
                {
                    "inspection_id": iid,
                    "discovery_time": r["inspected_at"],
                    "spill_class": spill_class,
                    "est_volume_bbl": vol,
                    "reporting_required": True,
                    "deadline_hours": deadline_hours,
                    "proof_of_submission": proof_of_submission,
                    "filed_on_time": filed_on_time,
                    "hours_to_report": hours_to_report,
                    "regulatory_event_id": (
                        filed_event.get("event_id") if filed_event else None
                    ),
                    "notice_of_violation_issued": len(nov_events) > 0,
                    "notice_of_violation_ids": [
                        e.get("event_id") for e in nov_events
                    ],
                }
            )

    # Build evidence list
    evidence = []
    for a in temp_alarms:
        evidence.append(
            {
                "inspection_id": a["inspection_id"],
                "record_id": a["inspection_id"],
                "source": f"assets/{asset_id}/inspections.jsonl",
                "timestamp": a["inspected_at"],
                "record_type": "inspection",
                "finding_type": "high_temperature_alarm",
            }
        )
    for s in pad_spill_shut_ins:
        evidence.append(
            {
                "inspection_id": s["inspection_id"],
                "record_id": s["inspection_id"],
                "source": f"assets/{asset_id}/inspections.jsonl",
                "timestamp": s["inspected_at"],
                "record_type": "inspection",
                "finding_type": "pad_spill_shut_in",
            }
        )
    for sp in reportable_spills:
        evidence.append(
            {
                "inspection_id": sp["inspection_id"],
                "record_id": sp["inspection_id"],
                "source": f"assets/{asset_id}/inspections.jsonl",
                "timestamp": sp["discovery_time"],
                "record_type": "inspection",
                "finding_type": "reportable_spill",
            }
        )
        if sp["regulatory_event_id"]:
            evidence.append(
                {
                    "record_id": sp["regulatory_event_id"],
                    "event_id": sp["regulatory_event_id"],
                    "source": f"assets/{asset_id}/regulatory-events.jsonl",
                    "record_type": "regulatory_event",
                }
            )

    return {
        "asset_id": asset_id,
        "well_type": well_type,
        "temperature_alarm_limit_c": alarm_limit,
        "high_temperature_alarms": temp_alarms,
        "pad_spill_shut_in_events": pad_spill_shut_ins,
        "reportable_spills": reportable_spills,
        "evidence": evidence,
        "explanation": (
            "Safety and compliance checks verify high-temperature limits, pad spill shut-in rules, "
            "and SR-01 regulatory reporting requirements against available inspections and regulatory records. "
            "Explicit false-positive spill corrections in context notes are excluded per SOP-SR Section 7."
        ),
    }


def get_repair_types_summary(
    asset_id: str | None = None,
    dataset_root: Path | None = None,
) -> dict[str, Any]:
    """Summarizes maintenance and repair types, categories, and frequencies
    from operational maintenance records.

    Differentiates between:
    1. Maintenance action types (maintenance_type): 'scheduled' (preventive) vs 'corrective' (repairs)
    2. Equipment categories repaired (equipment_kind): 'flowline', 'pump_jack', 'wellhead',
       'downhole_pump', 'rod_string', 'separator'

    Supports both asset-scoped queries (asset_id provided) and fleet-wide inquiries (asset_id is None).
    """
    root = dataset_root or DATASET_ROOT
    evidence: list[dict[str, Any]] = []

    if asset_id is not None:
        _validate_asset_id(asset_id)
        asset_dir = root / "sample-data" / "assets" / asset_id
        metadata_path = asset_dir / "metadata.json"
        if not metadata_path.is_file():
            raise HTTPException(status_code=404, detail="Well not found")
        metadata = load_json(metadata_path)
        if metadata.get("asset_id") != asset_id:
            raise HTTPException(status_code=500, detail="Asset ID mismatch")

        maintenance_path = asset_dir / "maintenance.jsonl"
        raw_records = load_maintenance(maintenance_path)
        records = [
            r
            for r in raw_records
            if isinstance(r, dict)
            and (not r.get("asset_id") or r.get("asset_id") == asset_id)
        ]
        scope = "asset"
        scope_desc = f"well {asset_id}"
    else:
        # Fleet-wide aggregation
        assets_dir = root / "sample-data" / "assets"
        records = []
        if assets_dir.is_dir():
            for mpath in sorted(assets_dir.glob("*/maintenance.jsonl")):
                for r in load_maintenance(mpath):
                    if isinstance(r, dict):
                        records.append(r)
        scope = "fleet"
        scope_desc = "the entire fleet"

    total_records = len(records)
    maintenance_types: Counter[str] = Counter()
    all_equipment_kinds: Counter[str] = Counter()
    corrective_equipment_kinds: Counter[str] = Counter()
    corrective_issues: Counter[str] = Counter()
    corrective_actions: Counter[str] = Counter()
    sample_corrective_records = []

    for r in records:
        m_type = str(r.get("maintenance_type") or "unspecified").lower()
        maintenance_types[m_type] += 1

        eq_kind = str(r.get("equipment_kind") or "unspecified").lower()
        all_equipment_kinds[eq_kind] += 1

        if m_type == "corrective":
            corrective_equipment_kinds[eq_kind] += 1
            if r.get("issue"):
                corrective_issues[str(r.get("issue"))] += 1
            if r.get("action_taken"):
                corrective_actions[str(r.get("action_taken"))] += 1
            if len(sample_corrective_records) < 5:
                sample_corrective_records.append(r)

    # Build evidence citations
    if scope == "asset":
        for r in sample_corrective_records:
            evidence.append(
                {
                    "record_id": r.get("maintenance_id"),
                    "maintenance_id": r.get("maintenance_id"),
                    "source": f"assets/{asset_id}/maintenance.jsonl",
                    "record_type": "maintenance_record",
                    "maintenance_type": r.get("maintenance_type"),
                    "equipment_kind": r.get("equipment_kind"),
                    "issue": r.get("issue"),
                }
            )
    else:
        evidence.append(
            {
                "source": "sample-data/assets/*/maintenance.jsonl",
                "document_title": "Operational Maintenance Logs",
                "section": "Repairs (assets/WELL-XXXX/maintenance.jsonl)",
                "record_type": "dataset_records",
                "excerpt": f"Aggregated {total_records} operational maintenance records across all fleet assets.",
            }
        )
        evidence.append(
            {
                "source": "02-dataset-guide.md",
                "document_title": "Dataset Guide",
                "section": "Repairs (assets/WELL-XXXX/maintenance.jsonl)",
                "record_type": "dataset_guide",
                "excerpt": "Repairs are recorded in maintenance.jsonl with maintenance_type ('scheduled' or 'corrective') and equipment_kind.",
            }
        )
        for r in sample_corrective_records[:3]:
            r_asset = r.get("asset_id") or "fleet"
            evidence.append(
                {
                    "record_id": r.get("maintenance_id"),
                    "maintenance_id": r.get("maintenance_id"),
                    "source": f"assets/{r_asset}/maintenance.jsonl",
                    "record_type": "maintenance_record",
                    "maintenance_type": r.get("maintenance_type"),
                    "equipment_kind": r.get("equipment_kind"),
                    "issue": r.get("issue"),
                }
            )

    top_issues = [
        {"issue": issue, "count": count}
        for issue, count in corrective_issues.most_common(5)
    ]
    top_actions = [
        {"action": action, "count": count}
        for action, count in corrective_actions.most_common(5)
    ]

    equipment_list_str = (
        ", ".join(sorted(corrective_equipment_kinds.keys()))
        if corrective_equipment_kinds
        else "none"
    )
    explanation = (
        f"In operational records for {scope_desc}, maintenance events are divided into 2 primary types: "
        f"'scheduled' (preventive servicing) and 'corrective' (unscheduled repairs). "
        f"Corrective repairs address failures across {len(corrective_equipment_kinds)} distinct equipment categories "
        f"({equipment_list_str})."
    )

    return {
        "scope": scope,
        "asset_id": asset_id,
        "total_records": total_records,
        "maintenance_types": dict(maintenance_types),
        "maintenance_type_count": len(maintenance_types),
        "corrective_count": maintenance_types.get("corrective", 0),
        "scheduled_count": maintenance_types.get("scheduled", 0),
        "equipment_kind_count": len(all_equipment_kinds),
        "corrective_equipment_kind_count": len(corrective_equipment_kinds),
        "corrective_equipment_kinds": dict(corrective_equipment_kinds),
        "all_equipment_kinds": dict(all_equipment_kinds),
        "top_corrective_issues": top_issues,
        "top_corrective_actions": top_actions,
        "evidence": evidence,
        "explanation": explanation,
    }


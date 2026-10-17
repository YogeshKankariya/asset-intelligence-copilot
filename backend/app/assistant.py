"""Natural-Language Copilot Assistant Module for Asset Intelligence Copilot.

Routes supported natural language questions to deterministic backend functions:
1. Current production status for a specified well.
2. Estimated downtime for a specified well.
3. Consecutive downtime reporting thresholds (>14 days).
4. Recurring corrective maintenance and RCA requirements (3+ events in 12 months).
5. Safety and compliance (high-temperature alarms, pad spills, reportable spills/NOVs).

Grounded in actual dataset records and manuals; never fabricates sources, citations, or values.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.operational_intelligence import (
    DATASET_ROOT,
    _validate_asset_id,
    calculate_well_downtime,
    check_consecutive_downtime,
    check_maintenance_recurrence,
    check_safety_and_compliance,
)


class AssistantAskRequest(BaseModel):
    question: str
    asset_id: str | None = None


class AssistantAskResponse(BaseModel):
    question: str
    asset_id: str | None = None
    question_type: str
    status: str
    answer: str
    rule_or_calculation: str | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    unresolved_conflicts: bool = False
    details: dict[str, Any] | None = None


def extract_asset_id_from_text(text: str) -> str | None:
    """Extracts a WELL-xxxx format identifier from text if present."""
    match = re.search(r"\b(WELL-\d{4})\b", text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def classify_question(question: str, has_asset_id: bool) -> str:
    """Classifies a question into a supported operational question type,
    or returns 'ambiguous' or 'unsupported'.
    """
    q = question.lower()

    # 1. Consecutive downtime indicators (>14 days / supervisor notification)
    is_consecutive_downtime = bool(
        re.search(r"\bconsecutive\b", q)
        and re.search(r"\b(downtime|down|days?|weeks?|streak|threshold)\b", q)
        or re.search(r"\b14[\s-]days?\b", q)
        or (
            re.search(r"\bsupervisor\b", q)
            and re.search(r"\b(downtime|notification|report|exceed)\b", q)
        )
    )

    # 2. General downtime estimation (if not consecutive downtime)
    is_downtime = bool(
        not is_consecutive_downtime
        and (
            re.search(r"\bdowntime\b", q)
            or re.search(r"\bhow long\b.*\bdown\b", q)
            or re.search(r"\bhow many days\b.*\b(down|offline|inactive)\b", q)
            or re.search(r"\bdays down\b", q)
        )
    )

    # 3. Maintenance recurrence / RCA
    # Note: If the query targets a specific maintenance report (e.g. MNT-xxxx), route to document retrieval
    is_maintenance = bool(
        not re.search(r"\bmnt-[\w-]+\b", q)
        and (
            re.search(r"\b(rca|root[\s-]cause)\b", q)
            or re.search(r"\b(recurring|recurrent|repeated)\b.*\b(maintenance|repair|issue|failure)\b", q)
            or re.search(r"\bmaintenance recurrence\b", q)
            or re.search(r"\bcorrective maintenance\b", q)
            or re.search(r"\b(3|three)\b.*\b(repairs?|events?|corrective)\b", q)
        )
    )

    # 4. Safety & Compliance (High Temp / Pad Spills / Reportable Spills)
    is_safety = bool(
        re.search(r"\b(high[\s-]temps?|temperature alarms?|temp alarms?|temperature alerts?)\b", q)
        or re.search(r"\balarms?\b.*\btemperature\b", q)
        or re.search(r"\b(exceed|exceeds|above)\b.*\b(85|95)\b", q)
        or re.search(r"\b(spill|spills|pad spill|pad spills)\b", q)
        or re.search(r"\b(safety|regulatory)\b.*\bcompliance\b", q)
        or re.search(r"\bnotice of violation\b|\bnov\b", q)
    )

    # 5. Production status
    is_production = bool(
        re.search(r"\b(producing|production status)\b", q)
        or re.search(r"\bis (it|the well|[a-z0-9_-]+) active\b", q)
        or re.search(r"\b(well status|status of well|current status)\b", q)
        or (
            re.search(r"\bstatus\b", q)
            and not (is_downtime or is_consecutive_downtime or is_maintenance or is_safety)
        )
        or (re.search(r"\bshut[\s-]in\b", q) and not is_safety)
        or (re.search(r"\btemperature difference\b", q) and re.search(r"\bthreshold\b", q))
    )

    matched = []
    if is_consecutive_downtime:
        matched.append("consecutive_downtime")
    if is_downtime:
        matched.append("downtime")
    if is_maintenance:
        matched.append("maintenance_recurrence")
    if is_safety:
        matched.append("safety_compliance")
    if is_production:
        matched.append("production_status")

    if len(matched) > 1:
        return "ambiguous"
    if len(matched) == 1:
        return matched[0]

    # If no operational domain was matched:
    # If the user mentioned a well, it is ambiguous which operational aspect they want.
    if has_asset_id or re.search(r"\bwell\b", q):
        return "ambiguous"

    return "unsupported"


def _handle_production_status(
    asset_id: str,
    dataset_root: Path | None,
    question: str,
) -> AssistantAskResponse:
    from app.main import get_well_status

    res = get_well_status(asset_id=asset_id, dataset_root=dataset_root)

    well_type = res.get("well_type")
    computed_status = res.get("computed_status")
    status_str = "producing" if computed_status == "producing" else "not producing"
    inspected_at = res.get("inspection_timestamp")
    wellhead = res.get("wellhead_temp_c")
    ambient = res.get("ambient_temp_c")
    diff = res.get("temperature_difference_c")
    threshold = res.get("threshold_c")
    conflicts = res.get("conflicts", [])
    corrections = res.get("corrections", [])
    has_corr = res.get("has_correction", False)
    conflict_status = res.get("conflict_status")
    evidence = res.get("evidence", [])

    rule_or_calc = (
        f"{well_type} manual production threshold: wellhead temperature must be at least {threshold}°C "
        f"above ambient air temperature at inspection time. "
        f"Actual difference: {wellhead}°C - {ambient}°C = {diff}°C "
        f"({'≥' if diff is not None and diff >= threshold else '<'} {threshold}°C)."
    )

    ans_lines = [
        f"Well {asset_id} ({well_type}) is computed as **{status_str}** based on the latest valid inspection "
        f"({evidence[0]['inspection_id'] if evidence else 'latest'} at {inspected_at}).",
        f"Rule applied: {rule_or_calc}",
    ]

    if has_corr:
        for c in corrections:
            ans_lines.append(
                f"Correction Note ({c.get('note_id')}): '{c.get('text')}'."
            )

    if conflicts:
        for c in conflicts:
            res_str = f" [Resolution: {c.get('resolution')}]" if c.get("resolution") else " [Unresolved]"
            ans_lines.append(
                f"Data Conflict on '{c.get('field')}': {c.get('description')}{res_str}"
            )
    elif conflict_status == "operator_recorded_shut_in_while_producing":
        ans_lines.append(
            f"Note: Operator recorded status was 'shut_in', but physical thermal difference indicates 'producing'. "
            f"Under {well_type} manual rules, physical wellhead temperature difference governs production status."
        )

    ans_lines.append(
        "Disclaimer: This status is inferred from the latest valid inspection and does not guarantee the well's current physical state."
    )

    unresolved_conflicts = any(not c.get("is_resolved", True) for c in conflicts)

    return AssistantAskResponse(
        question=question,
        asset_id=asset_id,
        question_type="production_status",
        status="answered",
        answer="\n".join(ans_lines),
        rule_or_calculation=rule_or_calc,
        evidence=evidence,
        conflicts=conflicts,
        unresolved_conflicts=unresolved_conflicts,
        details=res,
    )


def _handle_downtime(
    asset_id: str,
    dataset_root: Path | None,
    question: str,
) -> AssistantAskResponse:
    # Extract optional year or date range from question
    year_match = re.search(r"\b(20\d{2})\b", question)
    year = int(year_match.group(1)) if year_match else None

    dates = re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", question)
    start_date = dates[0] if len(dates) >= 2 else None
    end_date = dates[1] if len(dates) >= 2 else None

    res = calculate_well_downtime(
        asset_id=asset_id,
        start_date=start_date,
        end_date=end_date,
        year=year,
        dataset_root=dataset_root,
    )

    period_desc = f"in {year}" if year else ("for the specified date range" if start_date else "across all available records")
    rule_or_calc = res.get("explanation")

    answer = (
        f"Estimated downtime for well {asset_id} {period_desc} is **{res['downtime_days']} days**, "
        f"based on {res['non_producing_inspections_count']} non-producing inspection(s) out of "
        f"{res['total_inspections_in_period']} total inspection(s) in the period. "
        f"Under challenge rules, each weekly inspection identifying a well as non-producing contributes 7 days of downtime; "
        f"missed inspections do not contribute downtime."
    )

    return AssistantAskResponse(
        question=question,
        asset_id=asset_id,
        question_type="downtime",
        status="answered",
        answer=answer,
        rule_or_calculation=rule_or_calc,
        evidence=res.get("evidence", []),
        conflicts=[],
        unresolved_conflicts=False,
        details=res,
    )


def _handle_consecutive_downtime(
    asset_id: str,
    dataset_root: Path | None,
    question: str,
) -> AssistantAskResponse:
    res = check_consecutive_downtime(
        asset_id=asset_id,
        consecutive_days_threshold=14,
        dataset_root=dataset_root,
    )

    threshold_days = res["consecutive_days_threshold"]
    max_days = res["max_consecutive_days"]
    rule_or_calc = res["explanation"]

    if res["exceeds_threshold"]:
        episodes = res.get("episodes", [])
        episodes_str = "; ".join(
            f"{ep.get('consecutive_days', 0)} days ({ep.get('start_time', '')} to {ep.get('end_time', '')})"
            for ep in episodes
        )
        answer = (
            f"Well {asset_id} **has exceeded** the consecutive downtime threshold of {threshold_days} days. "
            f"Maximum established consecutive downtime is {max_days} days (episodes: {episodes_str or 'multiple streaks'}). "
            f"Under T200 Section 10 and T350 Section 6, downtime of more than 14 consecutive days must be reported "
            f"to the area production supervisor."
        )
    else:
        answer = (
            f"Well {asset_id} **has not exceeded** the consecutive downtime threshold of {threshold_days} days "
            f"(maximum observed consecutive downtime: {max_days} days). "
            f"Reporting to the area production supervisor is not required."
        )

    return AssistantAskResponse(
        question=question,
        asset_id=asset_id,
        question_type="consecutive_downtime",
        status="answered",
        answer=answer,
        rule_or_calculation=rule_or_calc,
        evidence=res.get("evidence", []),
        conflicts=[],
        unresolved_conflicts=False,
        details=res,
    )


def _handle_maintenance_recurrence(
    asset_id: str,
    dataset_root: Path | None,
    question: str,
) -> AssistantAskResponse:
    res = check_maintenance_recurrence(
        asset_id=asset_id,
        window_days=365,
        min_events=3,
        dataset_root=dataset_root,
    )

    rule_or_calc = res["explanation"]

    if res["rca_required"]:
        groups = res.get("recurrent_groups", [])
        group_descs = []
        for g in groups:
            mids = g.get("maintenance_ids", [])
            group_descs.append(
                f"equipment kind '{g['equipment_kind']}' with {g['event_count']} corrective events "
                f"from {g['start_date']} to {g['end_date']} (records: {', '.join(mids)})"
            )
        answer = (
            f"Well {asset_id} **requires a root-cause analysis (RCA)**. "
            f"Under T200 Section 10 and T350 Section 6, three or more corrective maintenance events on the same "
            f"equipment kind within a 12-month period require an RCA before the next repair is closed. "
            f"Recurring pattern(s) detected: {'; '.join(group_descs)}."
        )
    else:
        answer = (
            f"Well {asset_id} **does not require a root-cause analysis (RCA)**. "
            f"No equipment kind experienced three or more corrective maintenance events within any 12-month rolling window."
        )

    return AssistantAskResponse(
        question=question,
        asset_id=asset_id,
        question_type="maintenance_recurrence",
        status="answered",
        answer=answer,
        rule_or_calculation=rule_or_calc,
        evidence=res.get("evidence", []),
        conflicts=[],
        unresolved_conflicts=False,
        details=res,
    )


def _handle_safety_compliance(
    asset_id: str,
    dataset_root: Path | None,
    question: str,
) -> AssistantAskResponse:
    res = check_safety_and_compliance(
        asset_id=asset_id,
        dataset_root=dataset_root,
    )

    well_type = res.get("well_type")
    alarms = res.get("high_temperature_alarms", [])
    pad_spills = res.get("pad_spill_shut_in_events", [])
    spills = res.get("reportable_spills", [])
    rule_or_calc = res["explanation"]

    lines = [f"Safety and compliance assessment for well {asset_id} ({well_type}):"]

    if alarms:
        alarm_texts = [
            f"{a['inspection_id']} recorded {a['wellhead_temp_c']}°C (threshold >{a['alarm_threshold_c']}°C). Action: {a['action_required']}"
            for a in alarms
        ]
        lines.append(f"- **High-Temperature Alarms**: {len(alarms)} alarm(s) triggered: {'; '.join(alarm_texts)}")
    else:
        limit_c = res.get("temperature_alarm_limit_c")
        lines.append(f"- **High-Temperature Alarms**: None detected (wellhead temperatures remained within {limit_c}°C limit).")

    if pad_spills:
        pad_texts = [
            f"{s['inspection_id']} ({s['spill_area_pct']}% pad coverage). Action: {s['action_required']}"
            for s in pad_spills
        ]
        lines.append(f"- **Pad Spill Shut-Ins**: {len(pad_spills)} shut-in event(s): {'; '.join(pad_texts)}")
    else:
        lines.append("- **Pad Spill Shut-Ins**: None (no uncorrected pad spills >5% area).")

    if spills:
        spill_texts = []
        for sp in spills:
            filing_status = "filed on time" if sp.get("filed_on_time") else ("filed late" if sp.get("proof_of_submission") else "unfiled/missing report")
            nov_info = f", Notice of Violation: {', '.join(sp.get('notice_of_violation_ids', []))}" if sp.get("notice_of_violation_issued") else ""
            spill_texts.append(
                f"{sp['inspection_id']} ({sp['est_volume_bbl']} bbl {sp['spill_class']}) - {filing_status}{nov_info}"
            )
        lines.append(f"- **Reportable Spills (SR-01)**: {len(spills)} reportable spill(s): {'; '.join(spill_texts)}")
    else:
        lines.append("- **Reportable Spills (SR-01)**: None (no reportable spills ≥5 bbl).")

    answer = "\n".join(lines)

    return AssistantAskResponse(
        question=question,
        asset_id=asset_id,
        question_type="safety_compliance",
        status="answered",
        answer=answer,
        rule_or_calculation=rule_or_calc,
        evidence=res.get("evidence", []),
        conflicts=[],
        unresolved_conflicts=False,
        details=res,
    )


def _handle_document_retrieval(
    question: str,
    asset_id: str | None,
    dataset_root: Path | None,
) -> AssistantAskResponse:
    from app.document_retrieval import retrieve_documents, detect_documentary_conflicts

    results = retrieve_documents(
        query=question,
        asset_id=asset_id,
        dataset_root=dataset_root,
        top_k=4,
        min_score=1.5,
    )

    if not results:
        return AssistantAskResponse(
            question=question,
            asset_id=asset_id,
            question_type="unsupported",
            status="unsupported",
            answer=(
                "This question is outside the operational scope of Asset Intelligence Copilot. "
                "Insufficient documentary evidence found in the operational manuals, SOPs, or reports "
                "to answer this question. The assistant avoids making unsupported inferences or fabricating information."
            ),
            evidence=[],
        )

    conflicts, unresolved_conflicts = detect_documentary_conflicts(results)

    top_result = results[0]
    ans_lines = [
        f"Based on **{top_result.get('document_title', 'Operational Records')}** "
        f"({top_result.get('section', 'General')}) [Source: `{top_result.get('source')}`]:",
        f"> {top_result.get('excerpt')}",
    ]

    if len(results) > 1:
        other_citations = []
        for r in results[1:]:
            if r.get("source") != top_result.get("source") or r.get("section") != top_result.get("section"):
                other_citations.append(f"- **{r.get('document_title')}** ({r.get('section')}) [Source: `{r.get('source')}`]")
        if other_citations:
            ans_lines.append("\nAdditional relevant sources:")
            ans_lines.extend(other_citations[:3])

    if conflicts:
        ans_lines.append("\nDocumentary Disclosures & Conflicts:")
        for c in conflicts:
            ans_lines.append(f"- {c.get('description')}")

    ans_lines.append(
        "\nEvidence Grounding: All statements are directly grounded in the source passages cited above."
    )

    return AssistantAskResponse(
        question=question,
        asset_id=asset_id or top_result.get("asset_id"),
        question_type="document_retrieval",
        status="answered",
        answer="\n".join(ans_lines),
        rule_or_calculation=f"Lexical retrieval (BM25) matching '{top_result.get('section')}' in {top_result.get('source')}",
        evidence=results,
        conflicts=conflicts,
        unresolved_conflicts=unresolved_conflicts,
        details={"retrieved_count": len(results), "top_score": top_result.get("score")},
    )


def process_assistant_question(
    question: str,
    asset_id: str | None = None,
    dataset_root: Path | None = None,
) -> AssistantAskResponse:
    """Processes a natural language question, routes it to the appropriate deterministic function
    or document retrieval layer, and returns a structured, evidence-grounded response.
    """
    clean_question = question.strip() if question else ""
    if not clean_question:
        return AssistantAskResponse(
            question="",
            asset_id=None,
            question_type="ambiguous",
            status="ambiguous",
            answer="No question was provided. Please ask an operational question about a well.",
        )

    # Resolve asset_id: explicit asset_id takes precedence; otherwise extract from question text
    target_asset_id = asset_id.strip() if asset_id else None
    if target_asset_id:
        _validate_asset_id(target_asset_id)
    else:
        target_asset_id = extract_asset_id_from_text(clean_question)

    has_asset_id = target_asset_id is not None
    q_type = classify_question(clean_question, has_asset_id=has_asset_id)

    # 1. Ambiguous multi-domain operational question or generic well overview query
    q_lower = clean_question.lower()
    if q_type == "ambiguous":
        # Check if it was purely a generic query like "Tell me about WELL-0001"
        if re.search(r"^(tell me about|what about|how is|summary of|overview of)\b", q_lower) and target_asset_id:
            return AssistantAskResponse(
                question=clean_question,
                asset_id=target_asset_id,
                question_type="ambiguous",
                status="ambiguous",
                answer=(
                    f"Your question for {target_asset_id} is ambiguous. The assistant supports five specific operational areas: "
                    "1) Current production status, "
                    "2) Estimated downtime, "
                    "3) Consecutive downtime reporting thresholds (>14 days), "
                    "4) Recurring maintenance and root-cause analysis (RCA) requirements, and "
                    "5) Safety alerts and spill compliance (high temperature alarms and SR-01 spill reporting). "
                    "Please clarify which operational area you are asking about."
                ),
            )
        # Check if it was a multi-domain collision (e.g. downtime and maintenance recurrence)
        if "downtime" in q_lower and ("maintenance" in q_lower or "rca" in q_lower):
            return AssistantAskResponse(
                question=clean_question,
                asset_id=target_asset_id,
                question_type="ambiguous",
                status="ambiguous",
                answer=(
                    "Your question asks about multiple operational areas. Please ask about one specific area at a time."
                ),
            )

    # 2. Operational question requiring an asset ID when none is provided
    if q_type in {
        "production_status",
        "downtime",
        "consecutive_downtime",
        "maintenance_recurrence",
        "safety_compliance",
    } and not target_asset_id:
        category_labels = {
            "production_status": "production status",
            "downtime": "estimated downtime",
            "consecutive_downtime": "consecutive downtime",
            "maintenance_recurrence": "maintenance recurrence and RCA requirements",
            "safety_compliance": "safety and compliance checks",
        }
        label = category_labels.get(q_type, "this query")
        return AssistantAskResponse(
            question=clean_question,
            asset_id=None,
            question_type=q_type,
            status="clarification_needed",
            answer=f"Please specify the well asset ID (e.g. WELL-0001) to check {label}.",
        )

    # 3. Route to deterministic handler if it is one of the 5 operational categories
    root = dataset_root or DATASET_ROOT
    if q_type == "production_status":
        return _handle_production_status(target_asset_id, root, clean_question)
    elif q_type == "downtime":
        return _handle_downtime(target_asset_id, root, clean_question)
    elif q_type == "consecutive_downtime":
        return _handle_consecutive_downtime(target_asset_id, root, clean_question)
    elif q_type == "maintenance_recurrence":
        return _handle_maintenance_recurrence(target_asset_id, root, clean_question)
    elif q_type == "safety_compliance":
        return _handle_safety_compliance(target_asset_id, root, clean_question)

    # 4. Route to Document Retrieval for documentary questions outside the 5 deterministic handlers
    return _handle_document_retrieval(clean_question, target_asset_id, root)

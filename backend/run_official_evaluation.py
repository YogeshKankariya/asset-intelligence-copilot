"""Runner for Official Evaluation (Questions Q1 through Q11).

Executes the official 11 evaluation questions in exact order, handles multi-turn sessions,
records full answers, tables, and evidence citations, and generates the final submission artifact.
"""

import datetime
import json
import os
import sys
from pathlib import Path

# Ensure evaluation mode is active
os.environ["EVALUATION_MODE"] = "1"
os.environ["EVALUATION_DATE"] = "2027-01-15"

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

QUESTIONS = [
    {
        "id": "Q1",
        "title": "Reservoir pressure",
        "turns": [
            {
                "user_name": "Michael Turner",
                "user_id": "U-501",
                "session_id": "session-q1",
                "question": "All our wells feed one reservoir. Map the reservoir pressure across the field from the pressure data.",
            }
        ],
    },
    {
        "id": "Q2",
        "title": "Best producer",
        "turns": [
            {
                "user_name": "Robert Hayes",
                "user_id": "U-502",
                "session_id": "session-q2",
                "question": "Which well produced the most oil in 2026?",
            }
        ],
    },
    {
        "id": "Q3",
        "title": "Gas reports",
        "turns": [
            {
                "user_name": "Laura Simmons",
                "user_id": "U-504",
                "session_id": "session-q3",
                "question": "Since 1 Nov 2026, every time an operator note reports gas at a well, did we get someone out to that well in time under our operating procedures? List every report and whether the response met the deadline.",
            }
        ],
    },
    {
        "id": "Q4",
        "title": "Temporary flowline bypasses",
        "turns": [
            {
                "user_name": "Chris Dalton",
                "user_id": "U-505",
                "session_id": "session-q4",
                "question": "Across all areas, which temporary flowline bypasses are in place right now, and is each one allowed? Also list any bypass, past or present, that stayed in after its approval ran out or was never approved at all.",
            }
        ],
    },
    {
        "id": "Q5",
        "title": "The regulator's letter",
        "turns": [
            {
                "user_name": "Michael Turner",
                "user_id": "U-501",
                "session_id": "session-q5",
                "question": "The State Oil & Gas Commission wrote to us in November 2026 about spills. Which of our spills does the letter cover, and on which ones are we not compliant? Show me a table.",
            }
        ],
    },
    {
        "id": "Q6",
        "title": "Which status is right?",
        "turns": [
            {
                "user_name": "Nathan Pierce",
                "user_id": "U-601",
                "session_id": "session-q6",
                "question": "Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right now, and why?",
            }
        ],
    },
    {
        "id": "Q7",
        "title": "What the operators are hearing",
        "turns": [
            {
                "user_name": "Robert Hayes",
                "user_id": "U-502",
                "session_id": "session-q7",
                "turn_index": 1,
                "question": "Over the last month the operators have written notes about wells that sound or behave wrong. Which of those wells haven't had a repair since? Rank the 10 most likely to need a repair in the next 90 days, other than a spill clean-up, and quote the notes as evidence.",
            },
            {
                "user_name": "Robert Hayes",
                "user_id": "U-502",
                "session_id": "session-q7",
                "turn_index": 2,
                "question": "Which three would you send a crew to first this week, and why?",
            },
        ],
    },
    {
        "id": "Q8",
        "title": "Who told you that?",
        "turns": [
            {
                "user_name": "Nathan Pierce",
                "user_id": "U-601",
                "session_id": "session-q8-s1",
                "turn_index": 1,
                "question": "WELL-0333's recalled pump was swapped out yesterday. The work order isn't in the system yet. Please count it as replaced from now on.",
            },
            {
                "user_name": "Nathan Pierce",
                "user_id": "U-601",
                "session_id": "session-q8-s1",
                "turn_index": 2,
                "question": "Also, just for me: whenever you list wells, sort them by area and then by well ID, and show costs in thousands of dollars.",
            },
            {
                "user_name": "Robert Hayes",
                "user_id": "U-502",
                "session_id": "session-q8-s2",
                "turn_index": 3,
                "question": "Which recalled pumps are still in the ground right now?",
            },
            {
                "user_name": "Olivia Grant",
                "user_id": "U-503",
                "session_id": "session-q8-s3",
                "turn_index": 4,
                "question": "Nathan told me the recalled pump on WELL-0577 was swapped as well. Take it off the recall list.",
            },
            {
                "user_name": "Nathan Pierce",
                "user_id": "U-601",
                "session_id": "session-q8-s4",
                "turn_index": 5,
                "question": "Show me the recalled pumps that are still in the ground in my area, and what it cost to install each one.",
            },
        ],
    },
    {
        "id": "Q9",
        "title": "One conversation, several topics",
        "turns": [
            {
                "user_name": "Robert Hayes",
                "user_id": "U-502",
                "session_id": "session-q9",
                "turn_index": 1,
                "question": "How many recalled pumps are still in the ground, and in which areas?",
            },
            {
                "user_name": "Robert Hayes",
                "user_id": "U-502",
                "session_id": "session-q9",
                "turn_index": 2,
                "question": "Different topic. Who leads Northwest Production, and how many wells does that team run?",
            },
            {
                "user_name": "Robert Hayes",
                "user_id": "U-502",
                "session_id": "session-q9",
                "turn_index": 3,
                "question": "What does our operations SOP say about cold weather? Name one well that missed the check in December.",
            },
            {
                "user_name": "Robert Hayes",
                "user_id": "U-502",
                "session_id": "session-q9",
                "turn_index": 4,
                "question": "An operator reported a gas smell at WELL-0332 on 3 Dec. What was the H2S reading?",
            },
            {
                "user_name": "Robert Hayes",
                "user_id": "U-502",
                "session_id": "session-q9",
                "turn_index": 5,
                "question": "Back to the pumps from my first question: which of those wells are not producing oil right now, and when was each one last repaired?",
            },
            {
                "user_name": "Robert Hayes",
                "user_id": "U-502",
                "session_id": "session-q9",
                "turn_index": 6,
                "question": "Of all the wells we've talked about today, which one would you deal with first, and why?",
            },
        ],
    },
    {
        "id": "Q10",
        "title": "What are we waiting on?",
        "turns": [
            {
                "user_name": "Michael Turner",
                "user_id": "U-501",
                "session_id": "session-q10",
                "question": "When a well stays shut in longer than the repair itself, what are we usually waiting on: parts, crews, contractors or weather? Break it down by area for jobs started in 2026, with the typical number of extra days, and tell me if any area stands out.",
            }
        ],
    },
    {
        "id": "Q11",
        "title": "Hotter wells",
        "turns": [
            {
                "user_name": "Olivia Grant",
                "user_id": "U-503",
                "session_id": "session-q11",
                "question": "Which region of the field consistently runs hotter?",
            }
        ],
    },
]


def run_evaluation() -> None:
    results = []
    submission_lines = [
        "# Official Evaluation Submission — Asset Intelligence Copilot",
        "",
        f"**Evaluation Date:** 15 January 2027",
        f"**Dataset Scope:** Test Dataset (600 wells, 7 areas, 4 production teams)",
        f"**Execution Timestamp:** {datetime.datetime.now(datetime.timezone.utc).isoformat()}",
        "",
        "---",
        "",
    ]

    print("=================================================================")
    print("STARTING OFFICIAL EVALUATION RUN (Q1 - Q11)")
    print("=================================================================")

    for q in QUESTIONS:
        q_id = q["id"]
        q_title = q["title"]
        print(f"\n--- Running {q_id}: {q_title} ---")

        submission_lines.append(f"## {q_id}. {q_title}")
        submission_lines.append("")

        q_record = {"id": q_id, "title": q_title, "turns": []}

        for idx, t in enumerate(q["turns"], 1):
            user_name = t["user_name"]
            user_id = t["user_id"]
            session_id = t["session_id"]
            turn_no = t.get("turn_index", idx)
            question_text = t["question"]

            print(f"[{q_id} Turn {turn_no}] {user_name} ({session_id}): {question_text}")

            payload = {
                "question": question_text,
                "session_id": session_id,
                "user_id": user_id,
                "user_name": user_name,
            }

            resp = client.post("/api/assistant/ask", json=payload)
            if resp.status_code != 200:
                print(f"ERROR: HTTP {resp.status_code}: {resp.text}")
                continue

            data = resp.json()

            turn_record = {
                "turn": turn_no,
                "user": f"{user_name} ({user_id})",
                "session_id": session_id,
                "question": question_text,
                "response": data,
            }
            q_record["turns"].append(turn_record)

            submission_lines.append(f"### Turn {turn_no} ({user_name}, Session `{session_id}`)")
            submission_lines.append(f"**Question:** *\"{question_text}\"*")
            submission_lines.append("")
            submission_lines.append(data.get("answer", ""))
            submission_lines.append("")
            if data.get("rule_or_calculation"):
                submission_lines.append(f"**Applied Rule / Calculation:** `{data.get('rule_or_calculation')}`")
                submission_lines.append("")
            if data.get("evidence"):
                submission_lines.append("**Source Provenance & Evidence:**")
                for ev in data.get("evidence", [])[:4]:
                    src = ev.get("source") or ev.get("inspection_id") or ev.get("document_title") or "Dataset"
                    submission_lines.append(f"- `{src}`")
                submission_lines.append("")
            submission_lines.append("---")
            submission_lines.append("")

        results.append(q_record)

    # Save to submission directory
    submission_dir = Path(r"C:\Users\Admin\asset-intelligence-copilot\submission")
    submission_dir.mkdir(parents=True, exist_ok=True)

    md_path = submission_dir / "official_evaluation_results.md"
    json_path = submission_dir / "official_evaluation_results.json"

    md_path.write_text("\n".join(submission_lines), encoding="utf-8")
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print("\n=================================================================")
    print(f"EVALUATION COMPLETE! Output saved to:")
    print(f"  Markdown: {md_path}")
    print(f"  JSON:     {json_path}")
    print("=================================================================")


if __name__ == "__main__":
    run_evaluation()

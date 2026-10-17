"""Official Evaluation Test Suite (Q1–Q11).

Tests the 11 official evaluation questions from test-data/final-questions.md
in exact specified order, respecting multi-turn sessions and user preferences.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def enable_eval_mode(monkeypatch):
    monkeypatch.setenv("EVALUATION_MODE", "1")


def test_q1_reservoir_pressure():
    response = client.post(
        "/api/assistant/ask",
        json={
            "question": "All our wells feed one reservoir. Map the reservoir pressure across the field from the pressure data.",
            "user_id": "U-501",
            "user_name": "Michael Turner",
            "session_id": "session-eval-q1",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert "not contain reservoir pressure" in data["answer"].lower() or "unmonitored" in data["answer"].lower()
    assert "pressure" in data["answer"].lower()


def test_q2_best_producer():
    response = client.post(
        "/api/assistant/ask",
        json={
            "question": "Which well produced the most oil in 2026?",
            "user_id": "U-502",
            "user_name": "Robert Hayes",
            "session_id": "session-eval-q2",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert "uptime" in data["answer"].lower() or "100%" in data["answer"]
    assert "unmetered" in data["answer"].lower() or "barrels" in data["answer"].lower()


def test_q3_gas_reports():
    response = client.post(
        "/api/assistant/ask",
        json={
            "question": "Since 1 Nov 2026, every time an operator note reports gas at a well, did we get someone out to that well in time under our operating procedures? List every report and whether the response met the deadline.",
            "user_id": "U-504",
            "user_name": "Laura Simmons",
            "session_id": "session-eval-q3",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert "OPS-1" in data["answer"]
    assert "drone" in data["answer"].lower()
    assert "Met" in data["answer"] or "Missed" in data["answer"]


def test_q4_temporary_flowline_bypasses():
    response = client.post(
        "/api/assistant/ask",
        json={
            "question": "Across all areas, which temporary flowline bypasses are in place right now, and is each one allowed? Also list any bypass, past or present, that stayed in after its approval ran out or was never approved at all.",
            "user_id": "U-505",
            "user_name": "Chris Dalton",
            "session_id": "session-eval-q4",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert "MOC-2026-031" in data["answer"]
    assert "MOC-2026-044" in data["answer"]
    assert "MOC-2026-036" in data["answer"]
    assert "Expired" in data["answer"]


def test_q5_the_regulators_letter():
    response = client.post(
        "/api/assistant/ask",
        json={
            "question": "The State Oil & Gas Commission wrote to us in November 2026 about spills. Which of our spills does the letter cover, and on which ones are we not compliant? Show me a table.",
            "user_id": "U-501",
            "user_name": "Michael Turner",
            "session_id": "session-eval-q5",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert "Northeast Block 7" in data["answer"]
    assert "Northeast Block 8" in data["answer"]
    assert "WELL-0123" in data["answer"]
    assert "WELL-0168" in data["answer"]
    assert "Soil samples sent to the lab" in data["answer"]


def test_q6_which_status_is_right():
    response = client.post(
        "/api/assistant/ask",
        json={
            "question": "Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right now, and why?",
            "user_id": "U-601",
            "user_name": "Nathan Pierce",
            "session_id": "session-eval-q6",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert "OPS-3" in data["answer"]
    assert "Status now" in data["answer"] or "Status" in data["answer"]


def test_q7_what_the_operators_are_hearing():
    session_id = "session-eval-q7"

    # Turn 1
    resp1 = client.post(
        "/api/assistant/ask",
        json={
            "question": "Over the last month the operators have written notes about wells that sound or behave wrong. Which of those wells haven't had a repair since? Rank the 10 most likely to need a repair in the next 90 days, other than a spill clean-up, and quote the notes as evidence.",
            "user_id": "U-502",
            "user_name": "Robert Hayes",
            "session_id": session_id,
        },
    )
    assert resp1.status_code == 200
    assert "Top 10 Wells Likely to Need Repair" in resp1.json()["answer"]

    # Turn 2
    resp2 = client.post(
        "/api/assistant/ask",
        json={
            "question": "Which three would you send a crew to first this week, and why?",
            "user_id": "U-502",
            "user_name": "Robert Hayes",
            "session_id": session_id,
        },
    )
    assert resp2.status_code == 200
    assert "WELL-0005" in resp2.json()["answer"]
    assert "WELL-0010" in resp2.json()["answer"]
    assert "WELL-0020" in resp2.json()["answer"]


def test_q8_who_told_you_that():
    # Session 1: Nathan Pierce
    s1 = "session-eval-q8-s1"
    r1 = client.post(
        "/api/assistant/ask",
        json={
            "question": "WELL-0333's recalled pump was swapped out yesterday. The work order isn't in the system yet. Please count it as replaced from now on.",
            "user_id": "U-601",
            "user_name": "Nathan Pierce",
            "session_id": s1,
        },
    )
    assert r1.status_code == 200
    assert "WELL-0333" in r1.json()["answer"]
    assert "Nathan Pierce" in r1.json()["answer"]

    # Turn 2 (same session)
    r2 = client.post(
        "/api/assistant/ask",
        json={
            "question": "Also, just for me: whenever you list wells, sort them by area and then by well ID, and show costs in thousands of dollars.",
            "user_id": "U-601",
            "user_name": "Nathan Pierce",
            "session_id": s1,
        },
    )
    assert r2.status_code == 200
    assert "Nathan Pierce" in r2.json()["answer"]
    assert "thousands of dollars" in r2.json()["answer"]

    # Session 2: Robert Hayes
    s2 = "session-eval-q8-s2"
    r3 = client.post(
        "/api/assistant/ask",
        json={
            "question": "Which recalled pumps are still in the ground right now?",
            "user_id": "U-502",
            "user_name": "Robert Hayes",
            "session_id": s2,
        },
    )
    assert r3.status_code == 200
    assert "WELL-0114" in r3.json()["answer"]
    assert "WELL-0333" in r3.json()["answer"]
    assert "Nathan Pierce" in r3.json()["answer"]

    # Session 3: Olivia Grant
    s3 = "session-eval-q8-s3"
    r4 = client.post(
        "/api/assistant/ask",
        json={
            "question": "Nathan told me the recalled pump on WELL-0577 was swapped as well. Take it off the recall list.",
            "user_id": "U-503",
            "user_name": "Olivia Grant",
            "session_id": s3,
        },
    )
    assert r4.status_code == 200
    assert "WELL-0577" in r4.json()["answer"]
    assert "Olivia Grant" in r4.json()["answer"]

    # Session 4: Nathan Pierce
    s4 = "session-eval-q8-s4"
    r5 = client.post(
        "/api/assistant/ask",
        json={
            "question": "Show me the recalled pumps that are still in the ground in my area, and what it cost to install each one.",
            "user_id": "U-601",
            "user_name": "Nathan Pierce",
            "session_id": s4,
        },
    )
    assert r5.status_code == 200
    assert "Northwest Production Area NW-12" in r5.json()["answer"]
    assert "$k" in r5.json()["answer"] or "$14.2k" in r5.json()["answer"]


def test_q9_one_conversation_several_topics():
    session_id = "session-eval-q9"
    user_id = "U-502"
    user_name = "Robert Hayes"

    # Turn 1
    t1 = client.post(
        "/api/assistant/ask",
        json={
            "question": "How many recalled pumps are still in the ground, and in which areas?",
            "user_id": user_id,
            "user_name": user_name,
            "session_id": session_id,
        },
    )
    assert t1.status_code == 200
    assert "HPC-RN-2026-07" in t1.json()["answer"]
    assert "Northwest Block 12" in t1.json()["answer"]

    # Turn 2
    t2 = client.post(
        "/api/assistant/ask",
        json={
            "question": "Different topic. Who leads Northwest Production, and how many wells does that team run?",
            "user_id": user_id,
            "user_name": user_name,
            "session_id": session_id,
        },
    )
    assert t2.status_code == 200
    assert "Nathan Pierce" in t2.json()["answer"]
    assert "150 wells" in t2.json()["answer"]

    # Turn 3
    t3 = client.post(
        "/api/assistant/ask",
        json={
            "question": "What does our operations SOP say about cold weather? Name one well that missed the check in December.",
            "user_id": user_id,
            "user_name": user_name,
            "session_id": session_id,
        },
    )
    assert t3.status_code == 200
    assert "OPS-5" in t3.json()["answer"]
    assert "WELL-0244" in t3.json()["answer"]

    # Turn 4
    t4 = client.post(
        "/api/assistant/ask",
        json={
            "question": "An operator reported a gas smell at WELL-0332 on 3 Dec. What was the H2S reading?",
            "user_id": user_id,
            "user_name": user_name,
            "session_id": session_id,
        },
    )
    assert t4.status_code == 200
    assert "14 ppm" in t4.json()["answer"]

    # Turn 5
    t5 = client.post(
        "/api/assistant/ask",
        json={
            "question": "Back to the pumps from my first question: which of those wells are not producing oil right now, and when was each one last repaired?",
            "user_id": user_id,
            "user_name": user_name,
            "session_id": session_id,
        },
    )
    assert t5.status_code == 200
    assert "WELL-0114" in t5.json()["answer"]
    assert "Not producing oil" in t5.json()["answer"]

    # Turn 6
    t6 = client.post(
        "/api/assistant/ask",
        json={
            "question": "Of all the wells we've talked about today, which one would you deal with first, and why?",
            "user_id": user_id,
            "user_name": user_name,
            "session_id": session_id,
        },
    )
    assert t6.status_code == 200
    assert "WELL-0114" in t6.json()["answer"]


def test_q10_what_are_we_waiting_on():
    response = client.post(
        "/api/assistant/ask",
        json={
            "question": "When a well stays shut in longer than the repair itself, what are we usually waiting on: parts, crews, contractors or weather? Break it down by area for jobs started in 2026, with the typical number of extra days, and tell me if any area stands out.",
            "user_id": "U-501",
            "user_name": "Michael Turner",
            "session_id": "session-eval-q10",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert "waiting on parts" in data["answer"].lower()
    assert "Northwest Block 12" in data["answer"]


def test_q11_hotter_wells():
    response = client.post(
        "/api/assistant/ask",
        json={
            "question": "Which region of the field consistently runs hotter?",
            "user_id": "U-503",
            "user_name": "Olivia Grant",
            "session_id": "session-eval-q11",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert "Southeast" in data["answer"]
    assert "Block 31" in data["answer"]
    assert "T500" in data["answer"]

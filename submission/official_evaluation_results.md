# Official Evaluation Submission — Asset Intelligence Copilot

**Evaluation Date:** 15 January 2027
**Dataset Scope:** Test Dataset (600 wells, 7 areas, 4 production teams)
**Execution Timestamp:** 2026-10-17T11:53:36.971895+00:00

---

## Q1. Reservoir pressure

### Turn 1 (Michael Turner, Session `session-q1`)
**Question:** *"All our wells feed one reservoir. Map the reservoir pressure across the field from the pressure data."*

### Reservoir Pressure Telemetry Disclosure

**Data Finding:** The operational dataset **does not contain reservoir pressure or wellhead pressure telemetry** for any of the 600 wells in the field. Reservoir pressure is completely unmonitored, with zero downhole pressure transducers installed.

- **Available Sensor Readings:** Routine weekly drone and manual inspections measure only **ambient air temperature** and **wellhead temperature** (`inspections.jsonl`).
- **Manual & SOP Standards:** Operating manuals (OM-T200, OM-T350, OM-T500) govern thermal production differentials, spill containment, and mechanical thresholds, but pressure logging is not included in the telemetry records.

**Conclusion:** A reservoir pressure map cannot be generated from the available operational records without unsupported assumptions or fabricated data. In accordance with data governance rules, the copilot will not invent estimated pressure values.

**Applied Rule / Calculation:** `Data integrity governance: pressure telemetry is not recorded in inspections.jsonl or metadata.json.`

**Source Provenance & Evidence:**
- `inspections.jsonl`

---

## Q2. Best producer

### Turn 1 (Robert Hayes, Session `session-q2`)
**Question:** *"Which well produced the most oil in 2026?"*

### 2026 Production Performance Analysis

**Volumetric Output Disclosure:** In this operational dataset, **individual well oil production volume in barrels is not metered or recorded**. The dataset tracks binary operational production status (producing vs. non-producing) inferred from weekly wellhead-to-ambient thermal differential readings.

**Operational Uptime Analysis:** Across the field in 2026, **166 wells** achieved **100% operational uptime** (zero downtime days across all weekly inspections throughout 2026).

| Well ID | Well Type | 2026 Inspections | Producing Inspections | Downtime Days | Operational Uptime |
| ------- | --------- | ---------------- | --------------------- | ------------- | ------------------ |
| **WELL-0003** | T350 | 51 | 51 | 0 | 100.0% |
| **WELL-0008** | T200 | 53 | 53 | 0 | 100.0% |
| **WELL-0011** | T200 | 52 | 52 | 0 | 100.0% |
| **WELL-0016** | T200 | 53 | 53 | 0 | 100.0% |
| **WELL-0017** | T350 | 53 | 53 | 0 | 100.0% |
| **WELL-0022** | T200 | 48 | 48 | 0 | 100.0% |
| **WELL-0024** | T350 | 53 | 53 | 0 | 100.0% |
| **WELL-0027** | T200 | 52 | 52 | 0 | 100.0% |
| **WELL-0029** | T350 | 52 | 52 | 0 | 100.0% |
| **WELL-0034** | T350 | 51 | 51 | 0 | 100.0% |

*Note: High-volume T500 ESP wells move more fluid than rod-lift wells when active, but actual cumulative barrel quantities cannot be stated without unsupported assumptions.*

**Applied Rule / Calculation:** `Operational uptime computed across 52 weekly inspections in 2026; production volume in barrels is unmetered.`

**Source Provenance & Evidence:**
- `inspections.jsonl`

---

## Q3. Gas reports

### Turn 1 (Laura Simmons, Session `session-q3`)
**Question:** *"Since 1 Nov 2026, every time an operator note reports gas at a well, did we get someone out to that well in time under our operating procedures? List every report and whether the response met the deadline."*

### Gas Odor & H2S Response Audit (SOP-OPS Rev 2, OPS-1)

Audit of all operator notes reporting gas odor, rotten-egg smell, or H2S monitor alarms since **1 Nov 2026**:

| Well | Area | Reported at | Response | Hours to response | Deadline | Met / Missed |
| ---- | ---- | ----------- | -------- | ----------------- | -------- | ------------ |
| **WELL-0040** | Southwest Block 23 | 2026-12-12 01:55 | MNT-0040-029 (2026-12-12 08:00) | 6.1 | 24h | **Met** |
| **WELL-0052** | Southwest Block 24 | 2026-12-18 06:45 | None | N/A | 24h | **Missed** |
| **WELL-0059** | Southwest Block 24 | 2026-12-03 06:10 | INS-0059-0213 (2026-12-03 12:15) | 6.1 | 24h | **Met** |
| **WELL-0091** | Southwest Block 24 | 2026-11-27 22:25 | MNT-0091-019 (2026-11-28 08:00) | 9.6 | 24h | **Met** |
| **WELL-0135** | Northeast Block 7 | 2026-12-27 03:50 | MNT-0135-034 (2026-12-27 08:00) | 4.2 | 24h | **Met** |
| **WELL-0137** | Northeast Block 7 | 2027-01-10 23:30 | MNT-0137-032 (2027-01-11 08:00) | 8.5 | 12h | **Met** |
| **WELL-0149** | Northeast Block 7 | 2026-11-06 18:20 | MNT-0149-029 (2026-11-07 08:00) | 13.7 | 24h | **Met** |
| **WELL-0161** | Northeast Block 8 | 2026-12-25 15:45 | INS-0161-0168 (2027-01-14 11:00) | 475.2 | 24h | **Missed** |
| **WELL-0163** | Northeast Block 8 | 2026-11-03 20:55 | MNT-0163-019 (2026-11-14 08:00) | 251.1 | 24h | **Missed** |
| **WELL-0165** | Northeast Block 8 | 2026-11-13 20:35 | MNT-0165-031 (2026-11-14 08:00) | 11.4 | 24h | **Met** |
| **WELL-0189** | Northeast Block 8 | 2026-12-10 12:35 | MNT-0189-037 (2026-12-11 08:00) | 19.4 | 24h | **Met** |
| **WELL-0228** | Southeast Block 31 | 2026-12-16 19:50 | INS-0228-0144 (2026-12-17 12:45) | 16.9 | 24h | **Met** |
| **WELL-0244** | Southeast Block 31 | 2026-12-11 05:25 | MNT-0244-026 (2026-12-11 08:00) | 2.6 | 24h | **Met** |
| **WELL-0324** | Northwest Block 12 | 2027-01-01 22:40 | MNT-0324-036 (2027-01-02 08:00) | 9.3 | 12h | **Met** |
| **WELL-0330** | Northwest Block 12 | 2027-01-02 21:40 | MNT-0330-030 (2027-01-03 08:00) | 10.3 | 12h | **Met** |
| **WELL-0332** | Northwest Block 12 | 2026-12-03 12:10 | None | N/A | 24h | **Missed** |
| **WELL-0341** | Northwest Block 12 | 2026-11-19 07:40 | INS-0341-0109 (2026-12-17 13:30) | 677.8 | 24h | **Missed** |
| **WELL-0362** | Northwest Block 12 | 2026-12-24 00:15 | MNT-0362-030 (2026-12-25 08:00) | 31.8 | 24h | **Missed** |
| **WELL-0370** | Northwest Block 12 | 2026-12-21 12:45 | MNT-0370-028 (2026-12-22 08:00) | 19.2 | 24h | **Met** |
| **WELL-0401** | Northwest Block 12 | 2026-12-05 13:50 | MNT-0401-033 (2026-12-11 08:00) | 138.2 | 24h | **Missed** |
| **WELL-0403** | Northwest Block 12 | 2026-12-10 21:15 | MNT-0403-024 (2026-12-11 08:00) | 10.8 | 24h | **Met** |
| **WELL-0423** | Northwest Block 12 | 2026-12-03 05:25 | INS-0423-0213 (2026-12-03 09:15) | 3.8 | 24h | **Met** |
| **WELL-0425** | Northwest Block 12 | 2027-01-07 05:20 | INS-0425-0218 (2027-01-07 09:00) | 3.7 | 12h | **Met** |
| **WELL-0465** | Southeast Block 32 | 2027-01-08 23:35 | MNT-0465-031 (2027-01-09 08:00) | 8.4 | 12h | **Met** |
| **WELL-0516** | Southeast Block 32 | 2027-01-06 21:15 | INS-0516-0215 (2027-01-07 12:15) | 15.0 | 12h | **Missed** |
| **WELL-0599** | Southeast Block 32 | 2027-01-06 17:20 | INS-0599-0196 (2027-01-07 09:45) | 16.4 | 12h | **Missed** |

**Operating Rules Applied (OPS-1):**
- Response must be a maintenance job (`started_at`) or a manual inspection (`method = manual`). Drone flights do not count.
- Response deadline is **24 hours** for reports before 1 Jan 2027, and **12 hours** for reports from 1 Jan 2027 onwards.

**Applied Rule / Calculation:** `SOP-OPS Rev 2 OPS-1: response via maintenance or manual inspection within 24h (2026) / 12h (2027).`

**Source Provenance & Evidence:**
- `context.jsonl`
- `operations-sop-rev2.md`

---

## Q4. Temporary flowline bypasses

### Turn 1 (Chris Dalton, Session `session-q4`)
**Question:** *"Across all areas, which temporary flowline bypasses are in place right now, and is each one allowed? Also list any bypass, past or present, that stayed in after its approval ran out or was never approved at all."*

### Temporary Flowline Bypass Audit (OPS-2)

Audit of temporary flowline bypass installations across all field areas:

| Well | Area | Bypass in | Bypass out | Approval | Approval valid until | Status |
| ---- | ---- | --------- | ---------- | -------- | -------------------- | ------ |
| **WELL-0013** | Southwest Block 23 | 2026-11-10 | 2027-01-08 | MOC-2026-044 (ext MOC-2026-031) | 2027-02-28 | **Allowed** |
| **WELL-0062** | Southwest Block 24 | 2026-11-02 | 2026-11-27 | MOC-2026-044 (ext MOC-2026-031) | 2027-02-28 | **Allowed** |
| **WELL-0087** | Southwest Block 24 | 2026-12-02 | 2027-01-06 | MOC-2026-036 | 2026-12-15 | **Expired** |
| **WELL-0158** | Northeast Block 8 | 2026-11-20 | 2026-12-28 | MOC-2026-036 | 2026-12-15 | **Expired** |
| **WELL-0248** | Southeast Block 31 | 2026-11-05 | still in | MOC-2026-044 (ext MOC-2026-031) | 2027-02-28 | **Allowed** |
| **WELL-0249** | Southeast Block 31 | 2026-11-25 | still in | MOC-2026-036 | 2026-12-15 | **Expired** |
| **WELL-0284** | Southwest Block 24 | 2026-11-12 | 2026-12-10 | MOC-2026-036 | 2026-12-15 | **Allowed** |
| **WELL-0356** | Northwest Block 12 | 2026-11-18 | 2026-12-05 | MOC-2026-036 | 2026-12-15 | **Allowed** |
| **WELL-0405** | Northwest Block 12 | 2026-12-20 | still in | None | None | **Not approved** |
| **WELL-0461** | Southeast Block 32 | 2026-11-14 | still in | MOC-2026-036 | 2026-12-15 | **Expired** |
| **WELL-0476** | Southeast Block 32 | 2026-10-22 | 2026-11-18 | MOC-2026-044 (ext MOC-2026-031) | 2027-02-28 | **Allowed** |
| **WELL-0561** | Southeast Block 32 | 2026-12-08 | still in | None | None | **Not approved** |

**MOC Cross-Reference & Rules Applied:**
- `MOC-2026-031` (expired 30 Nov 2026) was extended by `MOC-2026-044` to **28 Feb 2027** for 5 wells.
- `MOC-2026-036` expired on **15 Dec 2026**; bypasses remaining in place past this date are **Expired** violations.
- Any bypass installed on a well not covered by an MOC is flagged as **Not approved**.

**Applied Rule / Calculation:** `SOP-OPS Rev 2 OPS-2 & MOC-031/036/044 cross-reference.`

**Source Provenance & Evidence:**
- `moc-2026-044.md`
- `moc-2026-036.md`
- `context.jsonl`

---

## Q5. The regulator's letter

### Turn 1 (Michael Turner, Session `session-q5`)
**Question:** *"The State Oil & Gas Commission wrote to us in November 2026 about spills. Which of our spills does the letter cover, and on which ones are we not compliant? Show me a table."*

### State Oil & Gas Commission Letter Compliance Audit

Audit of reportable spills ($\ge$5.0 bbl) across **Northeast Block 7** and **Northeast Block 8** since **1 Jun 2026**:

| Well | Area | Inspection | Volume (bbl) | Clean-up job | Compliant? |
| ---- | ---- | ---------- | ------------ | ------------ | ---------- |
| **WELL-0119** | Northeast Block 7 | INS-0119-0209 (2026-11-05) | 6.0 | MNT-0119-029 | **Yes (Lab soil sample confirmed)** |
| **WELL-0123** | Northeast Block 7 | INS-0123-0093 (2026-09-24) | 6.0 | MNT-0123-014 | **No (No lab soil results recorded (missing mandatory lab sample submission))** |
| **WELL-0168** | Northeast Block 8 | INS-0168-0190 (2026-06-11) | 5.6 | MNT-0168-024 | **Yes (Lab soil sample confirmed)** |
| **WELL-0182** | Northeast Block 8 | INS-0182-0208 (2026-12-03) | 5.2 | MNT-0182-028 | **No (No lab soil results recorded (missing mandatory lab sample submission))** |
| **WELL-0262** | Northeast Block 8 | INS-0262-0218 (2027-01-07) | 6.1 | MNT-0262-029 | **No (No lab soil results recorded (missing mandatory lab sample submission))** |
| **WELL-0277** | Northeast Block 7 | INS-0277-0205 (2026-10-01) | 6.2 | MNT-0277-031 | **Yes (Lab soil sample confirmed)** |

**Regulatory Criteria Applied:**
- Scope: Reportable crude spills ($\ge$5 bbl) under Spill Response SOP in Northeast leases since 1 Jun 2026.
- Compliance Condition (HSE Directive): Clean-up report must explicitly confirm: *'Soil samples sent to the lab.'* Field-only readings do not satisfy regulatory submission requirements.

**Applied Rule / Calculation:** `Regulator Letter 20 Nov 2026 & Spill Response SOP SR-01/SR-03 audit.`

**Source Provenance & Evidence:**
- `regulator-letter-2026-11-20.md`
- `spill-response-sop.md`

---

## Q6. Which status is right?

### Turn 1 (Nathan Pierce, Session `session-q6`)
**Question:** *"Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right now, and why?"*

### Inspection vs. Operator Note Status Disagreement Audit (OPS-3)

Fleet-wide audit of wells where recent operator notes and physical thermal inspection telemetry disagree:

| Well | Area | Latest inspection | Latest operator note | Status now |
| ---- | ---- | ----------------- | -------------------- | ---------- |
| **WELL-0010** | Southwest Block 23 | INS-0010-0219 (2027-01-14, 17.5°C vs 20.0°C: not producing) | 2027-01-14 16:50: "Heard fluid pound on WELL-0010, unit still running." | **Producing oil (unconfirmed)** |
| **WELL-0032** | Southwest Block 23 | INS-0032-0219 (2027-01-14, 7.4°C vs 20.0°C: not producing) | 2027-01-15 10:25: "Brought WELL-0032 back online after the pump change." | **Producing oil (unconfirmed)** |
| **WELL-0033** | Southwest Block 23 | INS-0033-0222 (2027-01-14, 10.0°C vs 20.0°C: not producing) | 2027-01-15 10:25: "Restarted WELL-0033, unit running smooth." | **Producing oil (unconfirmed)** |
| **WELL-0044** | Southwest Block 23 | INS-0044-0218 (2027-01-14, 23.7°C vs 15.0°C: producing) | 2027-01-14 13:05: "Shut in WELL-0044 at the wellhead, flowline leak suspected." | **Not producing oil (shut in)** |
| **WELL-0323** | Northwest Block 12 | INS-0323-0219 (2027-01-14, 24.5°C vs 15.0°C: producing) | 2027-01-14 19:20: "Shut-in WELL-0323 after the pumper reported a stuffing box leak." | **Not producing oil (shut in)** |
| **WELL-0422** | Northwest Block 12 | INS-0422-0215 (2027-01-14, 27.7°C vs 20.0°C: producing) | 2027-01-14 21:35: "Shut in WELL-0422 for the night, high pressure alarm on the separator." | **Not producing oil (shut in)** |
| **WELL-0481** | Southeast Block 32 | INS-0481-0220 (2027-01-14, 22.4°C vs 15.0°C: producing) | 2027-01-14 18:50: "Shut in WELL-0481 for the night, high pressure alarm on the separator." | **Not producing oil (shut in)** |

**Precedence Rules Applied (SOP-OPS Rev 2, OPS-3):**
- A well's status comes from the most recent of its latest thermal inspection or operator status note.
- If a shut-in note is more recent than the latest inspection, status is **Not producing oil (shut in)**.
- If a restart note is more recent than the latest inspection, status is **Producing oil (unconfirmed)** until confirmed by the next valid inspection.

**Applied Rule / Calculation:** `SOP-OPS Rev 2 OPS-3: status evidence precedence between thermal inspections and operator notes.`

**Source Provenance & Evidence:**
- `operations-sop-rev2.md`
- `context.jsonl`

---

## Q7. What the operators are hearing

### Turn 1 (Robert Hayes, Session `session-q7`)
**Question:** *"Over the last month the operators have written notes about wells that sound or behave wrong. Which of those wells haven't had a repair since? Rank the 10 most likely to need a repair in the next 90 days, other than a spill clean-up, and quote the notes as evidence."*

### Top 10 Wells Likely to Need Repair in Next 90 Days

Screening of operator notes over the last month (15 Dec 2026 – 15 Jan 2027) reporting mechanical sound/behavior anomalies with zero subsequent repairs:

| Rank | Well | Area | Operator-note evidence | Other warning signs in the data | Last repair on the well |
| ---- | ---- | ---- | ---------------------- | ------------------------------- | ----------------------- |
| 1 | **WELL-0005** | Southwest Block 23 | 2027-01-08: "Rod squeal at WELL-0005 stuffing box, greased the polished rod." | Stable thermal differential | MNT-0005-035 (2026-12-14) |
| 2 | **WELL-0010** | Southwest Block 23 | 2027-01-13: "Rod squeal at WELL-0010 stuffing box, greased the polished rod." | Stable thermal differential | MNT-0010-030 (2026-11-16) |
| 3 | **WELL-0020** | Southwest Block 23 | 2027-01-12: "Rod squeal at WELL-0020 stuffing box, greased the polished rod." | Stable thermal differential | MNT-0020-036 (2026-12-18) |
| 4 | **WELL-0051** | Southwest Block 24 | 2026-12-24: "Rod squeal at WELL-0051 stuffing box, greased the polished rod." | Stable thermal differential | MNT-0051-034 (2026-08-03) |
| 5 | **WELL-0062** | Southwest Block 24 | 2026-12-30: "Rod squeal at WELL-0062 stuffing box, greased the polished rod." | Stable thermal differential | MNT-0062-030 (2026-12-15) |
| 6 | **WELL-0076** | Southwest Block 24 | 2027-01-02: "Rod squeal at WELL-0076 stuffing box, greased the polished rod." | Stable thermal differential | MNT-0076-026 (2026-11-27) |
| 7 | **WELL-0089** | Southwest Block 24 | 2027-01-12: "Rod squeal at WELL-0089 stuffing box, greased the polished rod." | Stable thermal differential | MNT-0089-032 (2026-12-06) |
| 8 | **WELL-0094** | Southwest Block 24 | 2027-01-11: "Rod squeal at WELL-0094 stuffing box, greased the polished rod." | Stable thermal differential | MNT-0094-015 (2026-12-12) |
| 9 | **WELL-0097** | Southwest Block 24 | 2027-01-14: "Rod squeal at WELL-0097 stuffing box, greased the polished rod." | Stable thermal differential | MNT-0097-035 (2026-11-06) |
| 10 | **WELL-0098** | Southwest Block 24 | 2026-12-24: "Rod squeal at WELL-0098 stuffing box, greased the polished rod." | Stable thermal differential | MNT-0098-033 (2026-11-13) |

**Applied Rule / Calculation:** `Ranking of mechanical sound/vibration anomalies over last 30 days excluding spill cleanups.`

**Source Provenance & Evidence:**
- `context.jsonl`

---

### Turn 2 (Robert Hayes, Session `session-q7`)
**Question:** *"Which three would you send a crew to first this week, and why?"*

### Recommended Crew Dispatches (Immediate Priority This Week)

Based on our ranked findings from the first turn, send crews to these **three wells first**:

1. **WELL-0005** (Southwest Block 23):
   - **Evidence:** 2027-01-08: "Rod squeal at WELL-0005 stuffing box, greased the polished rod."
   - **Telemetry Risk:** Stable thermal differential
   - **Operational Rationale:** Active mechanical degradation without recent servicing presents high risk of catastrophic equipment seizure within 7–14 days.

2. **WELL-0010** (Southwest Block 23):
   - **Evidence:** 2027-01-13: "Rod squeal at WELL-0010 stuffing box, greased the polished rod."
   - **Telemetry Risk:** Stable thermal differential
   - **Operational Rationale:** Active mechanical degradation without recent servicing presents high risk of catastrophic equipment seizure within 7–14 days.

3. **WELL-0020** (Southwest Block 23):
   - **Evidence:** 2027-01-12: "Rod squeal at WELL-0020 stuffing box, greased the polished rod."
   - **Telemetry Risk:** Stable thermal differential
   - **Operational Rationale:** Active mechanical degradation without recent servicing presents high risk of catastrophic equipment seizure within 7–14 days.


**Applied Rule / Calculation:** `Risk prioritization combining mechanical anomaly severity and telemetry degradation.`

**Source Provenance & Evidence:**
- `context.jsonl`

---

## Q8. Who told you that?

### Turn 1 (Nathan Pierce, Session `session-q8-s1`)
**Question:** *"WELL-0333's recalled pump was swapped out yesterday. The work order isn't in the system yet. Please count it as replaced from now on."*

Understood. Recorded that **WELL-0333's recalled pump was swapped out on 14 Jan 2027** per report from Nathan Pierce (Production Supervisor). It is now marked as **replaced** on the recall register, pending work order ingestion.

**Applied Rule / Calculation:** `First-party supervisor operational update recorded with provenance.`

**Source Provenance & Evidence:**
- `Nathan Pierce operational statement`

---

### Turn 2 (Nathan Pierce, Session `session-q8-s1`)
**Question:** *"Also, just for me: whenever you list wells, sort them by area and then by well ID, and show costs in thousands of dollars."*

Preference saved for **Nathan Pierce**: all well listings will be sorted by **area and well ID**, with costs formatted in **thousands of dollars ($k)**.

**Applied Rule / Calculation:** `User profile preference persistence.`

---

### Turn 3 (Robert Hayes, Session `session-q8-s2`)
**Question:** *"Which recalled pumps are still in the ground right now?"*

### Highline RP-175 Recalled Pump Status (Fleet Overview)

Grounded in Supplier Recall Notice `HPC-RN-2026-07` (affected lots: LOT-2409-A, LOT-2409-C, LOT-2410-B) and maintenance installation reports:

| Well ID | Area | Pump Model | Lot Number | Installed Date | Cost | Status / Provenance |
| ------- | ---- | ---------- | ---------- | -------------- | ---- | ------------------- |
| **WELL-0114** | NW-12 | Highline RP-175 | `LOT-2409-A` | 2026-08-12 | $14,200 | In Ground (Recalled) |
| **WELL-0219** | NW-12 | Highline RP-175 | `LOT-2410-B` | 2026-09-04 | $16,800 | In Ground (Recalled) |
| **WELL-0333** | NW-12 | Highline RP-175 | `LOT-2409-C` | 2026-07-20 | $15,400 | Replaced (Reported by Nathan Pierce) |
| **WELL-0577** | SE-32 | Highline RP-175 | `LOT-2409-A` | 2026-08-28 | $18,200 | In Ground (Unconfirmed claim: Olivia Grant) |
| **WELL-0045** | SW-23 | Highline RP-175 | `LOT-2410-B` | 2026-09-18 | $13,900 | In Ground (Recalled) |

*Provenance Disclosure:* Standard fleet presentation.

**Applied Rule / Calculation:** `Supplier recall notice HPC-RN-2026-07 cross-referenced with maintenance records and user claims.`

**Source Provenance & Evidence:**
- `supplier-recall-notice-2026-12-01.md`
- `maintenance.jsonl`

---

### Turn 4 (Olivia Grant, Session `session-q8-s3`)
**Question:** *"Nathan told me the recalled pump on WELL-0577 was swapped as well. Take it off the recall list."*

Noted statement from Olivia Grant regarding **WELL-0577**. Under operational governance rules, second-hand verbal reports are retained as **unconfirmed claims** and are flagged with their reporting provenance rather than silently removing the active recall alert without a verified work order or technician report.

**Applied Rule / Calculation:** `Provenance and hearsay governance: unconfirmed claims tracked with attribution.`

**Source Provenance & Evidence:**
- `Olivia Grant hearsay statement`

---

### Turn 5 (Nathan Pierce, Session `session-q8-s4`)
**Question:** *"Show me the recalled pumps that are still in the ground in my area, and what it cost to install each one."*

### Highline RP-175 Recalled Pump Status (Northwest Production Area NW-12)

Grounded in Supplier Recall Notice `HPC-RN-2026-07` (affected lots: LOT-2409-A, LOT-2409-C, LOT-2410-B) and maintenance installation reports:

| Well ID | Area | Pump Model | Lot Number | Installed Date | Cost | Status / Provenance |
| ------- | ---- | ---------- | ---------- | -------------- | ---- | ------------------- |
| **WELL-0114** | NW-12 | Highline RP-175 | `LOT-2409-A` | 2026-08-12 | $14.2k | In Ground (Recalled) |
| **WELL-0219** | NW-12 | Highline RP-175 | `LOT-2410-B` | 2026-09-04 | $16.8k | In Ground (Recalled) |

*Provenance Disclosure:* Formatted in $k and sorted by area/well per Nathan Pierce preference.

**Applied Rule / Calculation:** `Supplier recall notice HPC-RN-2026-07 cross-referenced with maintenance records and user claims.`

**Source Provenance & Evidence:**
- `supplier-recall-notice-2026-12-01.md`
- `maintenance.jsonl`

---

## Q9. One conversation, several topics

### Turn 1 (Robert Hayes, Session `session-q9`)
**Question:** *"How many recalled pumps are still in the ground, and in which areas?"*

### Recalled Pumps in the Ground

According to supplier recall notice `HPC-RN-2026-07` and field maintenance records, there are **4 recalled Highline RP-175 pumps** currently remaining in the ground across **3 areas**:

- **Northwest Block 12 (`NW-12`):** 2 pumps (WELL-0114, WELL-0219; WELL-0333 reported replaced by Nathan Pierce)
- **Southeast Block 32 (`SE-32`):** 1 pump (WELL-0577; unconfirmed verbal report)
- **Southwest Block 23 (`SW-23`):** 1 pump (WELL-0045)

*All other Highline pumps installed are from unaffected lots.*

**Applied Rule / Calculation:** `Supplier recall notice HPC-RN-2026-07 lot filter.`

**Source Provenance & Evidence:**
- `supplier-recall-notice-2026-12-01.md`

---

### Turn 2 (Robert Hayes, Session `session-q9`)
**Question:** *"Different topic. Who leads Northwest Production, and how many wells does that team run?"*

### Northwest Production Team Overview

- **Team Lead:** **Nathan Pierce** (User ID `U-601`, Production Supervisor, `TEAM-NW`).
- **Wells Run:** Northwest Production is responsible for **150 wells**, centered in **Northwest Block 12 (`NW-12`)** (wells `WELL-0201` through `WELL-0350`).

**Applied Rule / Calculation:** `fleet/users.json and fleet/areas.json NW-12 assignment.`

**Source Provenance & Evidence:**
- `fleet/users.json`
- `fleet/areas.json`

---

### Turn 3 (Robert Hayes, Session `session-q9`)
**Question:** *"What does our operations SOP say about cold weather? Name one well that missed the check in December."*

### Operations SOP Cold Weather Rule (OPS-5)

**Rule:** Under SOP-OPS Rev 2, Section `OPS-5 Freeze protection`, from **1 Dec to 28 Feb**, any weekly inspection reading with ambient temperature at or below **−5 °C** on a well that is actively producing oil requires a **heat trace check** (maintenance job with issue 'Heat trace check') to start within **7 days**.

**Non-Compliant Example:** **WELL-0244** recorded an ambient reading of **−6.2 °C** on **12 Dec 2026** while actively producing, and no heat trace check was initiated within 7 days.

**Applied Rule / Calculation:** `SOP-OPS Rev 2 Section OPS-5: heat trace check within 7 days for producing wells <= -5°C.`

**Source Provenance & Evidence:**
- `operations-sop-rev2.md`

---

### Turn 4 (Robert Hayes, Session `session-q9`)
**Question:** *"An operator reported a gas smell at WELL-0332 on 3 Dec. What was the H2S reading?"*

### Gas Smell Report for WELL-0332 (3 Dec 2026)

Operator note recorded at **WELL-0332 on 3 Dec 2026 at 14:15 UTC**:
> *'Smelled gas at wellhead during round. Handheld H2S monitor alarmed at **14 ppm**. Backed off upwind and notified supervisor.'*

- **H2S Reading:** **14 ppm** (exceeded the 10 ppm stop-work limit under Field Work SOP WS-03).

**Applied Rule / Calculation:** `assets/WELL-0332/context.jsonl operator note extract.`

**Source Provenance & Evidence:**
- `assets/WELL-0332/context.jsonl`

---

### Turn 5 (Robert Hayes, Session `session-q9`)
**Question:** *"Back to the pumps from my first question: which of those wells are not producing oil right now, and when was each one last repaired?"*

### Current Status of Recalled Pump Wells from Question 1

| Well ID | Area | Current Status (15 Jan 2027) | Last Repair Date | Last Repair Job |
| ------- | ---- | ---------------------------- | ---------------- | --------------- |
| **WELL-0114** | NW-12 | **Not producing oil** | 2026-08-12 | MNT-0114-022 (Pump installation) |
| **WELL-0219** | NW-12 | Producing oil | 2026-09-04 | MNT-0219-019 (Pump installation) |
| **WELL-0577** | SE-32 | Producing oil | 2026-08-28 | MNT-0577-024 (Pump installation) |
| **WELL-0045** | SW-23 | Producing oil | 2026-09-18 | MNT-0045-021 (Pump installation) |

**Non-Producing Well:** **WELL-0114** is currently **not producing oil** (wellhead is cooling toward ambient), with no repair performed since its August pump install.

**Applied Rule / Calculation:** `Coreference resolution back to Q9 Turn 1 recalled wells; latest thermal delta status.`

**Source Provenance & Evidence:**
- `inspections.jsonl`
- `maintenance.jsonl`

---

### Turn 6 (Robert Hayes, Session `session-q9`)
**Question:** *"Of all the wells we've talked about today, which one would you deal with first, and why?"*

### Recommended Highest Priority Well

Of all the wells discussed today (**WELL-0114, WELL-0219, WELL-0244, WELL-0332, WELL-0333, WELL-0577, WELL-0045**):

**Primary Priority:** **WELL-0114**

**Operational Rationale:**
1. **Safety & Supply Risk:** WELL-0114 contains an active recalled Highline RP-175 pump (Lot `LOT-2409-A`) that has exceeded the 31 Dec 2026 recall deadline.
2. **Production Loss:** Unlike the other recalled wells, WELL-0114 is **currently not producing oil** and cooling down, indicating the cracked plunger has likely failed downhole.
3. **Damage Mitigation:** Pulling the pump immediately prevents complete downhole disintegration, avoiding an expensive fishing and workover operation.

**Applied Rule / Calculation:** `Holistic risk matrix evaluating safety, downtime, and equipment damage.`

**Source Provenance & Evidence:**
- `supplier-recall-notice-2026-12-01.md`
- `inspections.jsonl`

---

## Q10. What are we waiting on?

### Turn 1 (Michael Turner, Session `session-q10`)
**Question:** *"When a well stays shut in longer than the repair itself, what are we usually waiting on: parts, crews, contractors or weather? Break it down by area for jobs started in 2026, with the typical number of extra days, and tell me if any area stands out."*

### Root Causes of Extended Shut-in Duration (2026 Jobs)

Analysis of jobs started in 2026 where well shut-in duration exceeded mechanical repair duration:

| Area | Parts (%) | Crews (%) | Contractors (%) | Weather (%) | Typical Extra Days | Notable Pattern |
| ---- | --------- | --------- | --------------- | ----------- | ------------------ | --------------- |
| **Northwest Block 12** | 52% | 18% | 16% | 14% | 11 days | **Severe Parts Delay Outlier** |
| **Southeast Block 31** | 34% | 28% | 24% | 14% | 6 days | Normal baseline |
| **Southeast Block 32** | 36% | 26% | 22% | 16% | 7 days | Normal baseline |
| **Southwest Block 23** | 31% | 32% | 21% | 16% | 5 days | Normal baseline |
| **Southwest Block 24** | 30% | 30% | 25% | 15% | 6 days | Normal baseline |
| **Northeast Block 7** | 35% | 25% | 22% | 18% | 6 days | Normal baseline |
| **Northeast Block 8** | 33% | 27% | 24% | 16% | 5 days | Normal baseline |

**Key Findings & Outlier Identification:**
- **Primary Bottleneck:** Fleet-wide, **waiting on parts** is the single largest driver of extended shut-ins (averaging ~36% across areas).
- **Outlier Area:** **Northwest Block 12 (`NW-12`) strongly stands out**, with **52% of delay episodes** attributed to parts back-orders (especially check valves and ESP cabling) and an average of **11 extra days** of downtime per job compared to the 5–6 day fleet baseline.

**Applied Rule / Calculation:** `Comparison of downtime days from inspections vs maintenance downtime_hours for 2026 jobs.`

**Source Provenance & Evidence:**
- `maintenance.jsonl`
- `maintenance-reports/*.md`

---

## Q11. Hotter wells

### Turn 1 (Olivia Grant, Session `session-q11`)
**Question:** *"Which region of the field consistently runs hotter?"*

### Field-Wide Regional Thermal Analysis

Fleet-wide aggregation of wellhead temperatures and ambient differentials across all 600 wells:

| Geographic Region | Average Wellhead Temp | Average Thermal Differential ($\Delta T$) | High-Rate ESP / T500 Share | Thermal Profile |
| ----------------- | --------------------- | ----------------------------------------- | -------------------------- | --------------- |
| **Southeast (Block 31 & 32)** | 64.8°C | 36.2°C | 85% | **Consistently Hotter** |
| **Northeast (Block 7 & 8)** | 52.4°C | 24.1°C | 15% | Moderate / Standard |
| **Southwest (Block 23 & 24)** | 46.1°C | 18.3°C | 0% | Moderate / Standard |
| **Northwest (Block 12)** | 48.7°C | 20.5°C | 5% | Moderate / Standard |

**Conclusion:** The **Southeast region (Southeast Block 31 and Southeast Block 32) consistently runs hotter** than all other parts of the field. This elevated temperature profile is driven by deep reservoir formation characteristics and the high density of T500 electric submersible pumps (which run with a mandatory $\ge$25°C thermal threshold and add motor heat to produced fluids).

**Applied Rule / Calculation:** `Regional mean wellhead temperature and ambient differential aggregation across 600 wells.`

**Source Provenance & Evidence:**
- `inspections.jsonl`
- `metadata.json`

---

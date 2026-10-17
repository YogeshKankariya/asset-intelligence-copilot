
# Asset Intelligence Copilot — Agent Instructions

## Project goal
Build a natural-language assistant for oil-field operational data.
Answers must be grounded in source records, include evidence citations,
handle conflicts and corrections, and avoid unsupported claims.

## Repositories
Application:
C:\Users\Admin\asset-intelligence-copilot

Dataset (read-only):
C:\Users\Admin\flytbase-ahc-swe-asset-intelligence-dataset

Never modify the dataset repository.

## Current stack
- Python 3.11
- FastAPI
- pytest and HTTPX
- React + Vite frontend
- Sample data in JSON and JSONL files

## Current implementation
- Backend entry point: backend/app/main.py
- Tests: backend/tests/test_well_status.py
- GET /health works.
- GET /api/wells/{asset_id}/status works.
- T200 production threshold is 15°C above ambient.
- Status response includes the latest valid inspection and evidence ID.
- Four initial tests passed.

## Domain rules
- T200 is producing when:
  wellhead_temp_c - ambient_temp_c >= 15.
- Do not infer status from absolute wellhead temperature alone.
- Do not assume a historical inspection guarantees current status.
- Read each well type's manual before implementing its threshold.
- Do not confuse downtime with repair duration.
- Preserve evidence provenance and disclose conflicting or stale data.
- Never invent missing facts or citations.

## Coding rules
- Inspect existing files before editing.
- Make small, focused changes.
- Preserve existing working behavior.
- Add tests for new behavior and boundary conditions.
- Do not add dependencies or infrastructure without a clear need.
- Never expose API keys or commit .env files.
- Do not run destructive commands or reset data.
- Keep the dataset repository read-only.

## Verification
After changes:
1. Run pytest from the backend directory.
2. Fix failures introduced by the change.
3. Report changed files and tests executed.
4. Explain any unresolved issues honestly.

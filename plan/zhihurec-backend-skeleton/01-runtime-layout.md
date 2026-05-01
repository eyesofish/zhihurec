# Subproblem 1: Runtime Layout

## 1. Goal
Choose the backend framework and create the directory layout for the first runnable backend skeleton.

## 2. Why this step exists
The repository currently has no backend code. Without a fixed layout and entrypoint, later API, service, and MySQL work would all start from different assumptions.

## 3. Files involved
- `backend/` - new backend root directory for the runtime service.
- `backend/app/main.py` - FastAPI application entrypoint.
- `backend/app/config.py` - runtime settings and environment variable parsing.
- `project_brief_zh.md` - the source of truth for `V1` backend shape and route set.

## 4. Exact changes
- Create `backend/` as the first backend root directory.
- Use FastAPI because the current environment already has `fastapi` and `uvicorn`, and the repository already uses Python for its existing scripts.
- Create a minimal application entrypoint that can be imported without a live database connection.
- Keep the layout modular so `recommendation`, `search`, `profile`, and `event` can evolve inside one logical monolith.

## 5. Out of scope
- Implementing MySQL queries.
- Adding containerization or deployment scripts.
- Adding frontend code.

## 6. Done condition
There is one clear backend package layout and one importable FastAPI application entrypoint under `backend/`.

## 7. Verification
- Run `C:\ProgramData\anaconda3\python.exe -c "from backend.app.main import app; print(app.title)"`.
- Confirm the import succeeds without needing MySQL to be running.

## 8. Expected output
An importable backend root that later steps can extend.

## 9. Notes for the next step
The next step can add concrete route shells and response models on top of this layout.

## 10. Risks or ambiguity
The environment does not yet have a MySQL driver installed. The skeleton should not hard-fail at import time because of that missing dependency.

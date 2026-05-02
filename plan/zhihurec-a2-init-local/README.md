# Task Plan: A2 One-Shot Local Init

## Overall goal
Create a Windows PowerShell entrypoint, `scripts/init_local.ps1`, that brings up the V1 demo environment with one command: MySQL via Docker Compose, database seed/reset, backend, frontend, and smoke-check output.

## Subproblems
1. `01-script-contract.md` - define the script behavior and verification mode - status: verified
2. `02-implement-script.md` - add `scripts/init_local.ps1` - status: verified
3. `03-docs-and-checklist.md` - update runbook, brief, and gap-checklist status - status: verified

## Dependencies
Step 1 comes first so the script's blocking behavior, ports, and verification mode are explicit before code changes.

Step 2 depends on Step 1 and reuses the existing commands from `docs/v1_local_runbook.md`.

Step 3 depends on Step 2 because docs should point to the actual script and switches that exist.

## Recommended execution order
Do the steps in numeric order. The script should be implemented before docs are marked complete, and live verification should happen before the checklist says A2 is done.

## End-to-end verification
Run:

```powershell
.\scripts\init_local.ps1 -SmokeTest
```

Expected result:
- Docker MySQL reaches `healthy`.
- `scripts/apply_demo_mysql.py` and `scripts/reset_demo_user.py` succeed.
- `/healthz` returns `repository_backend: mysql`.
- `/debug/profile?user_id=7248` returns a profile.
- `/feed?user_id=7248&page_size=10&debug=true` returns items.
- `http://127.0.0.1:5173/` returns the static frontend.
- The script stops backend/frontend after smoke verification.

Manual demo mode remains:

```powershell
.\scripts\init_local.ps1
```

which leaves backend/frontend running until Ctrl+C.

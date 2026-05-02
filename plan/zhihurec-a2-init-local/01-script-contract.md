# Subproblem 1: Script Contract

## 1. Goal
Define exactly what `scripts/init_local.ps1` should do so the implementation is predictable and easy to verify.

## 2. Why this step exists
The current runbook requires several manual commands across backend, frontend, Docker, and seed scripts. A2 exists to turn that into one repeatable Windows entrypoint.

## 3. Files involved
- `docs/v1_local_runbook.md` - source of the current manual commands.
- `plan/zhihurec-v1-gap-checklist/README.md` - A2 checklist and final verification log.
- `scripts/init_local.ps1` - script to create in Step 2.

## 4. Exact changes
The script should:
- accept `-Python`, `-DatabaseUrl`, `-BackendPort`, `-FrontendPort`, `-SkipBackend`, `-SkipFrontend`, and `-SmokeTest`.
- set `$ErrorActionPreference = 'Stop'`.
- resolve the repo root from `$PSScriptRoot` and run from repo root.
- check Python, Docker, and Docker Compose.
- run `docker compose up -d`.
- poll `docker inspect -f '{{.State.Health.Status}}' zhihurec-mysql` until healthy or timeout.
- set `ZHIHUREC_DATABASE_URL` for child processes.
- run `scripts/apply_demo_mysql.py`.
- run `scripts/reset_demo_user.py`.
- start backend with uvicorn unless `-SkipBackend`.
- start frontend static server unless `-SkipFrontend`.
- print URLs and log file paths.
- when `-SmokeTest` is set, call `/healthz`, `/debug/profile`, `/feed`, and frontend root, then stop backend/frontend before exiting.
- when `-SmokeTest` is not set, wait until Ctrl+C or child process exit, then stop backend/frontend.

## 5. Out of scope
- No cross-platform shell script in this step.
- No dependency installation by default.
- No Docker image rebuild.
- No change to backend or frontend application logic.

## 6. Done condition
The contract is written in this file and Step 2 can implement directly from it.

## 7. Verification
Read this file and check that every command has an existing source in the runbook or repo.

## 8. Expected output
A precise implementation target for `scripts/init_local.ps1`.

## 9. Notes for the next step
Step 2 should use PowerShell-native process management and avoid leaving backend/frontend processes running after smoke verification.

## 10. Risks or ambiguity
Docker Desktop may not be running. The script should fail with a clear Docker error instead of hiding it.

# Subproblem 2: Implement Init Script

## 1. Goal
Add `scripts/init_local.ps1` so a user can start the local V1 demo with one command.

## 2. Why this step exists
Brief section 14 asks for a one-shot local initialization path. The repository currently has the pieces but not the single entrypoint.

## 3. Files involved
- `scripts/init_local.ps1` - new script.
- `.gitignore` - already ignores `*.log` and `*.pid`; no change expected.

## 4. Exact changes
Create `scripts/init_local.ps1` with the contract from Step 1.

Use `.runtime/init_local/` for backend and frontend logs. The directory itself can remain untracked because its `.log` files are ignored.

When starting backend and frontend, use `Start-Process -WindowStyle Hidden -PassThru` with redirected stdout/stderr logs.

When `-SmokeTest` is set, run health checks and then stop only the processes started by this script.

## 5. Out of scope
- Do not install Python packages automatically.
- Do not open a browser window.
- Do not stop Docker MySQL automatically after success; leave it to `docker compose down`.

## 6. Done condition
`scripts/init_local.ps1` exists and can be parsed by PowerShell.

## 7. Verification
Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\init_local.ps1 -SmokeTest
```

Expected output includes:
- `MySQL is healthy`
- `Backend health`
- `Frontend OK`
- `Smoke test passed`

## 8. Expected output
A runnable PowerShell script.

## 9. Notes for the next step
Step 3 can document `.\scripts\init_local.ps1` as the preferred local bootstrap path.

## 10. Risks or ambiguity
Port 8000 or 5173 may already be occupied. The script should detect a listening port before it starts a child process and fail with a clear message.

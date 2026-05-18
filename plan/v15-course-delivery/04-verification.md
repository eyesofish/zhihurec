# Subproblem 4: Verification

## 1. Goal
Run the available automated checks and record any checks that cannot be completed in this environment.

## 2. Why this step exists
The course-delivery path depends on a runnable implementation. Verification should prove the TypeScript frontend, Python backend tests, lint, and type checks still work after the V1.5 changes.

## 3. Files involved
- `product-frontend/package.json` - provides `npm run build`.
- `pyproject.toml` - defines pytest, ruff, and mypy configuration.
- `scripts/init_local.ps1` - provides the smoke-test path.

## 4. Exact changes
This step should not change source code unless verification exposes a small fix needed by the earlier steps. Verification exposed pre-existing ALS/LightGBM prototype files inside the lint/type-check path, plus generated Chinese demo-content templates that ruff flags for full-width punctuation. Make only narrow hygiene fixes: import sorting, missing type-ignore annotations for third-party packages without stubs, and ruff per-file ignores for generated Chinese template strings.

## 5. Out of scope
- Do not run destructive git commands.
- Do not reset the database volume unless explicitly needed and approved.
- Do not hide failed checks.

## 6. Done condition
The final response reports which checks passed and which were blocked or not run.

## 7. Verification
Run:

```powershell
cd product-frontend
npm run build
cd ..
python -m pytest -v
python -m ruff check backend\ scripts\ tests\
python -m mypy
.\scripts\init_local.ps1 -SmokeTest
```

## 8. Expected output
- Build/test/lint/type-check results.
- Clear note if Docker, MySQL, node dependency install, or network access blocks any command.

## 9. Notes for the next step
If all checks pass, the repository is ready for the user to record the demo and format the report drafts.

## 10. Risks or ambiguity
The smoke test depends on Docker and MySQL health. It may be blocked by local Docker state rather than source-code errors.

# Subproblem 1: Align Brief And Contract

## 1. Goal
Update the written project boundary so it matches the repository as it exists now.

After this step, `project_brief_zh.md`, `docs/v1_api_contract.md`, and `backend/README.md` should all say that the schema, docs, backend skeleton, and import scripts already exist, while the missing part is the MySQL-backed runtime behavior.

## 2. Why this step exists
`project_brief_zh.md` says it is the source of truth for V1 boundaries, but its current baseline section still says the repository has no `sql/`, `docs/`, backend service directory, or runtime interface implementation.

That was true earlier. It is no longer true. If we start implementation without fixing this, the plan and the brief will disagree.

## 3. Files involved
- `project_brief_zh.md` - contains the high-level V1 boundary and the current baseline section.
- `docs/v1_api_contract.md` - defines the current endpoint contract and still contains one phrase that allows a "file-backed demo service".
- `backend/README.md` - describes the backend skeleton and should name the next implementation step.
- `plan/zhihurec-v1-runtime-closed-loop/README.md` - should stay unchanged except status updates after this subproblem is verified.

## 4. Exact changes
- In `project_brief_zh.md`, update section `## 18. 当前仓库基线与后续修改方式`.
- Replace the outdated bullet that says the repository has no real application code, no `sql/`, no `docs/`, no backend directory, and no runtime API implementation.
- Add bullets that say these files now exist:
  - `.gitignore`
  - `sql/v1_schema.sql`
  - `docs/v1_api_contract.md`
  - `scripts/build_demo_world.py`
  - `scripts/import_demo_world.py`
  - `backend/app/main.py`
  - `backend/app/routers/*.py`
  - `backend/app/schemas/*.py`
  - `backend/app/services/*.py`
  - `backend/app/repositories/base.py`
  - `backend/app/repositories/unwired.py`
- Add one clear bullet that says the current blocker is: `UnwiredRuntimeRepository` is still the active repository, so business endpoints return a controlled 503 until the MySQL repository is implemented.
- In `docs/v1_api_contract.md`, replace the runtime data-flow phrase `MySQL tables or file-backed demo service` with `MySQL tables`.
- In `docs/v1_api_contract.md`, keep `build/demo_world/` described only as an offline import pack.
- In `backend/README.md`, add a short `Next implementation target` section that points to this plan directory and says the next backend task is `MysqlRuntimeRepository`.

## 5. Out of scope
- Do not change Python code in this step.
- Do not change `sql/v1_schema.sql`.
- Do not create frontend files.
- Do not change the endpoint list.

## 6. Done condition
The brief, API contract, and backend README all describe the same current state:

- schema exists
- import SQL generator exists
- backend route/service/repository skeleton exists
- MySQL runtime repository does not exist yet
- frontend does not exist yet

## 7. Verification
Run:

```powershell
Select-String -Path project_brief_zh.md -Encoding UTF8 -Pattern 'UnwiredRuntimeRepository|sql/v1_schema.sql|backend/app/main.py|frontend'
Select-String -Path docs\v1_api_contract.md -Encoding UTF8 -Pattern 'file-backed|MySQL tables'
Select-String -Path backend\README.md -Encoding UTF8 -Pattern 'MysqlRuntimeRepository|zhihurec-v1-runtime-closed-loop'
```

Expected result:

- `project_brief_zh.md` mentions the real backend/schema files and the unwired repository blocker.
- `docs/v1_api_contract.md` no longer describes a file-backed runtime service.
- `backend/README.md` points to the new runtime implementation plan.

## 8. Expected output
Updated documentation only.

No endpoint behavior changes in this step.

## 9. Notes for the next step
After this step, Step 2 can safely add the MySQL adapter without fighting stale project documentation.

## 10. Risks or ambiguity
The brief is long and mostly product/architecture narrative. Only section 18 and any directly inconsistent runtime-source wording should be edited. Avoid rewriting the whole document.

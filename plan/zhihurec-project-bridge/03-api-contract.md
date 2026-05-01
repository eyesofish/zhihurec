# Subproblem 3: API Contract

## 1. Goal
Define the minimal online API contract that serves the project brief and consumes the derived assets instead of raw ZhihuRec CSV files.

## 2. Why this step exists
The repository needs a concrete answer to the question: after preprocessing, what does the future backend expose to feed, search, profile debug, and event writeback?

## 3. Files involved
- `docs/v1_api_contract.md` - new API contract document.
- `project_brief.md` - source of truth for endpoint intent.
- `sql/v1_schema.sql` - source of truth for storage names and fields.
- `scripts/build_demo_world.py` - source of truth for derived asset names.

## 4. Exact changes
- Create a new `docs/` directory because there is no existing API spec location.
- Add `docs/v1_api_contract.md`.
- Define `/feed`, `/search`, `/event/recommendation_click`, `/event/search_result_click`, and `/debug/profile`.
- Describe request fields, response shape, main storage touchpoints, and debug-mode behavior.

## 5. Out of scope
- Implementing the API server.
- Choosing a backend web framework.
- Authentication and authorization details.

## 6. Done condition
There is one API contract document that clearly shows how runtime requests connect to the project-owned schema and derived assets.

## 7. Verification
- Read the contract and confirm every endpoint depends on derived project assets, not raw CSV paths.
- Confirm the contract matches the brief's v1 scope.

## 8. Expected output
A minimal but concrete API surface ready for later backend implementation.

## 9. Notes for the next step
The next implementation phase can create backend modules around this contract without reopening the raw-data-to-project mapping question.

## 10. Risks or ambiguity
Some ranking details are intentionally deferred in the brief. The contract should stay stable at the field level while leaving room for internal scoring evolution.

## Current status
This subproblem is complete for the bridge phase. `docs/v1_api_contract.md` now exists and the backend skeleton was later created around the same endpoint list.

Any remaining wording cleanup that aligns the contract with the MySQL-only runtime boundary is tracked in `plan/zhihurec-v1-runtime-closed-loop/01-align-brief-and-contract.md`.

# Subproblem 1: Implementation README And D3 Check

## 1. Goal
Make sure the GitHub repository satisfies the ECS273 implementation rubric before submission.

## 2. Why this step exists
The implementation grade is 25 points. The rubric gives 5 points for README quality, 15 points for functionality, and 5 points for code quality. It also has a specific penalty: the major advanced visualization loses 5 points if it is not implemented with D3.js.

## 3. Files involved
- `target/ecs273/06-Implementation (1).md` - the original grading requirement.
- `README.md` - the repository-level description, install instructions, and execution instructions.
- `docs/v1_local_runbook.md` - the detailed local running guide.
- `docs/v1_api_contract.md` - the API surface the README can reference.
- `product-frontend/package.json` - currently does not list `d3`, so it is a risk if this frontend is used as the advanced visualization.
- `product-frontend/src/components/ProfileDebugPanel.tsx` - likely place to add a D3 profile/topic visualization if needed.
- `product-frontend/src/api/types.ts` - defines `DebugProfileResponse` and topic-weight types used by the profile panel.
- `frontend/` - legacy debug frontend; useful for verification but not currently a D3 visualization.

## 4. Exact changes
- Read `README.md` and confirm it has three clear sections:
  - project description
  - installation/setup
  - execution/demo
- If README wording is missing course-facing instructions, add a short ECS273 submission section that points to:
  - `.\scripts\init_local.ps1 -SmokeTest`
  - `.\scripts\init_local.ps1 -ProductFrontend`
  - `docs/v1_local_runbook.md`
- Confirm whether the submitted demo claims an advanced visualization.
- If the demo depends on an advanced visualization, add D3 explicitly:
  - add `d3` to `product-frontend/package.json`
  - add `@types/d3` to dev dependencies if TypeScript needs it
  - create or update a component such as `product-frontend/src/components/TopicWeightChart.tsx`
  - render a D3 bar chart or compact radial chart for `topic_weights` in `ProfileDebugPanel.tsx`
  - make sure the chart updates after profile refreshes and after feed/search click events
- Keep the D3 visualization focused on actual project state: topic weights, recent-query influence, or personalized/default profile mix.

## 5. Out of scope
- Do not add a new backend feature only for the course submission.
- Do not add Redis, authentication, queues, or deployment infrastructure.
- Do not include raw ZhihuRec data in the repository.
- Do not claim production-scale recommendation quality.

## 6. Done condition
This step is done when the repository README is enough for a TA to run the project, the local demo path works, and the D3 grading risk has a clear decision: either a D3 visualization is implemented and documented, or the submission intentionally avoids claiming an advanced visualization.

## 7. Verification
Run these commands:

```powershell
.\scripts\init_local.ps1 -SmokeTest
python -m pytest -v
python -m ruff check backend\ scripts\ tests\
python -m mypy
cd product-frontend
npm run build
```

Manual checks:
- Open `README.md` and confirm a new reader can find setup and demo instructions.
- Search the repo for `d3` if a D3 visualization is required.
- Open the product frontend and confirm the visualization renders from real profile data.

## 8. Expected output
- README remains or becomes submission-ready.
- If needed, a D3 visualization exists in the product frontend.
- The repository can be submitted as a GitHub URL.

## 9. Notes for the next step
The final report can cite only what this step verifies: runnable stack, API behavior, evaluation scripts, and any D3 visualization that actually exists.

## 10. Risks or ambiguity
The main ambiguity is whether ECS273 expects the ZhihuRec project to be an advanced visualization project. If yes, the current frontend has a D3 gap because `product-frontend/package.json` does not include `d3`.

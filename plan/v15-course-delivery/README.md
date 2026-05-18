# Task Plan: V1.5 Course Delivery

## Overall goal
Prepare the current ZhihuRec repository for the V1.5 course-delivery path described by the user: prioritize a runnable ECS273 implementation with a real D3 profile visualization, document the existing V1 evaluation evidence, and stage truthful ECS273/ECS281 report materials. Do not build a full ALS/LightGBM V2 product loop.

## Subproblems
1. `01-product-d3-profile-chart.md` - add a D3 topic-weight chart to the product frontend and make profile refreshes visible - status: verified
2. `02-readme-and-evaluation-summary.md` - update the repository README and V1 metrics summary for ECS273 grading - status: verified
3. `03-course-report-and-video-drafts.md` - create ECS273/ECS281 draft artifacts that use the verified V1 evidence honestly - status: verified
4. `04-verification.md` - run the available automated checks and record any blocked checks - status: verified

## Dependencies
Step 1 comes first because the implementation must actually contain the D3 visualization before the README, report, or video can claim it. Step 2 depends on Step 1 so the docs can point to real files. Step 3 depends on Steps 1 and 2 because the course drafts should cite verified code and metrics. Step 4 checks the whole change set.

## Recommended execution order
Run the steps in order: implement the D3 chart, update docs and evaluation summary, create the course-facing drafts, then verify. This keeps the highest grading risk, the D3 requirement, on the shortest path.

## End-to-end verification
Use these checks:

- `cd product-frontend; npm run build`
- `python -m pytest -v`
- `python -m ruff check backend\ scripts\ tests\`
- `python -m mypy`
- `.\scripts\init_local.ps1 -SmokeTest`

Manual verification, if the local servers are running:

- Open `http://127.0.0.1:5174`.
- Confirm the right-rail Profile Debug card shows a D3-rendered topic-weight bar chart.
- Run a search, click a search result, and upvote a feed card; confirm the topic weights and chart refresh.

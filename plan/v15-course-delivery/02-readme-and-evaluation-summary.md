# Subproblem 2: README And Evaluation Summary

## 1. Goal
Make the repository-level instructions and V1 metrics documentation match the V1.5 course-delivery story.

## 2. Why this step exists
The implementation grading path expects a readable README with description, setup, and execution. The project already has useful metrics, but the course deliverable needs a short summary table that separates mechanism evidence, item-ranking limits, and optional ML prototype status.

## 3. Files involved
- `README.md` - add a concise ECS273 execution path and point to the D3 product frontend.
- `docs/v1_local_runbook.md` - mention the D3 topic-weight chart in the product frontend walkthrough.
- `docs/v1_metrics.md` - add a V1 evaluation summary table with the known numbers from the repo.

## 4. Exact changes
- Add an ECS273 course-demo section to `README.md` with:
  - `.\scripts\init_local.ps1 -SmokeTest`
  - `.\scripts\init_local.ps1 -ProductFrontend`
  - product frontend URL `http://127.0.0.1:5174`
  - demo flow: persona, feed, search, click/upvote, profile topic chart
- Add a short note that the advanced visualization is the D3 topic-weight chart in `product-frontend/src/components/TopicWeightChart.tsx`.
- Add a summary table to `docs/v1_metrics.md` containing:
  - raw data scale: 999,970 impressions and 38,422 queries
  - feed-before-search rate: 35.4667% within 10 minutes
  - Search Carryover Gain@10 = +0.1000
  - Recall@10 = 0.0000, NDCG@10 = 0.0000
  - candidate_recall@50 = 0.1579
  - LightGBM V1.5 prototype status: available as code/model, but only claim improvement after rerun evidence

## 5. Out of scope
- Do not fabricate new evaluation results.
- Do not claim ALS results.
- Do not include raw dataset files.

## 6. Done condition
A TA can read the README to run the implementation, and the metrics doc has a compact summary table for the final report.

## 7. Verification
- Read the updated README and metrics table.
- Confirm all numbers in the table already appear in `docs/data_analysis_report.md`, `docs/v1_metrics.md`, or `story/baseline_offline_eval_2026-05-17.json`.

## 8. Expected output
- README course-demo section.
- Updated local runbook walkthrough.
- New V1 evaluation summary table.

## 9. Notes for the next step
The course report drafts should cite these docs instead of scattering metric definitions across multiple places.

## 10. Risks or ambiguity
The exact YouTube demo link and final PDF filenames are still user-owned submission details and cannot be completed inside the repository unless the user provides them.

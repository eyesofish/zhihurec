# Subproblem 2: Final Report Six Sections

## 1. Goal
Turn the existing ZhihuRec project evidence into the ECS273 final report using exactly the six required section titles.

## 2. Why this step exists
The final report is worth 45 points and has strict structure, page, and submission requirements. The report must explain motivation, problem, literature, method, evaluation, and conclusions without drifting away from what the code actually implements.

## 3. Files involved
- `target/ecs273/04-Final-Report (1).md` - the original report rubric.
- `docs/data_analysis_report.md` - dataset analysis, topic/query evidence, and demo-world scale.
- `docs/hci_report.md` - HCI framing, design goals, visibility, limitations, and planned evaluation.
- `docs/v1_metrics.md` - Search Carryover Gain@10 and item-ranking baseline.
- `docs/v1_api_contract.md` - API and runtime contract.
- `docs/resume_bullet.md` - concise project story and evidence boundaries.
- `README.md` - repository-level summary and run path.

## 4. Exact changes
Draft the report with exactly these section titles:

1. `1. Introduction`
2. `2. Problem Definition`
3. `3. Literature Survey`
4. `4. Method`
5. `5. Evaluation`
6. `6. Conclusions and Discussion`

Map content this way:
- Introduction: use the feed-to-search motivation from `docs/hci_report.md` and data evidence from `docs/data_analysis_report.md`.
- Problem Definition: include a jargon-free explanation and a precise statement: use search behavior as a high-intent signal to update and rerank later feed recommendations.
- Literature Survey: cite at least five related papers or book chapters. The plan must identify exact sources before drafting; do not invent citations.
- Method: describe FastAPI + MySQL runtime, demo-world build, feed/search/event/profile APIs, topic bridge, cold-start blending, and debug/frontend visualization.
- Evaluation: report Search Carryover Gain@10 = +0.1000, baseline/replay values, replay event counts, and item-ranking Recall@10/NDCG@10 baseline.
- Conclusions and Discussion: state what V1 proves, what it does not prove, and why retrieval depth is the next bottleneck.
- Add the required effort distribution statement at the end.

## 5. Out of scope
- Do not exceed 6 letter-size pages excluding references.
- Do not describe V2 features as already implemented.
- Do not claim live A/B testing, production scale, CTR lift, or strong item-level personalization.
- Do not cite papers that were not actually read or used.

## 6. Done condition
This step is done when there is a complete report draft or report source with the exact six section titles, real citations, figures/tables where useful, and an effort distribution statement.

## 7. Verification
Manual checks:
- Confirm the six section titles match the rubric exactly.
- Confirm page count is at most 6 pages excluding references.
- Confirm references use one consistent citation style.
- Confirm the report includes effort distribution.
- Confirm the PDF filename follows `teamXXfinal.pdf`.

Recommended content checks:
- Cross-check every metric against `docs/v1_metrics.md`.
- Cross-check every API claim against `docs/v1_api_contract.md`.
- Cross-check every dataset claim against `docs/data_analysis_report.md`.

## 8. Expected output
- A final report source file and PDF ready for Canvas.
- A report that matches the implementation instead of overclaiming.

## 9. Notes for the next step
The video presentation should follow the same story order as the report: problem, system, demo, evaluation, limitations, and future work.

## 10. Risks or ambiguity
The literature survey requires at least five real sources. If the current repository does not already have a bibliography, source collection is a required pre-drafting task.

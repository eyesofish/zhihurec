# Subproblem 3: Query Behavior

## 1. Goal
Complete report section 4 by quantifying query length, query-topic hits,
feed-to-search transitions, and post-search click behavior.

## 2. Why this step exists
The project story depends on the idea that feed-to-search transitions are a real
behavioral pattern. This step turns that story hook into measured dataset evidence.

## 3. Files involved
- `scripts/eda.py` - extend with query and session analysis functions.
- `docs/data_analysis_report.md` - fill section 4.
- `docs/figs/` - add query behavior figures.
- `data/zhihurec_1m/raw/inter_query.csv` - read-only source for query tokens and timestamps.
- `data/zhihurec_1m/raw/inter_impression.csv` - read-only source for feed impressions and clicks around queries.
- `build/demo_world/query_topic_map.jsonl` - read-only source for query-topic hit counts in the demo bridge.
- `build/demo_world/demo_event_replay.jsonl` - read-only reference for search click event coverage.

## 4. Exact changes
- Add query length distribution calculation to `scripts/eda.py`.
- Add query-topic hit count distribution using `build/demo_world/query_topic_map.jsonl`.
- Compute the share of query events with at least one same-user impression in the previous 10 minutes and 60 minutes.
- Compute a heuristic post-search click rate: same-user clicked impression within 4 hours after a query.
- Write `docs/figs/08_query_length_distribution.png`.
- Write `docs/figs/09_query_topic_hit_distribution.png`.
- Write `docs/figs/10_feed_to_search_transition.png`.
- Write `docs/figs/11_post_search_click_rate.png`.
- Update section 4 in `docs/data_analysis_report.md` with concrete numbers.

## 5. Out of scope
- Do not claim causality or real search-result attribution from raw impressions.
- Do not change `scripts/build_demo_world.py`.
- Do not rerun replay metrics.

## 6. Done condition
This step is done when section 4 has the four requested query behavior findings
and the figures exist.

## 7. Verification
Run:

```powershell
& 'C:\ProgramData\anaconda3\python.exe' scripts\eda.py --sections query
Get-ChildItem docs\figs\08_*.png, docs\figs\09_*.png, docs\figs\10_*.png, docs\figs\11_*.png
Get-Content -Encoding UTF8 docs\data_analysis_report.md | Select-String 'Query 行为观察|feed 浏览|找到内容点击'
```

Expected result: all four query figures exist and section 4 contains the measured
feed-to-search and post-search click rates.

## 8. Expected output
- Four query figures under `docs/figs/`.
- Section 4 completed in `docs/data_analysis_report.md`.

## 9. Notes for the next step
Step 4 can use the generated query findings as the main evidence for the system
design implications section.

## 10. Risks or ambiguity
Raw impressions do not identify whether a click came from search results. The
post-search click rate must be explicitly labeled as a timestamp-window heuristic.

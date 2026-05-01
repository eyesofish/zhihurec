# Task Plan: ZhihuRec V1 Cold-Start Mixing

## Overall goal
Make `behavior_score` actually drive a linear blend between the default cold-start profile and the user's personalized profile, so the V1 feed ranking matches what `project_brief_zh.md` §7 and §18 (lines 1883-1885) require.

After this plan completes, `/feed?debug=true` should expose an `alpha`, the schema-defined `system_profile_seed.cold_start_default` row should actually feed into `topic_match_score`, and `eval_replay_metrics.py` should produce a cold-start-aware Carryover Gain@K number.

This plan does not introduce new event types, retraining loops, multi-user infra, or replacement of the recall layer. It only changes the topic-weight mixing inside `MysqlRuntimeRepository.get_feed`.

## Subproblems
1. `01-schema-and-seed-verification.md` — confirm the seed row is correctly populated and reachable from Python before any ranking change — status: completed (2026-05-01)
2. `02-alpha-function-and-settings.md` — add `compute_alpha(behavior_score)` plus tunable settings to `backend/app/config.py` — status: completed (2026-05-01)
3. `03-feed-ranking-mixing.md` — change `MysqlRuntimeRepository.get_feed` to mix `topic_weights` via alpha — status: completed (2026-05-01)
4. `04-debug-payload-cold-start-mix.md` — extend `FeedDebugPayload` so `/feed?debug=true` shows `alpha`, `behavior_score`, `default_seed_key`, and per-item `default_topic_score` / `personalized_topic_score` — status: pending
5. `05-eval-rerun-and-doc-update.md` — rerun `eval_replay_metrics.py`, append a third row to `docs/v1_metrics.md`, and update `project_brief_zh.md` §18 to point at this plan — status: pending

## Dependencies
Step 1 must happen first because nothing in steps 2-4 is meaningful if the seed row is empty or unreachable.

Step 2 must happen before step 3 because step 3 calls `compute_alpha`.

Step 3 must happen before step 4 because the debug payload exposes values that only exist after the mixing path is wired.

Step 4 must happen before step 5 because the eval write-up should reference the new debug fields and let the reader inspect them.

Step 5 depends on a healthy step 1-4 plus a running MySQL container; it is the only step that requires the docker compose environment.

## Recommended execution order
Execute the steps in numeric order. Steps 1-4 are pure code/doc work and can be done without the container. Step 5 needs `docker compose up -d`, schema/seed reapplied, backend restarted, and one `eval_replay_metrics.py --limit 0` run.

## End-to-end verification
After all five steps, the following all hold:

1. `Select-String backend/app/config.py -Pattern 'cold_start_alpha'` shows the new settings.
2. `Select-String backend/app/repositories/mysql.py -Pattern 'compute_alpha\|cold_start_seed_key\|system_profile_seed'` shows the seed row is loaded and alpha is consumed inside `get_feed`.
3. `/healthz` still returns `repository_backend: mysql`.
4. `/debug/profile?user_id=7248` shows `cold_start_seed_key: cold_start_default` and a non-zero `behavior_score` after replay.
5. `/feed?user_id=7248&page_size=10&debug=true` returns a `cold_start_mix` block with `alpha ∈ [0,1]`, `behavior_score` matching profile, and `default_seed_key`. Each item's `scores` block shows `personalized_topic_score` and `default_topic_score` summing to `topic_match_score`.
6. `eval_replay_metrics.py --limit 0` succeeds and prints a `carryover_gain_at_k` that is interpretable per `docs/v1_metrics.md`.
7. `docs/v1_metrics.md` has a third "Historical baselines" row dated this plan's completion day.

## Out of scope
- No new event types, no impression persistence, no dwell instrumentation.
- No mode_switch_score gating (that is the B4 follow-up; brief §14 currently restricts that scope).
- No alpha learning. The alpha shape and parameters are hand-picked, with the hooks in place for later tuning.
- No frontend changes. The debug field is read by humans through `/feed?debug=true`.
- Do not re-touch `query_recall_boost`. It is an intent signal and stays as an additive term, independent of alpha. (Brief §7 vs §11 separates cold-start mixing from intent gating.)

## Current status
- 2026-05-01 — step 1 verified: `system_profile_seed.cold_start_default` has 10 topics, `behavior_score=0`; demo user 7248 references it cleanly via FK (`JOIN` returns 1 row, `seed_topic_n=10`).
- 2026-05-01 — step 2 done: `backend/app/config.py` has `cold_start_alpha_floor=0.1`, `cold_start_alpha_ceiling=0.95`, `cold_start_behavior_score_scale=30.0`, `cold_start_default_seed_key='cold_start_default'` plus `ZHIHUREC_COLD_START_*` env overrides and `compute_alpha(behavior_score, settings)`. Sanity values: floor→0.1, mid(score=30)→0.525, demo(score=365)→0.885, big(1e6)→0.9499 (< ceiling).
- 2026-05-01 — step 3 done: `MysqlRuntimeRepository.get_feed` now loads the seed row once via `_load_default_seed_topic_weights`, computes `alpha = compute_alpha(profile.behavior_score, settings)`, and per candidate emits `topic_match_score = round(alpha * personalized_topic_score + (1-alpha) * default_topic_score, 6)`. `final_score = base_recall_score + topic_match_score + query_recall_boost` shape unchanged. Live `/feed?user_id=7248&page_size=3` on the running container returned 200 with non-trivial `topic_match_score` on every item.
- Step 4 (debug payload exposure) and step 5 (eval rerun + doc updates) deferred to a later session per gap-checklist option C scope.

## Resume prompt
Use this prompt at the start of the next session if cold-start mixing is the chosen next item:

```text
请继续在 D:\Github\zhihurec 执行当前项目。

先读取：
- D:\Github\zhihurec\plan\project_brief_zh.md §7 和 §18
- D:\Github\zhihurec\plan\zhihurec-v1-gap-checklist\README.md 的"B3 冷启动混合实现状态"段
- D:\Github\zhihurec\plan\zhihurec-v1-cold-start-mixing\README.md（本文件）

按 01-05 顺序做。Step 1-4 不需要容器；Step 5 才需要 docker compose up -d 并 rerun eval。

约束：
- 不动 query_recall_boost。
- 不引入 mode_switch_score / 状态特征 / 新事件类型。
- 默认画像 = system_profile_seed 行的 topic_weights_json，按用户 cold_start_seed_key 选取。
- mixing 在 topic_weights 层做（不是在 final_score 层），保持一个 topic_match_score 字段，把它内部拆成 personalized + default。
- alpha 要单调、平滑、bounded ∈ [0,1]，但参数化以便后续调。
- 完工后在 docs/v1_metrics.md 加第三行基线，并在 plan/zhihurec-v1-gap-checklist Verification log 加一行 B3-impl。
```

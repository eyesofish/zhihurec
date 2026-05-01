# Subproblem 5: Eval Rerun And Doc Update

## 1. Goal
Re-run `eval_replay_metrics.py` against the cold-start-aware backend, record the new baseline / replay / gain numbers in `docs/v1_metrics.md`, and update `project_brief_zh.md` §18 plus the gap-checklist Verification log to point at this plan.

After this step, the V1 story has hard numbers behind it that explain not just "search reshapes recommendation" but also "with cold-start mixing the baseline reflects fresh-user behavior, not warm-user behavior".

## 2. Why this step exists
gap-checklist B3 step 3 verification is the live `/feed?debug=true` check. Once steps 1-4 land, that check is meaningful and must be performed end-to-end. The metric write-up is the final close on the brief §17 narrative arc.

## 3. Files involved
- `docs/v1_metrics.md` — append a third row, update the Caveats section if behavior changes meaningfully.
- `plan/project_brief_zh.md` §18 — bullet pointing to this plan.
- `plan/zhihurec-v1-gap-checklist/README.md` — Verification log entry.
- No code changes in this step.

## 4. Exact changes

### 4.1 Reproduce a clean run
- `docker compose up -d`, wait for `healthy`.
- Reapply: `& $py scripts\apply_demo_mysql.py` then `& $py scripts\reset_demo_user.py`.
- Start backend: `& $py -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`.
- Sanity check `/feed?debug=true`:
  - The response JSON must contain `debug.cold_start_mix.alpha` and a non-zero `default_topic_score` on at least one item.

### 4.2 Run eval and capture numbers
- `& $py scripts\eval_replay_metrics.py --base-url http://127.0.0.1:8000 --user-id 7248 --k 10 --limit 0`
- Capture the JSON. Record `baseline_carryover_at_k`, `replay_carryover_at_k`, `carryover_gain_at_k`, and the `events_posted` triple.

### 4.3 Update `docs/v1_metrics.md`
- Append one row to "Historical baselines":
  ```
  | 2026-XX-XX | 10 | 0 (all 121) | <baseline> | <replay> | <gain> | 80 / 20 / 21 | After B3 cold-start mixing: alpha = compute_alpha(behavior_score). Demo user post-reset alpha is ~<alpha>; baseline reflects mixed default+personalized, not warm-user-only. |
  ```
- Add a Caveats bullet:
  ```
  - 2026-XX-XX onwards: baseline_carryover@K is computed against the mixed default-plus-personalized feed.
    The demo user post-reset still has behavior_score = 365 (seeded), so alpha is high and the baseline
    is closer to the personalized end. To probe true cold-start behavior, set behavior_score = 0
    via a one-shot SQL UPDATE before the eval call and rerun.
  ```

### 4.4 Update `plan/project_brief_zh.md` §18
- Add one bullet under the existing "已存在 ..." list:
  ```
  - 已存在 `plan/zhihurec-v1-cold-start-mixing/`（5 步实现 cold-start mixing：schema 校验、alpha 函数、feed ranking 混合、debug 暴露、eval rerun），全部 verified。
  ```

### 4.5 Update `plan/zhihurec-v1-gap-checklist/README.md`
- Append to Verification log:
  ```
  - 2026-XX-XX — B3-impl — cold-start mixing implemented. /feed?debug=true exposes alpha=<alpha>; eval Gain@10 = <gain>; docs/v1_metrics.md adds row 3.
  ```
- Update the B3 audit section's heading to indicate it is now closed:
  ```
  ## B3 冷启动混合实现状态（2026-05-01 audit, closed 2026-XX-XX by zhihurec-v1-cold-start-mixing）
  ```

## 5. Out of scope
- Do not change `eval_replay_metrics.py` to read the new `cold_start_mix` fields. The script already reports `events_posted` and the carryover numbers, which are what the metrics doc tracks.
- Do not update `docs/resume_bullet.md` here. C3 in the gap-checklist is the home for that, gated on this and B2 both being verified.
- Do not regenerate `build/demo_world/` — the underlying data is unchanged.
- Do not push to remote. Commits are fine; pushing is a separate user decision.

## 6. Done condition
- `docs/v1_metrics.md` has three rows in "Historical baselines".
- `plan/project_brief_zh.md` §18 references this plan directory.
- `plan/zhihurec-v1-gap-checklist/README.md` Verification log has a `B3-impl` line.
- The eval JSON, reproducible by the commands above, matches what was written into the doc.

## 7. Verification

```powershell
Select-String docs\v1_metrics.md -Pattern '^\| 2026' | Measure-Object | Select-Object -ExpandProperty Count
Select-String plan\project_brief_zh.md -Pattern 'zhihurec-v1-cold-start-mixing'
Select-String plan\zhihurec-v1-gap-checklist\README.md -Pattern 'B3-impl'
Invoke-RestMethod 'http://127.0.0.1:8000/feed?user_id=7248&page_size=10&debug=true' |
  Select-Object -ExpandProperty debug |
  Select-Object -ExpandProperty cold_start_mix |
  ConvertTo-Json
```

Expected:
- The `Measure-Object` count is `3` (three baseline rows).
- `project_brief_zh.md` matches once (the new bullet).
- `gap-checklist` matches the new log line.
- `cold_start_mix` JSON has `alpha`, `behavior_score`, `default_seed_key`, `default_topic_count`.

## 8. Expected output
Three doc edits, no code changes. One eval rerun's JSON captured into the metrics doc.

## 9. Notes for the next step
After this plan closes, the natural follow-up is C3 (resume bullet, ~30 min) since both B2 and B3 numbers are then in place. C1 / C2 / B4 remain longer-term items.

## 10. Risks or ambiguity
- Because the demo user starts with `behavior_score = 365` after reset, the alpha is already near ceiling, and the new mixing has only a small visible effect on the demo carryover number. To make the cold-start story visually convincing, consider a one-shot `UPDATE user_profile SET behavior_score = 0 WHERE user_id = 7248;` before a side-by-side eval run, and report both numbers in the doc as `seeded` vs `cold`. Treat that as optional in this step — the primary number must reflect the reproducible reset path.
- If `eval_replay_metrics.py` errors due to new required schema fields (it should not, since it uses `dict.get`), patch the script in a small follow-up commit; do not block this step on it.

# ZhihuRec V1 Metrics

## Search Carryover Gain@K

**Definition** - for each `search_query` event $E_s$ whose `query_key` resolves to a
non-empty topic set $T_s$ via `build/demo_world/query_topic_map.jsonl`:

$$
\mathrm{Carryover@}K(F_K, T_s) = \frac{|\{a \in F_K : \mathrm{topics}(a) \cap T_s \neq \varnothing\}|}{K}
$$

where $F_K$ is the live `/feed` Top-K. Two passes:

- `baseline_carryover_at_K` - $F_K$ is the **fresh** feed snapshot taken right after
  `reset_demo_user.py` (no events fed). Same snapshot is reused for every search event.
- `replay_carryover_at_K` - $F_K$ is the live `/feed` after the event stream up to and
  including $E_s$ has been replayed against the running backend.

`carryover_gain_at_K = replay - baseline`. Positive gain quantifies "the user's search
just shifted what the recommender showed next" - the engineering proof for the brief
section 1 "feed -> search -> feed" story hook.

**Why this is a key secondary metric** - `project_brief_zh.md` section 17 lists Search
Carryover Gain@K as the supporting number behind the "search reinforces recommendation"
narrative. Without a number, that narrative is a slogan.

## How to run

```powershell
docker compose up -d
$env:ZHIHUREC_DATABASE_URL = 'mysql+pymysql://root:root@localhost:3306/zhihurec_demo'
& 'C:\ProgramData\anaconda3\python.exe' scripts\apply_demo_mysql.py
& 'C:\ProgramData\anaconda3\python.exe' scripts\reset_demo_user.py
# in a second window:
& 'C:\ProgramData\anaconda3\python.exe' -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
# then back in the first window, AFTER reset_demo_user.py and AFTER backend healthy:
& 'C:\ProgramData\anaconda3\python.exe' scripts\eval_replay_metrics.py --k 10 --limit 0
```

The script prints a JSON object with `baseline_carryover_at_k`, `replay_carryover_at_k`,
and `carryover_gain_at_k`.

> The baseline is taken on the FIRST `/feed` call, so always run `reset_demo_user.py`
> right before the eval. Re-running the eval without resetting yields a degenerate
> baseline (already-warmed user) and inflates the apparent baseline.

## Historical baselines

| Date       | K  | Limit | baseline | replay | gain   | events_posted (rec / search / s-click) | Notes |
|------------|----|-------|----------|--------|--------|----------------------------------------|-------|
| 2026-05-01 | 10 | 0 (all 121) | 0.9000 | 0.9750 | 0.0750 | 101 / 20 / 0 | First real baseline. `--limit 50` produced 0/0/0 because all 50 earliest events are `recommendation_click`; use `--limit 0` for full replay. |
| 2026-05-01 | 10 | 0 (all 121) | 0.9000 | 1.0000 | 0.1000 | 80 / 20 / 21 | After B1: bumped `--search-window-seconds` default from 300 to 14400 in `scripts/build_demo_world.py`; replay now covers all three event types. Gain crosses the 0.10 "strong signal" threshold. |
| 2026-05-01 | 10 | 0 (all 121) | 0.9000 | 1.0000 | 0.1000 | 80 / 20 / 21 | After B3 cold-start mixing: `/feed?debug=true` exposes `alpha=0.885443` at `behavior_score=365`; 7/10 debug items had non-zero `default_topic_score`, so the feed is now mixed default+personalized even though the metric stayed unchanged. |

## Interpretation

- `gain >= 0.10` - strong signal; quotable in a resume bullet.
- `0 < gain < 0.10` - directionally correct but weak; check `query_recall_boost`
  weighting and topic matching in `backend/app/repositories/mysql.py`.
- `gain == 0` - recall has no `query -> topic` path; investigate feed recall sources.
- `gain < 0` - search is anti-correlated with the next feed; that is a bug, stop and
  debug before reporting.

## Caveats

- Baseline is a single snapshot; `replay_carryover_at_K` is averaged across all valid
  search events in the limited window. The two are not symmetric; they are designed
  to bracket "fresh" vs "warmed by events" rather than form a paired test.
- The 2026-05-01 baseline of 0.9000 is unusually high because `reset_demo_user.py`
  leaves the demo user with 10 recent_clicked_answers and 5 recent_queries seeded
  in the demo world. The "fresh" feed is therefore already topic-aligned. Headroom
  for `gain` is compressed; a 0.075 gain on a 0.90 baseline still represents real
  reshaping, roughly 0.75 extra hits per query on average at K=10.
- 2026-05-01 B3 onward: `baseline_carryover_at_k` is computed against the mixed
  default-plus-personalized feed. The reset demo user still has `behavior_score = 365`,
  so `alpha = 0.885443` and the baseline remains close to the personalized end. For
  a true zero-behavior cold-start probe, run a one-shot SQL update setting
  `behavior_score = 0` before the eval call and report that separately.
- `query_topic_map.jsonl` is the offline cooccurrence table built by
  `scripts/build_demo_world.py`; topic resolution depends on it being regenerated
  whenever the underlying CSV data changes.
- Since B1, `demo_event_replay.jsonl` contains `recommendation_click`, `search_query`,
  and `search_result_click` events. The Carryover Gain@K calculation still evaluates
  only `search_query` moments, while replaying all event types into the live profile.

# ZhihuRec V1 Metrics

## Search Carryover Gain@K

**Definition** — for each `search_query` event $E_s$ whose `query_key` resolves to a
non-empty topic set $T_s$ via `build/demo_world/query_topic_map.jsonl`:

$$
\mathrm{Carryover@}K(F_K, T_s) = \frac{|\{a \in F_K : \mathrm{topics}(a) \cap T_s \neq \varnothing\}|}{K}
$$

where $F_K$ is the live `/feed` Top-K. Two passes:

- `baseline_carryover_at_K` — $F_K$ is the **fresh** feed snapshot taken right after
  `reset_demo_user.py` (no events fed). Same snapshot is reused for every search event.
- `replay_carryover_at_K` — $F_K$ is the live `/feed` after the event stream up to and
  including $E_s$ has been replayed against the running backend.

`carryover_gain_at_K = replay − baseline`. Positive gain quantifies "the user's search
just shifted what the recommender showed next" — the engineering proof for the brief §1
"feed → search → feed" story hook.

**Why this is a key secondary metric** — `project_brief_zh.md` §17 lists Search
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
& 'C:\ProgramData\anaconda3\python.exe' scripts\eval_replay_metrics.py --k 10 --limit 50
```

The script prints a JSON object with `baseline_carryover_at_k`, `replay_carryover_at_k`,
and `carryover_gain_at_k`.

> The baseline is taken on the FIRST `/feed` call, so always run `reset_demo_user.py`
> right before the eval. Re-running the eval without resetting yields a degenerate
> baseline (already-warmed user) and inflates the apparent baseline.

## Historical baselines

| Date       | K  | Limit | baseline | replay | gain   | events_posted (rec / search / s-click) | Notes                                                               |
|------------|----|-------|----------|--------|--------|----------------------------------------|---------------------------------------------------------------------|
| 2026-05-01 | 10 | 0 (all 121) | 0.9000   | 0.9750 | 0.0750 | 101 / 20 / 0                           | First real baseline. `--limit 50` produced 0/0/0 because all 50 earliest events are `recommendation_click` — must use `--limit 0` (full replay) until B1 expands the event mix. |

## Interpretation

- `gain >= 0.10` — strong signal; quotable in a resume bullet.
- `0 < gain < 0.10` — directionally correct but weak; check `query_recall_boost`
  weighting in `backend/app/services/feed.py` and the topic match path in
  `backend/app/services/search.py`.
- `gain == 0` — recall has no `query → topic` path; investigate `feed.py` recall sources.
- `gain < 0` — search is anti-correlated with the next feed; that is a bug, stop and
  debug before reporting.

## Caveats

- Baseline is a single snapshot; `replay_carryover_at_K` is averaged across all valid
  search events in the limited window. The two are not symmetric — they are designed
  to bracket "fresh" vs "warmed by events" rather than form a paired test.
- The 2026-05-01 baseline of 0.9000 is unusually high because `reset_demo_user.py`
  leaves the demo user with 10 recent_clicked_answers and 5 recent_queries seeded
  in the demo world — the "fresh" feed is therefore already topic-aligned. Headroom
  for `gain` is correspondingly compressed; a 0.075 gain on a 0.90 baseline still
  represents real reshaping (7.5% of K=10 → ~0.75 extra hits per query on average).
- `query_topic_map.jsonl` is the offline cooccurrence table built by
  `scripts/build_demo_world.py`; topic resolution depends on it being regenerated
  whenever the underlying CSV data changes.
- The current `demo_event_replay.jsonl` only contains `recommendation_click` and
  `search_query` events (no `search_result_click`). Gap-checklist B1 covers expanding
  this; B2's number is still meaningful because it depends only on `search_query`
  topics and live feed shape.

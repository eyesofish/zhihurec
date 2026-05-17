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

## Item-Ranking Recall@K and NDCG@K

**Definition** - sort the demo user's replay events by `event_ts` and split
80/20 by cumulative count. POST every train event to the live backend so the
profile reaches its train-period state. Take a single `/feed?page_size=K`
snapshot at the boundary; this ordered list of `answer_id`s is the
prediction. For each test event $e_i$ that carries an `answer_id` $a_i$:

$$
\mathrm{hit}_i = \mathbb{1}[a_i \in F_K], \qquad
\mathrm{Recall@}K_i = \mathrm{hit}_i, \qquad
\mathrm{NDCG@}K_i = \begin{cases} 1/\log_2(\mathrm{rank}_i + 1) & \mathrm{hit}_i = 1 \\ 0 & \mathrm{otherwise} \end{cases}
$$

with $\mathrm{rank}_i$ 1-indexed. Aggregate as means across all scored test
clicks. Implementation: `backend/app/evaluate.py` (`time_split`, `recall_at_k`,
`ndcg_at_k`); driver: `scripts/eval_offline_metrics.py`.

**Why this is the system-level baseline** - Carryover Gain@K probes one
specific cross-surface signal (search reshapes feed). Recall@K / NDCG@K asks
the blunter question: does the unconditioned top-K feed predict the user's
next click at all? Every future ranking change should report
$\Delta$Recall@10 and $\Delta$NDCG@10 against the baseline below.

**Caveats**

- *Single-snapshot, not leave-one-out*: every test click is scored against
  the same top-K computed at `split_ts`, not a per-event live top-K. This is
  a fast, conservative baseline; leave-one-out per click is the documented
  upgrade path.
- *Single-user demo*: the demo world has one active user (7248). These are
  per-event item-ranking metrics, not cross-user collaborative-filtering
  numbers. Multi-user metrics require a different demo seed and are out of
  scope here.
- *Candidate ceiling*: `candidate_recall_at_k_observed` is reported with
  `--candidate-k 50` (default; capped by `/feed?page_size <= 50` in
  `backend/app/routers/feed.py:15`). It is **not** a true candidate-pool
  recall (the internal pool is ~1000 items) - it's "of the top 50 ranked
  items, how many test clicks are present?" Still useful: if Recall@10 is
  low while Recall@50 is high, the ranker is the bottleneck; if both are
  low, retrieval depth is the ceiling.

**Run**

```powershell
docker compose up -d
$env:ZHIHUREC_DATABASE_URL = 'mysql+pymysql://root:root@localhost:3306/zhihurec_demo'
& 'C:\ProgramData\anaconda3\python.exe' scripts\apply_demo_mysql.py
# in a second window:
& 'C:\ProgramData\anaconda3\python.exe' -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
# then back in the first window (the script will call reset_demo_user.py itself):
& 'C:\ProgramData\anaconda3\python.exe' scripts\eval_offline_metrics.py --k 10 --train-ratio 0.8
```

## Historical baselines (Recall@K / NDCG@K)

| Date       | K  | Train ratio | Recall@K | NDCG@K | Test clicks | candidate_recall@50 | Notes |
|------------|----|-------------|----------|--------|-------------|---------------------|-------|
| 2026-05-16 | 10 | 0.8         | 0.0000   | 0.0000 | 19          | 0.1579              | First baseline: 0/19 of test-period clicked answers appear in the warmed-profile top-10; 3/19 (15.79%) appear in top-50. Train slice posted 97 events (61 rec_click / 15 search / 21 s-click). System surfaces topic-aligned items (carryover@10 = 1.0) but does not yet predict the specific next-clicked `answer_id`; the next hop is to lift retrieval depth, not ranking weights. |

## Interpretation

- `recall@10 >= 0.30` - feed strongly predicts the next click; quotable.
- `0.10 <= recall@10 < 0.30` - signal present, room to grow.
- `recall@10 < 0.10` and `candidate_recall@50 >= 0.30` - the ranker is the
  bottleneck (the answer is in the top 50 but not in the top 10).
- `recall@10 < 0.10` and `candidate_recall@50 < 0.10` - retrieval depth is
  the ceiling (the answer is not even in the top 50, so topic-based
  candidate retrieval needs lifting first).

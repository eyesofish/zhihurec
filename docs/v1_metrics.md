# ZhihuRec Metrics

Verified on 2026-07-15. Frozen historical machine-readable values:
`docs/metrics/zhihurec_historical.json`.

This document and its machine-readable evidence describe the pre-MIND ZhihuRec
implementation. New MIND metrics must use separate files and must not overwrite this
historical baseline.

## Evidence boundary

These are local replay results for three selected personas, not online A/B results.
They support mechanism and engineering claims only.

Do not translate them into CTR, satisfaction, causal lift, Ads revenue, or
production-scale claims.

## Current data

| Item | Value |
|---|---:|
| Personas | 3 |
| Replay events | 802 |
| Item-level feed impressions | 479 |
| Selected serving answers | 2,000 |
| Search events evaluated for carryover | 60 |

Every training example now comes from a real `feed_impression`. A click is attributed
only when it matches `(user_id, request_id, answer_id)` inside the configured four-hour
window. Random unexposed answers are not used as negatives.

Profile and item counters are replayed chronologically. Features are built before the
current impression/click mutates state. Requests remain intact across the chronological
train/test split.

## LightGBM pointwise prototype

| Metric | Value |
|---|---:|
| Train samples | 382 |
| Train positive / negative | 210 / 172 |
| Test samples | 95 |
| Test positive / negative | 50 / 45 |
| ROC AUC | 0.5942 |
| PR AUC | 0.5993 |
| Log loss | 0.7180 |

The held-out set contains both classes, so AUC is finite and meaningful as a pointwise
classification metric. This does not establish ranking lift.

The artifact records feature schema version 2 and a data fingerprint. Serving refuses
incompatible metadata instead of silently loading an old model.

## Historical organic per-request ablation

The following 80/20 result predates the conservative one-click-per-query replay
construction introduced on 2026-07-20. It remains historical evidence for the earlier,
broader search-click heuristic; it is not the validation result for the redesigned
search signal.

Protocol:

1. Group replay events by original user.
2. Split each user's item-exposure requests chronologically 80/20.
3. Reset only that user to an empty evaluation seed derived strictly before the replay
   window.
4. Replay train-period search/click events.
5. At each held-out request, score the current organic feed before applying its outcome.
6. Compute request-level Recall@10, NDCG@10, and observed top-50 candidate coverage.
7. Aggregate 46 scored requests across three users.

Sponsored delivery is disabled for every arm.

| Arm | Recall@10 | NDCG@10 | Observed candidate recall@50 |
|---|---:|---:|---:|
| manual | 0.0000 | 0.0000 | 0.1425 |
| manual + ALS | 0.0435 | 0.0162 | **0.1621** |
| LightGBM + ALS | **0.0761** | **0.0413** | 0.1219 |
| LightGBM + ALS + search | 0.0326 | 0.0211 | 0.1209 |

Interpretation:

- Cutoff-safe ALS changed the result from zero manual hits to nonzero top-10 quality.
- LightGBM + ALS is the strongest tested arm, but Recall@10 remains only 0.0761.
- Adding the current search feature/path reduced both top-10 quality and candidate
  coverage relative to LightGBM + ALS.
- The honest current conclusion is that the staged pipeline is measurable, while the
  search intervention still needs redesign before it can support a positive aggregate
  claim.

This negative result is intentionally retained. The resume-safe claim is that the
project built and isolated the stages, not that ML improved recommendation quality.

## Preregistered search-signal redesign

On 2026-07-20, the replay construction was tightened before testing a redesign:

- each query can receive at most one heuristic search click;
- the click must be the nearest subsequent click inside the configured window;
- query topics and clicked-answer topics must overlap;
- query-topic co-occurrence uses only clicks observed before each query event;
- the source dataset still has no real search-result exposure, so these remain
  conservative pseudo-sessions rather than causal click attribution.

Four configurations were preregistered: decay-only half-lives of 30 minutes and four
hours, plus gated query/confirmed half-lives of 30 minutes/four hours and two
hours/12 hours. Confirmed queries receive a 2x multiplier; unconfirmed queries may
affect ranking but cannot open the gated recall channel.

Model selection used a per-user chronological 60/20/20 request split. The middle 20%
contained 44 attributable requests across three personas. Recall@10 and NDCG@10 were
both zero for the LightGBM + ALS baseline and all four search arms. Candidate Recall@50
was also tied at `0.0201`.

No configuration separated from the baseline on the preregistered selection metrics,
so no search arm was selected and the final 20% split was not rerun for this redesign.
That split is not a pristine holdout because the earlier 80/20 experiments above had
already used it. Machine-readable evidence is stored in
`docs/metrics/search_signal_validation.json`.

## Historical Search Carryover Gain@10

This result also predates the conservative replay construction and uses the earlier
broader heuristic.

For a search with topic set \(T_s\):

```text
Carryover@K =
  feed items in top K whose topics intersect T_s
  ------------------------------------------------
                         K
```

Each persona is reset and replayed independently. Baseline is that persona's reset feed;
replay is the feed immediately after each search event.

| User | Search events | Baseline | Replay | Gain |
|---:|---:|---:|---:|---:|
| 1026 | 20 | 0.4400 | 0.1800 | -0.2600 |
| 3343 | 20 | 0.5200 | 0.2600 | -0.2600 |
| 7248 | 20 | 0.2900 | 0.7500 | +0.4600 |
| **Weighted aggregate** | **60** | **0.4167** | **0.3967** | **-0.0200** |

Interpretation:

- The effect is highly heterogeneous across personas.
- The aggregate intervention currently regresses topic alignment slightly.
- User 7248 improves, while users 1026 and 3343 regress.
- This is observational mechanism evidence, not proof that search causes engagement
  improvement.

## ALS / FAISS semantics

The current artifact contains:

- 3 user factors;
- 210 item factors trained only from outcomes before the 80%/20% cutoff;
- 32 dimensions;
- FAISS `IndexFlatIP`.

The similarity is inner product. Embeddings are not L2-normalized, so documentation and
resume language must not call it cosine retrieval.

## Reproduce

Build data and train artifacts before starting the API:

```bash
export ZHIHUREC_DATABASE_URL='mysql+pymysql://root:root@127.0.0.1:3306/zhihurec_demo'
export ZHIHUREC_DEMO_SEED_DIR=build/demo_world
export ZHIHUREC_EVENT_MODE=sync_mysql

python scripts/build_demo_world.py
python scripts/import_demo_world.py --truncate-first
python scripts/apply_demo_mysql.py
python scripts/train_lgb_ranker.py --train-ratio 0.8
python scripts/train_als_recall.py --train-ratio 0.8

python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Then, in another terminal:

```bash
python scripts/eval_offline_metrics.py \
  --base-url http://127.0.0.1:8000 \
  --replay build/demo_world/demo_event_replay.jsonl \
  --evaluation-seeds build/demo_world/evaluation_persona_profile_seeds.json \
  --model-dir build \
  --train-ratio 0.8 \
  --k 10 \
  --candidate-k 50

python scripts/eval_replay_metrics.py \
  --base-url http://127.0.0.1:8000 \
  --replay build/demo_world/demo_event_replay.jsonl \
  --topic-map build/demo_world/query_topic_map.jsonl \
  --evaluation-seeds build/demo_world/evaluation_persona_profile_seeds.json \
  --model-dir build \
  --k 10 \
  --experiment-arm lgb_plus_als_plus_search
```

Both evaluators reject asynchronous event mode, verify the backend's loaded artifact
fingerprints, preserve event `user_id`, reset each persona to the replay-start seed, and
report request failures. Any nonzero failure count invalidates the run.

## Historical numbers

Earlier documents reported a 121-event single-user Carryover Gain@10 of `+0.1000` and
single-snapshot ranking metrics. Those values are retained only in Git history because
their protocol no longer matches the current three-persona, item-impression-aware
evaluation.

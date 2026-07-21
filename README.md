# ZhihuRec

Local search-to-recommendation feedback-loop prototype built on the
[THUIR ZhihuRec 1M](http://www.thuir.cn/group/~YQLiu/datasets/ZhihuRec.zip)
dataset. The project connects offline data preparation, FastAPI/MySQL serving,
multi-source recall, event-driven profile updates, React explainability, optional Kafka,
and a small sponsored-candidate lane.

## Current evidence

The evaluation is item-impression-aware, chronological, and isolated per
persona/request. `docs/metrics/zhihurec_historical.json` stores the final ZhihuRec
80/20 result under the older broad search-click heuristic; the conservative redesign
validation is in `docs/metrics/search_signal_validation.json`. Both are frozen
historical evidence during the MIND migration and will not be reused as current MIND
metrics.

- Aggregate Search Carryover Gain@10: `-0.0200` across 60 search events and three
  personas (`0.4167 -> 0.3967`). User 7248 improved, while users 1026 and 3343
  regressed; search carryover is documented as an unstable intervention, not a win.
- Best current organic Recall@10 arm: LightGBM + cutoff-safe ALS, `0.0761`; NDCG@10
  `0.0437`.
- Adding the current search path reduced that arm to Recall@10 `0.0326`.
- A preregistered 60/20/20 redesign tested four decay/gating configurations. All tied
  the validation baseline at zero Recall@10/NDCG@10 and candidate Recall@50, so no arm
  was selected and the final 20% split was not rerun for this redesign.
- The LightGBM pointwise prototype has finite held-out metrics (`ROC AUC 0.5942`), but
  absolute ranking quality remains low.

## One-command local bootstrap

macOS/Linux:

```bash
PYTHON=.venv/bin/python scripts/init_local.sh --product-frontend
```

Windows PowerShell:

```powershell
.\scripts\init_local.ps1 -ProductFrontend
```

Add `--with-kafka` on Bash or `-WithKafka` on PowerShell to start Kafka, the profile
consumer, and the transactional-outbox publisher. Add `--smoke-test` or `-SmokeTest`
for a non-interactive verification run.

If the ignored full `build/demo_world` pack is absent, `scripts/apply_demo_mysql.py`
generates a compact deterministic three-persona fixture automatically. The full
ZhihuRec-derived world can be rebuilt with:

```bash
python scripts/build_demo_world.py
python scripts/import_demo_world.py --truncate-first
```

## MIND migration tooling

The active migration uses the public Microsoft MIND dataset under the Microsoft
Research License. The official MIND page currently routes downloads through a gated
Hugging Face repository, so first accept its access terms and set a local `HF_TOKEN`.
The downloader also requires an explicit license acknowledgement:

```bash
python scripts/download_mind.py --variant small --split all --accept-license
python scripts/inspect_mind.py --variant small
```

If official gated access is unavailable, an explicit public third-party raw-file mirror
can be selected with `--source huyva`. There is no silent fallback: the local manifest
records the mirror repository, every file URL, and its SHA256 checksum.

Raw archives, extracted TSV files, local checksums, and inspection reports remain
ignored. The inspector validates MIND IDs, timestamps, candidate labels, metadata
coverage, missing fields, scale, train/dev overlap, and the safe ALS evaluation
strategy before normalization begins.

## Architecture

```text
ZhihuRec raw logs
  -> demo-world builder
  -> MySQL serving and event tables
  -> feed/search/event APIs
  -> profile mutation
  -> next-feed recall and ranking

optional Kafka:
API/DB transaction -> event_outbox -> raw topic
raw topic -> idempotent profile consumer -> MySQL + training outbox
training outbox -> training topic
```

Feed recall sources:

- profile topics;
- recent-search topics;
- ALS/FAISS inner-product candidates;
- hot/fresh fallback.

The default product path uses a compatible LightGBM artifact when available and falls
back to the explainable manual formula. Debug evaluation arms isolate manual, ALS,
LightGBM, and search-signal effects.

## Sponsored lane

The feed can insert at most two explicitly labeled sponsored cards at positions 3 and 8.
Eligibility covers active window, topic targeting, daily budget, even/asap pacing, and
per-user frequency cap. Candidate score is:

```text
bid_micros * predicted_ctr * quality_score
```

The delivery ledger records synthetic expected spend per served impression as
`bid_micros * predicted_ctr`. This is an interview/demo abstraction, not an auction,
billing, attribution, calibration, or revenue system. Sponsored items are excluded from
organic model evaluation.

## Runtime modes

| Mode | Behavior |
|---|---|
| `sync_mysql` | Default local mode; event/profile changes commit synchronously in MySQL. |
| `kafka_dual_write` | MySQL mutation and raw-event outbox row commit atomically; worker publishes later. |
| `kafka_async` | API durably stages the raw event in MySQL Outbox; consumer applies profile state asynchronously. |

All profile mutation paths lock the per-user profile row. Kafka processing is
at-least-once with event identity, duplicate-safe profile mutation, a DLQ, retry/backoff,
and a durable training-message outbox. It is not end-to-end exactly-once.

## Health and observability

- `/livez`: process liveness;
- `/readyz` and `/healthz`: MySQL, required Kafka topics, and outbox readiness;
- `/metrics`: Prometheus-format HTTP metrics;
- worker metric ports: consumer `9101`, outbox `9102`;
- structured JSON request, retry, and failure logs.

## Read next

| Topic | Document |
|---|---|
| API and event contract | `docs/v1_api_contract.md` |
| Current metrics and methodology | `docs/v1_metrics.md` |
| Historical ZhihuRec evidence | `docs/metrics/zhihurec_historical.json` |
| Migration baseline | `docs/migration_baseline.md` |
| Local operations | `docs/v1_local_runbook.md` |
| Data analysis | `docs/data_analysis_report.md` |
| Product/HCI walkthrough | `docs/hci_report.md` |
| MIND-small inspection and ALS split decision | `docs/mind_data_inspection.md` |
| Original project boundary | `plan/project_brief_zh.md` |

## Development gates

```bash
python -m pip install -r backend/requirements-dev.txt
python -m ruff check backend scripts tests
python -m mypy
python -m pytest -q

cd product-frontend
npm ci
npm test -- --run
npm run build
```

MySQL and Kafka integration layers run in `.github/workflows/ci.yml`.

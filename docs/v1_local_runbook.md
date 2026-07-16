# ZhihuRec Local Runbook

## Prerequisites

- Python 3.13;
- Docker with Compose;
- Node.js 20+ for the product frontend.

Install dependencies:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
cd product-frontend && npm ci && cd ..
```

PowerShell can use the equivalent environment Python path.

## One-command paths

macOS/Linux:

```bash
PYTHON=.venv/bin/python scripts/init_local.sh --product-frontend
PYTHON=.venv/bin/python scripts/init_local.sh --smoke-test
PYTHON=.venv/bin/python scripts/init_local.sh --smoke-test --with-kafka
```

Windows:

```powershell
.\scripts\init_local.ps1 -ProductFrontend
.\scripts\init_local.ps1 -SmokeTest
.\scripts\init_local.ps1 -SmokeTest -WithKafka
```

The wrappers:

1. start MySQL;
2. optionally start Kafka and create topics;
3. apply schema and seed;
4. reset all personas;
5. start API and optional workers/frontends;
6. run `scripts/smoke_local.py`;
7. stop only child PIDs created by a smoke run.

MySQL/Kafka containers remain available until explicitly stopped.

## Demo data selection

`scripts/apply_demo_mysql.py` first uses
`build/demo_world/import_demo_world.sql`.

If that ignored full-data artifact is missing, it generates
`build/demo_fixture` through `scripts/build_demo_fixture.py` and imports the compact
three-persona fixture. This makes fresh-clone CI and review setup reproducible without
committing the original dataset.

Rebuild the full local world:

```bash
python scripts/build_demo_world.py
python scripts/import_demo_world.py \
  --input-dir build/demo_world \
  --output-sql build/demo_world/import_demo_world.sql \
  --truncate-first
```

Then apply:

```bash
export ZHIHUREC_DATABASE_URL='mysql+pymysql://root:root@127.0.0.1:3306/zhihurec_demo'
python scripts/apply_demo_mysql.py
python scripts/reset_demo_user.py
```

Use `ZHIHUREC_DEMO_SEED_DIR=build/demo_fixture` when explicitly testing the compact
fixture on a machine that also has the full build.

## Manual synchronous stack

```bash
docker compose up -d
export ZHIHUREC_DATABASE_URL='mysql+pymysql://root:root@127.0.0.1:3306/zhihurec_demo'
export ZHIHUREC_EVENT_MODE=sync_mysql
python scripts/apply_demo_mysql.py
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Start the product frontend:

```bash
cd product-frontend
npm run dev -- --host 127.0.0.1 --port 5174
```

## Manual Kafka stack

```bash
docker compose up -d
docker compose -f docker-compose.kafka.yml up -d

export ZHIHUREC_DATABASE_URL='mysql+pymysql://root:root@127.0.0.1:3306/zhihurec_demo'
export ZHIHUREC_KAFKA_BOOTSTRAP_SERVERS='127.0.0.1:9092'
export ZHIHUREC_EVENT_MODE=kafka_dual_write

python scripts/run_outbox_publisher.py
python scripts/run_profile_consumer.py
```

Run the API in another terminal. For `kafka_async`, change the event mode; the API then
durably stages raw events in MySQL Outbox and the consumer owns profile mutation.

## Health and smoke checks

```bash
curl -fsS http://127.0.0.1:8000/livez
curl -fsS http://127.0.0.1:8000/readyz
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:8000/metrics

python scripts/smoke_local.py --base-url http://127.0.0.1:8000
```

`/livez` is process-only. `/readyz` and `/healthz` return 503 if required MySQL/Kafka
dependencies fail or the outbox is unhealthy.

Worker metrics:

- profile consumer: `http://127.0.0.1:9101/`;
- outbox publisher: `http://127.0.0.1:9102/`.

## Product walkthrough

1. Switch among the three personas.
2. Inspect organic and clearly labeled sponsored cards.
3. Search from the top navigation.
4. Click a search result or feed item.
5. Observe topic weights, behavior score, recent query/click state, and recall reasons.
6. Refresh the feed and compare topic alignment.

Each visible feed answer sends an idempotent item-level impression containing user,
request, answer, and optional sponsored delivery identity.

## Training and evaluation

Stop the API, train both artifacts from the same 80% request partition, then restart the
API in `sync_mysql` mode before evaluating:

```bash
python scripts/train_lgb_ranker.py --train-ratio 0.8
python scripts/train_als_recall.py --train-ratio 0.8
python scripts/eval_offline_metrics.py --k 10 --candidate-k 50
python scripts/eval_replay_metrics.py --k 10
```

See `docs/v1_metrics.md` before interpreting results.

## Test layers

```bash
python -m pytest -q

ZHIHUREC_DATABASE_URL='mysql+pymysql://root:root@127.0.0.1:3306/zhihurec_demo' \
  python -m pytest -q -m "mysql and not kafka"

ZHIHUREC_DATABASE_URL='mysql+pymysql://root:root@127.0.0.1:3306/zhihurec_demo' \
ZHIHUREC_KAFKA_BOOTSTRAP_SERVERS='127.0.0.1:9092' \
ZHIHUREC_EVENT_MODE=kafka_async \
  python -m pytest -q -m kafka
```

## Stop dependencies

```bash
docker compose -f docker-compose.kafka.yml down
docker compose down
```

Add `-v` only when intentionally deleting local volumes.

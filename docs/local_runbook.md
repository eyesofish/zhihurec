# NewsIntentRec Local Runbook

## Prerequisites

- Python 3.13
- Docker with Compose
- Node.js 20+

```bash
python -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
cd product-frontend && npm ci && cd ..
```

## Bootstrap

```bash
PYTHON=.venv/bin/python scripts/init_local.sh --product-frontend
```

Use `--smoke-test` for a one-shot run and `--with-kafka` to start Kafka, the profile
consumer, and the outbox publisher.

Key variables:

- `NEWSREC_DATABASE_URL`
- `NEWSREC_DEMO_SEED_DIR` (default `build/mind_demo_world`)
- `NEWSREC_MODEL_DIR` (default `build/mind_models`)
- `NEWSREC_EVENT_MODE`
- `NEWSREC_KAFKA_*`
- `VITE_NEWSREC_API_BASE`

`ZHIHUREC_*` aliases are accepted for one migration cycle and emit deprecation logs.

## Data and model rebuild

```bash
python scripts/download_mind.py --variant small --split all --accept-license --source huyva
python scripts/inspect_mind.py --variant small
python scripts/normalize_mind.py
python scripts/build_mind_demo_world.py
python scripts/import_demo_world.py \
  --input-dir build/mind_demo_world \
  --output-sql build/mind_demo_world/import_demo_world.sql \
  --truncate-first
python scripts/train_eval_mind.py
python scripts/report_mind_data.py
```

## Manual services

```bash
docker compose up -d
export NEWSREC_DATABASE_URL='mysql+pymysql://root:root@127.0.0.1:3306/newsrec_demo'
python scripts/apply_demo_mysql.py
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

For Kafka:

```bash
docker compose -f docker-compose.kafka.yml up -d
docker compose -f docker-compose.kafka.yml run --rm kafka-init
export NEWSREC_EVENT_MODE=kafka_async
export NEWSREC_KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092
python scripts/run_profile_consumer.py
python scripts/run_outbox_publisher.py
```

## Verification

```bash
python -m ruff check backend scripts tests
python -m mypy
python -m pytest -q
cd product-frontend && npm test -- --run && npm run build
```

Health endpoints: `/livez`, `/readyz`, `/healthz`, and `/metrics`.

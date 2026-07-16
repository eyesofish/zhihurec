# ZhihuRec Backend

FastAPI logical monolith for feed/search serving, event ingestion, profile state,
sponsored delivery, health, and observability.

## Runtime boundary

- MySQL is the online source of truth.
- `MysqlRuntimeRepository` owns serving orchestration and uses a bounded PyMySQL pool.
- `user_profile` JSON mutations are serialized with `SELECT ... FOR UPDATE`.
- `UnwiredRuntimeRepository` keeps imports and liveness available when no database URL is
  configured; business endpoints and readiness return 503.
- LightGBM and ALS artifacts are optional and schema-validated before serving.

## Event modes

- `sync_mysql`: mutate event/profile state synchronously.
- `kafka_dual_write`: commit the MySQL mutation and raw-event outbox row atomically.
- `kafka_async`: durably stage the raw event in MySQL Outbox and let the consumer mutate
  profile state.

`backend/app/events/consumer.py` validates schemas, preserves user-key ordering,
deduplicates by external event ID, retries transient failures, sends poison messages to
the DLQ, and writes training interactions through the durable outbox.

Run workers:

```bash
python scripts/run_profile_consumer.py
python scripts/run_outbox_publisher.py
```

## API groups

- recommendation: `/feed`;
- search: `/search`, `/search/suggestions`;
- product content: `/personas`, `/answers/{answer_id}`;
- events: legacy click endpoints plus `/event/track`;
- debugging: `/debug/profile`;
- system: `/livez`, `/readyz`, `/healthz`, `/metrics`.

The feed response is backward-compatible and adds `content_type` plus nullable sponsored
metadata. Sponsored delivery uses existing answer cards and a separate eligibility,
budget, pacing, frequency, and ledger path.

## Run

```bash
export ZHIHUREC_DATABASE_URL='mysql+pymysql://root:root@127.0.0.1:3306/zhihurec_demo'
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Use `scripts/init_local.sh` or `scripts/init_local.ps1` for the complete stack.

## Quality

```bash
python -m ruff check backend scripts tests
python -m mypy
python -m pytest -q
python -m pytest -q -m "mysql and not kafka"
python -m pytest -q -m kafka
```

The integration commands require the dependencies described in
`docs/v1_local_runbook.md`; CI provisions them automatically.

# 06 - Verification And Rollout

## Goal

Define how to prove the Kafka V2 path works without breaking the current V1 demo.

## Baseline checks

These must still pass without Kafka:

```powershell
python -m pytest -v
python -m ruff check backend\ scripts\ tests\
python -m mypy
cd product-frontend
npm run build
```

The MySQL-backed V1 smoke must still work in `sync_mysql` mode:

```powershell
docker compose up -d
$env:ZHIHUREC_DATABASE_URL='mysql+pymysql://root:root@127.0.0.1:3306/zhihurec_demo'
python scripts/apply_demo_mysql.py
python scripts/reset_demo_user.py
python -m pytest -v -m mysql
```

Kafka dependency install:

```powershell
python -m pip install -r backend\requirements-dev.txt
```

## Kafka infra smoke

Checks:

- Kafka container starts.
- All planned topics exist.
- Produce one test event to `zhihurec.events.raw`.
- Consume it back by key.
- Stop Kafka without affecting MySQL-only startup.

Commands:

```powershell
docker compose -f docker-compose.yml -f docker-compose.kafka.yml up -d
docker exec zhihurec-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server 127.0.0.1:9092 --list
```

## Dual-write verification

In `kafka_dual_write` mode:

1. Start MySQL and Kafka.
2. Start backend.
3. Trigger `/search`, `/event/track` upvote, and search-result click.
4. Confirm API response still matches V1 behavior.
5. Confirm corresponding Kafka events exist.
6. Confirm consumer can process the same events idempotently.

This mode is the safety bridge. Do not skip it.

Minimal env:

```powershell
$env:ZHIHUREC_EVENT_MODE='kafka_dual_write'
$env:ZHIHUREC_KAFKA_BOOTSTRAP_SERVERS='127.0.0.1:9092'
```

## Async verification

In `kafka_async` mode:

1. Reset demo user.
2. Capture initial profile.
3. Publish event through API.
4. Confirm API returns accepted/queued response.
5. Poll `/debug/profile` until the consumer-applied update appears.
6. Confirm `behavior_score` and recent event tails change exactly once.
7. Reprocess the same event and confirm no duplicate profile delta.

Run the consumer in a second shell:

```powershell
$env:ZHIHUREC_EVENT_MODE='kafka_async'
$env:ZHIHUREC_KAFKA_BOOTSTRAP_SERVERS='127.0.0.1:9092'
python scripts\run_profile_consumer.py
```

## Frontend checks

The product frontend should tolerate eventual consistency:

- search/click/upvote can show "event accepted" if profile refresh is delayed
- right-rail profile panel refreshes after the consumer applies the update
- no UI copy should imply a synchronous profile update in `kafka_async` mode

## Demo story

Honest V2 story:

> V1 proved the search/recommendation/profile loop synchronously. V2 introduces Kafka at the event boundary so search and interaction signals become replayable, consumers can update profiles asynchronously, and the same stream can feed future retrieval/ranking training data.

Do not claim:

- Kafka improved ranking quality by itself.
- The app is now a production-scale distributed system.
- Async profile updates are strictly better for the demo UX.

## Done condition

- V1 checks still pass.
- Kafka topics and producer/consumer smoke pass.
- Dual-write mode proves compatibility.
- Async mode proves eventual profile update and idempotency.
- Docs clearly explain the trade-off.

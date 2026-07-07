# 02 - Kafka Local Infrastructure

## Goal

Plan a local Kafka setup that can run alongside the existing MySQL container without making Kafka required for the default V1 path.

## Preferred local topology

Use `apache/kafka:3.9.1` as a single-node Kafka broker in KRaft mode.

Reasons:

- No ZooKeeper sidecar.
- Closer to modern Kafka deployments.
- Enough for local event-stream smoke tests.

## Compose strategy

Keep the existing MySQL-only `docker-compose.yml` behavior safe. The first implementation uses a separate `docker-compose.kafka.yml`, so users who only want V1 MySQL are unaffected.

## Planned services

| Service | Purpose |
|---|---|
| `mysql` | Existing V1 serving store |
| `kafka` | Single-node broker for V2 event stream |
| `kafka-init` | One-shot topic creation/check script |

Optional later:

| Service | Purpose |
|---|---|
| `kafka-ui` | Local topic inspection during demos |

## Planned topics

- `zhihurec.events.raw`
- `zhihurec.profile.update_commands`
- `zhihurec.training.interactions`
- `zhihurec.events.dlq`

## Local configuration

Planned environment variables:

```text
ZHIHUREC_EVENT_MODE=sync_mysql
ZHIHUREC_KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092
ZHIHUREC_KAFKA_CLIENT_ID=zhihurec-api
ZHIHUREC_KAFKA_PROFILE_GROUP_ID=zhihurec-profile-consumer
```

## Health checks

The infra plan should include:

- broker process is listening
- topic list command succeeds
- all planned topics exist
- a test message can be produced and consumed

## Teardown

Document two teardown levels:

```powershell
docker compose -f docker-compose.yml -f docker-compose.kafka.yml down
docker compose -f docker-compose.yml -f docker-compose.kafka.yml down -v
```

The first keeps data. The second removes local broker/MySQL volumes.

## Done condition

- Kafka can start independently from app code changes.
- Topic bootstrap is deterministic.
- V1 MySQL-only smoke still works when Kafka is not started.

## First-cut commands

Start MySQL + Kafka:

```powershell
docker compose -f docker-compose.yml -f docker-compose.kafka.yml up -d
```

List topics:

```powershell
docker exec zhihurec-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server 127.0.0.1:9092 --list
```

Stop:

```powershell
docker compose -f docker-compose.yml -f docker-compose.kafka.yml down
```

# Task Plan: ZhihuRec V2 Kafka Upgrade

## Overall goal

Turn the current V1/V1.5 ZhihuRec demo into a V2 architecture plan where user behavior events flow through Kafka before driving profile updates and training-sample generation.

V2 should preserve the current product loop:

```text
feed/search UI -> FastAPI -> MySQL-backed feed/profile/search
```

but add a durable event stream:

```text
search/click/upvote -> Kafka raw event topic -> profile consumer -> MySQL profile + training topic
```

Kafka is introduced for event decoupling and replayable training data, not for premature full microservice migration.

## Subproblems

1. `01-architecture-boundary.md` - define what changes in V2 and what remains V1-compatible - status: implemented-first-cut
2. `02-kafka-local-infra.md` - add a local single-node Kafka setup and topic bootstrap - status: implemented-first-cut
3. `03-event-contracts-and-topics.md` - define event schemas, topics, partition keys, idempotency, and DLQ behavior - status: implemented-first-cut
4. `04-backend-producer-path.md` - add producer integration for `/search`, legacy click routes, and `/event/track` - status: implemented-first-cut
5. `05-profile-consumer-and-training-sink.md` - add profile-update consumer and training-example sink - status: implemented-first-cut
6. `06-verification-and-rollout.md` - define validation, rollout modes, and demo story - status: implemented-first-cut

## Dependencies

Step 1 must happen first because it protects the V1 boundary: Kafka is a V2 feature and V1 must still run without it.

Step 2 can start after Step 1 because infra choices depend on the local-development boundary.

Step 3 depends on Step 1 because the event contracts must reflect the exact V2 behavior being decoupled from the current synchronous MySQL path.

Step 4 and Step 5 both depend on Step 3. Producers and consumers must share the same schema, topic names, partitioning rule, and idempotency contract.

Step 6 depends on Steps 2-5 because verification must cover infra, producer, consumer, and compatibility modes.

## Recommended execution order

1. Write and review the architecture boundary.
2. Add local Kafka infra as an optional V2 compose profile or separate compose file.
3. Freeze event topic names and schema version `1`.
4. Add a producer abstraction while keeping the existing synchronous MySQL path as the default.
5. Add `kafka_dual_write` mode before any asynchronous behavior becomes the default.
6. Add the profile consumer and training sink.
7. Only after dual-write verification, add `kafka_async` mode for the V2 demo path.

## Non-goals

- Do not change V1's default behavior.
- Do not require Kafka for `python -m pytest`, `/healthz`, or the current product frontend demo.
- Do not split every module into microservices in the first Kafka step.
- Do not replace MySQL as the serving store for feed/search/profile.
- Do not add authentication, deployment infrastructure, or unrelated Redis work as part of this plan.

## V2 architecture summary

| Area | V1 behavior | V2 Kafka plan |
|---|---|---|
| Event ingestion | API writes event/profile state synchronously in MySQL | API publishes normalized events to Kafka |
| Profile update | Happens inside request path | Happens in a consumer worker |
| Training examples | Derived offline or from DB snapshots | Emitted from event stream into `zhihurec.training.interactions` |
| Failure handling | Request transaction fails or succeeds | At-least-once delivery + idempotent consumer + DLQ |
| Consistency | Immediate profile update | Eventual consistency in `kafka_async`; immediate behavior preserved in `sync_mysql` |
| Local dev | MySQL only | MySQL only by default; Kafka optional for V2 smoke |

## Current handoff

This is now the in-repository V2 plan for Kafka-backed event streaming. Older references to the external `D:\Github\reco_learn_path\upgrade_v2` path should be treated as historical context unless that directory is explicitly restored.

First-cut implementation files:

- `docker-compose.kafka.yml`
- `backend/app/events/schema.py`
- `backend/app/events/publisher.py`
- `backend/app/events/consumer.py`
- `scripts/run_profile_consumer.py`
- `sql/v1_schema.sql` (`user_event.external_event_id` idempotency key)

Default behavior remains `ZHIHUREC_EVENT_MODE=sync_mysql`.

## Resume prompt

```text
Continue in the zhihurec repository.

Read:
- plan/project_brief_zh.md
- plan/zhihurec-v2-kafka-upgrade/README.md
- docs/v1_api_contract.md
- backend/app/repositories/mysql.py
- backend/app/routers/event_track.py

Goal:
Implement the V2 Kafka event-stream plan without breaking the V1 default path.

Execution order:
1. Start from 01-architecture-boundary.md.
2. Add optional Kafka local infra.
3. Freeze event contracts and topic names.
4. Add producer abstraction with sync_mysql default.
5. Add kafka_dual_write mode.
6. Add profile consumer and training sink.
7. Verify sync mode, dual-write mode, and async mode separately.
```

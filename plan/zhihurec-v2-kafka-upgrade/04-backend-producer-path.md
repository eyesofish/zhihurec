# 04 - Backend Producer Path

## Goal

Plan how the existing API writes user behavior events into Kafka without breaking the current synchronous MySQL path.

## Producer abstraction

Add a small event-publishing boundary rather than importing Kafka clients directly inside route handlers.

Implemented shape:

```text
backend/app/events/
  publisher.py
  schema.py
  consumer.py
```

Kafka client details are kept out of routers. `MysqlRuntimeRepository` builds normalized events and uses the publisher abstraction.

## Event modes

Configuration:

```text
ZHIHUREC_EVENT_MODE=sync_mysql|kafka_dual_write|kafka_async
```

### `sync_mysql`

Current behavior:

- event endpoint writes MySQL
- profile update happens in request path
- no Kafka required

### `kafka_dual_write`

Safe verification mode:

- current MySQL write/update still happens
- normalized event is also published to `zhihurec.events.raw`
- response semantics remain close to V1
- consumer output can be compared with the synchronous result

### `kafka_async`

V2 target mode:

- request validates event and publishes to Kafka
- profile update happens in consumer
- response should honestly report queued/accepted state
- frontend should refresh profile with eventual consistency in mind

## Routes to cover

- `POST /search`
- `POST /event/recommendation_click`
- `POST /event/search_result_click`
- `POST /event/track`

`GET /feed` does not publish events unless feed impressions are explicitly enabled. Product frontend already sends `feed_impression` through `/event/track`, so feed route should stay read-only.

## Failure behavior

Recommended behavior by mode:

| Mode | Kafka publish failure |
|---|---|
| `sync_mysql` | Not applicable |
| `kafka_dual_write` | Return success for MySQL write but log/persist publish failure for investigation |
| `kafka_async` | Return 503 or explicit publish failure; do not pretend the event was accepted |

Do not silently swallow Kafka failures in `kafka_async`.

## Event IDs

Use one of:

- client-provided `client_event_id` when available
- server-generated UUID
- deterministic ID from request ID + event type + user ID + answer/query + timestamp when replaying

The event ID must flow to the consumer and MySQL event row.

## Done condition

- Producer path has a documented mode switch.
- Existing sync behavior remains the default.
- All event-producing routes map to one normalized event schema.
- Kafka failures have explicit behavior.

## First-cut implementation notes

- `sync_mysql`: current synchronous profile behavior remains default.
- `kafka_dual_write`: MySQL commits first, then publishes `UserEventMessage` to `zhihurec.events.raw`; publish failure is logged and does not roll back the already successful MySQL request.
- `kafka_async`: event-producing routes publish to Kafka and skip synchronous profile mutation. Publish failure is surfaced as `event_publish_failed` with HTTP 503.
- `user_event.external_event_id` stores the V2 event id for idempotency.

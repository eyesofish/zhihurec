# 03 - Event Contracts And Topics

## Goal

Freeze the event schema and Kafka topic semantics before producers or consumers are implemented.

## Raw event topic

Topic:

```text
zhihurec.events.raw
```

Purpose:

Store normalized user behavior events emitted by FastAPI.

Partition key:

```text
user_id
```

Reason:

Profile updates are per-user state transitions. Partitioning by `user_id` preserves event order for one user while allowing different users to process in parallel.

## Schema version 1

Required fields:

```json
{
  "schema_version": 1,
  "event_id": "uuid-or-deterministic-id",
  "event_type": "search_query",
  "user_id": 7248,
  "answer_id": null,
  "query_key": "248 12125",
  "request_id": "zhihurec-feed-...",
  "surface": "search",
  "event_ts": 1713399900,
  "producer_ts": 1713399901,
  "source": "api"
}
```

Allowed `event_type` values should start from the existing product contract:

- `search_query`
- `recommendation_click`
- `search_result_click`
- `upvote`
- `feed_impression`
- `detail_view`
- `dwell`
- `downvote`
- `share`

Optional fields:

- `dwell_ms`
- `query_text`
- `debug`
- `client_event_id`
- `trace_id`

## Derived topics

### `zhihurec.profile.update_commands`

Purpose:

Optional intermediate topic if profile updates need a separate command shape after raw-event validation.

This can be deferred until raw-event consumer complexity justifies it.

### `zhihurec.training.interactions`

Purpose:

Append compact model-training examples after event normalization.

Example fields:

```json
{
  "schema_version": 1,
  "example_id": "event_id",
  "user_id": 7248,
  "answer_id": 123,
  "query_key": "248 12125",
  "label": 1,
  "event_type": "upvote",
  "event_ts": 1713399900,
  "source": "profile-consumer"
}
```

### `zhihurec.events.dlq`

Purpose:

Store malformed or permanently failing messages with enough context to debug.

Required DLQ fields:

- original topic
- original partition
- original offset
- original payload
- error type
- error message
- failed_at timestamp

## Idempotency

Delivery should be treated as at-least-once.

Rules:

- Every event must have an `event_id`.
- Consumer writes must be idempotent by `event_id`.
- MySQL should eventually have a uniqueness constraint or logical guard for event replay.
- A duplicate Kafka message must not increment `behavior_score` twice.

## Compatibility

The event schema should be derived from current Pydantic request models, but it should not expose internal-only Python object shapes. Kafka payloads are a public internal contract and need explicit schema versioning.

## Done condition

- Topic names are stable.
- Partitioning rule is documented.
- Required fields are sufficient for existing V1 event semantics.
- Duplicate-event behavior is specified before implementation.


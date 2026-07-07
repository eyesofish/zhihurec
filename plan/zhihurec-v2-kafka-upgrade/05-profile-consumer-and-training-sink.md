# 05 - Profile Consumer And Training Sink

## Goal

Plan the worker that consumes Kafka events, updates MySQL profile state, and emits training examples for future retrieval/ranking models.

## Consumer role

Input:

```text
zhihurec.events.raw
```

Outputs:

```text
MySQL user_event
MySQL user_profile
zhihurec.training.interactions
zhihurec.events.dlq
```

## Profile update semantics

The consumer should preserve the current business rules:

- `search_query` updates recent queries and behavior score.
- `recommendation_click` updates recent clicked answers and answer-topic weights.
- `search_result_click` combines query topics and answer topics, with stronger overlap boost.
- `upvote` behaves like a positive recommendation click.
- `feed_impression`, `detail_view`, `dwell`, `downvote`, and `share` are initially log-only unless V2 explicitly defines new profile deltas.

Implementation should reuse existing helpers from repository/DAO code where possible. Do not duplicate scoring constants in the worker.

## Offset and transaction strategy

Target behavior:

1. Consume message.
2. Validate schema.
3. Begin MySQL transaction.
4. Check whether `event_id` was already applied.
5. Write event row and profile update.
6. Commit MySQL transaction.
7. Produce training interaction if applicable.
8. Commit Kafka offset.

If step 7 fails after MySQL commit, either retry training production or produce from a separate durable outbox. Do not roll back a successful profile update only because training-sink production failed.

## Idempotency

The consumer must tolerate reprocessing.

Rules:

- duplicate event: no second profile delta
- malformed event: DLQ
- unknown event type: DLQ unless explicitly configured as log-only
- transient MySQL/Kafka errors: retry

## Training interaction labels

Initial mapping:

| Event type | Label |
|---|---:|
| `search_result_click` | 1 |
| `recommendation_click` | 1 |
| `upvote` | 1 |
| `downvote` | 0 |
| `feed_impression` | 0 or unlabeled impression |
| `detail_view` | weak positive, optional |
| `dwell` | depends on `dwell_ms`, optional |

Keep this simple in the first V2 implementation. The main value is creating a replayable stream, not inventing a perfect label strategy immediately.

## Done condition

- Consumer plan preserves existing profile math.
- Duplicate handling is specified.
- DLQ behavior is specified.
- Training sink has a minimal, honest label mapping.

## First-cut implementation notes

- Worker entrypoint: `scripts/run_profile_consumer.py`.
- Core applier: `backend/app/events/consumer.py`.
- The applier checks `user_event.external_event_id` before applying profile deltas.
- Positive labels are emitted for `recommendation_click`, `search_result_click`, and `upvote`.
- `downvote` and `feed_impression` emit label `0` when an `answer_id` is present.
- Malformed consumed messages are routed to `zhihurec.events.dlq` by the consumer loop.

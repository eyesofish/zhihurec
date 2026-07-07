# 01 - Architecture Boundary

## Goal

Define the V2 Kafka boundary without weakening the current V1 guarantee: the app must still run as a simple FastAPI + MySQL product demo when Kafka is absent.

## Current V1 behavior

- FastAPI handles feed/search/event/profile routes.
- MySQL is the online source of truth.
- `/search`, `/event/recommendation_click`, `/event/search_result_click`, and `/event/track` write events and update profile state synchronously.
- The product frontend expects profile changes to be visible quickly after search/click/upvote.

## V2 change

Kafka becomes the event log between request handling and downstream state updates.

```text
FastAPI producer
  -> zhihurec.events.raw
  -> profile consumer
  -> MySQL user_event/user_profile
  -> zhihurec.training.interactions
```

## Modes

| Mode | Runtime behavior | Intended use |
|---|---|---|
| `sync_mysql` | Current V1 synchronous MySQL writes and profile updates | Default, tests, simple local demo |
| `kafka_dual_write` | Keep current MySQL behavior, also publish events to Kafka | Safe V2 verification |
| `kafka_async` | Publish event to Kafka; consumer performs profile update | V2 event-stream demo |

## Boundary rules

- `sync_mysql` must remain the default.
- Kafka config must be optional.
- Existing non-MySQL tests must not need a running broker.
- MySQL remains the serving store for profile/feed/search reads.
- Consumer logic should reuse or extract the current profile-update semantics instead of duplicating formulas by hand.
- `kafka_async` changes consistency semantics; the frontend and docs must call out eventual consistency.

## Why not full microservices immediately

The project story is stronger if Kafka is introduced for a concrete bottleneck:

> user events need to be replayable, decoupled from request latency, and reusable for model training.

That is easier to defend than saying the whole monolith was split because "real systems use microservices." The first V2 cut should isolate the event path only.

## Done condition

- README and follow-up plan files clearly say Kafka is V2-only.
- V1 no-queue non-goals remain true.
- Future implementation can add Kafka without making V1 startup or tests heavier.


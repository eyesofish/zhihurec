# ZhihuRec API Contract

## Runtime data flow

```text
raw ZhihuRec CSVs or compact fixture
  -> scripts/build_demo_world.py / scripts/build_demo_fixture.py
  -> scripts/import_demo_world.py
  -> MySQL
  -> FastAPI
```

Raw CSV files are never read by online endpoints. ZhihuRec does not contain public
question/answer/author/topic text, so display strings remain synthetic while IDs retain
their dataset semantics.

## `GET /feed`

Query parameters:

- `user_id` required;
- `page_size` 1-50, default 10;
- `debug` default false;
- `experiment_arm`: `default`, `manual`, `manual_plus_als`, `lgb_plus_als`, or
  `lgb_plus_als_plus_search`;
- `include_sponsored` default true;
- `request_id`: optional client idempotency key for one logical feed load;
- `as_of_ts`: evaluation-only boundary for point-in-time popularity features.

The default organic candidate set can contain:

- `profile_topic`;
- `recent_query_topic`;
- `als_cf` using FAISS inner product;
- `hot_or_fresh`.

The default scorer uses a compatible LightGBM artifact when present and otherwise uses
the manual score. Explicit LightGBM arms fail if the artifact schema is missing or
incompatible; they never silently substitute the manual scorer.

Example item:

```json
{
  "answer_id": 456,
  "question_id": 321,
  "question_title": "Synthetic question title",
  "answer_summary": "Synthetic answer summary.",
  "author": {
    "author_id": 9001,
    "display_name": "Author 9001"
  },
  "topics": [
    {"topic_id": 12, "display_name": "Topic 12"}
  ],
  "selected_reason": "Selected because its topics match the user profile.",
  "scores": {
    "base_recall_score": 0.4,
    "personalized_topic_score": 0.2,
    "default_topic_score": 0.1,
    "topic_match_score": 0.18,
    "query_recall_boost": 0.0,
    "final_score": 0.58,
    "sponsored_score": null
  },
  "recall_sources": ["profile_topic"],
  "is_fallback": false,
  "content_type": "organic",
  "sponsored": null
}
```

Sponsored items use the same answer-card fields and add:

```json
{
  "content_type": "sponsored",
  "recall_sources": ["sponsored"],
  "sponsored": {
    "delivery_id": "ad-...",
    "campaign_id": 9001,
    "creative_id": 19001,
    "label": "Sponsored"
  }
}
```

The server reserves sponsored deliveries transactionally before responding. Eligibility
checks active window, topic targeting, budget, pacing, frequency cap, and content
availability. A 10-item page uses sponsored positions 3 and 8 when inventory is
eligible. Organic evaluation calls set `include_sponsored=false`.

With `debug=true`, the response includes:

- selected experiment arm;
- profile summary and cold-start mix;
- up to 50 organic recall candidates;
- sponsored candidate IDs, slots, score, and synthetic expected spend.

## `POST /search`

Request:

```json
{
  "user_id": 7248,
  "query_key": "248 12125",
  "query_text": "optional display query",
  "page_size": 10,
  "debug": true
}
```

The backend resolves the query, records `search_query`, updates recent-query profile
state in synchronous modes, retrieves topic-matched answers, and applies hot fallback.
In `kafka_async`, profile mutation occurs in the consumer.

## `POST /event/track`

Unified product event request:

```json
{
  "event_id": "imp-7248:feed-request:456",
  "user_id": 7248,
  "event_type": "feed_impression",
  "surface": "feed",
  "answer_id": 456,
  "query_key": null,
  "request_id": "feed-request",
  "sponsored_delivery_id": null,
  "dwell_ms": null,
  "debug": false
}
```

Allowed event types:

- `feed_impression`;
- `detail_view`;
- `dwell`;
- `upvote`;
- `downvote`;
- `share`;
- `recommendation_click`;
- `search_result_click`.

All listed event types require `answer_id`; `search_result_click` also requires
`query_key`, and `dwell` requires `dwell_ms` between 0 and 86,400,000. Frontend impression IDs are deterministic per
`(user_id, request_id, answer_id)`, and `user_event.external_event_id` makes retries
idempotent.

Profile semantics:

- recommendation click/upvote: answer-topic delta plus behavior delta;
- search-result click: query and answer topics, with a stronger overlap delta;
- impression/detail/dwell/downvote/share: log only.

Sponsored event requests carry only `sponsored_delivery_id`; the server loads and
validates campaign/creative facts from MySQL. A sponsored impression confirms the
delivery, and a sponsored recommendation click updates its click counters.

Response:

```json
{
  "ok": true,
  "event_type": "feed_impression",
  "profile_updated": false,
  "behavior_score": null
}
```

The legacy endpoints remain available:

- `POST /event/recommendation_click`;
- `POST /event/search_result_click`.

They accept additive optional `event_id` and `sponsored_delivery_id` fields.

## Read APIs

### `GET /debug/profile`

Returns the exact profile used by feed serving:

- topic weights;
- recent clicked answers;
- recent queries;
- behavior score;
- cold-start seed;
- vector summary.

### `GET /personas`

Lists demo users from `app_user.is_demo_user = 1`.

### `GET /search/suggestions`

Returns display labels and submit-ready `query_key` values from `query_topic_map`.

### `GET /answers/{answer_id}`

Returns the product answer card or 404.

## System endpoints

### `GET /livez`

Process liveness only. It remains 200 when dependencies fail.

### `GET /readyz` and `GET /healthz`

Readiness endpoints. They return 503 when:

- MySQL is missing or cannot answer `SELECT 1`;
- Kafka mode is enabled and the broker/required topics are unavailable;
- required worker heartbeats are stale or consumer lag is too high;
- the outbox has dead rows, excessive backlog, or an over-age pending row.

The body contains per-dependency status and outbox counts.

### `GET /metrics`

Prometheus text format for HTTP request count, latency, and errors. The consumer and
outbox workers expose their own metrics on ports 9101 and 9102 by default.

## Kafka event semantics

`UserEventMessage` and `TrainingInteractionMessage` are schema version 2.

- partition key: user ID;
- raw-event identity: `event_id`;
- profile mutation: idempotent in MySQL;
- training interaction: inserted into `event_outbox` in the same transaction as consumer
  state;
- feed impression training message: exposure with `label = null`; the trainer assigns
  the final label by reconciling later clicks with request/item identity;
- poison messages: DLQ before offset commit;
- transient failures: retry/backoff without offset commit.

The system provides at-least-once delivery with idempotent boundaries, not end-to-end
exactly-once processing.

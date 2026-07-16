# ZhihuRec HCI / Product Walkthrough

## 1. Interaction question

The product question is not whether users need another preference control. It is whether
a natural transition from feed browsing to search can update recommendation state in a
way that is visible and explainable when the user returns to the feed.

The implemented loop is:

```text
feed exposure/click
  -> search query
  -> query-topic resolution
  -> profile update
  -> next feed recall/ranking
```

This is a local mechanism prototype, not a deployed user study.

## 2. Data-backed motivation

The raw ZhihuRec analysis remains in `docs/data_analysis_report.md`.

- 999,970 feed-impression rows provide exposure context.
- 38,422 query rows show that search is not an edge behavior.
- 35.4667% of queries have same-user feed activity in the preceding 10 minutes.
- Query text is unavailable; the project uses token IDs and an offline query-topic
  bridge.

These observations motivate the mechanism but do not prove causal benefit.

## 3. Product personas

The current demo world contains three selected personas:

- user 7248;
- user 1026;
- user 3343.

Each has a distinct seeded profile and its own replay stream. The persona switcher changes
the active user, feed, search behavior, profile chart, and item-level impression identity.

There is no login/authentication system; the switcher is a controlled local-demonstration
device.

## 4. Verified walkthrough

The React/Vite product frontend runs at `http://127.0.0.1:5174`.

### Step 1: choose a persona

The top-right switcher selects one of the three demo users. A new feed request is issued,
and the right rail loads the exact profile used by serving.

### Step 2: inspect the feed

Each card shows:

- question/answer display copy;
- topic chips;
- recall/selection reason;
- organic or visibly labeled Sponsored status.

The browser sends one idempotent impression for every displayed answer, keyed by
`user_id`, `request_id`, and `answer_id`. A later request may legitimately record the same
answer again, and a persona switch records it for the new user.

### Step 3: search

The top navigation accepts a suggestion or query. Search updates recent-query state in
synchronous mode or through the Kafka consumer in asynchronous mode.

### Step 4: interact

Clicking a result/feed title or upvoting records the answer and request context. Positive
events update behavior score and answer/query topic weights. Sponsored title clicks also
reference the server-created delivery ledger.

### Step 5: inspect profile change

The right rail displays:

- behavior score;
- cold-start seed;
- D3 topic-weight chart;
- numeric topic weights;
- recent queries;
- recent clicked answers.

The view refreshes after state-changing actions.

### Step 6: return to the feed

The next feed exposes recall source, score decomposition, and cold-start mix in debug
mode. The latest leakage-safe replay produced a weighted Search Carryover Gain@10 of
`-0.0200` across 60 search events: one persona improved and two regressed. The UI makes
that instability inspectable rather than presenting the intervention as a win. See
`docs/v1_metrics.md`.

## 5. Explainability layers

### Item layer

`selected_reason`, `recall_sources`, `content_type`, and the Sponsored label explain the
card's path without opening developer tools.

### Request layer

`/feed?debug=true` includes:

- experiment arm;
- profile summary;
- organic recall candidates;
- cold-start alpha/default seed;
- sponsored candidate slot, score, and synthetic expected spend.

### Profile layer

`/debug/profile` exposes the same state consumed by feed serving.

### Operational layer

`/readyz`, `/metrics`, structured logs, worker metrics, event IDs, and outbox state let a
reviewer connect UI actions to backend processing and dependency health.

## 6. Evaluation status

No participant usability study was performed, so this document does not claim SUS,
trust, or qualitative interview results.

The currently completed evaluation consists of:

- reproducible product walkthrough;
- automated frontend tests for item-level impressions and sponsored labels;
- MySQL integration tests for profile updates and sponsored delivery;
- Kafka integration tests for raw event, training output, and DLQ;
- offline per-user/per-request ranking and Search Carryover metrics.

A future user study could use three tasks:

1. identify why a feed item was selected;
2. search for a topic and judge whether the next feed changed;
3. distinguish organic and sponsored cards and explain the label.

Suggested measures would be task completion, explanation accuracy, and a clearly
identified subjective questionnaire. Results must not be added until real participants
are observed.

## 7. Limitations

- Display text is synthetic because the dataset omits public content text.
- Three personas are not representative product traffic.
- Search Carryover is topic alignment, not satisfaction or causal engagement lift.
- LightGBM + cutoff-safe ALS is the strongest measured top-10 arm, but absolute
  Recall@10 remains low and adding the current search path reduces it.
- Sponsored expected spend is a serving-control abstraction, not billing.
- The project has no authentication, policy review, auction, attribution, conversion,
  calibration, or online experimentation.

## 8. Reproduce

```bash
PYTHON=.venv/bin/python scripts/init_local.sh --product-frontend
```

For the Kafka path:

```bash
PYTHON=.venv/bin/python scripts/init_local.sh --product-frontend --with-kafka
```

Use `docs/v1_local_runbook.md` for manual steps and `docs/v1_metrics.md` for the evidence
protocol.

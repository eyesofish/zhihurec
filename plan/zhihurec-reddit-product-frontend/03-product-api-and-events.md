# Subproblem 3: Product APIs and Unified Events

## 1. Goal

Add the backend API surface required by the product frontend:

- persona list
- search suggestions
- answer detail
- unified event tracking

## 2. Why this step exists

The current debug frontend can call feed, search, click, and profile endpoints directly. A product frontend needs more stable UI-oriented APIs and a single event endpoint for Reddit-like interactions.

## 3. Files involved

- `sql/v1_schema.sql` - extend `user_event.event_type`.
- `backend/app/schemas/` - add request/response models.
- `backend/app/routers/` - add product-facing routes.
- `backend/app/services/` - expose service methods.
- `backend/app/repositories/base.py` - extend runtime repository protocol.
- `backend/app/repositories/mysql.py` - implement MySQL-backed behavior.
- `backend/app/repositories/event_dao.py` - add generic event insertion helper.
- `backend/app/repositories/unwired.py` - keep unwired failure behavior.
- `backend/app/config.py` - include frontend port `5174` in default CORS origins.
- `docs/v1_api_contract.md` - document new API surface.
- `tests/` - add and update backend tests.

## 4. Exact changes

Add APIs:

```http
GET /personas
GET /search/suggestions?limit=12
GET /answers/{answer_id}
POST /event/track
```

`GET /personas` response:

```json
{
  "items": [
    {
      "user_id": 7248,
      "display_name": "User 7248",
      "behavior_score": 365.0,
      "top_topics": [{"topic_id": 46, "weight": 0.083333}]
    }
  ]
}
```

`GET /search/suggestions` response:

```json
{
  "items": [
    {
      "query_key": "248 12125",
      "label": "Query 248 12125",
      "topic_count": 5
    }
  ]
}
```

Use `query_topic_map.display_query` when present. Fall back to `Query {query_key}`.

`GET /answers/{answer_id}` response:

```json
{
  "answer_id": 123,
  "question_id": 456,
  "question_title": "Question 456",
  "answer_summary": "Synthetic answer summary for answer 123.",
  "author": {"author_id": 9, "display_name": "Author 9"},
  "topics": [{"topic_id": 46, "display_name": "Topic 46"}]
}
```

`POST /event/track` request:

```json
{
  "user_id": 7248,
  "event_type": "upvote",
  "surface": "home_feed",
  "answer_id": 123,
  "query_key": null,
  "request_id": "feed-...",
  "dwell_ms": null,
  "debug": true
}
```

Allowed event types:

- `feed_impression`
- `detail_view`
- `dwell`
- `upvote`
- `downvote`
- `share`
- `recommendation_click`
- `search_result_click`

Profile update rules:

- `recommendation_click` delegates to existing recommendation click logic.
- `search_result_click` delegates to existing search-result click logic.
- `upvote` applies the same positive profile update as recommendation click.
- `feed_impression`, `detail_view`, `dwell`, `downvote`, and `share` are log-only for V1.

Extend `user_event.event_type` ENUM to include the new values while keeping existing values.

Keep old endpoints:

- `POST /event/recommendation_click`
- `POST /event/search_result_click`

They must continue to work for the existing debug frontend.

## 5. Out of scope

- Do not implement real auth.
- Do not add comments or post creation.
- Do not add negative ranking or per-user suppression for downvotes in this step.
- Do not remove existing debug endpoints.

## 6. Done condition

The product frontend can load personas, search suggestions, answer details, and track Reddit-like events through stable APIs.

## 7. Verification

Run:

```powershell
python -m pytest -v
python -m pytest -v -m mysql
```

Add tests for:

- `/personas` returns three personas in MySQL mode.
- `/search/suggestions` returns submit-ready `query_key` values.
- `/answers/{answer_id}` returns an answer card payload.
- `/event/track` log-only events write `user_event` rows.
- `/event/track` `upvote` changes profile behavior score and recent clicked answers.
- unwired mode returns `503 repository_not_ready` for new business endpoints.

## 8. Expected output

Backend has a clean product API layer while preserving old debug compatibility.

## 9. Notes for the next step

The frontend can use only product-facing APIs except where it intentionally shows debug profile state.

## 10. Risks or ambiguity

Changing the `user_event.event_type` ENUM requires schema/import/test updates together. Do not update API code without updating SQL and generated import behavior.

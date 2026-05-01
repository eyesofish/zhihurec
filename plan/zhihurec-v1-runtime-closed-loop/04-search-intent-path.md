# Subproblem 4: Search Intent Path

## 1. Goal
Implement `POST /search` as a real closed-loop search intent endpoint.

The endpoint should record the search query, update the user's recent queries, find matching topics from `query_topic_map`, and return answer results through `query -> topic -> answer`.

## 2. Why this step exists
The project's main story is that search acts as a high-intent signal that affects later recommendation.

This step turns search from a route shell into the first write/read loop that future feed ranking can observe through `recent_queries_json`.

## 3. Files involved
- `backend/app/repositories/mysql.py` - implement `search()`.
- `backend/app/schemas/search.py` - add validation for `page_size` and `query_key` only if needed.
- `backend/app/schemas/feed.py` or shared helpers - reuse answer/topic card construction where practical.
- `docs/v1_api_contract.md` - update if the actual debug payload needs one small field such as fallback source.

## 4. Exact changes
- In `MysqlRuntimeRepository.search(payload)`, normalize `payload.query_key` by trimming repeated whitespace.
- Reject an empty normalized query key with a normal FastAPI validation error if this is handled in `SearchRequest`; otherwise raise a clear repository-level value error that maps to a 400 response in a later small error handler.
- Insert one row into `user_event`:
  - `event_type = 'search_query'`
  - `user_id = payload.user_id`
  - `query_key = normalized query key`
  - `surface = 'search'`
  - `source_confidence = 'confirmed'`
  - `event_ts = current Unix timestamp`
  - `query_tokens_json` parsed from the token IDs if possible
- Load `user_profile` for `payload.user_id`.
- Append the normalized query to `recent_queries_json`.
- Keep only the most recent 5 queries.
- Increase `behavior_score` by the configured search-query amount.
- Update `last_event_ts`.
- Query `query_topic_map` for the normalized query key ordered by:
  - `match_rank` ascending
  - `score` descending
- Use matched topics to find answer candidates through `answer_topic`.
- Score search results primarily by `query_topic_map.score`.
- Use `hot_answer_snapshot` only to backfill if fewer than `page_size` results are found.
- Return `SearchResponse`.
- Include `debug.matched_topics` and `debug.result_sources` only when `payload.debug` is true.

## 5. Out of scope
- Do not implement full-text search.
- Do not use online embeddings.
- Do not use raw `query_text` as a ranking feature.
- Do not trigger a feed refresh inside the search endpoint.
- Do not add frontend behavior in this step.

## 6. Done condition
With a seeded MySQL database:

- `POST /search` writes a `search_query` event.
- `user_profile.recent_queries_json` includes the new query.
- The response returns answer cards when the query exists in `query_topic_map`.
- Debug mode shows matched topics and result sources.

## 7. Verification
Use a query key that exists in the seeded data. One source is `build\demo_world\demo_user_profile_seed.json`, which contains recent query keys.

Example request shape:

```powershell
$body = @{
  user_id = 7248
  query_key = '<known query_key from demo_user_profile_seed.json>'
  query_text = 'demo query'
  page_size = 10
  debug = $true
} | ConvertTo-Json
Invoke-RestMethod 'http://127.0.0.1:8000/search' -Method Post -ContentType 'application/json' -Body $body
```

Expected result:

- response `user_id` is `7248`
- response `query_key` is the normalized query key
- response has `items`
- debug mode has `matched_topics`

Then verify profile changed:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/debug/profile?user_id=7248'
```

Expected result:

- `recent_queries` contains the posted query
- `behavior_score` is higher than before the search

Before a real DB is available, keep these import and schema checks passing:

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -c "from backend.app.main import app; print(sorted({route.path for route in app.routes}))"
& 'C:\ProgramData\anaconda3\python.exe' -c "from backend.app.schemas.search import SearchRequest; req=SearchRequest(user_id=7248, query_key='  18234   3402  ', page_size=10); print(req.query_key); print(req.page_size)"
```

Expected result:

- the route list still includes `/search`
- the second command prints normalized query key `18234 3402` and page size `10`

## 8. Expected output
Real search endpoint behavior plus profile carryover state for later feed calls.

## 9. Notes for the next step
Step 5 can assume search queries are persisted and can use `query_key` when processing a search result click.

## 10. Risks or ambiguity
Some query keys may have no matching topics after the compact demo-world selection. The endpoint should still return a valid empty or hot-backfilled response instead of failing.

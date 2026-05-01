# Subproblem 3: Feed And Profile Read Path

## 1. Goal
Implement the first real MySQL-backed read behavior:

- `GET /debug/profile`
- `GET /feed`

After this step, a seeded demo database should return real profile and feed data instead of `repository_not_ready`.

## 2. Why this step exists
Profile and feed are the safest first runtime slice because they mostly read existing tables.

They also prove that the backend can use `user_profile`, `answer`, `question`, `author`, `topic`, `answer_topic`, `query_topic_map`, and `hot_answer_snapshot` as the runtime source of truth.

## 3. Files involved
- `backend/app/repositories/mysql.py` - implement `get_debug_profile()` and `get_feed()`.
- `backend/app/schemas/profile.py` - keep the current response shape unless a field mismatch is discovered.
- `backend/app/schemas/feed.py` - adjust `FeedProfileSummary.top_topics` if needed so debug profile weights are not lost.
- `backend/app/schemas/common.py` - use existing `AuthorCard` and `TopicCard`; add a weighted topic model only if `feed.py` needs it.
- `docs/v1_api_contract.md` - update only if the response model changes in a small, intentional way.

## 4. Exact changes
- In `MysqlRuntimeRepository.get_debug_profile(user_id)`, query `user_profile` by `user_id`.
- Parse:
  - `topic_weights_json`
  - `recent_clicked_answers_json`
  - `recent_queries_json`
  - `behavior_score`
  - `cold_start_seed_key`
- Return `DebugProfileResponse`.
- Set `vector_summary.vector_key_count` to the number of topics or vector contributors available in the compact profile.
- Set `vector_summary.top_contributing_topics` from `topic_weights_json`.
- In `MysqlRuntimeRepository.get_feed(user_id, page_size, debug)`, load the profile first.
- Build a candidate pool from:
  - answers linked to the profile's top topics through `answer_topic`
  - recent query topics through `recent_queries_json -> query_topic_map -> answer_topic`
  - hot fallback rows through `hot_answer_snapshot`
- Join candidates to `answer`, `question`, `author`, and `topic` so every `FeedItem` has:
  - `answer_id`
  - `question_id`
  - `question_title`
  - `answer_summary`
  - `author`
  - `topics`
  - `selected_reason`
  - score fields
  - recall sources
  - fallback flag
- Compute simple explainable scores:
  - `base_recall_score` from normalized `answer.hot_score` or hot snapshot rank
  - `topic_match_score` from overlap between answer topics and profile topic weights
  - `query_recall_boost` from overlap between answer topics and recent query topics
  - `final_score = base_recall_score + topic_match_score + query_recall_boost`
- Sort by `final_score` descending, then `answer_id` ascending for stable tie-breaking.
- Return at most `page_size` items.
- If non-fallback candidates are fewer than `page_size`, fill the remaining slots from `hot_answer_snapshot`.
- Include `debug` only when `debug=true`.

## 5. Out of scope
- Do not implement vector search or ANN.
- Do not add Redis.
- Do not mutate `user_profile` in this step.
- Do not change endpoint paths.
- Do not make the frontend.

## 6. Done condition
With a seeded MySQL database and `ZHIHUREC_DATABASE_URL` set:

- `GET /debug/profile?user_id=7248` returns a real profile.
- `GET /feed?user_id=7248&page_size=10&debug=true` returns up to 10 answer cards.
- Feed items include debug scores and fallback markers.

## 7. Verification
After Step 6 has provided a seeded database path, run:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/debug/profile?user_id=7248'
Invoke-RestMethod 'http://127.0.0.1:8000/feed?user_id=7248&page_size=10&debug=true'
```

Expected result:

- profile response has `user_id = 7248`
- feed response has `items`
- each feed item has `question_title`, `answer_summary`, `author`, `topics`, and `scores`
- debug response has `profile_summary`, `recall_candidates`, and `fallback_used`

Before a real DB is available, keep this import check passing:

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -c "from backend.app.main import app; print(sorted({route.path for route in app.routes}))"
```

## 8. Expected output
Real read-only backend behavior for profile and feed.

## 9. Notes for the next step
Step 4 can reuse the answer-card and topic-card helper functions from this step for search results.

## 10. Risks or ambiguity
The current schema stores JSON in MySQL JSON columns. PyMySQL may return JSON values as strings depending on configuration. The repository should parse both string JSON and already-decoded Python values defensively.

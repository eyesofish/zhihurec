# Subproblem 5: Click Events And Profile Updates

## 1. Goal
Implement real behavior for:

- `POST /event/recommendation_click`
- `POST /event/search_result_click`

Both endpoints should write `user_event` rows and update `user_profile` synchronously.

## 2. Why this step exists
The V1 system is supposed to demonstrate a closed loop.

Search and feed are not enough by themselves. The project needs observable profile changes after user actions, especially stronger updates after a search-result click.

## 3. Files involved
- `backend/app/repositories/mysql.py` - implement `record_recommendation_click()` and `record_search_result_click()`.
- `backend/app/config.py` - add small configurable weights if needed.
- `backend/app/schemas/event.py` - keep the current request/response models unless a debug field is missing.
- `docs/v1_api_contract.md` - update only if the final debug response differs from the current documented shape.

## 4. Exact changes
- Add helper logic in the MySQL repository to load an answer's topics from `answer_topic`.
- Add helper logic to load query topics from `query_topic_map`.
- Add helper logic to update `topic_weights_json`:
  - read current topic weights
  - apply a small global decay
  - add deltas for new topics
  - keep only the top 10 topics
  - normalize or round weights so the debug output is stable
- For `record_recommendation_click(payload)`:
  - insert a `user_event` row with `event_type = 'recommendation_click'`
  - set `answer_id`, `request_id`, `surface = 'feed'`, and current Unix `event_ts`
  - update `recent_clicked_answers_json` with the clicked answer and timestamp
  - keep only the most recent 10 clicked answers
  - update topic weights using the answer's topics
  - increase `behavior_score` by the configured recommendation-click amount
  - return `EventAckResponse(ok=True, event_type='recommendation_click')`
  - if `debug=true`, include updated topic deltas, recent click tail, and behavior score
- For `record_search_result_click(payload)`:
  - insert a `user_event` row with `event_type = 'search_result_click'`
  - set `answer_id`, `query_key`, `request_id`, `surface = 'search'`, and current Unix `event_ts`
  - load query topics for `payload.query_key`
  - load answer topics for `payload.answer_id`
  - give overlap topics a stronger delta than topics appearing only on one side
  - update `recent_clicked_answers_json`
  - keep only the most recent 10 clicked answers
  - increase `behavior_score` by the configured search-result-click amount
  - return `EventAckResponse(ok=True, event_type='search_result_click')`
  - if `debug=true`, include query topics, answer topics, overlap topics, and behavior score

## 5. Out of scope
- Do not implement asynchronous event processing.
- Do not add a message queue.
- Do not retrain or rebuild item vectors.
- Do not return a new feed directly from the click endpoints.
- Do not add authentication.

## 6. Done condition
With a seeded MySQL database:

- Recommendation click writes one event and changes `recent_clicked_answers`.
- Search result click writes one event and changes `topic_weights`.
- Search result click has a stronger visible behavior score increase than recommendation click.
- `/debug/profile` reflects the updates immediately.

## 7. Verification
First get a feed item:

```powershell
$feed = Invoke-RestMethod 'http://127.0.0.1:8000/feed?user_id=7248&page_size=1&debug=true'
$answerId = $feed.items[0].answer_id
```

Post a recommendation click:

```powershell
$body = @{ user_id = 7248; answer_id = $answerId; request_id = $feed.request_id; debug = $true } | ConvertTo-Json
Invoke-RestMethod 'http://127.0.0.1:8000/event/recommendation_click' -Method Post -ContentType 'application/json' -Body $body
```

Expected result:

- response has `ok = true`
- response has `event_type = recommendation_click`
- debug has `updated_topics`

Then call:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/debug/profile?user_id=7248'
```

Expected result:

- `recent_clicked_answers` includes `$answerId`
- `behavior_score` increased

For search-result click, repeat with an answer returned by `/search` and include the same `query_key`.

Before a real DB is available, keep these import and config checks passing:

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -c "from backend.app.main import app; print(sorted({route.path for route in app.routes}))"
& 'C:\ProgramData\anaconda3\python.exe' -c "from backend.app.config import get_settings; s=get_settings(); print(s.recommendation_click_behavior_delta); print(s.search_result_click_behavior_delta); print(s.profile_topic_decay)"
```

Expected result:

- the route list still includes both click endpoints
- the second command prints the default click/profile tuning values

## 8. Expected output
Real event endpoints and observable profile mutation.

## 9. Notes for the next step
Step 6 can build reset and replay scripts around these stable endpoint behaviors.

## 10. Risks or ambiguity
Weight numbers are intentionally lightweight. The exact multipliers should be configurable and explained, not overfit. Keep the first version simple enough to debug from returned JSON.

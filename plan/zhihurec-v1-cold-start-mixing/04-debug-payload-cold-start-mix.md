# Subproblem 4: Debug Payload Cold Start Mix

## 1. Goal
Make the new mixing observable from the outside. After this step, `/feed?debug=true` returns enough information for a human reader to verify that alpha is being computed correctly and that the two components (`personalized` / `default`) blend in the expected way.

## 2. Why this step exists
gap-checklist B3 step 3's verification command is:
> 调一次 `/feed?debug=true`，debug 段里应能看到 alpha 或等价混合权重的数值。

Without surfaced fields, step 5's eval rerun is hard to interpret and the brief §17 "调试可见性" requirement is violated.

## 3. Files involved
- `backend/app/schemas/feed.py` — extend `FeedDebugPayload` and `FeedItemScores`.
- `backend/app/repositories/mysql.py` — populate the new fields in `get_feed`.
- `frontend/app.js` — optional, may render `cold_start_mix` if it is a small change. Defer if non-trivial.

## 4. Exact changes

### 4.1 `backend/app/schemas/feed.py`
- Add a new model:
  ```python
  class ColdStartMix(ApiModel):
      alpha: float
      behavior_score: float
      default_seed_key: str
      default_topic_count: int
  ```
- Extend `FeedItemScores` to include the two transparent components:
  ```python
  class FeedItemScores(ApiModel):
      base_recall_score: float
      personalized_topic_score: float
      default_topic_score: float
      topic_match_score: float
      query_recall_boost: float
      final_score: float
  ```
- Extend `FeedDebugPayload` with one optional field:
  ```python
  class FeedDebugPayload(ApiModel):
      profile_summary: FeedProfileSummary
      recall_candidates: list[RecallCandidateDebug]
      fallback_used: bool
      cold_start_mix: ColdStartMix
  ```

`extra="forbid"` is already on `ApiModel`, so adding fields is a hard contract change. That is intentional — V1 is internal, the API contract does not yet have external consumers, and the brief explicitly wants debug visibility.

### 4.2 `backend/app/repositories/mysql.py`
- Populate `personalized_topic_score` and `default_topic_score` on each `FeedItemScores` (these were already computed in step 3 — this is just naming them in the response).
- Construct the `cold_start_mix` block once:
  ```python
  cold_start_mix = ColdStartMix(
      alpha=round(alpha, 6),
      behavior_score=round(profile.behavior_score, 6),
      default_seed_key=profile.cold_start_seed_key or self._settings.cold_start_default_seed_key,
      default_topic_count=len(default_topic_weight_map),
  )
  ```
- Pass `cold_start_mix` into `FeedDebugPayload(...)` and into the empty-candidate early return as well, so the field is present even when there are zero candidates.

### 4.3 `frontend/app.js` (optional)
If the existing render for `/feed?debug=true` already prints the JSON blob, no change is needed — the new fields show up automatically. If it renders a curated view, add a one-line `Cold-start α: <alpha> @ behavior_score=<score>` near the existing debug panel header. Skip if the change is more than ~10 lines.

## 5. Out of scope
- Do not add new endpoints.
- Do not add fields outside `FeedDebugPayload` and `FeedItemScores` — `/search`, `/event/*`, `/debug/profile` stay the same.
- Do not add CSV/JSON dump tooling for the new fields.
- Do not back-fill the new fields when `debug=false`. The non-debug response keeps the new `personalized_topic_score` / `default_topic_score` only if they are part of the always-on score block; the `cold_start_mix` block remains debug-only.

## 6. Done condition
- `from backend.app.schemas.feed import ColdStartMix, FeedDebugPayload, FeedItemScores` succeeds.
- `/feed?user_id=7248&page_size=10&debug=true` JSON contains `debug.cold_start_mix.alpha` ∈ [0, 1] matching `compute_alpha(behavior_score, settings)` to 6 decimals.
- For every item, `scores.personalized_topic_score` and `scores.default_topic_score` are present, and `alpha * personalized + (1-alpha) * default` equals `topic_match_score` within rounding tolerance.

## 7. Verification

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -c "
from backend.app.schemas.feed import FeedDebugPayload, FeedItemScores, ColdStartMix
print('FeedDebugPayload fields:', list(FeedDebugPayload.model_fields))
print('FeedItemScores fields:',  list(FeedItemScores.model_fields))
print('ColdStartMix fields:',    list(ColdStartMix.model_fields))
"
```

Expected output:
- `FeedDebugPayload fields: ['profile_summary', 'recall_candidates', 'fallback_used', 'cold_start_mix']`
- `FeedItemScores fields: ['base_recall_score', 'personalized_topic_score', 'default_topic_score', 'topic_match_score', 'query_recall_boost', 'final_score']`
- `ColdStartMix fields: ['alpha', 'behavior_score', 'default_seed_key', 'default_topic_count']`

A live HTTP check is part of step 5.

## 8. Expected output
- `backend/app/schemas/feed.py` gains one model and two extra fields on existing models.
- `backend/app/repositories/mysql.py` constructs `ColdStartMix` once per request and emits the two new score components per item.
- Optional 1-2 line tweak to `frontend/app.js`.

## 9. Notes for the next step
Step 5 reads the debug payload to interpret the eval rerun. Specifically, it should record `cold_start_mix.alpha` for the demo user at the start and end of the replay so the doc can show how alpha moved.

## 10. Risks or ambiguity
- Adding required fields to a Pydantic model that uses `extra="forbid"` is a breaking schema change for any consumer. The current consumers are this repo's frontend and `eval_replay_metrics.py`, neither of which validates the response schema strictly — both use `dict.get(...)`. This is safe for V1 but should be flagged in the verification log so future API consumers know to refresh.
- Frontend rendering is optional in this step on purpose: if `app.js` already shows the raw debug JSON, no UI work is needed; if not, that work belongs in a follow-up plan.

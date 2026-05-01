# Subproblem 3: Feed Ranking Mixing

## 1. Goal
Make the feed ranking compute `topic_match_score` from a linear blend of the user's personalized topic weights and the cold-start seed's topic weights, with the blend driven by `compute_alpha(profile.behavior_score)`.

After this step, `final_score = base_recall_score + topic_match_score + query_recall_boost` still holds at the call site, but `topic_match_score` is internally `alpha * personalized + (1-alpha) * default`.

## 2. Why this step exists
This is the actual brief §7 / §18 implementation. Without it, `behavior_score` is recorded but does nothing during ranking, and the schema-level `cold_start_seed_key` is decorative.

Mixing at the topic-weight level (rather than at the score level) is cleaner because:
- The seed and the user share the same `[{topic_id, weight}]` shape.
- The downstream score formula does not branch — it still sums one topic-weight map over a candidate's topic ids.
- It is easy to expose two transparent components (`personalized_topic_score`, `default_topic_score`) without changing the recall pipeline.

## 3. Files involved
- `backend/app/repositories/mysql.py` — `MysqlRuntimeRepository.get_feed` plus a new `_load_default_seed_topic_weights` helper.
- `backend/app/dependencies.py` (or wherever `Settings` is currently injected into `MysqlRuntimeRepository`) — confirm the repository already has `self._settings`; add a property if not.
- No other application code changes in this step.

## 4. Exact changes
1. In `MysqlRuntimeRepository.get_feed` (around `mysql.py:106-213`):
   - After loading `profile`, also load the default seed:
     ```python
     default_topic_weight_map = self._load_default_seed_topic_weights(
         connection,
         seed_key=profile.cold_start_seed_key or self._settings.cold_start_default_seed_key,
     )
     ```
   - Compute `alpha`:
     ```python
     from backend.app.config import compute_alpha  # at module top, not in function

     alpha = compute_alpha(profile.behavior_score, self._settings)
     ```
   - In the per-candidate scoring loop (around `mysql.py:144-192`), replace the single `topic_match_score = ...` assignment with two parts:
     ```python
     personalized_topic_score = round(
         sum(topic_weight_map.get(t, 0.0) for t in topic_ids), 6
     )
     default_topic_score = round(
         sum(default_topic_weight_map.get(t, 0.0) for t in topic_ids), 6
     )
     topic_match_score = round(
         alpha * personalized_topic_score
         + (1.0 - alpha) * default_topic_score,
         6,
     )
     ```
   - `final_score = base_score + topic_match_score + query_recall_boost` stays unchanged.

2. Add `_load_default_seed_topic_weights(self, connection, *, seed_key) -> dict[int, float]`:
   ```python
   def _load_default_seed_topic_weights(
       self,
       connection: Any,
       *,
       seed_key: str,
   ) -> dict[int, float]:
       with connection.cursor() as cursor:
           cursor.execute(
               """
               SELECT topic_weights_json
               FROM system_profile_seed
               WHERE seed_key = %s
               """,
               (seed_key,),
           )
           row = cursor.fetchone()
       if row is None:
           return {}
       weights = self._parse_topic_weights(row.get("topic_weights_json"))
       return {item.topic_id: item.weight for item in weights}
   ```
   This reuses the existing `_parse_topic_weights` helper.

3. Cache the default seed map per request, not per candidate. The query above runs once inside `get_feed`.

4. Keep `query_recall_boost` exactly as it is. Brief §7 separates cold-start mixing from intent gating; mixing the intent boost by alpha would couple two orthogonal axes.

5. The empty-candidate early return path (`mysql.py:120-135`) does not need changes.

## 5. Out of scope
- Do not change the search ranking path.
- Do not change `recommendation_click` or `search_result_click` write paths.
- Do not change `base_recall_score` (the hot recall component) or alpha-gate it. Brief §6 / §11 treats hot as a recall fallback, not a personalization knob.
- Do not change `selected_reason` text in this step. Step 4 may add a `cold_start_mix` hint there if needed, but the default text from `_selected_reason` keeps working.
- Do not memoize `_load_default_seed_topic_weights` across requests — settings changes should take effect on the next request without restart cost.

## 6. Done condition
- `get_feed` calls `compute_alpha` exactly once per request.
- `get_feed` calls `_load_default_seed_topic_weights` exactly once per request.
- For every emitted feed item, `topic_match_score == round(alpha * personalized + (1-alpha) * default, 6)` within float tolerance.
- For `behavior_score = 0` and a fresh user with empty `topic_weights`, `topic_match_score` collapses to `(1 - alpha_floor) * default_topic_score`, which is non-zero whenever the seed has any topic overlap with the candidate.

## 7. Verification
Step 3 itself does not require a live container, but a quick offline check is useful:

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -c "
from backend.app.main import app
print(app.title)
print(sorted({route.path for route in app.routes}))
"
```

Expected: the FastAPI app still imports cleanly, the route list still contains `/feed`, `/search`, `/event/recommendation_click`, `/event/search_result_click`, `/debug/profile`, `/healthz`. Static analysis only — full HTTP verification is the job of step 5.

## 8. Expected output
A diff in `backend/app/repositories/mysql.py` that:
- Adds one import for `compute_alpha`.
- Adds one helper method (~12 lines).
- Replaces ~3 lines in the per-candidate loop with ~8 lines that compute the two components and the blended score.

No schema changes, no contract changes (the response shape is identical at this step).

## 9. Notes for the next step
Step 4 will add the new debug fields. Until step 4 lands, the new mixing is silent — there is no way for a caller to inspect alpha — but the math is already in place.

## 10. Risks or ambiguity
- If a user references a `cold_start_seed_key` that does not exist (FK violation in the wild would prevent this, but defensive code is cheap), `_load_default_seed_topic_weights` returns `{}`, which makes `default_topic_score = 0` and the math degenerates to `alpha * personalized`. That degradation is acceptable as a fallback.
- Rounding inside the per-candidate loop preserves the existing `final_score` precision; the new intermediate rounds may produce slightly different scores than the old single-step computation in edge cases. Acceptable.
- `query_recall_boost` is intentionally left out of the alpha gate. If a future plan wants to gate intent by alpha (e.g., dampen personalization-driven boosts when alpha is low), it should do so in a new plan and explicitly justify against brief §7 / §11.

# Subproblem 2: Alpha Function And Settings

## 1. Goal
Introduce a single, well-defined function that converts `behavior_score` into a mixing weight `alpha ∈ [floor, ceiling]`, plus the tunable settings that drive it.

After this step, any caller can ask `compute_alpha(behavior_score) -> float` and get a smooth, monotone, bounded output, without yet wiring it into the feed path.

## 2. Why this step exists
Brief §7 (lines 629-637) explicitly forbids hard-coding a formula in the brief while still requiring a monotone "more behavior → higher personalization weight" relationship. Putting the function in `backend/app/config.py` (where the other tunable scalars already live) keeps the parameter location consistent and avoids burying the curve inside `mysql.py`.

Doing this in its own step also lets us review the alpha shape on paper before committing to the integration in step 3.

## 3. Files involved
- `backend/app/config.py` — add four parameters and `compute_alpha`.
- No other application code changes in this step.

## 4. Exact changes
- Add four fields to the `Settings` dataclass:
  - `cold_start_alpha_floor: float = 0.1`
  - `cold_start_alpha_ceiling: float = 0.95`
  - `cold_start_behavior_score_scale: float = 30.0`
  - `cold_start_default_seed_key: str = "cold_start_default"`
- Add the corresponding env-var overrides in `get_settings()`:
  - `ZHIHUREC_COLD_START_ALPHA_FLOOR`
  - `ZHIHUREC_COLD_START_ALPHA_CEILING`
  - `ZHIHUREC_COLD_START_BEHAVIOR_SCORE_SCALE`
  - `ZHIHUREC_COLD_START_DEFAULT_SEED_KEY`
- Add a free function `compute_alpha(behavior_score: float, settings: Settings) -> float` in the same file, defined as:

  ```python
  def compute_alpha(behavior_score: float, settings: Settings) -> float:
      score = max(0.0, behavior_score)
      raw = score / (score + settings.cold_start_behavior_score_scale)
      span = settings.cold_start_alpha_ceiling - settings.cold_start_alpha_floor
      return settings.cold_start_alpha_floor + raw * span
  ```

  Properties:
  - `compute_alpha(0, s)` returns `s.cold_start_alpha_floor` exactly.
  - As `behavior_score → ∞`, the result approaches `s.cold_start_alpha_ceiling`.
  - The function is monotone non-decreasing in `behavior_score`.
  - At `behavior_score == scale`, `raw = 0.5`, so alpha is the midpoint.

- Do not memoize — the function is cheap and pure.
- Do not call `compute_alpha` from anywhere yet.

## 5. Out of scope
- Do not import `compute_alpha` into `mysql.py`, `feed.py`, or any router yet — that is step 3.
- Do not add tests in this repo — the project has no pytest harness today, and adding one is outside this plan.
- Do not change the existing `behavior_score` deltas or `profile_topic_decay`.
- Do not rename existing settings.

## 6. Done condition
- `Settings` instance has the four new fields with the documented defaults.
- `compute_alpha(0, settings)` returns `0.1` (within float epsilon).
- `compute_alpha(30, settings)` returns roughly `0.525`.
- `compute_alpha(365, settings)` returns roughly `0.890` (close to ceiling, as the demo user's seeded `behavior_score = 365`).
- `compute_alpha` is exported from `backend.app.config`.

## 7. Verification
Run the following in PowerShell from the repo root:

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -c "
from backend.app.config import get_settings, compute_alpha
s = get_settings()
print('floor', compute_alpha(0, s))
print('mid',   compute_alpha(s.cold_start_behavior_score_scale, s))
print('demo',  compute_alpha(365, s))
print('big',   compute_alpha(10**6, s))
"
```

Expected:
- `floor` close to `0.1`.
- `mid` close to `0.525`.
- `demo` close to `0.89`.
- `big` close to `0.95` and below the ceiling.

## 8. Expected output
A `backend/app/config.py` diff that adds four fields, four env-var overrides, and one function.

No behavioral change to any HTTP endpoint.

## 9. Notes for the next step
Step 3 imports `compute_alpha` and `get_settings` together. It should call `get_settings()` once at request time, not module-load time, so env-var overrides are honored on first request after the process starts.

## 10. Risks or ambiguity
- The `score / (score + scale)` form is one of several reasonable monotone bounded shapes. The choice is justified by being smooth, parameter-light, and obvious to read. If a future plan wants a piecewise-linear shape, only `compute_alpha` needs to change.
- `cold_start_behavior_score_scale = 30.0` is an opinionated default: the demo user reaches `behavior_score = 365` after the seed and grows from there, so 30 puts the midpoint within reach for a freshly-replayed session and the demo user lands well into the personalized end. If the curve feels too aggressive in step 5, raise the scale (delays personalization) or raise the floor (gives more default weight at high scores).

# Subproblem 1: Schema And Seed Verification

## 1. Goal
Confirm that the cold-start seed data is already correctly populated in MySQL and reachable via SQL, before changing any ranking code.

After this step, we know the `cold_start_default` row exists with non-empty `topic_weights_json`, the demo user references it via `cold_start_seed_key`, and a basic `JOIN` from `user_profile` to `system_profile_seed` returns a usable topic distribution.

## 2. Why this step exists
`backend/app/repositories/mysql.py` currently never reads `system_profile_seed`. Before adding code that loads it, we must rule out the case where the seed row is empty, missing, or malformed — debugging a wrong join is much harder once it lives inside `get_feed`.

The schema and the demo SQL already promise the seed exists (`sql/v1_schema.sql:162-170` and `build/demo_world/import_demo_world.sql` `INSERT INTO system_profile_seed`). This step verifies that promise instead of trusting it.

## 3. Files involved
- `sql/v1_schema.sql` — read-only, confirms the table and FK definition.
- `build/demo_world/import_demo_world.sql` — read-only, confirms the seed row payload.
- `scripts/inspect_zhihurec.py` — optional, may add a small probing helper.
- No application code changes in this step.

## 4. Exact changes
- Run the queries listed in section 7 against the running MySQL container (this is the only step that briefly needs the container; subsequent code-only steps do not).
- If `cold_start_default` is missing, blank, or has fewer than 5 topics: open a follow-up to fix `scripts/build_demo_world.py` (`build_default_profile_seed`) and rerun `import_demo_world.py` + `apply_demo_mysql.py`. Do not invent a hand-crafted seed.
- If the FK is satisfied but the demo user references a different `cold_start_seed_key` than `cold_start_default`: stop and reconcile with the `apply_demo_mysql.py` import path before continuing.

No code edits are expected to land in this step under the happy path.

## 5. Out of scope
- Do not change schema columns.
- Do not change `apply_demo_mysql.py` unless the verification fails.
- Do not start writing alpha code, mixing logic, or debug payloads here.
- Do not touch `user_profile` rows for users other than 7248.

## 6. Done condition
- `system_profile_seed` has a row with `seed_key = 'cold_start_default'` and `topic_weights_json` is a non-empty JSON array of `{topic_id, weight}` objects (current build has 10).
- `user_profile.cold_start_seed_key` for `user_id = 7248` equals `'cold_start_default'`.
- A simple JOIN returns the seed's topic weights when given the user's id.

## 7. Verification
Bring up the container and run:

```powershell
docker compose up -d
do { Start-Sleep -Seconds 3; $s = docker inspect -f '{{.State.Health.Status}}' zhihurec-mysql 2>$null; "status=$s" } while ($s -ne 'healthy')

docker exec zhihurec-mysql mysql -uroot -proot zhihurec_demo -e "
  SELECT seed_key, JSON_LENGTH(topic_weights_json) AS topic_n, behavior_score, notes
  FROM system_profile_seed;
  SELECT user_id, cold_start_seed_key, JSON_LENGTH(topic_weights_json) AS user_topic_n, behavior_score
  FROM user_profile WHERE user_id = 7248;
  SELECT u.user_id, s.seed_key, JSON_LENGTH(s.topic_weights_json) AS seed_topic_n
  FROM user_profile u
  JOIN system_profile_seed s ON s.seed_key = u.cold_start_seed_key
  WHERE u.user_id = 7248;
"
```

Expected output:
- `seed_key = cold_start_default`, `topic_n >= 5`, `behavior_score = 0`.
- `user_id = 7248`, `cold_start_seed_key = cold_start_default`, `user_topic_n >= 1`.
- The JOIN returns one row, with `seed_topic_n` matching the first query.

If anything fails: stop, fix the importer, rerun `apply_demo_mysql.py`, and re-verify before opening step 2.

## 8. Expected output
A short note appended to the plan README's "Current status" line:

> 2026-XX-XX — step 1 verified: `system_profile_seed.cold_start_default` has N topics; demo user 7248 references it cleanly.

No code or data changes under the happy path.

## 9. Notes for the next step
Step 2 can assume the seed exists with a non-trivial topic_weights distribution; it should not re-check this on every request.

## 10. Risks or ambiguity
- The schema FK enforces the link, so a missing row would already fail `apply_demo_mysql.py`. The realistic failure mode is "seed exists but `topic_weights_json` is empty" — which is why section 7 explicitly checks `JSON_LENGTH`.
- If the user is running against a non-demo MySQL instance, the seed contents may differ. Document that in the verification note instead of editing the seed row in place.

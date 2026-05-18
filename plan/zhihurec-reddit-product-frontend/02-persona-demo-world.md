# Subproblem 2: Persona Demo World

## 1. Goal

Create three real demo personas backed by MySQL `app_user`, `user_profile`, and event/profile seed data.

Persona switching must change backend state context, not just frontend labels.

## 2. Why this step exists

The current project is centered on one demo user, `7248`. A product frontend with a persona switcher is not credible if all personas map to the same user.

## 3. Files involved

- `scripts/build_demo_world.py` - select and export multiple demo personas.
- `scripts/import_demo_world.py` - import multiple persona profiles into SQL.
- `scripts/reset_demo_user.py` - reset all personas or one selected persona.
- `tests/conftest.py` - reset behavior for MySQL tests should remain predictable.
- `build/demo_world/*` - generated artifacts, not committed.

## 4. Exact changes

Update demo world generation:

- Add `--demo-persona-count`, default `3`.
- Keep `--demo-user-id` behavior as the preferred first persona when provided.
- Select remaining personas from users with both clicks and queries.
- Use the existing score idea from `choose_demo_user`: prefer users with queries, clicks, followed topics, and both signal types.
- Avoid near-duplicate personas when possible by comparing top topic overlap.
- If there are not enough diverse users, fill with the next highest-scoring users.

Output compatibility:

- Keep writing legacy `demo_user_profile_seed.json` for the first persona.
- Add `demo_persona_profile_seeds.json` as a list of all selected personas.
- Add `demo_personas.json` as a lightweight summary for docs/debugging.
- Write all selected persona rows to `app_user.jsonl`.
- Include persona-specific clicked/searched content in the selected answer/topic universe.
- Include replay events for all selected personas in `demo_event_replay.jsonl`.

Update import/reset:

- `import_demo_world.py` should import all rows from `demo_persona_profile_seeds.json` when present.
- Fall back to `demo_user_profile_seed.json` when the multi-persona file is absent.
- `reset_demo_user.py` should reset all personas by default when the multi-persona file exists.
- Add `--user-id` to reset only one persona when needed.
- Keep current single-user behavior for old generated worlds.

## 5. Out of scope

- Do not add authentication.
- Do not create synthetic frontend-only personas.
- Do not add a new table for personas unless the existing `app_user` and `user_profile` shape is insufficient.

## 6. Done condition

After applying generated SQL and reset scripts, MySQL contains three demo users with corresponding `user_profile` rows.

## 7. Verification

Run:

```powershell
& 'C:\ProgramData\anaconda3\python.exe' scripts\build_demo_world.py
& 'C:\ProgramData\anaconda3\python.exe' scripts\import_demo_world.py --input-dir build\demo_world --output-sql build\demo_world\import_demo_world.sql --truncate-first
& 'C:\ProgramData\anaconda3\python.exe' scripts\apply_demo_mysql.py
& 'C:\ProgramData\anaconda3\python.exe' scripts\reset_demo_user.py
```

Expected:

- `build/demo_world/demo_persona_profile_seeds.json` exists.
- It contains exactly 3 rows by default.
- `reset_demo_user.py` prints reset output for all personas.
- Existing tests that assume user `7248` still pass when `7248` is the first persona.

## 8. Expected output

The backend has real persona data that the product frontend can switch between.

## 9. Notes for the next step

The API step can now expose `/personas` from real MySQL rows.

## 10. Risks or ambiguity

The raw ZhihuRec data may not have many highly active users with both clicks and searches. The selector must degrade gracefully and still produce three usable personas if possible.

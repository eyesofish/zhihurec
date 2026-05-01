# Subproblem 2: Demo-World Import Chain

## 1. Goal
Add the import step that loads the existing `build/demo_world/` pack into the MySQL tables defined in `sql/v1_schema.sql`.

## 2. Why this step exists
`build/demo_world/` already exists, but `V1` has now frozen the rule that runtime services cannot read those files directly. The project needs an explicit import chain so those files become MySQL seed input rather than a second runtime storage layer.

## 3. Files involved
- `scripts/import_demo_world.py` - new importer that turns the demo-world pack into MySQL-compatible insert statements.
- `build/demo_world/manifest.json` - the import-pack manifest and row-count reference.
- `build/demo_world/*.jsonl` and `build/demo_world/*.json` - the actual importer inputs.
- `sql/v1_schema.sql` - the target schema that determines table names, column names, and insert order.

## 4. Exact changes
- Add `scripts/import_demo_world.py`.
- Make the script read `build/demo_world/` by default.
- Make the script emit MySQL-compatible seed SQL in dependency order: dimensions first, bridges next, profile seeds and user profile next, events last.
- Map `default_profile_seed.json` into `system_profile_seed`.
- Map `demo_user_profile_seed.json` into `user_profile`.
- Map `demo_event_replay.jsonl` into `user_event`.
- Keep the implementation standard-library based so it can run with the same Python environment used by the existing scripts.

## 5. Out of scope
- Starting or provisioning MySQL.
- Building the raw-to-demo-world step again in this subproblem.
- Writing the backend service that consumes the imported rows.

## 6. Done condition
There is a concrete import script that can turn the existing demo-world pack into a MySQL seed file or MySQL-ready statements without requiring manual JSON-to-SQL translation.

## 7. Verification
- Run `C:\ProgramData\anaconda3\python.exe scripts\import_demo_world.py --help`.
- Run the importer against `build/demo_world/` and generate an output SQL file.
- Inspect the output and confirm it contains inserts for `topic`, `author`, `app_user`, `question`, `answer`, `question_topic`, `answer_topic`, `query_topic_map`, `hot_answer_snapshot`, `system_profile_seed`, `user_profile`, and `user_event`.

## 8. Expected output
A reproducible bridge from `build/demo_world/` into MySQL seed data.

## 9. Notes for the next step
Once the importer exists, the API contract and init script can assume MySQL contains the runtime data and no runtime file reads are needed.

## 10. Risks or ambiguity
The current replay file only contains `search_query` and `recommendation_click` rows. The importer must still preserve the schema's support for `search_result_click`, because that event type is part of the frozen `V1` boundary.

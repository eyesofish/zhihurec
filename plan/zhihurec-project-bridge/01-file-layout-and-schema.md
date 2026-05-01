# Subproblem 1: MySQL Runtime Schema

## 1. Goal
Revise `sql/v1_schema.sql` so it cleanly represents the current `build/demo_world/` import pack and makes MySQL the only runtime source of truth for `V1`.

## 2. Why this step exists
The repository already has `build/demo_world/` outputs and a first schema draft, but the runtime boundary was still ambiguous. This step removes that ambiguity before the importer and backend code start depending on it.

## 3. Files involved
- `sql/v1_schema.sql` - the schema file that must become the explicit runtime boundary.
- `project_brief_zh.md` - the current source of truth for `V1` boundaries: MySQL-only runtime, first-batch directories, and init-script scope.
- `build/demo_world/manifest.json` - the current import-pack manifest that shows which derived files and row counts the schema must absorb.
- `build/demo_world/*.jsonl` and `build/demo_world/*.json` - the real field shapes that the schema must store without requiring file-backed runtime reads.

## 4. Exact changes
- Keep `sql/v1_schema.sql` as the first-batch schema location.
- Revise the file header comments so they explicitly say online services read MySQL tables only.
- Keep tables for `topic`, `author`, `app_user`, `question`, `answer`, `question_topic`, `answer_topic`, `query_topic_map`, `hot_answer_snapshot`, `system_profile_seed`, `user_profile`, and `user_event`.
- Preserve fields already present in the demo-world import pack, including synthetic display fields, `vector_key`, answer-level heat counters, and JSON profile structures.
- Keep the schema focused on current `V1` needs instead of adding Redis, queues, multi-tenant auth, or speculative ranking infrastructure.

## 5. Out of scope
- Starting MySQL in this step.
- Writing the importer logic itself.
- Defining backend ORM models or framework-specific migrations.

## 6. Done condition
`sql/v1_schema.sql` can represent the current `build/demo_world/` files without requiring the runtime service to read those files directly.

## 7. Verification
- Read `sql/v1_schema.sql` and confirm the header states MySQL is the runtime source of truth.
- Confirm the schema includes tables for content entities, profile state, event log, query-topic mapping, and hot fallback data.
- Confirm the schema can absorb `answer.jsonl`, `question.jsonl`, `author.jsonl`, `topic.jsonl`, `app_user.jsonl`, `query_topic_map.jsonl`, `hot_answer_snapshot.jsonl`, `default_profile_seed.json`, `demo_user_profile_seed.json`, and `demo_event_replay.jsonl`.

## 8. Expected output
A MySQL schema that exactly defines what the runtime service can read after the demo-world import step is done.

## 9. Notes for the next step
The importer can now target concrete tables and column names rather than treating `build/demo_world/` as an implicit runtime data source.

## 10. Risks or ambiguity
Some future runtime data, such as ANN index details, is still intentionally deferred. The schema should leave hooks such as `vector_key`, but it should not pretend those future assets already exist in MySQL.

# Task Plan: ZhihuRec Project Bridge

## Overall goal
Turn the existing ZhihuRec demo-world artifacts into a MySQL-backed runtime boundary for `V1`: define the runtime schema first, define the import chain from `build/demo_world/` second, and then align the API contract to that boundary.

## Subproblems
1. `01-file-layout-and-schema.md` - freeze the first-batch directory layout and revise `sql/v1_schema.sql` so MySQL is the only runtime source of truth - status: verified
2. `02-demo-world-import.md` - add the import path that loads `build/demo_world/` into the MySQL tables in a stable order - status: verified
3. `03-api-contract.md` - create the first API contract around the MySQL-backed runtime boundary - status: verified

## Dependencies
Step 2 depends on Step 1 because the import script must target concrete table names and field shapes.
Step 3 depends on Steps 1 and 2 because the API contract must refer to the MySQL tables that the importer populates, not to raw CSVs or runtime file reads.

## Recommended execution order
Start with the schema so the runtime boundary is explicit.
Then implement the import chain so `build/demo_world/` becomes a pure import pack rather than an implicit runtime data source.
Finally, update the API contract so it describes only the MySQL-backed online path.

## End-to-end verification
1. Confirm `sql/v1_schema.sql` states that online services read MySQL tables only.
2. Confirm `scripts/import_demo_world.py` reads from `build/demo_world/` and emits a MySQL-compatible import file or import statements in table dependency order.
3. Confirm the schema includes the entities and signals required by `V1`: answer, question, author, topic, app_user, user_profile, user_event, query_topic_map, and hot fallback storage.
4. Confirm `build/demo_world/` is treated as an offline import pack, not a runtime file-backed service source.
5. Confirm `docs/v1_api_contract.md` exists and defines the V1 endpoint list on top of project-owned schema and derived import assets.

## Current status
This bridge plan is complete for its original purpose. The repository now has:

- `sql/v1_schema.sql`
- `scripts/build_demo_world.py`
- `scripts/import_demo_world.py`
- `docs/v1_api_contract.md`
- generated local import artifacts under `build/demo_world/`

One final wording cleanup in `docs/v1_api_contract.md` is tracked in `plan/zhihurec-v1-runtime-closed-loop/01-align-brief-and-contract.md`, because it belongs to the current runtime implementation handoff rather than the original bridge work.

## Current handoff
Do not continue implementation from this bridge plan. Use `plan/zhihurec-v1-runtime-closed-loop/` for the active work that connects the existing schema, import pack, and API contract to a real MySQL-backed backend.

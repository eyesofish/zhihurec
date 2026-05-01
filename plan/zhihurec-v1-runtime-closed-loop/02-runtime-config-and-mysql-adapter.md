# Subproblem 2: Runtime Config And MySQL Adapter

## 1. Goal
Add the minimal database dependency and repository wiring needed for the backend to use MySQL when `ZHIHUREC_DATABASE_URL` is configured.

The endpoint behavior can still be incomplete after this step. The main goal is to introduce the adapter safely and keep the app importable.

## 2. Why this step exists
The current backend uses `UnwiredRuntimeRepository` from `backend/app/repositories/unwired.py`.

Every real business endpoint depends on replacing that placeholder with a repository that can query the tables created by `sql/v1_schema.sql`.

## 3. Files involved
- `backend/requirements.txt` - new dependency list for the backend runtime.
- `backend/app/config.py` - already reads `ZHIHUREC_DATABASE_URL`; extend it only if needed for stable runtime knobs.
- `backend/app/dependencies.py` - currently always returns `UnwiredRuntimeRepository`; update it to choose MySQL when configured.
- `backend/app/repositories/base.py` - contains the repository protocol. Keep the existing method names unless a later step proves a contract mismatch.
- `backend/app/repositories/mysql.py` - new file for `MysqlRuntimeRepository`.
- `backend/app/repositories/mysql_helpers.py` - optional new file for connection parsing, JSON parsing, row conversion, and small SQL helper functions if `mysql.py` becomes hard to read.
- `backend/README.md` - document how to install dependencies and set `ZHIHUREC_DATABASE_URL`.

## 4. Exact changes
- Create `backend/requirements.txt` with the backend dependencies that are actually imported:
  - `fastapi`
  - `uvicorn`
  - `pydantic`
  - `pymysql`
- Create `backend/app/repositories/mysql.py`.
- Add a class named `MysqlRuntimeRepository`.
- Set `MysqlRuntimeRepository.backend_name = "mysql"`.
- Give `MysqlRuntimeRepository.__init__` a `settings: Settings` argument.
- In `MysqlRuntimeRepository.__init__`, validate that `settings.database_url` is not blank.
- Add a private connection helper that opens a PyMySQL connection from `ZHIHUREC_DATABASE_URL`.
- Support a URL shape like:
  - `mysql+pymysql://user:password@localhost:3306/zhihurec_demo`
  - `mysql://user:password@localhost:3306/zhihurec_demo`
- Do not open a database connection during app import.
- In `backend/app/dependencies.py`, update `get_runtime_repository()`:
  - if `settings.database_configured` is false, return `UnwiredRuntimeRepository(settings)`
  - if true, return `MysqlRuntimeRepository(settings)`
- Keep `/healthz` behavior unchanged except `repository_backend` should become `mysql` when the env var is set.

## 5. Out of scope
- Do not implement feed/search/event SQL behavior in this step.
- Do not apply schema or seed data to MySQL.
- Do not add frontend files.
- Do not add Redis or async database libraries.

## 6. Done condition
The backend imports without a database.

When `ZHIHUREC_DATABASE_URL` is not set, `/healthz` still reports `repository_backend = "unwired"`.

When `ZHIHUREC_DATABASE_URL` is set, repository construction selects `MysqlRuntimeRepository` without connecting until an endpoint method is called.

## 7. Verification
Run without a database URL:

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -c "from backend.app.dependencies import get_runtime_repository; print(get_runtime_repository().backend_name)"
```

Expected output:

```text
unwired
```

Run in a fresh PowerShell process with a dummy database URL:

```powershell
$env:ZHIHUREC_DATABASE_URL='mysql+pymysql://root:root@localhost:3306/zhihurec_demo'
& 'C:\ProgramData\anaconda3\python.exe' -c "from backend.app.dependencies import get_runtime_repository; print(get_runtime_repository().backend_name)"
```

Expected output:

```text
mysql
```

Also run:

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -c "from backend.app.main import app; print(app.title)"
```

Expected output:

```text
ZhihuRec Backend
```

## 8. Expected output
New MySQL repository adapter files and backend dependency documentation.

Endpoint methods may still raise a clear "not implemented in mysql repository" style error until later steps fill them in.

## 9. Notes for the next step
Step 3 can assume repository selection works and can focus only on read behavior.

## 10. Risks or ambiguity
The local machine currently does not expose `mysql` on PATH, so MySQL verification may need either a configured MySQL service or the planned Python DB initialization script from Step 6.

Do not require the MySQL CLI for normal backend operation.

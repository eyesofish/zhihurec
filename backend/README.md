# ZhihuRec Backend

This directory contains the first backend skeleton for the ZhihuRec `V1` project.

Current scope:
- FastAPI logical monolith
- route shells for the frozen `V1` API set
- service layer and repository boundary
- explicit placeholder repository until MySQL query work is added

Current non-goal:
- real MySQL query implementation
- recommendation logic
- profile mutation logic

Install backend dependencies:

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m pip install -r backend\requirements.txt
```

Optional MySQL runtime configuration:

```powershell
$env:ZHIHUREC_DATABASE_URL='mysql+pymysql://root:root@localhost:3306/zhihurec_demo'
```

When `ZHIHUREC_DATABASE_URL` is not set, the backend uses `UnwiredRuntimeRepository`.
When it is set, the backend selects `MysqlRuntimeRepository` without opening a database connection during app import.

Local runtime setup order:

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m pip install -r backend\requirements.txt
& 'C:\ProgramData\anaconda3\python.exe' scripts\import_demo_world.py --input-dir build\demo_world --output-sql build\demo_world\import_demo_world.sql --truncate-first
$env:ZHIHUREC_DATABASE_URL='mysql+pymysql://root:root@localhost:3306/zhihurec_demo'
& 'C:\ProgramData\anaconda3\python.exe' scripts\apply_demo_mysql.py
& 'C:\ProgramData\anaconda3\python.exe' scripts\reset_demo_user.py
& 'C:\ProgramData\anaconda3\python.exe' -m uvicorn backend.app.main:app --reload
```

Smoke requests after the backend starts:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/healthz'
Invoke-RestMethod 'http://127.0.0.1:8000/debug/profile?user_id=7248'
Invoke-RestMethod 'http://127.0.0.1:8000/feed?user_id=7248&page_size=10&debug=true'
```

Optional event replay:

```powershell
& 'C:\ProgramData\anaconda3\python.exe' scripts\replay_demo_events.py --limit 10
```

Suggested import check:

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -c "from backend.app.main import app; print(app.title)"
```

Suggested route check:

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -c "from backend.app.main import app; print(sorted({route.path for route in app.routes}))"
```

## Next implementation target

Follow `plan/zhihurec-v1-runtime-closed-loop/` next.

The next backend task is to add `MysqlRuntimeRepository` and make it the active runtime repository when `ZHIHUREC_DATABASE_URL` is configured. Until then, `UnwiredRuntimeRepository` intentionally returns controlled `repository_not_ready` responses for business endpoints.

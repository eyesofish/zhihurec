# ZhihuRec V1 Local Runbook

## 1. Install Backend Dependencies

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m pip install -r backend\requirements.txt
```

## 2. Regenerate Import SQL

```powershell
& 'C:\ProgramData\anaconda3\python.exe' scripts\import_demo_world.py --input-dir build\demo_world --output-sql build\demo_world\import_demo_world.sql --truncate-first
```

Expected output includes:

```text
44690 row(s) across 12 table payload(s)
```

## 3. Configure MySQL

```powershell
$env:ZHIHUREC_DATABASE_URL='mysql+pymysql://root:root@localhost:3306/zhihurec_demo'
```

## 4. Initialize Database

```powershell
& 'C:\ProgramData\anaconda3\python.exe' scripts\apply_demo_mysql.py
& 'C:\ProgramData\anaconda3\python.exe' scripts\reset_demo_user.py
```

Use this dry-run check before connecting to MySQL:

```powershell
& 'C:\ProgramData\anaconda3\python.exe' scripts\apply_demo_mysql.py --dry-run
```

## 5. Start Backend

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

## 6. Smoke Checks

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/healthz'
Invoke-RestMethod 'http://127.0.0.1:8000/debug/profile?user_id=7248'
Invoke-RestMethod 'http://127.0.0.1:8000/feed?user_id=7248&page_size=10&debug=true'
```

For search, use a known key from `build\demo_world\demo_user_profile_seed.json`, such as a value in `recent_queries`.

## 7. Start Frontend

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m http.server 5173 -d frontend
```

Open:

```text
http://127.0.0.1:5173
```

## 8. Replay Events

```powershell
& 'C:\ProgramData\anaconda3\python.exe' scripts\replay_demo_events.py --limit 10
```

After replay, call `/debug/profile` again and check that `recent_queries`, `recent_clicked_answers`, or `behavior_score` changed.

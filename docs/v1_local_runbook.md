# ZhihuRec V1 Local Runbook

## 0. One-Shot Local Bootstrap

```powershell
.\scripts\init_local.ps1
```

This runs the local demo setup in one path: starts MySQL via Docker Compose, applies schema and demo seed data, resets the demo user, starts the FastAPI backend on `http://127.0.0.1:8000`, and starts the static debug frontend on `http://127.0.0.1:5173`.

For a non-interactive verification run that starts backend/frontend, checks the endpoints, and then stops only those child processes:

```powershell
.\scripts\init_local.ps1 -SmokeTest
```

Use the explicit per-step flow below only when debugging one part of the setup.

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

## 2.5 Start MySQL via Docker Compose

The repo ships a `docker-compose.yml` at root that brings up `mysql:8.0` on `127.0.0.1:3306` with database `zhihurec_demo`, account `root/root`, and a named volume for persistence.

```powershell
docker compose up -d
do { Start-Sleep -Seconds 3; $s = docker inspect -f '{{.State.Health.Status}}' zhihurec-mysql 2>$null; "status=$s" } while ($s -ne 'healthy')
```

Stop later with:

```powershell
docker compose down       # keep volume
docker compose down -v    # nuke volume too
```

If you already have a local MySQL running, you can skip this section and use the URL it exposes in §3 below.

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

## 8. Product Frontend (React/Vite/TS)

The product frontend at `product-frontend/` is a Reddit-inspired React app that demonstrates the full persona → feed → search → upvote → profile loop.

### 8.1 Install & Build

```powershell
cd product-frontend
npm install
npm run build
```

### 8.2 Start Dev Server

```powershell
cd product-frontend
npm run dev -- --host 127.0.0.1 --port 5174
```

Open:

```text
http://127.0.0.1:5174
```

The backend must be running at `http://127.0.0.1:8000` with `ZHIHUREC_DATABASE_URL` configured. The Vite dev server proxies nothing; all API calls go directly to the backend via the base URL in `product-frontend/src/api/client.ts`.

### 8.3 One-Shot with init_local.ps1

```powershell
.\scripts\init_local.ps1 -ProductFrontend
```

This starts MySQL, the backend on 8000, the debug frontend on 5173, and the product frontend on 5174 in a single command.

### 8.4 Walkthrough

1. **Persona switch** — click the persona avatar (top-right) to switch between demo users. Feed and profile panel update automatically.
2. **Feed** — scroll through personalised feed cards. Each shows community badge, title (link to detail), summary, topic chips, and selection reason.
3. **Search** — type in the top search box, select a suggestion, or press Enter. Results page shows keyword-matched answers.
4. **Post detail** — click a card title to see the full answer card with back-to-feed navigation.
5. **Upvote** — click the up arrow on any card. The event is tracked and profile weights update (visible in the right-rail Profile Debug panel).
6. **Profile debug** — the right rail shows behavior score, cold-start seed, topic weights, and recent clicks from `/debug/profile`.

The debug frontend at `http://127.0.0.1:5173` remains available and unaffected.

## 9. Replay Events

```powershell
& 'C:\ProgramData\anaconda3\python.exe' scripts\replay_demo_events.py --limit 10
```

After replay, call `/debug/profile` again and check that `recent_queries`, `recent_clicked_answers`, or `behavior_score` changed.

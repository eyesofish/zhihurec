# Subproblem 7: Debug Frontend And Runbook

## 1. Goal
Add the first minimal debug frontend and a runbook that explains how to use the local demo end to end.

The frontend should help inspect backend behavior. It should not try to be a polished product UI.

## 2. Why this step exists
The brief says the first batch includes a lightweight frontend because the project needs to demonstrate the closed loop clearly.

The frontend should make it easy to show feed results, search results, click events, and profile changes in one place.

## 3. Files involved
- `frontend/index.html` - new static page.
- `frontend/app.js` - new JavaScript file for calling backend endpoints.
- `frontend/styles.css` - new CSS file for a compact debug layout.
- `frontend/README.md` - new short frontend run instructions.
- `backend/app/main.py` - add CORS middleware only if the frontend is served from a different local port.
- `backend/app/config.py` - add a local CORS origin setting only if needed.
- `docs/v1_local_runbook.md` - new or updated end-to-end runbook.

## 4. Exact changes
- Create `frontend/index.html`.
- The first screen should be the actual debug tool, not a landing page.
- Include:
  - user ID input with default `7248`
  - API base URL input with default `http://127.0.0.1:8000`
  - refresh feed button
  - refresh profile button
  - search query input
  - run search button
  - feed results area
  - search results area
  - profile summary area
  - debug JSON area
- Create `frontend/app.js`.
- Implement functions:
  - `loadFeed()`
  - `loadProfile()`
  - `runSearch()`
  - `recordRecommendationClick(answerId, requestId)`
  - `recordSearchResultClick(answerId, queryKey)`
- Make click buttons call the event endpoints with `debug=true`.
- After a successful click, automatically refresh profile and feed.
- Create `frontend/styles.css`.
- Use a dense, work-focused layout with tables or compact panels.
- Do not use marketing sections, hero banners, or decorative backgrounds.
- If CORS blocks local frontend requests, update `backend/app/main.py` to add `CORSMiddleware`.
- Keep allowed origins local by default:
  - `http://127.0.0.1:5173`
  - `http://localhost:5173`
- Create `docs/v1_local_runbook.md`.
- Document:
  - dependency install
  - import SQL regeneration
  - `ZHIHUREC_DATABASE_URL`
  - DB initialization
  - backend startup
  - frontend static server startup
  - smoke checks
  - replay script

## 5. Out of scope
- Do not add React, Vite, Tailwind, or a package manager unless the user explicitly asks.
- Do not build login/authentication.
- Do not add charts unless the backend data is already stable.
- Do not expose the full raw dataset.
- Do not create a production deployment setup.

## 6. Done condition
With backend and MySQL running:

- the frontend loads in a browser
- it can load feed
- it can load profile
- it can run search
- it can record feed click and search-result click
- profile state visibly changes after events

## 7. Verification
Start backend:

```powershell
$env:ZHIHUREC_DATABASE_URL='mysql+pymysql://user:password@localhost:3306/zhihurec_demo'
& 'C:\ProgramData\anaconda3\python.exe' -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

In another PowerShell window, serve the frontend:

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m http.server 5173 -d frontend
```

Open:

```text
http://127.0.0.1:5173
```

Manual checks:

- click refresh feed
- click refresh profile
- paste a known `query_key` from `build\demo_world\demo_user_profile_seed.json`
- run search
- click one feed item
- click one search result
- confirm the profile panel changes after each click

Before MySQL and the backend are running, keep these static checks passing:

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -c "from backend.app.main import app; print(app.title); print(sorted({route.path for route in app.routes}))"
& 'C:\ProgramData\anaconda3\python.exe' -c "from backend.app.config import get_settings; print(get_settings().cors_origins)"
Select-String -Path frontend\app.js -Pattern 'function loadFeed|function loadProfile|function runSearch|function recordRecommendationClick|function recordSearchResultClick'
Test-Path docs\v1_local_runbook.md; Test-Path frontend\index.html; Test-Path frontend\styles.css; Test-Path frontend\app.js
& 'C:\ProgramData\anaconda3\python.exe' -c "import functools, http.server, socketserver, threading, urllib.request; Handler=functools.partial(http.server.SimpleHTTPRequestHandler, directory='frontend'); srv=socketserver.TCPServer(('127.0.0.1', 5173), Handler); t=threading.Thread(target=srv.serve_forever, daemon=True); t.start(); print(urllib.request.urlopen('http://127.0.0.1:5173', timeout=5).status); srv.shutdown(); srv.server_close()"
```

Expected result:

- backend import still works
- CORS includes the local frontend origins
- `frontend/app.js` contains the required endpoint functions
- the frontend and runbook files exist
- the short-lived static server check prints `200`

## 8. Expected output
A static debug frontend and a runbook that make the V1 closed loop demoable on a local machine.

## 9. Notes for the next step
After this step, the project can move from "runtime implementation" to "parameter tuning and offline replay metrics" as a separate plan.

## 10. Risks or ambiguity
The local browser may enforce CORS depending on how the frontend is served. Keep the CORS change local and explicit instead of opening all origins by default.

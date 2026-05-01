# ZhihuRec Debug Frontend

Serve this static frontend from the repository root:

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m http.server 5173 -d frontend
```

Open:

```text
http://127.0.0.1:5173
```

The backend should be running at `http://127.0.0.1:8000` with `ZHIHUREC_DATABASE_URL` configured.

# Run Locally (Reload Mode)

Run the FastAPI app locally with live-reload, without Docker.

Prerequisites

- Python 3.10+
- pip available in PATH
- Node.js and npm (for pm2 in production)
  - Install pm2 globally: `npm install -g pm2`

Quick dev run

```
python -m uvicorn app.main:app --host 0.0.0.0 --port 5680 --reload
```

Setup

1) Create and activate a virtualenv

- Bash (Linux/macOS): `python -m venv .venv && source .venv/bin/activate`
- PowerShell (Windows): `python -m venv .venv; .\.venv\Scripts\Activate.ps1`

2) Install dependencies

- `pip install -r requirements.txt`

3) Run in reload mode

- `python -m uvicorn app.main:app --host 0.0.0.0 --port 5680 --reload`

## Run in Production (pm2)

Use pm2 to manage the application in production. On Windows, prefer the ecosystem file method.

1) Install pm2 (if not already done): `npm install -g pm2`

Option A — ecosystem file (recommended on Windows)

- The repo includes `ecosystem.config.js` configured to launch uvicorn.
- Start: `pm2 start ecosystem.config.js --only scrapling-api`
- Logs: `pm2 logs scrapling-api`
- Restart/Stop: `pm2 restart scrapling-api` / `pm2 stop scrapling-api`
- Persist across restarts: `pm2 save` (and optionally `pm2 startup`)

Note: If Python is not on PATH or you use a different interpreter, edit `ecosystem.config.js` and adjust `script`/`args` accordingly.

Option B — one‑liner

- Linux/macOS: `pm2 start uvicorn --name scrapling-api -- app.main:app --host 0.0.0.0 --port 5680`
- Windows: Avoid quoting the whole command (e.g. "uvicorn ..."); if args are not passed correctly, use Option A.

## Troubleshooting

- The application reads additional settings from `.env`, but the uvicorn port is controlled by the `--port` flag shown above.
- Port already in use (Windows):
  - Find PID: `netstat -ano | Select-String ':5680'`
  - Inspect: `Get-Process -Id <PID>`
  - Stop: `Stop-Process -Id <PID> -Force` or change the `--port`.
- Port already in use (Linux/macOS): `lsof -i :5680` then kill the PID or change `--port`.
- PM2 logs: `pm2 logs scrapling-api` to see startup errors.

## Verify

- Health: `http://localhost:5680/health`
- Docs: `http://localhost:5680/docs`

## Tests

- `python -m pytest -q`


# Run Locally (Reload Mode)

Run the FastAPI app locally with live-reload, without Docker.

Prerequisites

- Python 3.10+
- pip available in PATH
  Quick:
- `python -m uvicorn app.main:app --host 0.0.0.0 --port 5699 --reload`

Setup

1) Create and activate a virtualenv

- Bash (Linux/macOS):
  - `python -m venv .venv && source .venv/bin/activate`
- PowerShell (Windows):
  - `py -m venv .venv; .\.venv\Scripts\Activate.ps1`

2) Install dependencies

- `pip install -r requirements.txt`

3) Run in reload mode

- Bash (Linux/macOS):
  - `export PORT=${PORT:-5699}`
  - `python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --reload`
- PowerShell (Windows):
  - `$env:PORT = "5699"`
  - `python -m uvicorn app.main:app --host 0.0.0.0 --port $env:PORT --reload`

Notes

- The application reads additional settings from `.env`, but the uvicorn port is controlled by the `--port` flag shown above.
- Verify it’s running:
  - Health: `http://localhost:5699/health`
  - Docs: `http://localhost:5699/docs`

Tests

- `python -m pytest -q`

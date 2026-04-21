# mcp-playwright-agent-adk

**Capstone project at Kyoto University of Advanced Science (2025-2026)**  
Industry-collaborative project.

An LLM-powered automation agent that navigates EDI systems autonomously 
and inputs product delivery information into invoices — reducing manual 
processing time by **3x (≈67% time reduction)**.

**Tech stack:** Python · Google Cloud ADK · MCP · Playwright · FastMCP  
**Result:** Manual workflow time reduced from ~10 minutes to ~3 minutes

## Prerequisites

- Python 3.12+
- pip or Poetry (Poetry recommended)
- (Optional) Google Cloud SDK (`gcloud`) and/or a service account JSON if you use GCS / Secret Manager features

## Repository layout (important files)

- `server.py` — main FastMCP server and Playwright tool implementations
- `app.py`, `deployment.py`, `model.py` — helper scripts used by the project
- `pyproject.toml`, `poetry.lock` — dependency manifests (the project uses Poetry)

## Checklist before running

- Install Python 3.12+ and ensure `python` is on your PATH
- Install Playwright browser binaries if you plan to use the Playwright tools
- Set any required environment variables for GCS/Secret Manager features (see Configuration)

## Setup (PowerShell)

1. Clone/open the project and create a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies (choose one):

   Option A — Poetry (recommended):

   ```powershell
   # If you have Poetry installed
   poetry install
   # Activate the virtualenv that Poetry creates (optional)
   # $poetryEnv = poetry env info --path; . "$poetryEnv\Scripts\Activate.ps1"
   ```

   Option B — pip (no Poetry installed):

   ```powershell
   # Export a requirements file from Poetry (works if poetry is available)
   poetry export -f requirements.txt --output requirements.txt --without-hashes
   pip install -r requirements.txt
   ```

3. Install Playwright browser binaries (required by the Playwright code paths):

   ```powershell
   python -m playwright install
   ```

## Configuration

Set environment variables used by `server.py` if you use GCS / Secret Manager features:

- `BUCKET_NAME` — GCS bucket (optional unless you use tools that read config)
- `CONFIG_BLOB_PATH` — path to JSON config blob in the bucket
- `GOOGLE_CLOUD_PROJECT` — your GCP project id
- `GOOGLE_APPLICATION_CREDENTIALS` — path to service account JSON (if not using `gcloud` auth)

Example (PowerShell, current session only):

```powershell
$env:BUCKET_NAME = 'my-bucket'
$env:CONFIG_BLOB_PATH = 'configs/companies.json'
$env:GOOGLE_CLOUD_PROJECT = 'my-project-id'
$env:GOOGLE_APPLICATION_CREDENTIALS = 'C:\path\to\sa.json'
```

## Running the server (local)

Run the MCP server which registers the Playwright tools and exposes an HTTP transport on port 8080 by default:

```powershell
python server.py
```

Stop the server with Ctrl+C. If you want to run on a different port, see the "Change port" suggestion below.

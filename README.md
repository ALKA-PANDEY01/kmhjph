# UK Wind Forecast Accuracy

## Overview

Compares day-ahead UK wind forecasts with metered actual generation.
Covers the January 2026 decision window (deliveries 2 January to 1 February).
Uses the latest forecast published by 09:00 Europe/London on D-1.

## Live app

- Frontend: https://kmhjph.vercel.app
- Backend health: https://kmhjph.onrender.com/health
- The free backend may take up to a minute to wake after being idle.

## Files and directories

This inventory covers the tracked paths from `git ls-files`.

| Directory | Description |
|---|---|
| `.` | Project docs and Docker Compose configuration. |
| `backend/` | FastAPI service, tests, and bundled processed data. |
| `backend/app/` | API application and schemas. |
| `backend/app/services/` | Forecast metric calculations. |
| `backend/data/` | Parquet data bundled with the API. |
| `backend/tests/` | Backend API, metric, and forecast selection tests. |
| `frontend/` | React/Vite application and deployment configuration. |
| `frontend/public/` | Static browser icons. |
| `frontend/src/` | Frontend source and global styles. |
| `frontend/src/assets/` | Static images and logos. |
| `frontend/src/components/` | Decision and accuracy views and styles. |
| `frontend/src/services/` | Frontend API client. |
| `ingestion/` | Elexon data retrieval and processing scripts. |
| `ingestion/data/` | Processed ingestion output. |

| File or group | Description |
|---|---|
| `README.md` | This setup, method, results, and limitations guide. |
| `.dockerignore`, `.gitignore` | Root Docker build exclusions and Git ignore rules. |
| `docker-compose.yml` | Runs the API and frontend containers. |
| `backend/Dockerfile`, `backend/.dockerignore` | Builds the backend image and filters its build context. |
| `backend/.env.example` | Example values for `ALLOWED_ORIGINS` and `DATA_PATH`. |
| `backend/app/main.py` | FastAPI routes and startup data loading. |
| `backend/app/models.py` | API response schemas. |
| `backend/app/services/metrics.py` | Metrics and time-series calculations. |
| `backend/data/wind_forecast_accuracy.parquet` | Bundled January 2026 hourly forecast and actuals. |
| `backend/requirements.txt` | Backend and test dependencies. |
| `backend/run_server.py`, `backend/run_metrics.py` | Start the API and print dataset metrics. |
| `backend/metrics_output.json` | Saved metrics summary. |
| `backend/tests/test_*.py` | API, cutoff, forecast selection, and metric tests. |
| `__init__.py` files | Python package markers in backend and ingestion. |
| `frontend/Dockerfile`, `frontend/.dockerignore` | Builds and serves the frontend image. |
| `frontend/.env.example` | Example `VITE_API_URL` value. |
| `frontend/vercel.json`, `frontend/nginx.conf` | SPA route fallback for Vercel and Nginx. |
| `frontend/package.json`, `frontend/package-lock.json` | Frontend dependencies and scripts, with locked versions. |
| `frontend/.gitignore`, `frontend/.oxlintrc.json` | Frontend ignore rules and Oxlint configuration. |
| `frontend/index.html`, `frontend/vite.config.js` | Browser entry document and Vite configuration. |
| `frontend/src/App.jsx`, `frontend/src/App.css` | Application shell, navigation, and top-level styles. |
| `frontend/src/main.jsx`, `frontend/src/index.css` | React mount point and global styles. |
| `frontend/src/components/AccuracyView.*` | Accuracy metrics and charts. |
| `frontend/src/components/DecisionView.*` | Daily forecast, actuals, and uncertainty band. |
| `frontend/src/services/api.js` | Calls the backend endpoints. |
| `frontend/src/assets/` and `frontend/public/` assets | Hero image, framework logos, favicon, and SVG icons. |
| `ingestion/config.py` | Elexon endpoints, date window, cutoff, and output settings. |
| `ingestion/fetch_elexon.py` | Fetches actual and forecast records. |
| `ingestion/process_data.py` | Cleans, selects, joins, and scores records. |
| `ingestion/ingest.py` | Runs ingestion and writes the processed parquet. |
| `ingestion/requirements.txt` | Ingestion dependencies. |
| `ingestion/bias_sanity_check.py`, `ingestion/investigate_cutoff.py`, `ingestion/verify.py` | Exploratory bias, cutoff, and forecast publication checks. |
| `ingestion/check_row_integrity.py` | Checks hourly counts, duplicates, and timestamp gaps. |
| `ingestion/data/wind_forecast_accuracy.parquet` | Parquet output from ingestion. |

## Start the application

### Docker

```sh
docker compose up --build
```

API: port 8000. Frontend: port 3000.

### Local backend (without Docker)

```sh
cd backend
python -m venv .venv
# Activate .venv, then install and start:
pip install -r requirements.txt && python run_server.py
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`; on macOS/Linux, use `source .venv/bin/activate`.

### Local frontend (without Docker)

```sh
cd frontend
npm install
# Set VITE_API_URL=http://localhost:8000
npm run dev
```

The frontend runs in its development server; keep the backend running in the other terminal.

| Variable | Purpose |
|---|---|
| `VITE_API_URL` | Backend base URL used by the frontend build. |
| `ALLOWED_ORIGINS` | Comma-separated browser origins accepted by the API. |
| `DATA_PATH` | Processed parquet path; defaults to `backend/data/wind_forecast_accuracy.parquet`. |

See `frontend/.env.example` and `backend/.env.example` for local examples.

### Re-run ingestion

```sh
cd ingestion
python -m venv .venv
pip install -r requirements.txt
python ingest.py
```

Copy the refreshed `ingestion/data/wind_forecast_accuracy.parquet` to `backend/data/` before restarting or rebuilding the API.

### Run tests

```sh
cd backend
python -m pytest
```

## Method and assumptions

- Selects the forecast with the latest `publishTime` at or before 09:00 Europe/London on D-1.
- Converts timestamps to UTC for processing and comparison.
- WINDFOR target timestamps are hourly; no interpolation is applied.
- The January window contains 744 hourly forecast/actual pairs.
- The inner join drops FUELHH `:30` actuals without a matching forecast.

## Key results

| Metric | January 2026 |
|---|---:|
| MAE | 2,022 MW (17.9%) |
| RMSE | 2,497 MW |
| Bias | +1,746 MW (15.5% over-forecast) |
| P90 absolute error | 4,154 MW |
| Selected forecasts published after cutoff | 0 |

## Known limitations

- Hourly WINDFOR resolution; FUELHH `:30` actuals are dropped in the join.
- January 2026 shows over-forecasting; its cause is unconfirmed.
- Results cover January 2026 only and may not generalize to other months.
- Data is wind generation at national level only.
- The free-tier backend may take up to a minute to wake after idle.

## AI usage

AI tools Kiro and Codex helped build the application. The author reviewed the code and verified forecast selection logic with tests.

# UK Wind Forecast Accuracy

## Overview

This application compares day-ahead UK wind generation forecasts with metered actual generation.
It covers a January 2026 decision window, with delivery dates from 2 January through 1 February.
For each delivery hour, it uses the latest forecast available by 09:00 Europe/London on D-1.
The API serves processed data; the frontend presents decision and accuracy views.

## Live app

- Frontend: https://kmhjph.vercel.app
- Backend health: https://kmhjph.onrender.com/health
- The free backend may take up to a minute to wake after being idle.

## Files and directories

Generated from tracked paths returned by `git ls-files`; each tracked folder and file has a one-line description.

```text
Energy_forecast/ - Application source, deployment configuration, and documentation.
|-- .dockerignore - Filters Docker build contexts.
|-- .gitignore - Ignores local environments, caches, and generated artifacts.
|-- backend/ - FastAPI service, tests, and bundled processed data.
|   |-- .dockerignore - Excludes backend development files from its image build.
|   |-- .env.example - Example backend environment variables.
|   |-- app/ - API implementation and schemas.
|   |   |-- __init__.py - Backend application package marker.
|   |   |-- main.py - FastAPI application, data loading, and routes.
|   |   |-- models.py - API request and response schemas.
|   |   \-- services/ - Backend metric logic.
|   |       |-- __init__.py - Services package marker.
|   |       \-- metrics.py - Forecast accuracy metric calculations.
|   |-- data/ - Processed parquet bundled with the API.
|   |   \-- wind_forecast_accuracy.parquet - Hourly forecast and actual data bundled with the API.
|   |-- Dockerfile - Builds the non-root Python API image with its data.
|   |-- metrics_output.json - Saved metric summary for the processed dataset.
|   |-- requirements.txt - Pinned backend and test dependencies.
|   |-- run_metrics.py - Prints and saves forecast metrics.
|   |-- run_server.py - Starts the backend development server.
|   \-- tests/ - Automated backend tests.
|       |-- __init__.py - Backend test package marker.
|       |-- test_api.py - API endpoint tests.
|       |-- test_cutoff_violations.py - Tests selected forecast cutoff compliance.
|       |-- test_forecast_selection.py - Tests forecast selection logic.
|       \-- test_metrics.py - Tests metric calculations and API behavior.
|-- docker-compose.yml - Builds and runs backend and frontend services.
|-- frontend/ - React/Vite application and deployment configuration.
|   |-- .dockerignore - Excludes frontend development files from its image build.
|   |-- .env.example - Example frontend API URL.
|   |-- .gitignore - Ignores frontend dependencies, output, and local env files.
|   |-- .oxlintrc.json - Oxlint configuration.
|   |-- Dockerfile - Builds the Vite app and serves it with Nginx.
|   |-- index.html - Browser HTML entry point.
|   |-- nginx.conf - Nginx SPA fallback configuration.
|   |-- package-lock.json - Locked npm dependency tree.
|   |-- package.json - Frontend dependencies and npm scripts.
|   |-- public/ - Static public assets.
|   |   |-- favicon.svg - Browser favicon.
|   |   \-- icons.svg - Reusable SVG icons.
|   |-- src/ - Frontend source code.
|   |   |-- App.css - Top-level application styles.
|   |   |-- App.jsx - Application shell and navigation.
|   |   |-- assets/ - Frontend images and logo assets.
|   |   |   |-- hero.png - Frontend hero artwork.
|   |   |   |-- react.svg - React logo asset.
|   |   |   \-- vite.svg - Vite logo asset.
|   |   |-- components/ - User interface views and styles.
|   |   |   |-- AccuracyView.css - Accuracy page styles.
|   |   |   |-- AccuracyView.jsx - Accuracy metrics and charts.
|   |   |   |-- DecisionView.css - Decision page styles.
|   |   |   \-- DecisionView.jsx - Decision forecast, actuals, and uncertainty band.
|   |   |-- index.css - Global frontend styles.
|   |   |-- main.jsx - Mounts the React application.
|   |   \-- services/ - Frontend backend client.
|   |       \-- api.js - Backend API client.
|   |-- vercel.json - Vercel SPA route rewrites.
|   \-- vite.config.js - Vite and React plugin configuration.
|-- ingestion/ - Elexon fetch and processing workflow.
|   |-- __init__.py - Ingestion package marker.
|   |-- bias_sanity_check.py - Exploratory forecast bias checks.
|   |-- check_row_integrity.py - Checks hourly record counts, duplicates, and gaps.
|   |-- config.py - Elexon endpoints, date range, cutoff, and output settings.
|   |-- data/ - Processed ingestion outputs.
|   |   \-- wind_forecast_accuracy.parquet - Processed parquet output from ingestion.
|   |-- fetch_elexon.py - Fetches Elexon actuals and forecasts.
|   |-- ingest.py - Runs fetching, selection, joining, and export.
|   |-- investigate_cutoff.py - Investigates publication times around the cutoff.
|   |-- process_data.py - Cleans, selects, joins, and scores records.
|   |-- requirements.txt - Ingestion dependencies.
|   \-- verify.py - Inspects forecast publication records.
\-- README.md - Project setup, method, results, and tracked-file inventory.
```

## Start the application

### Docker

From the repository root:

```sh
docker compose up --build
```

The API is on port 8000 and the frontend is on port 3000.

### Without Docker

Backend:

```sh
cd backend
python -m venv .venv
# Activate the virtual environment, then:
pip install -r requirements.txt
python run_server.py
```

Set `DATA_PATH` if the parquet is outside its bundled default. Set `ALLOWED_ORIGINS` to comma-separated frontend origins. See `backend/.env.example`.

Frontend, in a second terminal:

```sh
cd frontend
npm install
# Set VITE_API_URL=http://localhost:8000; see frontend/.env.example.
npm run dev
```

### Re-run ingestion

Install `ingestion/requirements.txt`, then run `python ingest.py` from `ingestion/`. This writes `ingestion/data/wind_forecast_accuracy.parquet`. Copy the refreshed parquet to `backend/data/wind_forecast_accuracy.parquet` before rebuilding or restarting the backend.

### Run tests

```sh
cd backend
python -m pytest
```

## Method and assumptions

For each delivery timestamp, ingestion selects the forecast with the latest `publishTime` at or before 09:00 Europe/London on D-1. Timestamps are stored and compared in UTC. WINDFOR is hourly, so 744 hourly periods are compared over this 31-day window; FUELHH actuals at `:30` are dropped by the inner join. The cutoff assumes `publishTime` represents when the forecast was operationally available.

## Key results

- MAE: **2,022 MW** (**17.9%** of mean actual generation)
- RMSE: **2,497 MW**
- Bias: **+1,746 MW**, an over-forecast of **15.5%** relative to mean actual generation
- P90 absolute error: **4,154 MW**
- Forecasts selected after the cutoff: **0**

## Known limitations

- Hourly forecast resolution; half-hourly `:30` actuals are excluded from the join.
- The dataset shows over-forecasting in January 2026; its cause is unconfirmed.
- January 2026 only; results may not generalize to other months or seasons.
- Wind generation only, at national level.
- The free-tier backend may have a cold start of up to a minute after idle time.

## AI usage

AI tools (Kiro and Codex) were used to help build the application. The author reviewed the code and verified the forecast selection logic with tests.

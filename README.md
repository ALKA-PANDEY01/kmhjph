# UK Wind Forecast Accuracy Web App

Web application for a UK energy utility client to evaluate wind generation forecast accuracy against actuals for January 2026 purchase decisions.

## Overview

The client's team buys wind-backed electricity from the UK day-ahead market. Decisions for delivery day D must be made on D-1 at **09:00 Europe/London**.

This app provides:
1. **Decision View**: What forecast was available at decision time for each hourly period
2. **Accuracy View**: Quantitative accuracy metrics (MAE, RMSE, MAPE, etc.)

## Architecture

```
┌─────────────────┐
│  Offline Script │  Fetch Elexon BMRS data, apply decision cutoff,
│   (Python)      │  compute errors → save to Parquet
└────────┬────────┘
         │
         ▼
    ┌────────────┐
    │  Parquet   │  Pre-processed data with errors
    │    File    │
    └─────┬──────┘
          │
          ▼
    ┌────────────┐
    │  FastAPI   │  Load Parquet at startup, serve REST API
    │  (Python)  │  Deploy: Heroku (Docker container stack)
    └─────┬──────┘
          │
          ▼
    ┌────────────┐
    │   React    │  Two pages: Decision View, Accuracy View
    │   (Vite)   │  Deploy: Vercel
    └────────────┘
```

## Data Source

**Elexon BMRS API** (public, no API key required):
- **FUELHH**: Actual half-hourly wind generation, joined to hourly WINDFOR forecasts; unmatched :30 actuals are excluded
- **WINDFOR**: Wind generation forecasts (with publish times)

## Project Structure

```
Energy_forecast/
├── ingestion/          # Offline Python script
│   ├── ingest.py       # Main entry point
│   ├── config.py       # Configuration (dates, URLs, cutoff)
│   ├── fetch_elexon.py # Elexon API client
│   ├── process_data.py # Data processing logic
│   ├── requirements.txt
│   └── README.md
│
├── backend/            # FastAPI (coming in Phase 2)
│   └── (TBD)
│
├── frontend/           # React + Vite (coming in Phase 3)
│   └── (TBD)
│
├── data/               # Generated data files (git-ignored)
│   └── wind_forecast_accuracy.parquet
│
└── README.md           # This file
```

## Phase 1: Offline Ingestion ✓

**Status**: Complete

See `ingestion/README.md` for details.

**Quick Start**:
```powershell
cd ingestion
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python ingest.py
```

Output: `data/wind_forecast_accuracy.parquet`

## Phase 2: FastAPI Backend (Coming Next)

- Load Parquet at startup
- Serve REST endpoints for frontend
- Deploy to Heroku with Docker

## Phase 3: React Frontend (Coming Next)

- Decision View page
- Accuracy View page
- Deploy to Vercel

## Key Business Rules

- **Decision cutoff**: 09:00 Europe/London on D-1
- **Forecast selection**: Latest forecast published ≤ cutoff time
- **Data scope**: January 2026 decisions (deliveries 2 Jan - 1 Feb 2026)
- **Timezone**: January = GMT (UTC+0, no daylight saving)

## Known limitations

- **Hourly resolution**: WINDFOR timestamps are hourly. The inner join drops the half-hourly FUELHH `:30` records, leaving 744 joined rows for the 31-day period.
- **Persistent over-forecast**: January 2026 forecasts average about 15.5% above actual generation (bias 1,745.94 MW against mean actual generation of about 11,670 MW). A possible cause is a difference in coverage or generation basis between WINDFOR forecasts and FUELHH actuals; this cause is unconfirmed.
- **Cutoff assumption**: Forecast selection treats the latest record with `publishTime` at or before 09:00 Europe/London on D-1 as available for the decision. This assumes the published timestamp represents operational availability.
- **Join drops half-hours**: Hourly WINDFOR has no `:30` targets, so the join excludes those FUELHH actuals.
- **January-only scope**: The dataset covers January 2026 decisions (deliveries 2 Jan–1 Feb 2026); results may not represent other seasons or months.

## Tech Stack

| Component | Technology | Deployment |
|-----------|-----------|------------|
| Ingestion | Python 3.11+ | Run locally/CI |
| Backend | FastAPI, Pandas, Pyarrow | Heroku (Docker) |
| Frontend | React, Vite, TypeScript | Vercel |
| Data | Parquet | Loaded at runtime |

## License

Proprietary - UK Energy Utility Client

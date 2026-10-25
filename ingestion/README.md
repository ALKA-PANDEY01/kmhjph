# Elexon BMRS Data Ingestion

Offline script to fetch, process, and prepare wind forecast accuracy data for the UK energy utility client.

## What It Does

1. **Fetches actuals** from Elexon FUELHH stream (wind generation by half-hour; joined data is hourly)
2. **Fetches forecasts** from Elexon WINDFOR stream (hourly wind forecasts)
3. **Applies decision cutoff logic**: For each delivery hour, selects the forecast with the latest publish time that was available at 09:00 London time on D-1
4. **Joins** actuals with selected forecasts
5. **Computes errors**: error, absolute error, squared error, absolute percentage error
6. **Saves to Parquet** for fast loading by the API

## Files

- `config.py` - Configuration (dates, URLs, cutoff time)
- `fetch_elexon.py` - Elexon API client
- `process_data.py` - Data cleaning and processing logic
- `ingest.py` - Main script (entry point)
- `requirements.txt` - Python dependencies

## Setup

```powershell
# Create virtual environment
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## Run

```powershell
python ingest.py
```

Output: `data/wind_forecast_accuracy.parquet`

## Configuration

Edit `config.py` to change:
- Delivery date range (currently: 2 Jan - 1 Feb 2026)
- Decision cutoff hour (currently: 09:00)
- Output path

## Data Scope

- **Decision period**: January 2026 (decisions made 1-31 Jan for deliveries 2 Jan - 1 Feb)
- **Decision cutoff**: 09:00 Europe/London on D-1
- **Timezone**: In January, London = GMT (UTC+0)

## Output Schema

| Column | Type | Description |
|--------|------|-------------|
| `startTime` | timestamp (UTC) | Target delivery hour |
| `publishTime` | timestamp (UTC) | When the forecast was issued |
| `forecast_generation` | float | Forecasted wind generation (MW) |
| `actual_generation` | float | Actual wind generation (MW) |
| `error` | float | Forecast - Actual (MW) |
| `absolute_error` | float | \|error\| (MW) |
| `squared_error` | float | error² (MW²) |
| `absolute_percentage_error` | float | \|error\| / actual × 100 (%) |

## Verification

After running, check:

1. **Record count**: WINDFOR is hourly; the inner join drops FUELHH `:30` records, so expect about 744 joined records for 31 days
2. **Join coverage**: Hourly timestamps have both forecast and actual; FUELHH `:30` timestamps have no hourly WINDFOR match
3. **Time range**: startTime should span 2026-01-02 00:00 to 2026-02-01 23:30 (UTC)
4. **Error statistics**: Check mean error, MAE, RMSE, MAPE in the log output

## Troubleshooting

**Issue**: Missing forecasts for some delivery times

- Check if WINDFOR data is available for the query range
- Verify that forecasts were published before the decision cutoff
- Check `FORECAST_QUERY_START_DATE` in config (may need to fetch earlier forecasts)

**Issue**: Time resolution mismatch (WINDFOR hourly vs FUELHH half-hourly)

- WINDFOR sample data shows hourly resolution
- If this persists in prod data, we may need interpolation logic
- Contact Elexon support to confirm WINDFOR resolution

**Issue**: API rate limits or timeouts

- Adjust `REQUEST_TIMEOUT` in config
- Add retry logic or split date ranges into smaller chunks

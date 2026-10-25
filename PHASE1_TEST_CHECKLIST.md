# Phase 1 Test Checklist

## Setup (one-time)

```powershell
# Navigate to ingestion directory
cd c:\Users\Sheetal\Desktop\Energy_forecast\ingestion

# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## Run the Ingestion Script

```powershell
# Make sure you're in the ingestion directory with venv activated
python ingest.py
```

## Expected Output

The script should:

1. ✅ Fetch FUELHH actuals for 2026-01-02 to 2026-02-01
2. ✅ Fetch WINDFOR forecasts for 2025-12-30 to 2026-02-02
3. ✅ Select one forecast per target half-hour (published before 09:00 D-1)
4. ✅ Join actuals with forecasts
5. ✅ Compute errors (error, absolute_error, squared_error, absolute_percentage_error)
6. ✅ Save to `../data/wind_forecast_accuracy.parquet`

## Verification Checks

### 1. File Created
```powershell
Test-Path ..\data\wind_forecast_accuracy.parquet
# Should return: True
```

### 2. Record Count
Expected: **~1,488 records** (31 days × 48 half-hours)

```powershell
# Quick check with Python
python -c "import pandas as pd; df = pd.read_parquet('../data/wind_forecast_accuracy.parquet'); print(f'Records: {len(df)}'); print(f'Columns: {list(df.columns)}'); print(df.head())"
```

### 3. Expected Columns

- `startTime` (timestamp, UTC)
- `publishTime` (timestamp, UTC)
- `forecast_generation` (float, MW)
- `actual_generation` (float, MW)
- `error` (float, MW)
- `absolute_error` (float, MW)
- `squared_error` (float, MW²)
- `absolute_percentage_error` (float, %)

### 4. Time Range
- `startTime` should span: **2026-01-02 00:00:00 UTC** to **2026-02-01 23:30:00 UTC**
- `publishTime` should all be **before** their corresponding decision cutoffs (09:00 D-1)

### 5. Data Quality
- ✅ No null values in key columns (startTime, forecast_generation, actual_generation)
- ✅ All forecasts published before their decision cutoff
- ✅ Error = forecast_generation - actual_generation

### 6. Error Statistics (from log output)
Check the log for reasonable values:
- Mean Error (ME) - should be close to 0 if forecasts are unbiased
- Mean Absolute Error (MAE) - typical range: hundreds of MW
- Root Mean Squared Error (RMSE) - slightly higher than MAE
- Mean Absolute Percentage Error (MAPE) - typical range: 5-20%

## Troubleshooting

### Issue: API connection error

**Symptom**: `Failed to fetch FUELHH` or `Failed to fetch WINDFOR`

**Solutions**:
1. Check internet connection
2. Verify API URLs in `config.py`
3. Try accessing the API manually:
   ```powershell
   Invoke-RestMethod -Uri "https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream?settlementDateFrom=2026-01-02&settlementDateTo=2026-01-03&fuelType=WIND"
   ```

### Issue: Missing forecasts for some delivery times

**Symptom**: Fewer than 1,488 records in output

**Root cause**: WINDFOR data may not have forecasts for all target times before the cutoff

**Solutions**:
1. Check `FORECAST_QUERY_START_DATE` in `config.py` - may need to fetch earlier
2. Verify WINDFOR has half-hourly resolution (sample data showed hourly)
3. Check log for "X actuals have no matching forecast" warning

### Issue: Time resolution mismatch

**Symptom**: WINDFOR returns hourly data (top of hour) but FUELHH is half-hourly

**Root cause**: WINDFOR dataset may only provide hourly forecasts

**Solutions**:
1. Verify with Elexon documentation
2. If confirmed hourly, we'll need to add interpolation logic in Phase 2
3. For now, we'll only match on the hourly points

### Issue: Import errors

**Symptom**: `ModuleNotFoundError: No module named 'pandas'` or similar

**Solutions**:
1. Make sure virtual environment is activated: `.\venv\Scripts\Activate.ps1`
2. Reinstall dependencies: `pip install -r requirements.txt`

## Success Criteria

✅ Script runs without errors  
✅ Parquet file created in `data/` directory  
✅ ~1,488 records (or explanation for fewer)  
✅ All 8 expected columns present  
✅ Time range covers 2026-01-02 to 2026-02-01  
✅ Error statistics look reasonable  

## Next Steps After Success

Once Phase 1 is verified:
1. Commit the ingestion code to git
2. Move to **Phase 2**: Build FastAPI backend to serve this data
3. Backend will load the Parquet file at startup and expose REST endpoints

## Manual Data Inspection (Optional)

```powershell
# Install pandas in your main Python environment (if not already)
pip install pandas pyarrow

# Inspect the data
python
```

```python
import pandas as pd

df = pd.read_parquet('../data/wind_forecast_accuracy.parquet')

# Basic info
print(f"Records: {len(df)}")
print(f"Columns: {list(df.columns)}")
print(f"\nTime range:")
print(f"  Start: {df['startTime'].min()}")
print(f"  End: {df['startTime'].max()}")

# Sample rows
print("\nFirst 10 rows:")
print(df.head(10))

# Error statistics
print("\nError Statistics:")
print(df[['error', 'absolute_error', 'squared_error', 'absolute_percentage_error']].describe())

# Check for missing data
print("\nMissing values:")
print(df.isnull().sum())

# Verify forecast selection logic
print("\nSample: checking one delivery day")
sample_day = df[df['startTime'].dt.date == pd.Timestamp('2026-01-15').date()]
print(sample_day[['startTime', 'publishTime', 'forecast_generation', 'actual_generation']])
```

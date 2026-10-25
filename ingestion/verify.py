#!/usr/bin/env python3
"""
Verification script to answer specific questions about the ingested data.
"""

import pandas as pd
from datetime import datetime, timedelta
import pytz

# Load the data
df = pd.read_parquet('data/wind_forecast_accuracy.parquet')

print('=' * 60)
print('VERIFICATION RESULTS')
print('=' * 60)
print()

# 1. Row count
print(f'1. Row count: {len(df)}')
print()

# 2. Min and max startTime
print(f'2. Min startTime: {df["startTime"].min()}')
print(f'   Max startTime: {df["startTime"].max()}')
print()

# 3. Rows with NULL forecast
print(f'3. Rows with NULL forecast: {df["forecast_generation"].isnull().sum()}')
print()

# 4. Columns
print(f'4. Columns:')
for col in df.columns:
    print(f'   - {col}')
print()

# === TARGET TIME ANALYSIS ===
print('=' * 60)
print('TARGET TIME: 2026-01-15 12:00:00 UTC')
print('=' * 60)
print()

target = pd.Timestamp('2026-01-15 12:00:00', tz='UTC')

# Compute decision cutoff
london_tz = pytz.timezone('Europe/London')
delivery_london = target.tz_convert(london_tz)
decision_date = delivery_london.date() - timedelta(days=1)
decision_time_london = london_tz.localize(
    datetime.combine(decision_date, datetime.min.time().replace(hour=9))
)
cutoff_utc = decision_time_london.astimezone(pytz.UTC)

print(f'Decision cutoff (09:00 Europe/London on D-1):')
print(f'  {cutoff_utc}')
print()

# Find all WINDFOR records for this target time
# Need to load raw forecasts to show all publishTimes
import requests

url = "https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream"
params = {
    "publishDateTimeFrom": "2025-12-01T00:00:00Z",
    "publishDateTimeTo": "2026-02-01T12:00:00Z"
}

print('Fetching all WINDFOR records for this target...')
response = requests.get(url, params=params, timeout=60)
all_forecasts = response.json()

# Filter for target time
target_forecasts = [
    f for f in all_forecasts 
    if pd.Timestamp(f['startTime'], tz='UTC') == target
]

target_forecasts_df = pd.DataFrame(target_forecasts)
target_forecasts_df['publishTime'] = pd.to_datetime(target_forecasts_df['publishTime'], utc=True)
target_forecasts_df['startTime'] = pd.to_datetime(target_forecasts_df['startTime'], utc=True)
target_forecasts_df = target_forecasts_df.sort_values('publishTime')

print(f'Found {len(target_forecasts_df)} WINDFOR forecasts for target {target}:')
print()
print('All publishTimes available:')
for idx, row in target_forecasts_df.iterrows():
    before_cutoff = "✓ BEFORE CUTOFF" if row['publishTime'] <= cutoff_utc else "✗ AFTER CUTOFF"
    print(f"  - {row['publishTime']} : generation={row['generation']} MW [{before_cutoff}]")
print()

# Find which one was selected
forecasts_before_cutoff = target_forecasts_df[target_forecasts_df['publishTime'] <= cutoff_utc]
if len(forecasts_before_cutoff) > 0:
    selected = forecasts_before_cutoff.iloc[-1]
    print(f'Selected forecast:')
    print(f'  publishTime: {selected["publishTime"]}')
    print(f'  generation: {selected["generation"]} MW')
    print()
    
    # Verify it's the latest before cutoff
    is_latest = selected['publishTime'] == forecasts_before_cutoff['publishTime'].max()
    print(f'Confirmation: This is the LATEST publishTime before cutoff? {is_latest}')
else:
    print('ERROR: No forecasts published before cutoff!')
print()

# Show the actual record in the output file
print('=' * 60)
print('Record in output Parquet file:')
print('=' * 60)
target_row = df[df['startTime'] == target]
if len(target_row) > 0:
    print(target_row.to_string(index=False))
else:
    print('NOT FOUND in output file!')
print()

# 5 sample rows
print('=' * 60)
print('5 SAMPLE ROWS (forecast, actual, error):')
print('=' * 60)
sample = df[['startTime', 'publishTime', 'forecast_generation', 'actual_generation', 'error']].head(5)
print(sample.to_string(index=False))

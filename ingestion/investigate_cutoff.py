"""Investigate the cutoff contradiction for 2026-01-15 12:00 UTC"""
import pandas as pd
from datetime import datetime, timezone
import pytz
from process_data import compute_decision_cutoff
from fetch_elexon import ElexonClient

# Fetch WINDFOR data
print("Fetching WINDFOR data for investigation...")
client = ElexonClient()
windfor_data = client.fetch_windfor(
    publish_datetime_from="2025-12-01T00:00:00Z",
    publish_datetime_to="2026-02-01T12:00:00Z"
)
client.close()

windfor_df = pd.DataFrame(windfor_data)
windfor_df['publishTime'] = pd.to_datetime(windfor_df['publishTime'], utc=True)
windfor_df['startTime'] = pd.to_datetime(windfor_df['startTime'], utc=True)
print(f"Fetched {len(windfor_df)} WINDFOR records")

# Target time
target = pd.Timestamp('2026-01-15 12:00:00', tz='UTC')
target_forecasts = windfor_df[windfor_df['startTime'] == target].copy()

print(f'\n=== All WINDFOR forecasts for {target} ===')
print(f'Total available: {len(target_forecasts)}')

# Compute cutoff for this target
cutoff = compute_decision_cutoff(target)
print(f'\nDecision cutoff (UTC): {cutoff}')
print()

# Show all publishTimes
target_forecasts = target_forecasts.sort_values('publishTime')
print('All publishTimes available:')
for idx, row in target_forecasts.iterrows():
    before_cutoff = 'BEFORE' if row['publishTime'] <= cutoff else 'AFTER '
    diff_hours = (row['publishTime'] - cutoff).total_seconds() / 3600
    print(f"  {row['publishTime']} - {before_cutoff} cutoff ({diff_hours:+.2f}h) - {row['generation']:,} MW")

# Filter to before cutoff
before = target_forecasts[target_forecasts['publishTime'] <= cutoff]
print(f'\n>>> Forecasts BEFORE cutoff: {len(before)}')
if len(before) > 0:
    latest = before.iloc[-1]
    print(f'>>> Latest BEFORE cutoff: {latest["publishTime"]}')
    print(f'>>> Forecast: {latest["generation"]:,} MW')

# Filter to after cutoff
after = target_forecasts[target_forecasts['publishTime'] > cutoff]
print(f'\n>>> Forecasts AFTER cutoff: {len(after)}')
if len(after) > 0:
    first_after = after.iloc[0]
    print(f'>>> First AFTER cutoff: {first_after["publishTime"]}')
    print(f'>>> Forecast: {first_after["generation"]:,} MW')

# Check what's in the final parquet
print('\n=== Checking final parquet file ===')
result_df = pd.read_parquet('data/wind_forecast_accuracy.parquet')
result_row = result_df[result_df['startTime'] == target]
if len(result_row) > 0:
    r = result_row.iloc[0]
    print(f'>>> Selected publishTime: {r["publishTime"]}')
    print(f'>>> Selected forecast: {r["forecast_generation"]:,} MW')
    
    # Check if this matches what we expected
    if len(before) > 0:
        if r['publishTime'] == latest['publishTime']:
            print('✓ Matches latest BEFORE cutoff')
        else:
            print('✗ DOES NOT match latest BEFORE cutoff!')
            print(f'  Expected: {latest["publishTime"]}')
            print(f'  Got: {r["publishTime"]}')
            
            # Check if it matches an AFTER forecast
            if len(after) > 0 and r['publishTime'] == first_after['publishTime']:
                print('  ⚠️  Matches first AFTER cutoff - BUG CONFIRMED!')

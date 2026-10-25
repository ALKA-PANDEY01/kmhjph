"""Check row integrity in the wind_forecast_accuracy.parquet file"""
import pandas as pd

df = pd.read_parquet('data/wind_forecast_accuracy.parquet')

print("=== ROW INTEGRITY CHECK ===\n")

# Total row count
print(f"Total rows: {len(df)}")

# Rows per delivery date
df['delivery_date'] = pd.to_datetime(df['startTime']).dt.date
rows_per_date = df.groupby('delivery_date').size()
print(f"\nRows per delivery date:")
print(rows_per_date)
print(f"\nExpected rows per day: 24 (hourly WINDFOR resolution)")
problematic_dates = rows_per_date[rows_per_date != 24]
if len(problematic_dates) > 0:
    print(f"⚠️  Dates with != 24 rows:")
    for date, count in problematic_dates.items():
        print(f"  {date}: {count} rows")
else:
    print("✓ All dates have 24 rows")

# Check for missing or duplicate startTime values
print(f"\n=== DUPLICATES CHECK ===")
duplicates = df[df.duplicated('startTime', keep=False)]
if len(duplicates) > 0:
    print(f"⚠️  Found {len(duplicates)} duplicate startTime rows:")
    print(duplicates[['startTime', 'publishTime', 'forecast_generation']].sort_values('startTime'))
else:
    print("✓ No duplicate startTime values")

# Check first and last startTime
df_sorted = df.sort_values('startTime')
print(f"\n=== FIRST/LAST TIMES ===")
print(f"First startTime: {df_sorted.iloc[0]['startTime']}")
print(f"Last startTime: {df_sorted.iloc[-1]['startTime']}")

# Check for gaps in the time series
print(f"\n=== GAP CHECK ===")
df_sorted = df_sorted.reset_index(drop=True)
time_diffs = df_sorted['startTime'].diff()
expected_diff = pd.Timedelta(hours=1)  # Should be hourly based on WINDFOR data
unusual_gaps = time_diffs[time_diffs != expected_diff].dropna()

if len(unusual_gaps) > 0:
    print(f"⚠️  Found {len(unusual_gaps)} unusual time gaps:")
    for idx in unusual_gaps.index[:10]:  # Show first 10
        prev_time = df_sorted.loc[idx-1, 'startTime']
        curr_time = df_sorted.loc[idx, 'startTime']
        gap = (curr_time - prev_time).total_seconds() / 3600
        print(f"  {prev_time} -> {curr_time} (gap: {gap:.1f} hours)")
else:
    print(f"✓ All gaps are consistent ({expected_diff})")

# Check if data is sorted
is_sorted = df['startTime'].is_monotonic_increasing
print(f"\n=== SORT ORDER ===")
if is_sorted:
    print("✓ Data is sorted by startTime")
else:
    print("⚠️  Data is NOT sorted by startTime")

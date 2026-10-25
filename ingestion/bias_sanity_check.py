"""Bias sanity check - test for time misalignment"""
import pandas as pd
import numpy as np

df = pd.read_parquet('data/wind_forecast_accuracy.parquet')
df = df.sort_values('startTime').reset_index(drop=True)

print("=== BIAS SANITY CHECK ===\n")

def compute_metrics(forecast_series, actual_series, label):
    """Compute MAE, RMSE, and Bias"""
    errors = forecast_series - actual_series
    mae = np.mean(np.abs(errors))
    rmse = np.sqrt(np.mean(errors ** 2))
    bias = np.mean(errors)
    return {
        'scenario': label,
        'mae': mae,
        'rmse': rmse,
        'bias': bias
    }

results = []

# (a) Current selection
results.append(compute_metrics(
    df['forecast_generation'],
    df['actual_generation'],
    'Current (no shift)'
))

# (b) Shift forecast by -2 hours (forecast for t-2 compared to actual at t)
df_shift_m2 = df.copy()
df_shift_m2['forecast_generation'] = df_shift_m2['forecast_generation'].shift(-2)
df_shift_m2 = df_shift_m2.dropna()
results.append(compute_metrics(
    df_shift_m2['forecast_generation'],
    df_shift_m2['actual_generation'],
    'Forecast -2h'
))

# (c) Shift forecast by -1 hour
df_shift_m1 = df.copy()
df_shift_m1['forecast_generation'] = df_shift_m1['forecast_generation'].shift(-1)
df_shift_m1 = df_shift_m1.dropna()
results.append(compute_metrics(
    df_shift_m1['forecast_generation'],
    df_shift_m1['actual_generation'],
    'Forecast -1h'
))

# (d) Shift forecast by +1 hour
df_shift_p1 = df.copy()
df_shift_p1['forecast_generation'] = df_shift_p1['forecast_generation'].shift(1)
df_shift_p1 = df_shift_p1.dropna()
results.append(compute_metrics(
    df_shift_p1['forecast_generation'],
    df_shift_p1['actual_generation'],
    'Forecast +1h'
))

# (e) Shift forecast by +2 hours
df_shift_p2 = df.copy()
df_shift_p2['forecast_generation'] = df_shift_p2['forecast_generation'].shift(2)
df_shift_p2 = df_shift_p2.dropna()
results.append(compute_metrics(
    df_shift_p2['forecast_generation'],
    df_shift_p2['actual_generation'],
    'Forecast +2h'
))

# Create results table
results_df = pd.DataFrame(results)
results_df['mae'] = results_df['mae'].round(2)
results_df['rmse'] = results_df['rmse'].round(2)
results_df['bias'] = results_df['bias'].round(2)

print("Alignment Test Results:")
print("=" * 60)
print(f"{'Scenario':<20} {'MAE (MW)':<12} {'RMSE (MW)':<12} {'Bias (MW)':<12}")
print("=" * 60)
for _, row in results_df.iterrows():
    print(f"{row['scenario']:<20} {row['mae']:<12.2f} {row['rmse']:<12.2f} {row['bias']:<12.2f}")
print("=" * 60)

# Find best alignment
best_idx = results_df['mae'].idxmin()
best_scenario = results_df.loc[best_idx, 'scenario']
best_mae = results_df.loc[best_idx, 'mae']

print(f"\n>>> Lowest MAE: {best_mae:.2f} MW with {best_scenario}")

if best_scenario != 'Current (no shift)':
    print(f"⚠️  WARNING: Time misalignment detected!")
    print(f"   Current MAE is {results_df.loc[0, 'mae']:.2f} MW")
    print(f"   Best MAE is {best_mae:.2f} MW with {best_scenario}")
    print(f"   Improvement: {results_df.loc[0, 'mae'] - best_mae:.2f} MW")
else:
    print("✓ Current alignment is optimal")

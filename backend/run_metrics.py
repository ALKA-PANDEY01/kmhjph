#!/usr/bin/env python3
"""
Run metrics on the full January 2026 dataset.
"""

import sys
from pathlib import Path
import json

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.metrics import ForecastMetricsService

def main():
    # Path to the parquet file from ingestion
    parquet_path = Path(__file__).parent.parent / 'ingestion' / 'data' / 'wind_forecast_accuracy.parquet'
    
    if not parquet_path.exists():
        print(f"Error: Parquet file not found at {parquet_path}")
        print("Run the ingestion script first: cd ../ingestion && python ingest.py")
        sys.exit(1)
    
    print("=" * 70)
    print("WIND FORECAST ACCURACY METRICS - JANUARY 2026")
    print("=" * 70)
    print()
    
    # Initialize service
    service = ForecastMetricsService(str(parquet_path))
    
    # Compute metrics for full dataset
    print("Computing metrics for full dataset...")
    metrics = service.compute_metrics()
    
    # Display results
    print()
    print("=" * 70)
    print("OVERALL METRICS")
    print("=" * 70)
    print()
    print(f"Record Count:              {metrics['record_count']:,}")
    print(f"Date Range:                {metrics['date_range']['start']}")
    print(f"                           to {metrics['date_range']['end']}")
    print()
    print("=" * 70)
    print("ERROR STATISTICS")
    print("=" * 70)
    print()
    print(f"Mean Actual Generation:    {metrics['mean_actual']:,.2f} MW")
    print()
    print(f"MAE (Mean Absolute Error): {metrics['mae']:,.2f} MW")
    print(f"RMSE (Root Mean Squared):  {metrics['rmse']:,.2f} MW")
    print(f"Bias (Mean Error):         {metrics['bias']:+,.2f} MW")
    print(f"Normalised MAE:            {metrics['normalised_mae']:.4f} ({metrics['normalised_mae']*100:.2f}%)")
    print()
    print("=" * 70)
    print("PERCENTILES (Absolute Error)")
    print("=" * 70)
    print()
    print(f"P50 (Median):              {metrics['percentiles']['p50_absolute_error']:,.2f} MW")
    print(f"P90:                       {metrics['percentiles']['p90_absolute_error']:,.2f} MW")
    print(f"P95:                       {metrics['percentiles']['p95_absolute_error']:,.2f} MW")
    print()
    print("=" * 70)
    print("ERROR BY HOUR OF DAY (Mean Absolute Error)")
    print("=" * 70)
    print()
    
    # Sort by hour
    sorted_hours = sorted(metrics['error_by_hour'].items())
    for hour, mae in sorted_hours:
        print(f"  {hour:02d}:00 - {mae:,.2f} MW")
    
    print()
    print("=" * 70)
    print("HISTOGRAM (Absolute Error Distribution)")
    print("=" * 70)
    print()
    
    bins = metrics['histogram']['bins']
    counts = metrics['histogram']['counts']
    
    print(f"{'Error Range (MW)':<25} {'Count':<10} {'Percentage':>12}")
    print("-" * 50)
    
    total_count = sum(counts)
    for i in range(len(counts)):
        if counts[i] > 0:  # Only show non-empty bins
            bin_start = bins[i]
            bin_end = bins[i + 1]
            percentage = (counts[i] / total_count) * 100
            print(f"{bin_start:>7.0f} - {bin_end:<7.0f} MW   {counts[i]:>5}      {percentage:>7.1f}%")
    
    print()
    print("=" * 70)
    print("PLAIN ENGLISH SUMMARY")
    print("=" * 70)
    print()
    print(metrics['summary'])
    print()
    
    # Save to JSON for reference
    output_path = Path(__file__).parent / 'metrics_output.json'
    with open(output_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print()
    print(f"Full metrics saved to: {output_path}")
    print()


if __name__ == '__main__':
    main()

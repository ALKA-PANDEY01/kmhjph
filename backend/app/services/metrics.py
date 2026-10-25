"""
Wind forecast accuracy metrics service.

Loads wind_forecast_accuracy.parquet and computes comprehensive error metrics.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ForecastMetricsService:
    """Service for computing wind forecast accuracy metrics."""
    
    def __init__(self, parquet_path: str):
        """
        Initialize the service by loading the parquet file.
        
        Args:
            parquet_path: Path to wind_forecast_accuracy.parquet
        """
        self.parquet_path = Path(parquet_path)
        if not self.parquet_path.exists():
            raise FileNotFoundError(f"Parquet file not found: {parquet_path}")
        
        self.df = pd.read_parquet(self.parquet_path)
        logger.info(f"Loaded {len(self.df)} records from {parquet_path}")
        
        # Validate required columns
        required_cols = [
            'startTime', 'publishTime', 
            'forecast_generation', 'actual_generation', 
            'error', 'absolute_error'
        ]
        missing = [col for col in required_cols if col not in self.df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
    
    def get_data(
        self, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get filtered data for a date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD), inclusive. None = no start filter
            end_date: End date (YYYY-MM-DD), inclusive. None = no end filter
        
        Returns:
            Filtered DataFrame
        """
        df = self.df.copy()
        
        if start_date:
            start = pd.Timestamp(start_date, tz='UTC')
            df = df[df['startTime'] >= start]
        
        if end_date:
            # End date is inclusive, so add 1 day and use <
            end = pd.Timestamp(end_date, tz='UTC') + pd.Timedelta(days=1)
            df = df[df['startTime'] < end]
        
        return df
    
    def compute_metrics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compute comprehensive forecast accuracy metrics.
        
        Args:
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)
        
        Returns:
            Dictionary with all metrics
        """
        df = self.get_data(start_date, end_date)
        
        if len(df) == 0:
            return {
                "error": "No data in specified date range",
                "record_count": 0
            }
        
        # Basic statistics
        forecast = df['forecast_generation']
        actual = df['actual_generation']
        error = df['error']  # forecast - actual
        abs_error = df['absolute_error']
        
        # Core metrics
        mae = abs_error.mean()
        rmse = np.sqrt((error ** 2).mean())
        bias = error.mean()  # Mean of (forecast - actual)
        mean_actual = actual.mean()
        normalised_mae = mae / mean_actual if mean_actual > 0 else None
        
        # Percentiles of absolute error
        p50_abs_error = abs_error.quantile(0.50)
        p90_abs_error = abs_error.quantile(0.90)
        p95_abs_error = abs_error.quantile(0.95)
        p5_signed_error = error.quantile(0.05)
        p95_signed_error = error.quantile(0.95)
        
        # Error by hour of day
        df['hour'] = df['startTime'].dt.hour
        error_by_hour = df.groupby('hour')['absolute_error'].mean().to_dict()
        
        # Histogram bins and counts
        # Use reasonable bins for wind forecast errors (every 500 MW)
        max_error = abs_error.max()
        bins = np.arange(0, max_error + 500, 500)
        hist_counts, hist_bins = np.histogram(abs_error, bins=bins)
        
        histogram = {
            "bins": hist_bins.tolist(),
            "counts": hist_counts.tolist()
        }
        
        # Plain English summary
        num_records = len(df)
        summary = (
            f"Over {num_records} hourly periods, the forecast was within "
            f"{p90_abs_error:.0f} MW of actual in 90% of cases. "
            f"The average error was {mae:.0f} MW ({normalised_mae*100:.1f}% of mean generation). "
            f"Forecasts {'over-predicted' if bias > 0 else 'under-predicted'} by "
            f"{abs(bias):.0f} MW on average."
        )
        
        return {
            "record_count": num_records,
            "date_range": {
                "start": df['startTime'].min().isoformat(),
                "end": df['startTime'].max().isoformat()
            },
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "bias": round(bias, 2),
            "mean_actual": round(mean_actual, 2),
            "normalised_mae": round(normalised_mae, 4) if normalised_mae else None,
            "percentiles": {
                "p50_absolute_error": round(p50_abs_error, 2),
                "p90_absolute_error": round(p90_abs_error, 2),
                "p95_absolute_error": round(p95_abs_error, 2),
                "p5_signed_error": round(p5_signed_error, 2),
                "p95_signed_error": round(p95_signed_error, 2)
            },
            "error_by_hour": {
                hour: round(mae_val, 2) 
                for hour, mae_val in error_by_hour.items()
            },
            "histogram": histogram,
            "summary": summary
        }
    
    def get_time_series(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get time series data for decision view.
        
        Args:
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)
        
        Returns:
            List of records with timestamp, forecast, actual, error
        """
        df = self.get_data(start_date, end_date)
        
        records = []
        for _, row in df.iterrows():
            records.append({
                "startTime": row['startTime'].isoformat(),
                "publishTime": row['publishTime'].isoformat(),
                "forecast": round(row['forecast_generation'], 2),
                "actual": round(row['actual_generation'], 2),
                "error": round(row['error'], 2)
            })
        
        return records

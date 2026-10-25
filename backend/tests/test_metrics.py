"""
Tests for forecast metrics service.

Tests include:
1. Hand-computed metric examples
2. Date range filtering
3. Edge cases
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
from datetime import datetime
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.metrics import ForecastMetricsService


@pytest.fixture
def sample_data_simple():
    """Simple hand-computed example."""
    data = {
        'startTime': pd.to_datetime([
            '2026-01-02 10:00:00',
            '2026-01-02 11:00:00',
            '2026-01-02 12:00:00',
            '2026-01-02 13:00:00',
        ], utc=True),
        'publishTime': pd.to_datetime([
            '2026-01-01 08:00:00',
            '2026-01-01 08:00:00',
            '2026-01-01 08:00:00',
            '2026-01-01 08:00:00',
        ], utc=True),
        'forecast_generation': [100.0, 200.0, 300.0, 400.0],
        'actual_generation': [110.0, 190.0, 310.0, 390.0],
        'error': [-10.0, 10.0, -10.0, 10.0],  # forecast - actual
        'absolute_error': [10.0, 10.0, 10.0, 10.0],
        'squared_error': [100.0, 100.0, 100.0, 100.0],
        'absolute_percentage_error': [9.09, 5.26, 3.23, 2.56]
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_data_with_bias():
    """Data with systematic over-forecasting."""
    data = {
        'startTime': pd.to_datetime([
            '2026-01-02 10:00:00',
            '2026-01-02 11:00:00',
            '2026-01-02 12:00:00',
        ], utc=True),
        'publishTime': pd.to_datetime([
            '2026-01-01 08:00:00',
            '2026-01-01 08:00:00',
            '2026-01-01 08:00:00',
        ], utc=True),
        'forecast_generation': [120.0, 230.0, 340.0],
        'actual_generation': [100.0, 200.0, 300.0],
        'error': [20.0, 30.0, 40.0],  # All positive = over-forecasting
        'absolute_error': [20.0, 30.0, 40.0],
        'squared_error': [400.0, 900.0, 1600.0],
        'absolute_percentage_error': [20.0, 15.0, 13.33]
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_parquet_file(sample_data_simple):
    """Create a temporary parquet file."""
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
        sample_data_simple.to_parquet(f.name, index=False)
        yield f.name
    Path(f.name).unlink()


def test_metrics_service_initialization(sample_parquet_file):
    """Test service initializes correctly."""
    service = ForecastMetricsService(sample_parquet_file)
    assert len(service.df) == 4
    assert 'startTime' in service.df.columns


def test_metrics_service_missing_file():
    """Test error when file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        ForecastMetricsService("nonexistent.parquet")


def test_mae_calculation(sample_parquet_file):
    """Test MAE calculation: mean of absolute errors."""
    service = ForecastMetricsService(sample_parquet_file)
    metrics = service.compute_metrics()
    
    # MAE = (10 + 10 + 10 + 10) / 4 = 10.0
    assert metrics['mae'] == 10.0


def test_rmse_calculation(sample_parquet_file):
    """Test RMSE calculation: sqrt(mean of squared errors)."""
    service = ForecastMetricsService(sample_parquet_file)
    metrics = service.compute_metrics()
    
    # RMSE = sqrt((100 + 100 + 100 + 100) / 4) = sqrt(100) = 10.0
    assert metrics['rmse'] == 10.0


def test_bias_calculation(sample_parquet_file):
    """Test bias calculation: mean of (forecast - actual)."""
    service = ForecastMetricsService(sample_parquet_file)
    metrics = service.compute_metrics()
    
    # Bias = (-10 + 10 + -10 + 10) / 4 = 0.0
    assert metrics['bias'] == 0.0


def test_bias_with_over_forecasting():
    """Test bias with systematic over-forecasting."""
    data = pd.DataFrame({
        'startTime': pd.to_datetime(['2026-01-02 10:00:00', '2026-01-02 11:00:00'], utc=True),
        'publishTime': pd.to_datetime(['2026-01-01 08:00:00', '2026-01-01 08:00:00'], utc=True),
        'forecast_generation': [120.0, 230.0],
        'actual_generation': [100.0, 200.0],
        'error': [20.0, 30.0],
        'absolute_error': [20.0, 30.0],
        'squared_error': [400.0, 900.0],
        'absolute_percentage_error': [20.0, 15.0]
    })
    
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
        temp_path = f.name
    
    data.to_parquet(temp_path, index=False)
    service = ForecastMetricsService(temp_path)
    metrics = service.compute_metrics()
    
    # Bias = (20 + 30) / 2 = 25.0 (positive = over-forecasting)
    assert metrics['bias'] == 25.0
    assert 'over-predicted' in metrics['summary']
    
    Path(temp_path).unlink()


def test_normalised_mae(sample_parquet_file):
    """Test normalised MAE calculation."""
    service = ForecastMetricsService(sample_parquet_file)
    metrics = service.compute_metrics()
    
    # Mean actual = (110 + 190 + 310 + 390) / 4 = 250.0
    # MAE = 10.0
    # Normalised MAE = 10.0 / 250.0 = 0.04
    assert metrics['normalised_mae'] == 0.04
    assert metrics['mean_actual'] == 250.0


def test_percentiles(sample_parquet_file):
    """Test percentile calculations."""
    service = ForecastMetricsService(sample_parquet_file)
    metrics = service.compute_metrics()
    
    # All absolute errors are 10.0, so all percentiles = 10.0
    assert metrics['percentiles']['p50_absolute_error'] == 10.0
    assert metrics['percentiles']['p90_absolute_error'] == 10.0
    assert metrics['percentiles']['p95_absolute_error'] == 10.0


def test_error_by_hour():
    """Test error grouping by hour of day."""
    data = pd.DataFrame({
        'startTime': pd.to_datetime([
            '2026-01-02 10:00:00',  # Hour 10
            '2026-01-02 10:00:00',  # Hour 10
            '2026-01-02 15:00:00',  # Hour 15
        ], utc=True),
        'publishTime': pd.to_datetime([
            '2026-01-01 08:00:00',
            '2026-01-01 08:00:00',
            '2026-01-01 08:00:00',
        ], utc=True),
        'forecast_generation': [100.0, 120.0, 300.0],
        'actual_generation': [110.0, 110.0, 350.0],
        'error': [-10.0, 10.0, -50.0],
        'absolute_error': [10.0, 10.0, 50.0],
        'squared_error': [100.0, 100.0, 2500.0],
        'absolute_percentage_error': [9.09, 9.09, 14.29]
    })
    
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
        temp_path = f.name
    
    data.to_parquet(temp_path, index=False)
    service = ForecastMetricsService(temp_path)
    metrics = service.compute_metrics()
    
    # Hour 10: MAE = (10 + 10) / 2 = 10.0
    # Hour 15: MAE = 50.0
    assert metrics['error_by_hour'][10] == 10.0
    assert metrics['error_by_hour'][15] == 50.0
    
    Path(temp_path).unlink()


def test_date_range_filter():
    """Test filtering by date range."""
    data = pd.DataFrame({
        'startTime': pd.to_datetime([
            '2026-01-02 10:00:00',
            '2026-01-03 10:00:00',
            '2026-01-04 10:00:00',
            '2026-01-05 10:00:00',
        ], utc=True),
        'publishTime': pd.to_datetime(['2026-01-01 08:00:00'] * 4, utc=True),
        'forecast_generation': [100.0, 200.0, 300.0, 400.0],
        'actual_generation': [110.0, 210.0, 310.0, 410.0],
        'error': [-10.0, -10.0, -10.0, -10.0],
        'absolute_error': [10.0, 10.0, 10.0, 10.0],
        'squared_error': [100.0] * 4,
        'absolute_percentage_error': [9.09, 4.76, 3.23, 2.44]
    })
    
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
        temp_path = f.name
    
    data.to_parquet(temp_path, index=False)
    service = ForecastMetricsService(temp_path)
    
    # Filter to Jan 3-4 (inclusive)
    metrics = service.compute_metrics(start_date='2026-01-03', end_date='2026-01-04')
    
    # Should only include 2 records
    assert metrics['record_count'] == 2
    
    # Verify date range in result
    assert '2026-01-03' in metrics['date_range']['start']
    assert '2026-01-04' in metrics['date_range']['end']
    
    Path(temp_path).unlink()


def test_empty_date_range():
    """Test behavior with empty date range."""
    data = pd.DataFrame({
        'startTime': pd.to_datetime(['2026-01-02 10:00:00'], utc=True),
        'publishTime': pd.to_datetime(['2026-01-01 08:00:00'], utc=True),
        'forecast_generation': [100.0],
        'actual_generation': [110.0],
        'error': [-10.0],
        'absolute_error': [10.0],
        'squared_error': [100.0],
        'absolute_percentage_error': [9.09]
    })
    
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
        temp_path = f.name
    
    data.to_parquet(temp_path, index=False)
    service = ForecastMetricsService(temp_path)
    
    # Request date range with no data
    metrics = service.compute_metrics(start_date='2026-02-01', end_date='2026-02-28')
    
    assert metrics['record_count'] == 0
    assert 'error' in metrics  # Should have error message
    
    Path(temp_path).unlink()


def test_histogram_structure():
    """Test histogram bins and counts structure."""
    data = pd.DataFrame({
        'startTime': pd.to_datetime([
            '2026-01-02 10:00:00',
            '2026-01-02 11:00:00',
            '2026-01-02 12:00:00',
        ], utc=True),
        'publishTime': pd.to_datetime(['2026-01-01 08:00:00'] * 3, utc=True),
        'forecast_generation': [100.0, 200.0, 1500.0],
        'actual_generation': [110.0, 210.0, 1000.0],
        'error': [-10.0, -10.0, 500.0],
        'absolute_error': [10.0, 10.0, 500.0],  # One small, one large
        'squared_error': [100.0, 100.0, 250000.0],
        'absolute_percentage_error': [9.09, 4.76, 50.0]
    })
    
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
        temp_path = f.name
    
    data.to_parquet(temp_path, index=False)
    service = ForecastMetricsService(temp_path)
    metrics = service.compute_metrics()
    
    # Should have histogram
    assert 'histogram' in metrics
    assert 'bins' in metrics['histogram']
    assert 'counts' in metrics['histogram']
    
    # Bins should be list of numbers
    assert isinstance(metrics['histogram']['bins'], list)
    assert len(metrics['histogram']['bins']) > 0
    
    # Counts should sum to number of records
    assert sum(metrics['histogram']['counts']) == 3
    
    Path(temp_path).unlink()


def test_summary_message(sample_parquet_file):
    """Test plain English summary generation."""
    service = ForecastMetricsService(sample_parquet_file)
    metrics = service.compute_metrics()
    
    summary = metrics['summary']
    
    # Should contain key phrases
    assert '90%' in summary
    assert 'MW' in summary
    assert 'average error' in summary
    
    # Should mention over or under prediction
    assert 'over-predicted' in summary or 'under-predicted' in summary


def test_time_series_output(sample_parquet_file):
    """Test time series data for decision view."""
    service = ForecastMetricsService(sample_parquet_file)
    time_series = service.get_time_series()
    
    assert len(time_series) == 4
    
    # Check structure of first record
    record = time_series[0]
    assert 'startTime' in record
    assert 'publishTime' in record
    assert 'forecast' in record
    assert 'actual' in record
    assert 'error' in record
    
    # Values should be rounded
    assert isinstance(record['forecast'], (int, float))
    assert isinstance(record['actual'], (int, float))

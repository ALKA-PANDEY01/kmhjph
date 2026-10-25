"""
FastAPI backend for wind forecast accuracy analysis.

Loads parquet data once at startup and serves REST API endpoints.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from pathlib import Path
import logging
import os
import pandas as pd
import pytz

from .models import (
    HealthResponse,
    ConfigResponse,
    ForecastDayResponse,
    ForecastPoint,
    ComparisonResponse,
    ComparisonPoint,
    MetricsResponse,
    ErrorByHourListResponse,
    ErrorByHourResponse,
    ErrorDistributionResponse,
    DistributionBin,
    ErrorResponse
)
from .services.metrics import ForecastMetricsService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Wind Forecast Accuracy API",
    description="API for analyzing UK wind generation forecast accuracy",
    version="1.0.0"
)

# CORS configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state - loaded at startup
metrics_service: ForecastMetricsService = None
data_df: pd.DataFrame = None
DATA_START: datetime = None
DATA_END: datetime = None


@app.on_event("startup")
async def startup_event():
    """Load parquet file once at startup."""
    global metrics_service, data_df, DATA_START, DATA_END
    
    # Path to parquet file
    parquet_path = Path(os.getenv(
        "DATA_PATH",
        str(Path(__file__).parent.parent / 'data' / 'wind_forecast_accuracy.parquet')
    ))
    
    if not parquet_path.exists():
        logger.error(f"Parquet file not found: {parquet_path}")
        raise RuntimeError("Data file not found. Run ingestion first.")
    
    logger.info(f"Loading data from {parquet_path}")
    metrics_service = ForecastMetricsService(str(parquet_path))
    data_df = metrics_service.df.copy()
    
    DATA_START = data_df['startTime'].min()
    DATA_END = data_df['startTime'].max()
    
    logger.info(f"Loaded {len(data_df)} records")
    logger.info(f"Date range: {DATA_START} to {DATA_END}")


def validate_date(date_str: str) -> datetime:
    """
    Validate and parse a date string.
    
    Args:
        date_str: Date in YYYY-MM-DD format
    
    Returns:
        Parsed datetime object (UTC)
    
    Raises:
        HTTPException: If date is invalid
    """
    try:
        dt = pd.Timestamp(date_str, tz='UTC')
        return dt
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {date_str}. Expected YYYY-MM-DD")


def check_date_in_range(dt: datetime, param_name: str = "date"):
    """
    Check if date is within available data range.
    
    Args:
        dt: Datetime to check
        param_name: Parameter name for error message
    
    Raises:
        HTTPException: If date is out of range
    """
    if dt < DATA_START or dt > DATA_END:
        raise HTTPException(
            status_code=400,
            detail=f"{param_name} {dt.date()} is out of range. Available: {DATA_START.date()} to {DATA_END.date()}"
        )


def compute_decision_cutoff_for_date(delivery_date: str) -> datetime:
    """
    Compute decision cutoff for a delivery date.
    
    Args:
        delivery_date: Delivery date (YYYY-MM-DD)
    
    Returns:
        Decision cutoff timestamp (UTC)
    """
    london_tz = pytz.timezone("Europe/London")
    
    # Parse delivery date
    delivery_dt = pd.Timestamp(delivery_date, tz='UTC')
    delivery_london = delivery_dt.tz_convert(london_tz)
    
    # Decision is made on D-1 at 09:00 London time
    decision_date = delivery_london.date() - timedelta(days=1)
    decision_time_london = london_tz.localize(
        datetime.combine(decision_date, datetime.min.time().replace(hour=9))
    )
    
    # Convert to UTC
    cutoff_utc = decision_time_london.astimezone(pytz.UTC)
    return cutoff_utc


# === API ENDPOINTS ===

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat() + "Z",
        records_loaded=len(data_df) if data_df is not None else 0
    )


@app.get("/api/config", response_model=ConfigResponse)
async def get_config():
    """Get API configuration and data range."""
    return ConfigResponse(
        decision_cutoff_hour=9,
        decision_cutoff_timezone="Europe/London",
        data_range={
            "start": DATA_START.date().isoformat(),
            "end": DATA_END.date().isoformat()
        },
        total_records=len(data_df),
        description="Decision cutoff: 09:00 Europe/London on D-1. Forecast is the latest one published before cutoff."
    )


@app.get("/api/forecast", response_model=ForecastDayResponse)
async def get_forecast_day(
    date: str = Query(..., description="Delivery date (YYYY-MM-DD)", pattern=r"^\d{4}-\d{2}-\d{2}$")
):
    """
    Get forecast and actual data for a specific delivery day.
    
    Returns up to 24 hourly points.
    Includes the decision cutoff used for that day.
    """
    # Validate date
    delivery_dt = validate_date(date)
    check_date_in_range(delivery_dt, "date")
    
    # Compute decision cutoff for this delivery date
    cutoff = compute_decision_cutoff_for_date(date)
    
    # Filter data for this delivery date
    delivery_end = delivery_dt + pd.Timedelta(days=1)
    day_data = data_df[
        (data_df['startTime'] >= delivery_dt) &
        (data_df['startTime'] < delivery_end)
    ].copy()
    
    if len(day_data) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No data available for {date}"
        )
    
    # Build data points
    points = []
    for _, row in day_data.iterrows():
        points.append(ForecastPoint(
            startTime=row['startTime'].isoformat(),
            publishTime=row['publishTime'].isoformat() if pd.notna(row['publishTime']) else None,
            forecast=round(row['forecast_generation'], 2) if pd.notna(row['forecast_generation']) else None,
            actual=round(row['actual_generation'], 2) if pd.notna(row['actual_generation']) else None,
            error=round(row['error'], 2) if pd.notna(row['error']) else None
        ))
    
    return ForecastDayResponse(
        delivery_date=date,
        decision_cutoff=cutoff.isoformat(),
        data_points=points,
        available_count=len(points)
    )


@app.get("/api/comparison", response_model=ComparisonResponse)
async def get_comparison(
    start: str = Query(..., description="Start date (YYYY-MM-DD)", pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end: str = Query(..., description="End date (YYYY-MM-DD)", pattern=r"^\d{4}-\d{2}-\d{2}$")
):
    """
    Get time-series comparison data for a date range.
    
    Returns forecast, actual, and error for each timestamp.
    """
    # Validate dates
    start_dt = validate_date(start)
    end_dt = validate_date(end)
    
    if start_dt > end_dt:
        raise HTTPException(status_code=400, detail="start date must be before or equal to end date")
    
    check_date_in_range(start_dt, "start")
    check_date_in_range(end_dt, "end")
    
    # Get time series data
    time_series = metrics_service.get_time_series(start_date=start, end_date=end)
    
    if len(time_series) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No data available for range {start} to {end}"
        )
    
    # Convert to response model
    data_points = [
        ComparisonPoint(
            startTime=point['startTime'],
            publishTime=point['publishTime'],
            forecast=point['forecast'],
            actual=point['actual'],
            error=point['error']
        )
        for point in time_series
    ]
    
    return ComparisonResponse(
        start_date=start,
        end_date=end,
        data=data_points,
        count=len(data_points)
    )


@app.get("/api/metrics", response_model=MetricsResponse)
async def get_metrics(
    start: str = Query(None, description="Start date (YYYY-MM-DD)", pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end: str = Query(None, description="End date (YYYY-MM-DD)", pattern=r"^\d{4}-\d{2}-\d{2}$")
):
    """
    Get comprehensive accuracy metrics.
    
    Optional date range filtering.
    """
    # Validate dates if provided
    if start:
        start_dt = validate_date(start)
        check_date_in_range(start_dt, "start")
    
    if end:
        end_dt = validate_date(end)
        check_date_in_range(end_dt, "end")
    
    if start and end and start_dt > end_dt:
        raise HTTPException(status_code=400, detail="start date must be before or equal to end date")
    
    # Compute metrics
    metrics = metrics_service.compute_metrics(start_date=start, end_date=end)
    
    if metrics.get('record_count', 0) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No data available for specified range"
        )
    
    return MetricsResponse(
        record_count=metrics['record_count'],
        date_range=metrics['date_range'],
        mae=metrics['mae'],
        rmse=metrics['rmse'],
        bias=metrics['bias'],
        mean_actual=metrics['mean_actual'],
        normalised_mae=metrics['normalised_mae'],
        percentiles=metrics['percentiles'],
        summary=metrics['summary']
    )


@app.get("/api/errors/by-hour", response_model=ErrorByHourListResponse)
async def get_errors_by_hour(
    start: str = Query(None, description="Start date (YYYY-MM-DD)", pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end: str = Query(None, description="End date (YYYY-MM-DD)", pattern=r"^\d{4}-\d{2}-\d{2}$")
):
    """
    Get error statistics grouped by hour of day.
    
    Useful for identifying time-of-day patterns in forecast accuracy.
    """
    # Validate dates if provided
    if start:
        start_dt = validate_date(start)
        check_date_in_range(start_dt, "start")
    
    if end:
        end_dt = validate_date(end)
        check_date_in_range(end_dt, "end")
    
    if start and end and start_dt > end_dt:
        raise HTTPException(status_code=400, detail="start date must be before or equal to end date")
    
    # Get filtered data
    df = metrics_service.get_data(start_date=start, end_date=end)
    
    if len(df) == 0:
        raise HTTPException(status_code=404, detail="No data available for specified range")
    
    # Group by hour
    df['hour'] = df['startTime'].dt.hour
    hourly_stats = df.groupby('hour').agg({
        'absolute_error': 'mean',
        'startTime': 'count'
    }).reset_index()
    hourly_stats.columns = ['hour', 'mae', 'count']
    
    # Build response
    data = [
        ErrorByHourResponse(
            hour=int(row['hour']),
            mae=round(row['mae'], 2),
            count=int(row['count'])
        )
        for _, row in hourly_stats.iterrows()
    ]
    
    return ErrorByHourListResponse(
        start_date=start,
        end_date=end,
        data=sorted(data, key=lambda x: x.hour)
    )


@app.get("/api/errors/distribution", response_model=ErrorDistributionResponse)
async def get_error_distribution(
    start: str = Query(None, description="Start date (YYYY-MM-DD)", pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end: str = Query(None, description="End date (YYYY-MM-DD)", pattern=r"^\d{4}-\d{2}-\d{2}$")
):
    """
    Get error distribution histogram.
    
    Shows how forecast errors are distributed across magnitude ranges.
    """
    # Validate dates if provided
    if start:
        start_dt = validate_date(start)
        check_date_in_range(start_dt, "start")
    
    if end:
        end_dt = validate_date(end)
        check_date_in_range(end_dt, "end")
    
    if start and end and start_dt > end_dt:
        raise HTTPException(status_code=400, detail="start date must be before or equal to end date")
    
    # Get metrics (includes histogram)
    metrics = metrics_service.compute_metrics(start_date=start, end_date=end)
    
    if metrics.get('record_count', 0) == 0:
        raise HTTPException(status_code=404, detail="No data available for specified range")
    
    # Build histogram response
    bins_list = metrics['histogram']['bins']
    counts_list = metrics['histogram']['counts']
    total_count = sum(counts_list)
    
    bins = []
    for i in range(len(counts_list)):
        if counts_list[i] > 0:  # Only include non-empty bins
            bins.append(DistributionBin(
                bin_start=round(bins_list[i], 2),
                bin_end=round(bins_list[i + 1], 2),
                count=int(counts_list[i]),
                percentage=round((counts_list[i] / total_count) * 100, 2)
            ))
    
    return ErrorDistributionResponse(
        start_date=start,
        end_date=end,
        total_count=total_count,
        bins=bins
    )

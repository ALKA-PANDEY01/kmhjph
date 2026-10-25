"""
Pydantic models for API responses.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Current timestamp (ISO 8601)")
    records_loaded: int = Field(..., description="Number of records in memory")


class ConfigResponse(BaseModel):
    """Configuration response."""
    decision_cutoff_hour: int = Field(..., description="Decision cutoff hour (London time)")
    decision_cutoff_timezone: str = Field(..., description="Timezone for cutoff")
    data_range: Dict[str, str] = Field(..., description="Available data range")
    total_records: int = Field(..., description="Total records available")
    description: str = Field(..., description="Business rule description")


class ForecastPoint(BaseModel):
    """Single forecast/actual data point."""
    startTime: str = Field(..., description="Target delivery time (ISO 8601)")
    publishTime: Optional[str] = Field(None, description="When forecast was published (ISO 8601)")
    forecast: Optional[float] = Field(None, description="Forecast generation (MW)")
    actual: Optional[float] = Field(None, description="Actual generation (MW)")
    error: Optional[float] = Field(None, description="Forecast - Actual (MW)")


class ForecastDayResponse(BaseModel):
    """Response for a single delivery day."""
    delivery_date: str = Field(..., description="Delivery date (YYYY-MM-DD)")
    decision_cutoff: str = Field(..., description="Decision cutoff used (ISO 8601)")
    data_points: List[ForecastPoint] = Field(..., description="Up to 24 hourly points")
    available_count: int = Field(..., description="Number of points with forecast data")


class ComparisonPoint(BaseModel):
    """Single point for time-series comparison."""
    startTime: str = Field(..., description="Target delivery time (ISO 8601)")
    publishTime: str = Field(..., description="When forecast was published (ISO 8601)")
    forecast: float = Field(..., description="Forecast generation (MW)")
    actual: float = Field(..., description="Actual generation (MW)")
    error: float = Field(..., description="Forecast - Actual (MW)")


class ComparisonResponse(BaseModel):
    """Time series comparison response."""
    start_date: str = Field(..., description="Start date filter (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date filter (YYYY-MM-DD)")
    data: List[ComparisonPoint] = Field(..., description="Time series data points")
    count: int = Field(..., description="Number of data points")


class MetricsResponse(BaseModel):
    """Comprehensive metrics response."""
    record_count: int = Field(..., description="Number of records analyzed")
    date_range: Dict[str, str] = Field(..., description="Actual date range of data")
    mae: float = Field(..., description="Mean Absolute Error (MW)")
    rmse: float = Field(..., description="Root Mean Squared Error (MW)")
    bias: float = Field(..., description="Bias: mean(forecast - actual) (MW)")
    mean_actual: float = Field(..., description="Mean actual generation (MW)")
    normalised_mae: Optional[float] = Field(None, description="MAE / mean_actual")
    percentiles: Dict[str, float] = Field(..., description="Absolute error percentiles and P5/P95 signed error")
    summary: str = Field(..., description="Plain English summary")


class ErrorByHourResponse(BaseModel):
    """Error grouped by hour of day."""
    hour: int = Field(..., description="Hour of day (0-23)")
    mae: float = Field(..., description="Mean Absolute Error for this hour (MW)")
    count: int = Field(..., description="Number of observations")


class ErrorByHourListResponse(BaseModel):
    """List of errors by hour."""
    start_date: Optional[str] = Field(None, description="Start date filter")
    end_date: Optional[str] = Field(None, description="End date filter")
    data: List[ErrorByHourResponse] = Field(..., description="Hourly error statistics")


class DistributionBin(BaseModel):
    """Single histogram bin."""
    bin_start: float = Field(..., description="Bin start (MW)")
    bin_end: float = Field(..., description="Bin end (MW)")
    count: int = Field(..., description="Number of observations")
    percentage: float = Field(..., description="Percentage of total")


class ErrorDistributionResponse(BaseModel):
    """Error distribution histogram."""
    start_date: Optional[str] = Field(None, description="Start date filter")
    end_date: Optional[str] = Field(None, description="End date filter")
    total_count: int = Field(..., description="Total observations")
    bins: List[DistributionBin] = Field(..., description="Histogram bins")


class ErrorResponse(BaseModel):
    """Error response."""
    detail: str = Field(..., description="Error message")

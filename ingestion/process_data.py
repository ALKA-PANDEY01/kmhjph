"""
Process and clean Elexon data.
"""

import pandas as pd
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def parse_fuelhh(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Parse FUELHH records into a clean DataFrame.
    
    Expected fields:
    - startTime: ISO 8601 timestamp (UTC)
    - generation: Numeric (MW)
    - settlementDate: YYYY-MM-DD
    - settlementPeriod: 1-48
    """
    df = pd.DataFrame(records)
    
    # Parse timestamps
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    
    # Keep only needed columns
    df = df[["startTime", "generation"]].copy()
    df.rename(columns={"generation": "actual_generation"}, inplace=True)
    
    # Sort by time
    df.sort_values("startTime", inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    logger.info(f"Parsed {len(df)} FUELHH records")
    logger.info(f"Time range: {df['startTime'].min()} to {df['startTime'].max()}")
    
    return df


def parse_windfor(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Parse WINDFOR records into a clean DataFrame.
    
    Expected fields:
    - startTime: ISO 8601 timestamp (target delivery time, UTC)
    - publishTime: ISO 8601 timestamp (when forecast was issued, UTC)
    - generation: Numeric (MW)
    """
    df = pd.DataFrame(records)
    
    # Parse timestamps
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    
    # Keep only needed columns
    df = df[["startTime", "publishTime", "generation"]].copy()
    df.rename(columns={"generation": "forecast_generation"}, inplace=True)
    
    # Sort by target time, then publish time
    df.sort_values(["startTime", "publishTime"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    logger.info(f"Parsed {len(df)} WINDFOR records")
    logger.info(f"Target time range: {df['startTime'].min()} to {df['startTime'].max()}")
    logger.info(f"Publish time range: {df['publishTime'].min()} to {df['publishTime'].max()}")
    
    return df


def compute_decision_cutoff(delivery_time: pd.Timestamp, cutoff_hour: int = 9) -> pd.Timestamp:
    """
    Compute the decision cutoff time for a given delivery time.
    
    Rule: Decision cutoff is at cutoff_hour (09:00) London time on D-1.
    
    Args:
        delivery_time: Target delivery timestamp (UTC)
        cutoff_hour: Hour of day for cutoff (default: 9)
    
    Returns:
        Decision cutoff timestamp (UTC)
    """
    london_tz = pytz.timezone("Europe/London")
    
    # Convert delivery time to London timezone
    delivery_london = delivery_time.tz_convert(london_tz)
    
    # Decision is made on D-1 at cutoff_hour
    decision_date = delivery_london.date() - timedelta(days=1)
    decision_time_london = london_tz.localize(
        datetime.combine(decision_date, datetime.min.time().replace(hour=cutoff_hour))
    )
    
    # Convert back to UTC
    decision_time_utc = decision_time_london.astimezone(pytz.UTC)
    
    return decision_time_utc


def select_forecasts(
    forecasts_df: pd.DataFrame,
    cutoff_hour: int = 9
) -> pd.DataFrame:
    """
    Select the latest forecast per target time that was published before the decision cutoff.
    
    Logic:
    1. For each unique startTime (target delivery half-hour):
       - Compute decision cutoff (09:00 London on D-1)
       - Filter forecasts where publishTime <= cutoff
       - Select the forecast with the latest publishTime
    
    Args:
        forecasts_df: DataFrame with columns [startTime, publishTime, forecast_generation]
        cutoff_hour: Hour of day for decision cutoff (default: 9)
    
    Returns:
        DataFrame with one forecast per startTime
    """
    logger.info("Selecting forecasts per decision cutoff...")
    
    # Compute decision cutoff for each target time
    forecasts_df["decision_cutoff"] = forecasts_df["startTime"].apply(
        lambda t: compute_decision_cutoff(t, cutoff_hour)
    )
    
    # Filter: keep only forecasts published before cutoff
    before_cutoff = forecasts_df[forecasts_df["publishTime"] <= forecasts_df["decision_cutoff"]].copy()
    
    logger.info(f"Forecasts before cutoff: {len(before_cutoff)} / {len(forecasts_df)}")
    
    # For each startTime, keep the forecast with the latest publishTime
    selected = before_cutoff.sort_values("publishTime").groupby("startTime").tail(1)
    
    # Drop the temporary decision_cutoff column but keep all original columns
    selected = selected.drop(columns=['decision_cutoff']).copy()
    selected.reset_index(drop=True, inplace=True)
    
    logger.info(f"Selected {len(selected)} forecasts (one per target time)")
    
    return selected


def join_actuals_and_forecasts(
    actuals_df: pd.DataFrame,
    forecasts_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Join actuals and forecasts on startTime.
    
    Args:
        actuals_df: DataFrame with [startTime, actual_generation]
        forecasts_df: DataFrame with [startTime, publishTime, forecast_generation]
    
    Returns:
        DataFrame with [startTime, publishTime, forecast_generation, actual_generation]
    """
    logger.info("Joining actuals and forecasts...")
    
    merged = pd.merge(
        forecasts_df,
        actuals_df,
        on="startTime",
        how="inner"  # Only keep times with both forecast and actual
    )
    
    logger.info(f"Joined {len(merged)} records")
    
    # Check for missing data
    missing_forecasts = len(actuals_df) - len(merged)
    if missing_forecasts > 0:
        logger.warning(f"{missing_forecasts} actuals have no matching forecast")
    
    return merged


def compute_errors(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute forecast errors.
    
    Error = Forecast - Actual
    
    Args:
        df: DataFrame with [forecast_generation, actual_generation]
    
    Returns:
        DataFrame with added columns: error, absolute_error, squared_error, absolute_percentage_error
    """
    logger.info("Computing errors...")
    
    df = df.copy()
    
    # Error = Forecast - Actual
    df["error"] = df["forecast_generation"] - df["actual_generation"]
    
    # Absolute error
    df["absolute_error"] = df["error"].abs()
    
    # Squared error
    df["squared_error"] = df["error"] ** 2
    
    # Absolute percentage error (APE)
    # Handle division by zero: if actual is 0, set APE to None
    df["absolute_percentage_error"] = (
        df["absolute_error"] / df["actual_generation"].replace(0, pd.NA) * 100
    )
    
    logger.info(f"Error statistics:")
    logger.info(f"  Mean Error (ME): {df['error'].mean():.2f} MW")
    logger.info(f"  Mean Absolute Error (MAE): {df['absolute_error'].mean():.2f} MW")
    logger.info(f"  Root Mean Squared Error (RMSE): {(df['squared_error'].mean() ** 0.5):.2f} MW")
    logger.info(f"  Mean Absolute Percentage Error (MAPE): {df['absolute_percentage_error'].mean():.2f}%")
    
    return df

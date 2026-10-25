#!/usr/bin/env python3
"""
Main ingestion script.

Fetches Elexon BMRS data, processes it, and saves to Parquet.

Usage:
    python ingest.py
"""

import logging
import sys
from pathlib import Path

import pandas as pd

from config import (
    DELIVERY_START_DATE,
    DELIVERY_END_DATE,
    FORECAST_PUBLISH_START,
    FORECAST_PUBLISH_END,
    OUTPUT_PARQUET_PATH,
    REQUEST_TIMEOUT,
    DECISION_CUTOFF_HOUR
)
from fetch_elexon import ElexonClient
from process_data import (
    parse_fuelhh,
    parse_windfor,
    select_forecasts,
    join_actuals_and_forecasts,
    compute_errors
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Main ingestion workflow."""
    
    logger.info("=" * 60)
    logger.info("Starting Elexon BMRS data ingestion")
    logger.info("=" * 60)
    
    # Initialize client
    client = ElexonClient(timeout=REQUEST_TIMEOUT)
    
    try:
        # Step 1: Fetch actuals (FUELHH)
        logger.info("\n[Step 1/5] Fetching actuals (FUELHH)...")
        actuals_raw = client.fetch_fuelhh(
            settlement_date_from=DELIVERY_START_DATE,
            settlement_date_to=DELIVERY_END_DATE,
            fuel_type="WIND"
        )
        actuals_df = parse_fuelhh(actuals_raw)
        
        # Step 2: Fetch forecasts (WINDFOR)
        logger.info("\n[Step 2/5] Fetching forecasts (WINDFOR)...")
        forecasts_raw = client.fetch_windfor(
            publish_datetime_from=FORECAST_PUBLISH_START,
            publish_datetime_to=FORECAST_PUBLISH_END
        )
        forecasts_df = parse_windfor(forecasts_raw)
        
        # Step 3: Select forecasts per decision cutoff
        logger.info("\n[Step 3/5] Selecting forecasts per decision cutoff...")
        selected_forecasts_df = select_forecasts(
            forecasts_df,
            cutoff_hour=DECISION_CUTOFF_HOUR
        )
        
        # Step 4: Join actuals and forecasts
        logger.info("\n[Step 4/5] Joining actuals and forecasts...")
        joined_df = join_actuals_and_forecasts(actuals_df, selected_forecasts_df)
        
        # Step 5: Compute errors
        logger.info("\n[Step 5/5] Computing errors...")
        final_df = compute_errors(joined_df)
        
        # Reorder columns for clarity
        final_df = final_df[[
            "startTime",
            "publishTime",
            "forecast_generation",
            "actual_generation",
            "error",
            "absolute_error",
            "squared_error",
            "absolute_percentage_error"
        ]]
        
        # Save to Parquet
        output_path = Path(OUTPUT_PARQUET_PATH)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        final_df.to_parquet(output_path, index=False, engine="pyarrow")
        logger.info(f"\n✓ Saved {len(final_df)} records to {output_path}")
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("INGESTION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Records: {len(final_df)}")
        logger.info(f"Time range: {final_df['startTime'].min()} to {final_df['startTime'].max()}")
        logger.info(f"Output: {output_path.as_posix()}")
        
        # Display sample
        logger.info("\nSample data (first 5 rows):")
        print(final_df.head().to_string(index=False))
        
    except Exception as e:
        logger.error(f"\n✗ Ingestion failed: {e}", exc_info=True)
        sys.exit(1)
    
    finally:
        client.close()


if __name__ == "__main__":
    main()

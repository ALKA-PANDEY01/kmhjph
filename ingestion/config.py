"""
Configuration for Elexon BMRS data ingestion.
"""

from datetime import datetime
import pytz

# Elexon BMRS API endpoints
FUELHH_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream"
WINDFOR_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream"

# Data scope: decisions made in January 2026 (for deliveries 2 Jan - 1 Feb 2026)
DELIVERY_START_DATE = "2026-01-02"  # First delivery day
DELIVERY_END_DATE = "2026-02-01"    # Last delivery day (inclusive)

# Decision cutoff: 09:00 Europe/London on D-1
# In January, London is in GMT (UTC+0)
DECISION_CUTOFF_HOUR = 9  # 09:00 local time
DECISION_CUTOFF_TIMEZONE = "Europe/London"

# Forecast query range: need forecasts published before the latest decision cutoff
# Decision for 2 Jan is made on 1 Jan at 09:00
# Decision for 1 Feb is made on 31 Jan at 09:00
# Fetch forecasts published throughout December 2025 and January 2026
# Use ISO 8601 format with Z for UTC
FORECAST_PUBLISH_START = "2025-12-01T00:00:00Z"  # Start of December (captures forecasts for early January)
FORECAST_PUBLISH_END = "2026-02-01T12:00:00Z"    # After last decision cutoff (31 Jan 09:00)

# Output
OUTPUT_PARQUET_PATH = "data/wind_forecast_accuracy.parquet"

# API request timeout (seconds)
REQUEST_TIMEOUT = 60

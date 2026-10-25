"""
Fetch data from Elexon BMRS API.
"""

import requests
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ElexonClient:
    """Client for Elexon BMRS Insights API."""
    
    def __init__(self, timeout: int = 60):
        self.timeout = timeout
        self.session = requests.Session()
        # API is public, no authentication needed
    
    def fetch_fuelhh(
        self,
        settlement_date_from: str,
        settlement_date_to: str,
        fuel_type: str = "WIND"
    ) -> List[Dict[str, Any]]:
        """
        Fetch FUELHH (actual generation) data.
        
        Args:
            settlement_date_from: Start date (YYYY-MM-DD)
            settlement_date_to: End date (YYYY-MM-DD)
            fuel_type: Fuel type filter (default: WIND)
        
        Returns:
            List of records with fields: startTime, generation, settlementDate, etc.
        """
        url = "https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream"
        params = {
            "settlementDateFrom": settlement_date_from,
            "settlementDateTo": settlement_date_to,
            "fuelType": fuel_type
        }
        
        logger.info(f"Fetching FUELHH: {settlement_date_from} to {settlement_date_to}, fuel={fuel_type}")
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Received {len(data)} FUELHH records")
            return data
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch FUELHH: {e}")
            raise
    
    def fetch_windfor(
        self,
        publish_datetime_from: str,
        publish_datetime_to: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch WINDFOR (wind forecast) data using publish time filters.
        
        Note: WINDFOR historical data requires publishDateTime filters (not settlementDate).
        The API returns forecasts that were published in the specified time window.
        
        Args:
            publish_datetime_from: Start of publish time window (ISO 8601 with Z, e.g. 2026-01-01T00:00:00Z)
            publish_datetime_to: End of publish time window (ISO 8601 with Z)
        
        Returns:
            List of records with fields: startTime, publishTime, generation
        """
        url = "https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream"
        params = {
            "publishDateTimeFrom": publish_datetime_from,
            "publishDateTimeTo": publish_datetime_to
        }
        
        logger.info(f"Fetching WINDFOR: publishTime {publish_datetime_from} to {publish_datetime_to}")
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Received {len(data)} WINDFOR records")
            return data
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch WINDFOR: {e}")
            raise
    
    def close(self):
        """Close the session."""
        self.session.close()

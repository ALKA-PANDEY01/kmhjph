"""
API endpoint tests using TestClient.
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app


@pytest.fixture(scope="module")
def client():
    """Create test client with startup/shutdown events."""
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data['status'] == 'healthy'
    assert 'timestamp' in data
    assert data['records_loaded'] > 0


def test_config_endpoint(client):
    """Test configuration endpoint."""
    response = client.get("/api/config")
    assert response.status_code == 200
    
    data = response.json()
    assert data['decision_cutoff_hour'] == 9
    assert data['decision_cutoff_timezone'] == 'Europe/London'
    assert 'data_range' in data
    assert 'start' in data['data_range']
    assert 'end' in data['data_range']
    assert data['total_records'] > 0


def test_forecast_day_valid(client):
    """Test forecast endpoint with valid date."""
    response = client.get("/api/forecast?date=2026-01-15")
    assert response.status_code == 200
    
    data = response.json()
    assert data['delivery_date'] == '2026-01-15'
    assert 'decision_cutoff' in data
    assert '2026-01-14' in data['decision_cutoff']  # Decision on D-1
    assert '09:00:00' in data['decision_cutoff']  # At 09:00
    assert len(data['data_points']) > 0
    assert data['available_count'] > 0
    
    # Check structure of first data point
    point = data['data_points'][0]
    assert 'startTime' in point
    assert 'publishTime' in point
    assert 'forecast' in point
    assert 'actual' in point
    assert 'error' in point


def test_forecast_day_invalid_date_format(client):
    """Test forecast endpoint with invalid date format."""
    response = client.get("/api/forecast?date=invalid")
    assert response.status_code == 422  # Validation error


def test_forecast_day_out_of_range(client):
    """Test forecast endpoint with date out of range."""
    response = client.get("/api/forecast?date=2025-01-01")
    assert response.status_code == 400
    assert 'out of range' in response.json()['detail'].lower()


def test_comparison_valid_range(client):
    """Test comparison endpoint with valid date range."""
    response = client.get("/api/comparison?start=2026-01-10&end=2026-01-12")
    assert response.status_code == 200
    
    data = response.json()
    assert data['start_date'] == '2026-01-10'
    assert data['end_date'] == '2026-01-12'
    assert data['count'] > 0
    assert len(data['data']) > 0


def test_metrics_full_range(client):
    """Test metrics endpoint without filters (full dataset)."""
    response = client.get("/api/metrics")
    assert response.status_code == 200
    
    data = response.json()
    assert data['record_count'] > 0
    assert 'date_range' in data
    assert data['mae'] > 0
    assert data['rmse'] > 0


def test_errors_by_hour_full_range(client):
    """Test errors by hour endpoint without filters."""
    response = client.get("/api/errors/by-hour")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data['data']) == 24  # 24 hours


def test_error_distribution_full_range(client):
    """Test error distribution endpoint without filters."""
    response = client.get("/api/errors/distribution")
    assert response.status_code == 200
    
    data = response.json()
    assert data['total_count'] > 0
    assert len(data['bins']) > 0

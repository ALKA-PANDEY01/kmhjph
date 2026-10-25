"""
Tests for forecast selection logic from the ingestion pipeline.

Tests the decision cutoff calculation and forecast selection,
including DST transitions.
"""

import pytest
import pandas as pd
import pytz
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add ingestion module to path
ingestion_path = Path(__file__).parent.parent.parent / 'ingestion'
sys.path.insert(0, str(ingestion_path))

from process_data import compute_decision_cutoff, select_forecasts


def test_compute_decision_cutoff_standard_time():
    """
    Test decision cutoff calculation in January (GMT, no DST).
    
    For delivery on 2026-01-15 12:00 UTC:
    - D-1 = 2026-01-14
    - 09:00 London = 09:00 GMT = 09:00 UTC (no offset in January)
    - Cutoff = 2026-01-14 09:00:00 UTC
    """
    delivery_time = pd.Timestamp('2026-01-15 12:00:00', tz='UTC')
    cutoff = compute_decision_cutoff(delivery_time, cutoff_hour=9)
    
    expected = pd.Timestamp('2026-01-14 09:00:00', tz='UTC')
    assert cutoff == expected


def test_compute_decision_cutoff_dst_summer():
    """
    Test decision cutoff calculation in July (BST, UTC+1).
    
    For delivery on 2026-07-15 12:00 UTC:
    - D-1 = 2026-07-14
    - 09:00 London BST = 09:00 UTC+1 = 08:00 UTC
    - Cutoff = 2026-07-14 08:00:00 UTC
    """
    delivery_time = pd.Timestamp('2026-07-15 12:00:00', tz='UTC')
    cutoff = compute_decision_cutoff(delivery_time, cutoff_hour=9)
    
    expected = pd.Timestamp('2026-07-14 08:00:00', tz='UTC')
    assert cutoff == expected


def test_compute_decision_cutoff_dst_transition_spring():
    """
    Test decision cutoff during spring DST transition (last Sunday in March).
    
    In 2026, clocks go forward on March 29 at 01:00 GMT → 02:00 BST.
    
    For delivery on 2026-03-30 12:00 UTC (day after DST starts):
    - D-1 = 2026-03-29 (DST transition day)
    - 09:00 London BST = 08:00 UTC
    - Cutoff = 2026-03-29 08:00:00 UTC
    """
    delivery_time = pd.Timestamp('2026-03-30 12:00:00', tz='UTC')
    cutoff = compute_decision_cutoff(delivery_time, cutoff_hour=9)
    
    # After DST starts, 09:00 London = 08:00 UTC
    expected = pd.Timestamp('2026-03-29 08:00:00', tz='UTC')
    assert cutoff == expected


def test_compute_decision_cutoff_dst_transition_autumn():
    """
    Test decision cutoff during autumn DST transition (last Sunday in October).
    
    In 2026, clocks go back on October 25 at 02:00 BST → 01:00 GMT.
    
    For delivery on 2026-10-26 12:00 UTC (day after DST ends):
    - D-1 = 2026-10-25 (DST transition day)
    - 09:00 London GMT = 09:00 UTC
    - Cutoff = 2026-10-25 09:00:00 UTC
    """
    delivery_time = pd.Timestamp('2026-10-26 12:00:00', tz='UTC')
    cutoff = compute_decision_cutoff(delivery_time, cutoff_hour=9)
    
    # After DST ends, 09:00 London = 09:00 UTC
    expected = pd.Timestamp('2026-10-25 09:00:00', tz='UTC')
    assert cutoff == expected


def test_select_forecast_just_before_cutoff():
    """
    Test forecast selection when publish time is just before cutoff.
    
    Target: 2026-01-15 12:00 UTC
    Cutoff: 2026-01-14 09:00:00 UTC
    
    Forecasts:
    - 07:00 → should be included
    - 08:59 → should be included and selected (latest before cutoff)
    - 09:00 → should be included (exactly at cutoff)
    - 09:01 → should be excluded (after cutoff)
    """
    forecasts = pd.DataFrame({
        'startTime': pd.to_datetime([
            '2026-01-15 12:00:00',
            '2026-01-15 12:00:00',
            '2026-01-15 12:00:00',
            '2026-01-15 12:00:00',
        ], utc=True),
        'publishTime': pd.to_datetime([
            '2026-01-14 07:00:00',
            '2026-01-14 08:59:00',
            '2026-01-14 09:00:00',  # Exactly at cutoff
            '2026-01-14 09:01:00',
        ], utc=True),
        'forecast_generation': [1000.0, 1100.0, 1200.0, 1300.0]
    })
    
    selected = select_forecasts(forecasts, cutoff_hour=9)
    
    # Should select exactly 1 forecast
    assert len(selected) == 1
    
    # Should select the one at 09:00 (latest publishTime <= cutoff)
    assert selected.iloc[0]['publishTime'] == pd.Timestamp('2026-01-14 09:00:00', tz='UTC')
    assert selected.iloc[0]['forecast_generation'] == 1200.0


def test_select_forecast_just_after_cutoff():
    """
    Test that forecast published just after cutoff is not selected.
    
    Target: 2026-01-15 12:00 UTC
    Cutoff: 2026-01-14 09:00:00 UTC
    
    Forecasts:
    - 08:59 → should be selected
    - 09:01 → should NOT be selected
    """
    forecasts = pd.DataFrame({
        'startTime': pd.to_datetime([
            '2026-01-15 12:00:00',
            '2026-01-15 12:00:00',
        ], utc=True),
        'publishTime': pd.to_datetime([
            '2026-01-14 08:59:00',
            '2026-01-14 09:01:00',
        ], utc=True),
        'forecast_generation': [1100.0, 1300.0]
    })
    
    selected = select_forecasts(forecasts, cutoff_hour=9)
    
    # Should select exactly 1 forecast (the one at 08:59)
    assert len(selected) == 1
    assert selected.iloc[0]['publishTime'] == pd.Timestamp('2026-01-14 08:59:00', tz='UTC')


def test_select_forecast_no_forecast_before_cutoff():
    """
    Test behavior when no forecast is published before cutoff.
    
    Target: 2026-01-15 12:00 UTC
    Cutoff: 2026-01-14 09:00:00 UTC
    
    All forecasts published after cutoff → no forecast selected.
    """
    forecasts = pd.DataFrame({
        'startTime': pd.to_datetime([
            '2026-01-15 12:00:00',
            '2026-01-15 12:00:00',
        ], utc=True),
        'publishTime': pd.to_datetime([
            '2026-01-14 10:00:00',
            '2026-01-14 11:00:00',
        ], utc=True),
        'forecast_generation': [1100.0, 1200.0]
    })
    
    selected = select_forecasts(forecasts, cutoff_hour=9)
    
    # Should return empty DataFrame
    assert len(selected) == 0


def test_select_forecast_multiple_targets():
    """
    Test forecast selection with multiple target times.
    
    Should select latest forecast before cutoff for each target time.
    """
    forecasts = pd.DataFrame({
        'startTime': pd.to_datetime([
            # Target 1: 2026-01-15 12:00
            '2026-01-15 12:00:00',
            '2026-01-15 12:00:00',
            '2026-01-15 12:00:00',
            # Target 2: 2026-01-16 12:00
            '2026-01-16 12:00:00',
            '2026-01-16 12:00:00',
        ], utc=True),
        'publishTime': pd.to_datetime([
            # Target 1 forecasts
            '2026-01-14 07:00:00',
            '2026-01-14 08:00:00',  # Should select this for target 1
            '2026-01-14 10:00:00',  # After cutoff for target 1
            # Target 2 forecasts
            '2026-01-15 08:00:00',  # Should select this for target 2
            '2026-01-15 10:00:00',  # After cutoff for target 2
        ], utc=True),
        'forecast_generation': [1000.0, 1100.0, 1200.0, 2000.0, 2100.0]
    })
    
    selected = select_forecasts(forecasts, cutoff_hour=9)
    
    # Should select 2 forecasts (one per target time)
    assert len(selected) == 2
    
    # Check target 1 selection
    target1 = selected[selected['startTime'] == pd.Timestamp('2026-01-15 12:00:00', tz='UTC')]
    assert len(target1) == 1
    assert target1.iloc[0]['publishTime'] == pd.Timestamp('2026-01-14 08:00:00', tz='UTC')
    
    # Check target 2 selection
    target2 = selected[selected['startTime'] == pd.Timestamp('2026-01-16 12:00:00', tz='UTC')]
    assert len(target2) == 1
    assert target2.iloc[0]['publishTime'] == pd.Timestamp('2026-01-15 08:00:00', tz='UTC')


def test_select_forecast_edge_case_midnight_delivery():
    """
    Test decision cutoff for delivery at midnight.
    
    For delivery on 2026-01-15 00:00 UTC (midnight):
    - D-1 = 2026-01-14
    - Cutoff = 2026-01-14 09:00:00 UTC
    """
    delivery_time = pd.Timestamp('2026-01-15 00:00:00', tz='UTC')
    cutoff = compute_decision_cutoff(delivery_time, cutoff_hour=9)
    
    expected = pd.Timestamp('2026-01-14 09:00:00', tz='UTC')
    assert cutoff == expected


def test_select_forecast_custom_cutoff_hour():
    """
    Test using a different cutoff hour (e.g., 10:00 instead of 09:00).
    """
    delivery_time = pd.Timestamp('2026-01-15 12:00:00', tz='UTC')
    cutoff = compute_decision_cutoff(delivery_time, cutoff_hour=10)
    
    expected = pd.Timestamp('2026-01-14 10:00:00', tz='UTC')
    assert cutoff == expected


def test_select_forecast_preserves_all_columns():
    """
    Test that forecast selection preserves all DataFrame columns.
    """
    forecasts = pd.DataFrame({
        'startTime': pd.to_datetime(['2026-01-15 12:00:00'], utc=True),
        'publishTime': pd.to_datetime(['2026-01-14 08:00:00'], utc=True),
        'forecast_generation': [1100.0],
        'extra_column': ['test_value']
    })
    
    selected = select_forecasts(forecasts, cutoff_hour=9)
    
    # Should preserve all columns
    assert 'extra_column' in selected.columns
    assert selected.iloc[0]['extra_column'] == 'test_value'

"""Test that no forecast publishTime is after its decision cutoff"""
import pytest
import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'ingestion'))

from process_data import compute_decision_cutoff


def test_no_cutoff_violations():
    """Verify that all selected forecasts have publishTime <= cutoff"""
    # Load the final parquet file
    parquet_path = Path(__file__).parent.parent.parent / 'ingestion' / 'data' / 'wind_forecast_accuracy.parquet'
    df = pd.read_parquet(parquet_path)
    
    violations = []
    
    for idx, row in df.iterrows():
        target_time = row['startTime']
        publish_time = row['publishTime']
        
        # Compute the cutoff for this target time
        cutoff = compute_decision_cutoff(target_time)
        
        # Check if publishTime is after cutoff
        if publish_time > cutoff:
            violations.append({
                'startTime': target_time,
                'publishTime': publish_time,
                'cutoff': cutoff,
                'violation_hours': (publish_time - cutoff).total_seconds() / 3600
            })
    
    # Print violations if any
    if violations:
        print(f"\n⚠️  Found {len(violations)} cutoff violations:")
        for v in violations[:10]:  # Show first 10
            print(f"  Target: {v['startTime']}, Publish: {v['publishTime']}, Cutoff: {v['cutoff']}")
            print(f"    Violation: {v['violation_hours']:.2f} hours after cutoff")
    else:
        print(f"\n✓ No cutoff violations found across {len(df)} records")
    
    # Assert no violations
    assert len(violations) == 0, f"Found {len(violations)} forecasts with publishTime > cutoff"


def test_specific_case_2026_01_15_12():
    """Test the specific case mentioned: 2026-01-15 12:00 UTC"""
    parquet_path = Path(__file__).parent.parent.parent / 'ingestion' / 'data' / 'wind_forecast_accuracy.parquet'
    df = pd.read_parquet(parquet_path)
    
    target = pd.Timestamp('2026-01-15 12:00:00', tz='UTC')
    row = df[df['startTime'] == target]
    
    assert len(row) == 1, f"Expected 1 row for {target}, got {len(row)}"
    
    r = row.iloc[0]
    cutoff = compute_decision_cutoff(target)
    
    print(f"\nTarget: {target}")
    print(f"Cutoff: {cutoff}")
    print(f"Selected publishTime: {r['publishTime']}")
    print(f"Is publishTime <= cutoff? {r['publishTime'] <= cutoff}")
    
    assert r['publishTime'] <= cutoff, \
        f"publishTime {r['publishTime']} is after cutoff {cutoff}"

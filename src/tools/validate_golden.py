#!/usr/bin/env python3
"""
Golden file validation script for change detection.

Compares detector output against expected fixtures to ensure
consistent behavior across versions.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.detector import detect_changes
from src.models import Snapshot


def load_snapshot(filepath: Path) -> Snapshot:
    """Load a snapshot from JSON file."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    return Snapshot(
        account_id=data.get('account_id', 'test_account'),
        case_id=data.get('case_id', 'TEST_CASE'),
        endpoint_type=data.get('endpoint_type', 'case_data'),
        raw_json=data.get('raw_json', {}),
        parsed_data=data.get('parsed_data', {}),
        timestamp=data.get('timestamp')
    )


def load_changes(filepath: Path) -> List[Dict]:
    """Load expected changes from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def compare_changes(actual: List[Dict], expected: List[Dict]) -> bool:
    """Compare two lists of changes, ignoring order."""
    if len(actual) != len(expected):
        return False
    
    # Sort by type and description for consistent comparison
    actual_sorted = sorted(actual, key=lambda x: (x.get('type', ''), x.get('description', '')))
    expected_sorted = sorted(expected, key=lambda x: (x.get('type', ''), x.get('description', '')))
    
    return actual_sorted == expected_sorted


def validate_golden_files(golden_dir: Path) -> bool:
    """Validate all golden file pairs in the directory."""
    success = True
    
    # Group files by test name and snapshot number
    file_groups = {}
    
    # Process all files in the golden directory
    for file_path in golden_dir.glob("*.json"):
        # Parse filename: testname_snapshot_#.json or testname_expected_changes_#.json
        stem = file_path.stem
        if '_snapshot_' in stem:
            # Snapshot file
            parts = stem.split('_snapshot_')
            if len(parts) == 2:
                test_name = parts[0]
                snapshot_num = parts[1]
                if test_name not in file_groups:
                    file_groups[test_name] = {}
                file_groups[test_name][f'snapshot_{snapshot_num}'] = file_path
        elif '_expected_changes_' in stem:
            # Expected changes file
            parts = stem.split('_expected_changes_')
            if len(parts) == 2:
                test_name = parts[0]
                snapshot_num = parts[1]
                if test_name not in file_groups:
                    file_groups[test_name] = {}
                file_groups[test_name][f'expected_{snapshot_num}'] = file_path
    
    # Validate each test group
    for test_name, files in file_groups.items():
        # We need at least two snapshots and their expected changes
        snapshot_nums = []
        for key in files.keys():
            if key.startswith('snapshot_'):
                snapshot_nums.append(int(key.split('_')[1]))  # Convert to int for sorting
        
        # For each pair of consecutive snapshots
        snapshot_nums.sort()
        for i in range(len(snapshot_nums) - 1):
            old_snapshot_num = snapshot_nums[i]
            new_snapshot_num = snapshot_nums[i + 1]
            
            old_snapshot_file = files.get(f'snapshot_{old_snapshot_num}')
            new_snapshot_file = files.get(f'snapshot_{new_snapshot_num}')
            expected_file = files.get(f'expected_{old_snapshot_num}')  # Expect changes from old_snapshot_num to new_snapshot_num
            
            if not all([old_snapshot_file, new_snapshot_file, expected_file]):
                print(f"⚠️  Incomplete golden file set for {test_name} transition {old_snapshot_num}→{new_snapshot_num}")
                continue
            
            try:
                # Load snapshots
                old_snapshot = load_snapshot(old_snapshot_file)
                new_snapshot = load_snapshot(new_snapshot_file)
                
                # Detect changes
                changes = detect_changes(old_snapshot, new_snapshot)
                actual_changes = [change.to_dict() for change in changes]
                
                # Load expected changes
                expected_changes = load_changes(expected_file)
                
                # Compare
                if compare_changes(actual_changes, expected_changes):
                    print(f"✅ {test_name}: {old_snapshot_num}→{new_snapshot_num}")
                else:
                    print(f"❌ {test_name}: {old_snapshot_num}→{new_snapshot_num} - MISMATCH")
                    print(f"   Expected: {expected_changes}")
                    print(f"   Actual:   {actual_changes}")
                    success = False
                    
            except Exception as e:
                print(f"💥 {test_name}: {old_snapshot_num}→{new_snapshot_num} - ERROR: {e}")
                success = False
    
    return success


def main():
    """Main validation function."""
    golden_dir = Path(__file__).parent.parent.parent / 'tests' / 'planner' / 'golden'
    
    if not golden_dir.exists():
        print(f"📁 Creating golden directory: {golden_dir}")
        golden_dir.mkdir(parents=True, exist_ok=True)
        print("ℹ️  Add golden test fixtures to begin validation")
        return 0
    
    print(f"🔍 Validating golden files in: {golden_dir}")
    
    if validate_golden_files(golden_dir):
        print("🎉 All golden file validations passed!")
        return 0
    else:
        print("💥 Some golden file validations failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
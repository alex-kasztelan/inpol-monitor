import pytest
from src.detector import Detector
from src.models import Snapshot
from datetime import datetime

def make_snapshot(data):
    return Snapshot(
        account_id="test",
        case_id="test",
        endpoint_type="case_data",
        raw_json=data,
        parsed_data=data,
        timestamp=datetime.utcnow()
    )

def test_no_changes_when_identical():
    """Test that identical snapshots yield no changes."""
    data = {
        "status": "4",
        "decisionDate": "2026-04-27T00:00:00Z",
        "editDate": "2026-03-23T12:07:21.6910163Z",
        "updatedAt": "2026-03-23T12:07:21.6910163Z",
        "relatedDocs": [],
        "timelineEvents": []
    }
    old_snapshot = make_snapshot(data)
    new_snapshot = make_snapshot(data)

    detector = Detector(None)
    changes = detector.detect_changes(old_snapshot, new_snapshot)
    assert len(changes) == 0

def test_first_check_no_previous():
    """Test that with previous snapshot None, no changes are detected."""
    data = {
        "status": "4",
        "decisionDate": "2026-04-27T00:00:00Z",
        "editDate": "2026-03-23T12:07:21.6910163Z",
        "updatedAt": "2026-03-23T12:07:21.6910163Z",
        "relatedDocs": [],
        "timelineEvents": []
    }
    new_snapshot = make_snapshot(data)

    detector = Detector(None)
    changes = detector.detect_changes(None, new_snapshot)
    assert len(changes) == 0

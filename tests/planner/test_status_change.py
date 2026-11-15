"""Test status change detection."""
import json
import pytest
from src.detector import Detector, ChangeType
from src.models import Snapshot
from datetime import datetime


@pytest.fixture
def sample_case_data():
    """Load sample case JSON from file."""
    with open('sampleCase.json') as f:
        return json.load(f)


def make_snapshot(data, account_id="test"):
    """Create a Snapshot from case data dict."""
    return Snapshot(
        account_id=account_id,
        case_id=data.get("signature", "test"),
        endpoint_type="case_data",
        raw_json=data,
        parsed_data={
            "status_raw": data.get("status"),
            "decision_date": data.get("decisionDate"),
            "submit_date": data.get("submitDate"),
            "updated_at": data.get("updatedAt", ""),
            "relatedDocs": data.get("relatedDocs", []),
            "timelineEvents": data.get("timelineEvents", [])
        },
        timestamp=datetime.utcnow()
    )


def test_status_change_from_1_to_5(sample_case_data):
    """Test detection of status code change."""
    old_data = sample_case_data.copy()
    old_data["status"] = "1"
    old_snapshot = make_snapshot(old_data)

    new_data = sample_case_data.copy()
    new_data["status"] = "5"
    new_snapshot = make_snapshot(new_data)

    detector = Detector(None)
    changes = detector.detect_changes(old_snapshot, new_snapshot)

    status_changes = [c for c in changes if c.type == ChangeType.STATUS]
    assert len(status_changes) == 1
    change = status_changes[0]
    assert change.old_value == "1"
    assert change.new_value == "5"
    assert "Status changed from '1 (New)' to '5 (In progress)'" in change.description

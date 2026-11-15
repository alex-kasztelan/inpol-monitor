import json
import pytest
from src.detector import Detector, ChangeType
from src.models import Snapshot
from datetime import datetime

@pytest.fixture
def sample_case_data():
    with open('sampleCase.json') as f:
        return json.load(f)

def make_snapshot(data):
    return Snapshot(
        account_id="test",
        case_id=data.get("signature", "test"),
        endpoint_type="case_data",
        raw_json=data,
        parsed_data={
            "status": data.get("status"),
            "decision_date": data.get("decisionDate"),
            "edit_date": data.get("editDate"),
            "updated_at": data.get("updatedAt", ""),
            "relatedDocs": data.get("relatedDocs", []),
            "timelineEvents": data.get("timelineEvents", [])
        },
        timestamp=datetime.utcnow()
    )

def test_new_timeline_event_detected(sample_case_data):
    """Test detection of a newly added timeline event."""
    base_events = sample_case_data.get("timelineEvents", [])
    if not base_events:
        pytest.skip("No timeline events in sample")

    old_data = sample_case_data.copy()
    old_data["timelineEvents"] = base_events[:-1]  # All except last

    new_data = sample_case_data.copy()
    # new_snapshot has full list; old_snapshot has all but last event

    old_snapshot = make_snapshot(old_data)
    new_snapshot = make_snapshot(new_data)

    detector = Detector(None)
    changes = detector.detect_changes(old_snapshot, new_snapshot)

    timeline_changes = [c for c in changes if c.type == ChangeType.TIMELINE_EVENT_ADDED]
    assert len(timeline_changes) == 1
    change = timeline_changes[0]
    assert change.old_value is None
    # The new_value should be a JSON string containing the added event
    event = json.loads(change.new_value)
    assert "eventType" in event
    assert "date" in event
    expected_event = new_data["timelineEvents"][-1]
    assert event["eventType"] == expected_event["eventType"]
    assert event["date"] == expected_event["date"]

def test_no_timeline_change_when_same(sample_case_data):
    """Test no timeline event change when both snapshots identical."""
    data = sample_case_data.copy()
    old_snapshot = make_snapshot(data)
    new_snapshot = make_snapshot(data)

    detector = Detector(None)
    changes = detector.detect_changes(old_snapshot, new_snapshot)
    timeline_changes = [c for c in changes if c.type == ChangeType.TIMELINE_EVENT_ADDED]
    assert len(timeline_changes) == 0

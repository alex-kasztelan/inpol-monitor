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
            "submit_date": data.get("submitDate") or data.get("creationDate"),
            "updated_at": data.get("updatedAt", ""),
            "relatedDocs": data.get("relatedDocs", []),
            "timelineEvents": data.get("timelineEvents", [])
        },
        timestamp=datetime.utcnow()
    )

def test_decision_date_change(sample_case_data):
    """Test detection of decisionDate change."""
    old_data = sample_case_data.copy()
    old_data["decisionDate"] = "2025-09-14T12:13:50.9742458Z"

    new_data = sample_case_data.copy()
    new_data["decisionDate"] = "2026-04-27T00:00:00Z"

    old_snap = make_snapshot(old_data)
    new_snap = make_snapshot(new_data)

    detector = Detector(None)
    changes = detector.detect_changes(old_snap, new_snap)

    dec_changes = [c for c in changes if c.type == ChangeType.DECISION_DATE_CHANGE]
    assert len(dec_changes) == 1
    change = dec_changes[0]
    assert change.old_value == old_data["decisionDate"]
    assert change.new_value == new_data["decisionDate"]

def test_submit_date_change(sample_case_data):
    """Test detection of creationDate change (submit date)."""
    old_data = dict(sample_case_data)
    old_data["creationDate"] = "2025-09-14T12:13:50.9893713Z"

    new_data = dict(sample_case_data)
    new_data["creationDate"] = "2026-04-14T12:13:50.9893713Z"

    old_snap = make_snapshot(old_data)
    new_snap = make_snapshot(new_data)

    detector = Detector(None)
    changes = detector.detect_changes(old_snap, new_snap)

    sub_changes = [c for c in changes if c.type == ChangeType.SUBMIT_DATE_CHANGE]
    assert len(sub_changes) == 1
    change = sub_changes[0]
    assert change.old_value == old_data["creationDate"]
    assert change.new_value == new_data["creationDate"]

def test_updated_at_change(sample_case_data):
    """Test detection of updated_at change."""
    old_data = sample_case_data.copy()
    old_data["updatedAt"] = "2026-03-23T12:07:21.6910163Z"

    new_data = sample_case_data.copy()
    new_data["updatedAt"] = "2026-04-27T10:15:00.0000Z"

    old_snap = make_snapshot(old_data)
    new_snap = make_snapshot(new_data)

    detector = Detector(None)
    changes = detector.detect_changes(old_snap, new_snap)

    upd_changes = [c for c in changes if c.type == ChangeType.UPDATED_AT_CHANGE]
    assert len(upd_changes) == 1
    change = upd_changes[0]
    assert change.old_value == old_data["updatedAt"]
    assert change.new_value == new_data["updatedAt"]

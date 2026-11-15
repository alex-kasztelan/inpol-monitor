"""Test document change detection using relatedDocs IDs."""
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


def make_snapshot(data):
    """Create a Snapshot from case data dict."""
    return Snapshot(
        account_id="test",
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


def test_new_document_added(sample_case_data):
    """Test detection of newly added documents in relatedDocs."""
    base_docs = sample_case_data.get("relatedDocs", [])

    # Old snapshot has empty docs
    old_data = sample_case_data.copy()
    old_data["relatedDocs"] = []
    old_snapshot = make_snapshot(old_data)

    # New snapshot has all docs
    new_data = sample_case_data.copy()
    new_snapshot = make_snapshot(new_data)

    detector = Detector(None)
    changes = detector.detect_changes(old_snapshot, new_snapshot)

    new_doc_changes = [c for c in changes if c.type == ChangeType.NEW_DOCUMENT]
    assert len(new_doc_changes) == len(base_docs)

    # Verify first document
    first_doc = base_docs[0]
    first_change = next(c for c in new_doc_changes if c.new_value == first_doc["id"])
    assert first_change.old_value is None
    assert first_doc["name"] in first_change.description


def test_document_removed(sample_case_data):
    """Test detection of removed document."""
    base_docs = sample_case_data.get("relatedDocs", [])
    if len(base_docs) < 1:
        pytest.skip("No documents to remove")

    # Old snapshot has all docs
    old_data = sample_case_data.copy()
    old_snapshot = make_snapshot(old_data)

    # New snapshot has one doc removed
    removed_doc = base_docs[0]
    new_data = sample_case_data.copy()
    new_data["relatedDocs"] = [d for d in base_docs if d["id"] != removed_doc["id"]]
    new_snapshot = make_snapshot(new_data)

    detector = Detector(None)
    changes = detector.detect_changes(old_snapshot, new_snapshot)

    removed_changes = [c for c in changes if c.type == ChangeType.REMOVED_DOCUMENT]
    assert len(removed_changes) == 1
    change = removed_changes[0]
    assert change.old_value == removed_doc["id"]
    assert change.new_value is None
    assert removed_doc["name"] in change.description


def test_simultaneous_document_changes(sample_case_data):
    """Test detection of both added and removed documents."""
    base_docs = sample_case_data.get("relatedDocs", [])
    if len(base_docs) < 2:
        pytest.skip("Need at least 2 documents for this test")

    # Old snapshot has all docs
    old_data = sample_case_data.copy()
    old_snapshot = make_snapshot(old_data)

    # New snapshot removes first doc
    removed_doc = base_docs[0]
    new_data = sample_case_data.copy()
    new_data["relatedDocs"] = [d for d in base_docs if d["id"] != removed_doc["id"]]
    new_snapshot = make_snapshot(new_data)

    detector = Detector(None)
    changes = detector.detect_changes(old_snapshot, new_snapshot)

    removed_changes = [c for c in changes if c.type == ChangeType.REMOVED_DOCUMENT]
    new_changes = [c for c in changes if c.type == ChangeType.NEW_DOCUMENT]

    assert len(removed_changes) == 1
    assert len(new_changes) == 0  # No new docs, only removal

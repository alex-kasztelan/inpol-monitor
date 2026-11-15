"""Tests for change detection module."""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from src.detector import (
    Change, ChangeType, Detector, StatusDetector,
    DocumentDetector, DateDetector, TimelineDetector, QuestionDetector,
    detect_changes, detect_all_changes
)
from src.models import Snapshot
from src.storage import SnapshotRepository


class TestChange:
    """Tests for Change model."""

    def test_create_change_status(self):
        """Test creating a status change."""
        change = Change(
            type=ChangeType.STATUS,
            old_value="In process",
            new_value="Accepted",
            description="Status changed: In process → Accepted"
        )
        assert change.type == ChangeType.STATUS
        assert change.old_value == "In process"
        assert change.new_value == "Accepted"
        assert "In process" in change.description
        assert "Accepted" in change.description

    def test_create_change_new_document(self):
        """Test creating a new document change."""
        change = Change(
            type=ChangeType.NEW_DOCUMENT,
            old_value=None,
            new_value="certification.pdf",
            description="New document added: certification.pdf"
        )
        assert change.type == ChangeType.NEW_DOCUMENT
        assert change.old_value is None
        assert change.new_value == "certification.pdf"

    def test_create_change_decision_date(self):
        """Test creating a decision date change."""
        change = Change(
            type=ChangeType.DECISION_DATE_CHANGE,
            old_value="2025-01-01",
            new_value="2025-01-15",
            description="Decision date changed from 2025-01-01 to 2025-01-15"
        )
        assert change.type == ChangeType.DECISION_DATE_CHANGE
        assert change.old_value == "2025-01-01"
        assert change.new_value == "2025-01-15"

    def test_change_to_dict(self):
        """Test converting change to dictionary."""
        change = Change(
            type=ChangeType.STATUS,
            old_value="Old",
            new_value="New",
            description="Status changed from Old to New"
        )
        result = change.to_dict()
        assert result["type"] == "status"
        assert result["old_value"] == "Old"
        assert result["new_value"] == "New"


class TestDetector:
    """Tests for Detector base class."""

    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage repository."""
        mock = MagicMock(spec=SnapshotRepository)
        mock._get_connection.return_value.cursor.return_value.fetchone.return_value = None
        return mock

    def test_no_previous_snapshot(self, mock_storage):
        """Test handling when no previous snapshot exists."""
        detector = Detector(mock_storage)
        new_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"status_raw": "new_status"},
            timestamp=datetime.utcnow()
        )
        changes = detector.detect_changes(None, new_snapshot)
        assert len(changes) == 0

    def test_detect_changes_with_previous(self, mock_storage):
        """Test detecting changes when previous snapshot exists."""
        # Create mock previous snapshot
        prev_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={
                "status_raw": "old_status",
                "status_label": "old_label",
                "decision_date": "2025-01-01",
                "attachments": [{"name": "doc1.pdf"}],
                "submit_date": "2025-01-01",
                "updated_at": "2025-01-01T00:00:00"
            },
            timestamp=datetime.utcnow()
        )

        # Create mock current snapshot
        current_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={
                "status_raw": "new_status",
                "status_label": "new_label",
                "decision_date": "2025-01-15",
                "attachments": [{"name": "doc1.pdf"}, {"name": "doc2.pdf"}],
                "submit_date": "2025-01-01",
                "updated_at": "2025-01-02T00:00:00"
            },
            timestamp=datetime.utcnow()
        )

        detector = Detector(mock_storage)
        changes = detector.detect_changes(prev_snapshot, current_snapshot)

        # Should detect multiple changes
        assert len(changes) > 0
        change_types = [c.type.value for c in changes]
        assert "status" in change_types
        assert "decision_date_change" in change_types


class TestStatusDetector:
    """Tests for StatusDetector."""

    def test_detect_status_change(self):
        """Test detecting status change."""
        prev_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"status_raw": "In process"},
            timestamp=datetime.utcnow()
        )

        current_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"status_raw": "Accepted"},
            timestamp=datetime.utcnow()
        )

        detector = StatusDetector()
        changes = detector.detect(prev_snapshot, current_snapshot)

        assert len(changes) == 1
        assert changes[0].type == ChangeType.STATUS
        assert changes[0].old_value == "In process"
        assert changes[0].new_value == "Accepted"

    def test_no_status_change(self):
        """Test when status hasn't changed."""
        prev_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"status_raw": "In process"},
            timestamp=datetime.utcnow()
        )

        current_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"status_raw": "In process"},
            timestamp=datetime.utcnow()
        )

        detector = StatusDetector()
        changes = detector.detect(prev_snapshot, current_snapshot)

        assert len(changes) == 0

    # Status label detection removed - status_label is derived from status_raw via i18n,
    # not a separate field that changes independently.


class TestDocumentDetector:
    """Tests for DocumentDetector."""

    def test_detect_new_document(self):
        """Test detecting new document."""
        prev_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"relatedDocs": [{"id": "doc1", "name": "doc1.pdf"}]},
            timestamp=datetime.utcnow()
        )

        current_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"relatedDocs": [{"id": "doc1", "name": "doc1.pdf"}, {"id": "doc2", "name": "doc2.pdf"}]},
            timestamp=datetime.utcnow()
        )

        detector = DocumentDetector(None)
        changes = detector.detect(prev_snapshot, current_snapshot)

        assert len(changes) == 1
        assert changes[0].type == ChangeType.NEW_DOCUMENT
        assert changes[0].new_value == "doc2"

    def test_detect_removed_document(self):
        """Test detecting removed document."""
        prev_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"relatedDocs": [{"id": "doc1", "name": "doc1.pdf"}, {"id": "doc2", "name": "doc2.pdf"}]},
            timestamp=datetime.utcnow()
        )

        current_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"relatedDocs": [{"id": "doc1", "name": "doc1.pdf"}]},
            timestamp=datetime.utcnow()
        )

        detector = DocumentDetector(None)
        changes = detector.detect(prev_snapshot, current_snapshot)

        assert len(changes) == 1
        assert changes[0].type == ChangeType.REMOVED_DOCUMENT
        assert changes[0].old_value == "doc2"

    def test_no_document_change(self):
        """Test when no document changes."""
        prev_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"relatedDocs": [{"id": "doc1", "name": "doc1.pdf"}]},
            timestamp=datetime.utcnow()
        )

        current_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"relatedDocs": [{"id": "doc1", "name": "doc1.pdf"}]},
            timestamp=datetime.utcnow()
        )

        detector = DocumentDetector(None)
        changes = detector.detect(prev_snapshot, current_snapshot)

        assert len(changes) == 0

    def test_empty_relatedDocs_old(self):
        """Test when old snapshot has empty relatedDocs."""
        prev_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"relatedDocs": []},
            timestamp=datetime.utcnow()
        )

        current_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"relatedDocs": [{"id": "doc1", "name": "doc1.pdf"}]},
            timestamp=datetime.utcnow()
        )

        detector = DocumentDetector(None)
        changes = detector.detect(prev_snapshot, current_snapshot)

        assert len(changes) == 1
        assert changes[0].type == ChangeType.NEW_DOCUMENT


class TestDateDetector:
    """Tests for DateDetector."""

    def test_detect_decision_date_change(self):
        """Test detecting decision date change."""
        prev_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"decision_date": "2025-01-01"},
            timestamp=datetime.utcnow()
        )

        current_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"decision_date": "2025-01-15"},
            timestamp=datetime.utcnow()
        )

        detector = DateDetector(None)
        changes = detector.detect(prev_snapshot, current_snapshot)

        assert len(changes) == 1
        assert changes[0].type == ChangeType.DECISION_DATE_CHANGE

    def test_detect_submit_date_change(self):
        """Test detecting submit date change."""
        prev_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"submit_date": "2025-01-01"},
            timestamp=datetime.utcnow()
        )

        current_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"submit_date": "2025-02-01"},
            timestamp=datetime.utcnow()
        )

        detector = DateDetector(None)
        changes = detector.detect(prev_snapshot, current_snapshot)

        assert len(changes) == 1
        assert changes[0].type == ChangeType.SUBMIT_DATE_CHANGE

    def test_no_date_change(self):
        """Test when no date changes."""
        prev_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"decision_date": "2025-01-15"},
            timestamp=datetime.utcnow()
        )

        current_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"decision_date": "2025-01-15"},
            timestamp=datetime.utcnow()
        )

        detector = DateDetector(None)
        changes = detector.detect(prev_snapshot, current_snapshot)

        assert len(changes) == 0

    def test_detect_updated_at_change(self):
        """Test detecting updated_at change."""
        prev_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"updated_at": "2025-01-01T00:00:00"},
            timestamp=datetime.utcnow()
        )

        current_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"updated_at": "2025-01-02T00:00:00"},
            timestamp=datetime.utcnow()
        )

        detector = DateDetector(None)
        changes = detector.detect(prev_snapshot, current_snapshot)

        assert len(changes) == 1
        assert changes[0].type == ChangeType.UPDATED_AT_CHANGE


class TestTimelineDetector:
    """Tests for TimelineDetector."""

    def test_detect_timeline_event_added(self):
        """Test detecting new timeline event."""
        prev_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"timelineEvents": [
                {"eventType": "Created", "date": "2025-09-14T12:13:50.9923305Z", "author": "Cudzoziemiec"}
            ]},
            timestamp=datetime.utcnow()
        )

        current_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"timelineEvents": [
                {"eventType": "Created", "date": "2025-09-14T12:13:50.9923305Z", "author": "Cudzoziemiec"},
                {"eventType": "ActivityCreated", "date": "2025-10-27T15:05:09.7084651Z", "author": "Wydział Spraw Cudzoziemców"}
            ]},
            timestamp=datetime.utcnow()
        )

        detector = TimelineDetector(None)
        changes = detector.detect(prev_snapshot, current_snapshot)

        assert len(changes) == 1
        assert changes[0].type == ChangeType.TIMELINE_EVENT_ADDED
        assert "ActivityCreated" in changes[0].description
        assert "2025-10-27" in changes[0].description

    def test_no_timeline_change(self):
        """Test when no timeline changes."""
        prev_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"timelineEvents": [
                {"eventType": "Created", "date": "2025-09-14T12:13:50.9923305Z", "author": "Cudzoziemiec"}
            ]},
            timestamp=datetime.utcnow()
        )

        current_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"timelineEvents": [
                {"eventType": "Created", "date": "2025-09-14T12:13:50.9923305Z", "author": "Cudzoziemiec"}
            ]},
            timestamp=datetime.utcnow()
        )

        detector = TimelineDetector(None)
        changes = detector.detect(prev_snapshot, current_snapshot)

        assert len(changes) == 0

    def test_empty_timeline_old(self):
        """Test when old snapshot has empty timeline."""
        prev_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"timelineEvents": []},
            timestamp=datetime.utcnow()
        )

        current_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"timelineEvents": [
                {"eventType": "Created", "date": "2025-09-14T12:13:50.9923305Z", "author": "Cudzoziemiec"}
            ]},
            timestamp=datetime.utcnow()
        )

        detector = TimelineDetector(None)
        changes = detector.detect(prev_snapshot, current_snapshot)

        assert len(changes) == 1
        assert changes[0].type == ChangeType.TIMELINE_EVENT_ADDED
        assert "Created" in changes[0].description


class TestQuestionDetector:
    """Tests for QuestionDetector."""

    def test_detect_new_question(self):
        """Test detecting new question (asked)."""
        prev_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"questions": []},
            timestamp=datetime.utcnow()
        )

        current_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"questions": [
                {"id": "q1", "status": 1, "title": 7, "sent_time": "2025-01-20T08:55:45.0303626Z"}
            ]},
            timestamp=datetime.utcnow()
        )

        detector = QuestionDetector()
        changes = detector.detect(prev_snapshot, current_snapshot)

        assert len(changes) == 1
        assert changes[0].type == ChangeType.QUESTION_ASKED
        assert "title: Other" in changes[0].description

    def test_detect_question_answered(self):
        """Test detecting question answered (status 1 -> 2)."""
        prev_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"questions": [
                {"id": "q1", "status": 1, "title": 7, "sent_time": "2025-01-20T08:55:45.0303626Z"}
            ]},
            timestamp=datetime.utcnow()
        )

        current_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"questions": [
                {"id": "q1", "status": 2, "title": 7, "sent_time": "2025-01-20T08:55:45.0303626Z"}
            ]},
            timestamp=datetime.utcnow()
        )

        detector = QuestionDetector()
        changes = detector.detect(prev_snapshot, current_snapshot)

        assert len(changes) == 1
        assert changes[0].type == ChangeType.QUESTION_ANSWERED
        assert "Other" in changes[0].description

    def test_no_question_change(self):
        """Test when no question changes."""
        prev_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"questions": [
                {"id": "q1", "status": 2, "title": 7, "sent_time": "2025-01-20T08:55:45.0303626Z"}
            ]},
            timestamp=datetime.utcnow()
        )

        current_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"questions": [
                {"id": "q1", "status": 2, "title": 7, "sent_time": "2025-01-20T08:55:45.0303626Z"}
            ]},
            timestamp=datetime.utcnow()
        )

        detector = QuestionDetector()
        changes = detector.detect(prev_snapshot, current_snapshot)

        assert len(changes) == 0

    def test_multiple_questions(self):
        """Test detecting changes across multiple questions."""
        prev_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"questions": [
                {"id": "q1", "status": 1, "title": 7, "sent_time": "2025-01-20T08:55:45.0303626Z"},
                {"id": "q2", "status": 2, "title": 8, "sent_time": "2025-01-21T10:00:00.0000000Z"}
            ]},
            timestamp=datetime.utcnow()
        )

        current_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"questions": [
                {"id": "q1", "status": 2, "title": 7, "sent_time": "2025-01-20T08:55:45.0303626Z"},  # answered
                {"id": "q2", "status": 2, "title": 8, "sent_time": "2025-01-21T10:00:00.0000000Z"},
                {"id": "q3", "status": 1, "title": 9, "sent_time": "2025-01-22T12:00:00.0000007Z"}   # new
            ]},
            timestamp=datetime.utcnow()
        )

        detector = QuestionDetector()
        changes = detector.detect(prev_snapshot, current_snapshot)

        assert len(changes) == 2
        change_types = [c.type.value for c in changes]
        assert "question_asked" in change_types
        assert "question_answered" in change_types
    def test_detect_question_answered_by_answer_change(self):
        """Test detecting question answered when answer is provided (status stays 1->2 but we also check answer change)."""
        prev_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"questions": [
                {"id": "q1", "status": 1, "title": 7, "sent_time": "2025-01-20T08:55:45.0303626Z", "answer": None}
            ]},
            timestamp=datetime.utcnow()
        )

        current_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"questions": [
                {"id": "q1", "status": 2, "title": 7, "sent_time": "2025-01-20T08:55:45.0303626Z", "answer": "This is the answer"}
            ]},
            timestamp=datetime.utcnow()
        )

        detector = QuestionDetector()
        changes = detector.detect(prev_snapshot, current_snapshot)

        # Should detect at least one change for the answered question
        assert len(changes) >= 1
        
        # Find the QUESTION_ANSWERED change
        answer_changes = [c for c in changes if c.type == ChangeType.QUESTION_ANSWERED]
        assert len(answer_changes) >= 1
        
        # Check that the change has the expected properties
        change = answer_changes[0]
        assert "Question answered" in change.description
        assert "This is the answer" in change.description


class TestDetectChanges:
    """Tests for detect_changes helper function."""

    def test_multiple_change_types(self):
        """Test that detect_changes returns all change types."""
        prev_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={
                "status_raw": "old_status",
                "decision_date": "2025-01-01",
                "relatedDocs": [{"id": "doc1", "name": "doc1.pdf"}],
                "submit_date": "2025-01-01",
                "updated_at": "2025-01-01T00:00:00"
            },
            timestamp=datetime.utcnow()
        )

        current_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={
                "status_raw": "new_status",
                "decision_date": "2025-01-15",
                "relatedDocs": [{"id": "doc1", "name": "doc1.pdf"}, {"id": "doc2", "name": "doc2.pdf"}],
                "submit_date": "2025-02-01",
                "updated_at": "2025-01-02T00:00:00"
            },
            timestamp=datetime.utcnow()
        )

        changes = detect_changes(prev_snapshot, current_snapshot)

        change_types = [c.type.value for c in changes]
        assert "status" in change_types
        assert "decision_date_change" in change_types
        assert "new_document" in change_types
        assert "submit_date_change" in change_types


class TestSnapshotRepository:
    """Tests for SnapshotRepository methods."""

    def test_get_previous_snapshot_not_found(self):
        """Test when no previous snapshot exists."""
        storage = SnapshotRepository("data/test_snapshots.db")

        prev = storage.get_previous_snapshot("account1", "CASE-123", "case_data")
        assert prev is None

    def test_get_previous_snapshot_found(self, tmp_path):
        """Test getting previous snapshot from database."""
        # Create test database
        db_path = tmp_path / "test_snapshots.db"
        storage = SnapshotRepository(str(db_path))

        # Create two snapshots - previous and current
        from datetime import datetime, timedelta
        prev_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"status_raw": "old_status"},
            timestamp=datetime.utcnow() - timedelta(hours=1)
        )
        storage.save_snapshot(prev_snapshot)

        current_snapshot = Snapshot(
            account_id="account1",
            case_id="CASE-123",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={"status_raw": "new_status"},
            timestamp=datetime.utcnow()
        )
        storage.save_snapshot(current_snapshot)

        # Get the previous snapshot (should be the first one)
        result = storage.get_previous_snapshot("account1", "CASE-123", "case_data")

        assert result is not None
        assert result.parsed_data.get("status_raw") == "old_status"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
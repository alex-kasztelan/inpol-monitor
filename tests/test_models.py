"""Tests for Pydantic models in src/models.py.

This module contains tests for CaseData, Attachment, Question, and Snapshot models.
"""

import pytest
from datetime import datetime
from src.models import CaseData, Attachment, Question, Snapshot, from_json_snapshot


class TestAttachment:
    """Tests for Attachment model."""

    def test_attachment_creation(self):
        """Attachment model accepts all required fields."""
        attachment = Attachment(
            name="document.pdf",
            date_added="2026-03-01",
            url="https://example.com/doc.pdf"
        )
        assert attachment.name == "document.pdf"
        assert attachment.date_added == "2026-03-01"
        assert attachment.url == "https://example.com/doc.pdf"

    def test_attachment_without_url(self):
        """Attachment model handles optional URL field."""
        attachment = Attachment(
            name="document.pdf",
            date_added="2026-03-01"
        )
        assert attachment.name == "document.pdf"
        assert attachment.url is None

    def test_attachment_defaults(self):
        """Attachment model uses defaults for optional fields."""
        attachment = Attachment(name="file.pdf", date_added="2026-03-01")
        assert attachment.url is None


class TestQuestion:
    """Tests for Question model."""

    def test_question_creation(self):
        """Question model accepts all required fields."""
        question = Question(
            id="Q001",
            content="Does the application meet all requirements?",
            status="PENDING",
            status_label="Pending review",
            sent_time="2026-03-01T10:00:00Z"
        )
        assert question.id == "Q001"
        assert question.content == "Does the application meet all requirements?"
        assert question.status == "PENDING"
        assert question.status_label == "Pending review"
        assert question.sent_time == "2026-03-01T10:00:00Z"

    def test_question_without_status_label(self):
        """Question model handles optional status_label field."""
        question = Question(
            id="Q001",
            content="Sample question",
            status="APPROVED",
            sent_time="2026-03-01T10:00:00Z"
        )
        assert question.status_label is None


class TestCaseData:
    """Tests for CaseData model."""

    def test_casedata_creation(self):
        """CaseData model accepts all required fields."""
        attachment = Attachment(name="doc.pdf", date_added="2026-03-01")
        question = Question(
            id="Q001",
            content="Sample question",
            status="PENDING",
            sent_time="2026-03-01T10:00:00Z"
        )

        casedata = CaseData(
            person_first="John",
            person_last="Doe",
            case_number="WSC-V.6153.4537.2025",
            case_type="Residency",
            submit_date="2026-02-01",
            decision_date="2026-05-01",
            updated_at="2026-03-01T12:00:00Z",
            status_raw="IN_PROGRESS",
            status_label="In Progress",
            attachments=[attachment],
            questions=[question],
            timeline=[]
        )

        assert casedata.person_first == "John"
        assert casedata.person_last == "Doe"
        assert casedata.case_number == "WSC-V.6153.4537.2025"
        assert casedata.case_type == "Residency"
        assert casedata.submit_date == "2026-02-01"
        assert casedata.decision_date == "2026-05-01"
        assert casedata.updated_at == "2026-03-01T12:00:00Z"
        assert casedata.status_raw == "IN_PROGRESS"
        assert casedata.status_label == "In Progress"
        assert len(casedata.attachments) == 1
        assert len(casedata.questions) == 1

    def test_casedata_without_optional_fields(self):
        """CaseData model handles missing optional fields."""
        casedata = CaseData(
            person_first="Jane",
            person_last="Smith",
            case_number="WSC-V.1234.5678.2025",
            case_type="Work Permit",
            updated_at="2026-03-01T12:00:00Z",
            status_raw="APPROVED"
        )

        assert casedata.submit_date is None
        assert casedata.decision_date is None
        assert casedata.status_label is None
        assert casedata.attachments == []
        assert casedata.questions == []
        assert casedata.timeline == []

    def test_casedata_with_empty_collections(self):
        """CaseData model handles empty lists for collections."""
        casedata = CaseData(
            person_first="Test",
            person_last="Person",
            case_number="WSC-V.9999.0000.2025",
            case_type="Test",
            updated_at="2026-03-01T12:00:00Z",
            status_raw="TEST",
            attachments=[],
            questions=[],
            timeline=[]
        )

        assert casedata.attachments == []
        assert casedata.questions == []
        assert casedata.timeline == []


class TestSnapshot:
    """Tests for Snapshot model."""

    def test_snapshot_creation(self):
        """Snapshot model accepts all required fields."""
        snapshot = Snapshot(
            account_id="account1",
            case_id="779596CE-F7AF-496C-9862-F4E7C837F2A6",
            endpoint_type="case_data",
            raw_json={"key": "value"},
            parsed_data={"status": "IN_PROGRESS"},
            timestamp=datetime(2026, 3, 1, 12, 0, 0)
        )

        assert snapshot.account_id == "account1"
        assert snapshot.case_id == "779596CE-F7AF-496C-9862-F4E7C837F2A6"
        assert snapshot.endpoint_type == "case_data"
        assert snapshot.raw_json == {"key": "value"}
        assert snapshot.parsed_data == {"status": "IN_PROGRESS"}
        assert snapshot.timestamp.year == 2026

    def test_snapshot_with_default_timestamp(self):
        """Snapshot model uses current time for timestamp when not provided."""
        snapshot = Snapshot(
            account_id="account1",
            case_id="TEST-CASE",
            endpoint_type="case_data",
            raw_json={}
        )

        assert snapshot.account_id == "account1"
        assert snapshot.case_id == "TEST-CASE"
        assert snapshot.endpoint_type == "case_data"
        assert snapshot.raw_json == {}
        assert snapshot.parsed_data == {}
        assert snapshot.timestamp is not None

    def test_from_json_snapshot(self):
        """from_json_snapshot helper creates Snapshot from raw JSON."""
        raw_data = {
            "id": 123,
            "name": "test",
            "timestamp": "2026-03-01T12:00:00Z"
        }

        snapshot = from_json_snapshot(
            account_id="account1",
            case_id="TEST-123",
            endpoint_type="case_data",
            raw_json=raw_data
        )

        assert snapshot.account_id == "account1"
        assert snapshot.case_id == "TEST-123"
        assert snapshot.endpoint_type == "case_data"
        assert snapshot.raw_json == raw_data
        assert snapshot.parsed_data == {}

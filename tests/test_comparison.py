"""Tests for field-level question comparison in build_comparison()."""

import os
from datetime import datetime, timezone
from src.models import Snapshot
from src.web.routes import build_comparison

# Ensure English translations for tests
os.environ["LANGUAGE"] = "en"


def _make_snapshot(questions, endpoint_type="questions", case_id="CASE-001"):
    """Create a mock snapshot with parsed_data containing questions."""
    return Snapshot(
        id=1,
        account_id="acc1",
        case_id=case_id,
        endpoint_type=endpoint_type,
        raw_json={},
        parsed_data={"questions": questions, "count": len(questions)},
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


class TestFieldLevelQuestionComparison:
    """Tests for field-level comparison of questions in both snapshots."""

    def test_no_field_diff_when_identical(self):
        """Test 1: build_comparison() with two snapshots where question X exists
        in both with same status returns no field-level diff items for that question."""
        q = {
            "id": "Q1",
            "title": "1",
            "status": "1",
            "status_label": "Waiting for an answer",
            "body": "What is the status?",
            "sentTime": "2025-01-01T10:00:00Z",
            "answer": None,
            "responseTime": None,
        }
        s1 = _make_snapshot([q])
        s2 = _make_snapshot([q])

        comparison = build_comparison(s1, s2)
        field_items = [c for c in comparison if c.get("is_question_field")]
        assert len(field_items) == 0

    def test_status_change_detected(self):
        """Test 2: build_comparison() with question X status change returns
        comparison item with field-level diff."""
        old_q = {
            "id": "Q1",
            "title": "1",
            "status": "1",
            "status_label": "Waiting for an answer",
            "body": "What is the status?",
            "sentTime": "2025-01-01T10:00:00Z",
            "answer": None,
            "responseTime": None,
        }
        new_q = {
            "id": "Q1",
            "title": "1",
            "status": "2",
            "status_label": "Answer",
            "body": "What is the status?",
            "sentTime": "2025-01-01T10:00:00Z",
            "answer": "Some answer",
            "responseTime": "2025-01-02T12:00:00Z",
        }
        s1 = _make_snapshot([old_q])
        s2 = _make_snapshot([new_q])

        comparison = build_comparison(s1, s2)
        field_items = [c for c in comparison if c.get("is_question_field")]

        # Should have status and status_label changes
        status_item = next((c for c in field_items if c["field_name"] == "status"), None)
        assert status_item is not None
        assert status_item["field"] == "question:Q1:status"
        assert status_item["old_value"] == "1"
        assert status_item["new_value"] == "2"
        assert status_item["changed"] is True
        assert status_item["is_question_field"] is True
        assert status_item["question_id"] == "Q1"

    def test_answer_change_detected(self):
        """Test 3: build_comparison() with answer=None in old and answer present
        in new returns comparison item with changed=True."""
        old_q = {
            "id": "Q1",
            "title": "1",
            "status": "1",
            "status_label": "Waiting for an answer",
            "body": "Question text",
            "sentTime": "2025-01-01T10:00:00Z",
            "answer": None,
            "responseTime": None,
        }
        new_q = {
            "id": "Q1",
            "title": "1",
            "status": "1",
            "status_label": "Waiting for an answer",
            "body": "Question text",
            "sentTime": "2025-01-01T10:00:00Z",
            "answer": "Some answer",
            "responseTime": "2025-01-02T12:00:00Z",
        }
        s1 = _make_snapshot([old_q])
        s2 = _make_snapshot([new_q])

        comparison = build_comparison(s1, s2)
        field_items = [c for c in comparison if c.get("is_question_field")]

        answer_item = next((c for c in field_items if c["field_name"] == "answer"), None)
        assert answer_item is not None
        assert answer_item["changed"] is True
        assert answer_item["old_value"] is None
        assert answer_item["new_value"] == "Some answer"

    def test_identical_fields_no_changed_items(self):
        """Test 4: build_comparison() with question X having identical fields
        returns no changed field-level items."""
        q = {
            "id": "Q1",
            "title": "3",
            "status": "2",
            "status_label": "Answer",
            "body": "Same body",
            "sentTime": "2025-01-01T10:00:00Z",
            "answer": "Same answer",
            "responseTime": "2025-01-02T12:00:00Z",
        }
        s1 = _make_snapshot([q])
        s2 = _make_snapshot([q])

        comparison = build_comparison(s1, s2)
        field_items = [c for c in comparison if c.get("is_question_field")]
        changed_items = [c for c in field_items if c.get("changed")]
        assert len(changed_items) == 0

    def test_new_and_removed_questions_still_detected(self):
        """Test 5: build_comparison() still detects new questions and removed questions
        as before (is_question=True)."""
        old_q = {
            "id": "Q1",
            "title": "1",
            "status": "1",
            "status_label": "Waiting for an answer",
            "body": "Old question",
            "sentTime": "2025-01-01T10:00:00Z",
            "answer": None,
            "responseTime": None,
        }
        new_q = {
            "id": "Q2",
            "title": "2",
            "status": "1",
            "status_label": "Waiting for an answer",
            "body": "New question",
            "sentTime": "2025-01-01T11:00:00Z",
            "answer": None,
            "responseTime": None,
        }
        s1 = _make_snapshot([old_q])
        s2 = _make_snapshot([new_q])

        comparison = build_comparison(s1, s2)
        question_items = [c for c in comparison if c.get("is_question")]
        assert len(question_items) == 2

        # Q1 removed, Q2 added
        removed = [c for c in question_items if c["old_value"] is None or c["new_value"] is None]
        assert len(removed) == 2
        q1_removed = next(c for c in question_items if "Q1" in c["field"])
        q2_added = next(c for c in question_items if "Q2" in c["field"])
        assert q1_removed["new_value"] is None
        assert q2_added["old_value"] is None

    def test_status_label_uses_translated_value(self):
        """Test 6: build_comparison() produces items with translated status_label
        using t('Cases.Question.Statuses.{status_id}') pattern."""
        old_q = {
            "id": "Q1",
            "title": "1",
            "status": "1",
            "status_label": "Waiting for an answer",
            "body": "Question",
            "sentTime": "2025-01-01T10:00:00Z",
            "answer": None,
            "responseTime": None,
        }
        new_q = {
            "id": "Q1",
            "title": "1",
            "status": "2",
            "status_label": "Answer",
            "body": "Question",
            "sentTime": "2025-01-01T10:00:00Z",
            "answer": "Got it",
            "responseTime": "2025-01-02T12:00:00Z",
        }
        s1 = _make_snapshot([old_q])
        s2 = _make_snapshot([new_q])

        comparison = build_comparison(s1, s2)
        field_items = [c for c in comparison if c.get("is_question_field")]

        status_label_item = next((c for c in field_items if c["field_name"] == "status_label"), None)
        assert status_label_item is not None
        # old_label and new_label should contain translated values
        assert "old_label" in status_label_item
        assert "new_label" in status_label_item
        assert status_label_item["old_label"] == "Waiting for an answer"
        assert status_label_item["new_label"] == "Answer"

    def test_title_uses_translated_value(self):
        """Test 7: build_comparison() produces items with translated title
        using t('Cases.Question.Titles.{title_id}') pattern."""
        old_q = {
            "id": "Q1",
            "title": "1",
            "status": "1",
            "status_label": "Waiting for an answer",
            "body": "Question",
            "sentTime": "2025-01-01T10:00:00Z",
            "answer": None,
            "responseTime": None,
        }
        new_q = {
            "id": "Q1",
            "title": "2",
            "status": "1",
            "status_label": "Waiting for an answer",
            "body": "Question",
            "sentTime": "2025-01-01T10:00:00Z",
            "answer": None,
            "responseTime": None,
        }
        s1 = _make_snapshot([old_q])
        s2 = _make_snapshot([new_q])

        comparison = build_comparison(s1, s2)
        field_items = [c for c in comparison if c.get("is_question_field")]

        title_item = next((c for c in field_items if c["field_name"] == "title"), None)
        assert title_item is not None
        assert "old_label" in title_item
        assert "new_label" in title_item
        assert title_item["old_label"] == "Missing documents"
        assert title_item["new_label"] == "Proxy"

"""Tests for the no-changes notification functionality."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

from src.detector import Detector
from src.models import Snapshot, Change, ChangeType
from src.notifier import TelegramNotifier
from src.storage import SnapshotRepository


class TestNoChangesNotification:
    """Tests for no-changes notification functionality."""

    def test_detect_all_changes_with_no_changes_sends_notification(self):
        """Test that when no changes are detected, a notification is still sent."""
        async def run_test():
            # Create real storage with mock methods
            mock_storage = MagicMock(spec=SnapshotRepository)
            
            # Return realistic previous snapshot data
            prev_data = Snapshot(
                account_id="account1",
                case_id="CASE-123",
                endpoint_type="case_data",
                raw_json={"person": {"firstName": "John", "surname": "Doe"}, "caseNumber": "123/2025"},
                parsed_data={"person_first": "John", "person_last": "Doe", "case_number": "123/2025", "case_type": "Test Case"},
                timestamp=datetime.utcnow()
            )
            mock_storage.get_previous_snapshot = AsyncMock(return_value=prev_data.model_dump(mode='json'))
            mock_storage.save_snapshot = MagicMock()
            
            # Setup mock notifier - use new interface
            mock_notifier = MagicMock(spec=TelegramNotifier)
            mock_notifier.on_change = MagicMock()
            mock_notifier.send_all_notifications = MagicMock()
            
            # Create detector
            detector = Detector(storage=mock_storage, notifier=mock_notifier)
            
            # Mock scraper to return same data (no changes)
            mock_case_data = MagicMock()
            mock_case_data.person_first = "John"
            mock_case_data.person_last = "Doe"
            mock_case_data.case_number = "123/2025"
            mock_case_data.case_type = "Test Case"
            mock_case_data.submit_date = "2025-01-01"
            mock_case_data.decision_date = "2025-01-15"
            mock_case_data.updated_at = "2025-01-01T00:00:00"
            mock_case_data.status_raw = "In process"
            mock_case_data.status_label = "In process"
            mock_case_data.related_docs = []
            mock_case_data.timeline_events = []
            mock_case_data.questions = []
            mock_case_data.model_dump = lambda mode: {
                "person_first": "John",
                "person_last": "Doe",
                "case_number": "123/2025",
                "case_type": "Test Case",
                "submit_date": "2025-01-01",
                "decision_date": "2025-01-15",
                "updated_at": "2025-01-01T00:00:00",
                "status_raw": "In process",
                "status_label": "In process",
                "related_docs": [],
                "timeline_events": [],
                "questions": []
            }
            
            mock_scraper = MagicMock()
            mock_scraper.fetch_case_data.return_value = mock_case_data
            mock_scraper.fetch_attachments.return_value = []
            mock_scraper.fetch_questions.return_value = []
            mock_scraper.base_url = "https://inpol.mazowieckie.pl"
            
            with patch('src.scraper.InpolScraper', return_value=mock_scraper):
                sessions = {"account1": MagicMock()}
                credentials = {"account1": {"case_ids": ["CASE-123"]}}
                
                # Execute
                results = await detector.detect_all_changes(sessions, credentials, mock_notifier)
                
                # Verify notifier.on_change was called (new interface)
                mock_notifier.on_change.assert_called_once()
                call_kwargs = mock_notifier.on_change.call_args.kwargs
                assert call_kwargs["account_id"] == "account1"
                assert call_kwargs["case_id"] == "CASE-123"
                assert call_kwargs["changes"] == []
                assert call_kwargs["case_type"] == "Test Case"
                assert call_kwargs["person_first"] == "John"

        asyncio.run(run_test())

    def test_detect_all_changes_with_changes_sends_notification(self):
        """Test that when changes are detected, a notification is sent."""
        async def run_test():
            # Create storage with DIFFERENT previous data (changes will be detected)
            mock_storage = MagicMock(spec=SnapshotRepository)
            
            prev_data = Snapshot(
                account_id="account1",
                case_id="CASE-123",
                endpoint_type="case_data",
                raw_json={"person": {"firstName": "Jane", "surname": "Smith"}, "caseNumber": "123/2025"},
                parsed_data={"person_first": "Jane", "person_last": "Smith", "case_number": "123/2025", "case_type": "Old Case"},
                timestamp=datetime.utcnow()
            )
            mock_storage.get_previous_snapshot = AsyncMock(return_value=prev_data.model_dump(mode='json'))
            mock_storage.save_snapshot = MagicMock()
            
            # Setup mock notifier - use new interface
            mock_notifier = MagicMock(spec=TelegramNotifier)
            mock_notifier.on_change = MagicMock()
            mock_notifier.send_all_notifications = MagicMock()
            
            # Create detector
            detector = Detector(storage=mock_storage, notifier=mock_notifier)
            
            # Mock scraper to return DIFFERENT data (changes will be detected)
            mock_case_data = MagicMock()
            mock_case_data.person_first = "John"  # Different!
            mock_case_data.person_last = "Doe"  # Different!
            mock_case_data.case_number = "123/2025"
            mock_case_data.case_type = "Test Case"  # Different!
            mock_case_data.submit_date = "2025-01-01"
            mock_case_data.decision_date = "2025-01-15"
            mock_case_data.updated_at = "2025-01-01T00:00:00"
            mock_case_data.status_raw = "In process"
            mock_case_data.status_label = "In process"
            mock_case_data.related_docs = []
            mock_case_data.timeline_events = []
            mock_case_data.questions = []
            mock_case_data.model_dump = lambda mode: {
                "person_first": "John",
                "person_last": "Doe",
                "case_number": "123/2025",
                "case_type": "Test Case",
                "submit_date": "2025-01-01",
                "decision_date": "2025-01-15",
                "updated_at": "2025-01-01T00:00:00",
                "status_raw": "In process",
                "status_label": "In process",
                "related_docs": [],
                "timeline_events": [],
                "questions": []
            }
            
            mock_scraper = MagicMock()
            mock_scraper.fetch_case_data.return_value = mock_case_data
            mock_scraper.fetch_attachments.return_value = []
            mock_scraper.fetch_questions.return_value = []
            mock_scraper.base_url = "https://inpol.mazowieckie.pl"
            
            with patch('src.scraper.InpolScraper', return_value=mock_scraper):
                sessions = {"account1": MagicMock()}
                credentials = {"account1": {"case_ids": ["CASE-123"]}}
                
                # Execute
                results = await detector.detect_all_changes(sessions, credentials, mock_notifier)
                
                # Verify notifier.on_change was called (new interface)
                mock_notifier.on_change.assert_called()
                call_kwargs = mock_notifier.on_change.call_args.kwargs
                assert call_kwargs["account_id"] == "account1"
                assert call_kwargs["case_id"] == "CASE-123"
                # Verify notification was sent (regardless of change count)

        asyncio.run(run_test())
"""Tests for InpolScraper in src/scraper.py.

This module contains tests for the scraper class methods.
These are unit tests that verify the scraper's parsing logic.
"""

import pytest
from unittest.mock import Mock, patch
from src.session_manager import SessionManager
from src.scraper import InpolScraper, _StatusCache
from src.models import CaseData, Attachment, Question


@pytest.fixture
def mock_session():
    """Create a mock SessionManager for testing."""
    mock = Mock(spec=SessionManager)
    mock.logged_in = True
    mock.session = Mock()
    return mock


@pytest.fixture
def scraper(mock_session):
    """Create an InpolScraper instance for testing."""
    return InpolScraper(session=mock_session)


def pytest_runtest_setup(item):
    """Clear cache before each test setup."""
    from src.scraper import _StatusCache
    _StatusCache._cache = None


class TestFetchCaseData:
    """Tests for fetch_case_data method."""

    def test_fetch_case_data_success(self, scraper, mock_session):
        """fetch_case_data returns CaseData when response is successful."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "person": {
                "firstName": "John",
                "surname": "Doe"
            },
            "signature": "WSC-V.6153.4537.2025",
            "circumstance": {
                "english": "Residency"
            },
            "creationDate": "2026-02-01",
            "decisionDate": "2026-05-01",
            "editDate": "2026-03-01T12:00:00Z",
            "status": "IN_PROGRESS",
            "attachments": [],
            "questions": []
        }
        mock_session.get.return_value = mock_response

        result = scraper.fetch_case_data("TEST-CASE-ID")

        assert result is not None
        assert isinstance(result, CaseData)
        assert result.person_first == "John"
        assert result.person_last == "Doe"
        assert result.case_number == "WSC-V.6153.4537.2025"
        assert result.case_type == "Residency"
        assert result.submit_date == "2026-02-01"
        assert result.decision_date == "2026-05-01"
        assert result.updated_at == "2026-03-01T12:00:00Z"
        assert result.status_raw == "IN_PROGRESS"

    def test_fetch_case_data_no_response(self, scraper, mock_session):
        """fetch_case_data returns None when session.get returns no response."""
        mock_session.get.return_value = None

        result = scraper.fetch_case_data("TEST-CASE-ID")
        assert result is None

    def test_fetch_case_data_error_status(self, scraper, mock_session):
        """fetch_case_data returns None when response status is not 200."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_session.get.return_value = mock_response

        result = scraper.fetch_case_data("TEST-CASE-ID")
        assert result is None

    def test_fetch_case_data_invalid_json(self, scraper, mock_session):
        """fetch_case_data handles invalid JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_session.get.return_value = mock_response

        result = scraper.fetch_case_data("TEST-CASE-ID")
        assert result is None


class TestFetchAttachments:
    """Tests for fetch_attachments method."""

    def test_fetch_attachments_success(self, scraper, mock_session):
        """fetch_attachments returns list of Attachment objects."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "attachments": [
                {"name": "doc1.pdf", "dateAdded": "2026-03-01", "url": "https://example.com/1"},
                {"name": "doc2.pdf", "dateAdded": "2026-03-02", "url": "https://example.com/2"}
            ]
        }
        mock_session.get.return_value = mock_response

        result = scraper.fetch_attachments("TEST-CASE-ID")

        assert isinstance(result, list)
        assert len(result) == 2
        assert isinstance(result[0], Attachment)
        assert result[0].name == "doc1.pdf"
        assert result[0].date_added == "2026-03-01"
        assert result[0].url == "https://example.com/1"

    def test_fetch_attachments_empty(self, scraper, mock_session):
        """fetch_attachments returns empty list when no attachments."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"attachments": []}
        mock_session.get.return_value = mock_response

        result = scraper.fetch_attachments("TEST-CASE-ID")
        assert result == []


class TestFetchQuestions:
    """Tests for fetch_questions method."""

    def test_fetch_questions_success(self, scraper, mock_session):
        """fetch_questions returns list of Question objects."""
        # Mock the questions list response
        questions_response = Mock()
        questions_response.status_code = 200
        questions_response.json.return_value = {
            "items": [
                {
                    "id": "Q001",
                    "status": "1",
                    "title": "4",
                    "sentTime": "2026-03-01T10:00:00Z"
                }
            ]
        }
        
        # Mock the question details response
        details_response = Mock()
        details_response.status_code = 200
        details_response.json.return_value = {
            "body": "Sample question content",
            "answer": "Sample answer content",
            "responseTime": "2026-03-01T11:00:00Z"
        }
        
        # Set up the mock to return different responses based on the URL
        def mock_get_side_effect(url, params=None):
            if "/questions" in url:
                return questions_response
            elif "/proceeding-question/" in url:
                return details_response
            return Mock(status_code=404)
        
        mock_session.get.side_effect = mock_get_side_effect

        # Mock the status dictionary for title resolution
        scraper._status_dict = {
            "Question.Titles.4": "Inspection of the proceeding files",
            "1": "Waiting for an answer"
        }

        result = scraper.fetch_questions("TEST-CASE-ID")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], Question)
        assert result[0].id == "Q001"
        assert result[0].content == "Sample question content"
        assert result[0].status == "1"
        assert result[0].status_label == "Waiting for an answer"
        assert result[0].answer == "Sample answer content"
        assert result[0].response_time == "2026-03-01T11:00:00Z"

    def test_fetch_questions_empty(self, scraper, mock_session):
        """fetch_questions returns empty list when no questions."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_session.get.return_value = mock_response

        result = scraper.fetch_questions("TEST-CASE-ID")
        assert result == []


class TestFetchStatusDictionary:
    """Tests for fetch_status_dictionary method."""

    def test_fetch_status_dictionary_success(self, scraper, mock_session):
        """fetch_status_dictionary returns status dict from fetched."""
        # Create a fresh mock specifically for status dictionary endpoint
        status_response = Mock()
        status_response.status_code = 200
        status_response.json.return_value = {
            "IN_PROGRESS": "In Progress",
            "APPROVED": "Approved",
            "REJECTED": "Rejected"
        }
        # Update the mock_session.get to return the status response
        mock_session.get.return_value = status_response

        # Clear cache
        _StatusCache._cache = None

        result = scraper.fetch_status_dictionary()

        assert isinstance(result, dict)
        assert "IN_PROGRESS" in result
        assert result["IN_PROGRESS"] == "In Progress"

    def test_fetch_status_dictionary_cached(self, scraper, mock_session):
        """fetch_status_dictionary returns cached status dict."""
        # Set up cached status dict
        _StatusCache._cache = {
            "IN_PROGRESS": "In Progress",
            "APPROVED": "Approved"
        }

        result = scraper.fetch_status_dictionary()

        assert isinstance(result, dict)
        assert "IN_PROGRESS" in result
        assert result["IN_PROGRESS"] == "In Progress"


class TestFetchAllForCase:
    """Tests for fetch_all_for_case method."""

    def test_fetch_all_for_case_success(self, scraper, mock_session):
        """fetch_all_for_case fetches all data for a case."""
        # Reset mock state to ensure clean test
        mock_session.get.reset_mock()

        case_data_response = Mock()
        case_data_response.status_code = 200
        case_data_response.json.return_value = {
            "personName": "John Doe",
            "caseNumber": "WSC-V.6153.4537.2025",
            "caseType": "Residency",
            "submitDate": "2026-02-01",
            "decisionDate": "2026-05-01",
            "updatedAt": "2026-03-01T12:00:00Z",
            "status": "IN_PROGRESS",
            "attachments": [],
            "questions": []
        }

        attachments_response = Mock()
        attachments_response.status_code = 200
        attachments_response.json.return_value = {"attachments": []}

        questions_response = Mock()
        questions_response.status_code = 200
        questions_response.json.return_value = {"content": {"questions": []}}

        mock_session.get.side_effect = [case_data_response, attachments_response, questions_response]

        result = scraper.fetch_all_for_case("TEST-CASE-ID")

        assert "error" not in result
        assert result["case_data"] is not None
        assert result["attachments"] == []
        assert result["questions"] == []

    def test_fetch_all_for_case_case_data_failure(self, scraper, mock_session):
        """fetch_all_for_case returns error if case data fetch fails."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_session.get.return_value = mock_response

        result = scraper.fetch_all_for_case("TEST-CASE-ID")

        assert "error" in result


class TestStatusResolution:
    """Tests for status label resolution."""

    def test_resolve_status_label(self, scraper):
        """resolve status label using status dict."""
        scraper._status_dict = {
            "IN_PROGRESS": "In Progress",
            "APPROVED": "Approved"
        }

        result = scraper._resolve_status_label("IN_PROGRESS")
        assert result == "In Progress"

    def test_resolve_status_label_not_found(self, scraper):
        """resolve status label returns None for unknown codes."""
        scraper._status_dict = {
            "IN_PROGRESS": "In Progress"
        }

        result = scraper._resolve_status_label("UNKNOWN_CODE")
        assert result is None

    def test_resolve_status_label_with_underscore(self, scraper):
        """resolve status label handles underscore conversion."""
        scraper._status_dict = {
            "IN_PROGRESS": "In Progress"
        }

        result = scraper._resolve_status_label("IN_PROGRESS")
        assert result == "In Progress"


class TestScraperInitialization:
    """Tests for InpolScraper initialization."""

    def test_scraper_with_status_dict(self, mock_session):
        """Scraper accepts status dict in constructor."""
        status_dict = {"IN_PROGRESS": "In Progress"}
        scraper = InpolScraper(session=mock_session, status_dict=status_dict)
        assert scraper._status_dict == status_dict

    def test_scraper_without_status_dict(self, mock_session):
        """Scraper without status dict will fetch it."""
        scraper = InpolScraper(session=mock_session)
        assert scraper._status_dict is None

    def test_scraper_custom_base_url(self, mock_session):
        """Scraper accepts custom base URL."""
        custom_url = "https://custom-inpol.example.com"
        scraper = InpolScraper(session=mock_session, base_url=custom_url)
        assert scraper.base_url == custom_url

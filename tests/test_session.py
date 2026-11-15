"""Tests for SessionManager class.

Tests cover:
- Session initialization with proper headers
- JWT login flow
- Session cleanup
"""

import pytest
from unittest.mock import Mock, patch
from curl_cffi.requests import Session

from src.session_manager import SessionManager


class TestSessionManagerInit:
    """Test SessionManager initialization."""

    def test_init_sets_base_url(self):
        """Test that base_url is stored correctly."""
        manager = SessionManager("https://example.com")
        assert manager.base_url == "https://example.com"

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is removed from base_url."""
        manager = SessionManager("https://example.com/")
        assert manager.base_url == "https://example.com"

    def test_init_creates_session(self):
        """Test that curl_cffi.Session is created."""
        manager = SessionManager("https://example.com")
        assert isinstance(manager.session, Session)

    def test_init_sets_user_agent(self):
        """Test that User-Agent header is set."""
        manager = SessionManager("https://example.com")
        assert "Chrome/124" in manager.session.headers.get("User-Agent", "")

    def test_init_sets_logged_in_false(self):
        """Test that logged_in starts as False."""
        manager = SessionManager("https://example.com")
        assert manager.logged_in is False

    def test_init_with_jwt_token(self):
        """Test that providing JWT token sets logged_in to True."""
        manager = SessionManager("https://example.com", jwt_token="eyJ.test.token")
        assert manager.logged_in is True
        assert manager.jwt_token == "eyJ.test.token"
        assert "Authorization" in manager.session.headers
        assert manager.session.headers["Authorization"] == "Bearer eyJ.test.token"


class TestJwtLogin:
    """Test JWT login functionality."""

    def test_login_success(self):
        """Test successful JWT login."""
        manager = SessionManager("https://example.com")

        # Mock the session.post to return a successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "token": "eyJ.abc.123",
            "refresh_token": "abc123",
            "expires_in": 3600
        }

        with patch.object(Session, 'post', return_value=mock_response):
            result = manager.login("user@example.com", "password123")

        assert result is True
        assert manager.logged_in is True
        assert manager.jwt_token == "eyJ.abc.123"
        assert manager.session.headers["Authorization"] == "Bearer eyJ.abc.123"

    def test_login_failure_wrong_credentials(self):
        """Test login failure returns False."""
        manager = SessionManager("https://example.com")

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "Code": "User_Email_Password-NotExists"
        }

        with patch.object(Session, 'post', return_value=mock_response):
            result = manager.login("user@example.com", "wrongpass")

        assert result is False
        assert manager.logged_in is False
        assert manager.jwt_token is None
        assert "Authorization" not in manager.session.headers

    def test_login_failure_missing_token(self):
        """Test login with response missing token returns False."""
        manager = SessionManager("https://example.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "refresh_token": "abc123",
            "expires_in": 3600
        }

        with patch.object(Session, 'post', return_value=mock_response):
            result = manager.login("user@example.com", "password123")

        assert result is False
        assert manager.logged_in is False

    def test_login_sends_correct_payload(self):
        """Test that login sends JSON payload with email and password."""
        manager = SessionManager("https://example.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "eyJ.abc.123"
        }

        captured_payload = {}

        def capture_post(url, json=None, **kwargs):
            captured_payload.update(json or {})
            return mock_response

        with patch.object(Session, 'post', side_effect=capture_post):
            manager.login("testuser@example.com", "testpass",)

        assert captured_payload == {
            "email": "testuser@example.com",
            "password": "testpass"
        }

    def test_login_uses_correct_endpoint(self):
        """Test that login posts to /identity/sign-in."""
        manager = SessionManager("https://example.com")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "eyJ.abc.123"
        }

        captured_url = None

        def capture_post(url, **kwargs):
            nonlocal captured_url
            captured_url = url
            return mock_response

        with patch.object(Session, 'post', side_effect=capture_post):
            manager.login("user@example.com", "pass")

        assert captured_url == "https://example.com/identity/sign-in"


class TestGetRequest:
    """Test GET requests with session."""

    def test_get_relative_url(self):
        """Test GET with relative URL."""
        manager = SessionManager("https://example.com/api")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"

        with patch.object(Session, 'get', return_value=mock_response) as mock_get:
            result = manager.get("/data")

        mock_get.assert_called_once_with("https://example.com/api/data")
        assert result is mock_response

    def test_get_absolute_url(self):
        """Test GET with absolute URL."""
        manager = SessionManager("https://example.com")

        mock_response = Mock()
        mock_response.status_code = 200

        with patch.object(Session, 'get', return_value=mock_response) as mock_get:
            result = manager.get("https://other.com/page")

        mock_get.assert_called_once_with("https://other.com/page")

    def test_get_returns_none_on_error(self):
        """Test that GET returns None on request error."""
        with patch.object(Session, 'get') as mock_get:
            mock_get.side_effect = Exception("Connection error")

            manager = SessionManager("https://example.com")
            result = manager.get("/page")

            assert result is None


class TestPostRequest:
    """Test POST requests with session."""

    def test_post_relative_url(self):
        """Test POST with relative URL."""
        manager = SessionManager("https://example.com/api")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}

        with patch.object(Session, 'post', return_value=mock_response) as mock_post:
            result = manager.post("/submit", json={"key": "value"})

        mock_post.assert_called_once_with("https://example.com/api/submit", json={"key": "value"})
        assert result is mock_response

    def test_post_returns_none_on_error(self):
        """Test that POST returns None on request error."""
        with patch.object(Session, 'post') as mock_post:
            mock_post.side_effect = Exception("Connection error")

            manager = SessionManager("https://example.com")
            result = manager.post("/api/data", json={})

            assert result is None


class TestClose:
    """Test session cleanup."""

    def test_close_sets_logged_in_false(self):
        """Test that close() resets logged_in flag."""
        manager = SessionManager("https://example.com", jwt_token="token")
        manager.logged_in = True

        manager.close()

        assert manager.logged_in is False

    def test_close_calls_session_close(self):
        """Test that close() calls underlying session.close()."""
        manager = SessionManager("https://example.com")
        mock_session = Mock()
        manager.session = mock_session

        manager.close()

        mock_session.close.assert_called_once()

    def test_context_manager_closes_session(self):
        """Test that context manager closes session on exit."""
        manager = SessionManager("https://example.com")
        mock_session = Mock()
        manager.session = mock_session

        with manager:
            pass

        mock_session.close.assert_called_once()

    def test_context_manager_closes_on_exception(self):
        """Test that context manager closes session even on exception."""
        manager = SessionManager("https://example.com")
        mock_session = Mock()
        manager.session = mock_session

        try:
            with manager:
                raise ValueError("Test error")
        except ValueError:
            pass

        mock_session.close.assert_called_once()

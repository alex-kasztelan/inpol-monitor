"""Tests for authentication flow module.

Tests cover:
- JWT-based account authentication
- Sequential multi-account login (D-04)
- Session validity checking (D-05)
"""

import pytest
from unittest.mock import Mock, patch

from src.auth import (
    authenticate_account,
    run_sequential_auth,
    check_session_validity,
    get_authenticated_session,
    DEFAULT_BASE_URL,
)
from src.session_manager import SessionManager


class TestAuthenticateAccount:
    """Test account authentication function."""

    def test_authenticate_success(self):
        """Test successful JWT authentication."""
        credentials = {"email": "user1@example.com", "password": "pass1"}

        with patch('src.auth.SessionManager') as MockManager:
            mock_session = Mock()
            mock_session.login.return_value = True
            mock_session.logged_in = True
            MockManager.return_value = mock_session

            result = authenticate_account("account1", credentials)

            assert result is mock_session
            MockManager.assert_called_once_with(DEFAULT_BASE_URL)
            mock_session.login.assert_called_once_with("user1@example.com", "pass1")

    def test_authenticate_failure(self):
        """Test authentication failure returns None."""
        credentials = {"email": "user1@example.com", "password": "wrong"}

        with patch('src.auth.SessionManager') as MockManager:
            mock_session = Mock()
            mock_session.login.return_value = False
            MockManager.return_value = mock_session

            result = authenticate_account("account1", credentials)

            assert result is None
            mock_session.close.assert_called_once()

    def test_authenticate_missing_credentials(self):
        """Test missing credentials returns None."""
        result = authenticate_account("account1", {})
        assert result is None

    def test_authenticate_missing_email(self):
        """Test missing email returns None."""
        credentials = {"password": "pass1"}
        result = authenticate_account("account1", credentials)
        assert result is None

    def test_authenticate_missing_password(self):
        """Test missing password returns None."""
        credentials = {"email": "user1@example.com"}
        result = authenticate_account("account1", credentials)
        assert result is None

    def test_authenticate_with_username_fallback(self):
        """Test that username field is used as email fallback."""
        credentials = {"username": "user1@example.com", "password": "pass1"}

        with patch('src.auth.SessionManager') as MockManager:
            mock_session = Mock()
            mock_session.login.return_value = True
            mock_session.logged_in = True
            MockManager.return_value = mock_session

            result = authenticate_account("account1", credentials)

            assert result is mock_session
            mock_session.login.assert_called_once_with("user1@example.com", "pass1")


class TestRunSequentialAuth:
    """Test sequential authentication."""

    def _make_session(self, logged_in=True):
        mock_session = Mock()
        mock_session.logged_in = logged_in
        mock_session.login.return_value = logged_in
        return mock_session

    def test_sequential_auth_both_accounts(self):
        """Test sequential auth for both accounts."""
        credentials = {
            "account1": {"email": "user1@example.com", "password": "pass1"},
            "account2": {"email": "user2@example.com", "password": "pass2"},
        }

        with patch('src.auth.authenticate_account') as mock_auth:
            mock_auth.side_effect = [
                self._make_session(),
                self._make_session(),
            ]

            results = list(run_sequential_auth(credentials))

            assert len(results) == 2
            assert results[0][0] == 'account1'
            assert results[1][0] == 'account2'
            assert mock_auth.call_count == 2

    def test_sequential_auth_skips_missing_account(self):
        """Test that missing account credentials are skipped."""
        credentials = {
            "account1": {"email": "user1@example.com", "password": "pass1"},
        }

        with patch('src.auth.authenticate_account') as mock_auth:
            mock_auth.return_value = self._make_session()

            results = list(run_sequential_auth(credentials))

            assert len(results) == 1
            assert results[0][0] == 'account1'

    def test_sequential_auth_skips_failed_login(self):
        """Test that failed logins are not yielded."""
        credentials = {
            "account1": {"email": "user1@example.com", "password": "pass1"},
        }

        with patch('src.auth.authenticate_account') as mock_auth:
            mock_auth.return_value = None

            results = list(run_sequential_auth(credentials))

            assert len(results) == 0

    def test_sequential_auth_empty_credentials(self):
        """Test that empty credentials result in no sessions."""
        results = list(run_sequential_auth({}))
        assert results == []

    def test_sequential_auth_loads_credentials_if_none(self):
        """Test that credentials are loaded from file if not provided."""
        with patch('src.auth.load_credentials') as mock_load, \
             patch('src.auth.authenticate_account') as mock_auth:
            mock_load.return_value = {}
            mock_auth.return_value = self._make_session()

            results = list(run_sequential_auth())

            assert results == []
            mock_load.assert_called_once()

    def test_sequential_auth_order(self):
        """Test that accounts are processed in order: account1, account2."""
        credentials = {
            "account2": {"email": "user2@example.com", "password": "pass2"},
            "account1": {"email": "user1@example.com", "password": "pass1"},
        }
        call_order = []

        def track_auth(name, *args):
            call_order.append(name)
            return self._make_session()

        with patch('src.auth.authenticate_account', side_effect=track_auth):
            results = list(run_sequential_auth(credentials))

            assert set(call_order) == {'account1', 'account2'}
            assert len(results) == 2


class TestCheckSessionValidity:
    """Test session validity checking."""

    def test_valid_session_with_jwt_token(self):
        """Test that valid JWT session is valid."""
        mock_session = Mock()
        mock_session.logged_in = True
        mock_session.jwt_token = "eyJ.abc.123"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response

        assert check_session_validity(mock_session) is True

    def test_invalid_session_not_logged_in_flag(self):
        """Test that not logged in session is invalid."""
        mock_session = Mock()
        mock_session.logged_in = False

        assert check_session_validity(mock_session) is False

    def test_invalid_session_no_jwt_token(self):
        """Test that session without JWT token is invalid."""
        mock_session = Mock()
        mock_session.logged_in = True
        mock_session.jwt_token = None

        assert check_session_validity(mock_session) is False

    def test_invalid_session_no_response(self):
        """Test that session without response is invalid."""
        mock_session = Mock()
        mock_session.logged_in = True
        mock_session.jwt_token = "eyJ.abc.123"
        mock_session.get.return_value = None

        assert check_session_validity(mock_session) is False


class TestGetAuthenticatedSession:
    """Test get_authenticated_session convenience function."""

    def test_get_authenticated_session_success(self):
        """Test successful session retrieval."""
        with patch('src.auth.authenticate_account') as mock_auth:
            mock_session = Mock()
            mock_session.logged_in = True
            mock_auth.return_value = mock_session

            result = get_authenticated_session("account1")

            assert result is mock_session

    def test_get_authenticated_session_loads_credentials(self):
        """Test that credentials are loaded from file."""
        with patch('src.auth.load_credentials') as mock_load, \
             patch('src.auth.authenticate_account') as mock_auth:
            mock_load.return_value = {
                "account1": {"email": "user1@example.com", "password": "pass1"}
            }
            mock_auth.return_value = None

            get_authenticated_session("account1")

            mock_auth.assert_called_once_with(
                "account1",
                {"email": "user1@example.com", "password": "pass1"},
                DEFAULT_BASE_URL
            )

    def test_get_authenticated_session_missing_account(self):
        """Test that missing account credentials return None."""
        with patch('src.auth.load_credentials') as mock_load:
            mock_load.return_value = {}

            result = get_authenticated_session("nonexistent")

            assert result is None

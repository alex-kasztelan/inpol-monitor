"""Tests for Telegram bot authorization and commands."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.telegram_bot import is_authorized
from src.config import get_authorized_telegram_users


class TestAuthorization:
    """Tests for authorization logic."""

    def test_is_authorized_with_configured_user(self):
        """Test that configured user is authorized."""
        with patch('src.config.os.getenv') as mock_getenv:
            def get_env(key, default=''):
                if key == 'AUTHORIZED_TELEGRAM_USERS':
                    return '123,456'
                if key == 'TELEGRAM_USER_ID':
                    return '789'
                return default
            
            mock_getenv.side_effect = get_env
            
            assert is_authorized('123') is True
            assert is_authorized('456') is True

    def test_is_authorized_with_unconfigured_user(self):
        """Test that unconfigured user is not authorized."""
        with patch('src.config.os.getenv') as mock_getenv:
            def get_env(key, default=''):
                if key == 'AUTHORIZED_TELEGRAM_USERS':
                    return '123'
                if key == 'TELEGRAM_USER_ID':
                    return ''
                return default
            
            mock_getenv.side_effect = get_env
            
            assert is_authorized('999') is False
            assert is_authorized('abc') is False

    def test_is_authorized_empty_config(self):
        """Test fallback behavior with empty config."""
        with patch('src.config.os.getenv') as mock_getenv:
            def get_env(key, default=''):
                if key == 'AUTHORIZED_TELEGRAM_USERS':
                    return ''
                if key == 'TELEGRAM_USER_ID':
                    return '789'
                return default
            
            mock_getenv.side_effect = get_env
            
            # Should fall back to TELEGRAM_USER_ID
            assert is_authorized('789') is True

    def test_is_authorized_string_id_comparison(self):
        """Test that authorization works with string comparison."""
        with patch('src.config.os.getenv') as mock_getenv:
            def get_env(key, default=''):
                if key == 'AUTHORIZED_TELEGRAM_USERS':
                    return '1078357459'
                if key == 'TELEGRAM_USER_ID':
                    return '1078357459'
                return default
            
            mock_getenv.side_effect = get_env
            
            assert is_authorized('1078357459') is True
            assert is_authorized(1078357459) is True


class TestGetAuthorizedUsers:
    """Tests for get_authorized_telegram_users function."""

    def test_multiple_users(self):
        """Test parsing multiple comma-separated users."""
        with patch('src.config.os.getenv') as mock_getenv:
            mock_getenv.return_value = '123,456,789'
            
            users = get_authorized_telegram_users()
            assert users == ['123', '456', '789']

    def test_single_user(self):
        """Test parsing single user."""
        with patch('src.config.os.getenv') as mock_getenv:
            mock_getenv.return_value = '123'
            
            users = get_authorized_telegram_users()
            assert users == ['123']

    def test_empty_string(self):
        """Test empty string returns fallback."""
        with patch('src.config.os.getenv') as mock_getenv:
            def get_env(key, default=''):
                if key == 'AUTHORIZED_TELEGRAM_USERS':
                    return ''
                if key == 'TELEGRAM_USER_ID':
                    return '999'
                return default
            
            mock_getenv.side_effect = get_env
            
            users = get_authorized_telegram_users()
            assert users == ['999']

    def test_whitespace(self):
        """Test whitespace is stripped."""
        with patch('src.config.os.getenv') as mock_getenv:
            mock_getenv.return_value = ' 123 , 456 '
            
            users = get_authorized_telegram_users()
            assert users == ['123', '456']

    def test_empty_entries_ignored(self):
        """Test empty entries between commas are ignored."""
        with patch('src.config.os.getenv') as mock_getenv:
            mock_getenv.return_value = '123,,456'
            
            users = get_authorized_telegram_users()
            assert users == ['123', '456']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
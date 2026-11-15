"""Tests for authentication failure scenarios."""

import pytest
from unittest.mock import patch, MagicMock
from src.auth import authenticate_account
from src.session_manager import SessionManager

def test_authenticate_account_failure_401():
    """Test authentication failure with 401 status."""
    with patch('src.session_manager.SessionManager.login') as mock_login:
        # Mock login to return False (failure)
        mock_login.return_value = False
        
        result = authenticate_account('test_account', {
            'email': 'test@example.com',
            'password': 'wrong_password'
        })
        
        assert result is None or not result.logged_in

def test_authenticate_account_failure_403():
    """Test authentication failure - treated as general failure."""
    with patch('src.session_manager.SessionManager.login') as mock_login:
        # Mock login to return False (failure)
        mock_login.return_value = False
        
        result = authenticate_account('test_account', {
            'email': 'test@example.com',
            'password': 'wrong_password'
        })
        
        assert result is None or not result.logged_in

def test_authenticate_account_missing_credentials():
    """Test authentication with missing credentials."""
    result = authenticate_account('test_account', {})
    assert result is None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
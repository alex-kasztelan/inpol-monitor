"""Tests for Telegram notification failure scenarios."""

import pytest
import os
from unittest.mock import patch, MagicMock
from src.notifier import TelegramNotifier
from src.models import Change, ChangeType

def test_telegram_notifier_failure_handling(monkeypatch):
    """Test that Telegram failures are handled gracefully."""
    # Set up authorized users (3 users)
    monkeypatch.setenv("AUTHORIZED_TELEGRAM_USERS", "Karol IV")
    
    # Reload notifier to pick up the new env
    from src import notifier as notifier_module
    notifier_module._env_values = {}
    notifier_module.load_dotenv()
    
    notifier = TelegramNotifier("test:token")
    
    # Add a case to accumulate
    changes = [Change(
        type=ChangeType.STATUS,
        old_value="1",
        new_value="2",
        description="Status changed"
    )]
    
    notifier.on_change("test_account", "karol@test.org", "TEST_CASE", changes, case_type="Test", person_first="John")
    
    # Mock the bot's send_message method to raise an exception
    with patch.object(notifier.bot, 'send_message') as mock_send:
        mock_send.side_effect = Exception("Network error")
        
        # send_all_notifications should handle the exception gracefully
        # The exception will be raised since we don't catch it
        try:
            notifier.send_all_notifications()
        except Exception as e:
            # Expected - we re-raise exceptions so callers know it failed
            assert str(e) == "Network error"

        # Verify send_message was attempted for all 3 users
        assert mock_send.call_count == 3

def test_telegram_rate_limiting_handling(monkeypatch):
    """Test handling of Telegram rate limiting (429)."""
    monkeypatch.setenv("AUTHORIZED_TELEGRAM_USERS", "1078357777")
    
    from src import notifier as notifier_module
    notifier_module._env_values = {}
    notifier_module.load_dotenv()
    
    notifier = TelegramNotifier("test:token")
    
    # Mock the bot's send_message method to raise a rate limit exception
    with patch.object(notifier.bot, 'send_message') as mock_send:
        mock_send.side_effect = Exception("429 Too Many Requests")
        
        # Should handle gracefully without crashing
        notifier.on_error("test_account", "TEST_CASE", Exception("Rate limit"), "RATE_LIMIT_ERROR")
        
        # Verify send_message was attempted
        mock_send.assert_called_once()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
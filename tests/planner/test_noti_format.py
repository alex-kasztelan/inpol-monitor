"""Tests for notification format validation."""

import os
os.environ["LANGUAGE"] = "en"

import pytest
from src.notifier import TelegramNotifier
from src.models import Change, ChangeType

def test_notification_format_markdown_v2():
    """Test that notifications use proper MarkdownV2 formatting."""
    notifier = TelegramNotifier("test:token")
    
    # Create test changes
    changes = [
        Change(
            type=ChangeType.STATUS,
            old_value="1",
            new_value="2",
            description="Status changed from New to In progress"
        ),
        Change(
            type=ChangeType.NEW_DOCUMENT,
            old_value=None,
            new_value="doc123",
            description="New document added: certification.pdf"
        )
    ]
    
    # Test message building
    message = notifier._build_change_message("test_account", "TEST_CASE", changes, len(changes))
    print("Generated message:")
    print(repr(message))
    print("Actual message:")
    print(message)
    
    # Verify plain text format
    assert "Changes Detected in test_account account" in message
    assert "Summary:" in message
    assert "Case ID: TEST_CASE" in message
    assert "* Status:" in message
    assert "* New document:" in message

def test_error_notification_format():
    """Test error notification format."""
    notifier = TelegramNotifier("test:token")
    
    message = notifier._build_error_message(
        "test_account", 
        "TEST_CASE", 
        Exception("Test error"), 
        "TEST_ERROR"
    )
    
    assert "[TEST_CASE] Case list" in message
    assert "Error:" in message
    assert "TEST_ERROR: Test error" in message

def test_notification_character_limit():
    """Test that notifications respect character limits."""
    notifier = TelegramNotifier("test:token")
    
    # Create many changes to test length
    changes = []
    for i in range(50):  # Enough to potentially exceed limit
        changes.append(Change(
            type=ChangeType.STATUS,
            old_value=f"old_{i}",
            new_value=f"new_{i}",
            description=f"Status changed from old_{i} to new_{i}"
        ))
    
    message = notifier._build_change_message("test_account", "TEST_CASE", changes, len(changes))
    
    # Telegram limit is 4096 characters
    assert len(message) <= 4096, f"Message too long: {len(message)} characters"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
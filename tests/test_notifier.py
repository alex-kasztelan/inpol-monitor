"""Tests for Telegram notification module."""

import os
os.environ["LANGUAGE"] = "en"

from unittest.mock import MagicMock, patch

from src.models import Change, ChangeType
from src.notifier import TelegramNotifier, ChangeNotifier, MockBot

# Load real credentials from .env
ENV_FILE = os.path.join(os.path.dirname(__file__), '..', '.env')
from dotenv import load_dotenv
load_dotenv(ENV_FILE)  # Load .env file at module level

# Get real credentials once at module level (before any mocking)
REAL_TELEGRAM_USER_ID = os.getenv("TELEGRAM_USER_ID", "123456789")
REAL_TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "test:token")


class TestChangeNotifier:
    """Tests for ChangeNotifier base class."""

    def test_base_class_exists(self):
        """Test that ChangeNotifier is a base class."""
        assert issubclass(ChangeNotifier, object)


class TestTelegramNotifier:
    """Tests for TelegramNotifier."""

    def test_init_with_token(self, monkeypatch):
        """Test initialization with bot token."""
        # Use test Telegram credentials to ensure MockBot is used
        test_user_id = "123456789"
        test_bot_token = "test:test-token"
        monkeypatch.setattr("os.environ", MagicMock(get={
            "TELEGRAM_USER_ID": test_user_id,
            "TELEGRAM_BOT_TOKEN": test_bot_token,
        }))

        notifier = TelegramNotifier(test_bot_token)

        # Verify bot is MockBot for test tokens
        assert isinstance(notifier.bot, MockBot)
        assert notifier.message_count == 0
        assert notifier._cases_to_notify == []
        assert notifier._messages_sent == []

    def test_on_change_accumulates_cases(self, monkeypatch):
        """Test on_change accumulates cases for batched notification."""
        # Use test Telegram credentials to ensure MockBot is used
        test_user_id = "123456789"
        test_bot_token = "test:test-token"
        monkeypatch.setenv("TELEGRAM_USER_ID", test_user_id)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", test_bot_token)

        notifier = TelegramNotifier(test_bot_token)

        # Call on_change for two different cases
        notifier.on_change(
            "acc1",
            "karol@test.org",
            "case1",
            [Change.model_validate({"type": "status", "old_value": "old", "new_value": "new", "description": "test"})],
            case_type="Test Type",
            person_first="John",
            case_url="https://inpol.mazowieckie.pl/home/cases/case1",
            status="1"
        )
        notifier.on_change(
            "acc1",
            "karol@test.org",
            "case2",
            [Change.model_validate({"type": "new_document", "old_value": None, "new_value": "doc.pdf", "description": "test"})],
            case_type="Other Type",
            person_first="Jane",
            case_url="https://inpol.mazowieckie.pl/home/cases/case2",
            status="2"
        )

        # Cases should be accumulated
        assert len(notifier._cases_to_notify) == 2

        # No messages sent yet (need to call send_all_notifications)
        assert len(notifier._messages_sent) == 0

    def test_send_all_notifications_sends_combined_message(self, monkeypatch):
        """Test send_all_notifications sends single combined message."""
        test_user_id = "123456789"
        test_bot_token = "test:test-token"
        monkeypatch.setenv("TELEGRAM_USER_ID", test_user_id)
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", test_bot_token)

        notifier = TelegramNotifier(test_bot_token)

        # Add two cases
        notifier.on_change(
            "acc1",
            "karol@test.org",
            "case1",
            [Change.model_validate({"type": "status", "old_value": "old", "new_value": "new", "description": "test"})],
            case_type="Test Type",
            person_first="John",
            case_url="https://inpol.mazowieckie.pl/home/cases/case1",
            status="1"
        )
        notifier.on_change(
            "acc1",
            "karol@test.org",
            "case2",
            [],
            case_type="Other Type",
            person_first="Jane",
            case_url="https://inpol.mazowieckie.pl/home/cases/case2",
            status="2"
        )

        # Send all notifications
        notifier.send_all_notifications()

        # Verify message sent
        assert len(notifier._messages_sent) == 1

        # Verify combined message format
        msg = notifier._messages_sent[0]["message"]
        assert "Summary:" in msg
        assert "<b>1</b> change(s) in" in msg
        assert "<a href=" in msg
        assert "case1" in msg
        assert "case2" in msg
        assert "Case Details:" in msg
        assert "Case ID: case1" in msg
        assert "Case ID: case2" in msg

    def test_on_error_sends_error_notification(self):
        """Test on_error triggers error notification."""
        # Use test Telegram credentials to ensure MockBot is used
        test_user_id = "123456789"
        test_bot_token = "test:test-token"
        notifier = TelegramNotifier(test_bot_token)

        # Call on_error
        notifier.on_error("acc1", "case1", Exception("test error"), "LOGIN_ERROR")

        # Verify notification sent
        assert len(notifier._messages_sent) == 1

        # Verify message type
        assert notifier._messages_sent[0]["type"] == "error"

    def test_build_single_message_format(self):
        """Test combined message formatting."""
        test_user_id = "123456789"
        test_bot_token = "test:test-token"
        notifier = TelegramNotifier(test_bot_token)

        from src.notifier import CaseInfo
        cases = [
            CaseInfo(
                case_id="case1",
                account_id="acc1",
                case_type="Test Type",
                person_first="John",
                changes=[
                    Change.model_validate({"type": "status", "old_value": "In process", "new_value": "Accepted", "description": "Status changed"})
                ],
                total_changes=1,
                account_login="karol@test.org",
                case_url="https://inpol.mazowieckie.pl/home/cases/case1"
            ),
            CaseInfo(
                case_id="case2",
                account_id="acc1",
                case_type="Other Type",
                person_first="Jane",
                changes=[],
                total_changes=0,
                account_login="karol@test.org",
                case_url="https://inpol.mazowieckie.pl/home/cases/case2"
            ),
        ]

        message = notifier._build_single_message(cases)

        # Verify structure
        assert "Summary:" in message
        assert "<b>1</b> change(s) in <a href=" in message
        assert "(<b>karol@test.org</b>)" in message
        assert "<b>0</b> change(s) in <a href=" in message
        assert "case1" in message
        assert "Case Details:" in message
        assert "Case ID: case1" in message
        assert "Type: <b>Test Type</b>" in message
        assert "Person: <b>John</b>" in message
        assert "Case ID: case2" in message
        assert "* Status: In process -> Accepted" in message
        # Account should NOT be in Case Details (it's in summary now)
        assert "Account:" not in message

    def test_build_error_message(self):
        """Test error message formatting."""
        # Use test Telegram credentials to ensure MockBot is used
        test_user_id = "123456789"
        test_bot_token = "test:test-token"
        notifier = TelegramNotifier(test_bot_token)

        error = Exception("Login failed")
        message = notifier._build_error_message("acc1", "CASE-123", error, "LOGIN_ERROR")

        # Verify message structure
        assert "[CASE-123]" in message
        assert "Error:" in message
        assert "LOGIN_ERROR: Login failed" in message

    def test_reset_clears_accumulated_cases(self):
        """Test reset clears accumulated cases."""
        # Use test Telegram credentials to ensure MockBot is used
        test_user_id = "123456789"
        test_bot_token = "test:test-token"
        notifier = TelegramNotifier(test_bot_token)

        # Add a case
        notifier.on_change("acc1", "karol@test.org", "case1", [Change.model_validate({"type": "status", "old_value": "old", "new_value": "new", "description": "test"})], status="1")
        assert len(notifier._cases_to_notify) == 1

        notifier.reset()

        # After reset, cases_to_notify should be empty
        assert notifier._cases_to_notify == []
        assert notifier._messages_sent == []

    def test_bot_instance_is_created(self):
        """Verify bot instance is created correctly."""
        # Use test Telegram credentials to ensure MockBot is used
        test_user_id = "123456789"
        test_bot_token = "test:test-token"
        notifier = TelegramNotifier(test_bot_token)
        # For test tokens, bot should be MockBot instance
        assert isinstance(notifier.bot, MockBot)

    def test_on_change_with_error_message(self):
        """Test on_change with error_message for inaccessible cases."""
        test_user_id = "123456789"
        test_bot_token = "test:test-token"
        notifier = TelegramNotifier(test_bot_token)

        # Add a case with error (authentication failed)
        notifier.on_change(
            account_id="account1",
            account_login="karol@test.org",
            case_id="CASE-123",
            changes=[],
            case_type="",
            person_first="",
            case_url="https://inpol.mazowieckie.pl/home/cases/CASE-123",
            error_message="Account authentication failed or session unavailable"
        )

        assert len(notifier._cases_to_notify) == 1
        case = notifier._cases_to_notify[0]
        assert case.error_message == "Account authentication failed or session unavailable"

    def test_build_single_message_with_error_cases(self):
        """Test combined message formatting with inaccessible cases."""
        test_user_id = "123456789"
        test_bot_token = "test:test-token"
        notifier = TelegramNotifier(test_bot_token)

        from src.notifier import CaseInfo
        cases = [
            CaseInfo(
                case_id="case1",
                account_id="acc1",
                case_type="Test Type",
                person_first="John",
                changes=[],
                total_changes=0,
                account_login="karol@test.org",
                case_url="https://inpol.mazowieckie.pl/home/cases/case1",
                error_message="Account authentication failed or session unavailable"
            ),
            CaseInfo(
                case_id="case2",
                account_id="acc1",
                case_type="Other Type",
                person_first="Jane",
                changes=[Change.model_validate({"type": "status", "old_value": "In process", "new_value": "Accepted", "description": "Status changed"})],
                total_changes=1,
                account_login="karol@test.org",
                case_url="https://inpol.mazowieckie.pl/home/cases/case2"
            ),
        ]

        message = notifier._build_single_message(cases)

        # Verify summary shows error message for inaccessible case
        assert "Unable to access the case" in message
        assert "case1" in message
        assert "karol@test.org" in message
        assert "Account authentication failed" in message

        # Verify normal case shows changes
        assert "<b>1</b> change(s) in" in message
        assert "case2" in message

        # Verify case details section shows error for case1
        assert "Case Details:" in message
        assert "Case ID: case1" in message
        assert "Error: Account authentication failed" in message

        # Verify case2 details still show changes
        assert "Case ID: case2" in message
        assert "* Status: In process -> Accepted" in message


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])

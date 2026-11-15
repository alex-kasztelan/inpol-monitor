"""Tests for email notification module."""

import os
from unittest.mock import MagicMock, patch

import pytest
from src.email_notifier import EmailNotifier

ENV_FILE = os.path.join(os.path.dirname(__file__), '..', '.env')
from dotenv import load_dotenv
load_dotenv(ENV_FILE)


class TestEmailNotifier:
    """Tests for EmailNotifier class."""

    def test_init_with_valid_config(self):
        """Test initialization with valid SMTP config."""
        config = {
            "host": "smtp.example.com",
            "port": 587,
            "username": "user",
            "password": "pass",
            "from_addr": "from@example.com",
            "to_addr": "to@example.com",
        }
        notifier = EmailNotifier(config)

        assert notifier.enabled is True
        assert notifier.host == "smtp.example.com"
        assert notifier.port == 587

    def test_init_with_missing_config(self):
        """Test initialization with incomplete config."""
        config = {
            "host": "",
            "port": 587,
            "username": "",
            "password": "",
            "from_addr": "",
            "to_addr": "",
        }
        notifier = EmailNotifier(config)

        assert notifier.enabled is False

    def test_init_with_partial_config(self):
        """Test initialization with partial config - missing to_addr."""
        config = {
            "host": "smtp.example.com",
            "port": 587,
            "username": "user",
            "password": "pass",
            "from_addr": "from@example.com",
            "to_addr": "",
        }
        notifier = EmailNotifier(config)

        assert notifier.enabled is False

    @patch("src.email_notifier.smtplib.SMTP")
    def test_send_change_notification(self, mock_smtp):
        """Test sending change notification email."""
        config = {
            "host": "smtp.example.com",
            "port": 587,
            "username": "user",
            "password": "pass",
            "from_addr": "from@example.com",
            "to_addr": "to@example.com",
        }
        notifier = EmailNotifier(config)

        changes = [
            {"type": "status", "old_value": "In process", "new_value": "Accepted", "description": "Status changed"},
        ]

        result = notifier.send_change_notification("account1", "case123", "Immigration", "John", changes)

        assert result is True
        mock_smtp.return_value.ehlo.assert_called()
        mock_smtp.return_value.starttls.assert_called()
        mock_smtp.return_value.login.assert_called()
        mock_smtp.return_value.sendmail.assert_called_once()
        mock_smtp.return_value.quit.assert_called_once()

    @patch("src.email_notifier.smtplib.SMTP")
    def test_send_error_notification(self, mock_smtp):
        """Test sending error notification email."""
        config = {
            "host": "smtp.example.com",
            "port": 587,
            "username": "user",
            "password": "pass",
            "from_addr": "from@example.com",
            "to_addr": "to@example.com",
        }
        notifier = EmailNotifier(config)

        result = notifier.send_error_notification("account1", "case123", "Login failed", "LOGIN_ERROR")

        assert result is True
        mock_smtp.return_value.ehlo.assert_called()
        mock_smtp.return_value.starttls.assert_called()
        mock_smtp.return_value.login.assert_called()
        mock_smtp.return_value.sendmail.assert_called_once()
        mock_smtp.return_value.quit.assert_called_once()

    def test_send_change_notification_disabled(self):
        """Test that email is not sent when disabled."""
        config = {
            "host": "",
            "port": 587,
            "username": "",
            "password": "",
            "from_addr": "",
            "to_addr": "",
        }
        notifier = EmailNotifier(config)

        changes = [{"type": "status", "old_value": "old", "new_value": "new", "description": "test"}]
        result = notifier.send_change_notification("account1", "case123", "Type", "John", changes)

        assert result is False

    @patch("src.email_notifier.smtplib.SMTP")
    def test_send_email_smtp_failure(self, mock_smtp):
        """Test handling SMTP connection failure."""
        mock_smtp.side_effect = Exception("SMTP connection failed")

        config = {
            "host": "smtp.example.com",
            "port": 587,
            "username": "user",
            "password": "pass",
            "from_addr": "from@example.com",
            "to_addr": "to@example.com",
        }
        notifier = EmailNotifier(config)

        changes = [{"type": "status", "old_value": "old", "new_value": "new", "description": "test"}]
        result = notifier.send_change_notification("account1", "case123", "Type", "John", changes)

        assert result is False


class TestEmailNotifierConfig:
    """Tests for email configuration functions."""

    def test_get_email_enabled_true(self, monkeypatch):
        """Test get_email_enabled returns True when set."""
        monkeypatch.setenv("EMAIL_ENABLED", "true")
        import os
        # Force reload of config to pick up new env var
        import importlib
        import src.config
        importlib.reload(src.config)
        from src.config import get_email_enabled

        assert get_email_enabled() is True

    def test_get_email_enabled_false(self, monkeypatch):
        """Test get_email_enabled returns False when unset."""
        monkeypatch.delenv("EMAIL_ENABLED", raising=False)
        import importlib
        import src.config
        importlib.reload(src.config)
        from src.config import get_email_enabled

        assert get_email_enabled() is False

    def test_get_smtp_config(self, monkeypatch):
        """Test get_smtp_config returns correct values."""
        monkeypatch.setenv("SMTP_SERVER", "smtp.test.com")
        monkeypatch.setenv("SMTP_PORT", "587")
        monkeypatch.setenv("SMTP_USERNAME", "user")
        monkeypatch.setenv("SMTP_PASSWORD", "pass")
        monkeypatch.setenv("EMAIL_FROM", "from@test.com")
        monkeypatch.setenv("EMAIL_TO", "to@test.com")

        import importlib
        import src.config
        importlib.reload(src.config)
        from src.config import get_smtp_config

        config = get_smtp_config()

        assert config["host"] == "smtp.test.com"
        assert config["port"] == 587
        assert config["username"] == "user"
        assert config["password"] == "pass"
        assert config["from_addr"] == "from@test.com"
        assert config["to_addr"] == "to@test.com"

    def test_get_smtp_config_defaults(self, monkeypatch):
        """Test get_smtp_config returns defaults when unset."""
        monkeypatch.delenv("SMTP_SERVER", raising=False)
        monkeypatch.delenv("SMTP_PORT", raising=False)
        monkeypatch.delenv("SMTP_USERNAME", raising=False)
        monkeypatch.delenv("SMTP_PASSWORD", raising=False)
        monkeypatch.delenv("EMAIL_FROM", raising=False)
        monkeypatch.delenv("EMAIL_TO", raising=False)

        import importlib
        import src.config
        importlib.reload(src.config)
        from src.config import get_smtp_config

        config = get_smtp_config()

        assert config["host"] == ""
        assert config["port"] == 587
        assert config["username"] == ""
        assert config["password"] == ""
        assert config["from_addr"] == ""
        assert config["to_addr"] == ""
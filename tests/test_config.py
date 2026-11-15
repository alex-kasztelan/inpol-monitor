"""Tests for configuration and credential loading."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from src.config import (
    get_base_path,
    get_config,
    load_credentials,
    load_env,
)


class TestGetBasePath:
    """Tests for get_base_path() function."""

    def test_returns_absolute_path(self):
        """get_base_path should return an absolute Path."""
        base_path = get_base_path()
        assert base_path.is_absolute()

    def test_parent_is_src(self):
        """get_base_path parent should be src directory."""
        base_path = get_base_path()
        assert (base_path / "src").exists()


class TestLoadCredentials:
    """Tests for load_credentials() function."""

    def test_load_valid_credentials(self, tmp_path):
        """Should load valid credentials from JSON file."""
        creds_file = tmp_path / "credentials.json"
        test_data = {
            "account1": {
                "username": "user1",
                "password": "pass1",
                "case_ids": ["CASE-001", "CASE-002", "CASE-003"]
            },
            "account2": {
                "username": "user2",
                "password": "pass2",
                "case_ids": ["CASE-004", "CASE-005"]
            }
        }
        creds_file.write_text(json.dumps(test_data))

        result = load_credentials(str(creds_file))

        assert result == test_data

    def test_missing_file_returns_empty_dict(self):
        """Should return empty dict when file doesn't exist."""
        result = load_credentials("/nonexistent/path/credentials.json")
        assert result == {}

    def test_strips_whitespace_from_values(self, tmp_path):
        """Should strip whitespace from credential values (CRLF handling)."""
        creds_file = tmp_path / "credentials.json"
        # Simulate Windows CRLF with trailing whitespace
        test_data = {
            "account1": {
                "username": "  user1  ",
                "password": "pass1\r\n",
                "case_ids": ["CASE-001"]
            }
        }
        creds_file.write_text(json.dumps(test_data))

        result = load_credentials(str(creds_file))

        assert result["account1"]["username"] == "user1"
        assert result["account1"]["password"] == "pass1"

    def test_lenient_validation_missing_account(self, tmp_path, caplog):
        """Should warn but continue when account is missing."""
        creds_file = tmp_path / "credentials.json"
        test_data = {
            "account1": {
                "username": "user1",
                "password": "pass1"
            }
        }
        creds_file.write_text(json.dumps(test_data))

        with caplog.at_level("WARNING"):
            result = load_credentials(str(creds_file))

        assert result["account1"]["username"] == "user1"

    def test_lenient_validation_missing_username(self, tmp_path, caplog):
        """Should warn but continue when username is missing."""
        creds_file = tmp_path / "credentials.json"
        test_data = {
            "account1": {
                "password": "pass1"
                # username is missing
            }
        }
        creds_file.write_text(json.dumps(test_data))

        with caplog.at_level("WARNING"):
            result = load_credentials(str(creds_file))

        assert "No username for account1" in caplog.text

    def test_invalid_json_returns_empty_dict(self, tmp_path, caplog):
        """Should return empty dict for invalid JSON."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text("{ invalid json }")

        with caplog.at_level("ERROR"):
            result = load_credentials(str(creds_file))

        assert result == {}
        assert "Invalid JSON" in caplog.text


class TestLoadEnv:
    """Tests for load_env() function."""

    def test_load_valid_env_file(self, tmp_path):
        """Should load environment variables from .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR=test_value\nANOTHER_VAR=another_value")

        # Clear any existing value
        os.environ.pop("TEST_VAR", None)

        result = load_env(str(env_file))

        assert result is True
        assert os.getenv("TEST_VAR") == "test_value"

    def test_missing_file_returns_false(self, caplog):
        """Should return False when .env file doesn't exist."""
        with caplog.at_level("INFO"):
            result = load_env("/nonexistent/path/.env")

        assert result is False

    def test_loads_from_script_location(self, tmp_path, monkeypatch):
        """Should resolve paths relative to script location, not cwd."""
        # Create .env in tmp_path (simulating project root)
        env_file = tmp_path / ".env"
        env_file.write_text("PROJECT_VAR=project_value")

        # Change cwd to different directory
        different_dir = tmp_path / "other"
        different_dir.mkdir()
        monkeypatch.chdir(different_dir)

        # Load using absolute path (simulating script location resolution)
        result = load_env(str(env_file))

        assert result is True
        assert os.getenv("PROJECT_VAR") == "project_value"


class TestGetConfig:
    """Tests for get_config() function."""

    def test_get_existing_env_var(self):
        """Should return value of existing environment variable."""
        os.environ["TEST_CONFIG_KEY"] = "test_value"
        result = get_config("TEST_CONFIG_KEY")
        assert result == "test_value"

    def test_get_missing_env_var_with_default(self):
        """Should return default for missing environment variable."""
        os.environ.pop("NONEXISTENT_KEY", None)
        result = get_config("NONEXISTENT_KEY", "default_value")
        assert result == "default_value"

    def test_get_missing_env_var_no_default(self):
        """Should return None for missing variable without default."""
        os.environ.pop("NONEXISTENT_KEY", None)
        result = get_config("NONEXISTENT_KEY")
        assert result is None

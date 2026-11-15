"""Shared test fixtures and configuration."""

import os
import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def clean_environment():
    """Clean environment variables before each test."""
    # Store original environment
    original_env = os.environ.copy()

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def sample_credentials():
    """Sample credentials data for testing."""
    return {
        "account1": {
            "username": "test_user_1",
            "password": "test_pass_1",
            "case_ids": ["CASE-001", "CASE-002", "CASE-003"]
        },
        "account2": {
            "username": "test_user_2",
            "password": "test_pass_2",
            "case_ids": ["CASE-004", "CASE-005"]
        }
    }


@pytest.fixture
def temp_credentials_file(tmp_path, sample_credentials):
    """Create a temporary credentials.json file."""
    import json
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text(json.dumps(sample_credentials))
    return creds_file

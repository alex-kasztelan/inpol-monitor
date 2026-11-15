"""Tests for SnapshotRepository in src/storage.py.

This module contains tests for the SnapshotRepository class.
"""

import json
import os
import sqlite3
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from src.storage import SnapshotRepository, DatabaseMixin
from src.models import Snapshot


@pytest.fixture
def temp_db_file(tmp_path):
    """Create a temporary database file for testing."""
    db_path = tmp_path / "test_snapshots.db"
    db_path.touch()  # Create empty file
    return str(db_path)


@pytest.fixture
def repository(temp_db_file):
    """Create a SnapshotRepository instance for testing."""
    return SnapshotRepository(temp_db_file)


class TestDatabaseMixin:
    """Tests for DatabaseMixin."""

    def test_init_creates_db(self, repository):
        """Database is created and initialized on instantiation."""
        assert os.path.exists(repository.db_path)

    def test_init_creates_table(self, repository):
        """Snapshots table exists after initialization."""
        conn = sqlite3.connect(repository.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='snapshots'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_init_creates_indexes(self, repository):
        """Indexes are created after initialization."""
        conn = sqlite3.connect(repository.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_case_id'")
        assert cursor.fetchone() is not None

        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_timestamp'")
        assert cursor.fetchone() is not None

        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_account_endpoint'")
        assert cursor.fetchone() is not None

        conn.close()


class TestSaveSnapshot:
    """Tests for save_snapshot method."""

    def test_save_snapshot_creates_row(self, repository, temp_db_file):
        """save_snapshot creates new row in database."""
        snapshot = Snapshot(
            account_id="account1",
            case_id="TEST-CASE-1",
            endpoint_type="case_data",
            raw_json={"test": "data"},
            parsed_data={"status": "IN_PROGRESS"},
            timestamp=datetime(2026, 3, 1, 12, 0, 0)
        )

        repository.save_snapshot(snapshot)

        conn = sqlite3.connect(temp_db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM snapshots WHERE case_id='TEST-CASE-1'")
        count = cursor.fetchone()[0]
        assert count == 1
        conn.close()

    def test_save_snapshot_inserts_all_fields(self, repository, temp_db_file):
        """save_snapshot inserts all required fields."""
        snapshot = Snapshot(
            account_id="account1",
            case_id="TEST-CASE-2",
            endpoint_type="attachments",
            raw_json={"attachments": []},
            parsed_data={"count": 0},
            timestamp=datetime(2026, 3, 1, 12, 0, 0)
        )

        repository.save_snapshot(snapshot)

        conn = sqlite3.connect(temp_db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT account_id, case_id, endpoint_type, timestamp FROM snapshots")
        row = cursor.fetchone()
        assert row is not None
        # Handle both tuple and dict-like row
        account_id = row[0] if isinstance(row, tuple) else row["account_id"]
        case_id = row[1] if isinstance(row, tuple) else row["case_id"]
        endpoint_type = row[2] if isinstance(row, tuple) else row["endpoint_type"]
        assert account_id == "account1"
        assert case_id == "TEST-CASE-2"
        assert endpoint_type == "attachments"
        conn.close()

    def test_save_snapshot_uses_json_for_raw_and_parsed(self, repository, temp_db_file):
        """save_snapshot stores raw_json and parsed_data as JSON text."""
        snapshot = Snapshot(
            account_id="account1",
            case_id="TEST-CASE-3",
            endpoint_type="case_data",
            raw_json={"nested": {"key": "value"}},
            parsed_data={"status": "APPROVED", "date": "2026-03-01"},
            timestamp=datetime(2026, 3, 1, 12, 0, 0)
        )

        repository.save_snapshot(snapshot)

        conn = sqlite3.connect(temp_db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT raw_json, parsed_data FROM snapshots")
        row = cursor.fetchone()
        assert row is not None
        # Handle both tuple and dict-like row
        raw_json = row[0] if isinstance(row, tuple) else row["raw_json"]
        parsed_data = row[1] if isinstance(row, tuple) else row["parsed_data"]
        assert raw_json == '{"nested": {"key": "value"}}'
        assert parsed_data == '{"status": "APPROVED", "date": "2026-03-01"}'
        conn.close()

    def test_save_snapshot_does_not_update_existing(self, repository, temp_db_file):
        """save_snapshot inserts new row instead of updating existing."""
        # Save first snapshot
        snapshot1 = Snapshot(
            account_id="account1",
            case_id="TEST-CASE-4",
            endpoint_type="case_data",
            raw_json={"v1": True},
            parsed_data={"status": "IN_PROGRESS"},
            timestamp=datetime(2026, 3, 1, 10, 0, 0)
        )
        repository.save_snapshot(snapshot1)

        # Save second snapshot for same case
        snapshot2 = Snapshot(
            account_id="account1",
            case_id="TEST-CASE-4",
            endpoint_type="case_data",
            raw_json={"v2": True},
            parsed_data={"status": "APPROVED"},
            timestamp=datetime(2026, 3, 1, 12, 0, 0)
        )
        repository.save_snapshot(snapshot2)

        # Verify both rows exist
        conn = sqlite3.connect(temp_db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM snapshots WHERE case_id='TEST-CASE-4'")
        count = cursor.fetchone()[0]
        assert count == 2
        conn.close()


class TestGetLatestSnapshot:
    """Tests for get_latest_snapshot method."""

    def test_get_latest_snapshot_returns_latest(self, repository, temp_db_file):
        """get_latest_snapshot returns most recent snapshot."""
        # Save snapshot 1
        snapshot1 = Snapshot(
            account_id="account1",
            case_id="TEST-CASE-5",
            endpoint_type="case_data",
            raw_json={"ts": "10:00"},
            parsed_data={},
            timestamp=datetime(2026, 3, 1, 10, 0, 0)
        )
        repository.save_snapshot(snapshot1)

        # Save snapshot 2
        snapshot2 = Snapshot(
            account_id="account1",
            case_id="TEST-CASE-5",
            endpoint_type="case_data",
            raw_json={"ts": "12:00"},
            parsed_data={},
            timestamp=datetime(2026, 3, 1, 12, 0, 0)
        )
        repository.save_snapshot(snapshot2)

        # Get latest
        result = repository.get_latest_snapshot("TEST-CASE-5", "case_data")

        assert result is not None
        assert result.raw_json == {"ts": "12:00"}
        assert result.timestamp == datetime(2026, 3, 1, 12, 0, 0)

    def test_get_latest_snapshot_returns_none_when_not_found(self, repository, temp_db_file):
        """get_latest_snapshot returns None when no snapshot exists."""
        result = repository.get_latest_snapshot("NONEXISTENT-CASE", "case_data")
        assert result is None

    def test_get_latest_snapshot_different_endpoint(self, repository, temp_db_file):
        """get_latest_snapshot returns None for different endpoint_type."""
        # Save snapshot for case_data
        snapshot = Snapshot(
            account_id="account1",
            case_id="TEST-CASE-6",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={},
            timestamp=datetime(2026, 3, 1, 12, 0, 0)
        )
        repository.save_snapshot(snapshot)

        # Try to get attachments endpoint
        result = repository.get_latest_snapshot("TEST-CASE-6", "attachments")
        assert result is None


class TestGetSnapshotsByAccount:
    """Tests for get_snapshots_by_account method."""

    def test_get_snapshots_by_account(self, repository, temp_db_file):
        """get_snapshots_by_account returns all snapshots for account."""
        # Save snapshots for account1
        for i in range(3):
            snapshot = Snapshot(
                account_id="account1",
                case_id=f"TEST-CASE-{i}",
                endpoint_type="case_data",
                raw_json={},
                parsed_data={},
                timestamp=datetime(2026, 3, 1, 10, i, 0)
            )
            repository.save_snapshot(snapshot)

        # Save snapshot for account2
        snapshot = Snapshot(
            account_id="account2",
            case_id="TEST-CASE-10",
            endpoint_type="case_data",
            raw_json={},
            parsed_data={},
            timestamp=datetime(2026, 3, 1, 11, 0, 0)
        )
        repository.save_snapshot(snapshot)

        # Get snapshots for account1
        results = repository.get_snapshots_by_account("account1")

        assert len(results) == 3
        all_account1 = all(s.account_id == "account1" for s in results)
        assert all_account1

    def test_get_snapshots_by_account_empty(self, repository, temp_db_file):
        """get_snapshots_by_account returns empty list for account with no snapshots."""
        results = repository.get_snapshots_by_account("nonexistent-account")
        assert results == []


class TestGetAllSnapshots:
    """Tests for get_all_snapshots method."""

    def test_get_all_snapshots(self, repository, temp_db_file):
        """get_all_snapshots returns all snapshots ordered by timestamp."""
        # Save snapshots
        for i in range(3):
            snapshot = Snapshot(
                account_id="account1",
                case_id=f"TEST-CASE-{i}",
                endpoint_type="case_data",
                raw_json={},
                parsed_data={},
                timestamp=datetime(2026, 3, 1, 10, i, 0)
            )
            repository.save_snapshot(snapshot)

        results = repository.get_all_snapshots()

        assert len(results) == 3
        # Should be ordered by timestamp DESC
        assert results[0].timestamp > results[1].timestamp > results[2].timestamp


class TestGetSnapshot:
    """Tests for get_snapshot method."""

    def test_get_snapshot_by_timestamp(self, repository, temp_db_file):
        """get_snapshot returns snapshot by timestamp."""
        snapshot = Snapshot(
            account_id="account1",
            case_id="TEST-CASE-11",
            endpoint_type="case_data",
            raw_json={"ts": "2026-03-01T12:00:00Z"},
            parsed_data={},
            timestamp=datetime(2026, 3, 1, 12, 0, 0)
        )
        repository.save_snapshot(snapshot)

        result = repository.get_snapshot("TEST-CASE-11", "case_data", "2026-03-01T12:00:00")

        assert result is not None
        assert result.raw_json == {"ts": "2026-03-01T12:00:00Z"}

    def test_get_snapshot_not_found(self, repository, temp_db_file):
        """get_snapshot returns None when snapshot not found."""
        result = repository.get_snapshot("TEST-CASE-11", "case_data", "2026-03-01T13:00:00")
        assert result is None


class TestSnapshotRepositoryInit:
    """Tests for SnapshotRepository initialization."""

    def test_init_with_default_path(self, tmp_path):
        """Repository initializes with default database path."""
        # Create a temp directory for the data folder
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        db_path = data_dir / "snapshots.db"
        db_path.touch()

        repo = SnapshotRepository(str(db_path))
        assert repo.db_path == db_path

    def test_init_with_custom_path(self, tmp_path):
        """Repository initializes with custom database path."""
        custom_db = tmp_path / "custom.db"
        custom_db.touch()
        repo = SnapshotRepository(str(custom_db))
        assert repo.db_path == custom_db

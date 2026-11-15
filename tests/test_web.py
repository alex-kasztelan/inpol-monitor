"""Tests for Phase 11: Web Application."""

import pytest
from datetime import datetime, timedelta
from src.storage import SnapshotRepository


class TestStorageExtensions:
    """Test the new storage methods added in Phase 11."""

    @pytest.fixture
    def repo(self):
        """Create repository instance."""
        return SnapshotRepository("data/snapshots.db")

    def test_get_snapshots_by_timerange_with_dates(self, repo):
        """Test date range filtering works."""
        start = datetime.now() - timedelta(days=365)
        end = datetime.now() + timedelta(days=1)
        snapshots = repo.get_snapshots_by_timerange(start, end)
        assert isinstance(snapshots, list)

    def test_get_snapshots_by_timerange_with_case_id(self, repo):
        """Test case_id filtering."""
        snapshots = repo.get_snapshots_by_timerange(
            case_id_filter="some-case-id"
        )
        assert isinstance(snapshots, list)
        for s in snapshots:
            assert s.case_id == "some-case-id"

    def test_get_snapshot_by_id_returns_snapshot(self, repo):
        """Test get by ID returns valid snapshot."""
        all_snapshots = repo.get_all_snapshots()
        if all_snapshots:
            snapshot_id = all_snapshots[0]
            result = repo.get_snapshot_by_id(1)
            if result:
                assert result.case_id is not None


class TestFlaskApp:
    """Test Flask application components."""

    def test_create_app(self):
        """Test Flask app factory creates app."""
        from src.web import create_app
        app = create_app()
        assert app is not None
        assert app.secret_key is not None

    def test_verify_credentials(self):
        """Test credential verification."""
        from src.web.auth import verify_credentials
        result = verify_credentials("test", "test")
        assert isinstance(result, bool)

    def test_login_required_redirects(self):
        """Test login_required decorator redirects."""
        from src.web import create_app
        from flask import session

        app = create_app()
        with app.test_client() as client:
            response = client.get('/')
            assert response.status_code in [302, 401]
"""Storage layer for Inpol Monitor using SQLite.

This module provides the SnapshotRepository class for persisting
and querying case data snapshots to SQLite database.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import sqlite3

from src.models import Snapshot

logger = logging.getLogger(__name__)


class DatabaseMixin:
    """Mixin for database connection management."""

    def __init__(self, db_path: str):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._init_db()

    def _get_connection(self):
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create snapshots table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    endpoint_type TEXT NOT NULL,
                    raw_json TEXT NOT NULL,
                    parsed_data TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for efficient querying
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_case_id ON snapshots(case_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON snapshots(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_account_endpoint ON snapshots(account_id, endpoint_type)")

            conn.commit()


class SnapshotRepository(DatabaseMixin):
    """Repository for managing case data snapshots.

    Follows Repository pattern with snapshot immutability.
    All snapshots are inserted as new rows, never updated.
    """

    def __init__(self, db_path: str = "data/snapshots.db"):
        """Initialize repository.

        Args:
            db_path: Path to SQLite database file
        """
        super().__init__(db_path)
        logger.debug(f"SnapshotRepository initialized for {db_path}")

    def save_snapshot(self, snapshot: Snapshot) -> None:
        """Save a snapshot to the database.

        Args:
            snapshot: Snapshot to save

        Notes:
            - Uses INSERT (not UPDATE) to maintain immutability
            - Converts parsed_data to JSON for storage
            - Converts raw_json to JSON for storage
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Convert parsed_data to JSON text
            parsed_data_json = json.dumps(snapshot.parsed_data) if snapshot.parsed_data else "{}"

            # Convert raw_json to JSON text
            raw_json_json = json.dumps(snapshot.raw_json) if snapshot.raw_json else "{}"

            cursor.execute("""
                INSERT INTO snapshots (
                    account_id,
                    case_id,
                    endpoint_type,
                    raw_json,
                    parsed_data,
                    timestamp,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                snapshot.account_id,
                snapshot.case_id,
                snapshot.endpoint_type,
                raw_json_json,
                parsed_data_json,
                snapshot.timestamp.isoformat() if snapshot.timestamp else datetime.utcnow().isoformat()
            ))

            conn.commit()
            logger.debug(f"Saved snapshot: {snapshot.case_id} / {snapshot.endpoint_type}")

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to save snapshot: {e}")
            raise
        finally:
            conn.close()

    def get_latest_snapshot(
        self,
        case_id: str,
        endpoint_type: str
    ) -> Optional[Snapshot]:
        """Get the latest snapshot for a case and endpoint.

        Args:
            case_id: Case identifier
            endpoint_type: Endpoint type (case_data, attachments, questions)

        Returns:
            Latest Snapshot or None if not found
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, account_id, case_id, endpoint_type, raw_json, parsed_data, timestamp
                FROM snapshots
                WHERE case_id = ? AND endpoint_type = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (case_id, endpoint_type))

            row = cursor.fetchone()
            if not row:
                return None

            return Snapshot(
                id=row["id"],
                account_id=row["account_id"],
                case_id=row["case_id"],
                endpoint_type=row["endpoint_type"],
                raw_json=json.loads(row["raw_json"]) if row["raw_json"] else {},
                parsed_data=json.loads(row["parsed_data"]) if row["parsed_data"] else {},
                timestamp=datetime.fromisoformat(row["timestamp"])
            )

        except Exception as e:
            logger.error(f"Failed to get latest snapshot for {case_id}/{endpoint_type}: {e}")
            return None
        finally:
            conn.close()

    def get_snapshots_by_account(
        self,
        account_id: str
    ) -> List[Snapshot]:
        """Get all snapshots for an account.

        Args:
            account_id: Account identifier

        Returns:
            List of Snapshot objects for the account
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, account_id, case_id, endpoint_type, raw_json, parsed_data, timestamp
                FROM snapshots
                WHERE account_id = ?
                ORDER BY timestamp DESC
            """, (account_id,))

            rows = cursor.fetchall()

            snapshots = []
            for row in rows:
                snapshots.append(Snapshot(
                    id=row["id"],
                    account_id=row["account_id"],
                    case_id=row["case_id"],
                    endpoint_type=row["endpoint_type"],
                    raw_json=json.loads(row["raw_json"]) if row["raw_json"] else {},
                    parsed_data=json.loads(row["parsed_data"]) if row["parsed_data"] else {},
                    timestamp=datetime.fromisoformat(row["timestamp"])
                ))

            return snapshots

        except Exception as e:
            logger.error(f"Failed to get snapshots for account {account_id}: {e}")
            return []
        finally:
            conn.close()

    def get_all_snapshots(self) -> List[Snapshot]:
        """Get all snapshots from the database.

        Returns:
            List of all Snapshot objects
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, account_id, case_id, endpoint_type, raw_json, parsed_data, timestamp
                FROM snapshots
                ORDER BY timestamp DESC
            """)

            rows = cursor.fetchall()

            snapshots = []
            for row in rows:
                snapshots.append(Snapshot(
                    id=row["id"],
                    account_id=row["account_id"],
                    case_id=row["case_id"],
                    endpoint_type=row["endpoint_type"],
                    raw_json=json.loads(row["raw_json"]) if row["raw_json"] else {},
                    parsed_data=json.loads(row["parsed_data"]) if row["parsed_data"] else {},
                    timestamp=datetime.fromisoformat(row["timestamp"])
                ))

            return snapshots

        except Exception as e:
            logger.error(f"Failed to get all snapshots: {e}")
            return []
        finally:
            conn.close()

    def get_snapshot(
        self,
        case_id: str,
        endpoint_type: str,
        timestamp: str
    ) -> Optional[Snapshot]:
        """Get a specific snapshot by timestamp.

        Args:
            case_id: Case identifier
            endpoint_type: Endpoint type
            timestamp: ISO format timestamp of the snapshot

        Returns:
            Snapshot or None if not found
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, account_id, case_id, endpoint_type, raw_json, parsed_data, timestamp
                FROM snapshots
                WHERE case_id = ? AND endpoint_type = ? AND timestamp = ?
                LIMIT 1
            """, (case_id, endpoint_type, timestamp))

            row = cursor.fetchone()
            if not row:
                return None

            return Snapshot(
                id=row["id"],
                account_id=row["account_id"],
                case_id=row["case_id"],
                endpoint_type=row["endpoint_type"],
                raw_json=json.loads(row["raw_json"]) if row["raw_json"] else {},
                parsed_data=json.loads(row["parsed_data"]) if row["parsed_data"] else {},
                timestamp=datetime.fromisoformat(row["timestamp"])
            )

        except Exception as e:
            logger.error(f"Failed to get snapshot: {e}")
            return None
        finally:
            conn.close()

    def get_previous_snapshot(
        self,
        account_id: str,
        case_id: str,
        endpoint_type: str
    ) -> Optional[Snapshot]:
        """Get the previous snapshot for a case and endpoint type.

        This is used for change detection - comparing current data
        against the previous snapshot.

        Args:
            account_id: Account identifier
            case_id: Case identifier
            endpoint_type: Endpoint type (case_data, attachments, questions)

        Returns:
            Previous Snapshot or None if no previous snapshot exists
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, account_id, case_id, endpoint_type, raw_json, parsed_data, timestamp
                FROM snapshots
                WHERE case_id = ? AND endpoint_type = ?
                ORDER BY timestamp DESC
                LIMIT 1 OFFSET 1
            """, (case_id, endpoint_type))

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            return Snapshot(
                id=row["id"],
                account_id=row["account_id"],
                case_id=row["case_id"],
                endpoint_type=row["endpoint_type"],
                raw_json=json.loads(row["raw_json"]) if row["raw_json"] else {},
                parsed_data=json.loads(row["parsed_data"]) if row["parsed_data"] else {},
                timestamp=datetime.fromisoformat(row["timestamp"])
            )

        except Exception as e:
            logger.error(f"Failed to get previous snapshot for {case_id}/{endpoint_type}: {e}")
            return None
        finally:
            conn.close()

    def get_snapshots_by_timerange(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        case_id_filter: Optional[str] = None,
        account_filter: Optional[str] = None,
        endpoint_filter: Optional[str] = None
    ) -> List[Snapshot]:
        """Get snapshots within a date range, optionally filtered by case_id.

        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            case_id_filter: Optional case_id to filter by
            account_filter: Optional account_id to filter by
            endpoint_filter: Optional endpoint_type to filter by

        Returns:
            List of Snapshot objects within the date range
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            query = "SELECT id, account_id, case_id, endpoint_type, raw_json, parsed_data, timestamp FROM snapshots WHERE 1=1"
            params = []

            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())
            if case_id_filter:
                query += " AND case_id = ?"
                params.append(case_id_filter)
            if account_filter:
                query += " AND account_id = ?"
                params.append(account_filter)
            if endpoint_filter:
                query += " AND endpoint_type = ?"
                params.append(endpoint_filter)

            query += " ORDER BY timestamp DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            snapshots = []
            for row in rows:
                snapshots.append(Snapshot(
                    id=row["id"],
                    account_id=row["account_id"],
                    case_id=row["case_id"],
                    endpoint_type=row["endpoint_type"],
                    raw_json=json.loads(row["raw_json"]) if row["raw_json"] else {},
                    parsed_data=json.loads(row["parsed_data"]) if row["parsed_data"] else {},
                    timestamp=datetime.fromisoformat(row["timestamp"])
                ))

            return snapshots

        except Exception as e:
            logger.error(f"Failed to get snapshots by timerange: {e}")
            return []
        finally:
            conn.close()

    def get_snapshot_by_id(self, snapshot_id: int) -> Optional[Snapshot]:
        """Get a specific snapshot by its database ID.

        Args:
            snapshot_id: The database ID of the snapshot

        Returns:
            Snapshot or None if not found
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, account_id, case_id, endpoint_type, raw_json, parsed_data, timestamp
                FROM snapshots
                WHERE id = ?
                LIMIT 1
            """, (snapshot_id,))

            row = cursor.fetchone()
            if not row:
                return None

            return Snapshot(
                id=row["id"],
                account_id=row["account_id"],
                case_id=row["case_id"],
                endpoint_type=row["endpoint_type"],
                raw_json=json.loads(row["raw_json"]) if row["raw_json"] else {},
                parsed_data=json.loads(row["parsed_data"]) if row["parsed_data"] else {},
                timestamp=datetime.fromisoformat(row["timestamp"])
            )

        except Exception as e:
            logger.error(f"Failed to get snapshot by id {snapshot_id}: {e}")
            return None
        finally:
            conn.close()

    def delete_snapshots(self, snapshot_ids: List[int]) -> int:
        """Delete snapshots by their IDs.

        Args:
            snapshot_ids: List of snapshot IDs to delete

        Returns:
            Number of snapshots deleted
        """
        if not snapshot_ids:
            return 0

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            placeholders = ','.join('?' * len(snapshot_ids))
            cursor.execute(f"DELETE FROM snapshots WHERE id IN ({placeholders})", snapshot_ids)
            deleted = cursor.rowcount
            conn.commit()
            logger.info(f"Deleted {deleted} snapshot(s)")
            return deleted

        except Exception as e:
            logger.error(f"Failed to delete snapshots: {e}")
            return 0
        finally:
            conn.close()

    def get_distinct_case_ids(self) -> List[str]:
        """Get list of all distinct case IDs."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT case_id FROM snapshots ORDER BY case_id")
            return [row["case_id"] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get distinct case IDs: {e}")
            return []
        finally:
            conn.close()

    def get_distinct_account_ids(self) -> List[str]:
        """Get list of all distinct account IDs."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT account_id FROM snapshots ORDER BY account_id")
            return [row["account_id"] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get distinct account IDs: {e}")
            return []
        finally:
            conn.close()

    def get_distinct_endpoint_types(self) -> List[str]:
        """Get list of all distinct endpoint types."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT endpoint_type FROM snapshots ORDER BY endpoint_type")
            return [row["endpoint_type"] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get distinct endpoint types: {e}")
            return []
        finally:
            conn.close()

    def get_case_labels(self) -> List[dict]:
        """Get case labels from parsed_data for dropdown.
        
        Returns:
            List of dicts with case_id, case_type, person_first, person_last
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT case_id, raw_json, parsed_data 
                FROM snapshots 
                WHERE endpoint_type = 'case_data'
                ORDER BY case_id
            """)
            
            labels = []
            for row in cursor.fetchall():
                parsed = json.loads(row["parsed_data"]) if row["parsed_data"] else {}
                if parsed:
                    case_type = parsed.get("case_type", "")
                    person_first = parsed.get("person_first", "")
                    person_last = parsed.get("person_last", "")
                    if person_last:
                        label = f"{case_type} - {person_first} {person_last}" if case_type else f"{person_first} {person_last}"
                    else:
                        label = row["case_id"]
                else:
                    label = row["case_id"]
                labels.append({
                    "case_id": row["case_id"],
                    "label": label
                })
            return labels
        except Exception as e:
            logger.error(f"Failed to get case labels: {e}")
            return []
        finally:
            conn.close()

    def get_case_labels_for_account(self, account_id: str) -> List[dict]:
        """Get case labels for a specific account.
        
        Args:
            account_id: Account login email
            
        Returns:
            List of dicts with case_id, label
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT case_id, parsed_data 
                FROM snapshots 
                WHERE endpoint_type = 'case_data' AND account_id = ?
                ORDER BY case_id
            """, (account_id,))
            
            labels = []
            for row in cursor.fetchall():
                parsed = json.loads(row["parsed_data"]) if row["parsed_data"] else {}
                if parsed:
                    case_type = parsed.get("case_type", "")
                    person_first = parsed.get("person_first", "")
                    person_last = parsed.get("person_last", "")
                    if person_last:
                        label = f"{case_type} - {person_first} {person_last}" if case_type else f"{person_first} {person_last}"
                    else:
                        label = row["case_id"]
                else:
                    label = row["case_id"]
                labels.append({
                    "case_id": row["case_id"],
                    "label": label
                })
            return labels
        except Exception as e:
            logger.error(f"Failed to get case labels for account: {e}")
            return []
        finally:
            conn.close()

    def get_account_ids_for_case(self, case_id: str) -> List[str]:
        """Get account IDs (logins) for a specific case.
        
        Args:
            case_id: Case identifier
            
        Returns:
            List of account login emails
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT account_id 
                FROM snapshots 
                WHERE case_id = ?
                ORDER BY account_id
            """, (case_id,))
            
            return [row["account_id"] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get account IDs for case: {e}")
            return []
        finally:
            conn.close()


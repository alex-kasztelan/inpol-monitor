---
phase: 03-data-storage
plan: 01
type: tdd
wave: 1
depends_on: [02-PLAN.md]
files_modified:
  - data/snapshots.db
  - src/storage.py
  - src/models.py
  - tests/test_storage.py
autonomous: false
user_setup:
  - service: inpol_mazowieckie_pl
    why: "Authentication required to fetch real case data for testing"
    env_vars:
      - name: INPOL_USERNAME_ACCOUNT1
        source: "Credentials file -> Account 1 username"
      - name: INPOL_PASSWORD_ACCOUNT1
        source: "Credentials file -> Account 1 password"
      - name: INPOL_USERNAME_ACCOUNT2
        source: "Credentials file -> Account 2 username"
      - name: INPOL_PASSWORD_ACCOUNT2
        source: "Credentials file -> Account 2 password"
must_haves:
  truths:
    - "Snapshots are persisted to SQLite database with timestamps"
    - "Latest snapshot can be queried by (case_id, endpoint_type)"
    - "Previous snapshot is available for change detection comparison"
    - "All historical snapshots are retained (INSERT only, no UPDATE)"
  artifacts:
    - path: "data/snapshots.db"
      provides: "SQLite database with snapshots table and indexes"
      exports: ["snapshots table", "idx_case_id index", "idx_timestamp index", "idx_account_endpoint index"]
    - path: "src/storage.py"
      provides: "SnapshotRepository implementation"
      exports: ["DatabaseMixin", "SnapshotRepository"]
    - path: "src/models.py"
      provides: "Pydantic Snapshot model"
      contains: ["Snapshot", "from_json_snapshot"]
  key_links:
    - from: "src/storage.py"
      to: "data/snapshots.db"
      via: "SQLite connection via DatabaseMixin"
      pattern: "sqlite3\\.connect|DatabaseMixin"
    - from: "src/storage.py"
      to: "src/models.py"
      via: "Snapshot model serialization/deserialization"
      pattern: "Snapshot\\(|json\\.loads"
    - from: "src/storage.py"
      to: "src/scraper.py"
      via: "Snapshot creation and persistence"
      pattern: "Snapshot\\(|storage\\.save_snapshot"
---

<objective>
Initialize SQLite database and verify SnapshotRepository can persist and retrieve real case data from inpol.mazowieckie.pl
Purpose: Phase 02 created SnapshotRepository but it was never tested with live data. This plan validates the storage layer works end-to-end.
Output: Database file with test snapshots, verified CRUD operations, working test suite
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/02-data-extraction/02-SUMMARY.md
@src/models.py
@src/storage.py

# Phase 03 Requirement IDs (from ROADMAP):
- DETECT-01: Compare current vs previous snapshot
- DETECT-02: Detect status changes, new documents, date modifications

# Key Decisions from CONTEXT.md:
- D-01: Query latest by (case_id, endpoint_type)
- D-02: Compare both raw JSON and parsed data
- D-03: Batch notifications, one per check time
- D-04: Database at data/snapshots.db in project root
- D-05: INSERT-only snapshots (immutability)
</context>

<tasks>

<!-- Wave 0: Write failing tests for storage layer -->
<!-- TDD: Define expected behavior before implementation -->
<task type="tdd">
  <name>Task 0: Write failing tests for SnapshotRepository</name>
  <files>tests/test_storage.py</files>
  <behavior>
    - Test 1: Save snapshot → 200 OK with row count 1
    - Test 2: Get latest snapshot for valid case_id/endpoint_type → Snapshot with correct fields
    - Test 3: Get latest snapshot for non-existent case → None
    - Test 4: Get previous snapshot when only 1 snapshot exists → previous snapshot returned
    - Test 5: Save snapshot again → INSERT (not UPDATE), row count increases by 1
    - Test 6: Get snapshot by timestamp → correct snapshot returned
    - Test 7: Get all snapshots for account → all snapshots ordered by timestamp DESC
  </behavior>
  <action>
    Update tests/test_storage.py with comprehensive test cases that exercise all SnapshotRepository methods:
    
    1. TestSaveSnapshot creates database file, inserts snapshot with INSERT, returns row count 1, uses json.dumps for raw_json and parsed_data
    
    2. TestGetLatestSnapshot queries by (case_id, endpoint_type), ORDER BY timestamp DESC, LIMIT 1, returns Snapshot with deserialized raw_json and parsed_data
    
    3. TestGetSnapshotByTimestamp queries by case_id, endpoint_type, timestamp
    
    4. TestGetPreviousSnapshot gets the previous snapshot for change detection
    
    5. TestSaveDuplicateInserts saves same snapshot twice, verifies second insert (not update), row count increases by 1
    
    6. TestGetAllSnapshots returns all snapshots for account ordered by timestamp DESC
    
    7. TestDatabaseInitialization ensures data/snapshots.db is created with correct schema (snapshots table, 3 indexes)
    
    Use Pydantic Snapshot model for test fixtures. Use mock SessionManager to avoid authentication overhead.
  </action>
  <verify>
    python -m pytest tests/test_storage.py::test_database_initialization -v -x
  </verify>
  <done>
    Test file updated with 7+ comprehensive tests, test runs and fails (RED phase)
  </done>
</task>

<!-- Wave 1: Initialize database and save real snapshots -->
<!-- Verifies D-04, D-05, D-01 -->
<task type="auto">
  <name>Task 1: Initialize database and save real snapshots</name>
  <files>data/snapshots.db, src/storage.py, src/models.py</files>
  <action>
    Implement SnapshotRepository methods to persist and retrieve real data:
    
    1. Create data/snapshots.db (creates snapshots table with columns: id, account_id, case_id, endpoint_type, raw_json, parsed_data, timestamp, created_at)
    
    2. Create DatabaseMixin with:
       - _get_connection() — sqlite3 with row_factory=sqlite3.Row
       - _init_db() — creates snapshots table + 3 indexes (idx_case_id, idx_timestamp, idx_account_endpoint)
    
    3. Implement SnapshotRepository with:
       - save_snapshot(snapshot) — INSERT INTO snapshots, json.dumps for raw_json/parsed_data, returns None (immutable)
       - get_latest_snapshot(case_id, endpoint_type) — SELECT ... WHERE case_id=? AND endpoint_type=? ORDER BY timestamp DESC LIMIT 1
       - get_previous_snapshot(account_id, case_id, endpoint_type) — Same query as get_latest_snapshot for change detection
       - get_snapshot(case_id, endpoint_type, timestamp) — SELECT by specific timestamp
       - get_snapshots_by_account(account_id) — SELECT ... WHERE account_id=? ORDER BY timestamp DESC
       - get_all_snapshots() — SELECT all ordered by timestamp DESC
    
    4. Create test fixtures to save real snapshots using SessionManager to authenticate, InpolScraper to fetch case data, then persist to storage
    
    5. Save snapshots for at least 2 accounts with multiple cases each to demonstrate persistence history
  </action>
  <verify>
    python -m pytest tests/test_storage.py -v -x
  </verify>
  <done>
    data/snapshots.db created with snapshots table and indexes, all tests pass (46 tests), real snapshots persisted for multiple cases
  </done>
</task>

<!-- Wave 1: Verify change detection with stored snapshots -->
<!-- Verifies D-01, D-02, D-05 -->
<task type="auto">
  <name>Task 2: Verify change detection using stored snapshots</name>
  <files>data/snapshots.db, src/storage.py</files>
  <action>
    Implement end-to-end verification that change detection works with persisted data:
    
    1. Load snapshots from data/snapshots.db for a specific case
    
    2. Fetch the same case again (simulate new check)
    
    3. Compare current snapshot against stored previous snapshot:
       - raw_json comparison (D-02: compare raw JSON)
       - parsed_data comparison (D-02: compare parsed fields)
       - Detect differences in status, dates, documents
    
    4. Verify get_previous_snapshot() returns correct previous snapshot
    
    5. Verify get_latest_snapshot() returns the newly fetched snapshot
    
    6. Demonstrate that INSERT-only pattern (D-05) works: old snapshot remains in database unchanged
    
    7. Show both raw JSON diff and parsed data diff
  </action>
  <verify>
    python -m pytest tests/test_storage.py::test_change_detection_with_stored_snapshots -v
  </verify>
  <done>
    Change detection verified: previous snapshot retrieved, raw_json and parsed_data compared, INSERT-only pattern works, old snapshot unchanged in database
  </done>
</task>

</tasks>

<verification>
<!-- End-to-end verification of storage layer -->
1. Database file exists: `ls data/snapshots.db`
2. Schema verification: `sqlite3 data/snapshots.db ".schema snapshots"`
3. Indexes verified: `sqlite3 data/snapshots.db ".indexes snapshots"`
4. Snapshot count: `sqlite3 data/snapshots.db "SELECT COUNT(*) FROM snapshots"` (should be > 1)
5. Latest snapshot query: `sqlite3 data/snapshots.db "SELECT * FROM snapshots ORDER BY timestamp DESC LIMIT 1"`
6. Previous snapshot query: `sqlite3 data/snapshots.db "SELECT * FROM snapshots ORDER BY timestamp DESC LIMIT 1 OFFSET 1"`
7. All 46 tests pass (17 storage tests)
</verification>

<success_criteria>
- data/snapshots.db file exists and contains snapshots table with 3 indexes
- get_latest_snapshot(case_id, endpoint_type) returns correct Snapshot object with deserialized data
- get_previous_snapshot(account_id, case_id, endpoint_type) returns correct previous snapshot for change detection
- get_all_snapshots(account_id) returns all snapshots for account ordered by timestamp DESC
- get_snapshot(case_id, endpoint_type, timestamp) returns snapshot by specific timestamp
- All INSERT operations use INSERT (not UPDATE) — immutability verified
- All historical snapshots retained (old snapshots unchanged in database)
- 46 tests pass (11 model + 18 scraper + 17 storage tests)
- Raw JSON preserved in database for detailed comparison
- Parsed data stored alongside raw JSON for fast comparison
</success_criteria>

<output>
After completion, create `.planning/phases/03-data-storage/03-SUMMARY.md`
</output>

<tool_call>
<function=Write>
<parameter=file_path>
C:\Prjs\Claude\InpolPub\.planning\phases\03-data-storage\03-VERIFICATION-PLAN.md
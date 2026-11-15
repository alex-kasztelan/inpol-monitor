---
phase: 03-data-storage
plan: 03
type: tdd
wave: 1
depends_on: [02-PLAN.md]
files_modified:
  - data/snapshots.db
  - tests/test_storage.py
autonomous: false
user_setup:
  - service: inpol_mazowieckie_pl
    why: "Authentication required to fetch real case data for database initialization"
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
    - "Snapshots are persisted to data/snapshots.db with timestamps"
    - "Latest snapshot query returns correct data by (case_id, endpoint_type)"
    - "Previous snapshot is available for change detection comparison"
    - "All historical snapshots retained (INSERT only, no UPDATE)"
  artifacts:
    - path: "data/snapshots.db"
      provides: "SQLite database with snapshots table and 3 indexes"
      contains: ["snapshots table", "idx_case_id", "idx_timestamp", "idx_account_endpoint"]
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
      pattern: "sqlite3.connect|DatabaseMixin"
    - from: "src/storage.py"
      to: "src/models.py"
      via: "Snapshot serialization/deserialization"
      pattern: "json.dumps|json.loads|Snapshot("
    - from: "src/storage.py"
      to: "src/scraper.py"
      via: "Snapshot creation and persistence"
      pattern: "Snapshot|storage.save_snapshot"
---

<objective>
Write TDD tests and initialize real database with actual case snapshots from inpol.mazowieckie.pl
Purpose: Phase 02 created SnapshotRepository but it was never tested with live data. This plan validates the storage layer persists real case data.
Output: data/snapshots.db with real snapshots, comprehensive tests, verified CRUD operations
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

<!-- Wave 0: Write failing tests to define expected behavior -->
<task type="tdd">
  <name>Task 0: Write failing tests for snapshot persistence</name>
  <files>tests/test_storage.py</files>
  <behavior>
    - Test 1: Save snapshot → 200 OK with row count 1
    - Test 2: Get latest snapshot by (case_id, endpoint_type) → Snapshot with deserialized raw_json and parsed_data
    - Test 3: Get latest snapshot for non-existent case → None
    - Test 4: Insert duplicate snapshot → INSERT (not UPDATE), row count increases by 1
    - Test 5: Get snapshots by account → all snapshots ordered by timestamp DESC
    - Test 6: Get snapshot by timestamp → correct snapshot returned
    - Test 7: Get previous snapshot for change detection → returns previous snapshot
    - Test 8: Raw JSON and parsed data preserved in database for comparison
  </behavior>
  <action>
    Update tests/test_storage.py with comprehensive tests:
    
    1. test_save_snapshot_creates_row - Creates database, saves snapshot, verifies row count 1
    
    2. test_get_latest_snapshot_returns_real_data - Saves snapshot via real API, retrieves and verifies raw_json and parsed_data are correctly deserialized
    
    3. test_get_latest_snapshot_nonexistent_case - Returns None when no snapshot exists
    
    4. test_insert_not_update - Saves same snapshot twice, verifies second insert (row count = 2), not update
    
    5. test_get_snapshots_by_account_multiple_cases - Saves snapshots for multiple cases, retrieves all for account
    
    6. test_get_snapshot_by_timestamp - Retrieves specific snapshot by timestamp
    
    7. test_get_previous_snapshot_for_change_detection - Retrieves previous snapshot for comparing against current
    
    8. test_raw_json_and_parsed_data_preserved - Verifies both raw JSON and parsed data persist correctly for comparison
    
    Tests should use real API calls to ensure data/snapshots.db is created. Use SessionManager to authenticate.
  </action>
  <verify>
    python -m pytest tests/test_storage.py::test_save_snapshot_creates_row -v -x
  </verify>
  <done>
    Test file updated with 8 comprehensive tests, tests run and fail (RED phase)
  </done>
</task>

<!-- Wave 1: Initialize database with real snapshots -->
<task type="auto">
  <name>Task 1: Initialize database with real case snapshots</name>
  <files>data/snapshots.db, src/storage.py, src/models.py, src/scraper.py</files>
  <action>
    Implement end-to-end database initialization:
    
    1. Load credentials from credentials.json (Account 1 and Account 2)
    
    2. Authenticate both accounts using SessionManager (already implemented in Phase 02)
    
    3. For each case (5 cases: 3 in account 1, 2 in account 2):
       - Fetch case_data endpoint using InpolScraper
       - Fetch attachments endpoint
       - Fetch questions endpoint
       - Fetch i18n status dictionary
       - Create Snapshot from raw JSON and parsed data
       - Call storage.save_snapshot() to persist to data/snapshots.db
    
    4. Verify data/snapshots.db is created with:
       - snapshots table (id, account_id, case_id, endpoint_type, raw_json, parsed_data, timestamp, created_at)
       - 3 indexes (idx_case_id, idx_timestamp, idx_account_endpoint)
       - At least 14 snapshots (5 cases × 3 endpoints = 15, may have some failures)
    
    5. Verify INSERT-only: Save same snapshot twice, confirm row count increases by 1 (not UPDATE)
    
    6. Verify queries work: get_latest_snapshot, get_snapshots_by_account, get_previous_snapshot
  </action>
  <verify>
    python -m pytest tests/test_storage.py -v --tb=short
  </verify>
  <done>
    data/snapshots.db created with real snapshots, 40+ tests pass, database schema correct with 3 indexes, INSERT-only pattern works
  </done>
</task>

</tasks>

<verification>
<!-- End-to-end database verification -->
1. Database file exists: `test -f data/snapshots.db`
2. Schema correct: `sqlite3 data/snapshots.db ".schema snapshots"`
3. Indexes verified: `sqlite3 data/snapshots.db ".indexes snapshots"`
4. Snapshot count: `sqlite3 data/snapshots.db "SELECT COUNT(*) FROM snapshots"` (expect ~14-15)
5. Latest snapshot: `sqlite3 data/snapshots.db "SELECT account_id, case_id, endpoint_type, timestamp FROM snapshots ORDER BY timestamp DESC LIMIT 3"`
6. All 40+ tests pass

<!-- SQLite queries to verify -->
```sql
-- Check table schema
.schema snapshots

-- Verify indexes exist
SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%';

-- Count snapshots per account
SELECT account_id, COUNT(*) FROM snapshots GROUP BY account_id;

-- Latest snapshot per case
SELECT case_id, endpoint_type, MAX(timestamp) FROM snapshots GROUP BY case_id, endpoint_type;

-- Verify INSERT (not UPDATE) - old snapshot still exists
SELECT * FROM snapshots WHERE case_id='TEST-CASE-1';
```
</verification>

<success_criteria>
- data/snapshots.db file exists in project root
- snapshots table created with correct schema (8 columns)
- 3 indexes exist: idx_case_id, idx_timestamp, idx_account_endpoint
- ~14-15 snapshots persisted for 5 cases across 2 accounts
- get_latest_snapshot(case_id, endpoint_type) returns Snapshot with deserialized raw_json and parsed_data
- get_snapshots_by_account(account_id) returns all snapshots for account ordered by timestamp DESC
- get_previous_snapshot(account_id, case_id, endpoint_type) returns previous snapshot for change detection
- get_snapshot(case_id, endpoint_type, timestamp) returns snapshot by specific timestamp
- INSERT-only pattern verified: old snapshots remain in database unchanged
- 40+ tests pass (17 storage tests, 18 scraper tests, 11 model tests)
- Raw JSON preserved for detailed comparison with parsed data
- Status labels resolved via i18n dictionary
</success_criteria>

<output>
After completion, create `.planning/phases/03-data-storage/03-SUMMARY.md`
</output>

<tool_call>
<function=Write>
<parameter=file_path>
C:\Prjs\Claude\InpolPub\.planning\phases/03-data-storage/03-VERIFY-PLAN.md
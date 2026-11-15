---
phase: 03-data-storage
plan: 03
type: execute
wave: 1
depends_on: [02-PLAN.md]
files_modified:
  - src/storage.py
  - data/snapshots.db
  - tests/test_storage.py
autonomous: false
requirements: [STORE-01, STORE-02]
user_setup:
  - service: inpol_mazowieckie_pl
    why: "Authentication required to fetch real case data for storage layer verification"
    env_vars:
      - name: INPOL_USERNAME_ACCOUNT1
        source: "credentials.json -> Account 1 username"
      - name: INPOL_PASSWORD_ACCOUNT1
        source: "credentials.json -> Account 1 password"
      - name: INPOL_USERNAME_ACCOUNT2
        source: "credentials.json -> Account 2 username"
      - name: INPOL_PASSWORD_ACCOUNT2
        source: "credentials.json -> Account 2 password"
must_haves:
  truths:
    - "Snapshots persist to SQLite in data/snapshots.db with all fields"
    - "Querying returns Snapshot objects with raw JSON and parsed data"
    - "Latest snapshot retrieval uses (case_id, endpoint_type) per D-01"
    - "Historical snapshots retained indefinitely (INSERT-only, no UPDATE) per D-05"
  artifacts:
    - path: "src/storage.py"
      provides: "SnapshotRepository CRUD operations"
      exports: ["SnapshotRepository", "save_snapshot", "get_latest_snapshot", "get_previous_snapshot", "get_snapshots_by_account", "get_snapshot", "get_all_snapshots"]
    - path: "data/snapshots.db"
      provides: "SQLite database with snapshots table and indexes"
    - path: "tests/test_storage.py"
      provides: "Comprehensive storage layer tests"
  key_links:
    - from: "src/storage.py"
      to: "src/models.py"
      via: "Snapshot model for data transfer objects"
      pattern: "Snapshot\\("
    - from: "src/storage.py"
      to: "src/scraper.py"
      via: "SnapshotRepository injection in fetch_all_cases"
      pattern: "storage\\.(save|get_latest)"
---

<objective>
Verify existing SnapshotRepository implementation and initialize database with real case data from inpol.mazowieckie.pl
Purpose: The SnapshotRepository was implemented in Phase 02 but Phase 03 was created to document and verify the implementation against STORE-01 (save snapshots) and STORE-02 (retain historical snapshots) requirements.
Output: Verified database implementation with real snapshots, comprehensive tests
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/02-data-extraction/02-SUMMARY.md
@src/models.py
@src/storage.py

# Key Decisions (from CONTEXT.md):
- D-01: Query latest by (case_id, endpoint_type)
- D-02: Compare both raw JSON and parsed data
- D-03: Batch notifications, one per check time
- D-04: Database at data/snapshots.db in project root
- D-05: INSERT-only snapshots (immutability)
</context>

<interfaces>
From src/models.py:
```python
class Snapshot(BaseModel):
    account_id: str
    case_id: str
    endpoint_type: str
    raw_json: dict
    parsed_data: dict
    timestamp: datetime
```

From src/storage.py:
- `DatabaseMixin(db_path)` - SQLite connection management with row_factory
- `SnapshotRepository(db_path)` - Repository following Repository pattern
- `save_snapshot(snapshot)` - INSERT new snapshot
- `get_latest_snapshot(case_id, endpoint_type)` - SELECT latest (per D-01)
- `get_previous_snapshot(account_id, case_id, endpoint_type)` - SELECT previous for comparison
- `get_snapshots_by_account(account_id)` - SELECT by account
- `get_snapshot(case_id, endpoint_type, timestamp)` - SELECT by timestamp
- `get_all_snapshots()` - SELECT all
</interfaces>

</context>

<tasks>

<!-- Wave 1: Verify SnapshotRepository implementation details -->
<task type="auto" tdd="true">
  <name>Task 0: Verify SnapshotRepository implementation against requirements</name>
  <files>src/storage.py, src/models.py, data/snapshots.db</files>
  <behavior>
    - Verify save_snapshot() uses INSERT (not UPDATE) per D-05
    - Verify get_latest_snapshot() queries by (case_id, endpoint_type) per D-01
    - Confirm raw_json and parsed_data are stored as TEXT JSON
    - Verify database path is data/snapshots.db per D-04
    - Confirm indexes exist for case_id, timestamp, account_id+endpoint_type
  </behavior>
  <action>
    Verify existing src/storage.py implementation:
    
    1. Check save_snapshot() uses `INSERT INTO snapshots (...) VALUES (...)` (no UPDATE)
    
    2. Verify get_latest_snapshot() query uses: `WHERE case_id=? AND endpoint_type=? ORDER BY timestamp DESC LIMIT 1`
    
    3. Confirm raw_json and parsed_data are stored as TEXT using json.dumps()
    
    4. Verify database path defaults to "data/snapshots.db"
    
    5. Check database has 3 indexes: idx_case_id, idx_timestamp, idx_account_endpoint
    
    6. Verify Snapshot model has all fields: account_id, case_id, endpoint_type, raw_json, parsed_data, timestamp
    
    7. Confirm JSON deserialization uses json.loads() for raw_json and parsed_data
    
    8. Confirm timestamp storage uses isoformat() and retrieval uses datetime.fromisoformat()
    
    Test commands:
    - python -c "from src.storage import SnapshotRepository; r = SnapshotRepository(); print('Default path:', r.db_path)"
    - python -c "import re; from src.storage import SnapshotRepository; r = SnapshotRepository(); src = inspect.getsource(r.save_snapshot); print('Uses INSERT:', 'INSERT' in src and 'UPDATE' not in src)"
  </action>
  <verify>
    python -c "
from src.storage import SnapshotRepository, Snapshot
from src.models import from_json_snapshot
import json

# Verify import and instantiation
r = SnapshotRepository()
assert r.db_path == 'data/snapshots.db', f'Default db path incorrect: {r.db_path}'

# Verify Snapshot model fields
s = from_json_snapshot('acc1', 'case1', 'case_data', {'test': 'data'})
assert hasattr(s, 'account_id')
assert hasattr(s, 'case_id')
assert hasattr(s, 'endpoint_type')
assert hasattr(s, 'raw_json')
assert hasattr(s, 'parsed_data')
assert hasattr(s, 'timestamp')

# Verify repository methods exist
methods = ['save_snapshot', 'get_latest_snapshot', 'get_previous_snapshot', 
           'get_snapshots_by_account', 'get_snapshot', 'get_all_snapshots']
for m in methods:
    assert hasattr(r, m), f'Missing method: {m}'

print('All imports and method checks passed')
"
  </verify>
  <done>
    SnapshotRepository implements all 6 CRUD methods with INSERT-only persistence per D-05
    All 17 storage tests pass
    Database has correct schema with 3 indexes
  </done>
</task>

<!-- Wave 1: Verify database schema and real data -->
<task type="auto">
  <name>Task 1: Verify database schema and real snapshots</name>
  <files>src/storage.py, data/snapshots.db</files>
  <action>
    Verify database schema and existing real data:
    
    1. Check snapshots table has all columns: id, account_id, case_id, endpoint_type, raw_json, parsed_data, timestamp, created_at
    
    2. Verify indexes exist: idx_case_id, idx_timestamp, idx_account_endpoint
    
    3. Check current record count (should be > 0 from Phase 02)
    
    4. Verify INSERT-only: Save same snapshot twice, confirm row count increases by 1
    
    5. Verify queries work with real data:
       - get_latest_snapshot() returns latest snapshot for case_id/endpoint_type
       - get_previous_snapshot() returns previous snapshot for comparison
       - get_all_snapshots() returns all snapshots ordered by timestamp DESC
    
    6. Confirm JSON deserialization: raw_json and parsed_data are Python dicts, not strings
    
    Test commands:
    - python -m sqlite3 data/snapshots.db ".schema snapshots"
    - python -m sqlite3 data/snapshots.db ".indices snapshots"
    - python -c "import sqlite3; c=sqlite3.connect('data/snapshots.db'); print(f'Records: {c.execute(\"SELECT COUNT(*) FROM snapshots\").fetchone()[0]}')"
  </action>
  <verify>
    python -m sqlite3 "C:/Prjs/Claude/Inpol/data/snapshots.db" <<'EOF'
.mode column
.headers on

-- Verify table structure
SELECT name, sql FROM sqlite_master WHERE type='table' AND name='snapshots';

-- Verify indexes
SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='snapshots';

-- Count records
SELECT COUNT(*) FROM snapshots;
EOF
  </verify>
  <done>
    Database schema verified with all columns and 3 indexes
    Real snapshots exist in data/snapshots.db (from Phase 02)
    CRUD operations verified with existing real data
  </done>
</task>

<!-- Wave 1: End-to-end CRUD verification with real data -->
<task type="auto">
  <name>Task 2: End-to-end CRUD verification with real data</name>
  <files>src/storage.py, src/models.py</files>
  <action>
    Test full CRUD cycle with real database:
    
    1. Connect to data/snapshots.db (not temp file)
    
    2. Create test snapshot using from_json_snapshot() with real account_id and case_id
    
    3. Save to database using save_snapshot()
    
    4. Retrieve via get_latest_snapshot()
    
    5. Compare retrieved snapshot with original - verify data integrity
    
    6. Verify both raw_json and parsed_data are preserved
    
    7. Test immutability - save same snapshot again, confirm row count increased by 1
    
    8. Verify get_previous_snapshot() returns the snapshot we just saved
    
    9. Test empty case retrieval - get_latest_snapshot() should return None for non-existent case
    
    Test commands:
    - python -c "
from src.storage import SnapshotRepository
from src.models import from_json_snapshot

r = SnapshotRepository()

# Create test snapshot
original = from_json_snapshot(
    account_id='acc1',
    case_id='case-001',
    endpoint_type='case_data',
    raw_json={'status': 'in_progress', 'test': 'data'}
)

# Save and retrieve
r.save_snapshot(original)
retrieved = r.get_latest_snapshot('case-001', 'case_data')

# Verify
assert retrieved is not None, 'Snapshot retrieval failed'
assert retrieved.account_id == original.account_id
assert retrieved.case_id == original.case_id
assert retrieved.endpoint_type == original.endpoint_type
assert retrieved.raw_json == original.raw_json

# Test immutability
r.save_snapshot(original)
count = r.get_snapshots_by_account('acc1')
print(f'Row count after two inserts: {len(count)}')
assert len(count) == 2, 'INSERT-only not working'
"
  </action>
  <verify>
    python -c "
from src.storage import SnapshotRepository
from src.models import from_json_snapshot

r = SnapshotRepository()

# Test save
original = from_json_snapshot(
    account_id='acc1',
    case_id='case-001',
    endpoint_type='case_data',
    raw_json={'status': 'in_progress'}
)
r.save_snapshot(original)

# Test retrieval
retrieved = r.get_latest_snapshot('case-001', 'case_data')
assert retrieved is not None
assert retrieved.raw_json == original.raw_json

# Test historical retrieval
prev = r.get_previous_snapshot('acc1', 'case-001', 'case_data')
assert prev is not None
assert prev.raw_json == original.raw_json

# Test empty case
none = r.get_latest_snapshot('nonexistent', 'case_data')
assert none is None

print('All CRUD operations verified')
"
  </verify>
  <done>
    Snapshot save/retrieve cycle works with real data
    Data integrity preserved (raw_json and parsed_data match)
    INSERT-only pattern verified (row count increases on duplicate save)
    get_previous_snapshot() returns correct snapshot for change detection
  </done>
</task>

</tasks>

<verification>
**Code Verification:**
- All imports work without errors
- Snapshot model has all required fields (account_id, case_id, endpoint_type, raw_json, parsed_data, timestamp)
- Repository has all 6 CRUD methods
- save_snapshot() uses INSERT only (no UPDATE)

**Schema Verification:**
- snapshots table created with all columns (8 columns)
- 3 indexes present: idx_case_id, idx_timestamp, idx_account_endpoint
- CREATE TABLE IF NOT EXISTS pattern used

**Database Content:**
- data/snapshots.db exists in project root (per D-04)
- At least 2+ real snapshots (from Phase 02)
- No error on queries with existing data

**Functionality Verification:**
- CRUD round-trip preserves data
- JSON serialization/deserialization works
- Timestamp handling correct (isoformat/fromisoformat)
- get_latest_snapshot() queries by (case_id, endpoint_type) per D-01
- get_previous_snapshot() retrieves for comparison per DETECT-01
- All 17 storage tests pass

**Requirement Coverage:**
- STORE-01: Save snapshots with timestamp ✓
- STORE-02: Retain all historical snapshots (INSERT-only) ✓
</verification>

<success_criteria>
- python -c "from src.storage import SnapshotRepository" succeeds
- Snapshot model has all required fields (account_id, case_id, endpoint_type, raw_json, parsed_data, timestamp)
- Database has snapshots table with all columns and 3 indexes
- save_snapshot() inserts records (no UPDATE)
- get_latest_snapshot() returns Snapshot with raw_json and parsed_data
- CRUD operations verified with test data
- 17 storage tests pass
- Real snapshots exist in data/snapshots.db (not just temp files)
- INSERT-only pattern verified: row count increases on duplicate save
</success_criteria>

<output>
After completion, create `.planning/phases/03-data-storage/03-SUMMARY.md`
</output>

<tool_call>
<function=Bash>
<parameter=command>
node "C:/Prjs/Claude/Inpol/gsd-tools.cjs" commit "docs(03): create and verify Phase 03 data storage PLAN.md" --files "C:/Prjs/Claude/Inpol/.planning/phases/03-data-storage/03-PLAN.md" 2>&1
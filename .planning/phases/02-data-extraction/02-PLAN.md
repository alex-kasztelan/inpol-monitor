---
phase: 02-data-extraction
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - src/scraper.py
  - src/models.py
  - src/storage.py
  - tests/test_scraper.py
  - tests/conftest.py
autonomous: true
requirements: [DATA-01, DATA-02]

must_haves:
  truths:
    - "All 5 cases can be fetched via authenticated JSON endpoints"
    - "Raw JSON snapshots are persisted to SQLite with timestamps"
    - "Parsed fields (status, dates, attachments, questions) are extracted and stored"
    - "Status values are resolved using the i18n dictionary"
    - "Errors are logged without stopping processing of other cases"
  artifacts:
    - path: "src/scraper.py"
      provides: "InpolScraper class with methods for all 4 JSON endpoints"
      exports: ["InpolScraper", "CaseData", "Attachment", "Question"]
    - path: "src/models.py"
      provides: "Pydantic models for case data structures"
      contains: "CaseData, Attachment, Question, Snapshot models"
    - path: "src/storage.py"
      provides: "SnapshotRepository for persisting and querying snapshots"
      exports: ["SnapshotRepository", "Snapshot"]
  key_links:
    - from: "src/scraper.py"
      to: "src/session_manager.py"
      via: "SessionManager injection"
      pattern: "SessionManager\\.session\\.(get|post)"
    - from: "src/storage.py"
      to: "data/snapshots.db"
      via: "SQLite connection"
      pattern: "sqlite3\\.connect|DatabaseMixin"
    - from: "src/scraper.py"
      to: "src/models.py"
      via: "Pydantic model validation"
      pattern: "CaseData\\(|Attachment\\(|Question\\("
---

<objective>
Implement data extraction layer to fetch, parse, and persist case data from all 5 cases across 2 accounts.

Purpose: Enable change detection (Phase 04) by storing raw JSON snapshots + parsed fields with full fidelity.
Output: Scraper module with 4 endpoint methods, Pydantic models for data structures, SQLite repository for snapshots.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/02-data-extraction/02-CONTEXT.md
@.planning/phases/01-project-foundation-authentication/01-SUMMARY.md
@.planning/research/ARCHITECTURE.md

<interfaces>
<!-- Key types and contracts from Phase 01 - use these directly -->

From src/session_manager.py:
```python
class SessionManager:
    def __init__(self, base_url: str)
    def extract_csrf(self, login_url: str) -> Optional[str]
    def login(self, username: str, password: str, csrf_token: str) -> bool
    def get(self, url: str, **kwargs) -> Optional[requests.Response]
    def post(self, url: str, data: Optional[dict] = None, **kwargs) -> Optional[requests.Response]
    def close(self)
    logged_in: bool  # Authentication state flag
```

From src/auth.py (expected):
```python
def run_sequential_auth() -> Generator[SessionManager, None, None]
# Yields authenticated SessionManager instances per account
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Define Pydantic models for case data structures</name>
  <files>src/models.py</files>
  <behavior>
    - Test 1: CaseData model accepts all required fields (person, case_number, case_type, dates, status, attachments, questions)
    - Test 2: Attachment model has name, date_added, url fields
    - Test 3: Question model has id, content, status, sent_time fields
    - Test 4: Snapshot model has account_id, case_id, endpoint_type, raw_json, parsed_data, timestamp fields
    - Test 5: Models validate correctly with sample JSON from endpoints
  </behavior>
  <action>
    Create Pydantic models in src/models.py:

    1. Attachment model:
       - name: str (filename)
       - date_added: str (parse from JSON)
       - url: Optional[str] (download link if available)

    2. Question model:
       - id: str
       - content: str
       - status: str (raw value from JSON)
       - status_label: Optional[str] (resolved via i18n)
       - sent_time: str

    3. CaseData model:
       - person_first: str
       - person_last: str
       - case_number: str (format: "WSC-V.6153.4537.2025")
       - case_type: str
       - submit_date: Optional[str]
       - decision_date: Optional[str]
       - updated_at: str (critical for change detection per D-22)
       - status_raw: str (from JSON)
       - status_label: Optional[str] (resolved via i18n)
       - attachments: list[Attachment]
       - questions: list[Question]
       - timeline: list[dict] (raw timeline entries)

    4. Snapshot model:
       - account_id: str
       - case_id: str
       - endpoint_type: str ("case_data", "attachments", "questions")
       - raw_json: dict (full response)
       - parsed_data: dict (extracted fields)
       - timestamp: datetime (UTC)

    Use pydantic>=2.0 syntax with BaseModel, Field, Optional.
    Add helper methods: from_json() for parsing endpoint responses.
  </action>
  <verify>
    <automated>pytest tests/test_models.py -x -v</automated>
  </verify>
  <done>Models defined, validated, and tests passing</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement InpolScraper with 4 JSON endpoint methods</name>
  <files>src/scraper.py</files>
  <behavior>
    - Test 1: fetch_case_data(case_id) returns parsed CaseData object
    - Test 2: fetch_attachments(case_id) returns list of Attachment objects
    - Test 3: fetch_questions(case_id) returns list of Question objects
    - Test 4: fetch_status_dictionary() returns dict of status codes -> labels
    - Test 5: All methods handle HTTP errors gracefully (return None, log error)
    - Test 6: All methods require authenticated SessionManager
  </behavior>
  <action>
    Create InpolScraper class in src/scraper.py:

    ```python
    class InpolScraper:
        def __init__(self, session: SessionManager, status_dict: Optional[dict] = None)
    ```

    Methods to implement:

    1. fetch_case_data(case_id: str) -> Optional[CaseData]:
       - GET /api/proceedings/{case_id}
       - Parse JSON response for: person name, case number, case type, dates, status
       - Resolve status using status_dict if provided
       - Return CaseData model or None on error

    2. fetch_attachments(case_id: str) -> list[Attachment]:
       - GET /api/proceedings/getRequiredAttachments?official_proceedings_id={case_id}
       - Parse JSON response for attachment list
       - Return list of Attachment models

    3. fetch_questions(case_id: str) -> list[Question]:
       - GET /api/proceedings/{case_id}/questions?page=1&results=100&filterBy=&orderBy=Status desc,SentTime desc
       - Parse JSON response for questions list
       - Resolve status labels using status_dict
       - Return list of Question models

    4. fetch_status_dictionary(lang: str = "en") -> dict[str, str]:
       - GET /assets/i18n/{lang}.json
       - Parse JSON for status code -> label mapping
       - Cache for reuse across multiple case fetches

    Error handling (per D-29, D-30):
    - Log errors with case_id and endpoint details
    - Return None or empty list on failure (don't raise)
    - Continue processing other cases if one fails

    Use session.get() from SessionManager for all requests.
  </action>
  <verify>
    <automated>pytest tests/test_scraper.py -x -v</automated>
  </verify>
  <done>InpolScraper class with 4 endpoint methods, error handling, tests passing</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Implement SnapshotRepository for SQLite persistence</name>
  <files>src/storage.py</files>
  <behavior>
    - Test 1: save_snapshot() inserts new row with all fields
    - Test 2: get_latest_snapshot(case_id, endpoint_type) returns most recent snapshot
    - Test 3: get_snapshots_by_account(account_id) returns all snapshots for account
    - Test 4: Database schema includes indexes on case_id, timestamp
    - Test 5: Snapshots are immutable (INSERT only, no UPDATE)
  </behavior>
  <action>
    Extend src/storage.py with SnapshotRepository following Repository Pattern (ARCHITECTURE.md):

    Database schema:
    ```sql
    CREATE TABLE IF NOT EXISTS snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id TEXT NOT NULL,
        case_id TEXT NOT NULL,
        endpoint_type TEXT NOT NULL,
        raw_json TEXT NOT NULL,
        parsed_data TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX idx_case_id ON snapshots(case_id);
    CREATE INDEX idx_timestamp ON snapshots(timestamp);
    ```

    SnapshotRepository class methods:
    1. __init__(db_path: str) - Initialize SQLite connection
    2. save_snapshot(snapshot: Snapshot) -> None - INSERT new snapshot
    3. get_latest_snapshot(case_id: str, endpoint_type: str) -> Optional[Snapshot] - SELECT latest
    4. get_snapshots_by_account(account_id: str) -> list[Snapshot] - SELECT by account
    5. get_all_snapshots() -> list[Snapshot] - SELECT all for testing

    Implementation notes:
    - Store raw_json and parsed_data as JSON text (sqlite3 native JSON support)
    - Use ISO 8601 timestamps (UTC)
    - Follow snapshot immutability pattern (ARCHITECTURE.md Pattern 4)
    - Use context manager for DB connections
  </action>
  <verify>
    <automated>pytest tests/test_storage.py -x -v</automated>
  </verify>
  <done>SnapshotRepository with save/query methods, schema created, tests passing</done>
</task>

<task type="auto">
  <name>Task 4: Create orchestrator function to fetch all cases</name>
  <files>src/scraper.py</files>
  <action>
    Add orchestrator function to src/scraper.py:

    ```python
    def fetch_all_cases(
        sessions: list[SessionManager],
        credentials: dict,
        storage: SnapshotRepository
    ) -> dict[str, any]:
        """
        Fetch and persist data for all 5 cases across 2 accounts.

        Args:
            sessions: List of authenticated SessionManager instances
            credentials: Loaded credentials with account/case structure
            storage: SnapshotRepository for persistence

        Returns:
            Summary dict: {"success": int, "failed": int, "errors": list}
        """
    ```

    Implementation:
    1. For each account in credentials:
       - Get SessionManager from sessions list
       - Fetch status dictionary once (cache for all cases)
       - Create InpolScraper with session + status_dict

    2. For each case_id in account["cases"]:
       - Fetch case data -> save snapshot
       - Fetch attachments -> save snapshot
       - Fetch questions -> save snapshot
       - Log progress: "Fetched case {case_id}: {status}"

    3. Error handling (per D-29, D-30):
       - Wrap each case fetch in try/except
       - Log full error details (case_id, endpoint, exception)
       - Continue to next case on failure
       - Track success/failure counts

    4. Return summary with counts and any errors
  </action>
  <verify>
    <automated>pytest tests/test_orchestrator.py -x -v</automated>
  </verify>
  <done>fetch_all_cases() function orchestrates all 5 cases, handles errors, returns summary</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 5: Verify end-to-end data extraction</name>
  <what-built>
    - Pydantic models for case data (Task 1)
    - InpolScraper with 4 endpoint methods (Task 2)
    - SnapshotRepository for SQLite persistence (Task 3)
    - fetch_all_cases() orchestrator (Task 4)
  </what-built>
  <how-to-verify>
    1. Ensure .env and credentials.json are configured with both accounts

    2. Run manual extraction:
       ```bash
       python -c "
       from src.scraper import fetch_all_cases
       from src.storage import SnapshotRepository
       from src.config import load_credentials, load_env
       from src.auth import run_sequential_auth

       load_env('.env')
       creds = load_credentials('credentials.json')
       storage = SnapshotRepository('data/snapshots.db')
       sessions = list(run_sequential_auth())
       result = fetch_all_cases(sessions, creds, storage)
       print(f'Success: {result[\"success\"]}, Failed: {result[\"failed\"]}')
       if result['errors']:
           print('Errors:', result['errors'])
       "
       ```

    3. Verify database has snapshots:
       ```bash
       sqlite3 data/snapshots.db "SELECT case_id, endpoint_type, timestamp FROM snapshots ORDER BY timestamp DESC LIMIT 10;"
       ```

    4. Expected: 5 cases x 3 endpoints = 15 snapshots (minimum)
  </how-to-verify>
  <resume-signal>Type "approved" if snapshots exist for all 5 cases, or describe any errors</resume-signal>
</task>

</tasks>

<verification>
Overall phase verification:
1. All 15+ snapshots exist in database (5 cases x 3 endpoints)
2. Raw JSON is preserved (can re-parse later if needed)
3. Parsed fields are queryable (status, dates, attachment names)
4. Status labels are resolved (not just raw codes)
5. Error log shows no unhandled exceptions
</verification>

<success_criteria>
- [ ] DATA-01 satisfied: Case data pulled from all 5 cases via JSON endpoints
- [ ] DATA-02 satisfied: Status, dates, attachments, questions extracted and stored
- [ ] Raw JSON snapshots persisted with timestamps
- [ ] All tests pass (models, scraper, storage, orchestrator)
- [ ] Manual end-to-end run completes with snapshots in database
- [ ] Errors logged with sufficient detail for debugging
</success_criteria>

<output>
After completion, create `.planning/phases/02-data-extraction/02-SUMMARY.md` with:
- Files created/modified
- Test results
- Snapshot counts per case
- Any errors encountered
- Commits made
</output>

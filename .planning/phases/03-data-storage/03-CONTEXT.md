# Phase 03: Data Storage - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase implements the complete database layer for the Inpol Monitor. It provides:
- Database schema design and initialization
- SnapshotRepository class for CRUD operations
- Methods to save current snapshots and query previous snapshots for change detection
- Persistence of all historical snapshots (no overwrites, only inserts)

**What this phase does NOT do:**
- Change detection logic (Phase 04)
- Telegram notification integration (Phase 05)
- Automated scheduling (Phase 07)
</domain>

<decisions>
## Implementation Decisions

### Query Strategy for Change Detection
- **D-01:** Query the most recent snapshot by (case_id, endpoint_type)
  - `SELECT * FROM snapshots WHERE case_id=? AND endpoint_type=? ORDER BY timestamp DESC LIMIT 1`
  - Returns the same snapshot if nothing changed between checks
  - Simpler implementation, matches Phase 02 pattern

### Snapshot Comparison Method
- **D-02:** Compare both raw JSON and parsed data
  - Use raw JSON for integrity verification (byte-for-byte)
  - Use parsed data for human-readable diffs
  - Double verification ensures accuracy while maintaining readability
  - `compare(raw_json_old, raw_json_new)` AND `compare(parsed_data_old, parsed_data_new)`

### Notification Timing
- **D-03:** Batch all changes, one notification per check time
  - Aggregate changes from all 3 checks (8:00, 12:30, 18:00)
  - One notification per check cycle, regardless of case count
  - Balances real-time response with user experience

### Database Storage Location
- **D-04:** Use project root (`data/snapshots.db`)
  - Matches Phase 02 implementation
  - Simple path, no configuration needed
  - User accepts this location

### Data Immutability
- **D-05:** All snapshots are INSERT-only (no UPDATE)
  - Matches Repository pattern from Phase 02
  - Historical data is preserved exactly as captured
  - Enables accurate change detection by comparing timestamps

## Folded Todos

### Phase 02: Database Integration
- **Stored:** `Create credentials.json with real credentials for live testing`
  - Belongs in Phase 05 (Notifications) where credentials are used for Telegram
- **Stored:** `Create .env file for environment configuration`
  - Will be addressed in Phase 01 re-run or Phase 06 (Orchestration)

## Deferred Ideas

### None
- Discussion stayed within phase scope

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specifications
- `.planning/PROJECT.md` — Project vision, requirements, constraints
- `.planning/ROADMAP.md` — Phase scope and deliverables
- `.planning/STATE.md` — Current progress and session continuity

### Phase 02 References
- `.planning/phases/02-data-extraction/02-SUMMARY.md` — Database schema, SnapshotRepository API
- `src/storage.py` — Existing Repository pattern implementation
- `src/models.py` — Snapshot model structure

### Key Links
- `src/storage.py::get_previous_snapshot()` — Query method for change detection
- `src/models.py::Snapshot` — Data structure to persist
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/storage.py::SnapshotRepository` — Repository pattern already implemented
- `src/models.py::Snapshot` — Model with raw_json and parsed_data fields
- `DatabaseMixin` — Connection management with row factory

### Established Patterns
- Repository pattern (Phase 02)
- JSON serialization for text storage
- Indexes on case_id, timestamp, account_id+endpoint_type
- Error handling with rollback on failure

### Integration Points
- `src/scraper.py::fetch_all_cases()` — Persists snapshots after fetching
- `src/auth.py::run_sequential_auth()` — Provides authenticated sessions
- `src/config.py::load_credentials()` — Reads credentials for account IDs

</code_context>

<specifics>
## Specific Ideas

None — open to standard approaches within scope

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-data-storage*
*Context gathered: 2026-04-01*

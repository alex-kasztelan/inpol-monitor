---
phase: 04-change-detection
plan: 01
type: execute
depends_on:
  - 01-CONTEXT.md
files_modified:
  - src/detector.py
  - src/models.py
  - tests/test_detector.py
  - src/storage.py
autonomous: true
requirements:
  - DETECT-01
  - DETECT-02
user_setup:
  - service: inpol.mazowieckie.pl
    why: "Need authenticated data to test change detection"
    manual_steps:
      - "Run: python check.py -v to populate database with snapshots"
      - "Update test snapshots with modified data"

must_haves:
  truths:
    - "Previous snapshot can be loaded from SQLite"
    - "Changes are detected by comparing snapshots"
    - "Status changes are identified"
    - "New documents are detected"
    - "Date modifications are flagged"
    - "Question/answer changes are detected (extension)"
  artifacts:
    - path: "src/detector.py"
      provides: "Detector class with strategy pattern for change detection"
      exports: ["Detector", "StatusDetector", "DocumentDetector", "DateDetector", "TimelineDetector", "QuestionDetector"]
    - path: "src/models.py"
      provides: "Change model to represent detected changes"
      contains: ["Change", "ChangeType", "QUESTION_TITLES"]
    - path: "tests/test_detector.py"
      provides: "Unit tests for change detection logic"
      contains: "test_status_change", "test_new_document", "test_date_change", "test_question_detection"
  key_links:
    - from: "src/detector.py"
      to: "src/storage.py"
      via: "get_previous_snapshot, save_snapshot"
      pattern: "storage.get_previous|storage.save_snapshot"
    - from: "src/detector.py"
      to: "src/models.py"
      via: "Change model, Snapshot model"
      pattern: "Change\\(|Snapshot\\("
    - from: "src/detector.py"
      to: "src/scheduler.py"
      via: "detector.run_check()"
      pattern: "detector\\.(run_check|run)"
---

# Phase 04 Change Detection - Plan

**Objective**: Implement change detection layer that compares snapshots and identifies status changes, new documents, and date modifications.

## Context

Phase 03 complete - Storage layer with SQLite database implemented. Need to implement detector layer that:
1. Loads previous snapshots from database
2. Compares against current data
3. Detects specific change types using strategy pattern
4. Returns structured change list

## Tasks

### Task 1: Add Change model to models.py

**Files**: src/models.py

**Action**:
- Add `Change` class with fields: type, old_value, new_value, description
- Add `ChangeType` enum: STATUS, NEW_DOCUMENT, REMOVED_DOCUMENT, DATE_CHANGE, DECISION_DATE_CHANGE
- Add `Changes` model (list of Change)
- Update Snapshot model to include parsed_data for change comparison

**Verify**:
- models.py exports Change, ChangeType, Changes
- Change has type, old_value, new_value fields

### Task 2: Implement Detector class with strategy pattern

**Files**: src/detector.py

**Action**:
- Create base `BaseDetector` class with `detect()` method
- Create `StatusDetector`:
  - Compares status_raw between snapshots
  - Returns Change(type=STATUS, ...)
- Create `DocumentDetector`:
  - Compares relatedDocs lists by ID
  - Detects new and removed documents
- Create `DateDetector`:
  - Compares decision_date, submit_date, updated_at
  - Returns DECISION_DATE_CHANGE, SUBMIT_DATE_CHANGE, UPDATED_AT_CHANGE
- Create `TimelineDetector`:
  - Detects new timelineEvents by (eventType, date) tuple
  - Returns TIMELINE_EVENT_ADDED
- Create `QuestionDetector` (extension):
  - Detects new questions (status=1) and answers (status 1→2)
  - Uses QUESTION_TITLES dict for title translation
  - Returns QUESTION_ASKED, QUESTION_ANSWERED
- `Detector` class coordinates all detectors
- `detect_all_changes()` orchestrates full workflow

**Verify**:
- All detector classes present and integrated
- 6 change types detectable (status, documents, dates, timeline, questions)

### Task 3: Extend SnapshotRepository to support querying

**Files**: src/storage.py

**Action**:
- Add `get_previous_snapshot(account_id, case_id, endpoint_type)` method
- Returns previous snapshot for comparison or None if first check
- Handle edge case: no previous snapshot exists

**Verify**:
- storage.py exports SnapshotRepository
- get_previous_snapshot method exists
- Returns None when no previous snapshot found

### Task 4: Create test suite

**Files**: tests/test_detector.py

**Action**:
- test_get_previous_snapshot: tests database query
- test_detect_changes_empty: tests empty change list
- test_status_change: tests status detection
- test_status_label_change: tests label detection
- test_new_document: tests new attachment detection
- test_removed_document: tests removed attachment detection
- test_decision_date_change: tests date change detection
- test_no_previous_snapshot: tests handling of first check

**Verify**:
- test_detector.py exists with all test functions
- All tests pass

### Task 5: Create orchestrator function

**Files**: src/detector.py

**Action**:
- Create `detect_all_changes(sessions, credentials, storage)` function
- Fetches current data for all cases
- Loads previous snapshots
- Runs detectors for each case
- Returns aggregated change list per account

**Verify**:
- detector.py exports detect_all_changes
- Function handles empty change list (no previous snapshot)
- Function returns structured dict with changes per account

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| DETECT-01: Compare current vs previous snapshot | Done |
| DETECT-02: Detect status changes | Done |
| DETECT-02: Detect new documents | Done |
| DETECT-02: Detect date modifications | Done |

## Test Coverage

- Unit tests for each detector strategy
- Integration tests for complete change detection flow
- Edge case tests (no previous snapshot, empty changes)

## Known Edge Cases

1. **First check**: No previous snapshot exists → Return empty changes
2. **No attachments**: DocumentDetector handles empty list
3. **Missing fields**: Handle None/empty values gracefully

## Output

After completion:
- Working change detection layer
- Unit tests passing
- Integration with orchestrator ready

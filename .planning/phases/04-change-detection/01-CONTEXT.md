---
phase: 04-change-detection
plan: 01
type: context
depends_on:
  - 02-SUMMARY.md (Storage layer with snapshots)
  - research/ARCHITECTURE.md (Detector pattern design)
files_modified:
  - src/detector.py
  - src/models.py
  - tests/test_detector.py
autonomous: true
---

# Phase 04 Change Detection - Context

## Phase Objective

Implement change detection layer that compares current snapshots against historical snapshots to identify status changes, new documents, and deadline modifications.

## Core Value

Enable automatic detection of case status changes, document additions, and deadline modifications with precise delta calculations between snapshots.

## Decisions Already Made

### From Phase 02 (Data Extraction)

- **D-22**: `updated_at` field is critical for change detection (must always be analyzed)
- **D-27**: Full JSON snapshots preserved in database (enables re-parsing if field extraction changes)
- Repository pattern used for storage (easy to add detectors later)
- Snapshot immutability enforced (INSERT only, never UPDATE)

### From Architecture Research

- **Detector Layer**: Compare current snapshot vs previous, identify changes
- **Strategy Pattern**: Separate comparison logic per data type (status, dates, documents)
- **Batch-Then-Notify**: Complete all 5 cases before sending notification
- **Snapshot Immutability**: Never update historical snapshots; always insert new rows

## Change Detection Requirements

### DETECT-01: Compare current data with previous snapshot

- Load latest snapshot for each endpoint type (case_data, attachments, questions)
- Compare current vs previous snapshot
- Return list of detected changes
- Handle "no previous snapshot" case (first check)

### DETECT-02: Detect specific change types

#### Status Changes
- Compare `status_raw` field
- Compare `status_label` field
- Return: `{type: "status", old: "X", new: "Y"}`

#### Document Changes
- Compare `attachments` list
- Detect added documents
- Detect removed documents
- Return: `{type: "new_document", name: "...", old: [], new: [...]}`

#### Date Modifications
- Compare `submit_date` (if changed after initial submission)
- Compare `decision_date` (if deadline updated)
- Compare `updated_at` (always analyze)
- Return: `{type: "date_change", field: "decision_date", old: "YYYY-MM-DD", new: "YYYY-MM-DD"}`

### Data Flow

```
1. Load previous snapshots for all 5 cases
2. Fetch current data for all 5 cases
3. For each case:
   a. Compare case_data snapshot
   b. Compare attachments snapshot
   c. Compare questions snapshot
   d. Aggregate changes
4. Return complete change list per account
```

## Anti-Patterns to Avoid

- **Tight coupling**: Detector shouldn't depend on scraper internals
- **Silent failures**: Missing previous snapshot should be handled gracefully
- **Full re-parsing**: Don't parse JSON twice; use cached parsed_data

## Test Coverage

Need tests for:
- `Detector.get_previous_snapshot()` - Handle missing previous snapshot
- `Detector.detect_changes()` - Compare snapshots and return changes
- `StatusDetector.detect()` - Status change detection
- `DocumentDetector.detect()` - Document addition/deletion
- `DateDetector.detect()` - Date modification detection

## Next Steps

1. Create `Detector` class with strategy pattern for different detectors
2. Implement `SnapshotRepository.get_previous()` method
3. Write unit tests for each detector
4. Integrate with orchestrator layer

# Phase 08: Validation & Polish - Overview

## Goal
Validate change detection accuracy, error scenario handling, and notification formatting.

## Scope (Locked)

### Validation Method
- **Golden files** - exact comparison of detector output against expected fixtures

### Change Detection (7 types)
- status, status_label, new_document, removed_document
- decision_date_change, submit_date_change, updated_at_change

### Error Scenarios to Test
- Authentication failures (401/403) → verify Telegram error sent
- Telegram failures (mocked bot errors) → graceful handling + logging
- Rate limiting (429) → verify backoff/retry logic

### Notification Formatting
- Changes grouped by type (status → docs → dates)
- English MarkdownV2 only
- Error format: "Error checking case X: [message]"
- Character limit: < 4096 chars

## Deliverables
1. Golden file test fixtures (`tests/planner/golden/`)
2. Authentication failure test (`tests/planner/test_auth_fail.py`)
3. Telegram failure test (`tests/planner/test_telegram_fail.py`)
4. Notification format validation test (`tests/planner/test_noti_format.py`)
5. Manual verification checklist (`docs/VALIDATION_CHECKLIST.md`)
6. Golden file validation script (`src/tools/validate_golden.py`)

## Acceptance Criteria
- All Phase 08 tests pass
- Manual verification checklist completed successfully
- Golden file validation script produces no diffs for known good data
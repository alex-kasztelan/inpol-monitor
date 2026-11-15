---
status: complete
phase: 05-telegram-notifications
source: 01-SUMMARY.md
started: 2026-07-09T19:45:00Z
updated: 2026-07-09T20:05:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 6
name: Reset Functionality
expected: |
  reset() clears accumulated changes so the next check starts fresh.
awaiting: user response

## Tests

### 1. Change Notification Format
expected: When changes are detected, a Telegram notification is sent with case ID, summary of changes, and individual change details.
result: pass

### 2. Error Notification Format
expected: When a check fails, a Telegram notification is sent with error type, error message, and timestamp.
result: pass

### 3. Markdown Formatting
expected: Notifications use HTML formatting with <b>bold</b> tags and * list markers (MarkdownV2 was replaced due to rendering issues in Telegram).
result: pass

### 4. Batch-Then-Notify
expected: Changes are aggregated per account before sending (one notification per account, not per case).
result: pass

### 5. Bot Initialization
expected: Telegram bot is initialized with the provided token and is ready to send messages.
result: pass

### 6. Reset Functionality
expected: reset() clears accumulated changes so the next check starts fresh.
result: pass

## Summary

total: 6
passed: 6
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- **FIXED**: `status_id` undefined in `notifier.py:715` — `_build_error_message()` referenced undefined variable. Fixed by removing the status label from error header. Also added `os.environ["LANGUAGE"] = "en"` to `test_notifier.py` for consistent localization in tests.

---
status: complete
phase: 12-enhanced-question-comparison
source: 12-01-SUMMARY.md
started: 2026-07-09T19:35:00Z
updated: 2026-07-09T20:20:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

number: 7
name: Removed Questions Detected
expected: |
  Removed questions appear in comparison with is_question=True, new_value=None, showing all question fields.
awaiting: user response

## Tests

### 1. View Question Status Change
expected: Comparison view shows a row for "question:Q1:status" with old_value="1" and new_value="2" when a question's status changed between snapshots.
result: pass

### 2. View Answer Change
expected: Comparison view shows a row for "question:Q1:answer" with old_value=None and new_value="Some answer" when a question receives an answer between snapshots.
result: pass

### 3. Translated Status Labels
expected: Status label field shows "Waiting for an answer" (old) and "Answer" (new) using Cases.Question.Statuses translations.
result: pass

### 4. Translated Title Labels
expected: Title field shows "Missing documents" (old) and "Proxy" (new) using Cases.Question.Titles translations.
result: pass

### 5. All Question Fields Displayed
expected: Comparison view shows rows for all 7 question fields: title, status, status_label, body, sentTime, answer, responseTime.
result: pass

### 6. New Questions Detected
expected: New questions appear in comparison with is_question=True, old_value=None, showing all question fields.
result: pass

### 7. Removed Questions Detected
expected: Removed questions appear in comparison with is_question=True, new_value=None, showing all question fields.
result: pass

## Summary

total: 7
passed: 7
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- **FIXED**: `scraper.py:610` — questions snapshot `parsed_data` didn't include `questions` list, only `count` and `totalResults`. Fixed to include the full questions list in `parsed_data` so comparison code can access it.

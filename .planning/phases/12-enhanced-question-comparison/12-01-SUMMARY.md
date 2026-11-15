---
phase: 12-enhanced-question-comparison
plan: 01
subsystem: ui
tags: [comparison, questions, localization, field-diff, tdd]

# Dependency graph
requires:
  - phase: 11-web-application
    provides: "Web UI with Flask app, compare route, and comparison template"
provides:
  - "Field-level question comparison in build_comparison()"
  - "Compare template rendering all 7 question fields with change highlighting"
  - "Localization keys for comparison field labels"
affects: [12-enhanced-question-comparison]

# Tech tracking
tech-stack:
  added: []
  patterns: ["field-level comparison with is_question_field flag", "translated labels via old_label/new_label keys"]

key-files:
  created:
    - tests/test_comparison.py
  modified:
    - src/web/routes.py
    - src/web/templates/compare.html
    - en.json

key-decisions:
  - "Field-level comparison uses is_question_field flag to distinguish from entire-question items"
  - "status_label and title fields include old_label/new_label with translated values"
  - "FieldLabels localization key added to en.json for comparison column headers"

patterns-established:
  - "Field-level diff pattern: iterate common items, compare per-field, emit item with field_name flag"

requirements-completed: [COMP-01, COMP-02, COMP-03]

# Metrics
duration: 3min
completed: 2026-07-09
---

# Phase 12 Plan 01: Enhanced Question Comparison Summary

**Field-level question comparison with per-field change detection and localized label rendering in snapshot compare view**

## Performance

- **Duration:** 3 min
- **Started:** 2026-07-09T19:29:19Z
- **Completed:** 2026-07-09T19:32:57Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- build_comparison() now detects per-field changes for questions present in both snapshots (7 fields: title, status, status_label, body, sentTime, answer, responseTime)
- Compare template renders field-level changes with translated labels for status_label and title
- Added Cases.Question.FieldLabels localization keys for comparison column headers
- All changes covered by 7 TDD tests (RED+GREEN committed)

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Add failing test for field-level question comparison** - `83e9090` (test)
2. **Task 1 (GREEN): Implement field-level question comparison** - `b1d3522` (feat)
3. **Task 2: Render all question fields with change highlighting** - `ebcf89d` (feat)

## Files Created/Modified
- `tests/test_comparison.py` - 7 tests for build_comparison() field-level diff detection
- `src/web/routes.py` - Added common_ids loop with per-field comparison in build_comparison()
- `src/web/templates/compare.html` - Added is_question_field rendering block and CSS classes
- `en.json` - Added Cases.Question.FieldLabels with 7 field label translations

## Decisions Made
- Field-level comparison uses `is_question_field: True` flag to distinguish from entire-question items (`is_question: True`)
- status_label and title comparison items include `old_label`/`new_label` with translated values via localization
- FieldLabels localization key added under Cases.Question for comparison column headers

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test failure in `tests/planner/test_noti_format.py` (NameError: `status_id` undefined in `notifier.py:715`) — unrelated to this plan, not introduced by these changes

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Enhanced question comparison complete, field-level diffs now visible in web UI
- Ready for next phase or verification testing

---
*Phase: 12-enhanced-question-comparison*
*Completed: 2026-07-09*

## Self-Check: PASSED

- tests/test_comparison.py: FOUND
- src/web/routes.py: FOUND
- src/web/templates/compare.html: FOUND
- en.json: FOUND
- Commit 83e9090: FOUND
- Commit b1d3522: FOUND
- Commit ebcf89d: FOUND

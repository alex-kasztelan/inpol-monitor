# Phase 12: Enhanced Question Comparison - Context

**Gathered:** 2026-07-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Improve the web UI's snapshot comparison to display all question fields (status_label, answer, responseTime) and detect field-level changes within questions (not just new/removed questions).

</domain>

<decisions>
## Implementation Decisions

### Change Detection Scope
- **D-01:** Detect changes to ALL question fields (status, answer, body, sentTime, title, responseTime, status_label) — not just status + answer
- **D-02:** When a question exists in both snapshots, compare each field individually and highlight which ones changed

### UI Display
- **D-03:** Display all question fields in comparison view: title, status, status_label, body, sentTime, answer, responseTime
- **D-04:** Highlight changed fields with visual indicator (table-warning class already exists)

### Localization
- **D-05:** Use existing localization keys from en.json (Cases.Question.Statuses, Cases.Question.Titles) for status_label display
- **D-06:** No new translation keys needed — status_label is already translated in the snapshot data

### the agent's Discretion
- Comparison layout and formatting details
- Whether to show field-level diff inline or in a separate section
- How to handle empty/null values in comparison

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Web UI
- `src/web/routes.py` — build_comparison() function (lines 255-358) — current comparison logic
- `src/web/templates/compare.html` — comparison template — current UI rendering
- `src/localization.py` — t() function for translations

### Data Layer
- `src/detector.py` — lines 708-719 — questions snapshot structure (what fields are saved)
- `src/models.py` — Question model definition

### Localization
- `en.json` — Cases.Question.Statuses, Cases.Question.Titles — existing translation keys

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `build_comparison()` in routes.py: Already handles question comparison — needs field-level diff logic added
- `compare.html` template: Already has question rendering block — needs additional fields displayed
- `table-warning` CSS class: Already used for highlighting changed rows — can highlight individual fields

### Established Patterns
- Questions snapshot saves all fields: id, title, body, status, status_label, sentTime, answer, responseTime
- Comparison items use `is_question: True` flag for special rendering
- Localization uses `t('key', 'default')` pattern with dot-notation keys

### Integration Points
- `build_comparison()` → compare.html template data flow
- Questions endpoint snapshot → parsed_data.questions → comparison logic

</code_context>

<specifics>
## Specific Ideas

The user wants to see ALL question field changes in the comparison view, not just whether a question was added or removed. When a question's status changes from "Waiting for an answer" to "Answer", or when an answer appears, these should be highlighted as individual field changes.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 12-Enhanced Question Comparison*
*Context gathered: 2026-07-09*

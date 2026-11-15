# Phase 02: Data Extraction - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

---

## Phase Boundary

Extract and persist case data from inpol.mazowieckie.pl for all 5 cases across 2 accounts.

**In scope:**
- Discover and call JSON API endpoints for case data
- Extract: person name, case number, case type, dates, status, attachments, questions, timeline
- Persist raw JSON snapshots + parsed fields to SQLite
- Enable change detection in Phase 04 (not implemented here)

**Out of scope:**
- Change detection logic (Phase 04)
- Telegram notifications (Phase 05)
- Windows Task Scheduler integration (Phase 07)

---

## Implementation Decisions

### Data Source Strategy
- **D-11:** Server returns HTML pages with client-side JSON subrequests — we must replicate the subrequests
- **D-12:** Store raw JSON responses + parsed fields — full fidelity for re-parsing later

### Known JSON Endpoints
- **D-13:** Main case data: `GET /api/proceedings/<Case ID>`
- **D-14:** Attachments: `GET /api/proceedings/getRequiredAttachments?official_proceedings_id=<Case ID>`
- **D-15:** Status dictionary: `GET /assets/i18n/en.json` (localized per language)
- **D-16:** Questions: `GET /api/proceedings/<Case ID>/questions?page=1&results=100&filterBy=&orderBy=Status desc,SentTime desc`

### Fields to Extract (per case)
- **D-17:** Person (first + last name)
- **D-18:** Case number (format: "WSC-V.6153.4537.2025")
- **D-19:** Case type (e.g., "Residence permit for a long-term resident of the European Union")
- **D-20:** Submit date
- **D-21:** Decision date
- **D-22:** Updated at (must always be analyzed for changes)
- **D-23:** Status (resolved via `/assets/i18n/en.json` dictionary)
- **D-24:** Attachments — detect new files by name and date added (attachments cannot be removed, only added)
- **D-25:** Questions — track whether any question has status "Answer"
- **D-26:** Timeline — track any new message/state added (sequence of icons with text messages)

### Snapshot Strategy
- **D-27:** Persist full JSON snapshots — enables re-parsing if field extraction logic changes
- **D-28:** Each snapshot includes: account_id, case_id, endpoint_type, raw_json, parsed_fields, timestamp

### Error Handling
- **D-29:** Log all errors with sufficient detail for debugging
- **D-30:** Continue processing other cases if one fails (no hard failures)

### Claude's Discretion
- Exact URL pattern for case ID discovery (may need HTML parsing to find case IDs)
- Handling of pagination in questions endpoint (currently page=1&results=100)
- Status dictionary caching strategy (fetch once per session vs cache indefinitely)

---

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture
- `.planning/research/ARCHITECTURE.md` — Scraper layer patterns, Repository pattern for snapshots

### Requirements
- `.planning/PROJECT.md` — DATA-01 (pull case data), DATA-02 (extract status, dates, documents, deadlines)

### Upstream Context
- `.planning/phases/01-project-foundation-authentication/01-CONTEXT.md` — Authentication decisions
- `.planning/phases/01-project-foundation-authentication/01-SUMMARY.md` — SessionManager capabilities

---

## Existing Code Insights

### Reusable Assets
- `src/session_manager.py` — SessionManager class with authenticated session
- `src/auth.py` — `run_sequential_auth()` yields authenticated sessions per account

### Integration Points
- All JSON endpoints require authenticated session cookies from SessionManager
- Case IDs must be discovered (possibly from HTML or from auth flow response)

---

## Specific Ideas

- 5 total cases: 3 in account 1, 2 in account 2
- Status values are localized — use `/assets/i18n/en.json` for English labels
- Attachments are append-only — only detect additions, never removals
- Timeline entries are sequential — detect new entries by count or content

---

## Deferred Ideas

None — all discussion stayed within phase scope.

---

*Phase: 02-data-extraction*
*Context gathered: 2026-03-30*

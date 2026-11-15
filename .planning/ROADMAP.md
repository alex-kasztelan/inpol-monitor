# Inpol Monitor - Roadmap

## Milestone M1: Initial Development

**Goal**: Working monitoring system that checks all 5 cases and sends Telegram notifications on changes

---

## Phase 1: Project Foundation & Authentication

**Goal**: Set up project structure, dependencies, and authentication flow for both accounts

**Scope**:
- Project directory structure
- Python dependencies (requests, beautifulsoup4, python-dotenv, sqlite3)
- .env configuration for credentials
- Authentication module for inpol.mazowieckie.pl
- Session management (cookies, CSRF tokens)
- Manual CLI trigger for testing

**Plans:** 3 plans

**Plan list:**
- [x] 01-PLAN.md — Project structure, dependencies, config loading (AUTH-02)
- [x] 02-PLAN.md — SessionManager and auth flow (AUTH-01)
- [x] 03-PLAN.md — CLI entry point and test scaffolding (AUTH-01, AUTH-02)

**Canonical refs**:
- `.planning/research/ARCHITECTURE.md` - Auth layer design patterns

---

## Phase 2: Data Extraction (COMPLETED)

**Goal**: Fetch case data from all 5 cases across both accounts and persist to SQLite

**Scope**:
- JSON API parsing for case pages
- Extract: status, last update date, documents list, decision deadline
- Handle both account layouts
- Structure data for storage
- Error handling for missing/malformed data
- Status label resolution via i18n dictionary
- SQLite persistence with Repository pattern

**Plans:** 1 plan

**Plan list:**
- [x] 02-PLAN.md — Pydantic models, InpolScraper class, SnapshotRepository

**Artifacts:**
- `src/models.py` - Pydantic models: CaseData, Attachment, Question, Snapshot
- `src/scraper.py` - InpolScraper with 4 endpoint methods + orchestrator
- `src/storage.py` - SnapshotRepository for SQLite persistence
- `tests/test_models.py` - 11 tests for Pydantic models
- `tests/test_scraper.py` - 18 tests for scraper methods
- `tests/test_storage.py` - 17 tests for repository operations

**Test Results:** 46 tests passing

**Canonical refs**:
- `.planning/research/ARCHITECTURE.md` - Repository pattern, Snapshot immutability

---

## Phase 3: Data Storage (COMPLETED)

**Goal**: Persist snapshots to SQLite with full history

**Scope**:
- Database schema design
- SnapshotRepository implementation
- Save current data with timestamp
- Query latest snapshot for comparison
- Retain all historical records (STORE-02)

**Plans:** 1 plan

**Plan list:**
- [x] 01-PLAN.md — Document and verify SnapshotRepository implementation (STORE-01, STORE-02)

**Artifacts:**
- `src/storage.py` - Complete SnapshotRepository with CRUD operations
- `data/snapshots.db` - SQLite database with snapshots table and indexes

**Test Results:** 17 tests passing

**Canonical refs**:
- `.planning/research/ARCHITECTURE.md` - Repository pattern, Snapshot immutability

---

## Phase 4: Change Detection (COMPLETED)

**Goal**: Compare current vs previous snapshot and identify all changes

**Scope**:
- Load previous snapshot from database
- Compare status, dates, documents
- Detect: status changes, new documents, date modifications
- Build change list for notification
- Strategy pattern for different field types

**Plans:** 1 plan

**Plan list:**
- [x] 01-PLAN.md — Change detection with Strategy pattern

**Artifacts:**
- `src/detector.py` — Detector class with 7 change types: status, status_label, new_document, removed_document, decision_date_change, submit_date_change, updated_at_change
- `tests/test_detector.py` — 20 tests passing

**Test Results:** 20 tests passing

**Canonical refs**:
- `.planning/research/ARCHITECTURE.md` - Strategy pattern for detection

---

## Phase 5: Telegram Notifications (COMPLETED)

**Goal**: Send detailed change reports to user's Telegram

**Scope**:
- Telegram bot integration
- Format detailed change messages
- Include case ID and specific changes
- Handle no-change cycles (silent)
- Error notifications

**Plans:** 3 plans

**Plan list:**
- [x] 01-PLAN.md — Telegram bot integration with aiogram 3.x
- [x] 02-PLAN.md — Message formatting with MarkdownV2
- [x] 03-PLAN.md — Error notifications and batch sending

**Artifacts:**
- `src/notifier.py` — TelegramNotifier with change aggregation and error handling
- `tests/test_notifier.py` — 11 tests passing

**Test Results:** 11 tests passing

**Canonical refs**:
- `.planning/research/ARCHITECTURE.md` - Notifier layer

---

## Phase 6: Orchestration & Error Handling (COMPLETED)

**Goal**: Wire all components together with comprehensive error handling

**Scope**:
- Main orchestrator script
- Error handler wrapper
- Send error notifications on failure
- Logging setup
- Manual CLI end-to-end test

**Artifacts:**
- `src/orchestrator.py` — run_check() cycle: auth → scrape → detect → notify → save
- `src/detector.py` — detect_all_changes() with notifier injection

**Test Results:** Integration verified via component tests (131 total)

**Canonical refs**:
- `.planning/research/ARCHITECTURE.md` - Batch-then-notify, Error flow

---

## Phase 7: Windows Task Scheduler Integration (COMPLETED)

**Goal**: Automated execution at 8:00, 12:30, 18:00 Poland time

**Scope**:
- Windows Task Scheduler setup script/documentation
- Batch file or PowerShell wrapper
- Timezone handling (CET/CEST)
- Test scheduled execution
- Manual CLI option (SCHED-03)

**Artifacts**:
- `run_check.cmd` - Batch runner for Task Scheduler
- `SCHEDULING.md` - Setup and management documentation

**Test Results**: Manual verification sufficient (automation works)

**Canonical refs**:
- `.planning/research/ARCHITECTURE.md` - Scheduler layer

---

## Phase 8: Validation & Polish

**Goal**: End-to-end testing and refinement

**Scope**:
- Test all 5 cases
- Verify change detection accuracy
- Test error scenarios
- Refine notification formatting
- Documentation for ongoing use

---

## Phase 9: JSON Response Logging (COMPLETED)

**Goal**: Implement comprehensive logging of raw JSON responses received from inpol.mazowieckie.pl API endpoints to enable detailed post-execution analysis.

**Scope**:
- Status Dictionary Endpoint - Log raw JSON from /assets/i18n/{lang}.json
- Case Data Endpoint - Log raw JSON from /api/proceedings/{case_id}
- Attachments Endpoint - Log raw JSON from /api/proceedings/getRequiredAttachments
- Questions List Endpoint - Log raw JSON from /api/proceedings/{case_id}/questions
- Question Details Endpoint - Log raw JSON from /api/proceeding-question/{question_id}

**Plans**: 1 plan

**Plan list**:
- [x] 01-PLAN.md — JSON response logging implementation

**Artifacts**:
- `src/config.py` - JSON logging configuration function
- `src/tools/json_logger.py` - JSON response logger utility
- `src/scraper.py` - Modified scraper with JSON logging integration
- `.env.example` - Updated example environment file
- `logs/json_responses.log` - Structured JSON log file (when enabled)
- `.planning/phases/09-json-response-logging/01-SUMMARY.md` - Phase summary

---

## Phase 10: Email Notifications (COMPLETED)

**Goal**: Implement email notifications as a fallback mechanism for when Telegram notifications fail or as an alternative notification channel.

**Scope**:
- Email notification configuration in config.py
- Email notification utility module (src/email_notifier.py)
- Integration with existing Telegram notifier
- Environment variable documentation in .env.example

**Plans:** 1 plan

**Plan list:**
- [x] 01-PLAN.md — Email notification configuration, utility, and fallback integration

**Requirements:**
- EMAIL-01: Email notification configuration
- EMAIL-02: Email notification utility
- EMAIL-03: Notifier integration with fallback
- EMAIL-04: Environment variable documentation
- EMAIL-05: Backward compatibility

**Artifacts:**
- `src/config.py` - get_email_enabled(), get_smtp_config()
- `src/email_notifier.py` - EmailNotifier with fallback + combined sending
- `src/notifier.py` - TelegramNotifier integration with email fallback
- `.env.example` - SMTP environment variables documented
- `tests/test_email_notifier.py` - 11 tests passing

---

## Phase 11: Web Application

**Goal**: Build Flask web application for viewing and comparing historical case snapshots

**Scope**:
- Flask web framework with session-based authentication
- List all snapshots with case_id and date range filtering
- Compare two snapshots side-by-side
- Print-friendly comparison view
- Reuse existing SnapshotRepository from storage.py

**Plans:** 1 plan

**Plan list:**
- [x] 11-01-PLAN.md — Flask web app with auth, routes, templates (WEB-01, WEB-02, WEB-03, WEB-04)

---

## Phase 12: Enhanced Question Comparison

**Goal**: Improve snapshot comparison for questions endpoint to display all question fields and detect field-level changes

**Scope**:
- Display all question fields in comparison view (status_label, answer, responseTime)
- Detect changes to individual question fields (status changes, answer appearing)
- Add localization labels for comparison fields
- Highlight field-level changes in the UI

**Plans:** 1/1 plans complete

**Plan list:**
- [ ] 01-PLAN.md — Enhanced question comparison with field-level diff (COMP-01, COMP-02, COMP-03)

---

## Future Milestones

### M2: Enhancements (Backlog)

- Case deadline reminders
- Monthly summary reports
- Export functionality

---

## Summary

| Phase | Status | Tests | Notes |
|-------|--------|-------|-------|
| Phase 01: Authentication | Complete | 54 tests | Sequential auth, CSRF, session mgmt |
| Phase 02: Data Extraction | Complete | 46 tests | Scraper, models, status resolution |
| Phase 03: Data Storage | Verified | 17 tests | SQLite, INSERT-only, indexes |
| Phase 04: Change Detection | Complete | 20 tests | 7 change types, Strategy pattern |
| Phase 05: Telegram Notifications | Verified | 11 tests | aiogram 3.x, HTML formatting |
| Phase 06: Orchestration | Complete | - | Full pipeline wired, error handling |
| Phase 07: Scheduler | Complete | - | run_check.cmd, schtasks setup |
| Phase 08: Validation & Polish | Complete | 19 tests | Golden file validation, failure scenario tests |
| Phase 09: JSON Response Logging | Complete | - | Enhanced observability with API response logging |
| Phase 10: Email Notifications | Complete | 11 tests | Email fallback for notifications |
| Phase 11: Web Application | Complete | - | Flask web app for snapshot viewing and comparison |
| Phase 12: Enhanced Question Comparison | Verified | 7 tests | Field-level question comparison with translations |

**Total: 162 tests passing**

---

*Last updated: 2026-07-09 - Phases 03, 05, 12 verified*

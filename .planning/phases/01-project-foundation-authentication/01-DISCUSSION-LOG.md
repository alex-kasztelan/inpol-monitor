# Phase 1: Project Foundation & Authentication - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-27
**Phase:** 01-project-foundation-authentication
**Areas discussed:** Project structure, Authentication flow, Credential management, Testing approach

---

## Project Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Flat - all modules in root | check.py, auth.py, scraper.py, storage.py, notifier.py in root + .env, requirements.txt | |
| Organized - src/ with subdirs | Organized: src/ for Python modules, data/ for SQLite, logs/ for output | ✓ |
| Package - installable Python package | src/inpol_monitor/ with __init__.py, setup.py for pip install | |

**User's choice:** Organized - src/ with subdirs

**Notes:** Architecture doc recommends this approach. Flat structure would work for a simple script but organized is preferred for maintainability.

---

## Authentication Flow

| Option | Description | Selected |
|--------|-------------|----------|
| Sequential - one account at a time | Login to account 1, fetch 3 cases, logout. Login to account 2, fetch 2 cases, logout. Simple, sequential. | ✓ |
| Parallel sessions - both accounts first | Login to both accounts first, keep both sessions active, fetch all 5 cases, then logout both. | |
| Session manager - switch accounts in same object | Single session object that can switch between accounts, reusable across the check cycle | |

**User's choice:** Sequential - one account at a time

**Notes:** Simpler implementation, matches the batch-then-notify architecture pattern.

---

## Auth Session Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Standard flow - CSRF + POST + verify | Extract CSRF from login page, POST credentials, save session cookies, verify login succeeded | |
| With auto-retry - one retry on failure | Try login, if fails retry once with fresh session before reporting error | |
| Session reuse - skip login if valid session exists | Check if session cookie exists and is valid before attempting fresh login | ✓ |

**User's choice:** Session reuse - skip login if valid session exists

**Notes:** Reduces unnecessary login requests, faster execution when sessions are still valid.

---

## Credential Management

| Option | Description | Selected |
|--------|-------------|----------|
| Single .env - all 4 values | INPOL_USERNAME_1, INPOL_PASSWORD_1, INPOL_USERNAME_2, INPOL_PASSWORD_2 - all in one .env | |
| Named accounts - ACCOUNT_1_*, ACCOUNT_2_* | ACCOUNT_1_USERNAME, ACCOUNT_1_PASSWORD (for account 1), ACCOUNT_2_* (for account 2) - clearer naming | |
| JSON file - structured credentials | credentials.json with {"account1": {...}, "account2": {...}} - structured but more complex | ✓ |

**User's choice:** JSON file - structured credentials

**Notes:** More scalable if accounts increase, easier to parse programmatically.

---

## Credential Validation

| Option | Description | Selected |
|--------|-------------|----------|
| Strict - fail fast if any missing | Fail immediately with clear error: "Missing INPOL_USERNAME_1" - no check runs without all credentials | |
| Lenient - warn but continue with what's available | Warning but allow running with subset - useful for testing one account at a time | ✓ |

**User's choice:** Lenient - warn but continue with what's available

**Notes:** Enables testing with one account while credentials for the other are being set up.

---

## Testing Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Real credentials - test live | Use your real 2 accounts and 5 cases from day 1 - test against real portal | |
| Mock first - test parsing without live site | Start with mocked HTML responses to verify parsing logic, switch to real credentials later | |
| Hybrid - record real responses, replay for testing | Hybrid: real auth + save HTML snapshots to replay tests offline | ✓ |

**User's choice:** Hybrid - record real responses, replay for testing

**Notes:** Best of both worlds - real data for accuracy, offline replay for fast iteration.

---

## Progress Output

| Option | Description | Selected |
|--------|-------------|----------|
| Print statements - simple CLI output | print() statements showing login progress, then exit - simplest approach | |
| Logging module - structured logs | Python logging module with INFO/DEBUG levels, configurable via env | |
| Verbose flag - optional detailed output | Verbose flag (-v) that toggles detailed output vs silent mode | ✓ |

**User's choice:** Verbose flag - optional detailed output

**Notes:** Silent by default for scheduled runs, verbose for debugging.

---

## Claude's Discretion

- Specific directory names within src/ (e.g., `src/auth/` vs `src/`)
- Exact JSON structure for credentials (as long as it covers both accounts)
- Logging library choice (standard `logging` module vs third-party)
- Session validity check implementation (time-based expiry vs request-based)

## Deferred Ideas

None - all discussion stayed within Phase 1 scope.

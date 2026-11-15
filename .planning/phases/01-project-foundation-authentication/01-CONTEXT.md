# Phase 1: Project Foundation & Authentication - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Set up project structure, dependencies, and authentication flow for both inpol.mazowieckie.pl accounts. This phase delivers:
- Working project structure with organized src/ layout
- Authentication module that logs into both accounts sequentially
- Session management with reuse capability
- Manual CLI trigger for testing auth flow

**Out of scope:** Data extraction, storage, notifications - those are Phases 2-5.

</domain>

<decisions>
## Implementation Decisions

### Project Structure
- **D-01:** Organized structure with `src/` directory for Python modules
- **D-02:** Separate directories for `data/` (SQLite database) and `logs/` (execution logs)
- **D-03:** Root-level entry point `check.py` for CLI execution

### Authentication Flow
- **D-04:** Sequential authentication - login to account 1, fetch 3 cases, logout, then login to account 2, fetch 2 cases, logout
- **D-05:** Session reuse - check if valid session exists before attempting fresh login
- **D-06:** Standard login flow: extract CSRF from login page, POST credentials, save session cookies, verify login succeeded

### Credential Management
- **D-07:** JSON file (`credentials.json`) for structured credentials with format: `{"account1": {...}, "account2": {...}}`
- **D-08:** Lenient validation - warn but continue if some credentials are missing (useful for testing one account at a time)

### Testing Approach
- **D-09:** Hybrid testing - use real credentials to record HTML responses, then replay offline for parsing tests
- **D-10:** Verbose flag (`-v`) toggles detailed output vs silent mode

### Claude's Discretion
- Specific directory names within src/ (e.g., `src/auth/` vs `src/`)
- Exact JSON structure for credentials (as long as it covers both accounts)
- Logging library choice (standard `logging` module vs third-party)
- Session validity check implementation (time-based expiry vs request-based)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture
- `.planning/research/ARCHITECTURE.md` - Auth layer design patterns, session management, Repository pattern

### Requirements
- `.planning/PROJECT.md` - AUTH-01 (authenticate 2 accounts), AUTH-02 (store credentials securely)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None - greenfield project

### Established Patterns
- None - first phase

### Integration Points
- inpol.mazowieckie.pl login endpoint
- Windows filesystem for credentials and database

</code_context>

<specifics>
## Specific Ideas

- User has existing Telegram bot (for future phases)
- 5 total cases: 3 in account 1, 2 in account 2
- Portal URL: https://inpol.mazowieckie.pl/

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 01-project-foundation-authentication*
*Context gathered: 2026-03-27*

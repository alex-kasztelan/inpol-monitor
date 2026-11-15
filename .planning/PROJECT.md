# Inpol Monitor

## What This Is

An automated monitoring system for the Polish government portal (inpol.mazowieckie.pl) that checks 5 immigration cases across 2 accounts on a schedule and notifies the user of any changes via Telegram.

## Core Value

Reliable, timely detection of any changes to immigration case statuses, documents, or deadlines — so the user never misses an important update.

## Requirements

### Validated

- [x] **AUTH-01**: Authenticate to inpol.mazowieckie.pl with username/password for 2 separate accounts (Phase 01)
- [x] **AUTH-02**: Store credentials securely in .env file (Phase 01)
- [x] **DATA-01**: Pull case data for all 5 cases (3 from account 1, 2 from account 2) (Phase 02)
- [x] **DATA-02**: Extract status, last update date, documents list, and decision deadline for each case (Phase 02)
- [x] **STORE-01**: Save snapshots to SQLite database with timestamp (Phase 02)
- [x] **STORE-02**: Retain all historical snapshots indefinitely (Phase 02)
- [x] **STORE-03**: Query snapshots by case_id only (case_id is unique across all accounts)

### Active

- [ ] **DETECT-01**: Compare current data with previous snapshot for each case (Phase 04)
- [ ] **DETECT-02**: Detect status changes, new documents, and date modifications (Phase 04)
- [ ] **NOTIFY-01**: Send detailed change report to Telegram private chat (Phase 05) ✅
- [ ] **NOTIFY-02**: Include case identifier and specific changes in notification (Phase 05) ✅
- [ ] **SCHED-01**: Run automated checks at 8:00, 12:30, and 18:00 Poland time (CET/CEST)
- [ ] **SCHED-02**: Integrate with Windows Task Scheduler for automation
- [ ] **SCHED-03**: Support manual on-demand checks via CLI option
- [ ] **ERROR-01**: Send error notification to Telegram when check fails (site down, login fails)

### Out of Scope

- Web UI or dashboard — CLI-only tool, run locally
- Multi-user support — single user, private Telegram notifications
- Screenshot capture — text-based detailed reports only
- Paid services — free tier only (user has existing Telegram bot)

## Context

- **Portal**: https://inpol.mazowieckie.pl/ — Polish government immigration case management system
- **Accounts**: 2 separate accounts with username/password authentication
- **Cases**: 5 total cases (3 in account 1, 2 in account 2)
- **Deployment**: Local Windows machine
- **Check frequency**: 3 times daily at Poland timezone

## Constraints

- **Tech stack**: Python script — user preference
- **Deployment**: Windows local machine — must work with Windows Task Scheduler
- **Budget**: Free only — no paid services or hosting
- **Storage**: SQLite — lightweight, file-based database

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python | User preference, good for scripting | — Pending |
| SQLite | Lightweight, no setup needed, persists all history | — Pending |
| Windows Task Scheduler | Matches deployment environment | — Pending |
| .env file for credentials | Simple, standard practice for local scripts | — Pending |
| Single batch check | All 5 cases checked together, not grouped by account | — Pending |
| Detailed Telegram reports | User wants full change details, not just summaries | — Pending |
| case_id unique across system | Case IDs are globally unique — no account_id filtering needed in snapshot queries | Validated |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-26 after initialization*

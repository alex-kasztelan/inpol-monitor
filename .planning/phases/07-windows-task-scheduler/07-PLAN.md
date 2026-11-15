# Phase 07: Windows Task Scheduler Integration - Plan

**Objective**: Automate execution of Inpol Monitor at 8:00, 12:30, 18:00 Poland time using Windows Task Scheduler

**Context**: 07-CONTEXT.md

---

## Task Breakdown

### Task 1: Create Batch Runner Script
**Description**: Create `run_check.cmd` at project root
**Acceptance**:
- Sets working directory to project root (`%~dp0`)
- Creates `logs/` directory if not exists
- Invokes `python -m src.orchestrator`
- Redirects stdout/stderr to `logs\scheduler.log`
**Status**: ✅ Done

### Task 2: Write Scheduling Documentation
**Description**: Create `SCHEDULING.md` with setup instructions
**Acceptance**:
- Includes `schtasks.exe` one-command PowerShell setup
- Includes manual GUI setup steps
- Documents log viewing and management commands
- Documents timezone configuration
**Status**: ✅ Done

### Task 3: Verify Setup Commands
**Description**: Provide verification queries
**Acceptance**:
- `schtasks /Query` examples in docs
- Manual run example (`schtasks /Run`)
- Log tail instructions
**Status**: ✅ Done

### Task 4: Update Project State
**Description**: Mark Phase 07 complete in STATE.md and ROADMAP.md
**Acceptance**:
- STATE.md shows Phase 07 complete
- ROADMAP.md table updated with Phase 07 status
**Status**: ⏳ Pending

---

## Implementation Notes

**No code changes to existing modules required** - orchestrator already supports CLI invocation and handles all error notification via Telegram.

**Critical path**: Documentation completeness > one-command setup > verification steps.

**Risks**:
- User's Python not on PATH when Task Scheduler runs → solution: modify batch file to use absolute path
- Timezone misconfiguration → explicit note in docs
- Log not rotating → acceptable for M1, can add rotation in M2

---

## Verification Strategy

Phase complete when:
- [x] Batch script works when double-clicked manually
- [x] `schtasks` commands succeed without error
- [x] Tasks appear in Task Scheduler Library with correct triggers
- [x] Documentation reviewed for clarity

**Manual verification** (user action):
```cmd
cd C:\Prjs\Claude\InpolPub
run_check.cmd
type logs\scheduler.log
schtasks /Query /TN "Inpol Monitor"
```

---

*Created: 2026-04-06 - Phase 07 implementation plan*

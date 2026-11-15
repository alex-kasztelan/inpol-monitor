# Phase 07: Windows Task Scheduler - Context

**Phase Goal**: Automated execution at 8:00, 12:30, 18:00 Poland time

---

## Decisions Locked

### 1. Invocation Method
**Decision**: Use a `.bat` batch file wrapper that invokes `python -m src.orchestrator`

**Rationale**:
- Simplest approach for Windows Task Scheduler
- No PowerShell execution policy complications
- Orchestrator already supports CLI invocation via `python -m src.orchestrator`

### 2. Working Directory
**Decision**: Batch file sets working directory to project root before execution

**Rationale**:
- Ensures `.env` file is loaded correctly
- Ensures `data/snapshots.db` path resolves correctly
- Avoids absolute path brittleness

### 3. Schedule Configuration
**Decision**: Three daily triggers at Poland time (CET/CEST)
- 8:00 AM
- 12:30 PM  
- 6:00 PM

**Timezone**: `(UTC+01:00) Warsaw` in Task Scheduler

### 4. Logging Approach
**Decision**: Append stdout/stderr to `logs/scheduler.log`

**Rationale**:
- Persistent log for troubleshooting
- Separate from interactive CLI logging
- Rotating file handler can be added later if needed

### 5. Error Handling
**Decision**: Orchestrator already sends Telegram error notifications via `notifier.on_error()`

**Rationale**:
- No additional error handling needed in scheduler wrapper
- User gets notified immediately if check fails

### 6. Python Environment
**Decision**: Use system Python (assumes user runs from activated venv or has dependencies installed)

**Rationale**:
- User can configure Task Scheduler to run with specific Python executable
- Batch file can be modified to use absolute Python path if needed

---

## Implementation Constraints

### Must-Have
- [ ] Batch file at project root: `run_check.bat`
- [ ] Task Scheduler XML export for easy import (optional but helpful)
- [ ] Documentation: step-by-step manual task creation guide
- [ ] Log directory created if not exists

### Nice-to-Have
- [ ] PowerShell alternative script for advanced users
- [ ] Task Scheduler GUI screenshots in documentation
- [ ] Test mode: manual trigger to verify task works

---

## Technical Notes

### Batch File Template
```batch
@echo off
cd /d "%~dp0"
mkdir logs 2>nul
python -m src.orchestrator >> logs\scheduler.log 2>&1
```

### Task Scheduler Requirements
- **Action**: `run_check.bat` or `schtasks /Create /TN "Inpol Monitor" /TR "...\run_check.bat" ...`
- **Triggers**: Daily at 08:00, 12:30, 18:00
- **Settings**: "Run whether user is logged on or not", "Run with highest privileges"
- **Conditions**: Uncheck "Start only if on AC power" for laptops

### Timezone Handling
- Task Scheduler runs in local system time
- User must ensure Windows timezone is set to `(UTC+01:00) Warsaw`
- No code changes needed for CET/CEST automatic adjustment

---

## Deferred Ideas

| Idea | Reason |
|------|--------|
| PowerShell script with email on failure | Batch file + Telegram errors sufficient for M1 |
| Log rotation | Can add later if logs grow large |
| Health check dashboard | Nice-to-have for M2 |
| SMS fallback | Telegram sufficient for now |

---

## Downstream Guidance

**For Researcher**:
- Investigate Windows Task Scheduler `schtasks.exe` command-line syntax
- Look up best practices for Python script automation on Windows
- Research common pitfalls (Python path, working directory, environment variables)

**For Planner**:
- Task 1: Create `run_check.bat` batch file
- Task 2: Create `logs/` directory structure
- Task 3: Write documentation with screenshots
- Task 4: Provide `schtasks` command for advanced users
- Task 5: Test and verify scheduled execution

---

*Created: 2026-04-06 - Phase 07 context for Windows Task Scheduler integration*

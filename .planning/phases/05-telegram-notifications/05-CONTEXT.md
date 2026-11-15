# Phase 05: Telegram Notifications - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase implements Telegram notification integration for the Inpol Monitor. It provides:
- Telegram bot integration using aiogram 3.x
- Markdown-formatted change notification messages
- Error notifications when checks fail
- Integration with existing notifier pattern

**What this phase does NOT do:**
- Change detection logic (Phase 04)
- Windows Task Scheduler (Phase 07)
- Main orchestrator (Phase 06)
</domain>

<decisions>
## Implementation Decisions

### Telegram Library Selection
- **D-01:** Use **aiogram 3.x** for Telegram integration
  - Async-first architecture
  - Active development and good documentation
  - Recommended in `.planning/research/ARCHITECTURE.md`
  - Built-in bot handlers and error handling

### Message Format
- **D-02:** Use **Markdown** formatting for notifications
  - Bold text (`**text**`)
  - Italic text (`*text*`)
  - Lists (`- items`)
  - Standard for Telegram alerts

### Error Notification Conditions
- **D-03:** Notify for **both changes and errors**
  - Send notification when status changes detected
  - Send notification when check fails (site down, login fails, API errors)
  - ERROR-01 requirement: Send error notification to Telegram when check fails

### Telegram Bot Setup
- **D-04:** Create **new bot** via @BotFather
  - Full control over bot configuration
  - Clean separation from user's existing Telegram setup
  - New bot token stored in `.env` file

## Folded Todos

### Phase 02: Database Configuration
- **Stored:** `Create credentials.json with real credentials for live testing`
  - Will be needed for Telegram bot authentication

## Deferred Ideas

### None
- Discussion stayed within phase scope

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specifications
- `.planning/PROJECT.md` — Project requirements and Telegram notification requirements (NOTIFY-01, NOTIFY-02, ERROR-01)
- `.planning/ROADMAP.md` — Phase 05 scope and deliverables
- `.planning/STATE.md` — Current progress and session continuity

### Architecture Documents
- `.planning/research/ARCHITECTURE.md` — Notifier layer pattern, component boundaries, data flow

### Phase 04 References
- `.planning/phases/04-change-detection/01-CONTEXT.md` — Change detection structure and outputs
- `src/detector.py` — Change model and detector outputs

### Key Links
- `src/notifier.py` — Telegram notification class
- `src/models.py::Change` — Change model for notification data
- `.env` — Bot token and Telegram configuration
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/detector.py::Change` — Change model with type, old_value, new_value, description
- `src/models.py::Snapshot` — Snapshot structure for data comparison
- `src/storage.py::SnapshotRepository` — Database access for previous snapshots

### Established Patterns
- Repository pattern for storage
- Strategy pattern for detectors
- Batch-Then-Notify architecture from ARCHITECTURE.md
- Async/await pattern from aiogram 3.x

### Integration Points
- `src/detector.py::detect_all_changes()` — Provides change list for notifications
- `src/orchestrator.py` — Will integrate notifier after detection
- `.env` — Bot token and environment configuration

</code_context>

<specifics>
## Specific Ideas

### Notification Message Format
```
# [Case ID] Changes Detected

## Summary
- {N} changes across {M} cases

### Case Details

**{Case ID}**
- Status: {old} → {new}
- New document: {filename}

**Case ID:** {case_id}
```

### Error Notification Format
```
# [Case ID] Check Failed

## Error Details
- {error_type}: {error_message}
- {timestamp}: Check execution failed

**Case ID:** {case_id}
```

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-telegram-notifications*
*Context gathered: 2026-04-02*

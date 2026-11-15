# Phase 03: Data Storage - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-01
**Phase:** 03-data-storage
**Areas discussed:** Query strategy, Snapshot structure, Notification timing, Database path

---

## Query Strategy for Change Detection

| Option | Description | Selected |
|--------|-------------|----------|
| Latest by (case_id, endpoint_type) | Query most recent snapshot for each case | ✓ |
| Track last fetch timestamp | Query snapshots before last_fetched time | |
| Use a 'last_check' field | Add last_check field, compare against current time | |

**User's choice:** Latest by (case_id, endpoint_type)
```sql
SELECT * FROM snapshots WHERE case_id=? AND endpoint_type=? ORDER BY timestamp DESC LIMIT 1
```
Returns the same snapshot if nothing changed between checks. Simple implementation, matches Phase 02 pattern.

**Notes:** The query returns the most recent snapshot for each case/endpoint combination. This means if the first check runs and no data has been added, subsequent checks will return that same snapshot. This is acceptable for our use case where we're comparing against the initial snapshot.

---

## Snapshot Structure: What Should Be Compared

| Option | Description | Selected |
|--------|-------------|----------|
| Raw JSON only | Byte-for-byte comparison | |
| Parsed data only | Structural comparison, ignores raw JSON format | |
| Both - raw for integrity, parsed for readability | Double verification | ✓ |

**User's choice:** Both - raw for integrity, parsed for readability
- Use raw JSON for integrity verification
- Use parsed data for human-readable diffs

**Notes:** Double verification ensures accuracy while maintaining readability. Raw JSON catches schema changes, while parsed data provides meaningful diffs for the user.

---

## Notification Timing: When Should Notifications Be Sent

| Option | Description | Selected |
|--------|-------------|----------|
| Immediately after each check | Real-time but spammy with 3x daily checks | |
| Batch all changes, one per check time | One notification per cycle at 8:00, 12:30, 18:00 | ✓ |
| Dedupe changes, one notification per day | Collect all changes, send one regardless of time | |

**User's choice:** Batch all changes, one per check time
- Aggregate changes from all 3 checks
- One notification per check cycle

**Notes:** This balances real-time response with user experience. The user gets notified at their scheduled check times, but with consolidated information.

---

## Database Storage Location

| Option | Description | Selected |
|--------|-------------|----------|
| Project root (data/) | Matches Phase 02 implementation | ✓ |
| User home directory | Better security, but requires path updates | |
| App directory with accounts | Most organized, but most complex | |

**User's choice:** Project root (data/)
- Matches Phase 02 implementation
- Simple path, no configuration needed

**Notes:** Keeping the database in the project root maintains consistency with Phase 02 and requires no additional configuration.

---

## Claude's Discretion

None — all decisions captured above

---

## Deferred Ideas

None — discussion stayed within phase scope

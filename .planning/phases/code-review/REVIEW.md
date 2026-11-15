---
phase: code-review
reviewed: 2026-07-15T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - src/notifier.py
  - src/email_notifier.py
  - src/detector.py
findings:
  critical: 1
  warning: 4
  info: 2
  total: 7
status: issues_found
---

# Phase Code Review: Status Field Threading

**Reviewed:** 2026-07-15
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed the `status` field threading across `detector.py → notifier.py → email_notifier.py`. The main notification path (`on_change` → `send_all_notifications` → `_build_single_message`) correctly threads the status. However, there is an HTML injection vulnerability in all email output paths, a status-field gap in the single-case Telegram notification path, and several dead code artifacts from the implementation.

## Critical Issues

### CR-01: HTML Injection in Email Notifications — User-Controlled Data Rendered as Raw HTML

**File:** `src/email_notifier.py:205-221`
**File:** `src/notifier.py:670-687`

**Issue:** All user-controlled values (`case_id`, `account_id`, `case_type`, `person_first`, `status`, `status_label`, `error_message`, change values) are interpolated directly into HTML strings via f-strings without any escaping. Since these values originate from scraped web data (the Inpol portal), a specially crafted status text, case type, or error message containing `<script>` tags or HTML attributes could execute in the recipient's email client (stored XSS via email).

**Affected code paths:**

1. `_format_change_email()` in `email_notifier.py:202-221` — single-case email
2. `_build_single_message()` in `notifier.py:670-687` — used as `html_body` for both Telegram HTML and combined email via `send_combined_notification()`
3. `_format_error_email()` in `email_notifier.py:242-253` — error email (same pattern)

No `html.escape()` is imported or used anywhere in the project. The project has zero HTML escaping.

**Fix:** Use `html.escape()` on all user-controlled values before interpolation:

```python
import html

# In _format_change_email:
safe_case_id = html.escape(str(case_id))
safe_account = html.escape(str(account_id))
safe_status = html.escape(str(status))
safe_status_label = html.escape(str(status_label))
safe_type = html.escape(str(case_type))
safe_person = html.escape(str(person_first))

html = f"""<html>
<body>
<h2>Inpol Case Update</h2>
<p><strong>Case ID:</strong> {safe_case_id}</p>
<p><strong>Account:</strong> {safe_account}</p>
<p><strong>Type:</strong> {safe_type}</p>
<p><strong>Status:</strong> {safe_status} - {safe_status_label}</p>
<p><strong>Person:</strong> {safe_person}</p>
"""
# Apply same pattern to all interpolated values in change descriptions
```

The same treatment is needed in `_build_single_message()` and `_format_error_email()`.

## Warnings

### WR-01: Status Field Not Included in Single-Case Telegram Message (`_build_change_message`)

**File:** `src/notifier.py:430-443` and `src/notifier.py:577`

**Issue:** `send_change_notification()` accepts `status: str = ""` (line 430) and `send_change_notification_sync()` passes it through (line 485), but `send_change_notification()` calls `_build_change_message()` (line 443) which does **not** accept or use a `status` parameter. The Telegram message produced in the single-case path silently omits the status field.

This is inconsistent with `_build_single_message()` (line 684) which does render status. The batch path works; the single-case path loses the data.

**Fix:** Add `status` parameter to `_build_change_message()` and render it in the message:

```python
def _build_change_message(self, account_id, case_id, changes, total_changes,
                          case_type="", person_first="", status=""):
    # ... existing code ...
    if status:
        status_label = _t(f'Cases.States.{status}', status)
        message += f"  Status: {status} - {status_label}\n"
    # ...
```

And update the call at line 443:
```python
message = self._build_change_message(account_id, case_id, changes, total_changes,
                                      case_type, person_first, status)
```

### WR-02: `_send_fallback_email()` Omits `status` When Calling Email Notifier

**File:** `src/notifier.py:751-757`

**Issue:** `_send_fallback_email()` iterates over `CaseInfo` objects (which have `.status`) but does not pass `status` to `email_notifier.send_change_notification()`. The status field is available on each `case` object but is silently dropped.

**Fix:**
```python
self.email_notifier.send_change_notification(
    account_id=case.account_id,
    case_id=case.case_id,
    case_type=case.case_type,
    person_first=case.person_first,
    changes=changes_dicts,
    status=case.status,  # <-- add this
)
```

### WR-03: Duplicate `_env_values` and `get_env` Definitions

**File:** `src/notifier.py:33-60` and `src/notifier.py:63-90`

**Issue:** `_env_values = {}` is defined at line 33 and redefined at line 63. `get_env()` is defined at lines 36-60 and then completely redefined (identical implementation) at lines 66-90. The second definition silently shadows the first. This is dead code that appears to be a merge/duplication artifact and makes the module confusing to maintain.

**Fix:** Remove the first definition block (lines 33-60) and keep only lines 63-90.

### WR-04: Unused `case_info` Variable in `send_change_notification_sync()`

**File:** `src/notifier.py:494-502`

**Issue:** A `CaseInfo` object is constructed but never used after assignment. The status is passed separately to the email notifier at line 509. This is dead code that adds confusion.

```python
case_info = CaseInfo(       # <-- this object is never referenced again
    case_id=case_id,
    account_id=account_id,
    case_type=case_type,
    person_first=person_first,
    changes=changes,
    total_changes=total_changes,
    status=status
)
```

**Fix:** Remove the unused `case_info` construction, or use it (e.g., pass to a unified email method).

## Info

### IN-01: Duplicate `from datetime import datetime` Import

**File:** `src/notifier.py:784`

**Issue:** `datetime` is already imported at line 9 (`from datetime import datetime, timezone`). The redundant import at line 784 is unnecessary.

**Fix:** Remove line 784.

### IN-02: `_build_change_message()` Docstring Says "Plain Text" But Uses HTML Tags

**File:** `src/notifier.py:578-580`

**Issue:** The docstring states "Format is plain text (no Markdown/HTML) for better compatibility across Telegram clients" but the function uses `<b>` tags (lines 600-601). The docstring is misleading.

**Fix:** Update the docstring to reflect that HTML formatting is used (consistent with `parse_mode=ParseMode.HTML` in callers).

---

_Reviewed: 2026-07-15_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_

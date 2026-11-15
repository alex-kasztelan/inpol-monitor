---
phase: 10-next-steps
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/config.py
  - src/email_notifier.py
  - src/notifier.py
  - .env.example
autonomous: true
requirements:
  - EMAIL-01
  - EMAIL-02
  - EMAIL-03
  - EMAIL-04
  - EMAIL-05
user_setup:
  - service: email notifications
    why: "Need to configure email server settings for fallback notifications"
    manual_steps:
      - "Add SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO to .env"
      - "Set EMAIL_ENABLED=true to enable email notifications"
must_haves:
  truths:
    - "Email notifications sent when Telegram notifications fail"
    - "Email notifications sent when EMAIL_ENABLED=true regardless of Telegram status"
    - "Email contains formatted change details with case information"
    - "No email sent when EMAIL_ENABLED=false or unset"
    - "Existing Telegram functionality unchanged"
  artifacts:
    - path: "src/config.py"
      provides: "Email configuration functions"
      exports: ["get_email_enabled", "get_smtp_config"]
    - path: "src/email_notifier.py"
      provides: "Email notification utility class"
      exports: ["EmailNotifier"]
    - path: "src/notifier.py"
      provides: "Modified notifier with email fallback"
    - path: ".env.example"
      provides: "Updated example environment file"
  key_links:
    - from: "src/config.py:get_email_enabled"
      to: "src/notifier.py:TelegramNotifier.__init__"
      via: "configuration check"
    - from: "src/email_notifier.py:EmailNotifier"
      to: "src/notifier.py:TelegramNotifier"
      via: "email notifier initialization"
    - from: "src/notifier.py:TelegramNotifier.on_change"
      to: "src/email_notifier.py:EmailNotifier.send_change_notification"
      via: "fallback email sending"
---

<objective>
Implement email notifications as a fallback mechanism for when Telegram notifications fail or as an alternative notification channel.

Purpose: Enhance system reliability by providing multiple notification channels
Output: Email notification module integrated with existing Telegram notifier
</objective>

<context>
@.planning/phases/10-next-steps/01-overview.md
@.planning/STATE.md

Phase 09 JSON Response Logging complete - System validated and ready for production. Phase 10 enhances reliability by adding email notifications as a backup channel.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add email configuration functions</name>
  <files>src/config.py</files>
  <action>
- Add get_email_enabled() function to check EMAIL_ENABLED environment variable (convert to boolean, defaults to False)
- Add get_smtp_config() function to retrieve SMTP server settings from environment
- Return appropriate defaults when variables unset or invalid
- Follow existing configuration patterns in config.py
  </action>
  <verify>
    <automated>python -c "from src.config import get_email_enabled, get_smtp_config; print(get_email_enabled()); print(get_smtp_config())"</automated>
  </verify>
  <done>Configuration functions exist and return correct values, defaults to False when unset</done>
</task>

<task type="auto">
  <name>Task 2: Create EmailNotifier utility class</name>
  <files>src/email_notifier.py</files>
  <action>
- Create EmailNotifier class with __init__ accepting SMTP config
- Implement send_change_notification(changes: list) method - formats and sends HTML/plain text email
- Implement send_error_notification(error: str) method - sends error alert email
- Handle SMTP connection with proper error handling and logging
- Only send when credentials configured
  </action>
  <verify>
    <automated>python -c "from src.email_notifier import EmailNotifier; n = EmailNotifier({'host': 'localhost', 'port': 25}); print('EmailNotifier initialized')"</automated>
  </verify>
  <done>EmailNotifier class exists, initializes correctly, methods available</done>
</task>

<task type="auto">
  <name>Task 3: Integrate email fallback into TelegramNotifier</name>
  <files>src/notifier.py</files>
  <action>
- Import EmailNotifier and configuration functions
- Initialize email notifier in TelegramNotifier.__init__ when enabled
- In on_change method: try Telegram first, on failure try email fallback
- In on_error method: try Telegram first, on failure try email fallback
- Log when falling back to email
- Ensure existing behavior unchanged when email disabled
  </action>
  <verify>
    <automated>python -c "from src.notifier import TelegramNotifier; print('TelegramNotifier supports email fallback')"</automated>
  </verify>
  <done>Fallback logic integrated, TelegramNotifier works with email fallback</done>
</task>

<task type="auto">
  <name>Task 4: Update .env.example with email variables</name>
  <files>.env.example</files>
  <action>
- Add EMAIL_ENABLED=false comment with description
- Add SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO with descriptions
- Follow existing comment style in file
  </action>
  <verify>
    <automated>grep -q "EMAIL_ENABLED" .env.example && grep -q "SMTP_" .env.example</automated>
  </verify>
  <done>Email configuration documented in .env.example</done>
</task>

<task type="auto">
  <name>Task 5: Verify backward compatibility</name>
  <files>src/notifier.py, src/config.py</files>
  <action>
- Verify existing functionality works when EMAIL_ENABLED=false or unset
- Run existing test suite to confirm no regressions
- No email code runs when disabled
  </action>
  <verify>
    <automated>python -m pytest tests/ -x --tb=short 2>&1 | tail -20</automated>
  </verify>
  <done>All existing tests pass, no behavior change when email disabled</done>
</task>

</tasks>

<verification>
- EmailNotifier initializes without errors
- Configuration functions return correct defaults
- Integration with TelegramNotifier complete
- Backward compatibility verified
</verification>

<success_criteria>
- EMAIL_ENABLED=false or unset: System operates identically to Phase 09
- EMAIL_ENABLED=true: Email notifications sent alongside/instead of Telegram
- All 155+ existing tests continue passing
</success_criteria>

<output>
After completion, create `.planning/phases/10-next-steps/01-SUMMARY.md`
</output>
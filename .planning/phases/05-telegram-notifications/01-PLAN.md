---
phase: 05-telegram-notifications
plan: 01
type: tdd
wave: 1
depends_on:
  - 04-PLAN.md (Detector layer provides Change model and detect_all_changes())
files_modified:
  - src/notifier.py
  - requirements.txt
user_setup:
  - service: telegram
    why: "Bot token required for Telegram API access"
    dashboard_config:
      - task: "Create new bot via @BotFather, save token in .env"
        instructions: "/newbot username in .env (e.g., inpolmonpl_bot)"

must_haves:
  truths:
    - "Change notifications sent to Telegram with formatted Markdown" ✅
    - "Error notifications sent to Telegram when checks fail" ✅
    - "Notification includes case ID and specific change details" ✅
  artifacts:
    - path: "src/notifier.py"
      provides: "TelegramNotifier class with aiogram 3.x integration"
      exports: ["send_change_notification", "send_error_notification", "on_change", "send_all_notifications"]
      status: "Complete" ✅
    - path: "src/models.py::Change"
      provides: "Change model with type, old_value, new_value, description"
      exports: ["type", "old_value", "new_value", "description"]
  key_links:
    - from: "src/notifier.py::TelegramNotifier"
      to: "src/detector.py::detect_all_changes()"
      via: "Notification triggered on change detection"
      pattern: "notifier.on_change(account_name, case_id, changes)"
    - from: "src/notifier.py::TelegramNotifier"
      to: "src/storage.py::SnapshotRepository"
      via: "Error notification includes account_id and case_id"
      pattern: "repo.get_snapshot(account_id=...)"
---

<objective>
Implement Telegram notification layer using aiogram 3.x with Markdown-formatted messages for both change reports and error notifications.

Purpose: Fulfill NOTIFY-01, NOTIFY-02, ERROR-01 requirements by providing Telegram integration for the monitoring system.

Output:
- `src/notifier.py` - TelegramNotifier class with send_change_notification() and send_error_notification() methods
- `requirements.txt` update with aiogram 3.x dependency
- .env file with TELEGRAM_BOT_TOKEN (requires user setup via @BotFather)
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
From src/models.py::Change:
```python
class Change(BaseModel):
    type: ChangeType = Field(..., description="Type of change")
    old_value: Any = Field(..., description="Value from previous snapshot")
    new_value: Any = Field(..., description="Value from current snapshot")
    description: str = Field(..., description="Human-readable description")
```

From src/models.py::Snapshot:
```python
class Snapshot(BaseModel):
    account_id: str = Field(..., description="Account identifier")
    case_id: str = Field(..., description="Case identifier")
    raw_json: dict = Field(default_factory=dict, description="Full raw JSON response")
    parsed_data: dict = Field(default_factory=dict, description="Extracted fields")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
```

From .planning/research/ARCHITECTURE.md - Notifier Layer:
```
┌─────────────────────────────────────────────────────────────────┐
│                     NOTIFICATION LAYER                          │
│                  (Telegram: send change report)                 │
└─────────────────────────────────────────────────────────────────┘
```

From CONTEXT.md decisions:
- D-01: Use aiogram 3.x (async-first, recommended in ARCHITECTURE.md)
- D-02: Use Markdown formatting (`**bold**`, `*italic*`, `- lists`)
- D-03: Notify for both changes and errors
- D-04: Create new bot via @BotFather, token in .env

From CONTEXT.md - Change notification format:
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

From CONTEXT.md - Error notification format:
```
# [Case ID] Check Failed

## Error Details
- {error_type}: {error_message}
- {timestamp}: Check execution failed

**Case ID:** {case_id}
```
</context>

<interfaces>
TelegramNotifier contract:
- `__init__(self, token: str)` - Initialize with Bot token from .env
- `send_change_notification(self, account_id: str, case_id: str, changes: List[Change], total_changes: int) -> None` - Send formatted change notification
- `send_error_notification(self, account_id: str, case_id: str, error: Exception, error_type: str) -> None` - Send error notification

Change model contract (from models.py):
- `type: ChangeType` - Enum (status, new_document, date_change, etc.)
- `old_value: Any` - Previous value
- `new_value: Any` - Current value
- `description: str` - Human-readable description

Snapshot model contract (from models.py):
- `account_id: str` - Account identifier for error notifications
- `case_id: str` - Case identifier for error notifications
</interfaces>

<tasks>
<task type="tdd" files="src/notifier.py">
  <name>Task 0: Define TelegramNotifier interface with aiogram 3.x contract</name>
  <action>
    Create `src/notifier.py` with ChangeNotifier base class and TelegramNotifier implementation.
    
    - Import ChangeType from src.models (per D-03: use ChangeType enum)
    - Implement ChangeNotifier abstract base class with abstract methods:
      * `send_notification()` - Base method for all notification types
      * `format_message()` - Base method for message formatting
    - Implement TelegramNotifier extending ChangeNotifier:
      * __init__(token: str) - Store token, create Bot instance using aiogram 3.x
      * send_change_notification(account_id, case_id, changes, total_changes) - Build Markdown message per CONTEXT.md format, send via Bot.send_message()
      * send_error_notification(account_id, case_id, error, error_type) - Build error Markdown message per CONTEXT.md format, send via Bot.send_message()
      * on_change = lambda: send_change_notification(account_id, case_id, changes, len(changes)) - Callback hook for detector integration
    - Use aiogram 3.x Bot class (not python-telegram-bot 20.x)
    - Format messages using MarkdownV2 (aiogram 3.x standard)
    - Per D-04: Store token in self, loaded from .env
  </action>
  <verify>
    <automated>
      1. Create failing test: tests/test_notifier.py::TestTelegramNotifier::test_send_change_notification
         ```python
         async def test_send_change_notification(self):
             notifier = TelegramNotifier("test:token")
             # Verify Bot instance created
             assert isinstance(notifier.bot, aiogram.types.Bot)
             # Verify message sent (mocked)
             await notifier.send_change_notification("acc_1", "case_123", [Change(...)], 1)
             assert notifier.bot.messages[0]["chat"]["id"] == "123456"
         ```
      2. Verify aiogram import works:
         ```bash
         python -c "import aiogram; print(aiogram.__version__)"
         ```
    </automated>
  </verify>
  <done>
    src/notifier.py created with ChangeNotifier base class and TelegramNotifier implementation
    aiogram 3.x imported and Bot instance created
    send_change_notification() and send_error_notification() methods implemented
    Message formatting uses MarkdownV2 (per D-02)
    Token stored in .env (D-04 requires user setup)
  </done>
</task>

<task type="tdd" files="requirements.txt" behavior="
  - Test 1: aiogram import works and version is 3.x
  - Test 2: TelegramNotifier can be instantiated with token
  - Test 3: send_change_notification method exists and accepts Change list
  - Test 4: send_error_notification method exists and accepts Exception
">
  <name>Task 1: Update dependencies and create notifier tests</name>
  <files>requirements.txt, tests/test_notifier.py</files>
  <action>
    Update requirements.txt with aiogram==3.17.0 (aiogram 3.x, per D-01).
    
    Create tests/test_notifier.py with unit tests:
    - Test __init__ stores token correctly
    - Test send_change_notification constructs Markdown message per CONTEXT.md format
    - Test send_error_notification constructs error message per CONTEXT.md format
    - Verify Change model fields (type, old_value, new_value, description) used in formatting
    
    Run tests to verify:
    ```bash
    pytest tests/test_notifier.py -v
    ```
  </action>
  <verify>
    <automated>
      npm test not applicable - use:
      ```bash
      pytest tests/test_notifier.py -v
      ```
    </automated>
  </verify>
  <done>
    requirements.txt updated with aiogram 3.x
    Test file created with passing tests for TelegramNotifier
  </done>
</task>

</tasks>

<verification>
### Verify Bot Token Setup (User Required)
1. Create bot via @BotFather on Telegram:
   - Open Telegram, search for @BotFather
   - Send /newbot
   - Follow prompts: username (e.g., "inpol_monitor_bot"), token generation
2. Copy generated token to .env file:
   - Edit .env, add: `TELEGRAM_BOT_TOKEN=your_token_here`
3. Verify token loads:
   ```bash
   python -c "from dotenv import load_dotenv; from src.notifier import TelegramNotifier; load_dotenv(); t = TelegramNotifier(); print('OK')"
   ```

### Verify Notification Flow
1. Run orchestrator (after Phase 06 is complete) to trigger a check
2. Monitor Telegram for notifications
3. Verify change notification format matches CONTEXT.md specification
4. Verify error notification format matches CONTEXT.md specification
</verification>

<success_criteria>
- TelegramNotifier class implements aiogram 3.x integration
- send_change_notification() sends Markdown-formatted message with case ID and changes
- send_error_notification() sends Markdown-formatted error message
- Tests pass with aiogram 3.x import successful
- User has created bot via @BotFather with token in .env (D-04)
</success_criteria>

<output>
After completion, create `.planning/phases/05-telegram-notifications/01-SUMMARY.md`
</output>

<tool_call>
<function=Write>
<parameter=file_path>
C:\Prjs\Claude\InpolPub\.planning\phases\05-telegram-notifications\02-PLAN.md
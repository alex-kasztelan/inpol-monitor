---
phase: 05-telegram-notifications
plan: 03
type: auto
wave: 2
depends_on:
  - 01-PLAN.md (TelegramNotifier with send_error_notification method)
files_modified:
  - src/notifier.py
  - src/orchestrator.py
user_setup: []

must_haves:
  truths:
    - "Error notification sent to Telegram when check fails"
    - "ERROR-01 requirement satisfied: error notification on check failure"
  artifacts:
    - path: "src/notifier.py::TelegramNotifier.send_error_notification"
      provides: "Error notification method per CONTEXT.md format"
  key_links:
    - from: "src/orchestrator.py::Orchestrator"
      to: "src/notifier.py::TelegramNotifier.send_error_notification()"
      via: "Exception caught -> error notification sent"
      pattern: "try:\n    run_check()\nexcept Exception as e:\n    notifier.send_error_notification(...)"
---

<objective>
Integrate TelegramNotifier error notification into Orchestrator to send error messages when any check fails, fulfilling ERROR-01 requirement.

Purpose: Ensure all errors (site down, login fails, API errors) are notified via Telegram, not silently logged.

Output:
- `src/notifier.py` - TelegramNotifier.send_error_notification() method
- `src/orchestrator.py` - Exception handler wiring error notification
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
From src/models.py::Snapshot:
```python
class Snapshot(BaseModel):
    account_id: str
    case_id: str
    ...
```

From .planning/research/ARCHITECTURE.md - Error Flow:
```
At any step:
         │
   Exception caught
         │
   ┌───────────────────────────────────────┐
   │ Build error message:                  │
   │ "Check failed at [step]: [error]"     │
   └───────────────────────────────────────┘
         │
   Send error notification to Telegram
```

From CONTEXT.md - Error notification format:
```
# [Case ID] Check Failed

## Error Details
- {error_type}: {error_message}
- {timestamp}: Check execution failed

**Case ID:** {case_id}
```

From .planning/phases/05-telegram-notifications/01-PLAN.md (D-03):
> D-03: Notify for both changes and errors
> - Send notification when status changes detected
> - Send notification when check fails (site down, login fails, API errors)
```

### Notification Flow Decision
Based on D-03 "Notify for both changes and errors":
- Change notification: Aggregated, one message per account (all 5 cases in batch)
- Error notification: Per-case error (individual message for each failing case)
</context>

<interfaces>
ErrorNotifier contract (added to TelegramNotifier):
- `send_error_notification(self, account_id: str, case_id: str, error: Exception, error_type: str) -> None` - Send formatted error notification

Orchestrator integration:
- `orchestrator.notifier` - TelegramNotifier instance (injected via __init__)
- Exception handlers call orchestrator.notifier.send_error_notification()
</interfaces>

<tasks>
<task type="auto" files="src/notifier.py, src/orchestrator.py" action="
- Add send_error_notification() method to TelegramNotifier (src/notifier.py):
  ```python
  def send_error_notification(self, account_id: str, case_id: str, error: Exception, error_type: str) -> None:
      \"\"\"Send error notification to Telegram per CONTEXT.md format.\"\"\"
      # Build error message using MarkdownV2
      message = f\"\"\"
      # [Case ID] Check Failed
      
      ## Error Details
      - {error_type}: {str(error)}
      - {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}: Check execution failed
      
      **Case ID:** {case_id}
      \"\"\"
      await self.bot.send_message(chat_id=account_id, text=message, parse_mode='MarkdownV2')
      log.error(f'Error notification sent for case {case_id}: {error}')
  
  - Update TelegramNotifier.__init__ to store account_id (for per-account error notifications):
    ```python
    def __init__(self, token: str, account_id: str = None):
        self.bot = Bot(token=token)
        self.account_id = account_id
        self.on_change = None  # Callback hook
    ```

- Update Orchestrator to inject TelegramNotifier and handle errors:
  ```python
  class Orchestrator:
      notifier: TelegramNotifier  # Type hint
      account_id: str = None  # Current account ID
      
      def __init__(self, config: Dict):
          self.notifier = TelegramNotifier(config.get('telegram_token'))
          self.account_id = config.get('account_id')
          self.storage = SnapshotRepository()
          self.detector = Detector(self.storage, self.notifier)
      
      async def run_check(self) -> None:
          try:
              # ... fetch data ...
              # ... detect changes ...
          except Exception as e:
              error_type = 'check_failed'
              await self.notifier.send_error_notification(
                  account_id=self.account_id,
                  case_id=self.current_case_id,  # Need to track case ID
                  error=e,
                  error_type=error_type
              )
              raise  # Don't swallow, propagate to error handler
  ```

- Verify ERROR-01 requirement is met:
  ```python
  from src.notifier import TelegramNotifier
  from src.orchestrator import Orchestrator
  
  notifier = TelegramNotifier('test:token')
  notifier.send_error_notification('acc_1', 'case_123', Exception('test'), 'check_failed')
  # Verify Bot.send_message was called with formatted message
  ```

- Run end-to-end error test:
  1. Mock scraper to raise exception
  2. Run orchestrator
  3. Verify error notification sent to Telegram
", verify="Verify error notification sent", done="ERROR-01 requirement satisfied">
  <name>Task 3: Integrate error notification with Orchestrator</name>
  <files>src/notifier.py, src/orchestrator.py</files>
  <action>
    Update src/notifier.py::TelegramNotifier:
    - Add send_error_notification(account_id, case_id, error, error_type) method
    - Format error message per CONTEXT.md specification (bold case ID, error details, timestamp)
    - Use MarkdownV2 parse mode in Bot.send_message()
    - Store account_id in __init__ for per-account error notifications
    
    Update src/orchestrator.py:
    - Add notifier: TelegramNotifier and account_id: str type hints
    - Initialize notifier with token from config
    - Initialize current_case_id tracking
    - Wrap run_check() in try/except:
      * Catch Exception
      * Build error_type based on exception class:
        - TypeError -> 'login_failed'
        - ConnectionError -> 'site_unavailable'
        - HTTPError -> 'api_error'
        - Exception -> 'check_failed'
      * Call notifier.send_error_notification()
      * Re-raise exception after sending notification (don't swallow)
      * Log error message to file (logs/check.log)
    
    Verify ERROR-01 requirement:
    - Error notification format matches CONTEXT.md
    - Notification sent before re-raising exception
    - Orchestrator.error_handler method updated if exists
  </action>
  <verify>
    <automated>
      1. Verify TelegramNotifier.send_error_notification exists:
         ```bash
         python -c "from src.notifier import TelegramNotifier; t = TelegramNotifier(''); print(hasattr(t, 'send_error_notification'))"
         ```
      2. Verify Orchestrator has notifier instance:
         ```python
         from src.orchestrator import Orchestrator
         from src.notifier import TelegramNotifier
         orchestrator = Orchestrator({'telegram_token': 'test'})
         assert isinstance(orchestrator.notifier, TelegramNotifier)
         ```
      3. Verify exception handling wiring:
         ```python
         # Simulate error
         orchestrator.run_check()  # Should raise
         # Verify send_error_notification was called (check internal state)
         ```
    </automated>
  </verify>
  <done>
    TelegramNotifier.send_error_notification() implemented with CONTEXT.md format
    Orchestrator injects TelegramNotifier instance
    Exception handler calls send_error_notification before re-raising
    ERROR-01 requirement: Error notification sent when check fails
  </done>
</task>

</tasks>

<verification>
### Verify Error Notification Format
1. Check send_error_notification message format:
   ```python
   from src.notifier import TelegramNotifier
   from unittest.mock import patch, MagicMock
   
   notifier = TelegramNotifier('test:token')
   with patch.object(notifier.bot, 'send_message') as mock_send:
       notifier.send_error_notification('acc_1', 'case_123', Exception('test'), 'check_failed')
       # Verify message content
       call_args = mock_send.call_args
       message = call_args[0]['text']
       # Expected format (per CONTEXT.md):
       assert '# [Case ID] Check Failed' in message
       assert 'Error Details' in message
       assert 'Case ID: case_123' in message
   ```

### Verify Orchestrator Error Handling
1. Verify exception handler wiring:
   ```python
   from src.orchestrator import Orchestrator
   
   orchestrator = Orchestrator({'telegram_token': 'test'})
   
   # Simulate error in run_check
   try:
       orchestrator.run_check()
   except Exception as e:
       # Verify send_error_notification was called
       assert orchestrator.notifier.last_notification['type'] == 'error'
   ```

### End-to-End Error Test
1. Create test that triggers error:
   ```python
   # tests/test_orchestrator.py::test_error_notification
   async def test_error_notification(self, mocker):
       mocker.patch('src.orchestrator.Scraper.run', side_effect=Exception('test error'))
       
       orchestrator = Orchestrator({
           'telegram_token': 'test:token',
           'account_id': 'acc_1'
       })
       
       await orchestrator.run_check()
       
       # Verify error notification sent
       assert orchestrator.notifier.last_notification['type'] == 'error'
       assert orchestrator.notifier.last_notification['account_id'] == 'acc_1'
   ```

2. Run test:
   ```bash
   pytest tests/test_orchestrator.py::test_error_notification -v
   ```
</verification>

<success_criteria>
- TelegramNotifier.send_error_notification() method implemented
- Error message format matches CONTEXT.md specification
- Orchestrator injects TelegramNotifier and handles exceptions
- ERROR-01 requirement satisfied: notification sent when check fails
- Notification sent before exception is re-raised
- Error notification format verified in unit test
</success_criteria>

<output>
After completion, create `.planning/phases/05-telegram-notifications/03-SUMMARY.md`
</output>

<tool_call>
<function=Grep>
<parameter=pattern>
class Orchestrator
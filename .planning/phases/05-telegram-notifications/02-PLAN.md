---
phase: 05-telegram-notifications
plan: 02
type: auto
wave: 1
depends_on:
  - 04-PLAN.md (Detector layer provides detect_all_changes() callback)
files_modified:
  - src/notifier.py
  - src/detector.py (add notification callback)
user_setup: []

must_haves:
  truths:
    - "Detector callback triggers notification on change detection"
    - "No notification sent when no changes detected (silent cycle)"
  artifacts:
    - path: "src/notifier.py::TelegramNotifier.on_change"
      provides: "Callback hook for detector integration"
  key_links:
    - from: "src/detector.py::Detector"
      to: "src/notifier.py::TelegramNotifier"
      via: "on_change callback on change detection"
      pattern: "detector.on_change()"
---

<objective>
Integrate TelegramNotifier into Detector layer to trigger notifications when changes are detected, implementing the "Batch-Then-Notify" pattern from ARCHITECTURE.md.

Purpose: Complete the integration chain so detectors trigger notifications after detecting changes.

Output:
- `src/notifier.py` - TelegramNotifier.on_change callback method
- `src/detector.py` - Detector.on_change hook wired to notifier
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
From src/detector.py::Change:
```python
class Change(BaseModel):
    type: ChangeType
    old_value: Any
    new_value: Any
    description: str
```

From src/detector.py::Detector (expected interface):
- `detector.detect_all_changes()` - Returns list of Change objects per account
- `detector.on_change()` - Callback hook to be implemented by notifier

From .planning/research/ARCHITECTURE.md - Batch-Then-Notify pattern:
> "Complete all 5 case checks before sending notification"
> - Single notification vs 5 separate messages
> - User sees full picture at once
> - Reduces Telegram API calls

From CONTEXT.md:
> Batch-Then-Notify: Complete all 5 cases before sending one consolidated notification
```
7. Build notification message:
   ┌──────────────────────────────────────┐
   │ "[Case ID] Status changed: X → Y"   │
   │ "[Case ID] New document: ..."       │
   └──────────────────────────────────────┘
   │
8. Send to Telegram → User receives alert
```
</context>

<tasks>
<task type="auto" files="src/notifier.py, src/detector.py" action="
- Add TelegramNotifier.on_change() method to src/notifier.py:
  ```python
  def on_change(self, account_id: str, case_id: str, changes: List[Change]) -> None:
      \"\"\"Callback invoked when changes detected.\"\"\"
      send_change_notification(account_id, case_id, changes, len(changes))
  ```

- Update src/detector.py::Detector to inject TelegramNotifier:
  ```python
  class Detector:
      notifier: TelegramNotifier  # Type hint, actual instance from Orchestrator
      on_change: Callable = None  # Callback hook
      
      def __init__(self, storage: SnapshotRepository, notifier: TelegramNotifier):
          self.storage = storage
          self.notifier = notifier
          self.on_change = notifier.on_change
      
      def detect_all_changes(self, account_id: str, current_data: Dict) -> List[Change]:
          changes = []
          # ... detection logic ...
          
          if changes:
              self.on_change(account_id, case_id, changes)  # Trigger notification
          return changes
  ```

- Verify orchestrator wires Detector with TelegramNotifier instance
- Run end-to-end test:
  1. Run orchestrator with mock data that triggers changes
  2. Verify notification sent to Telegram
  3. Verify message format matches CONTEXT.md specification
", verify="Run orchestrator and verify notification received", done="Notification callback wired and functional">
  <name>Task 2: Wire Detector with TelegramNotifier for change notification callback</name>
  <files>src/notifier.py, src/detector.py</files>
  <action>
    Update src/notifier.py::TelegramNotifier with on_change() callback method:
    - Method signature: on_change(self, account_id: str, case_id: str, changes: List[Change]) -> None
    - Implementation: delegate to send_change_notification() with proper formatting
    
    Update src/detector.py::Detector:
    - Add notifer: TelegramNotifier type hint to __init__ signature
    - Add on_change: Callable = None instance variable
    - Inject notifier instance in __init__
    - Call self.on_change(account_id, case_id, changes) after detecting changes
    - Handle case where on_change is None (no notifier configured)
    
    Verify integration:
    - Orchestrator passes TelegramNotifier to Detector during initialization
    - Detector.on_change triggers notifier.send_change_notification() on change detection
  </action>
  <verify>
    <automated>
      1. Verify TelegramNotifier.on_change method exists:
         ```bash
         python -c "from src.notifier import TelegramNotifier; t = TelegramNotifier(''); print(hasattr(t, 'on_change'))"
         ```
      2. Verify Detector has on_change hook:
         ```bash
         python -c "from src.detector import Detector; print(hasattr(Detector, 'on_change'))"
         ```
      3. Verify callback invokes send_change_notification:
         ```python
         # Integration test
         notifier = TelegramNotifier('test:token')
         detector = Detector(storage, notifier)
         # Simulate change detection
         notifier.on_change('acc_1', 'case_123', [Change(...)])
         # Verify send_change_notification was called with correct args
         ```
    </automated>
  </verify>
  <done>
    TelegramNotifier.on_change callback implemented
    Detector injects notifier instance and calls on_change on change detection
    Batch-Then-Notify pattern enforced (all changes aggregated before notification)
    Orchestrator wires Detector with TelegramNotifier
  </done>
</task>

</tasks>

<verification>
### Verify Integration Chain
1. Check Detector has notifier instance and on_change hook:
   ```python
   from src.detector import Detector
   from src.notifier import TelegramNotifier
   
   notifier = TelegramNotifier('test:token')
   detector = Detector(storage, notifier)
   
   assert isinstance(detector.notifier, TelegramNotifier)
   assert callable(detector.on_change)
   ```

2. Verify on_change invokes send_change_notification:
   ```python
   notifier = TelegramNotifier('test:token')
   notifier.on_change('acc_1', 'case_123', [Change(...)])
   
   # Verify send_change_notification was called (check internal state)
   assert notifier.last_notification['type'] == 'change'
   ```

3. Verify orchestrator wires the notifier:
   ```python
   from src.orchestrator import Orchestrator
   orchestrator = Orchestrator()
   # Verify Detector uses orchestrator's notifier instance
   ```

### End-to-End Test
1. Run orchestrator:
   ```bash
   python src/orchestrator.py
   ```
2. Monitor Telegram for notifications
3. Verify message format matches CONTEXT.md:
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
</verification>

<success_criteria>
- TelegramNotifier.on_change callback method implemented
- Detector injects TelegramNotifier instance in __init__
- on_change hook called after detecting changes
- No notification sent when no changes (silent cycle)
- Integration test verifies orchestrator wires Detector with notifier
</success_criteria>

<output>
After completion, create `.planning/phases/05-telegram-notifications/02-SUMMARY.md`
</output>

<tool_call>
<function=Write>
<parameter=file_path>
C:\Prjs\Claude\InpolPub\.planning\phases\05-telegram-notifications\03-PLAN.md
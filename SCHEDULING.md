# Inpol Monitor - Scheduling Guide

Configure automated execution at 8:00, 12:30, 18:00 Poland time using Windows Task Scheduler.

---

## Quick Setup

### Prerequisites

1. Ensure your Python environment is on the system `PATH` (or your venv is activated when running interactively)
2. Verify the orchestrator works manually first:
   ```cmd
   cd C:\Prjs\Claude\InpolPub
   python -m src.orchestrator
   ```

### One-Command Setup

Open PowerShell **as Administrator** and run:

```powershell
$PROJECT_DIR = "C:\Prjs\Claude\InpolPub"
$SCRIPT = Join-Path $PROJECT_DIR "run_check.cmd"
$TASK_NAME = "Inpol Monitor"

schtasks /Create /TN $TASK_NAME /TR $SCRIPT `
  /SC DAILY /ST 08:00 /F `
  /RL HIGHEST

schtasks /Create /TN "$TASK_NAME\Noon Check" /TR $SCRIPT `
  /SC DAILY /ST 12:30 /F `
  /RL HIGHEST

schtasks /Create /TN "$TASK_NAME\Evening Check" /TR $SCRIPT `
  /SC DAILY /ST 18:00 /F `
  /RL HIGHEST
```

This creates three subtasks under `Inpol Monitor`:
- `Inpol Monitor` — 8:00 AM
- `Inpol Monitor\Noon Check` — 12:30 PM
- `Inpol Monitor\Evening Check` — 6:00 PM

### Verify

```cmd
schtasks /Query /TN "Inpol Monitor" /FO LIST
schtasks /Query /TN "Inpol Monitor\Noon Check" /FO LIST
schtasks /Query /TN "Inpol Monitor\Evening Check" /FO LIST
```

---

## Manual Setup (Task Scheduler GUI)

1. Press `Win + R`, type `taskschd.msc`, press Enter
2. Right-click **Task Scheduler Library** → **Create Task**
3. **General** tab:
   - Name: `Inpol Monitor`
   - ☑ Run with highest privileges
   - Configure for: Windows 10/11
4. **Triggers** tab:
   - New → Daily → 8:00 AM
   - New → Daily → 12:30 PM
   - New → Daily → 6:00 PM
5. **Actions** tab:
   - New → Start a program
   - Program: `C:\Prjs\Claude\InpolPub\run_check.cmd`
6. **Conditions** tab:
   - ☐ Uncheck "Start the task only if the computer is on AC power"
7. **Settings** tab:
   - ☑ Allow task to be run on demand
   - ☑ If the task fails, restart every (optional): 1 minute, up to 3 attempts
8. Click **OK**

---

## Logs

All output is appended to `logs/scheduler.log`:

```cmd
type logs\scheduler.log
```

Or in real-time:
```cmd
powershell -Command "Get-Content logs\scheduler.log -Wait"
```

---

## Timezone Note

Task Scheduler uses the system clock. Ensure your Windows timezone is set to:

> `(UTC+01:00) Amsterdam, Berlin, Bern, Rome, Stockholm, Vienna`

This handles CET/CEST (daylight saving) automatically.

---

## Management Commands

### Run on demand

```cmd
schtasks /Run /TN "Inpol Monitor"
```

### Stop

```cmd
schtasks /Stop /TN "Inpol Monitor"
```

### Disable (without deleting)

```cmd
schtasks /Change /TN "Inpol Monitor" /DISABLE
```

### Re-enable

```cmd
schtasks /Change /TN "Inpol Monitor" /ENABLE
```

### Delete all tasks

```cmd
schtasks /Delete /TN "Inpol Monitor" /F
schtasks /Delete /TN "Inpol Monitor\Noon Check" /F
schtasks /Delete /TN "Inpol Monitor\Evening Check" /F
```

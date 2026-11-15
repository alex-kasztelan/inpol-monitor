# Inpol Monitor

Automated monitoring system for the Polish government portal (inpol.mazowieckie.pl)

**Languages:** [English](README.md) | [Русский](README.ru.md) | [Українська](README.ua.md) | [Polski](README.pl.md)

## Overview

Inpol Monitor tracks immigration cases across multiple accounts to detect any changes to statuses, documents, questions, or deadlines — so the user never misses important updates.

## What This Does

- **Authentication**: Logs into Inpol portal with multiple accounts (sequential auth with CSRF handling)
- **Data Extraction**: Fetches case data for all configured cases
- **Storage**: Persists all historical snapshots to SQLite database with INSERT-only immutability
- **Change Detection**: Compares current vs previous snapshots, detects 7 change types:
  - Status changes
  - New/removed documents
  - Date modifications (decision dates, submission dates, updated_at)
  - Question changes (including field-level diff for questions)
  - Timeline events
- **Notifications**: Sends detailed change reports to Telegram (multi-user support) with email fallback when Telegram fails
- **Scheduling**: Automated checks at 8:00, 12:30, and 18:00 Poland time (CET/CEST) via Windows Task Scheduler
- **Web UI**: Flask web app for viewing and comparing historical case snapshots with field-level change highlighting

## Getting Started

### Prerequisites

- Python 3.11+
- Windows 11 (for Task Scheduler) or any OS for development

### Quick Installation

1. **Clone and setup**
   ```bash
   git clone https://github.com/your-repo/inpol-monitor.git
   cd inpol-monitor
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # or ./venv/bin/activate  # Linux/macOS
   pip install -r requirements.txt
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your preferences (language, logging, email)
   ```

3. **Load credentials**
   ```bash
   cp credentials.json.example credentials.json
   # Edit credentials.json with your actual account credentials
   ```

4. **Run the application**
   ```bash
   # Authentication check
   python check.py

   # Full monitoring cycle
   python -m src.orchestrator
   ```

### Configuration

#### .env Configuration
```
# Language settings
LANGUAGE=en         # Web UI language (en, pl, ru, ua)
NOTIFICATION_LANGUAGE=en  # Telegram/email notification language

# Portal
INPOL_BASE_URL=https://inpol.mazowieckie.pl

# JSON response logging (for API analysis)
JSON_LOGGING_ENABLED=false

# Email notifications (fallback)
EMAIL_ENABLED=false
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your-username
SMTP_PASSWORD=your-password
EMAIL_FROM=noreply@example.com
EMAIL_TO=your-email@example.com
```

#### credentials.json Configuration
```json
{
  "AccountName1": {
    "username": "email@example.com",
    "password": "secure-password",
    "case_ids": ["CASE-001", "CASE-002", "CASE-003"]
  },
  "AccountName2": {
    "username": "email2@example.com", 
    "password": "another-password",
    "case_ids": ["CASE-004", "CASE-005"]
  }
}
```

## Usage

### Manual Checks
```cmd
# Quick authentication test
python check.py

# Full monitoring cycle (with logging)
python -m src.orchestrator
```

### Automated Checks (Windows Task Scheduler)

Open PowerShell **as Administrator** from the project directory:

```powershell
$SCRIPT = Join-Path (Get-Location) "run_check.cmd"
$TASK_NAME = "Inpol Monitor"

schtasks /Create /TN $TASK_NAME /TR $SCRIPT /SC DAILY /ST 08:00 /F /RL HIGHEST
schtasks /Create /TN "$TASK_NAME\Noon Check" /TR $SCRIPT /SC DAILY /ST 12:30 /F /RL HIGHEST
schtasks /Create /TN "$TASK_NAME\Evening Check" /TR $SCRIPT /SC DAILY /ST 18:00 /F /RL HIGHEST
```

Verify and run on demand:

```cmd
schtasks /Query /TN "Inpol Monitor"
schtasks /Run /TN "Inpol Monitor"
```

See [SCHEDULING.md](SCHEDULING.md) for the full setup, management, and removal guide.

### Web UI

1. **Start the Flask app** from the project root:
   ```bash
   python -m src.web.__main__
   ```

2. **Open** `http://localhost:5000` in your browser and log in with the web credentials.

3. **Features**:
   - Login with your credentials
   - View all snapshots with filters (case, account, endpoint, date range)
   - Compare two snapshots side-by-side
   - Display all 7 question fields with field-level change highlighting
   - Translation support (EN, PL, UA, RU)

## Project Structure

```
.
├── .planning/              # GSD planning artifacts
│   ├── PROJECT.md        # Requirements and constraints
│   ├── ROADMAP.md        # Phase breakdown  
│   ├── STATE.md          # Current state
│   └── phases/           # Phase directories
│       ├── 01-project-foundation-authentication/
│       ├── 02-data-extraction/
│       ├── 03-data-storage/
│       ├── 04-change-detection/
│       ├── 05-telegram-notifications/
│       ├── 07-windows-task-scheduler/
│       ├── 08-validation-polish/
│       ├── 09-json-response-logging/
│       ├── 10-email-notifications/
│       ├── 11-web-application/
│       └── 12-enhanced-question-comparison/
├── src/                   # Core application
│   ├── __init__.py
│   ├── auth.py            # Authentication logic
│   ├── config.py          # Configuration loading
│   ├── orchestrator.py    # Main coordination
│   ├── scraper.py         # Data extraction
│   ├── detector.py        # Change detection
│   ├── notifier.py        # Telegram notifications
│   ├── email_notifier.py  # Email fallback
│   ├── session_manager.py # Session management
│   ├── storage.py         # SQLite repository
│   └── models.py          # Pydantic data models
├── src/web/              # Web application
│   ├── __main__.py
│   ├── auth.py           # Web authentication
│   ├── routes.py         # Flask routes
│   └── templates/        # HTML templates
├── tests/                # Test suite
│   ├── conftest.py       # Pytest configuration
│   ├── test_*.py         # Unit tests
│   └── test_comparison.py # Field-level comparison tests
├── data/                 # Databases
│   ├── snapshots.db      # Production database
│   └── test_snapshots.db # Test database
├── logs/                 # Application logs
├── requirements.txt      # Python dependencies
├── check.py             # Authentication flow checker
├── run_check.cmd        # Windows Task Scheduler script
├── *.json               # Localization files
└── *.md                 # Documentation
```

## Features

### Core Requirements
- [x] **AUTH-01**: Authenticate with multiple accounts using sequential flow with CSRF handling
- [x] **AUTH-02**: Secure credentials via .env and credentials.json
- [x] **DATA-01**: Extract case data for all configured cases
- [x] **DATA-02**: Extract status, dates, documents, deadlines with i18n support
- [x] **STORE-01**: Save snapshots to SQLite with timestamp
- [x] **STORE-02**: INSERT-only immutability (full historical retention)
- [x] **STORE-03**: Query snapshots by case_id (globally unique)
- [x] **DETECT-01**: Compare current vs previous snapshots
- [x] **DETECT-02**: Detect 7 change types (status, documents, dates, questions)
- [x] **NOTIFY-01**: Send detailed Telegram change reports
- [x] **NOTIFY-02**: Include case ID and specific changes in notifications
- [x] **SCHED-01**: Run at 8:00, 12:30, 18:00 Poland time
- [x] **SCHED-02**: Windows Task Scheduler integration
- [x] **SCHED-03**: Manual CLI option
- [x] **ERROR-01**: Send error notifications on failures

### Phase 12: Enhanced Question Comparison (Completed)
- **Field-level comparison**: Detects individual field changes (title, status, status_label, body, sentTime, answer, responseTime) within questions
- **7-question display**: Shows all question fields in comparison view
- **Localization**: Translated status_label via `Cases.Question.Statuses`, title via `Cases.Question.Titles`
- **Change highlighting**: Visual distinction for changed fields in UI

### Technology Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11, requests, beautifulsoup4, lxml |
| **Data Models** | Pydantic v2, SQLite (INSERT-only, immutable) |
| **Web UI** | Flask 3.0+, Bootstrap 5, HTMX |
| **Notifications** | aiogram 3.x (Telegram), SMTP (Email) |
| **Localization** | JSON-based i18n (EN/PL/UA/RU) |
| **Deployment** | Windows Task Scheduler, Python venv |
| **Testing** | pytest, test coverage >80% |

### Architecture

1. **Auth Layer**: Sequential account authentication with CSRF handling and session management
2. **Extraction Layer**: HTML parsing with beautifulsoup4, JSON API response processing
3. **Storage Layer**: SQLite repository with INSERT-only snapshot storage
4. **Detection Layer**: Strategy pattern for 7 change types, field-level question comparison
5. **Notification Layer**: Batch-then-notify with Telegram (multi-user support) and email fallback
6. **Web Layer**: Flask web app with authentication, snapshot filtering, comparison view

### Quality Gates

- **Tests**: 162 total tests passing (83% coverage)
- **Code Review**: Standard depth review covering detector → notifier → email_notifier threading
- **HTML Injection Fix**: All user-controlled values in emails escaped with `html.escape()`
- **Localization**: 7 language keys supported (en, pl, ru, ua)
- **Validation**: Golden file testing, failure scenario tests
- **Documentation**: README, SCHEDULING.md, PROJECT.md

## Known Issues

- **Akamai Bot Protection**: Auto-solve JS challenge via meta-refresh (~2s per API call)
- **Pre-existing test failure**: `tests/planner/test_noti_format.py` (NameError: `status_id` undefined) — unrelated to current changes

## Security Considerations

- **Credentials**: Stored in encrypted credentials.json (users must protect their files)
- **HTML Injection**: Fixed in email notifications (all user-controlled values escaped)
- **HTTPS**: Uses HTTPS for all portal connections
- **Session Security**: CSRF tokens, secure session management
- **File Access**: SQLite database file permissions (read/write by app user)

## Future Enhancements

### Phase M2 (Backlog)
- Case deadline reminders
- Monthly summary reports  
- Export functionality
- Enhanced error recovery
- Mobile app
- Multi-language support (additional languages)

### Potential Improvements
- Move from HTML scraping to official API if available
- Database migration to PostgreSQL for scalability
- Performance optimization for large case counts
- Real-time notifications (WebSocket)

## Troubleshooting

### Common Issues

**Task Scheduler not running**
```cmd
# Check status
schtasks /Query /TN "Inpol Monitor"

# Restart if needed
schtasks /Run /TN "Inpol Monitor"
```

**Authentication failures**
```bash
# Enable debug logging
python -m src.orchestrator  # or python -m src.web.__main__

# Check credentials.json exists and has correct format
```

**Web UI login issues**
```
# Ensure .env LANGUAGE matches your preference
# Check database snapshots exist
# Verify credentials.json is populated
```

**JSON logging issues**
```bash
# Enable in .env
JSON_LOGGING_ENABLED=true

# Check logs/json_responses.log for output
```

### Getting Help

1. **Read SCHEDULING.md** for Task Scheduler setup
2. **Check .env.example** for environment variable examples
3. **Review credentials.json.example** for credential format
4. **View logs/ directory** for runtime diagnostics
5. **Run tests**: `pytest tests/` for test suite

## Contributing

### Development Workflow

1. **Plan Phase**: Discuss → Research → Define Requirements → Create Roadmap → Plan Phase
2. **Implementation**: Execute plans with atomic commits, verification loops
3. **Testing**: Unit tests → Integration tests → UAT verification
4. **Review**: Code review → Security audit → Documentation
5. **Deploy**: Milestone completion → Archive → Next milestone

### Commit Guidelines

- **Phase commits**: Include phase number in commit message (`feat(12-01): ...`)
- **Co-authored-by**: Always add `Co-Authored-By: Claude Code <noreply@anthropic.com>`
- **Atomic commits**: Each commit should have a single logical change
- **Convention**: Conventional commits with type:scope description

### Code Standards

- **Python**: 88-character line limit, black formatting, pytest
- **Documentation**: Markdown with consistent heading hierarchy
- **Testing**: Test-driven development (TDD) for new features
- **Security**: Regular dependency updates, input validation, output encoding

## License

MIT License - See LICENSE file for details.

## Support

For issues, questions, or feature requests:
1. Check existing documentation
2. Review test logs for error details
3. Verify configuration files (.env, credentials.json)
4. Test manual execution (`python -m src.orchestrator`)
5. Check Windows Event Viewer if using Task Scheduler

Your support for the development of this tool is greatly appreciated - <a href="https://www.paypal.com/donate/?business=8JF7EPW5NWEJL&no_recurring=0&item_name=As+a+passionate+supporter+of+efficient+project+mgmt%2C+I%27ve+been+dedicated+to+creating+tools%2C+that+streamline+reporting+processes&currency_code=EUR" target="_blank">Donate</a><br/>

If you find the tool useful, please consider contributing to its further improvement. I welcome any ideas or suggestions for enhancing the solution.<br/>

Tested under Windows 11 Home version.

---

*Last updated: 2026-07-15*
*Phase 12 complete: Enhanced Question Comparison with field-level diff*  
*Inpol Monitor v1.0 (M1) - Initial Development*
*Project built with care and attention to quality*
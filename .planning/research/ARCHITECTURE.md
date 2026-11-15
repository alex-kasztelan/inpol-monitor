# Architecture Patterns

**Domain:** Web Monitoring / Change Detection System
**Researched:** 2026-03-26

## Recommended Architecture

For a single-user, CLI-based monitoring system running on Windows with scheduled checks, a **layered batch architecture** is recommended over event-driven or microservice patterns.

```
┌─────────────────────────────────────────────────────────────────┐
│                      SCHEDULER LAYER                            │
│              (Windows Task Scheduler + CLI entry point)         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATION LAYER                        │
│              (Main script: coordinate check cycle)              │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   AUTH LAYER     │ │  SCRAPER LAYER   │ │  DETECTOR LAYER  │
│  (Login, sess.)  │ │ (Parse, extract) │ │  (Diff, compare) │
└──────────────────┘ └──────────────────┘ └──────────────────┘
              │               │               │
              └───────────────┼───────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       STORAGE LAYER                             │
│                  (SQLite: snapshots, history)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     NOTIFICATION LAYER                          │
│                  (Telegram: send change report)                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|----------------|-------------------|
| **Scheduler** | Trigger check execution at 8:00, 12:30, 18:00 CET/CEST | Windows Task Scheduler → CLI entry point |
| **Orchestrator** | Coordinate one complete check cycle for all 5 cases | Auth, Scraper, Detector, Storage, Notifier |
| **Auth Manager** | Handle login, session cookies, CSRF tokens | Inpol portal (HTTPS), `.env` credentials |
| **Scraper** | Navigate portal, extract case data (status, documents, dates) | Inpol portal (authenticated), returns structured data |
| **Detector** | Compare current snapshot vs previous, identify changes | Storage (previous snapshot), outputs change list |
| **Storage** | Persist snapshots with timestamps, query history | SQLite database file |
| **Notifier** | Format and send Telegram message with change details | Telegram Bot API |
| **Error Handler** | Catch failures, send error notification | Notifier, logging |

---

## Data Flow

### Normal Check Cycle (No Changes)

```
1. Scheduler triggers CLI
         │
2. Load credentials from .env
         │
3. For each account (2):
   ┌─────────────────────────────────────┐
   │ Authenticate → Get session cookies  │
   └─────────────────────────────────────┘
         │
4. For each case (5 total):
   ┌─────────────────────────────────────┐
   │ Fetch case page → Extract data      │
   │ → Structure: {status, date, docs}   │
   └─────────────────────────────────────┘
         │
5. For each case:
   ┌─────────────────────────────────────┐
   │ Load previous snapshot from SQLite  │
   │ Compare: current vs previous        │
   │ → Changes: [] (empty)               │
   └─────────────────────────────────────┘
         │
6. Save current snapshot to SQLite
         │
7. No notification (no changes)
```

### Check Cycle With Changes Detected

```
Steps 1-5: Same as above
         │
5b. Detector finds changes:
   ┌─────────────────────────────────────┐
   │ Changes: [                          │
   │   {type: "status", old: "X", new: "Y"}, │
   │   {type: "new_document", name: "..."}   │
   │ ]                                   │
   └─────────────────────────────────────┘
         │
6. Save current snapshot to SQLite
         │
7. Build notification message:
   ┌─────────────────────────────────────┐
   │ "[Case ID] Status changed: X → Y"   │
   │ "[Case ID] New document: ..."       │
   └─────────────────────────────────────┘
         │
8. Send to Telegram → User receives alert
```

### Error Flow

```
At any step:
         │
   Exception caught
         │
   ┌─────────────────────────────────────┐
   │ Build error message:                │
   │ "Check failed at [step]: [error]"   │
   └─────────────────────────────────────┘
         │
   Send error notification to Telegram
```

---

## Patterns to Follow

### Pattern 1: Repository Pattern for Storage

**What:** Abstract database operations behind a simple interface.

**When:** Any component needs to read/write snapshots.

**Example:**
```python
class SnapshotRepository:
    def get_latest(self, case_id: str) -> Optional[Snapshot]:
        ...
    def save(self, snapshot: Snapshot) -> None:
        ...
    def get_history(self, case_id: str) -> List[Snapshot]:
        ...
```

**Why:** Makes storage swapable (SQLite → PostgreSQL later), keeps SQL out of business logic.

---

### Pattern 2: Strategy Pattern for Change Detection

**What:** Separate comparison logic per data type (status, dates, documents).

**When:** Different fields need different comparison strategies.

**Example:**
```python
class StatusDetector:
    def detect(self, old: str, new: str) -> Optional[Change]:
        return Change("status", old, new) if old != new else None

class DocumentDetector:
    def detect(self, old: List[str], new: List[str]) -> List[Change]:
        added = set(new) - set(old)
        return [Change("new_doc", doc) for doc in added]
```

**Why:** Easy to add new detectors (deadline changes, fee updates) without modifying core logic.

---

### Pattern 3: Batch-Then-Notify

**What:** Complete all 5 case checks before sending one consolidated notification.

**When:** Multiple items checked in single cycle.

**Why:**
- Single notification vs 5 separate messages
- User sees full picture at once
- Reduces Telegram API calls

---

### Pattern 4: Snapshot Immutability

**What:** Never update historical snapshots; always insert new rows.

**When:** Saving check results.

**Why:**
- Full audit trail (requirement STORE-02)
- Enables retroactive analysis
- Simplifies diff logic (always compare latest vs previous)

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Tight Coupling Between Scraper and Site Structure

**What:** HTML parsing logic mixed with business logic.

**Why bad:** Site changes break entire system, hard to test.

**Instead:** Separate extraction layer:
```python
# Bad
status = html.find("div.status").text  # Mixed with business logic

# Good
class InpolExtractor:
    def extract_status(self, html: str) -> str:
        # All HTML knowledge here
        ...
```

---

### Anti-Pattern 2: Storing Credentials in Code

**What:** Hardcoded username/password.

**Why bad:** Security risk, accidentally committed to git.

**Instead:** `.env` file with `python-dotenv`:
```python
from dotenv import load_dotenv
load_dotenv()
INPOL_USERNAME = os.getenv("INPOL_USERNAME")
```

---

### Anti-Pattern 3: Silent Failures

**What:** Exception caught but not reported.

**Why bad:** User doesn't know checks are failing.

**Instead:** Always notify on error (requirement ERROR-01):
```python
try:
    run_check()
except Exception as e:
    send_error_notification(e)
    raise  # Don't swallow
```

---

### Anti-Pattern 4: Polling in Application Code

**What:** Script runs continuously, checking every N minutes.

**Why bad:** Wastes resources, conflicts with Windows Task Scheduler.

**Instead:** Run once per invocation, exit cleanly. Let OS handle scheduling.

---

## Scalability Considerations

| Concern | Current (1 user, 5 cases) | At 100 cases | At 1000 cases |
|---------|---------------------------|--------------|---------------|
| **Check duration** | ~30-60 seconds | 5-10 minutes | Need parallel workers |
| **Storage** | ~1 MB/month | ~20 MB/month | Need partitioning |
| **Telegram limits** | 1-2 msgs/day | 10-20 msgs/day | 30 msg/sec limit applies |
| **Architecture** | Single script | Add concurrency | Message queue + workers |

---

## Suggested Build Order

Based on component dependencies:

| Order | Component | Rationale |
|-------|-----------|-----------|
| 1 | **Storage Layer** | Foundation: need to persist before comparing |
| 2 | **Scraper Layer** | Core: extract data from portal |
| 3 | **Auth Manager** | Prerequisite for scraper to work |
| 4 | **Detector Layer** | Needs storage (previous) + scraper (current) |
| 5 | **Notifier Layer** | Needs detector output (changes) |
| 6 | **Orchestrator** | Wires all components together |
| 7 | **Error Handler** | Wraps orchestrator |
| 8 | **Scheduler Integration** | Final: automate existing working script |

**Build implication:** Start with manual CLI (`python check.py`), add Windows Task Scheduler only after end-to-end works.

---

## Directory Structure Recommendation

```
inpol-monitor/
├── .env                    # Credentials (gitignored)
├── .env.example            # Template
├── requirements.txt
├── check.py                # CLI entry point
├── src/
│   ├── auth.py             # Auth Manager
│   ├── scraper.py          # Scraper + Extractor
│   ├── detector.py         # Change detectors
│   ├── storage.py          # Repository pattern
│   ├── notifier.py         # Telegram sender
│   └── orchestrator.py     # Coordination logic
├── data/
│   └── snapshots.db        # SQLite database
└── logs/
    └── check.log           # Execution logs
```

---

## Sources

- [Web Scraping Architecture Explained (2026) - BytesFlows](https://bytesflows.com/en/blog/web-scraping-architecture-explained)
- [Web Scraping Best Practices 2026 - Apify](https://use-apify.com/blog/web-scraping-best-practices-2026)
- [Firecrawl Observer Architecture](https://tools.firecrawl.dev/blog/introducing-firecrawl-observer)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/en/master/userguide.html)
- [aiogram 3.x Documentation](https://docs.aiogram.dev/en/v3.17.0)
- [python-telegram-bot Architecture](https://github.com/python-telegram-bot/python-telegram-bot/wiki/Architecture)
- [DataDios SmartDiff Architecture](https://arxiv.org/html/2509.00293v1)

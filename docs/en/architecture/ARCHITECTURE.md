# Inpol Monitor — Architecture Diagrams

This document provides architectural component diagrams and interaction diagrams for the Inpol Monitor project. Diagrams use Mermaid syntax and render in GitHub, GitLab, VS Code, and any Mermaid-compatible viewer.

Available translations: [English](ARCHITECTURE.md) | [Polski](../pl/architecture/ARCHITECTURE.md) | [Русский](../ru/architecture/ARCHITECTURE.md) | [Українська](../ua/architecture/ARCHITECTURE.md)

---

## 1. Component Diagram

High-level view of the system's layers and their relationships.

```mermaid
flowchart TB
    subgraph EXT[External Systems]
        INPOL[Inpol Portal\ninpol.mazowieckie.pl]
        TG[Telegram Bot API]
        SMTP[SMTP Email Server]
        SCH[Windows Task Scheduler]
        USER[User]
    end

    subgraph APP[Inpol Monitor Application]
        direction TB

        ORCH[orchestrator.py\nCheck Cycle Coordinator]

        subgraph AUTH_L[Authentication Layer]
            AUTH[auth.py\nSequential Auth + CSRF]
            SESS[session_manager.py\nHTTP Session + Akamai Solve]
        end

        subgraph EXTRACT_L[Extraction Layer]
            SCRAPER[scraper.py\nInpolScraper\nHTML/JSON Parsing]
            CONFIG[config.py\n.env + credentials.json]
        end

        subgraph STORAGE_L[Storage Layer]
            REPO[storage.py\nSnapshotRepository\nINSERT-only]
            DB[(SQLite\nsnapshots.db)]
        end

        subgraph DETECT_L[Detection Layer]
            DET[detector.py\n7 Detector Strategies]
            MODELS[models.py\nPydantic Models]
        end

        subgraph NOTIFY_L[Notification Layer]
            NOTIF[notifier.py\nTelegramNotifier\nBatch-then-Notify]
            EMAIL[email_notifier.py\nEmail Fallback]
            BOT[telegram_bot.py\nBot Commands]
        end

        subgraph WEB_L[Web Layer]
            WAUTH[web/auth.py\nWeb Auth]
            ROUTES[web/routes.py\nFlask Routes]
            TPL[web/templates\nHTML]
        end

        L10N[localization.py\ni18n Engine]
        LANGS[(en/pl/ru/ua.json\nTranslation Files)]
    end

    SCH -->|Triggers 08:00/12:30/18:00 CET| ORCH
    USER -->|Manual CLI| ORCH
    USER -->|Browser :5000| WAUTH

    ORCH --> CONFIG
    ORCH --> AUTH
    AUTH --> SESS
    SESS -->|HTTPS| INPOL
    ORCH --> SCRAPER
    SCRAPER -->|HTTP| INPOL
    ORCH --> DET
    DET --> MODELS
    MODELS --> L10N
    L10N --> LANGS
    ORCH --> REPO
    REPO --> DB
    ORCH --> NOTIF
    NOTIF -->|Primary| TG
    NOTIF -.->|On failure| EMAIL
    EMAIL -.->|Fallback| SMTP
    BOT --> NOTIF
    BOT --> REPO
    WAUTH --> CONFIG
    ROUTES --> REPO
    ROUTES --> DET
    ROUTES --> TPL
    ROUTES --> L10N
```

---

## 2. Sequence Diagram — Main Check Cycle

The full monitoring cycle triggered by Task Scheduler, manual CLI, or the web UI.

```mermaid
sequenceDiagram
    autonumber
    actor S as Task Scheduler / CLI
    participant O as Orchestrator
    participant C as Config
    participant A as Auth
    participant SM as SessionManager
    participant P as Inpol Portal
    participant SC as Scraper
    participant R as SnapshotRepository
    participant DB as SQLite
    participant D as Detector
    participant N as TelegramNotifier
    participant TG as Telegram API
    participant E as EmailNotifier

    S->>O: run_check()
    O->>C: load_credentials()
    C-->>O: credentials

    loop Each account (sequential)
        O->>A: authenticate_account(name, creds)
        A->>SM: login(email, password)
        SM->>P: GET /login (CSRF token)
        P-->>SM: HTML + CSRF
        SM->>P: POST credentials + CSRF
        P-->>SM: Session cookies
        SM-->>A: Authenticated session
        A-->>O: Session
    end

    loop Each case_id
        O->>SC: fetch_case_data(case_id)
        SC->>P: GET /api/case/{id}
        P-->>SC: JSON
        SC-->>O: CaseData

        O->>R: get_latest_snapshot(case_id)
        R->>DB: SELECT latest
        DB-->>R: Previous snapshot
        R-->>O: old_snapshot

        O->>D: detect_all_changes(old, new)
        D->>D: Run 7 strategies
        D-->>O: List[Change]

        O->>R: save_snapshot(new)
        R->>DB: INSERT (immutable)
        DB-->>R: OK

        O->>N: queue_notification(case_id, changes)
    end

    O->>N: send_all_notifications()
    N->>TG: Batch messages
    alt Telegram OK
        TG-->>N: 200 OK
    else Telegram fails
        N->>E: send email fallback
        E->>SMTP: Send
        SMTP-->>E: Result
    end

    O->>SM: close() all sessions
    O-->>S: exit code
```

---

## 3. Sequence Diagram — Change Detection Detail

Strategy-pattern detail for the 7 change types.

```mermaid
sequenceDiagram
    autonumber
    participant O as Orchestrator
    participant DA as detect_all_changes()
    participant R as SnapshotRepository
    participant SD as StatusDetector
    participant DD as DocumentDetector
    participant DT as DateDetector
    participant QD as QuestionDetector
    participant TD as TimelineDetector
    participant N as TelegramNotifier
    participant L as localization.py

    O->>DA: detect_all_changes(storage, sessions, creds, notifier)

    loop Each account, each case
        DA->>R: get_latest_snapshot(case_id)
        R-->>DA: old_snapshot or None
        DA->>DA: Build new_snapshot

        par Strategy Pattern
            DA->>SD: detect(old, new)
            SD-->>DA: status changes
            DA->>DD: detect(old, new)
            DD-->>DA: added/removed docs
            DA->>DT: detect(old, new)
            DT-->>DA: date changes
            DA->>QD: detect(old, new)
            QD->>L: get_question_title/status
            L-->>QD: localized labels
            QD-->>DA: question field diffs
            DA->>TD: detect(old, new)
            TD-->>DA: timeline events
        end

        DA->>N: queue_notification(case_id, changes)
        DA->>R: save_snapshot(new)
    end

    DA-->>O: Dict[account, List[Change]]
```

The 7 change types: `STATUS`, `NEW_DOCUMENT`, `REMOVED_DOCUMENT`, `DECISION_DATE_CHANGE`, `SUBMIT_DATE_CHANGE`, `UPDATED_AT_CHANGE`, `TIMELINE_EVENT_ADDED`, plus question-level types (`QUESTION_ASKED`, `QUESTION_ANSWERED`, `QUESTION_COUNT_CHANGE`, `NEW_QUESTION_DETAIL`).

---

## 4. Sequence Diagram — Web UI

Flask web app: login, snapshot list, side-by-side comparison.

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant B as Browser
    participant R as web/routes.py
    participant WA as web/auth.py
    participant REP as SnapshotRepository
    participant D as detector.py
    participant L as localization.py
    participant T as Jinja2 Templates

    U->>B: Open http://localhost:5000
    B->>R: GET /
    R->>WA: login_required check
    alt Not authenticated
        R-->>B: Redirect /login
        B->>R: GET /login
        R->>T: Render login.html
        T-->>B: Login form
        U->>B: Submit credentials
        B->>R: POST /login
        R->>WA: verify_credentials()
        WA-->>R: Valid / Invalid
        R-->>B: Set session cookie + redirect
    else Authenticated
        R->>REP: get_all_snapshots(filters)
        REP-->>R: Snapshots
        R->>L: UI translations
        L-->>R: Localized strings
        R->>T: Render index.html
        T-->>B: Snapshot list

        U->>B: Click "Compare" on 2 snapshots
        B->>R: GET /compare?snap1=X&snap2=Y
        R->>REP: get_snapshot(id1), get_snapshot(id2)
        R->>D: detect_all_changes(old, new)
        D-->>R: Field-level diff
        R->>L: Translate labels
        L-->>R: Localized labels
        R->>T: Render compare.html
        T-->>B: Side-by-side with highlighting
    end
```

Key routes (`src/web/routes.py`): `index`, `login`, `logout`, `compare`, `build_comparison`, `delete`, `set_language`.

---

## 5. Data Flow Summary

```mermaid
flowchart LR
    subgraph IN[Inputs]
        CRED[credentials.json]
        ENV[.env]
        WC[web credentials]
    end

    subgraph PIPE[Pipeline]
        AUTH[Authenticate]
        FETCH[Fetch Case Data]
        PARSE[Parse + Extract]
        CMP[Compare Snapshots]
        DET[Detect Changes]
        STORE[Store Immutable Snapshot]
    end

    subgraph OUT[Outputs]
        TG[TTelegram]
        EM[Email Fallback]
        WEB[Web UI]
        LOG[Logs]
        JLOG[JSON Response Log]
    end

    subgraph STORE[Storage]
        DB[(snapshots.db)]
        LF[(l10n JSON)]
    end

    CRED --> AUTH
    ENV --> AUTH
    ENV --> FETCH
    AUTH --> FETCH
    FETCH --> PARSE
    PARSE --> CMP
    DB --> CMP
    CMP --> DET
    DET --> STORE
    STORE --> DB
    DET --> TG
    TG -.->|fail| EM
    DB --> WEB
    DET --> WEB
    LF --> WEB
    FETCH --> JLOG
    AUTH --> LOG
    DET --> LOG
```

---

## 6. Deployment Architecture

```mermaid
flowchart TB
    subgraph WIN[Windows 11 Host]
        subgraph DIR[Project Directory]
            VENV[.venv Python 3.11+]
            SRC[src/ application code]
            DATA[data/snapshots.db]
            LOGS[logs/]
            JLOG[logs/json_responses.log]
        end
        subgraph TS[Task Scheduler]
            T1[08:00 task]
            T2[12:30 task]
            T3[18:00 task]
            CMD[run_check.cmd]
        end
    end

    subgraph NET[External Network]
        P[Inpol Portal HTTPS]
        TGT[Telegram API HTTPS]
        S[SMTP TLS]
    end

    T1 --> CMD
    T2 --> CMD
    T3 --> CMD
    CMD --> VENV
    VENV --> SRC
    SRC --> DATA
    SRC --> LOGS
    SRC --> JLOG
    SRC --> P
    SRC --> TGT
    SRC -.-> S

    USER[User] -->|Manual CLI| VENV
    USER -->|Web UI :5000| SRC
```

---

## 7. Architectural Patterns

| Pattern | Location | Description |
|---------|----------|-------------|
| Strategy | `detector.py` | 7 detector classes implement `BaseDetector.detect(old, new)` |
| Repository | `storage.py` | `SnapshotRepository` abstracts SQLite CRUD |
| Batch-then-notify | `notifier.py` | Collect all changes, send one batched message |
| Fallback chain | `notifier.py` → `email_notifier.py` | Telegram primary, email fallback |
| INSERT-only immutability | `storage.py` | Snapshots never updated/deleted; full history |
| Dependency injection | `orchestrator.py` | Storage/notifier/sessions passed to detector |
| i18n with fallback | `localization.py` + `models.py` | JSON bundles + hardcoded fallback maps |
| Session management | `session_manager.py` | HTTP session + CSRF + Akamai meta-refresh solve |

---

## 8. Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, requests, beautifulsoup4, lxml |
| Models | Pydantic v2 |
| Storage | SQLite (INSERT-only, immutable) |
| Web UI | Flask 3.0+, Bootstrap 5, HTMX, Jinja2 |
| Notifications | aiogram 3.x (Telegram), smtplib (SMTP) |
| Localization | JSON i18n (EN/PL/UA/RU) |
| Deployment | Windows Task Scheduler, Python venv |
| Testing | pytest, coverage >80% |

---

*Grounded in the actual codebase: `src/orchestrator.py`, `src/auth.py`, `src/session_manager.py`, `src/scraper.py`, `src/storage.py`, `src/detector.py`, `src/notifier.py`, `src/email_notifier.py`, `src/localization.py`, `src/models.py`, `src/web/routes.py`, `src/web/auth.py`.*

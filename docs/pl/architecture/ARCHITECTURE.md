# Inpol Monitor — Diagramy architektury i interakcji

Ten dokument zawiera wizualne reprezentacje architektury systemu i interakcji między komponentami projektu Inpol Monitor. Diagramy używają składni Mermaid i renderują się w GitHub, GitLab, VS Code oraz w dowolnej przeglądarce kompatybilnej z Mermaid.

Dostępne tłumaczenia: [English](../en/architecture/ARCHITECTURE.md) | [Polski](ARCHITECTURE.md) | [Русский](../ru/architecture/ARCHITECTURE.md) | [Українська](../ua/architecture/ARCHITECTURE.md)

---

## 1. Diagram komponentów

Ogólny widok warstw systemu i relacji między nimi.

```mermaid
flowchart TB
    subgraph EXT[Systemy zewnętrzne]
        INPOL[Portal Inpol\ninpol.mazowieckie.pl]
        TG[Telegram Bot API]
        SMTP[Serwer pocztowy SMTP]
        SCH[Harmon zadań Windows]
        USER[Użytkownik]
    end

    subgraph APP[Aplikacja Inpol Monitor]
        direction TB

        ORCH[orchestrator.py\nKoordynator cyklu sprawdzania]

        subgraph AUTH_L[Warstwa uwierzytelniania]
            AUTH[auth.py\nSekwencyjne uwierzytelnianie + CSRF]
            SESS[session_manager.py\nSesja HTTP + rozwiązywanie Akamai]
        end

        subgraph EXTRACT_L[Warstwa ekstrakcji danych]
            SCRAPER[scraper.py\nInpolScraper\nParsowanie HTML/JSON]
            CONFIG[config.py\n.env + credentials.json]
        end

        subgraph STORAGE_L[Warstwa przechowywania]
            REPO[storage.py\nSnapshotRepository\nTylko INSERT]
            DB[(SQLite\nsnapshots.db)]
        end

        subgraph DETECT_L[Warstwa wykrywania zmian]
            DET[detector.py\n7 strategii detektorów]
            MODELS[models.py\nModele Pydantic]
        end

        subgraph NOTIFY_L[Warstwa powiadomień]
            NOTIF[notifier.py\nTelegramNotifier\nNajpierw zbierz, potem wyślij]
            EMAIL[email_notifier.py\nZapasowa poczta]
            BOT[telegram_bot.py\nKomendy bota]
        end

        subgraph WEB_L[Warstwa webowa]
            WAUTH[web/auth.py\nUwierzytelnianie webowe]
            ROUTES[web/routes.py\nTrasy Flask]
            TPL[web/templates\nHTML]
        end

        L10N[localization.py\nSilnik i18n]
        LANGS[(en/pl/ru/ua.json\nPliki tłumaczeń)]
    end

    SCH -->|Uruchomienie o 08:00/12:30/18:00 CET| ORCH
    USER -->|Ręczne CLI| ORCH
    USER -->|Przeglądarka :5000| WAUTH

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
    NOTIF -->|Główny| TG
    NOTIF -.->|W razie błędu| EMAIL
    EMAIL -.->|Zapasowy| SMTP
    BOT --> NOTIF
    BOT --> REPO
    WAUTH --> CONFIG
    ROUTES --> REPO
    ROUTES --> DET
    ROUTES --> TPL
    ROUTES --> L10N
```

---

## 2. Diagram sekwencji — główny cykl sprawdzania

Pełny cykl monitoringu uruchamiany przez harmon zadań, ręczne CLI lub interfejs webowy.

```mermaid
sequenceDiagram
    autonumber
    actor S as Harmon / CLI
    participant O as Orchestrator
    participant C as Config
    participant A as Auth
    participant SM as SessionManager
    participant P as Portal Inpol
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

    loop Każde konto (sekwencyjnie)
        O->>A: authenticate_account(name, creds)
        A->>SM: login(email, password)
        SM->>P: GET /login (token CSRF)
        P-->>SM: HTML + CSRF
        SM->>P: POST dane + CSRF
        P-->>SM: Ciasteczka sesji
        SM-->>A: Sesja uwierzytelniona
        A-->>O: Session
    end

    loop Każdy case_id
        O->>SC: fetch_case_data(case_id)
        SC->>P: GET /api/case/{id}
        P-->>SC: JSON
        SC-->>O: CaseData

        O->>R: get_latest_snapshot(case_id)
        R->>DB: SELECT najnowszy
        DB-->>R: Poprzedni zrzut
        R-->>O: old_snapshot

        O->>D: detect_all_changes(old, new)
        D->>D: Uruchom 7 strategii
        D-->>O: List[Change]

        O->>R: save_snapshot(new)
        R->>DB: INSERT (niezmienne)
        DB-->>R: OK

        O->>N: queue_notification(case_id, changes)
    end

    O->>N: send_all_notifications()
    N->>TG: Wysyłka wsadowa
    alt Telegram OK
        TG-->>N: 200 OK
    else Telegram niedostępny
        N->>E: wyślij zapasowy mail
        E->>SMTP: Send
        SMTP-->>E: Wynik
    end

    O->>SM: close() wszystkie sesje
    O-->>S: kod wyjścia
```

---

## 3. Diagram sekwencji — szczegóły wykrywania zmian

Wzorzec strategii dla 7 typów zmian.

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

    loop Każde konto, każdy case
        DA->>R: get_latest_snapshot(case_id)
        R-->>DA: old_snapshot lub None
        DA->>DA: Zbuduj new_snapshot

        par Wzorzec strategii
            DA->>SD: detect(old, new)
            SD-->>DA: zmiany statusu
            DA->>DD: detect(old, new)
            DD-->>DA: dodane/usunięte dokumenty
            DA->>DT: detect(old, new)
            DT-->>DA: zmiany dat
            DA->>QD: detect(old, new)
            QD->>L: get_question_title/status
            L-->>QD: zlokalizowane etykiety
            QD-->>DA: diff pól pytań
            DA->>TD: detect(old, new)
            TD-->>DA: zdarzenia osi czasu
        end

        DA->>N: queue_notification(case_id, changes)
        DA->>R: save_snapshot(new)
    end

    DA-->>O: Dict[account, List[Change]]
```

7 typów zmian: `STATUS`, `NEW_DOCUMENT`, `REMOVED_DOCUMENT`, `DECISION_DATE_CHANGE`, `SUBMIT_DATE_CHANGE`, `UPDATED_AT_CHANGE`, `TIMELINE_EVENT_ADDED`, a także typy poziomu pytań (`QUESTION_ASKED`, `QUESTION_ANSWERED`, `QUESTION_COUNT_CHANGE`, `NEW_QUESTION_DETAIL`).

---

## 4. Diagram sekwencji — interfejs webowy

Aplikacja webowa Flask: logowanie, lista zrzutów, porównanie dwóch zrzutów.

```mermaid
sequenceDiagram
    autonumber
    actor U as Użytkownik
    participant B as Przeglądarka
    participant R as web/routes.py
    participant WA as web/auth.py
    participant REP as SnapshotRepository
    participant D as detector.py
    participant L as localization.py
    participant T as Szablony Jinja2

    U->>B: Otwórz http://localhost:5000
    B->>R: GET /
    R->>WA: sprawdzenie login_required
    alt Nieuwierzytelniony
        R-->>B: Przekierowanie /login
        B->>R: GET /login
        R->>T: Renderuj login.html
        T-->>B: Formularz logowania
        U->>B: Wyślij dane
        B->>R: POST /login
        R->>WA: verify_credentials()
        WA-->>R: Poprawne / Niepoprawne
        R-->>B: Ustaw ciasteczko + przekieruj
    else Uwierzytelniony
        R->>REP: get_all_snapshots(filters)
        REP-->>R: Zrzuty
        R->>L: tłumaczenia interfejsu
        L-->>R: Zlokalizowane ciągi
        R->>T: Renderuj index.html
        T-->>B: Lista zrzutów

        U->>B: Kliknij "Porównaj" dla 2 zrzutów
        B->>R: GET /compare?snap1=X&snap2=Y
        R->>REP: get_snapshot(id1), get_snapshot(id2)
        R->>D: detect_all_changes(old, new)
        D-->>R: diff na poziomie pól
        R->>L: Tłumacz etykiety
        L-->>R: Zlokalizowane etykiety
        R->>T: Renderuj compare.html
        T-->>B: Porównanie obok siebie z podświetleniem
    end
```

Kluczowe trasy (`src/web/routes.py`): `index`, `login`, `logout`, `compare`, `build_comparison`, `delete`, `set_language`.

---

## 5. Diagram przepływu danych

```mermaid
flowchart LR
    subgraph IN[Wejścia]
        CRED[credentials.json]
        ENV[.env]
        WC[dane uwierzytelniające web]
    end

    subgraph PIPE[Potok]
        AUTH[Uwierzytelnianie]
        FETCH[Pobierz dane]
        PARSE[Analiza]
        CMP[Porównanie zrzutów]
        DET[Wykrywanie zmian]
        STORE[Zapisz niemutowalny zrzut]
    end

    subgraph OUT[Wyjścia]
        TG[Telegram]
        EM[Zapasowa poczta]
        WEB[Interfejs webowy]
        LOG[Dzienniki]
        JLOG[Dziennik odpowiedzi JSON]
    end

    subgraph STORE[Magazyn]
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
    TG -.->|błąd| EM
    DB --> WEB
    DET --> WEB
    LF --> WEB
    FETCH --> JLOG
    AUTH --> LOG
    DET --> LOG
```

---

## 6. Architektura wdrożenia

```mermaid
flowchart TB
    subgraph WIN[Host Windows 11]
        subgraph DIR[Katalog projektu]
            VENV[.venv Python 3.11+]
            SRC[src/ kod aplikacji]
            DATA[data/snapshots.db]
            LOGS[logs/]
            JLOG[logs/json_responses.log]
        end
        subgraph TS[Harmon zadań]
            T1[Zadanie 08:00]
            T2[Zadanie 12:30]
            T3[Zadanie 18:00]
            CMD[run_check.cmd]
        end
    end

    subgraph NET[Sieć zewnętrzna]
        P[Portal Inpol HTTPS]
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

    USER[Użytkownik] -->|Ręczne CLI| VENV
    USER -->|Web :5000| SRC
```

---

## 7. Wzorce architektoniczne

| Wzorzec | Lokalizacja | Opis |
|---------|--------------|----------|
| Strategy | `detector.py` | 7 klas detektorów implementuje `BaseDetector.detect(old, new)` |
| Repository | `storage.py` | `SnapshotRepository` abstrahuje operacje SQLite |
| Najpierw zbierz, potem wyślij | `notifier.py` | Zbierz wszystkie zmiany, wyślij jedną wiadomość |
| Łańcuch zapasowy | `notifier.py` → `email_notifier.py` | Główny kanał — Telegram, zapasowy — poczta |
| Niemutowalność tylko INSERT | `storage.py` | Zrzuty nigdy nie są aktualizowane ani usuwane |
| Wstrzykiwanie zależności | `orchestrator.py` | Magazyn/powiadomiacz/sesje przekazywane detektorowi |
| i18n z zapasem | `localization.py` + `models.py` | Pakiety JSON + zaszyfrowane mapy zapasowe |
| Zarządzanie sesją | `session_manager.py` | Sesja HTTP + CSRF + rozwiązywanie challenge Akamai przez meta-refresh |

---

## 8. Stos technologiczny

| Warstwa | Technologia |
|------|------------|
| Backend | Python 3.11+, requests, beautifulsoup4, lxml |
| Modele | Pydantic v2 |
| Przechowywanie | SQLite (tylko INSERT, niezmienne) |
| Interfejs webowy | Flask 3.0+, Bootstrap 5, HTMX, Jinja2 |
| Powiadomienia | aiogram 3.x (Telegram), smtplib (SMTP) |
| Lokalizacja | JSON i18n (EN/PL/UA/RU) |
| Wdrożenie | Harmon zadań Windows, Python venv |
| Testowanie | pytest, pokrycie >80% |

---

*Oparte na prawdziwym kodzie: `src/orchestrator.py`, `src/auth.py`, `src/session_manager.py`, `src/scraper.py`, `src/storage.py`, `src/detector.py`, `src/notifier.py`, `src/email_notifier.py`, `src/localization.py`, `src/models.py`, `src/web/routes.py`, `src/web/auth.py`.*

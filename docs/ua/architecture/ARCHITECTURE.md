# Inpol Monitor — Діаграми архітектури та взаємодій

Цей документ містить візуальні представлення архітектури системи та взаємодії між компонентами проєкту Inpol Monitor. Діаграми використовують синтаксис Mermaid і відображаються в GitHub, GitLab, VS Code та будь-якому сумісному переглядачу Mermaid.

Доступні переклади: [English](../../en/architecture/ARCHITECTURE.md) | [Polski](../../pl/architecture/ARCHITECTURE.md) | [Русский](../../ru/architecture/ARCHITECTURE.md) | [Українська](ARCHITECTURE.md)

---

## 1. Діаграма компонентів

Загальний вигляд шарів системи та зв'язків між ними.

```mermaid
flowchart TB
    subgraph EXT[Зовнішні системи]
        INPOL[Портал Inpol\ninpol.mazowieckie.pl]
        TG[Telegram Bot API]
        SMTP[SMTP сервер пошти]
        SCH[Планувальник задач Windows]
        USER[Користувач]
    end

    subgraph APP[Застосунок Inpol Monitor]
        direction TB

        ORCH[orchestrator.py\nКоординатор циклу перевірки]

        subgraph AUTH_L[Шар автентифікації]
            AUTH[auth.py\nПослідовна автентифікація + CSRF]
            SESS[session_manager.py\nHTTP-сесія + розв'язання Akamai]
        end

        subgraph EXTRACT_L[Шар витягування даних]
            SCRAPER[scraper.py\nInpolScraper\nПарсинг HTML/JSON]
            CONFIG[config.py\n.env + credentials.json]
        end

        subgraph STORAGE_L[Шар зберігання]
            REPO[storage.py\nSnapshotRepository\nТільки INSERT]
            DB[(SQLite\nsnapshots.db)]
        end

        subgraph DETECT_L[Шар виявлення змін]
            DET[detector.py\n7 стратегій-детекторів]
            MODELS[models.py\nМоделі Pydantic]
        end

        subgraph NOTIFY_L[Шар сповіщень]
            NOTIF[notifier.py\nTelegramNotifier\nСпершу зібрати, потім надіслати]
            EMAIL[email_notifier.py\nРезервна пошта]
            BOT[telegram_bot.py\nКоманди бота]
        end

        subgraph WEB_L[Веб-шар]
            WAUTH[web/auth.py\nВеб-автентифікація]
            ROUTES[web/routes.py\nМаршрути Flask]
            TPL[web/templates\nHTML]
        end

        L10N[localization.py\nРушій i18n]
        LANGS[(en/pl/ru/ua.json\nФайли перекладів)]
    end

    SCH -->|Запуск о 08:00/12:30/18:00 CET| ORCH
    USER -->|Ручний CLI| ORCH
    USER -->|Браузер :5000| WAUTH

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
    NOTIF -->|Основний| TG
    NOTIF -.->|При збої| EMAIL
    EMAIL -.->|Резервний| SMTP
    BOT --> NOTIF
    BOT --> REPO
    WAUTH --> CONFIG
    ROUTES --> REPO
    ROUTES --> DET
    ROUTES --> TPL
    ROUTES --> L10N
```

---

## 2. Діаграма послідовності — головний цикл перевірки

Повний цикл моніторингу, що запускається планувальником задач, ручним CLI або веб-інтерфейсом.

```mermaid
sequenceDiagram
    autonumber
    actor S as Планувальник / CLI
    participant O as Orchestrator
    participant C as Config
    participant A as Auth
    participant SM as SessionManager
    participant P as Портал Inpol
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

    loop Кожен акаунт (послідовно)
        O->>A: authenticate_account(name, creds)
        A->>SM: login(email, password)
        SM->>P: GET /login (CSRF токен)
        P-->>SM: HTML + CSRF
        SM->>P: POST облікові дані + CSRF
        P-->>SM: Кукі сесії
        SM-->>A: Аутентифікована сесія
        A-->>O: Session
    end

    loop Кожен case_id
        O->>SC: fetch_case_data(case_id)
        SC->>P: GET /api/case/{id}
        P-->>SC: JSON
        SC-->>O: CaseData

        O->>R: get_latest_snapshot(case_id)
        R->>DB: SELECT останній
        DB-->>R: Попередній знімок
        R-->>O: old_snapshot

        O->>D: detect_all_changes(old, new)
        D->>D: Запуск 7 стратегій
        D-->>O: List[Change]

        O->>R: save_snapshot(new)
        R->>DB: INSERT (незмінювано)
        DB-->>R: OK

        O->>N: queue_notification(case_id, changes)
    end

    O->>N: send_all_notifications()
    N->>TG: Пакетна відправка
    alt Telegram OK
        TG-->>N: 200 OK
    else Telegram недоступний
        N->>E: надіслати резервний лист
        E->>SMTP: Send
        SMTP-->>E: Результат
    end

    O->>SM: close() всі сесії
    O-->>S: код виходу
```

---

## 3. Діаграма послідовності — деталі виявлення змін

Паттерн «Стратегія» для 7 типів змін.

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

    loop Кожен акаунт, кожен case
        DA->>R: get_latest_snapshot(case_id)
        R-->>DA: old_snapshot або None
        DA->>DA: Побудувати new_snapshot

        par Паттерн «Стратегія»
            DA->>SD: detect(old, new)
            SD-->>DA: зміни статусу
            DA->>DD: detect(old, new)
            DD-->>DA: додані/видалені документи
            DA->>DT: detect(old, new)
            DT-->>DA: зміни дат
            DA->>QD: detect(old, new)
            QD->>L: get_question_title/status
            L-->>QD: локалізовані мітки
            QD-->>DA: diff по полях питань
            DA->>TD: detect(old, new)
            TD-->>DA: події таймлайну
        end

        DA->>N: queue_notification(case_id, changes)
        DA->>R: save_snapshot(new)
    end

    DA-->>O: Dict[account, List[Change]]
```

7 типів змін: `STATUS`, `NEW_DOCUMENT`, `REMOVED_DOCUMENT`, `DECISION_DATE_CHANGE`, `SUBMIT_DATE_CHANGE`, `UPDATED_AT_CHANGE`, `TIMELINE_EVENT_ADDED`, а також типи рівня питань (`QUESTION_ASKED`, `QUESTION_ANSWERED`, `QUESTION_COUNT_CHANGE`, `NEW_QUESTION_DETAIL`).

---

## 4. Діаграма послідовності — веб-інтерфейс

Веб-застосунок Flask: вхід, список знімків, порівняння двох знімків.

```mermaid
sequenceDiagram
    autonumber
    actor U as Користувач
    participant B as Браузер
    participant R as web/routes.py
    participant WA as web/auth.py
    participant REP as SnapshotRepository
    participant D as detector.py
    participant L as localization.py
    participant T as Jinja2 шаблони

    U->>B: Відкрити http://localhost:5000
    B->>R: GET /
    R->>WA: перевірка login_required
    alt Не автентифіковано
        R-->>B: Редирект /login
        B->>R: GET /login
        R->>T: Render login.html
        T-->>B: Форма входу
        U->>B: Ввід облікових даних
        B->>R: POST /login
        R->>WA: verify_credentials()
        WA-->>R: Валідно / Невалідно
        R-->>B: Встановити cookie + редирект
    else Автентифіковано
        R->>REP: get_all_snapshots(filters)
        REP-->>R: Знімки
        R->>L: переклади інтерфейсу
        L-->>R: Локалізовані рядки
        R->>T: Render index.html
        T-->>B: Список знімків

        U->>B: Натиснути "Порівняти" для 2 знімків
        B->>R: GET /compare?snap1=X&snap2=Y
        R->>REP: get_snapshot(id1), get_snapshot(id2)
        R->>D: detect_all_changes(old, new)
        D-->>R: diff по полях
        R->>L: Переклад міток
        L-->>R: Локалізовані мітки
        R->>T: Render compare.html
        T-->>B: Порівняння бок об бок з підсвіткою
    end
```

Ключові маршрути (`src/web/routes.py`): `index`, `login`, `logout`, `compare`, `build_comparison`, `delete`, `set_language`.

---

## 5. Діаграма потоку даних

```mermaid
flowchart LR
    subgraph IN[Входи]
        CRED[credentials.json]
        ENV[.env]
        WC[веб-облікові дані]
    end

    subgraph PIPE[Конвеєр]
        AUTH[Аутентифікація]
        FETCH[Отримання даних]
        PARSE[Парсинг]
        CMP[Порівняння знімків]
        DET[Виявлення змін]
        STORE[Збереження знімка]
    end

    subgraph OUT[Виходи]
        TG[Telegram]
        EM[Резервна пошта]
        WEB[Веб-інтерфейс]
        LOG[Журнали]
        JLOG[Журнал JSON-відповідей]
    end

    subgraph STORE[Сховище]
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
    TG -.->|збій| EM
    DB --> WEB
    DET --> WEB
    LF --> WEB
    FETCH --> JLOG
    AUTH --> LOG
    DET --> LOG
```

---

## 6. Діаграма розгортання

```mermaid
flowchart TB
    subgraph WIN[Хост Windows 11]
        subgraph DIR[Каталог проєкту]
            VENV[.venv Python 3.11+]
            SRC[src/ код застосунку]
            DATA[data/snapshots.db]
            LOGS[logs/]
            JLOG[logs/json_responses.log]
        end
        subgraph TS[Планувальник задач]
            T1[Задача 08:00]
            T2[Задача 12:30]
            T3[Задача 18:00]
            CMD[run_check.cmd]
        end
    end

    subgraph NET[Зовнішня мережа]
        P[Портал Inpol HTTPS]
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

    USER[Користувач] -->|Ручний CLI| VENV
    USER -->|Веб :5000| SRC
```

---

## 7. Архітектурні паттерни

| Паттерн | Розташування | Опис |
|---------|--------------|----------|
| Strategy | `detector.py` | 7 класів-детекторів реалізують `BaseDetector.detect(old, new)` |
| Repository | `storage.py` | `SnapshotRepository` абстрагує операції SQLite |
| Спершу зібрати, потім надіслати | `notifier.py` | Зібрати всі зміни, надіслати одним повідомленням |
| Ланцюжок резервів | `notifier.py` → `email_notifier.py` | Основний канал — Telegram, резервний — пошта |
| Незмінність тільки INSERT | `storage.py` | Знімки ніколи не оновлюються і не видаляються |
| Впровадження залежностей | `orchestrator.py` | Сховище/сповіщувач/сесії передаються детектору |
| i18n з резервом | `localization.py` + `models.py` | JSON-словники + жорстко задані резервні відповідності |
| Керування сесією | `session_manager.py` | HTTP-сесія + CSRF + розв'язання challenge Akamai через meta-refresh |

---

## 8. Технологічний стек

| Шар | Технологія |
|------|------------|
| Бекенд | Python 3.11+, requests, beautifulsoup4, lxml |
| Моделі | Pydantic v2 |
| Зберігання | SQLite (тільки INSERT, незмінювано) |
| Веб-інтерфейс | Flask 3.0+, Bootstrap 5, HTMX, Jinja2 |
| Сповіщення | aiogram 3.x (Telegram), smtplib (SMTP) |
| Локалізація | JSON i18n (EN/PL/UA/RU) |
| Розгортання | Планувальник задач Windows, Python venv |
| Тестування | pytest, покриття >80% |

---

*Ґрунтується на реальному коді: `src/orchestrator.py`, `src/auth.py`, `src/session_manager.py`, `src/scraper.py`, `src/storage.py`, `src/detector.py`, `src/notifier.py`, `src/email_notifier.py`, `src/localization.py`, `src/models.py`, `src/web/routes.py`, `src/web/auth.py`.*

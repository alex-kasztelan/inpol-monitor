# Inpol Monitor — Диаграммы архитектуры и взаимодействий

Этот документ содержит визуальные представления архитектуры системы и взаимодействия между компонентами проекта Inpol Monitor. Диаграммы используют синтаксис Mermaid и отображаются в GitHub, GitLab, VS Code и любом совместимом с Mermaid просмотрщике.

Доступные переводы: [English](../../en/architecture/ARCHITECTURE.md) | [Polski](../../pl/architecture/ARCHITECTURE.md) | [Русский](ARCHITECTURE.md) | [Українська](../../ua/architecture/ARCHITECTURE.md)

---

## 1. Диаграмма компонентов

Общий вид слоёв системы и связей между ними.

```mermaid
flowchart TB
    subgraph EXT[Внешние системы]
        INPOL[Портал Inpol\ninpol.mazowieckie.pl]
        TG[Telegram Bot API]
        SMTP[SMTP сервер почты]
        SCH[Планировщик задач Windows]
        USER[Пользователь]
    end

    subgraph APP[Приложение Inpol Monitor]
        direction TB

        ORCH[orchestrator.py\nКоординатор цикла проверки]

        subgraph AUTH_L[Слой аутентификации]
            AUTH[auth.py\nПоследовательная аутентификация + CSRF]
            SESS[session_manager.py\nHTTP-сессия + решение Akamai]
        end

        subgraph EXTRACT_L[Слой извлечения данных]
            SCRAPER[scraper.py\nInpolScraper\nПарсинг HTML/JSON]
            CONFIG[config.py\n.env + credentials.json]
        end

        subgraph STORAGE_L[Слой хранения]
            REPO[storage.py\nSnapshotRepository\nТолько INSERT]
            DB[(SQLite\nsnapshots.db)]
        end

        subgraph DETECT_L[Слой обнаружения изменений]
            DET[detector.py\n7 стратегий-детекторов]
            MODELS[models.py\nМодели Pydantic]
        end

        subgraph NOTIFY_L[Слой уведомлений]
            NOTIF[notifier.py\nTelegramNotifier\nСначала собрать, потом отправить]
            EMAIL[email_notifier.py\nРезервная почта]
            BOT[telegram_bot.py\nКоманды бота]
        end

        subgraph WEB_L[Веб-слой]
            WAUTH[web/auth.py\nВеб-аутентификация]
            ROUTES[web/routes.py\nМаршруты Flask]
            TPL[web/templates\nHTML]
        end

        L10N[localization.py\nДвижок i18n]
        LANGS[(en/pl/ru/ua.json\nФайлы переводов)]
    end

    SCH -->|Запуск в 08:00/12:30/18:00 CET| ORCH
    USER -->|Ручной CLI| ORCH
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
    NOTIF -->|Основной| TG
    NOTIF -.->|При сбое| EMAIL
    EMAIL -.->|Резервный| SMTP
    BOT --> NOTIF
    BOT --> REPO
    WAUTH --> CONFIG
    ROUTES --> REPO
    ROUTES --> DET
    ROUTES --> TPL
    ROUTES --> L10N
```

---

## 2. Диаграмма последовательности — основной цикл проверки

Полный цикл мониторинга, запускаемый планировщиком задач, ручным CLI или веб-интерфейсом.

```mermaid
sequenceDiagram
    autonumber
    actor S as Планировщик / CLI
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

    loop Каждый аккаунт (последовательно)
        O->>A: authenticate_account(name, creds)
        A->>SM: login(email, password)
        SM->>P: GET /login (CSRF токен)
        P-->>SM: HTML + CSRF
        SM->>P: POST учётные данные + CSRF
        P-->>SM: Куки сессии
        SM-->>A: Аутентифицированная сессия
        A-->>O: Session
    end

    loop Каждый case_id
        O->>SC: fetch_case_data(case_id)
        SC->>P: GET /api/case/{id}
        P-->>SC: JSON
        SC-->>O: CaseData

        O->>R: get_latest_snapshot(case_id)
        R->>DB: SELECT последний
        DB-->>R: Предыдущий снимок
        R-->>O: old_snapshot

        O->>D: detect_all_changes(old, new)
        D->>D: Запуск 7 стратегий
        D-->>O: List[Change]

        O->>R: save_snapshot(new)
        R->>DB: INSERT (неизменяемо)
        DB-->>R: OK

        O->>N: queue_notification(case_id, changes)
    end

    O->>N: send_all_notifications()
    N->>TG: Пакетная отправка
    alt Telegram OK
        TG-->>N: 200 OK
    else Telegram недоступен
        N->>E: отправить резервное письмо
        E->>SMTP: Send
        SMTP-->>E: Результат
    end

    O->>SM: close() все сессии
    O-->>S: код выхода
```

---

## 3. Диаграмма последовательности — детали обнаружения изменений

Паттерн «Стратегия» для 7 типов изменений.

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

    loop Каждый аккаунт, каждый case
        DA->>R: get_latest_snapshot(case_id)
        R-->>DA: old_snapshot или None
        DA->>DA: Построить new_snapshot

        par Паттерн «Стратегия»
            DA->>SD: detect(old, new)
            SD-->>DA: изменения статуса
            DA->>DD: detect(old, new)
            DD-->>DA: добавленные/удалённые документы
            DA->>DT: detect(old, new)
            DT-->>DA: изменения дат
            DA->>QD: detect(old, new)
            QD->>L: get_question_title/status
            L-->>QD: локализованные метки
            QD-->>DA: diff по полям вопросов
            DA->>TD: detect(old, new)
            TD-->>DA: события таймлайна
        end

        DA->>N: queue_notification(case_id, changes)
        DA->>R: save_snapshot(new)
    end

    DA-->>O: Dict[account, List[Change]]
```

7 типов изменений: `STATUS`, `NEW_DOCUMENT`, `REMOVED_DOCUMENT`, `DECISION_DATE_CHANGE`, `SUBMIT_DATE_CHANGE`, `UPDATED_AT_CHANGE`, `TIMELINE_EVENT_ADDED`, а также типы уровня вопросов (`QUESTION_ASKED`, `QUESTION_ANSWERED`, `QUESTION_COUNT_CHANGE`, `NEW_QUESTION_DETAIL`).

---

## 4. Диаграмма последовательности — веб-интерфейс

Веб-приложение Flask: вход, список снимков, сравнение двух снимков.

```mermaid
sequenceDiagram
    autonumber
    actor U as Пользователь
    participant B as Браузер
    participant R as web/routes.py
    participant WA as web/auth.py
    participant REP as SnapshotRepository
    participant D as detector.py
    participant L as localization.py
    participant T as Jinja2 шаблоны

    U->>B: Открыть http://localhost:5000
    B->>R: GET /
    R->>WA: проверка login_required
    alt Не аутентифицирован
        R-->>B: Редирект /login
        B->>R: GET /login
        R->>T: Render login.html
        T-->>B: Форма входа
        U->>B: Ввод учётных данных
        B->>R: POST /login
        R->>WA: verify_credentials()
        WA-->>R: Валидно / Невалидно
        R-->>B: Установить cookie + редирект
    else Аутентифицирован
        R->>REP: get_all_snapshots(filters)
        REP-->>R: Снимки
        R->>L: переводы интерфейса
        L-->>R: Локализованные строки
        R->>T: Render index.html
        T-->>B: Список снимков

        U->>B: Нажать "Сравнить" для 2 снимков
        B->>R: GET /compare?snap1=X&snap2=Y
        R->>REP: get_snapshot(id1), get_snapshot(id2)
        R->>D: detect_all_changes(old, new)
        D-->>R: diff по полям
        R->>L: Перевод меток
        L-->>R: Локализованные метки
        R->>T: Render compare.html
        T-->>B: Сравнение бок о бок с подсветкой
    end
```

Ключевые маршруты (`src/web/routes.py`): `index`, `login`, `logout`, `compare`, `build_comparison`, `delete`, `set_language`.

---

## 5. Сводка потока данных

```mermaid
flowchart LR
    subgraph IN[Входы]
        CRED[credentials.json]
        ENV[.env]
        WC[веб-учётные данные]
    end

    subgraph PIPE[Конвейер]
        AUTH[Аутентификация]
        FETCH[Получение данных]
        PARSE[Парсинг]
        CMP[Сравнение снимков]
        DET[Обнаружение изменений]
        STORE[Сохранение снимка]
    end

    subgraph OUT[Выходы]
        TG[Telegram]
        EM[Резервная почта]
        WEB[Веб-интерфейс]
        LOG[Журналы]
        JLOG[Журнал JSON-ответов]
    end

    subgraph STORE[Хранилище]
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
    TG -.->|сбой| EM
    DB --> WEB
    DET --> WEB
    LF --> WEB
    FETCH --> JLOG
    AUTH --> LOG
    DET --> LOG
```

---

## 6. Архитектура развёртывания

```mermaid
flowchart TB
    subgraph WIN[Хост Windows 11]
        subgraph DIR[Каталог проекта]
            VENV[.venv Python 3.11+]
            SRC[src/ код приложения]
            DATA[data/snapshots.db]
            LOGS[logs/]
            JLOG[logs/json_responses.log]
        end
        subgraph TS[Планировщик задач]
            T1[Задача 08:00]
            T2[Задача 12:30]
            T3[Задача 18:00]
            CMD[run_check.cmd]
        end
    end

    subgraph NET[Внешняя сеть]
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

    USER[Пользователь] -->|Ручной CLI| VENV
    USER -->|Веб :5000| SRC
```

---

## 7. Архитектурные паттерны

| Паттерн | Расположение | Описание |
|---------|--------------|----------|
| Strategy | `detector.py` | 7 классов-детекторов реализуют `BaseDetector.detect(old, new)` |
| Repository | `storage.py` | `SnapshotRepository` абстрагирует операции SQLite |
| Сначала собрать, потом отправить | `notifier.py` | Собрать все изменения, отправить одним сообщением |
| Цепочка резервов | `notifier.py` → `email_notifier.py` | Основной канал — Telegram, резервный — почта |
| Неизменяемость только INSERT | `storage.py` | Снимки никогда не обновляются и не удаляются |
| Внедрение зависимостей | `orchestrator.py` | Хранилище/уведомитель/сессии передаются детектору |
| i18n с резервом | `localization.py` + `models.py` | JSON-словари + жёстко заданные резервные соответствия |
| Управление сессией | `session_manager.py` | HTTP-сессия + CSRF + решение challenge Akamai через meta-refresh |

---

## 8. Технологический стек

| Слой | Технология |
|------|------------|
| Бэкенд | Python 3.11+, requests, beautifulsoup4, lxml |
| Модели | Pydantic v2 |
| Хранение | SQLite (только INSERT, неизменяемо) |
| Веб-интерфейс | Flask 3.0+, Bootstrap 5, HTMX, Jinja2 |
| Уведомления | aiogram 3.x (Telegram), smtplib (SMTP) |
| Локализация | JSON i18n (EN/PL/UA/RU) |
| Развёртывание | Планировщик задач Windows, Python venv |
| Тестирование | pytest, покрытие >80% |

---

*На основе реального кода: `src/orchestrator.py`, `src/auth.py`, `src/session_manager.py`, `src/scraper.py`, `src/storage.py`, `src/detector.py`, `src/notifier.py`, `src/email_notifier.py`, `src/localization.py`, `src/models.py`, `src/web/routes.py`, `src/web/auth.py`.*

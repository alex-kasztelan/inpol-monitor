# Inpol Monitor — Діаграми взаємодій системи

Детальні діаграми взаємодій, засновані на реальній базі коду. Усі потоки отримано з реалізації в `src/`, `.planning/` та архітектурі застосунку.

Доступні переклади: [English](../en/system-interactions/SYSTEM_INTERACTIONS.md) | [Polski](../pl/system-interactions/SYSTEM_INTERACTIONS.md) | [Русский](../ru/system-interactions/SYSTEM_INTERACTIONS.md) | [Українська](SYSTEM_INTERACTIONS.md)

---

## 1. Потік автентифікації (послідовна автентифікація з CSRF)

```mermaid
sequenceDiagram
    autonumber
    participant O as Orchestrator
    participant A as auth.py
    participant SM as SessionManager
    participant P as Портал Inpol

    O->>A: authenticate_account(name, creds)
    A->>SM: SessionManager(base_url)
    SM->>P: GET /login сторінка
    P-->>SM: HTML з CSRF токеном
    SM->>SM: Зберегти CSRF токен у сесії
    SM->>P: POST /login (email, password, CSRF)
    P-->>SM: Кукі сесії

    alt Виявлено JS-challenge Akamai
        SM->>P: meta-refresh очікування (~2с)
        P-->>SM: Сторінка челленджу
        SM->>SM: Розв'язати челлендж
        SM->>P: Повторити POST даних
        P-->>SM: Кукі сесії
    else Прямий вхід
        SM-->>A: Аутентифікована сесія
    end

    A-->>O: Об'єкт сесії (logged_in=True)
```

**Ключові методи** (`src/auth.py`, `src/session_manager.py`):
- `authenticate_account(name, creds)` — точка входу послідовної автентифікації
- `run_sequential_auth()` — обробляє всі налаштовані акаунти
- `login(email, password)` — виконує автентифікацію
- `_has_akamai_challenge(html)` — виявляє захист Akamai
- `_solve_challenge(html, url)` — розв'язувач через meta-refresh (~2с очікування на виклик API)

---

## 2. Потік витягування даних

```mermaid
sequenceDiagram
    autonumber
    participant O as Orchestrator
    participant SC as Scraper
    participant SM as SessionManager
    participant P as Портал Inpol
    participant L as localization.py

    O->>SC: fetch_case_data(case_id)
    SC->>SM: GET /api/case/{id}
    SM->>P: HTTP запит із сесією
    P-->>SM: JSON відповідь
    SM-->>SC: Дані відповіді

    SC->>SC: Парсинг CaseData (Pydantic)
    SC->>L: get_status_label(status_id)
    L-->>SC: Локалізована мітка статусу
    SC->>L: get_question_title(title_id)
    L-->>SC: Локалізований заголовок питання

    SC-->>O: CaseData(person_first, person_last, case_number, status_raw, status_label, attachments, questions, timeline, related_docs, timeline_events)
```

**Ключові методи** (`src/scraper.py`):
- `fetch_case_data(case_id)` — витягує модель CaseData Pydantic
- `fetch_questions(case_id)` — витягує дані питань із всіма 7 полями
- `fetch_attachments(case_id)` — витягує вкладення документів
- `_resolve_status_label(code)` — мапить коди статусів на зрозумілі мітки
- `_resolve_question_title(id)` — мапить заголовки питань через локалізацію
- `fetch_all_for_case(case_id)` — коорординує повне отримання даних справи

---

## 3. Потік зберігання (тільки INSERT, незмінне)

```mermaid
sequenceDiagram
    autonumber
    participant O as Orchestrator
    participant R as SnapshotRepository
    participant DB as SQLite

    O->>R: get_latest_snapshot(case_id)
    R->>DB: SELECT * FROM snapshots WHERE case_id=? ORDER BY timestamp DESC LIMIT 1
    DB-->>R: Попередній знімок (або None)
    R-->>O: old_snapshot

    O->>R: save_snapshot(new_snapshot)
    R->>DB: INSERT INTO snapshots (account_id, case_id, endpoint_type, raw_json, parsed_data, timestamp)
    DB-->>R: ID рядка
    R-->>O: Успіх

    Note over R,DB: Знімки ніколи не оновлюються і не видаляються
    Note over R,DB: Повне історичне зберігання (STORE-02)
```

**Ключові методи** (`src/storage.py`):
- `save_snapshot(snapshot)` — тільки INSERT, ніколи не оновлює/не видаляє
- `get_latest_snapshot(case_id)` — найсвіжіший знімок для справи
- `get_previous_snapshot(case_id)` — другий найсвіжіший
- `get_all_snapshots()` — повні історичні записи
- `get_snapshots_by_account(account_id)` — фільтр за акаунтом
- `get_distinct_case_ids()` — глобально унікальні ID справ (STORE-03)
- `get_snapshot_by_id(id)` — отримання одного знімка

---

## 4. Потік виявлення змін (паттерн «Стратегія»)

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

    loop Кожен акаунт, кожна справа
        DA->>R: get_latest_snapshot(case_id)
        R-->>DA: old_snapshot або None
        DA->>DA: Побудувати new_snapshot з даних scraper'а

        par Запуск стратегій детекторів
            DA->>SD: detect(old, new)
            SD-->>DA: [Change] або []
            DA->>DD: detect(old, new)
            DD-->>DA: [Change] або []
            DA->>DT: detect(old, new)
            DT-->>DA: [Change] або []
            DA->>QD: detect(old, new)
            QD->>L: get_question_title/status
            L-->>QD: Локалізовані мітки
            QD-->>DA: [Change] або []
            DA->>TD: detect(old, new)
            TD-->>DA: [Change] або []
        end

        DA->>N: queue_notification(case_id, all_changes)
        DA->>R: save_snapshot(new_snapshot)
    end

    DA-->>O: Dict[account, List[Change]]
```

**7 типів змін** (`src/models.py` `ChangeType`):
- `STATUS` — зміна коду статусу
- `NEW_DOCUMENT` — додано новий документ
- `REMOVED_DOCUMENT` — документ видалено
- `DECISION_DATE_CHANGE` — змінено дату рішення
- `SUBMIT_DATE_CHANGE` — змінено дату подачі
- `UPDATED_AT_CHANGE` — змінено мітку часу updated_at
- `TIMELINE_EVENT_ADDED` — нову подію таймлайну

А також типи рівня питань: `QUESTION_ASKED`, `QUESTION_ANSWERED`, `QUESTION_COUNT_CHANGE`, `NEW_QUESTION_DETAIL`.

**Ключові методи** (`src/detector.py`):
- `BaseDetector.detect(old, new)` — абстрактний інтерфейс стратегії
- Кожен детектор повертає `List[Change]` (пустий список при відсутності змін)
- М'яка обробка `old_snapshot=None` (сценарій першого запуску)

---

## 5. Потік сповіщень Telegram (спершу зібрати, потім надіслати)

```mermaid
sequenceDiagram
    autonumber
    participant D as Detector
    participant N as TelegramNotifier
    participant C as Config
    participant TG as Telegram API
    participant E as EmailNotifier

    D->>N: queue_notification(case_id, changes)
    N->>N: Зберегти у внутрішній черзі

    loop Усі зібрані сповіщення
        N->>N: Зібрати повідомлення з ID справи, змінами, локалізованими мітками
    end

    N->>N: send_all_notifications()
    N->>C: get_notification_language()
    C-->>N: Код мови (en/pl/ru/ua)
    N->>TG: send_message(chat_id, text, parse_mode='Markdown')

    alt Telegram OK
        TG-->>N: 200 OK
    else Telegram недоступний
        N->>E: _send_fallback_email()
        E->>C: get_smtp_config()
        C-->>E: Сервер SMTP, порт, користувач, пароль
        E->>SMTP: connect() з TLS
        SMTP-->>E: Підключено
        E->>SMTP: sendmail(from, to, subject, html_body)
        SMTP-->>E: Повідомлення прийнято
    end
```

**Ключові методи** (`src/notifier.py`):
- `send_all_notifications()` — ітерує всі сповіщення у черзі
- `_build_change_message()` — багате повідомлення Markdown з деталями справи
- `_build_single_message()` — повідомлення однієї справи
- `_build_error_message()` — формат сповіщення про помилку
- `_send_fallback_email()` — запускає резервну пошту
- `_tn()` — помічник локалізації для ключів сповіщень
- `_resolve_chat_id(user_id)` — мапить ID користувачів на чати Telegram

---

## 6. Потік резервної пошти

```mermaid
sequenceDiagram
    autonumber
    participant N as TelegramNotifier
    participant E as EmailNotifier
    participant C as Config
    participant S as Сервер SMTP
    participant U as Отримувач

    N->>C: get_email_enabled()
    C-->>N: false (за замовчуванням) або true
    alt Пошта увімкнена
        N->>E: send_change_notification()
        E->>C: get_smtp_config()
        C-->>E: Сервер SMTP, порт, користувач, пароль
        E->>S: connect() з TLS
        S-->>E: Підключено
        E->>S: sendmail(from, to, subject, html_body)
        S-->>E: Повідомлення прийнято
        E->>U: Лист доставлено до скриньки
        E-->>N: Результат відправки
    else Пошта не налаштована
        N->>C: get_error_channel()
        C-->>N: ID користувача Telegram адміна
        N->>TG: Надіслати алерт про помилку адміну
        TG-->>N: OK
    end
```

**Ключові методи** (`src/email_notifier.py`):
- `_validate_config()` — перевіряє наявність конфігурації SMTP
- `_format_change_email()` — HTML-тело листа з таблицею до/після
- `_format_error_email()` — тіло листа про помилку
- `send_change_notification()` — головна точка входу
- `send_combined_notification()` — об'єднує всі зміни в одному листі

---

## 7. Потік веб-інтерфейсу (Flask)

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
    participant T as Шаблони Jinja2

    U->>B: Відкрити http://localhost:5000
    B->>R: GET /
    R->>WA: Перевірка login_required
    alt Не автентифіковано
        R-->>B: Редирект /login
        B->>R: GET /login
        R->>T: Render login.html
        T-->>B: Форма входу з вибором мови
        U->>B: Відправити дані
        B->>R: POST /login
        R->>WA: verify_credentials()
        WA-->>R: Валідно / Невалідно
        R-->>B: Встановити cookie + редирект
    else Автентифіковано
        R->>REP: get_all_snapshots(filters)
        REP-->>R: Знімки
        R->>L: Переклади інтерфейсу
        L-->>R: Локалізовані рядки
        R->>T: Render index.html
        T-->>B: Список знімків

        U->>B: Натиснути «Порівняти» для 2 знімків
        B->>R: GET /compare?snap1=X&snap2=Y
        R->>REP: get_snapshot(id1), get_snapshot(id2)
        R->>D: detect_all_changes(old, new)
        D-->>R: Diff на рівні полів
        R->>L: Перекласти мітки
        L-->>R: Локалізовані мітки
        R->>T: Render compare.html
        T-->>B: Бік об бік з підсвіткою
    end
```

**Ключові маршрути** (`src/web/routes.py`): `index`, `login`, `logout`, `compare`, `build_comparison`, `delete`, `set_language`.

**Ключова автентифікація** (`src/web/auth.py`): `verify_credentials()`, `login_user()` / `logout_user()`, декоратор `login_required`.

---

## 8. Потік локалізації / i18n

```mermaid
flowchart TB
    subgraph LF[Файли мов]
        EN[en.json]
        PL[pl.json]
        RU[ru.json]
        UA[ua.json]
    end

    subgraph L10N[Рушій локалізації]
        LOAD[load_translations(lang)]
        T[t(key, default, lang)]
        SL[get_status_label(id)]
        QT[get_question_title(id)]
        QS[get_question_status(id)]
        FT[get_file_type(id)]
    end

    subgraph FALLBACK[Резервні карти]
        QTF[_QUESTION_TITLES_FALLBACK]
        QSF[_QUESTION_STATUSES_FALLBACK]
        SF[_STATUSES_FALLBACK]
    end

    LF -->|Читати при старті| LOAD
    LOAD -->|Мапити на| FALLBACK
    LOAD -->|Перезаписати через| Мапінги JSON
    SL --> LOAD
    QT --> LOAD
    QS --> LOAD
    T --> LOAD
    FALLBACK -->|Коли ключ JSON відсутній| LOAD
```

**Ключові методи** (`src/localization.py`):
- `load_translations(language)` — завантажує JSON-файл для коду мови
- `t(key, default, language)` — перекладає ключ локалізації
- `get_language()` / `set_language(lang)` — отримати/встановити поточну мову
- `get_status_label(status_id)` — мапить код статусу на перекладену мітку
- `get_question_title(title_id)` — мапить ID заголовка на перекладену мітку
- `get_question_status(status_id)` — мапить код статусу на мітку статусу
- `get_file_type(file_type_id)` — мапить ID типу файлу на мітку

**Резервні карти** (`src/models.py`):
- `_QUESTION_TITLES_FALLBACK` — 7 заголовків питань
- `_QUESTION_STATUSES_FALLBACK` — 2 статуси питань
- `_STATUSES_FALLBACK` — 22 коди статусів

---

## 9. Потік обробки помилок і відновлення

```mermaid
flowchart TD
    subgraph ERR[Джерела помилок]
        EA[Помилка автентифікації]
        EN[Мережа/Timeout]
        ET[Помилка Telegram]
        EC[Конфігурація пошти]
        ED[Валідація даних]
    end

    subgraph REC[Дії відновлення]
        RL[Залогувати помилку]
        RT[Сповіщення Telegram про помилку]
        RE[Резервна пошта]
        RS[Пропустити справу]
        RR[Повторити з backoff]
    end

    EA --> RL
    EN --> RL
    ET --> RT
    EC --> RE
    ED --> RS

    RL --> RR
    RT --> RE
    RE --> RL
    RS -->|Наступний акаунт/справа| CONT[Продовжити цикл]
    RR -->|Експоненційний backoff| EN
```

**Обробка помилок із бази коду:**

**З `src/orchestrator.py`:**
- `main()` оборачує все в try/except
- При помилці: `notifier.on_error(account_id, case_id, error, "SYSTEM_ERROR")`
- Сповіщення про помилку надсилається в Telegram

**З `src/notifier.py`:**
- `on_error()` — надсилає сповіщення про помилку в Telegram
- `_build_error_message()` — форматує деталі помилки
- `_send_error_fallback_email()` — резервна пошта для помилок

**З `src/session_manager.py`:**
- `get(url, max_retries=1)` — логіка повтору з параметром `max_retries`
- Автоматичне розв'язання челленджів Akamai через meta-refresh (~2с очікування)
- Логування помилок всюди

**З `src/detector.py`:**
- Кожен детектор повертає `List[Change]` (пустий список при відсутності змін)
- Винятків при нормальній детекції не виникає
- Коректна обробка `old_snapshot=None` (сценарій першого запуску)

---

## 10. Потік конфігурації

```mermaid
flowchart TD
    subgraph SRC[Джерела]
        ENV[Файл .env]
        CRED[credentials.json]
        WEB[веб-облікові дані]
    end

    subgraph CFG[Модуль конфігурації]
        LE[load_env(path)]
        LC[load_credentials(path)]
        GC[get_config(key, default)]
        GA[get_accounts()]
        GS[get_smtp_config()]
        GE[get_email_enabled()]
        GJ[get_json_logging_enabled()]
        GT[get_authorized_telegram_users()]
    end

    subgraph CONSUMERS[Споживачі]
        ORCH[orchestrator.py]
        AUTH[auth.py]
        SCR[scraper.py]
        NOT[notifier.py]
        EM[email_notifier.py]
        STO[storage.py]
        WEBAPP[web/routes.py]
    end

    ENV --> LE
    CRED --> LC
    LE --> CFG
    LC --> CFG
    CFG --> CONSUMERS
```

**Ключові методи** (`src/config.py`):
- `load_env(path)` — завантажує файл .env, повертає успіх
- `load_credentials(path)` — завантажує credentials.json, повертає словник
- `get_base_path()` — отримує базовий шлях проєкту
- `get_config(key, default)` — загальний пошук конфігурації
- `get_accounts()` — перелічує імена налаштованих акаунтів
- `get_smtp_config()` — повертає словник SMTP
- `get_email_enabled()` / `get_json_logging_enabled()` — логічні значення
- `get_authorized_telegram_users()` — список авторизованих ID користувачів

**Ключі .env** (з README.md):
```
LANGUAGE=en                # Мова веб-інтерфейсу
NOTIFICATION_LANGUAGE=en   # Мова сповіщень Telegram/пошта
INPOL_BASE_URL=https://inpol.mazowieckie.pl
JSON_LOGGING_ENABLED=false
EMAIL_ENABLED=false
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your-username
SMTP_PASSWORD=your-password
EMAIL_FROM=noreply@example.com
EMAIL_TO=your-email@example.com
```

**Формат credentials.json** (з README.md):
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

---

## 11. Потік інтеграції з Планувальником задач Windows

```mermaid
flowchart TB
    subgraph TS[Планувальник задач]
        T1[Задача 08:00]
        T2[Задача 12:30]
        T3[Задача 18:00]
    end

    subgraph APP[Застосунок]
        CMD[run_check.cmd]
        VENV[.venv\Scripts\python.exe]
        ORCH[python -m src.orchestrator]
    end

    T1 --> CMD
    T2 --> CMD
    T3 --> CMD
    CMD --> VENV
    VENV --> ORCH
```

**Ключові команди** (з README.md та `run_check.cmd`):
- Повна команда PowerShell для створення всіх 3 задач:
  ```powershell
  $SCRIPT = Join-Path (Get-Location) "run_check.cmd"
  $TASK_NAME = "Inpol Monitor"

  schtasks /Create /TN $TASK_NAME /TR $SCRIPT /SC DAILY /ST 08:00 /F /RL HIGHEST
  schtasks /Create /TN "$TASK_NAME\Noon Check" /TR $SCRIPT /SC DAILY /ST 12:30 /F /RL HIGHEST
  schtasks /Create /TN "$TASK_NAME\Evening Check" /TR $SCRIPT /SC DAILY /ST 18:00 /F /RL HIGHEST
  ```
- Окремі запити та запуски задач:
  ```cmd
  schtasks /Query /TN "Inpol Monitor"
  schtasks /Run /TN "Inpol Monitor"
  ```
- Зміст `run_check.cmd`: `@cd %~dp0 & .venv\Scripts\python -m src.orchestrator`

---

*Ґрунтується на реальному коді: `src/orchestrator.py`, `src/auth.py`, `src/session_manager.py`, `src/scraper.py`, `src/storage.py`, `src/detector.py`, `src/notifier.py`, `src/email_notifier.py`, `src/localization.py`, `src/models.py`, `src/config.py`, `src/web/routes.py`, `src/web/auth.py`.*

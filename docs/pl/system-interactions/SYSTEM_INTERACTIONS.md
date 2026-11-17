# Inpol Monitor — Diagramy interakcji systemu

Szczegółowe diagramy interakcji oparte na rzeczywistej bazie kodu. Wszystkie przepływy pochodzą z implementacji w `src/`, `.planning/` i architekturze aplikacji.

Dostępne tłumaczenia: [English](../../en/system-interactions/SYSTEM_INTERACTIONS.md) | [Polski](SYSTEM_INTERACTIONS.md) | [Русский](../../ru/system-interactions/SYSTEM_INTERACTIONS.md) | [Українська](../../ua/system-interactions/SYSTEM_INTERACTIONS.md)

---

## 1. Przepływ uwierzytelniania (sekwencyjne uwierzytelnianie z CSRF)

```mermaid
sequenceDiagram
    autonumber
    participant O as Orchestrator
    participant A as auth.py
    participant SM as SessionManager
    participant P as Portal Inpol

    O->>A: authenticate_account(name, creds)
    A->>SM: SessionManager(base_url)
    SM->>P: GET /login page
    P-->>SM: HTML z tokenem CSRF
    SM->>SM: Zapisz token CSRF w sesji
    SM->>P: POST /login (email, password, CSRF)
    P-->>SM: Ciasteczka sesji

    alt Wykryto wyzwanie JS Akamai
        SM->>P: meta-refresh czekaj (~2s)
        P-->>SM: Strona wyzwania
        SM->>SM: Rozwiąż wyzwanie
        SM->>P: Ponów POST danych
        P-->>SM: Ciasteczka sesji
    else Bezpośrednie logowanie
        SM-->>A: Sesja uwierzytelniona
    end

    A-->>O: Obiekt sesji (logged_in=True)
```

**Kluczowe metody** (`src/auth.py`, `src/session_manager.py`):
- `authenticate_account(name, creds)` — punkt wejścia sekwencyjnego uwierzytelniania
- `run_sequential_auth()` — przetwarza wszystkie skonfigurowane konta
- `login(email, password)` — wykonuje uwierzytelnianie
- `_has_akamai_challenge(html)` — wykrywa ochronę Akamai
- `_solve_challenge(html, url)` — rozwiązywacz meta-refresh (~2s czekania na wywołanie API)

---

## 2. Przepływ ekstrakcji danych

```mermaid
sequenceDiagram
    autonumber
    participant O as Orchestrator
    participant SC as Scraper
    participant SM as SessionManager
    participant P as Portal Inpol
    participant L as localization.py

    O->>SC: fetch_case_data(case_id)
    SC->>SM: GET /api/case/{id}
    SM->>P: Żądanie HTTP z sesją
    P-->>SM: Odpowiedź JSON
    SM-->>SC: Dane odpowiedzi

    SC->>SC: Parsuj CaseData (Pydantic)
    SC->>L: get_status_label(status_id)
    L-->>SC: Zlokalizowana etykieta statusu
    SC->>L: get_question_title(title_id)
    L-->>SC: Zlokalizowany tytuł pytania

    SC-->>O: CaseData(person_first, person_last, case_number, status_raw, status_label, attachments, questions, timeline, related_docs, timeline_events)
```

**Kluczowe metody** (`src/scraper.py`):
- `fetch_case_data(case_id)` — wyodrębnia model CaseData Pydantic
- `fetch_questions(case_id)` — wyodrębnia dane pytań ze wszystkimi 7 polami
- `fetch_attachments(case_id)` — wyodrębnia załączniki dokumentów
- `_resolve_status_label(code)` — mapuje kody statusów na etykiety czytelne dla człowieka
- `_resolve_question_title(id)` — mapuje tytuły pytań przez lokalizację
- `fetch_all_for_case(case_id)` — koordynuje pełne pobranie danych sprawy

---

## 3. Przepływ przechowywania (tylko INSERT, niezmienne)

```mermaid
sequenceDiagram
    autonumber
    participant O as Orchestrator
    participant R as SnapshotRepository
    participant DB as SQLite

    O->>R: get_latest_snapshot(case_id)
    R->>DB: SELECT * FROM snapshots WHERE case_id=? ORDER BY timestamp DESC LIMIT 1
    DB-->>R: Poprzedni zrzut (lub None)
    R-->>O: old_snapshot

    O->>R: save_snapshot(new_snapshot)
    R->>DB: INSERT INTO snapshots (account_id, case_id, endpoint_type, raw_json, parsed_data, timestamp)
    DB-->>R: Id wiersza
    R-->>O: Sukces

    Note over R,DB: Zrzuty nigdy nie są aktualizowane ani usuwane
    Note over R,DB: Pełne przechowywanie historii (STORE-02)
```

**Kluczowe metody** (`src/storage.py`):
- `save_snapshot(snapshot)` — tylko INSERT, nigdy nie aktualizuje/usuwa
- `get_latest_snapshot(case_id)` — najnowszy zrzut dla sprawy
- `get_previous_snapshot(case_id)` — drugi najnowszy
- `get_all_snapshots()` — pełne historyczne rekordy
- `get_snapshots_by_account(account_id)` — filtruj po koncie
- `get_distinct_case_ids()` — globalnie unikalne identyfikatory spraw (STORE-03)
- `get_snapshot_by_id(id)` — pobieranie pojedynczego zrzutu

---

## 4. Przepływ wykrywania zmian (wzorzec strategii)

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
        DA->>DA: Zbuduj new_snapshot z danych scrapera

        par Uruchom strategie detektorów
            DA->>SD: detect(old, new)
            SD-->>DA: [Change] lub []
            DA->>DD: detect(old, new)
            DD-->>DA: [Change] lub []
            DA->>DT: detect(old, new)
            DT-->>DA: [Change] lub []
            DA->>QD: detect(old, new)
            QD->>L: get_question_title/status
            L-->>QD: Zlokalizowane etykiety
            QD-->>DA: [Change] lub []
            DA->>TD: detect(old, new)
            TD-->>DA: [Change] lub []
        end

        DA->>N: queue_notification(case_id, all_changes)
        DA->>R: save_snapshot(new_snapshot)
    end

    DA-->>O: Dict[account, List[Change]]
```

**7 typów zmian** (`src/models.py` `ChangeType`):
- `STATUS` — zmiana kodu statusu
- `NEW_DOCUMENT` — dodano nowy dokument
- `REMOVED_DOCUMENT` — usunięto dokument
- `DECISION_DATE_CHANGE` — zmieniono datę decyzji
- `SUBMIT_DATE_CHANGE` — zmieniono datę złożenia
- `UPDATED_AT_CHANGE` — zmieniono znacznik czasu updated_at
- `TIMELINE_EVENT_ADDED` — nowe zdarzenie na osi czasu

Oraz typy poziomu pytań: `QUESTION_ASKED`, `QUESTION_ANSWERED`, `QUESTION_COUNT_CHANGE`, `NEW_QUESTION_DETAIL`.

**Kluczowe metody** (`src/detector.py`):
- `BaseDetector.detect(old, new)` — abstrakcyjny interfejs strategii
- Każdy detektor zwraca `List[Change]` (pusta lista, gdy brak zmian)
- Łagodne obsługiwanie `old_snapshot=None` (pierwsze uruchomienie)

---

## 5. Przepływ powiadomień Telegram (najpierw zbierz, potem wyślij)

```mermaid
sequenceDiagram
    autonumber
    participant D as Detector
    participant N as TelegramNotifier
    participant C as Config
    participant TG as Telegram API
    participant E as EmailNotifier

    D->>N: queue_notification(case_id, changes)
    N->>N: Zapisz wewnętrznej kolejce

    loop Wszystkie połączone powiadomienia
        N->>N: Zbuduj wiadomość z ID sprawy, zmianami, zlokalizowanymi etykietami
    end

    N->>N: send_all_notifications()
    N->>C: get_notification_language()
    C-->>N: Kod języka (en/pl/ru/ua)
    N->>TG: send_message(chat_id, text, parse_mode='Markdown')

    alt Telegram OK
        TG-->>N: 200 OK
    else Telegram nie działa
        N->>E: _send_fallback_email()
        E->>C: get_smtp_config()
        C-->>E: Serwer SMTP, port, użytkownik, hasło
        E->>SMTP: connect() z TLS
        SMTP-->>E: Połączono
        E->>SMTP: sendmail(from, to, subject, html_body)
        SMTP-->>E: Wiadomość zaakceptowana
    end
```

**Kluczowe metody** (`src/notifier.py`):
- `send_all_notifications()` — iteruje po wszystkich powiadomieniach w kolejce
- `_build_change_message()` — bogata wiadomość Markdown ze szczegółami sprawy
- `_build_single_message()` — wiadomość pojedynczej sprawy
- `_build_error_message()` — format powiadomienia o błędzie
- `_send_fallback_email()` — uruchamia zapasową pocztę
- `_tn()` — pomocnik lokalizacji dla kluczy powiadomień
- `_resolve_chat_id(user_id)` — mapuje identyfikatory użytkowników na czaty Telegram

---

## 6. Przepływ zapasowej poczty

```mermaid
sequenceDiagram
    autonumber
    participant N as TelegramNotifier
    participant E as EmailNotifier
    participant C as Config
    participant S as Serwer SMTP
    participant U as Odbiorca

    N->>C: get_email_enabled()
    C-->>N: false (domyślnie) lub true
    alt Poczta włączona
        N->>E: send_change_notification()
        E->>C: get_smtp_config()
        C-->>E: Serwer SMTP, port, użytkownik, hasło
        E->>S: connect() z TLS
        S-->>E: Połączono
        E->>S: sendmail(from, to, subject, html_body)
        S-->>E: Wiadomość zaakceptowana
        E->>U: Wiadomość dostarczona do skrzynki
        E-->>N: Wynik wysyłki
    else Poczta nieskonfigurowana
        N->>C: get_error_channel()
        C-->>N: Identyfikator użytkownika Telegram admina
        N->>TG: Wyślij alert o błędzie do admina
        TG-->>N: OK
    end
```

**Kluczowe metody** (`src/email_notifier.py`):
- `_validate_config()` — sprawdza czy konfiguracja SMTP istnieje
- `_format_change_email()` — treść HTML z tabelą przed/po
- `_format_error_email()` — treść powiadomienia o błędzie
- `send_change_notification()` — główny punkt wejścia
- `send_combined_notification()` — łączy wszystkie zmiany w jednym mailu

---

## 7. Przepływ interfejsu webowego (Flask)

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
        R-->>B: Przekieruj /login
        B->>R: GET /login
        R->>T: Renderuj login.html
        T-->>B: Formularz logowania z selektorem języka
        U->>B: Wyślij dane
        B->>R: POST /login
        R->>WA: verify_credentials()
        WA-->>R: Poprawne / Niepoprawne
        R-->>B: Ustaw ciasteczko sesji + przekieruj
    else Uwierzytelniony
        R->>REP: get_all_snapshots(filters)
        REP-->>R: Zrzuty
        R->>L: Tłumaczenia interfejsu
        L-->>R: Zlokalizowane ciągi
        R->>T: Renderuj index.html
        T-->>B: Lista zrzutów

        U->>B: Kliknij "Porównaj" dla 2 zrzutów
        B->>R: GET /compare?snap1=X&snap2=Y
        R->>REP: get_snapshot(id1), get_snapshot(id2)
        R->>D: detect_all_changes(old, new)
        D-->>R: Diff na poziomie pól
        R->>L: Tłumacz etykiety
        L-->>R: Zlokalizowane etykiety
        R->>T: Renderuj compare.html
        T-->>B: Obok siebie z podświetleniem
    end
```

**Kluczowe trasy** (`src/web/routes.py`): `index`, `login`, `logout`, `compare`, `build_comparison`, `delete`, `set_language`.

**Kluczowa autentykacja** (`src/web/auth.py`): `verify_credentials()`, `login_user()` / `logout_user()`, dekorator `login_required`.

---

## 8. Przepływ lokalizacji / i18n

```mermaid
flowchart TB
    subgraph LF[Pliki językowe]
        EN[en.json]
        PL[pl.json]
        RU[ru.json]
        UA[ua.json]
    end

    subgraph L10N[Silnik lokalizacji]
        LOAD[load_translations(lang)]
        T[t(key, default, lang)]
        SL[get_status_label(id)]
        QT[get_question_title(id)]
        QS[get_question_status(id)]
        FT[get_file_type(id)]
    end

    subgraph FALLBACK[Mapy zapasowe]
        QTF[_QUESTION_TITLES_FALLBACK]
        QSF[_QUESTION_STATUSES_FALLBACK]
        SF[_STATUSES_FALLBACK]
    end

    LF -->|Czytaj przy starcie| LOAD
    LOAD -->|Mapuj na| FALLBACK
    LOAD -->|Nadpisz za pomocą| Mapowania JSON
    SL --> LOAD
    QT --> LOAD
    QS --> LOAD
    T --> LOAD
    FALLBACK -->|Gdy klucz JSON brakny| LOAD
```

**Kluczowe metody** (`src/localization.py`):
- `load_translations(language)` — ładuje plik JSON dla kodu języka
- `t(key, default, language)` — tłumaczy klucz lokalizacji
- `get_language()` / `set_language(lang)` — pobranie/ustawienie bieżącego języka
- `get_status_label(status_id)` — mapuje kod statusu na przetłumaczoną etykietę
- `get_question_title(title_id)` — mapuje identyfikator tytułu na przetłumaczoną etykietę
- `get_question_status(status_id)` — mapuje kod statusu na etykietę statusu
- `get_file_type(file_type_id)` — mapuje identyfikator typu pliku na etykietę

**Mapy zapasowe** (`src/models.py`):
- `_QUESTION_TITLES_FALLBACK` — 7 tytułów pytań
- `_QUESTION_STATUSES_FALLBACK` — 2 statusy pytań
- `_STATUSES_FALLBACK` — 22 kody statusów

---

## 9. Przepływ obsługi błędów i odzyskiwania

```mermaid
flowchart TD
    subgraph ERR[Źródła błędów]
        EA[Błąd uwierzytelniania]
        EN[Sieć/Timeout]
        ET[Błąd Telegram]
        EC[Konfiguracja poczty]
        ED[Walidacja danych]
    end

    subgraph REC[Akcje odzyskiwania]
        RL[Zaloguj błąd]
        RT[Powiadomienie Telegram o błędzie]
        RE[Zapasowa poczta]
        RS[Pomiń sprawę]
        RR[Ponów z backoff]
    end

    EA --> RL
    EN --> RL
    ET --> RT
    EC --> RE
    ED --> RS

    RL --> RR
    RT --> RE
    RE --> RL
    RS -->|Następne konto/sprawa| CONT[Kontynuuj cykl]
    RR -->|Backoff wykładniczy| EN
```

**Obsługa błędów z bazy kodu:**

**Z `src/orchestrator.py`:**
- `main()` owija wszystko w try/except
- W razie błędu: `notifier.on_error(account_id, case_id, error, "SYSTEM_ERROR")`
- Powiadomienie o błędzie wysyłane do Telegrama

**Z `src/notifier.py`:**
- `on_error()` — wysyła powiadomienie o błędzie do Telegrama
- `_build_error_message()` — formatuje szczegóły błędu
- `_send_error_fallback_email()` — zapasowa poczta dla błędów

**Z `src/session_manager.py`:**
- `get(url, max_retries=1)` — logika ponawiania z parametrem `max_retries`
- Automatyczne rozwiązywanie wyzwań Akamai przez meta-refresh (~2s oczekiwania)
- Rejestrowanie błędów w całej aplikacji

**Z `src/detector.py`:**
- Każdy detektor zwraca `List[Change]` (pusta lista, gdy brak zmian)
- Brak wyjątków podczas normalnej detekcji
- Łagodne obsługiwanie `old_snapshot=None` (scenariusz pierwszego uruchomienia)

---

## 10. Przepływ konfiguracji

```mermaid
flowchart TD
    subgraph SRC[Źródła]
        ENV[Plik .env]
        CRED[credentials.json]
        WEB[dane uwierzytelniające web]
    end

    subgraph CFG[Moduł konfiguracji]
        LE[load_env(path)]
        LC[load_credentials(path)]
        GC[get_config(key, default)]
        GA[get_accounts()]
        GS[get_smtp_config()]
        GE[get_email_enabled()]
        GJ[get_json_logging_enabled()]
        GT[get_authorized_telegram_users()]
    end

    subgraph CONSUMERS[Konsumenci]
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

**Kluczowe metody** (`src/config.py`):
- `load_env(path)` — ładuje plik .env, zwraca sukces
- `load_credentials(path)` — ładuje credentials.json, zwraca słownik
- `get_base_path()` — pobiera bazową ścieżkę projektu
- `get_config(key, default)` — ogólne wyszukiwanie konfiguracji
- `get_accounts()` — listuje nazwy skonfigurowanych kont
- `get_smtp_config()` — zwraca słownik SMTP
- `get_email_enabled()` / `get_json_logging_enabled()` — wartości logiczne
- `get_authorized_telegram_users()` — lista autoryzowanych identyfikatorów użytkowników

**Klucze .env** (z README.md):
```
LANGUAGE=en                # Język interfejsu web
NOTIFICATION_LANGUAGE=en   # Język powiadomień Telegram/poczta
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

**Format credentials.json** (z README.md):
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

## 11. Przepływ integracji z Harmanem zadań Windows

```mermaid
flowchart TB
    subgraph TS[Harman zadań]
        T1[Zadanie 08:00]
        T2[Zadanie 12:30]
        T3[Zadanie 18:00]
    end

    subgraph APP[Aplikacja]
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

**Kluczowe komendy** (z README.md i `run_check.cmd`):
- Pełne polecenie PowerShell do utworzenia wszystkich 3 zadań:
  ```powershell
  $SCRIPT = Join-Path (Get-Location) "run_check.cmd"
  $TASK_NAME = "Inpol Monitor"

  schtasks /Create /TN $TASK_NAME /TR $SCRIPT /SC DAILY /ST 08:00 /F /RL HIGHEST
  schtasks /Create /TN "$TASK_NAME\Noon Check" /TR $SCRIPT /SC DAILY /ST 12:30 /F /RL HIGHEST
  schtasks /Create /TN "$TASK_NAME\Evening Check" /TR $SCRIPT /SC DAILY /ST 18:00 /F /RL HIGHEST
  ```
- Pojedyncze zapytania i uruchomienia zadań:
  ```cmd
  schtasks /Query /TN "Inpol Monitor"
  schtasks /Run /TN "Inpol Monitor"
  ```
- Zawartość `run_check.cmd`: `@cd %~dp0 & .venv\Scripts\python -m src.orchestrator`

---

*Oparte na rzeczywistym kodzie: `src/orchestrator.py`, `src/auth.py`, `src/session_manager.py`, `src/scraper.py`, `src/storage.py`, `src/detector.py`, `src/notifier.py`, `src/email_notifier.py`, `src/localization.py`, `src/models.py`, `src/config.py`, `src/web/routes.py`, `src/web/auth.py`.*

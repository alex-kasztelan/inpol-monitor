# Inpol Monitor

Zautomatyzowany system monitoringu polskiego portalu rządowego (inpol.mazowieckie.pl)

**Języki:** [English](README.md) | [Русский](README.ru.md) | [Українська](README.ua.md) | [Polski](README.pl.md)

## Dokumentacja

- **[Diagramy architektury](docs/pl/architecture/ARCHITECTURE.md)** — diagram komponentów, sekwencja cyklu sprawdzania, szczegóły wykrywania zmian, przepływ interfejsu webowego, przepływ danych, architektura wdrożenia, wzorce architektoniczne
- **[Interakcje systemu](docs/pl/system-interactions/SYSTEM_INTERACTIONS.md)** — uwierzytelnianie, ekstrakcja danych, przechowywanie, wykrywanie zmian, powiadomienia, interfejs webowy, lokalizacja, obsługa błędów, konfiguracja, przepływy Harmonogramu zadań
- **[Indeks dokumentacji](docs/README.md)** — cała dokumentacja w 4 językach (EN/PL/RU/UA)

## Przegląd

Inpol Monitor śledzi sprawy imigracyjne na wielu kontach, aby wykrywać wszelkie zmiany statusów, dokumentów, pytań lub terminów — dzięki czemu użytkownik nigdy nie przegapi ważnej aktualizacji.

## Co robi system

- **Uwierzytelnianie**: Logowanie do portalu Inpol z wieloma kontami (sekwencyjne uwierzytelnianie z obsługą CSRF)
- **Pobieranie danych**: Pobieranie danych dla wszystkich skonfigurowanych spraw
- **Przechowywanie**: Zapisywanie wszystkich historycznych migawek do bazy danych SQLite z niezmiennością (tylko INSERT)
- **Wykrywanie zmian**: Porównywanie bieżącego stanu z poprzednią migawką, wykrywanie 7 typów zmian:
  - Zmiany statusu
  - Nowe/usunięte dokumenty
  - Zmiany dat (terminy decyzji, daty złożenia, updated_at)
  - Zmiany pytań (w tym zmiany na poziomie pól)
  - Zdarzenia osi czasu
- **Powiadomienia**: Wysyłanie szczegółowych raportów o zmianach na Telegram (obsługa wielu użytkowników) z zapasową wysyłką e-mail, gdy Telegram jest niedostępny
- **Harmonogram**: Automatyczne sprawdzenia o 8:00, 12:30 i 18:00 czasu polskiego (CET/CEST) przez Harmonogram zadań Windows
- **Interfejs webowy**: Aplikacja Flask do przeglądania i porównywania historycznych migawek spraw z podświetlaniem zmian na poziomie pól

## Rozpoczęcie pracy

### Wymagania wstępne

- Python 3.11+
- Windows 11 (dla Harmonogramu zadań) lub dowolny system operacyjny do programowania

### Szybka instalacja

1. **Klonowanie i konfiguracja**
   ```bash
   git clone https://github.com/your-repo/inpol-monitor.git
   cd inpol-monitor
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # lub ./venv/bin/activate  # Linux/macOS
   pip install -r requirements.txt
   ```

2. **Konfiguracja środowiska**
   ```bash
   cp .env.example .env
   # Edytuj .env ze swoimi ustawieniami (język, logowanie, e-mail)
   ```

3. **Załaduj dane uwierzytelniające**
   ```bash
   cp credentials.json.example credentials.json
   # Edytuj credentials.json swoimi rzeczywistymi danymi uwierzytelniającymi
   ```

4. **Uruchom aplikację**
   ```bash
   # Sprawdzenie uwierzytelniania
   python check.py

   # Pełny cykl monitoringu
   python -m src.orchestrator
   ```

### Konfiguracja

#### Konfiguracja .env
```
# Ustawienia języka
LANGUAGE=en         # Język interfejsu webowego (en, pl, ru, ua)
NOTIFICATION_LANGUAGE=en  # Język powiadomień Telegram/e-mail

# Portal
INPOL_BASE_URL=https://inpol.mazowieckie.pl

# Logowanie odpowiedzi JSON (do analizy API)
JSON_LOGGING_ENABLED=false

# Powiadomienia e-mail (kanał zapasowy)
EMAIL_ENABLED=false
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your-username
SMTP_PASSWORD=your-password
EMAIL_FROM=noreply@example.com
EMAIL_TO=your-email@example.com
```

#### Konfiguracja credentials.json
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

## Użycie

### Ręczne sprawdzenia
```cmd
# Szybkie sprawdzenie uwierzytelniania
python check.py

# Pełny cykl monitoringu (z logowaniem)
python -m src.orchestrator
```

### Automatyczne sprawdzenia (Harmonogram zadań Windows)

Otwórz PowerShell **jako administrator** z katalogu projektu:

```powershell
$SCRIPT = Join-Path (Get-Location) "run_check.cmd"
$TASK_NAME = "Inpol Monitor"

schtasks /Create /TN $TASK_NAME /TR $SCRIPT /SC DAILY /ST 08:00 /F /RL HIGHEST
schtasks /Create /TN "$TASK_NAME\Noon Check" /TR $SCRIPT /SC DAILY /ST 12:30 /F /RL HIGHEST
schtasks /Create /TN "$TASK_NAME\Evening Check" /TR $SCRIPT /SC DAILY /ST 18:00 /F /RL HIGHEST
```

Weryfikacja i uruchomienie ręczne:

```cmd
schtasks /Query /TN "Inpol Monitor"
schtasks /Run /TN "Inpol Monitor"
```

Pełny przewodnik konfiguracji, zarządzania i usuwania znajdziesz w [SCHEDULING.md](SCHEDULING.md).

### Interfejs webowy

1. **Uruchom aplikację Flask** z katalogu głównego projektu:
   ```bash
   python -m src.web.__main__
   ```

2. **Otwórz** `http://localhost:5000` w przeglądarce i zaloguj się danymi interfejsu webowego.

3. **Funkcje**:
   - Logowanie danymi uwierzytelniającymi
   - Przeglądanie wszystkich migawek z filtrami (sprawa, konto, endpoint, zakres dat)
   - Porównywanie dwóch migawek obok siebie
   - Wyświetlanie wszystkich 7 pól pytania z podświetlaniem zmian na poziomie pól
   - Obsługa tłumaczeń (EN, PL, UA, RU)

## Struktura projektu

```
.
├── .planning/              # Artefakty planowania GSD
│   ├── PROJECT.md        # Wymagania i ograniczenia
│   ├── ROADMAP.md        # Podział na fazy
│   ├── STATE.md          # Bieżący stan
│   └── phases/           # Katalogi faz
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
├── src/                   # Główna aplikacja
│   ├── __init__.py
│   ├── auth.py            # Logika uwierzytelniania
│   ├── config.py          # Ładowanie konfiguracji
│   ├── orchestrator.py    # Główna koordynacja
│   ├── scraper.py         # Pobieranie danych
│   ├── detector.py        # Wykrywanie zmian
│   ├── notifier.py        # Powiadomienia Telegram
│   ├── email_notifier.py  # Zapasowa wysyłka e-mail
│   ├── session_manager.py # Zarządzanie sesjami
│   ├── storage.py         # Repozytorium SQLite
│   └── models.py          # Modele danych Pydantic
├── src/web/              # Aplikacja webowa
│   ├── __main__.py
│   ├── auth.py           # Uwierzytelnianie webowe
│   ├── routes.py         # Trasy Flask
│   └── templates/        # Szablony HTML
├── tests/                # Zestaw testów
│   ├── conftest.py       # Konfiguracja pytest
│   ├── test_*.py         # Testy jednostkowe
│   └── test_comparison.py # Testy porównywania na poziomie pól
├── data/                 # Bazy danych
│   ├── snapshots.db      # Produkcyjna baza danych
│   └── test_snapshots.db # Testowa baza danych
├── logs/                 # Logi aplikacji
├── requirements.txt      # Zależności Pythona
├── check.py             # Sprawdzenie przepływu uwierzytelniania
├── run_check.cmd        # Skrypt dla Harmonogramu zadań Windows
├── *.json               # Pliki lokalizacji
└── *.md                 # Dokumentacja
```

## Funkcje

### Główne wymagania
- [x] **AUTH-01**: Uwierzytelnianie z wieloma kontami przez sekwencyjny przepływ z obsługą CSRF
- [x] **AUTH-02**: Bezpieczne przechowywanie danych uwierzytelniających przez .env i credentials.json
- [x] **DATA-01**: Pobieranie danych dla wszystkich skonfigurowanych spraw
- [x] **DATA-02**: Pobieranie statusów, dat, dokumentów, terminów z obsługą i18n
- [x] **STORE-01**: Zapisywanie migawek w SQLite z znaczkiem czasu
- [x] **STORE-02**: Niezmienność (tylko INSERT, pełne zachowanie historii)
- [x] **STORE-03**: Zapytania migawek po case_id (globalnie unikalne)
- [x] **DETECT-01**: Porównywanie bieżącego stanu z poprzednią migawką
- [x] **DETECT-02**: Wykrywanie 7 typów zmian (status, dokumenty, daty, pytania)
- [x] **NOTIFY-01**: Wysyłanie szczegółowych raportów o zmianach na Telegram
- [x] **NOTIFY-02**: Dołączanie ID sprawy i konkretnych zmian do powiadomień
- [x] **SCHED-01**: Uruchamianie o 8:00, 12:30, 18:00 czasu polskiego
- [x] **SCHED-02**: Integracja z Harmonogramem zadań Windows
- [x] **SCHED-03**: Ręczne uruchamianie przez CLI
- [x] **ERROR-01**: Wysyłanie powiadomień o błędach przy awariach

### Faza 12: Rozszerzone porównywanie pytań (zakończona)
- **Porównywanie na poziomie pól**: Wykrywanie zmian poszczególnych pól (title, status, status_label, body, sentTime, answer, responseTime) wewnątrz pytań
- **Wyświetlanie 7 pól pytania**: Pokazywanie wszystkich pól pytania w widoku porównania
- **Lokalizacja**: Przetłumaczone status_label przez `Cases.Question.Statuses`, title przez `Cases.Question.Titles`
- **Podświetlanie zmian**: Wizualne wyróżnienie zmienionych pól w interfejsie

### Stos technologii

| Warstwa | Technologia |
|-------|------------|
| **Backend** | Python 3.11, requests, beautifulsoup4, lxml |
| **Modele danych** | Pydantic v2, SQLite (tylko INSERT, niezmienność) |
| **Interfejs webowy** | Flask 3.0+, Bootstrap 5, HTMX |
| **Powiadomienia** | aiogram 3.x (Telegram), SMTP (E-mail) |
| **Lokalizacja** | JSON-based i18n (EN/PL/UA/RU) |
| **Wdrożenie** | Harmonogram zadań Windows, Python venv |
| **Testowanie** | pytest, pokrycie testami >80% |

### Architektura

1. **Warstwa uwierzytelniania**: Sekwencyjne uwierzytelnianie kont z obsługą CSRF i zarządzaniem sesjami
2. **Warstwa pobierania**: Parsowanie HTML z beautifulsoup4, przetwarzanie odpowiedzi JSON API
3. **Warstwa przechowywania**: Repozytorium SQLite z zapisem migawek INSERT-only
4. **Warstwa wykrywania**: Strategy pattern dla 7 typów zmian, porównywanie na poziomie pól pytania
5. **Warstwa powiadomień**: Batch-then-notify z Telegramem (obsługa wielu użytkowników) i zapasowym e-mailem
6. **Warstwa webowa**: Aplikacja Flask z uwierzytelnianiem, filtrowaniem migawek, widokiem porównania

> 📊 **Wizualna architektura**: Zobacz [Diagramy architektury](docs/pl/architecture/ARCHITECTURE.md) i [Interakcje systemu](docs/pl/system-interactions/SYSTEM_INTERACTIONS.md) dla pełnych diagramów komponentów i sekwencji.

### Kontrola jakości

- **Testy**: 162 testy przechodzą (pokrycie 83%)
- **Przegląd kodu**: Przegląd standardowej głębokości obejmujący thread- przebieg detector → notifier → email_notifier
- **Poprawka wstrzykiwania HTML**: Wszystkie wartości kontrolowane przez użytkownika w e-mailach są escapowane przez `html.escape()`
- **Lokalizacja**: Obsługa 7 kluczy językowych (en, pl, ru, ua)
- **Walidacja**: Pliki złotych, testy scenariuszy awarii
- **Dokumentacja**: README, SCHEDULING.md, PROJECT.md

## Znane problemy

- **Ochrona przed botami Akamai**: Automatyczne rozwiązywanie JS-challenge przez meta-refresh (~2s na wywołanie API)
- **Istniejący błąd testu**: `tests/planner/test_noti_format.py` (NameError: `status_id` niezdefiniowany) — niezwiązane z bieżącymi zmianami

## Zabezpieczenia

- **Dane uwierzytelniające**: Przechowywane w zaszyfrowanym credentials.json (użytkownicy muszą chronić swoje pliki)
- **Wstrzykiwanie HTML**: Poprawione w powiadomieniach e-mail (wszystkie wartości kontrolowane przez użytkownika są escapowane)
- **HTTPS**: Używane HTTPS dla wszystkich połączeń z portalem
- **Bezpieczeństwo sesji**: Tokeny CSRF, bezpieczne zarządzanie sesjami
- **Dostęp do plików**: Uprawnienia pliku bazy danych SQLite (odczyt/zapis tylko dla użytkownika aplikacji)

## Przyszłe ulepszenia

### Faza M2 (backlog)
- Przypomnienia o terminach spraw
- Miesięczne raporty
- Funkcja eksportu
- Ulepszone odzyskiwanie po błędach
- Aplikacja mobilna
- Obsługa dodatkowych języków

### Możliwe ulepszenia
- Przejście ze scrapowania HTML na oficjalne API, jeśli pojawi się
- Migracja bazy danych na PostgreSQL dla skalowalności
- Optymalizacja wydajności dla dużej liczby spraw
- Powiadomienia w czasie rzeczywistym (WebSocket)

## Rozwiązywanie problemów

### Częste problemy

**Harmonogram zadań nie działa**
```cmd
# Sprawdź status
schtasks /Query /TN "Inpol Monitor"

# Uruchom ponownie w razie potrzeby
schtasks /Run /TN "Inpol Monitor"
```

**Błędy uwierzytelniania**
```bash
# Włącz szczegółowe logowanie
python -m src.orchestrator  # lub python -m src.web.__main__

# Sprawdź, czy credentials.json istnieje i ma poprawny format
```

**Problemy z logowaniem do interfejsu webowego**
```
# Upewnij się, że LANGUAGE w .env odpowiada Twojemu wyborowi
# Sprawdź, czy migawki istnieją w bazie danych
# Upewnij się, że credentials.json jest wypełniony
```

**Problemy z logowaniem JSON**
```bash
# Włącz w .env
JSON_LOGGING_ENABLED=true

# Sprawdź wynik w logs/json_responses.log
```

### Uzyskiwanie pomocy

1. **Przeczytaj SCHEDULING.md** dotyczące konfiguracji Harmonogramu zadań
2. **Sprawdź .env.example** w celu uzyskania przykładów zmiennych środowiskowych
3. **Przejrzyj credentials.json.example** w celu poznania formatu danych uwierzytelniających
4. **Sprawdź katalog logs/** w celu diagnostyki działania
5. **Uruchom testy**: `pytest tests/` dla zestawu testów

## Wkład w projekt

### Przepływ pracy programisty

1. **Faza planowania**: Omówienie → Badanie → Zdefiniowanie wymagań → Utworzenie mapy drogowej → Planowanie fazy
2. **Implementacja**: Wykonywanie planów z atomowymi commitami, cyklami weryfikacji
3. **Testowanie**: Testy jednostkowe → Testy integracyjne → Weryfikacja UAT
4. **Przegląd**: Przegląd kodu → Audyt bezpieczeństwa → Dokumentacja
5. **Wdrożenie**: Zakończenie etapu → Archiwizacja → Następny etap

### Zasady commitów

- **Commity fazy**: Dołączaj numer fazy w komunikacie commita (`feat(12-01): ...`)
- **Co-authored-by**: Zawsze dodawaj `Co-Authored-By: Claude Code <noreply@anthropic.com>`
- **Atomowe commity**: Każdy commit powinien zawierać jedną logiczną zmianę
- **Konwencja**: Conventional commits z typem:zakres opis

### Standardy kodu

- **Python**: Limit linii 88 znaków, formatowanie black, pytest
- **Dokumentacja**: Markdown ze spójną hierarchią nagłówków
- **Testowanie**: Programowanie sterowane testami (TDD) dla nowych funkcji
- **Bezpieczeństwo**: Regularne aktualizacje zależności, walidacja wejścia, kodowanie wyjścia

## Licencja

Licencja MIT — patrz plik LICENSE dla szczegółów.

## Wsparcie

W przypadku pytań, problemów lub sugestii:
1. Sprawdź istniejącą dokumentację
2. Przejrzyj logi testów w celu uzyskania szczegółów błędów
3. Sprawdź pliki konfiguracyjne (.env, credentials.json)
4. Przetestuj ręczne uruchomienie (`python -m src.orchestrator`)
5. Sprawdź Podgląd zdarzeń systemu Windows, jeśli używasz Harmonogramu zadań

Twoje wsparcie dla rozwoju tego narzędzia jest bardzo doceniane - <a href="https://www.paypal.com/donate/?business=8JF7EPW5NWEJL&no_recurring=0&item_name=As+a+passionate+supporter+of+efficient+project+mgmt%2C+I%27ve+been+dedicated+to+creating+tools%2C+that+streamline+reporting+processes&currency_code=EUR" target="_blank">Przekaż darowiznę</a><br/>

Jeśli narzędzie jest przydatne, rozważ wsparcie jego dalszego rozwoju. Z chęcią poznam wszelkie pomysły i sugestie dotyczące ulepszania rozwiązania.<br/>

Testowane pod Windows 11 Home.

---

*Ostatnia aktualizacja: 2026-07-15*
*Faza 12 zakończona: Rozszerzone porównywanie pytań z diff na poziomie pól*
*Inpol Monitor v1.0 (M1) - Wstępne wdrożenie*
*Projekt stworzony z troską i uwagą na jakość*

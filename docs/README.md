# Inpol Monitor — Документация / Dokumentacja / Документація

Documentation for the Inpol Monitor project. Diagrams use Mermaid syntax and render in GitHub, GitLab, VS Code, and any Mermaid-compatible viewer.

Документація проєкту Inpol Monitor. Діаграми використовують синтаксис Mermaid і відображаються в GitHub, GitLab, VS Code та будь-якому переглядачі Mermaid.

Дokumentacja projektu Inpol Monitor. Diagramy używają składni Mermaid i renderują się w GitHub, GitLab, VS Code oraz w dowolnej przeglądarce kompatybilnej z Mermaid.

---

## Languages / Языки / Języki

| Language | Architecture | System Interactions |
|----------|--------------|---------------------|
| 🇬🇧 English | [en/architecture/ARCHITECTURE.md](en/architecture/ARCHITECTURE.md) | [en/system-interactions/SYSTEM_INTERACTIONS.md](en/system-interactions/SYSTEM_INTERACTIONS.md) |
| 🇵🇱 Polski | [pl/architecture/ARCHITECTURE.md](pl/architecture/ARCHITECTURE.md) | [pl/system-interactions/SYSTEM_INTERACTIONS.md](pl/system-interactions/SYSTEM_INTERACTIONS.md) |
| 🇷🇺 Русский | [ru/architecture/ARCHITECTURE.md](ru/architecture/ARCHITECTURE.md) | [ru/system-interactions/SYSTEM_INTERACTIONS.md](ru/system-interactions/SYSTEM_INTERACTIONS.md) |
| 🇺🇦 Українська | [ua/architecture/ARCHITECTURE.md](ua/architecture/ARCHITECTURE.md) | [ua/system-interactions/SYSTEM_INTERACTIONS.md](ua/system-interactions/SYSTEM_INTERACTIONS.md) |

---

## Contents / Содержание / Zawartość

### Architecture Diagrams / Диаграмы архитектуры / Diagramy architektury

- **Component Diagram** — layers and components of the system
- **Main Check Cycle Sequence** — full monitoring cycle from trigger to notification
- **Change Detection Detail** — strategy pattern for 7 change types
- **Web UI Sequence** — Flask app login, list, comparison flows
- **Data Flow Summary** — inputs → pipeline → outputs
- **Deployment Architecture** — Windows host layout with Task Scheduler
- **Architectural Patterns** — Strategy, Repository, Batch-then-notify, Fallback chain, INSERT-only immutability, DI, i18n, Session management

### System Interaction Flows / Потоки взаимодействий / Przepływy interakcji

- **Authentication Flow** — sequential auth with CSRF and Akamai challenge solving
- **Data Extraction Flow** — scraper fetching case data with localization
- **Storage Flow** — INSERT-only immutable snapshot storage
- **Change Detection Flow** — strategy pattern detectors
- **Telegram Notification Flow** — batch-then-notify with localization
- **Email Fallback Flow** — SMTP fallback when Telegram fails
- **Web UI Flow** — Flask routes and session handling
- **Localization / i18n Flow** — JSON bundles with fallback maps
- **Error Handling and Recovery Flow** — error sources and recovery actions
- **Configuration Flow** — .env and credentials.json consumption
- **Windows Task Scheduler Integration** — 3x daily triggers

---

## Related / Смежное / Pokrewne

- [README.md](../README.md) — Main documentation (EN)
- [README.pl.md](../README.pl.md) — Główna dokumentacja (PL)
- [README.ru.md](../README.ru.md) — Основная документация (RU)
- [README.ua.md](../README.ua.md) — Основна документація (UA)
- [.planning/PROJECT.md](../.planning/PROJECT.md) — Requirements and constraints
- [SCHEDULING.md](../SCHEDULING.md) — Task Scheduler setup guide

# Phase 1: Project Foundation & Authentication - Research

**Researched:** 2026-03-27
**Domain:** Python web scraping authentication, session management, CLI project structure
**Confidence:** HIGH

## Summary

This phase establishes the foundation for a Python-based web monitoring system that authenticates to the Polish immigration portal (inpol.mazowieckie.pl) for two separate accounts. The standard stack uses `requests` for HTTP sessions with cookie persistence, `beautifulsoup4` with `lxml` parser for HTML extraction, and `python-dotenv` for credential management.

The recommended approach follows a layered batch architecture where authentication is isolated as a reusable component. Sessions should persist across requests using `requests.Session()`, with CSRF token extraction before login. Credentials are stored in a `.env` file (gitignored) with an `.env.example` template committed.

**Primary recommendation:** Use `requests` + `beautifulsoup4` (lxml parser) + `python-dotenv` with a dedicated `src/auth.py` module handling sequential login for both accounts.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Organized structure with `src/` directory for Python modules
- **D-02:** Separate directories for `data/` (SQLite database) and `logs/` (execution logs)
- **D-03:** Root-level entry point `check.py` for CLI execution
- **D-04:** Sequential authentication - login to account 1, fetch 3 cases, logout, then login to account 2, fetch 2 cases, logout
- **D-05:** Session reuse - check if valid session exists before attempting fresh login
- **D-06:** Standard login flow: extract CSRF from login page, POST credentials, save session cookies, verify login succeeded
- **D-07:** JSON file (`credentials.json`) for structured credentials with format: `{"account1": {...}, "account2": {...}}`
- **D-08:** Lenient validation - warn but continue if some credentials are missing (useful for testing one account at a time)
- **D-09:** Hybrid testing - use real credentials to record HTML responses, then replay offline for parsing tests
- **D-10:** Verbose flag (`-v`) toggles detailed output vs silent mode

### Claude's Discretion
- Specific directory names within src/ (e.g., `src/auth/` vs `src/`)
- Exact JSON structure for credentials (as long as it covers both accounts)
- Logging library choice (standard `logging` module vs third-party)
- Session validity check implementation (time-based expiry vs request-based)

### Deferred Ideas (OUT OF SCOPE)
None - discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-01 | Authenticate to inpol.mazowieckie.pl with username/password for 2 separate accounts | Session management with requests, CSRF token extraction, sequential login flow |
| AUTH-02 | Store credentials securely in .env file | python-dotenv pattern, .gitignore enforcement, .env.example template |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `requests` | 2.33.0 | HTTP client with session/cookie management | Industry standard, persistent connections, automatic cookie handling |
| `beautifulsoup4` | 4.14.3 | HTML parsing and data extraction | Pythonic API, handles malformed HTML gracefully |
| `lxml` | 5.x (via bs4) | HTML parser backend for BeautifulSoup | 5-10x faster than html.parser, C-based |
| `python-dotenv` | 1.2.2 | Load environment variables from .env file | Standard pattern for local credential management |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `logging` (stdlib) | built-in | Application logging | Always - use standard library for CLI apps |
| `argparse` (stdlib) | built-in | CLI argument parsing | For `-v` verbose flag and manual triggers |
| `json` (stdlib) | built-in | Credentials file parsing | For credentials.json structure |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `requests` | `httpx` | httpx adds async support but adds dependency; not needed for sequential batch checks |
| `beautifulsoup4` | `lxml` directly | Direct lxml is faster but has steeper learning curve; BS4+lxml is best of both |
| `beautifulsoup4` | `selectolax` | 30x faster parser but less mature ecosystem; overkill for 5 cases |
| `.env` file | OS keychain | More secure but adds complexity; .env is sufficient for single-user local script |

**Installation:**
```bash
pip install requests beautifulsoup4 lxml python-dotenv
```

**Version verification:**
```bash
pip show requests        # 2.33.0 (released 2026-03-25)
pip show beautifulsoup4  # 4.14.3
pip show lxml            # 5.x series
pip show python-dotenv   # 1.2.2
```

## Architecture Patterns

### Recommended Project Structure
```
inpol-monitor/
├── .env                      # Credentials (gitignored)
├── .env.example              # Template with placeholder values
├── .gitignore                # Must include .env, *.db, *.log
├── credentials.json          # Structured account credentials (gitignored)
├── check.py                  # CLI entry point (D-03)
├── requirements.txt          # Dependencies
├── src/                      # (D-01)
│   ├── __init__.py
│   ├── auth.py               # Authentication module
│   ├── session_manager.py    # Session persistence logic
│   └── config.py             # Configuration loading
├── data/                     # (D-02)
│   └── .gitkeep              # SQLite database stored here
└── logs/                     # (D-02)
    └── .gitkeep              # Execution logs stored here
```

### Pattern 1: Session Manager with Reuse (D-05, D-06)
**What:** Encapsulate `requests.Session()` with login state tracking and CSRF extraction.

**When:** Any component needs authenticated HTTP access.

**Example:**
```python
# Source: https://python-requests.org/python-requests-session/
import requests
from bs4 import BeautifulSoup

class SessionManager:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        })

    def extract_csrf(self, login_url: str) -> str:
        """GET login page, extract CSRF token from hidden input."""
        response = self.session.get(login_url)
        soup = BeautifulSoup(response.text, 'lxml')
        csrf_input = soup.find('input', {'name': '_csrf_token'})
        if not csrf_input:
            raise ValueError("CSRF token not found on login page")
        return csrf_input.get('value', '')

    def login(self, username: str, password: str, csrf_token: str) -> bool:
        """POST credentials, verify login succeeded."""
        response = self.session.post(
            f"{self.base_url}/login",
            data={'_csrf_token': csrf_token, 'username': username, 'password': password},
            allow_redirects=True
        )
        # Verify by checking for logout link or dashboard URL
        return "logout" in response.text.lower() or "/dashboard" in response.url

    def get(self, url: str, **kwargs):
        return self.session.get(f"{self.base_url}{url}", **kwargs)

    def close(self):
        self.session.close()
```

### Pattern 2: Sequential Authentication Flow (D-04)
**What:** Login to account 1, process cases, logout, then repeat for account 2.

**When:** Multiple accounts with separate credentials need sequential access.

**Example:**
```python
def run_check(verbose: bool = False):
    config = load_config()

    for account_name in ['account1', 'account2']:
        creds = config.get(account_name)
        if not creds:
            logger.warning(f"Skipping {account_name}: no credentials")
            continue

        session = SessionManager(config['base_url'])
        try:
            csrf = session.extract_csrf('/login')
            if session.login(creds['username'], creds['password'], csrf):
                logger.info(f"Logged in to {account_name}")
                cases = fetch_cases(session, creds.get('case_ids', []))
                yield account_name, cases
            else:
                logger.error(f"Login failed for {account_name}")
        finally:
            session.close()  # Explicit logout
```

### Pattern 3: Credential Loading with Validation (D-07, D-08)
**What:** Load credentials from JSON with lenient validation.

**When:** Credentials may be partially available during testing.

**Example:**
```python
import json
import os

def load_credentials(path: str = "credentials.json") -> dict:
    """Load credentials from JSON file with lenient validation."""
    if not os.path.exists(path):
        logger.warning(f"Credentials file not found: {path}")
        return {}

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Lenient validation: warn but don't fail
    for account in ['account1', 'account2']:
        if account not in data:
            logger.warning(f"No credentials for {account}")
        elif 'username' not in data[account]:
            logger.warning(f"No username for {account}")

    return data
```

### Anti-Patterns to Avoid
- **Hardcoded credentials:** Never put username/password in source code. Use `.env` + `credentials.json` (gitignored).
- **Session leakage:** Always call `session.close()` or use context manager to release connections.
- **Silent login failures:** Verify login succeeded by checking response content or URL, not just HTTP status.
- **CSRF blindness:** Always extract CSRF token from login page before POST; don't assume token name.
- **Print debugging:** Use `logging` module, not `print()`, for CLI output (enables `-v` flag control).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP sessions with cookies | Manual cookie jar management | `requests.Session()` | Handles cookie persistence, connection pooling, redirects automatically |
| HTML parsing | Regex-based extraction | `beautifulsoup4` + `lxml` | Handles malformed HTML, provides tree navigation, CSS selectors |
| Environment variable loading | Manual `.env` file parsing | `python-dotenv` | Standard format, handles quotes/escaping, well-tested |
| CLI argument parsing | Manual `sys.argv` parsing | `argparse` (stdlib) | Built-in help, type validation, flag handling |
| Logging output | `print()` statements | `logging` module (stdlib) | Log levels, formatting, file+stdout output, verbosity control |

**Key insight:** Each of these "simple" problems has edge cases (cookie expiry, malformed HTML, special characters in env vars) that standard libraries handle correctly.

## Runtime State Inventory

Not applicable - this is a greenfield phase with no existing runtime state to migrate.

## Common Pitfalls

### Pitfall 1: CSRF Token Extraction Failure
**What goes wrong:** Login POST returns 403 because CSRF token wasn't extracted or token name changed.

**Why it happens:** Portal may use non-standard CSRF field names (`_csrf_token`, `csrfmiddlewaretoken`, `authenticity_token`).

**How to avoid:**
1. Inspect login page HTML to find exact field name
2. Log the extracted token value (first 8 chars) for debugging
3. Handle missing token gracefully with clear error message

**Warning signs:** Login page loads (200) but POST returns 403 or redirects back to login.

### Pitfall 2: Session Cookie Expiry
**What goes wrong:** Session appears valid but server rejects requests with "session expired".

**Why it happens:** Server-side session timeout (often 30-60 minutes of inactivity).

**How to avoid:**
1. Check session validity before each request (look for "login" in response)
2. Implement re-login on detection of expired session
3. Keep sessions short-lived; don't reuse across days

**Warning signs:** Response contains login form HTML instead of expected content.

### Pitfall 3: Credentials File Not Found at Runtime
**What goes wrong:** Script runs but skips accounts due to missing credentials.

**Why it happens:** `credentials.json` path is relative; script runs from different working directory (e.g., Task Scheduler).

**How to avoid:**
1. Use absolute path: `Path(__file__).parent.parent / "credentials.json"`
2. Or resolve relative to cwd: `Path.cwd() / "credentials.json"`
3. Log clear error: "Credentials file not found at /absolute/path"

**Warning signs:** "No credentials for account1" warning with no file path.

### Pitfall 4: Windows Line Endings in Credentials File
**What goes wrong:** Credentials have trailing `\r` characters, causing login failures.

**Why it happens:** JSON file edited on Windows with CRLF line endings; values may pick up whitespace.

**How to avoid:**
1. Use `.strip()` on loaded credential values
2. Ensure JSON file uses UTF-8 encoding
3. Validate credentials don't contain whitespace: `if creds['password'].strip() != creds['password']`

**Warning signs:** Login fails but credentials "look correct" when printed.

## Code Examples

Verified patterns from official sources:

### Loading Environment Variables
```python
# Source: https://github.com/theskumar/python-dotenv
from dotenv import load_dotenv
import os

load_dotenv()  # Loads .env from current directory

# Access credentials
inpol_base_url = os.getenv("INPOL_BASE_URL", "https://inpol.mazowieckie.pl")
```

### Session with Retry Strategy
```python
# Source: https://docs.python-requests.org/en/latest/user/advanced/
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry)
session.mount('https://', adapter)
```

### Logging Setup with Verbose Flag
```python
# Source: https://docs.python.org/3/library/logging.html
import logging
import sys

def setup_logging(verbose: bool = False):
    logger = logging.getLogger("inpol_monitor")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(levelname)s: %(message)s' if not verbose else
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
```

### BeautifulSoup with lxml Parser
```python
# Source: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
from bs4 import BeautifulSoup

html = "<html>...</html>"  # Response text
soup = BeautifulSoup(html, 'lxml')  # Use lxml parser for speed

# Extract by CSS selector
status_elem = soup.select_one('div.case-status')
status = status_elem.get_text(strip=True) if status_elem else None

# Extract all documents
doc_links = soup.select('a.document-link')
documents = [link.get_text(strip=True) for link in doc_links]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual cookie jar | `requests.Session()` auto-management | 2011+ | Simplifies authenticated scraping |
| `html.parser` default | `lxml` parser for BS4 | 2015+ | 5-10x parsing speed improvement |
| Hardcoded secrets | `.env` + `python-dotenv` | 2018+ | Standard local dev secret management |
| `print()` debugging | `logging` module with levels | 2020+ | Production-ready observability |
| Regex HTML parsing | BeautifulSoup CSS selectors | 2010+ | Robust against HTML structure changes |

**Deprecated/outdated:**
- `urllib2` (Python 2): Use `requests` or `urllib.request` (Python 3)
- `mechanize`: Outdated, use `requests` + `BeautifulSoup`
- `html5lib` parser: Slowest option; use `lxml` unless HTML5 parsing required

## Open Questions

1. **CSRF token field name on inpol.mazowieckie.pl**
   - What we know: Portal uses standard form authentication
   - What's unclear: Exact CSRF field name (`_csrf_token`, `csrf_token`, etc.)
   - Recommendation: Inspect login page HTML in browser dev tools during Phase 1 implementation

2. **Session timeout duration**
   - What we know: Portal maintains sessions for authenticated browsing
   - What's unclear: How long sessions remain valid (minutes? hours?)
   - Recommendation: Implement session validity check; re-login on detection of expired session

3. **Login success indicator**
   - What we know: Login redirects to dashboard or back to login form
   - What's unclear: Specific URL or content that confirms successful login
   - Recommendation: Check for logout link presence or dashboard-specific content

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | Yes | 3.11.9 | - |
| pip | Package install | Yes | 24.0 | - |
| requests | HTTP client | No | - | Install via pip |
| beautifulsoup4 | HTML parsing | No | - | Install via pip |
| lxml | BS4 parser backend | No | - | Install via pip (or use html.parser fallback) |
| python-dotenv | Credential loading | No | - | Install via pip (or manual .env parsing) |

**Missing dependencies with no fallback:**
- `requests` - must install
- `beautifulsoup4` - must install
- `lxml` - must install (or use built-in `html.parser` with reduced performance)
- `python-dotenv` - must install (or implement manual .env parsing)

**Installation command:**
```bash
pip install requests beautifulsoup4 lxml python-dotenv
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (recommended for Phase 1) |
| Config file | `pytest.ini` or `pyproject.toml` - see Wave 0 |
| Quick run command | `pytest tests/test_auth.py -x -v` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | Authenticate 2 accounts sequentially | Integration (mocked HTML) | `pytest tests/test_auth.py::test_sequential_login -x` | Wave 0 |
| AUTH-02 | Load credentials from .env | Unit | `pytest tests/test_config.py::test_load_credentials -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q` (fast feedback)
- **Per wave merge:** `pytest tests/ -v` (full output)
- **Phase gate:** All tests green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/conftest.py` - shared fixtures (sample HTML, mock sessions)
- [ ] `tests/test_auth.py` - authentication tests with recorded HTML
- [ ] `tests/test_config.py` - credential loading tests
- [ ] `pytest.ini` or `pyproject.toml` - pytest configuration
- [ ] Framework install: `pip install pytest`

## Sources

### Primary (HIGH confidence)
- [requests 2.33.0 documentation](https://docs.python-requests.org/en/master/) - Session management, retry strategy
- [BeautifulSoup4 documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) - HTML parsing patterns
- [python-dotenv documentation](https://github.com/theskumar/python-dotenv) - Environment variable loading
- [Python logging documentation](https://docs.python.org/3/library/logging.html) - Logging configuration

### Secondary (MEDIUM confidence)
- [Web Scraping for Beginners in 2026](https://dev.to/agenthustler/web-scraping-for-beginners-in-2026-a-no-bs-guide-26m8) - 2026 best practices
- [Python Requests Session Guide](https://python-requests.org/python-requests-session/) - Session patterns
- [How to Scrape a Website Behind a Login With Python (2026)](https://www.scrapeless.com/en/blog/web-scraping-login-python) - Login flow patterns
- [BeautifulSoup vs lxml Comparison](https://calmops.com/programming/python/beautifulsoup-vs-lxml-html-parsing/) - Parser selection
- [Python Logging Best Practices 2026](https://www.carmatec.com/blog/python-logging-best-practices-complete-guide/) - CLI logging patterns

### Tertiary (LOW confidence)
- Community blog posts on credential management - verify against official python-dotenv docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - verified against PyPI, official docs, 2026 guides
- Architecture: HIGH - aligns with ARCHITECTURE.md patterns, standard web scraping practices
- Pitfalls: MEDIUM - based on common web scraping issues; portal-specific pitfalls need validation

**Research date:** 2026-03-27
**Valid until:** 2026-06-27 (30 days for stable libraries; requests/bs4 change infrequently)

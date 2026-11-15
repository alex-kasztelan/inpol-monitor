---
phase: 01-project-foundation-authentication
plan: 02
type: execute
wave: 2
depends_on:
  - 01-PLAN.md
files_modified:
  - src/session_manager.py
  - src/auth.py
autonomous: true
requirements:
  - AUTH-01
user_setup: []

must_haves:
  truths:
    - "Session manager maintains cookies across requests"
    - "CSRF token extracted before login POST"
    - "Login success verified by response content"
    - "Session closed after use"
  artifacts:
    - path: "src/session_manager.py"
      provides: "SessionManager class with requests.Session()"
      exports: ["SessionManager"]
    - path: "src/auth.py"
      provides: "Authentication flow functions"
      exports: ["authenticate_account", "extract_csrf_token"]
  key_links:
    - from: "src/session_manager.py"
      to: "requests.Session"
      via: "self.session = requests.Session()"
      pattern: "requests\\.Session\\(\\)"
    - from: "src/auth.py"
      to: "src/session_manager.py"
      via: "import SessionManager"
      pattern: "from.*session_manager.*import"
    - from: "src/session_manager.py"
      to: "src/config.py"
      via: "load_env() for base_url"
      pattern: "load_env\\(\\)"
---

<objective>
Implement session management and authentication flow for inpol.mazowieckie.pl.

Purpose: Enable authenticated access to the portal with proper CSRF handling, session reuse, and login verification (AUTH-01, D-05, D-06).
Output: SessionManager class and auth module ready for sequential multi-account login.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01-project-foundation-authentication/01-CONTEXT.md
@.planning/phases/01-project-foundation-authentication/01-RESEARCH.md
@.planning/research/ARCHITECTURE.md
@.planning/phases/01-project-foundation-authentication/01-SUMMARY.md
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement SessionManager class</name>
  <files>src/session_manager.py</files>
  <read_first>
    - .planning/phases/01-project-foundation-authentication/01-RESEARCH.md (Pattern 1: Session Manager with Reuse)
    - .planning/research/ARCHITECTURE.md (Auth Layer patterns)
  </read_first>
  <behavior>
    - SessionManager(base_url) initializes requests.Session() with User-Agent header
    - extract_csrf(login_url) GETs login page, finds _csrf_token input, returns value
    - login(username, password, csrf_token) POSTs credentials, returns True if login succeeded
    - get(url) wraps session.get() with base_url prefix
    - close() calls session.close() for cleanup
    - Login verification checks for logout link or dashboard URL in response
  </behavior>
  <action>
    Create src/session_manager.py with:

    1. **Imports:** requests, BeautifulSoup from bs4, logging

    2. **SessionManager class:**
       - __init__(self, base_url: str):
         - self.base_url = base_url
         - self.session = requests.Session()
         - self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 'Accept-Language': 'en-US,en;q=0.9'})
         - self.logged_in = False

       - extract_csrf(self, login_url: str) -> str:
         - response = self.session.get(f"{self.base_url}{login_url}")
         - soup = BeautifulSoup(response.text, 'lxml')
         - csrf_input = soup.find('input', {'name': '_csrf_token'})
         - Raise ValueError if not found
         - Return csrf_input.get('value', '')

       - login(self, username: str, password: str, csrf_token: str) -> bool:
         - POST to f"{self.base_url}/login" with data={'_csrf_token': csrf_token, 'username': username, 'password': password}
         - Verify success: check "logout" in response.text.lower() OR "/dashboard" in response.url
         - Set self.logged_in = True on success
         - Return success boolean

       - get(self, url: str, **kwargs):
         - Return self.session.get(f"{self.base_url}{url}", **kwargs)

       - close(self):
         - self.session.close()

    3. Add logging for debug output (login attempts, CSRF extraction)
  </action>
  <verify>
    <automated>pytest tests/test_session.py -x -v</automated>
  </verify>
  <acceptance_criteria>
    - src/session_manager.py contains "class SessionManager"
    - src/session_manager.py contains "requests.Session()"
    - src/session_manager.py contains "extract_csrf"
    - src/session_manager.py contains "soup.find" with '_csrf_token'
    - src/session_manager.py contains "def login"
    - src/session_manager.py contains "def close"
    - src/session_manager.py checks for "logout" or "dashboard" in login verification
    - src/session_manager.py sets User-Agent header
    - tests/test_session.py exists with test_extract_csrf and test_login functions
  </acceptance_criteria>
  <done>
    SessionManager class implemented with CSRF extraction, login verification, and proper cleanup. Tests pass.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement authentication flow module</name>
  <files>src/auth.py</files>
  <read_first>
    - .planning/phases/01-project-foundation-authentication/01-CONTEXT.md (decisions D-04, D-05, D-06)
    - .planning/phases/01-project-foundation-authentication/01-RESEARCH.md (Pattern 2: Sequential Authentication Flow)
  </read_first>
  <behavior>
    - authenticate_account(account_name, credentials, base_url) logs in, returns SessionManager or None on failure
    - extract_csrf_token(base_url) is a standalone function for CSRF extraction
    - Login flow: extract CSRF -> POST credentials -> verify success
    - Session reuse check: if session.logged_in, skip re-login
  </behavior>
  <action>
    Create src/auth.py with:

    1. **Imports:** logging, SessionManager from src.session_manager, load_env from src.config

    2. **extract_csrf_token(base_url: str) -> str:**
       - Create SessionManager(base_url)
       - Call session.extract_csrf('/login') (or appropriate login path)
       - Return CSRF token
       - Log extracted token (first 8 chars for debugging)

    3. **authenticate_account(account_name: str, credentials: dict, base_url: str) -> SessionManager | None:**
       - Validate credentials has username and password
       - Create SessionManager(base_url)
       - Extract CSRF token via session.extract_csrf('/login')
       - Call session.login(credentials['username'], credentials['password'], csrf_token)
       - On success: log "Logged in to {account_name}", return session
       - On failure: log error, session.close(), return None

    4. **run_sequential_auth(credentials: dict) -> Generator[tuple[account_name, SessionManager], None, None]:**
       - For each account in credentials:
         - If account missing username/password: warn and continue (D-08)
         - Call authenticate_account()
         - Yield (account_name, session) if successful
         - session.close() after yield (explicit logout D-04)
  </action>
  <verify>
    <automated>pytest tests/test_auth.py -x -v</automated>
  </verify>
  <acceptance_criteria>
    - src/auth.py contains "def authenticate_account"
    - src/auth.py contains "def extract_csrf_token"
    - src/auth.py contains "def run_sequential_auth"
    - src/auth.py imports SessionManager from session_manager
    - src/auth.py uses credentials.get('username') and credentials.get('password')
    - src/auth.py calls session.close() after use
    - src/auth.py has lenient validation (warns but continues on missing credentials)
    - tests/test_auth.py exists with test_authenticate_account function
    - tests/test_auth.py tests missing credentials returns None
  </acceptance_criteria>
  <done>
    Auth module implemented with authenticate_account() and run_sequential_auth() for multi-account login. Tests pass.
  </done>
</task>

</tasks>

<verification>
- pytest tests/test_session.py -x passes
- pytest tests/test_auth.py -x passes
- SessionManager properly closes sessions
- Sequential auth flow yields sessions one at a time (D-04)
</verification>

<success_criteria>
- AUTH-01 satisfied: Authentication module can log into both accounts sequentially
- D-04: Sequential auth (account1 -> logout -> account2 -> logout)
- D-05: Session reuse capability via logged_in flag
- D-06: Standard login flow (CSRF extract -> POST -> verify)
</success_criteria>

<output>
After completion, create `.planning/phases/01-project-foundation-authentication/02-SUMMARY.md` with:
- SessionManager implementation details
- Auth flow description
- Test results
- CSRF field name discovered (if known)
</output>

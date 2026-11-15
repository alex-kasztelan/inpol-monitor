---
phase: 01-project-foundation-authentication
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - requirements.txt
  - .gitignore
  - .env.example
  - credentials.json.example
  - src/__init__.py
  - src/config.py
  - data/.gitkeep
  - logs/.gitkeep
autonomous: true
requirements:
  - AUTH-02
user_setup: []

must_haves:
  truths:
    - "Project has all required directories (src/, data/, logs/)"
    - "Dependencies can be installed via pip"
    - "Credentials load from JSON file with lenient validation"
    - ".env file loads environment variables"
  artifacts:
    - path: "requirements.txt"
      provides: "Python dependency declarations"
      contains: "requests, beautifulsoup4, lxml, python-dotenv"
    - path: ".gitignore"
      provides: "Git exclusion rules"
      contains: ".env, credentials.json, *.db, *.log"
    - path: "src/config.py"
      provides: "Configuration and credential loading"
      exports: ["load_credentials", "load_env"]
    - path: "credentials.json.example"
      provides: "Template for account credentials"
      contains: "account1, account2 structure"
  key_links:
    - from: "src/config.py"
      to: "credentials.json"
      via: "json.load()"
      pattern: "json\\.load.*credentials"
    - from: "src/config.py"
      to: ".env"
      via: "load_dotenv()"
      pattern: "load_dotenv\\(\\)"
---

<objective>
Create project foundation: directory structure, dependencies, and configuration loading.

Purpose: Establish organized project layout (D-01, D-02) with secure credential management (AUTH-02, D-07, D-08).
Output: Installable dependencies, git-safe structure, working credential loader with lenient validation.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-project-foundation-authentication/01-CONTEXT.md
@.planning/phases/01-project-foundation-authentication/01-RESEARCH.md
@.planning/research/ARCHITECTURE.md
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Create project structure and dependencies</name>
  <files>requirements.txt, .gitignore, .env.example, credentials.json.example, src/__init__.py, data/.gitkeep, logs/.gitkeep</files>
  <read_first>
    - .planning/phases/01-project-foundation-authentication/01-CONTEXT.md (decisions D-01, D-02)
    - .planning/phases/01-project-foundation-authentication/01-RESEARCH.md (Standard Stack section)
    - .planning/research/ARCHITECTURE.md (Directory Structure Recommendation)
  </read_first>
  <action>
    Create the following files with exact content:

    1. **requirements.txt** - Python dependencies:
       ```
       requests==2.33.0
       beautifulsoup4==4.14.3
       lxml>=5.0.0
       python-dotenv==1.2.2
       ```

    2. **.gitignore** - Git exclusions (must include):
       ```
       # Credentials
       .env
       credentials.json

       # Data
       *.db
       data/*.db

       # Logs
       *.log
       logs/*.log

       # Python
       __pycache__/
       *.py[cod]
       .pytest_cache/
       ```

    3. **.env.example** - Environment variable template:
       ```
       # Inpol Monitor Environment Configuration
       # Copy this file to .env and fill in actual values

       # Portal base URL
       INPOL_BASE_URL=https://inpol.mazowieckie.pl

       # Login endpoint (will be discovered during implementation)
       # INPOL_LOGIN_URL=
       ```

    4. **credentials.json.example** - Account credentials template:
       ```json
       {
         "account1": {
           "username": "YOUR_USERNAME_HERE",
           "password": "YOUR_PASSWORD_HERE",
           "case_ids": ["CASE1", "CASE2", "CASE3"]
         },
         "account2": {
           "username": "YOUR_USERNAME_HERE",
           "password": "YOUR_PASSWORD_HERE",
           "case_ids": ["CASE4", "CASE5"]
         }
       }
       ```

    5. **src/__init__.py** - Empty package initializer

    6. **data/.gitkeep** - Empty file to preserve directory

    7. **logs/.gitkeep** - Empty file to preserve directory

    8. Create directories: src/, data/, logs/
  </action>
  <verify>
    <automated>ls requirements.txt .gitignore .env.example credentials.json.example src/__init__.py data/.gitkeep logs/.gitkeep 2>&1 | head -20</automated>
  </verify>
  <acceptance_criteria>
    - requirements.txt contains "requests==2.33.0"
    - requirements.txt contains "beautifulsoup4==4.14.3"
    - requirements.txt contains "lxml"
    - requirements.txt contains "python-dotenv==1.2.2"
    - .gitignore contains ".env"
    - .gitignore contains "credentials.json"
    - .gitignore contains "*.db"
    - .gitignore contains "*.log"
    - .env.example contains "INPOL_BASE_URL"
    - credentials.json.example contains "account1" and "account2"
    - credentials.json.example contains "case_ids" array for each account
    - src/ directory exists
    - data/ directory exists
    - logs/ directory exists
  </acceptance_criteria>
  <done>
    All foundation files created with correct content. Directories src/, data/, logs/ exist with .gitkeep files.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement credential and config loading module</name>
  <files>src/config.py</files>
  <read_first>
    - .planning/phases/01-project-foundation-authentication/01-CONTEXT.md (decisions D-07, D-08)
    - .planning/phases/01-project-foundation-authentication/01-RESEARCH.md (Pattern 3: Credential Loading)
  </read_first>
  <behavior>
    - load_credentials(path) returns dict with account1, account2 keys when file exists
    - load_credentials(path) returns empty dict when file missing, logs warning
    - load_credentials(path) warns but continues if account missing username/password
    - load_env() loads .env file and returns base URL with default fallback
    - All paths resolved relative to script location, not cwd
  </behavior>
  <action>
    Create src/config.py with:

    1. **Imports:** json, os, logging, Path from pathlib, load_dotenv from dotenv

    2. **Logger setup:** getLogger("inpol_monitor.config")

    3. **load_credentials(path: str = "credentials.json") -> dict:**
       - Resolve path relative to project root (not cwd)
       - Return {} if file doesn't exist, log warning
       - Parse JSON, return data
       - For each account (account1, account2): warn if missing or missing username/password (D-08 lenient validation)
       - Strip whitespace from username/password values (avoid Windows CRLF issues)

    4. **load_env() -> dict:**
       - Call load_dotenv() to load .env from current directory
       - Return dict with:
         - "base_url": os.getenv("INPOL_BASE_URL", "https://inpol.mazowieckie.pl")
  </action>
  <verify>
    <automated>pytest tests/test_config.py -x -v</automated>
  </verify>
  <acceptance_criteria>
    - src/config.py contains "def load_credentials"
    - src/config.py contains "def load_env"
    - src/config.py contains "load_dotenv()"
    - src/config.py contains "json.load"
    - src/config.py contains logging.getLogger
    - src/config.py contains ".strip()" for credential values
    - src/config.py resolves path using Path(__file__) or similar (not relative to cwd)
    - tests/test_config.py exists with test_load_credentials function
    - tests/test_config.py tests missing file returns {}
    - tests/test_config.py tests lenient validation (missing keys warn but don't fail)
  </acceptance_criteria>
  <done>
    Config module implemented with load_credentials() (lenient, strips whitespace) and load_env(). Tests pass.
  </done>
</task>

</tasks>

<verification>
- All files from Task 1 exist with correct content
- pip install -r requirements.txt succeeds
- pytest tests/test_config.py -x passes
</verification>

<success_criteria>
- Project structure created per D-01, D-02
- Dependencies installable
- Credentials load from JSON with lenient validation (D-07, D-08)
- .env loading works via python-dotenv (AUTH-02)
</success_criteria>

<output>
After completion, create `.planning/phases/01-project-foundation-authentication/01-SUMMARY.md` with:
- Files created
- Test results
- Any issues encountered (e.g., path resolution problems)
</output>

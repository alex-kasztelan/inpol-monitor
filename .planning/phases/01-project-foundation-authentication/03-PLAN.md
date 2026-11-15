---
phase: 01-project-foundation-authentication
plan: 03
type: execute
wave: 3
depends_on:
  - 01-PLAN.md
  - 02-PLAN.md
files_modified:
  - check.py
  - tests/conftest.py
  - tests/test_config.py
  - tests/test_session.py
  - tests/test_auth.py
  - pytest.ini
autonomous: true
requirements:
  - AUTH-01
  - AUTH-02
user_setup:
  - service: inpol.mazowieckie.pl
    why: "Authentication testing requires real credentials"
    manual_steps:
      - "Create credentials.json with actual account credentials for testing"
      - "Run: python check.py -v to test authentication flow"

must_haves:
  truths:
    - "CLI entry point runs authentication flow"
    - "Verbose flag toggles detailed output"
    - "Tests run with pytest"
    - "Hybrid testing records HTML for offline replay"
  artifacts:
    - path: "check.py"
      provides: "CLI entry point with argparse"
      exports: ["main"]
    - path: "tests/conftest.py"
      provides: "Pytest fixtures and shared test data"
      contains: "sample HTML fixtures, mock sessions"
    - path: "pytest.ini"
      provides: "Pytest configuration"
      contains: "testpaths, python_files"
  key_links:
    - from: "check.py"
      to: "src/auth.py"
      via: "import run_sequential_auth"
      pattern: "from.*auth.*import"
    - from: "check.py"
      to: "src/config.py"
      via: "import load_credentials, load_env"
      pattern: "from.*config.*import"
    - from: "tests/conftest.py"
      to: "tests/*.py"
      via: "pytest fixtures"
      pattern: "@pytest.fixture"
---

<objective>
Create CLI entry point and test scaffolding for authentication flow verification.

Purpose: Enable manual testing via CLI (D-03, D-09, D-10) and automated testing via pytest.
Output: Working check.py script, pytest test suite, recorded HTML samples for offline testing.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01-project-foundation-authentication/01-CONTEXT.md
@.planning/phases/01-project-foundation-authentication/01-RESEARCH.md
@.planning/phases/01-project-foundation-authentication/01-SUMMARY.md
@.planning/phases/01-project-foundation-authentication/02-SUMMARY.md
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Create CLI entry point with verbose flag</name>
  <files>check.py</files>
  <read_first>
    - .planning/phases/01-project-foundation-authentication/01-CONTEXT.md (decisions D-03, D-09, D-10)
    - .planning/phases/01-project-foundation-authentication/01-RESEARCH.md (Logging Setup with Verbose Flag)
    - .planning/phases/01-project-foundation-authentication/01-SUMMARY.md (config module exports)
    - .planning/phases/01-project-foundation-authentication/02-SUMMARY.md (auth module exports)
  </read_first>
  <action>
    Create check.py with:

    1. **Imports:** argparse, logging, sys, Path from pathlib
       - Import load_credentials, load_env from src.config
       - Import run_sequential_auth from src.auth

    2. **setup_logging(verbose: bool) -> logging.Logger:**
       - Create logger "inpol_monitor"
       - Set level: DEBUG if verbose else INFO
       - Add StreamHandler to sys.stdout
       - Format: '%(levelname)s: %(message)s' if not verbose else '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
       - Return logger

    3. **main() function:**
       - Parse args: argparse with -v/--verbose flag
       - Call setup_logging(args.verbose)
       - Load credentials via load_credentials()
       - Load env config via load_env()
       - Call run_sequential_auth(credentials)
       - For each (account_name, session) yielded:
         - Log "Processing {account_name}: {len(session.cases)} cases"
         - Log "Logout complete for {account_name}"
       - Catch exceptions, log error, exit 1

    4. **if __name__ == "__main__": main()**

    5. Add docstring at top describing purpose
  </action>
  <verify>
    <automated>python check.py --help</automated>
  </verify>
  <acceptance_criteria>
    - check.py exists at project root
    - check.py contains "argparse" and "ArgumentParser"
    - check.py contains "-v" or "--verbose" argument
    - check.py contains "load_credentials"
    - check.py contains "load_env"
    - check.py contains "run_sequential_auth"
    - check.py contains "if __name__ == '__main__'"
    - check.py has setup_logging function with verbose parameter
    - python check.py --help outputs usage information
    - python check.py -v runs with verbose output
  </acceptance_criteria>
  <done>
    CLI entry point working. python check.py -v runs auth flow with verbose logging.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Create test scaffolding and pytest configuration</name>
  <files>tests/__init__.py, tests/conftest.py, tests/test_config.py, tests/test_session.py, tests/test_auth.py, pytest.ini</files>
  <read_first>
    - .planning/phases/01-project-foundation-authentication/01-RESEARCH.md (Validation Architecture section)
    - .planning/phases/01-project-foundation-authentication/01-SUMMARY.md (config module)
    - .planning/phases/01-project-foundation-authentication/02-SUMMARY.md (auth module, session_manager)
  </read_first>
  <action>
    Create test infrastructure:

    1. **tests/__init__.py** - Empty package initializer

    2. **pytest.ini:**
       ```ini
       [pytest]
       testpaths = tests
       python_files = test_*.py
       python_functions = test_*
       addopts = -v --tb=short
       ```

    3. **tests/conftest.py:**
       - Import pytest
       - Create @pytest.fixture for sample_login_html (real HTML from inpol login page)
       - Create @pytest.fixture for mock_session (MagicMock with SessionManager interface)
       - Create @pytest.fixture for sample_credentials dict with account1, account2

    4. **tests/test_config.py:**
       - test_load_credentials_missing_file: returns {} when file not found
       - test_load_credentials_valid: returns dict with accounts when file exists
       - test_load_credentials_lenient: warns but continues on missing username
       - test_load_env: returns dict with base_url

    5. **tests/test_session.py:**
       - test_extract_csrf: returns token from HTML
       - test_extract_csrf_missing: raises ValueError when no CSRF token
       - test_login_success: returns True when login succeeds
       - test_login_failure: returns False when login fails

    6. **tests/test_auth.py:**
       - test_authenticate_account_success: returns SessionManager on success
       - test_authenticate_account_missing_creds: returns None on missing credentials
       - test_run_sequential_auth: yields sessions for each account
  </action>
  <verify>
    <automated>pip install pytest && pytest tests/ -x -q</automated>
  </verify>
  <acceptance_criteria>
    - tests/ directory exists
    - tests/__init__.py exists
    - pytest.ini exists with [pytest] section
    - tests/conftest.py contains @pytest.fixture
    - tests/test_config.py contains test_load_credentials function
    - tests/test_session.py contains test_extract_csrf function
    - tests/test_auth.py contains test_authenticate_account function
    - pytest tests/ -x -q runs without import errors
  </acceptance_criteria>
  <done>
    Test scaffolding complete. pytest runs without import errors. Fixtures available for integration testing.
  </done>
</task>

</tasks>

<verification>
- python check.py --help shows usage
- python check.py -v runs (may fail on credentials, but code path works)
- pytest tests/ -x -q runs without import errors
- All test files exist with required test functions
</verification>

<success_criteria>
- D-03: CLI entry point check.py created at project root
- D-09: Hybrid testing ready (conftest has HTML recording fixtures)
- D-10: Verbose flag -v implemented
- AUTH-01, AUTH-02: Both requirements have test coverage
</success_criteria>

<output>
After completion, create `.planning/phases/01-project-foundation-authentication/03-SUMMARY.md` with:
- CLI usage instructions
- Test coverage summary
- Known issues or TODOs for next phase
- CSRF field name if discovered during testing
</output>

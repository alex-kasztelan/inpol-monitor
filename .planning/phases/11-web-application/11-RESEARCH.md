# Phase 11: Web Application - Research

**Researched:** 2026-04-22
**Domain:** Flask web application with SQLite for case snapshot viewing
**Confidence:** HIGH

## Summary

Phase 11 builds a Flask web interface for viewing historical case snapshots stored in the existing SQLite database. The application must provide: (1) list all snapshots across all cases, (2) filter by case ID and date range, (3) select and compare two snapshots of the same case, and (4) print-friendly comparison view.

**Primary recommendation:** Use Flask 3.x with Flask-Login for authentication, reusing the existing `SnapshotRepository` from `src/storage.py` to query the existing `data/snapshots.db` database. Add missing query capabilities (date range, snapshot-by-ID) as new methods to the repository, not as a separate data layer.

## User Constraints (from Context)

> No CONTEXT.md found for this phase. Using additional_context from phase description.

### Tech Constraints
- **Framework:** Flask (lightweight, internal tool)
- **Auth:** Reuse existing credentials.json
- **Deployment:** Local only
- **Database:** SQLite (existing snapshots.db)

### What's Already Available
- `src/storage.py` with `SnapshotRepository` (get_all_snapshots, get_snapshots_by_case, etc.)
- `src/models.py` with `Snapshot`, `CaseData` models
- `src/config.py` for configuration
- `data/snapshots.db` SQLite database

### What's NOT in Existing Codebase
- No Flask or any web framework
- No timestamp range filtering in storage
- No snapshot-by-ID queries

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|----------------|
| WEB-01 | List all snapshots for all cases | Reuse get_all_snapshots() from SnapshotRepository |
| WEB-02 | Filter by case IDs and time frames | Add date range query methods to storage.py |
| WEB-03 | Compare 2 selected snapshots of same case | Add get_snapshots_by_case_and_timerange() |
| WEB-04 | Print comparison view | Flask route with print-friendly template |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | 3.x (latest) | Web framework | Lightweight, Python-native, matches constraint |
| Flask-Login | 0.6.x | Session management, route protection | Standard Flask auth, handles cookies/sessions |
| Flask-SQLAlchemy | 3.x | ORM (optional - can use existing storage.py) | Pythonic DB queries, but NOT required since existing repo works |
| Werkzeug | (bundled with Flask) | Password hashing | Secure password verification for credentials.json |
| Flask-WTF | 1.x | Form handling, CSRF protection | Standard for form validation and security |
| WTForms | 3.x | Form field definitions | Required by Flask-WTF |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Bootstrap | 5.x (CDN) | UI styling | For responsive, print-friendly templates |
| python-dotenv | 1.x (already installed) | .env loading | For config.py reuse |

### Alternative Approaches Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Flask-Login | Manual session + decorator | Flask-Login is standard, provides remember_me, user_loader |
| Flask-SQLAlchemy | Reuse existing storage.py | Existing SnapshotRepository works - don't duplicate |

**Installation:**
```bash
pip install flask flask-login flask-wtf wtforms
```

**Note:** Flask-SQLAlchemy is NOT required. The project already has a working `SnapshotRepository` in `src/storage.py` that handles all SQLite operations. Add missing query methods to `storage.py` rather than introducing a new ORM layer.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── web/
│   ├── __init__.py       # Flask app factory
│   ├── auth.py           # Login logic using credentials.json
│   ├── routes.py        # All Flask routes
│   ├── templates/      # HTML templates
│   │   ├── base.html  # Base layout
│   │   ├── login.html # Login page
│   │   ├── index.html # Snapshot list with filters
│   │   └── compare.html # Comparison view
│   └── static/
│       └── style.css   # Custom styles
├── storage.py           # EXISTING - add missing query methods
└── ...
```

### Pattern 1: Reuse Existing SnapshotRepository
**What:** Import and extend the existing `SnapshotRepository` from `src/storage.py` instead of creating a new data layer.
**When to use:** Always - maintains consistency with existing code, no data duplication
**Example:**
```python
# src/web/routes.py
from src.storage import SnapshotRepository

repo = SnapshotRepository("data/snapshots.db")

@bp.route('/snapshots')
def list_snapshots():
    snapshots = repo.get_all_snapshots()
    return render_template('index.html', snapshots=snapshots)
```

### Pattern 2: Flask-Login Authentication
**What:** Use Flask-Login with credentials.json for authentication.
**When to use:** For protected routes
**Example:**
```python
# Source: DigitalOcean tutorial - Flask-Login
from flask_login import LoginManager, login_user, logout_user, login_required

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        credentials = load_credentials()
        # Verify against credentials.json
        if username == credentials['account1']['username']:
            # Use werkzeug for password check
            if check_password_hash(credentials['account1']['password'], password):
                login_user(user)
```

### Pattern 3: Date Range Filtering
**What:** Add query methods for filtering snapshots by date range.
**When to use:** For WEB-02 (filter by from/to dates)
**Example:**
```python
# src/storage.py - add new method
def get_snapshots_by_timerange(
    self,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    case_id_filter: Optional[str] = None
) -> List[Snapshot]:
    """Get snapshots within a date range, optionally filtered by case_id."""
    conn = self._get_connection()
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM snapshots WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())
        if case_id_filter:
            query += " AND case_id = ?"
            params.append(case_id_filter)
            
        cursor.execute(query, params)
        # ... map rows to Snapshot objects
    finally:
        conn.close()
```

### Pattern 4: Print-Friendly Comparison View
**What:** Use CSS @media print to create print-friendly views.
**When to use:** For WEB-04 (print comparison)
**Example:**
```html
<!-- templates/compare.html -->
<style>
@media print {
    .no-print { display: none; }
    body { font-size: 12pt; }
    .comparison-table { page-break-inside: avoid; }
}
</style>
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|------------|------------|-----|
| Session management | Manual cookie handling | Flask-Login | Handles remember_me, user_loader, secure cookies |
| Password verification | Custom hashing | Werkzeug's check_password_hash | Secure, well-tested, maintained |
| Form validation | Manual input checking | WTForms + Flask-WTF | CSRF protection, validation, reusable |
| Route protection | if not logged_in | @login_required decorator | Standard, consistent |

**Key insight:** For internal tool with single-user authentication, Flask-Login may be overkill. A simple session check using Flask's `session` with credentials.json verification is sufficient and requires fewer dependencies.

## Common Pitfalls

### Pitfall 1: Database Connection Not Closed
**What goes wrong:** Database connections leak, causing "database is locked" errors
**Why it happens:** Forgetting to close connections in route handlers
**How to avoid:** Use context managers or Flask's teardown_appcontext
**Warning signs:** "sqlite3.OperationalError: database is locked"

### Pitfall 2: Datetime Format Mismatch
**What goes wrong:** Date filters return no results
**Why it happens:** SQLite stores timestamps in ISO format, Python compares as datetime objects
**How to avoid:** Convert both to ISO format strings for comparison, or use datetime objects consistently
**Warning signs:** Empty results with valid input dates

### Pitfall 3: SQL Injection in Dynamic Queries
**What goes wrong:** User-provided case_id enables SQL injection
**Why it happens:** Building queries with string concatenation
**How to avoid:** Always use parameterized queries (? placeholders)
**Warning signs:** N/A - prevent at source

### Pitfall 4: Missing SECRET_KEY
**What goes wrong:** Session errors, "SECRET_KEY must be set"
**Why it happens:** Flask requires SECRET_KEY for signed cookies
**How to avoid:** Set app.config['SECRET_KEY'] from environment or config
**Warning signs:** RuntimeError on login

## Code Examples

### Example 1: Flask App with Existing Storage
```python
# src/web/__init__.py
from flask import Flask
from src.config import load_credentials, get_base_path
import os

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    
    # Register blueprints
    from src.web.routes import bp
    app.register_blueprint(bp)
    
    return app
```

### Example 2: Authentication Route Using credentials.json
```python
# src/web/auth.py
from flask import session, redirect, url_for
from werkzeug.security import check_password_hash
from src.config import load_credentials

def verify_credentials(username: str, password: str) -> bool:
    """Verify credentials against credentials.json."""
    creds = load_credentials()
    
    for account in ['account1', 'account2']:
        if account in creds:
            account_creds = creds[account]
            if account_creds.get('username') == username:
                # Direct password comparison (credentials.json stores plaintext)
                if account_creds.get('password') == password:
                    return True
    return False
```

### Example 3: Snapshot Comparison Route
```python
# src/web/routes.py
from flask import Blueprint, render_template, request
from src.storage import SnapshotRepository

bp = Blueprint('web', __name__)
repo = SnapshotRepository("data/snapshots.db")

@bp.route('/compare', methods=['GET', 'POST'])
@login_required
def compare():
    case_id = request.args.get('case_id')
    snapshot1_id = request.args.get('snapshot1')
    snapshot2_id = request.args.get('snapshot2')
    
    # Get both snapshots and compute diff
    s1 = repo.get_snapshot_by_id(snapshot1_id)
    s2 = repo.get_snapshot_by_id(snapshot2_id)
    
    diff = compute_diff(s1, s2)  # Reuse from src/detector.py
    
    return render_template('compare.html', 
                         case_id=case_id,
                         snapshot1=s1, 
                         snapshot2=s2,
                         diff=diff)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom session handling | Flask-Login | Standard since 2019 | Better security, remember_me |
| Direct SQLite queries | Flask-SQLAlchemy or existing repo | Both valid now | Existing repo avoids migration |
| Jinja2 only | Bootstrap + Jinja2 | Standard | Responsive, print-friendly |

**Deprecated/outdated:**
- **Flask < 2.3:** Old import patterns (flask_sqlalchemy → flask_sqlalchemy)
- **WTF < 3.0:** Old form processing (use Flask-WTF instead)

## Open Questions

1. **Authentication complexity**
   - What we know: Single user internal tool, can reuse credentials.json
   - What's unclear: Is Flask-Login worth the dependency overhead?
   - Recommendation: Use simple session-based auth first, add Flask-Login only if needed

2. **Print comparison**
   - What we know: Need print-friendly CSS for comparison view
   - What's unclear: How to format diff for print (tabular vs detailed)?
   - Recommendation: Use Bootstrap table, add @media print styles

3. **Existing storage capabilities**
   - What we know: get_all_snapshots(), get_snapshots_by_account() exist
   - What's unclear: Does get_snapshots_by_case() exist? Need to verify
   - Recommendation: Check storage.py line 176 - method exists, verify it filters correctly

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Flask | Web framework | ✗ (need install) | 3.x | — |
| Flask-Login | Session auth | ✗ (need install) | 0.6.x | Simple session auth |
| Flask-WTF | Forms/CSRF | ✗ (need install) | 1.x | Manual forms |
| python-dotenv | Config loading | ✓ | 1.2.2 | — |
| SQLite | Database | ✓ (built-in) | — | — |
| Werkzeug | Password hashing | ✓ (via Flask) | bundled | — |

**Missing dependencies with no fallback:**
- Flask and extensions need to be installed

**Missing dependencies with fallback:**
- Flask-Login — simple Flask session auth is sufficient for single-user internal tool

## Runtime State Inventory

> This is a NEW feature (web interface), not a rename/refactor - no runtime state migration needed.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — reads from existing snapshots.db | None |
| Live service config | None — local Flask only | None |
| OS-registered state | None | None |
| Secrets/env vars | Existing .env file | None — reuse |
| Build artifacts | None | None |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | pytest.ini (existing) |
| Quick run command | `pytest tests/ -x` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WEB-01 | List all snapshots | unit | `pytest tests/test_storage.py::test_get_all_snapshots -x` | ✅ |
| WEB-02 | Filter by date range | unit | NEW test needed | ❌ Wave 0 |
| WEB-03 | Compare snapshots | unit | Reuse test_detector.py | ✅ |
| WEB-04 | Print view | smoke | Manual verification | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_storage.py -x`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** 177 existing tests + new tests pass

### Wave 0 Gaps
- [ ] `tests/test_storage.py` — add date range filter tests
- [ ] `tests/test_web.py` — new test file for Flask routes
- [ ] Flask install via requirements.txt or pyproject.toml

## Sources

### Primary (HIGH confidence)
- Flask-SQLAlchemy docs (2026) - Date filtering with .between()
- DigitalOcean Flask-Login tutorial - Authentication pattern
- Werkzeug security - Password hashing

### Secondary (MEDIUM confidence)
- CodeStips Flask SQLite guide - Connection management
- oneuptime.com Flask guide - Project structure

### Tertiary (LOW confidence)
- Stack Overflow - Date range queries (marked for validation)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Flask 3.x is current, existing storage.py can be reused
- Architecture: HIGH - Clear patterns for Flask + SQLite
- Pitfalls: MEDIUM - Database connection patterns confirmed via multiple sources

**Research date:** 2026-04-22
**Valid until:** 2026-07-22 (Flask stable, unlikely to change soon)
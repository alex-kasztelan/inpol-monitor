"""Routes module for Flask web application."""

import os
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from src.storage import SnapshotRepository
from src.web.auth import verify_credentials, login_required, login_user, logout_user
from src.localization import t as _t

bp = Blueprint('web', __name__)
repo = SnapshotRepository("data/snapshots.db")

# Available languages
AVAILABLE_LANGUAGES = {
    'en': 'English',
    'pl': 'Polski',
    'ua': 'Українська',
    'ru': 'Русский'
}


def get_session_language():
    """Get language from session, defaulting to .env value."""
    if 'language' not in session:
        session['language'] = os.getenv('LANGUAGE', 'en')
    return session['language']


@bp.route('/api/set-language', methods=['POST'])
@login_required
def set_language():
    """Set the session language."""
    lang = request.form.get('language', 'en')
    if lang in AVAILABLE_LANGUAGES:
        session['language'] = lang
        flash(_t('Web.Nav.LanguageChanged', 'Language changed', language=lang).format(
            language=AVAILABLE_LANGUAGES[lang]), 'success')
    else:
        flash('Invalid language selection.', 'danger')
    return redirect(url_for('web.index'))


@bp.route('/api/accounts-for-case/<case_id>')
@login_required
def accounts_for_case(case_id):
    """Get accounts (logins) available for a specific case."""
    accounts = repo.get_account_ids_for_case(case_id)
    return jsonify(accounts)


@bp.route('/api/cases-for-account/<account_id>')
@login_required
def cases_for_account(account_id):
    """Get cases available for a specific account."""
    cases = repo.get_case_labels_for_account(account_id)
    return jsonify(cases)


@bp.route('/')
@login_required
def index():
    """List all snapshots with optional filters."""
    case_id = request.args.get('case_id', '').strip()
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    account_id = request.args.get('account_id', '')
    endpoint_type = request.args.get('endpoint_type', '')
    sort_by = request.args.get('sort_by', 'timestamp')
    sort_dir = request.args.get('sort_dir', 'desc')
    
    # Parse dates
    start_dt = None
    end_dt = None
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            flash('Invalid start date format. Use YYYY-MM-DD.', 'danger')
            start_date = ''
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            end_dt = end_dt + timedelta(days=1)
        except ValueError:
            flash('Invalid end date format. Use YYYY-MM-DD.', 'danger')
            end_date = ''
    
    # Get snapshots with filters
    if case_id or start_dt or end_dt or account_id or endpoint_type:
        snapshots = repo.get_snapshots_by_timerange(
            start_dt, end_dt, 
            case_id if case_id else None,
            account_id if account_id else None,
            endpoint_type if endpoint_type else None
        )
    else:
        snapshots = repo.get_all_snapshots()
    
    # Sort snapshots
    reverse = sort_dir == 'desc'
    if sort_by == 'timestamp':
        snapshots.sort(key=lambda s: s.timestamp or datetime.min, reverse=reverse)
    elif sort_by == 'case_id':
        snapshots.sort(key=lambda s: s.case_id or '', reverse=reverse)
    elif sort_by == 'account_id':
        snapshots.sort(key=lambda s: s.account_id or '', reverse=reverse)
    elif sort_by == 'endpoint_type':
        snapshots.sort(key=lambda s: s.endpoint_type or '', reverse=reverse)
    
    # Get filter options
    case_ids = repo.get_distinct_case_ids()
    account_ids = repo.get_distinct_account_ids()
    endpoint_types = repo.get_distinct_endpoint_types()
    case_labels = repo.get_case_labels()
    
    # Build account -> cases mapping for filter dropdown
    account_cases = {}
    for acc in account_ids:
        account_cases[acc] = [c["case_id"] for c in repo.get_case_labels_for_account(acc)]
    
    # Add accounts to each case label for cascading filter
    for case_label in case_labels:
        case_label["accounts"] = repo.get_account_ids_for_case(case_label["case_id"])
    
    return render_template('index.html', 
                         snapshots=snapshots,
                         case_id=case_id,
                         start_date=start_date,
                         end_date=end_date,
                         selected_account=account_id,
                         selected_endpoint=endpoint_type,
                         sort_by=sort_by,
                         sort_dir=sort_dir,
                         case_ids=case_ids,
                         account_ids=account_ids,
                         endpoint_types=endpoint_types,
                         case_labels=case_labels,
                         account_cases=account_cases)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login form."""
    if session.get('logged_in'):
        return redirect(url_for('web.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash(t('Web.Login.PleaseEnter', 'Please enter both username and password.'), 'danger')
            return render_template('login.html')
        
        if verify_credentials(username, password):
            login_user(username)
            lang = session.get('language', os.getenv('LANGUAGE', 'en'))
            flash(_t('Web.Nav.LoggedIn', 'Welcome, {username}!', language=lang).format(username=username), 'success')
            
            # Redirect to next parameter or index
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('web.index'))
        else:
            flash(t('Web.Login.InvalidCredentials', 'Invalid username or password.'), 'danger')
    
    return render_template('login.html')


@bp.route('/logout')
def logout():
    """Log out the current user."""
    logout_user()
    lang = session.get('language', os.getenv('LANGUAGE', 'en'))
    flash(_t('Web.Nav.LoggedOut', 'You have been logged out.', language=lang), 'info')
    return redirect(url_for('web.login'))


@bp.route('/delete', methods=['POST'])
@login_required
def delete():
    """Delete selected snapshots."""
    snapshot_ids = request.form.getlist('snapshot_ids')
    
    if not snapshot_ids:
        flash('No snapshots selected for deletion.', 'warning')
        return redirect(url_for('web.index'))
    
    try:
        int_ids = [int(sid) for sid in snapshot_ids]
    except ValueError:
        flash('Invalid snapshot IDs.', 'danger')
        return redirect(url_for('web.index'))
    
    deleted = repo.delete_snapshots(int_ids)
    flash(f'Deleted {deleted} snapshot(s).', 'success')
    
    return redirect(url_for('web.index'))


@bp.route('/compare', methods=['GET', 'POST'])
@login_required
def compare():
    """Compare two selected snapshots."""
    snapshot1_id = request.args.get('snapshot1_id', '').strip()
    snapshot2_id = request.args.get('snapshot2_id', '').strip()
    
    if not snapshot1_id or not snapshot2_id:
        flash('Please select two snapshots to compare.', 'warning')
        return redirect(url_for('web.index'))
    
    if snapshot1_id == snapshot2_id:
        flash('Please select two different snapshots.', 'warning')
        return redirect(url_for('web.index'))
    
    # Get both snapshots
    try:
        s1_id = int(snapshot1_id)
        s2_id = int(snapshot2_id)
    except ValueError:
        flash('Invalid snapshot IDs.', 'danger')
        return redirect(url_for('web.index'))
    
    s1 = repo.get_snapshot_by_id(s1_id)
    s2 = repo.get_snapshot_by_id(s2_id)
    
    if not s1:
        flash(f'Snapshot {snapshot1_id} not found.', 'danger')
        return redirect(url_for('web.index'))
    if not s2:
        flash(f'Snapshot {snapshot2_id} not found.', 'danger')
        return redirect(url_for('web.index'))
    
    # Ensure same case for comparison
    if s1.case_id != s2.case_id:
        flash('Can only compare snapshots for the same case.', 'warning')
        return redirect(url_for('web.index'))
    
    # Determine which is earlier/later
    earlier, later = (s1, s2) if s1.timestamp <= s2.timestamp else (s2, s1)
    
    # Build comparison data
    comparison = build_comparison(earlier, later)
    
    return render_template('compare.html',
                         snapshot1=earlier,
                         snapshot2=later,
                         comparison=comparison,
                         case_id=s1.case_id)


def build_comparison(s1, s2):
    """Build comparison data between two snapshots.
    
    Args:
        s1: First snapshot
        s2: Second snapshot
        
    Returns:
        List of comparison items with field names and values
    """
    from datetime import datetime, timezone
    
    def format_dt(value):
        if not value:
            return ""
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            local = value.astimezone()
            return local.strftime("%Y-%b-%d %H:%M")
        return str(value)
    
    comparison = []
    
    comparison.append({
        'field': 'case_id',
        'old_value': s1.case_id,
        'new_value': s2.case_id,
        'changed': s1.case_id != s2.case_id
    })
    comparison.append({
        'field': 'account_id',
        'old_value': s1.account_id,
        'new_value': s2.account_id,
        'changed': s1.account_id != s2.account_id
    })
    comparison.append({
        'field': 'endpoint_type',
        'old_value': s1.endpoint_type,
        'new_value': s2.endpoint_type,
        'changed': s1.endpoint_type != s2.endpoint_type
    })
    comparison.append({
        'field': 'timestamp',
        'old_value': format_dt(s1.timestamp) if s1.timestamp else None,
        'new_value': format_dt(s2.timestamp) if s2.timestamp else None,
        'changed': s1.timestamp != s2.timestamp
    })
    
    p1 = s1.parsed_data or {}
    p2 = s2.parsed_data or {}
    
    if p1 or p2:
        all_keys = set(p1.keys()) | set(p2.keys())
        for key in sorted(all_keys):
            val1 = p1.get(key)
            val2 = p2.get(key)
            
            if key == "questions" and s1.endpoint_type == "questions":
                old_qs = val1 if isinstance(val1, list) else []
                new_qs = val2 if isinstance(val2, list) else []
                
                old_by_id = {q.get("id"): q for q in old_qs if isinstance(q, dict) and q.get("id")}
                new_by_id = {q.get("id"): q for q in new_qs if isinstance(q, dict) and q.get("id")}
                
                new_ids = set(new_by_id.keys()) - set(old_by_id.keys())
                for qid in new_ids:
                    q = new_by_id[qid]
                    comparison.append({
                        'field': f'question:{qid}',
                        'old_value': None,
                        'new_value': q,
                        'changed': True,
                        'is_question': True
                    })
                
                removed_ids = set(old_by_id.keys()) - set(new_by_id.keys())
                for qid in removed_ids:
                    q = old_by_id[qid]
                    comparison.append({
                        'field': f'question:{qid}',
                        'old_value': q,
                        'new_value': None,
                        'changed': True,
                        'is_question': True
                    })

                # Field-level comparison for questions present in both snapshots
                common_ids = set(old_by_id.keys()) & set(new_by_id.keys())
                question_fields = ["title", "status", "status_label", "body", "sentTime", "answer", "responseTime"]
                for qid in sorted(common_ids):
                    old_q = old_by_id[qid]
                    new_q = new_by_id[qid]
                    for field_name in question_fields:
                        old_val = old_q.get(field_name)
                        new_val = new_q.get(field_name)
                        if old_val != new_val:
                            item = {
                                'field': f'question:{qid}:{field_name}',
                                'old_value': old_val,
                                'new_value': new_val,
                                'changed': True,
                                'is_question_field': True,
                                'question_id': qid,
                                'field_name': field_name,
                            }
                            # Add translated labels for status_label
                            if field_name == "status_label":
                                item['old_label'] = _t(f'Cases.Question.Statuses.{old_val}', str(old_val) if old_val else '(empty)')
                                item['new_label'] = _t(f'Cases.Question.Statuses.{new_val}', str(new_val) if new_val else '(empty)')
                            # Add translated labels for title
                            elif field_name == "title":
                                item['old_label'] = _t(f'Cases.Question.Titles.{old_val}', str(old_val) if old_val else '(empty)')
                                item['new_label'] = _t(f'Cases.Question.Titles.{new_val}', str(new_val) if new_val else '(empty)')
                            comparison.append(item)
            else:
                changed = False
                if isinstance(val1, list) and isinstance(val2, list):
                    changed = len(val1) != len(val2)
                    if not changed:
                        changed = any(str(a) != str(b) for a, b in zip(val1, val2))
                else:
                    changed = val1 != val2
                
                if key not in ["questions", "count", "totalResults"]:
                    comparison.append({
                        'field': key,
                        'old_value': val1,
                        'new_value': val2,
                        'changed': changed
                    })
    
    return comparison
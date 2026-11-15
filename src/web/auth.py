"""Authentication module for Flask web application."""

import os
from functools import wraps
from flask import session, redirect, url_for, flash, request
from src.config import load_credentials


def verify_credentials(username: str, password: str) -> bool:
    """Verify credentials against credentials.json.
    
    Args:
        username: Username to verify
        password: Password to verify
        
    Returns:
        True if credentials match any account in credentials.json
    """
    try:
        creds = load_credentials()
        account_names = list(creds.keys())
        
        for account in account_names:
            if account in creds:
                account_creds = creds[account]
                if account_creds.get('username') == username:
                    if account_creds.get('password') == password:
                        return True
        return False
    except Exception:
        return False


def login_required(f):
    """Decorator to require login for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('web.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def login_user(username: str):
    """Log in a user by setting session variables.
    
    Args:
        username: The username that was authenticated
    """
    session['logged_in'] = True
    session['username'] = username
    # Initialize language from .env if not set
    if 'language' not in session:
        session['language'] = os.getenv('LANGUAGE', 'en')


def logout_user():
    """Log out the current user by clearing session variables."""
    # Preserve language setting on logout
    saved_lang = session.get('language', 'en')
    session.clear()
    # Restore language for re-login
    session['language'] = saved_lang
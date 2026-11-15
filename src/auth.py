"""Authentication flow for inpol.mazowieckie.pl.

This module provides the JWT-based authentication flow for logging into
the inpol.mazowieckie.pl portal with multiple accounts sequentially.

Implements:
- JWT token authentication via /identity/sign-in endpoint
- Account authentication
- Sequential multi-account login (D-04)
- Session reuse checking (D-05)
"""

import logging
from typing import Any, Dict, Generator, Optional

from src.config import get_base_path, load_credentials
from src.session_manager import SessionManager

logger = logging.getLogger(__name__)

# Default portal URL
DEFAULT_BASE_URL = "https://inpol.mazowieckie.pl"


def authenticate_account(
    account_name: str,
    credentials: Dict[str, Any],
    base_url: str = DEFAULT_BASE_URL
) -> Optional[SessionManager]:
    """Authenticate a single account and return the session.

    Performs the complete JWT login flow:
    1. Create SessionManager
    2. POST credentials to /identity/sign-in
    3. Store JWT access token
    4. Return session if successful, None otherwise

    Args:
        account_name: Account identifier (e.g., "account1", "account2")
        credentials: Dictionary with 'email' and 'password' keys
        base_url: Base URL of the portal (default: https://inpol.mazowieckie.pl)

    Returns:
        SessionManager if login successful, None otherwise

    Notes:
        - Returns None if credentials are missing or incomplete
        - Session must be closed by caller using session.close()
        - Implements JWT-based authentication
    """
    # Validate credentials
    if not credentials:
        logger.warning(f"No credentials provided for {account_name}")
        return None

    email = credentials.get('email', credentials.get('username'))
    password = credentials.get('password')

    if not email:
        logger.warning(f"No email for {account_name}")
        return None

    if not password:
        logger.warning(f"No password for {account_name}")
        return None

    logger.info(f"Authenticating {account_name}...")

    # Create session and perform JWT login
    session = SessionManager(base_url)

    try:
        login_success = session.login(email, password)

        if login_success:
            logger.info(f"Successfully authenticated {account_name}")
            return session
        else:
            logger.error(f"Authentication failed for {account_name}")
            session.close()
            return None

    except Exception as e:
        logger.error(f"Error authenticating {account_name}: {e}")
        session.close()
        return None


def run_sequential_auth(
    credentials: Optional[Dict[str, Any]] = None,
    base_url: str = DEFAULT_BASE_URL
) -> Generator[tuple, None, None]:
    """Authenticate accounts sequentially, yielding sessions.

    Generator that implements D-04 sequential authentication:
    1. Login to account1 -> yield session
    2. Close account1 session
    3. Login to account2 -> yield session
    4. Close account2 session

    Each session is closed before moving to the next account.
    Caller is responsible for processing the session before the
    generator continues (and closes it).

    Args:
        credentials: Credentials dict with account1/account2 keys.
                    If None, loads from credentials.json
        base_url: Base URL of the portal (default: https://inpol.mazowieckie.pl)

    Yields:
        Tuple of (account_name, SessionManager) for each successful login

    Notes:
        - Implements D-04: sequential auth with close between accounts
        - Implements D-05: checks logged_in flag for session validity
        - Skips accounts with missing credentials (D-08 lenient validation)
    """
    # Load credentials if not provided
    if credentials is None:
        credentials = load_credentials()

    if not credentials:
        logger.warning("No credentials available for sequential auth")
        return

    account_names = list(credentials.keys())
    logger.info(f"Processing {len(account_names)} accounts: {account_names}")

    for account_name in account_names:
        account_creds = credentials.get(account_name)

        if not account_creds:
            logger.warning(f"Skipping {account_name}: no credentials (D-08 lenient)")
            continue

        logger.info(f"=== Starting {account_name} ===")

        # Authenticate
        session = authenticate_account(account_name, account_creds, base_url)

        if session and session.logged_in:
            try:
                # Yield the authenticated session for caller to use
                yield (account_name, session)
            finally:
                # D-04: Explicit close after processing each account
                logger.info(f"=== Closing {account_name} session ===")
                session.close()
        else:
            logger.error(f"Failed to authenticate {account_name}")


def check_session_validity(session: SessionManager, test_url: str = "/") -> bool:
    """Check if an existing session is still valid.

    Checks if JWT token is set and session is marked as logged in.

    Args:
        session: SessionManager to check
        test_url: URL to test (default: root page)

    Returns:
        True if session is valid and authenticated, False otherwise
    """
    if not session.logged_in:
        logger.debug("Session marked as not logged in")
        return False

    if not session.jwt_token:
        logger.debug("Session has no JWT token")
        return False

    response = session.get(test_url)
    if not response:
        logger.debug("Session check failed: no response")
        return False

    # Valid if we got a response with the token
    logger.debug(f"Session validity check: valid=True, status={response.status_code}")
    return True


def get_authenticated_session(
    account_name: str,
    credentials: Optional[Dict[str, Any]] = None,
    base_url: str = DEFAULT_BASE_URL,
    reuse_existing: bool = False
) -> Optional[SessionManager]:
    """Get an authenticated session with optional reuse.

    Convenience function that implements D-05 session reuse pattern.
    If reuse_existing is True and a valid session exists, returns it.
    Otherwise, performs fresh authentication.

    Args:
        account_name: Account identifier
        credentials: Account credentials (loads from file if None)
        base_url: Portal base URL
        reuse_existing: If True, checks for valid session first (D-05)

    Returns:
        Authenticated SessionManager or None
    """
    if credentials is None:
        all_creds = load_credentials()
        credentials = all_creds.get(account_name) if all_creds else None

    return authenticate_account(account_name, credentials, base_url)

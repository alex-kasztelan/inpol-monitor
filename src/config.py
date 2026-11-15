"""Configuration and credential loading for Inpol Monitor.

This module provides functions to load credentials from JSON files
and environment variables from .env files, with lenient validation
and Windows CRLF handling.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def get_base_path() -> Path:
    """Get the base path of the project (parent of src/).

    Resolves paths relative to script location, not cwd.
    This ensures the script works when run from any directory
    (e.g., Windows Task Scheduler).

    Returns:
        Path: Absolute path to project root directory
    """
    return Path(__file__).resolve().parent.parent


def load_credentials(path: Optional[str] = None) -> Dict[str, Any]:
    """Load credentials from JSON file with lenient validation.

    Args:
        path: Path to credentials.json file. If None, uses default
              location (project root / credentials.json).

    Returns:
        Dictionary with credential data. Empty dict if file not found.

    Notes:
        - Strips whitespace from all credential values (Windows CRLF handling)
        - Warns but continues on missing credentials (lenient validation D-08)
        - Paths are resolved relative to script location, not cwd
    """
    if path is None:
        path = str(get_base_path() / "credentials.json")

    credentials_path = Path(path)

    # Handle relative paths - resolve relative to script location
    if not credentials_path.is_absolute():
        credentials_path = get_base_path() / path

    if not credentials_path.exists():
        logger.warning(f"Credentials file not found: {credentials_path}")
        return {}

    try:
        with open(credentials_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in credentials file: {e}")
        return {}
    except IOError as e:
        logger.error(f"Error reading credentials file: {e}")
        return {}

    # Strip whitespace from all string values (Windows CRLF handling)
    data = _strip_whitespace(data)

    # Lenient validation: warn but don't fail
    _validate_credentials(data)

    return data


def _strip_whitespace(data: Any) -> Any:
    """Recursively strip whitespace from all string values in data structure.

    Args:
        data: Any data structure (dict, list, or primitive)

    Returns:
        Cleaned data structure with whitespace stripped from strings
    """
    if isinstance(data, dict):
        return {k: _strip_whitespace(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_strip_whitespace(item) for item in data]
    elif isinstance(data, str):
        return data.strip()
    else:
        return data


def _validate_credentials(data: Dict[str, Any]) -> None:
    """Validate credentials structure with lenient validation.

    Warns but continues if credentials are missing or incomplete.
    This is useful for testing one account at a time.

    Args:
        data: Credential data dictionary
    """
    account_names = list(data.keys())
    for account in account_names:
        if not isinstance(data[account], dict):
            logger.warning(f"Invalid credentials format for {account}")
            continue

        if 'username' not in data[account]:
            logger.warning(f"No username for {account}")

        if 'password' not in data[account]:
            logger.warning(f"No password for {account}")


def get_accounts() -> List[str]:
    """Get list of account names from credentials.json.
    
    Returns:
        List of account keys (e.g., ["account1", "account2"] or ["john", "mary"])
    """
    data = load_credentials()
    return list(data.keys())


def load_env(path: Optional[str] = None) -> bool:
    """Load environment variables from .env file using python-dotenv.

    Args:
        path: Path to .env file. If None, uses default location
              (project root / .env).

    Returns:
        True if .env file was loaded successfully, False otherwise.

    Notes:
        - Paths are resolved relative to script location, not cwd
        - Uses python-dotenv for standard .env file parsing
    """
    if path is None:
        path = str(get_base_path() / ".env")

    env_path = Path(path)

    # Handle relative paths - resolve relative to script location
    if not env_path.is_absolute():
        env_path = get_base_path() / path

    if not env_path.exists():
        logger.info(f".env file not found: {env_path}")
        return False

    try:
        result = load_dotenv(dotenv_path=str(env_path))
        if result:
            logger.debug(f"Loaded environment from: {env_path}")
        return result
    except Exception as e:
        logger.error(f"Error loading .env file: {e}")
        return False


def get_config(key: str, default: Any = None) -> Any:
    """Get a configuration value from environment variables.

    Args:
        key: Environment variable name
        default: Default value if not found

    Returns:
        Configuration value or default
    """
    return os.getenv(key, default)


def get_json_logging_enabled() -> bool:
    """Check if JSON response logging is enabled.

    Returns:
        True if JSON_LOGGING_ENABLED environment variable is set to "true" (case-insensitive),
        False otherwise (default behavior when unset or invalid)
    """
    return os.getenv("JSON_LOGGING_ENABLED", "false").lower() == "true"


def get_authorized_telegram_users() -> list:
    """Get list of authorized Telegram user IDs.

    Returns:
        List of authorized user IDs (as strings). Empty list if not configured.
        Falls back to TELEGRAM_USER_ID if AUTHORIZED_TELEGRAM_USERS is not set.
    """
    users = os.getenv("AUTHORIZED_TELEGRAM_USERS", "").strip()
    if not users:
        # Fallback to single user from TELEGRAM_USER_ID
        fallback = os.getenv("TELEGRAM_USER_ID", "").strip()
        if fallback:
            return [fallback]
        return []
    # Split by comma and clean up
    return [u.strip() for u in users.split(",") if u.strip()]


def get_email_enabled() -> bool:
    """Check if email notifications are enabled.

    Returns:
        True if EMAIL_ENABLED environment variable is set to "true" (case-insensitive),
        False otherwise (default behavior when unset or invalid)
    """
    return os.getenv("EMAIL_ENABLED", "false").lower() == "true"


def get_smtp_config() -> Dict[str, Any]:
    """Get SMTP configuration from environment variables.

    Returns:
        Dictionary with SMTP settings: host, port, username, password, from_addr, to_addr.
        Empty values for missing configuration.
    """
    return {
        "host": os.getenv("SMTP_SERVER", ""),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "username": os.getenv("SMTP_USERNAME", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from_addr": os.getenv("EMAIL_FROM", ""),
        "to_addr": os.getenv("EMAIL_TO", ""),
    }

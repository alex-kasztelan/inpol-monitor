"""Telegram notification layer for Inpol Monitor.

This module provides Telegram integration using aiogram 3.x for
sending formatted change notifications and error reports.
"""

import html
import logging
import os
from datetime import datetime, timezone
from typing import List, Any, Callable, Optional

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
from src.models import Change, ChangeType
from src.storage import SnapshotRepository
from src.config import get_email_enabled, get_smtp_config, get_authorized_telegram_users
from src.email_notifier import EmailNotifier

try:
    from src.localization import t as _t, get_status_label, get_question_title, get_question_status
    _USE_L10N = True
except ImportError:
    _USE_L10N = False
    def _t(key, default=None, language=None):
        return default or key

logger = logging.getLogger(__name__)


def get_notification_language() -> str:
    """Get language for notifications (separate from web UI language).
    
    Returns:
        Language code for notifications (defaults to 'en')
    """
    return os.getenv("NOTIFICATION_LANGUAGE", "en")


def _tn(key: str, default: str = None) -> str:
    """Get translated string using notification language.
    
    Args:
        key: Translation key (dot-separated path)
        default: Default value if key not found
    
    Returns:
        Translated string in notification language
    """
    if _USE_L10N:
        return _t(key, default, language=get_notification_language())
    return default or key

# Store env values in a dict for easier mocking in tests
_env_values = {}


def get_env(key: str, default: str = None) -> str:
    """Get environment variable value.

    Args:
        key: Environment variable key
        default: Default value if key is not found

    Returns:
        Environment variable value or default
    """
    logger.debug(f"Getting env var {key}. _env_values has {len(_env_values)} items. os.environ has {len(os.environ)} items.")
    logger.debug(f"_env_values contains '{key}': {key in _env_values}")
    logger.debug(f"os.environ contains '{key}': {key in os.environ}")
    
    # First check in our cached env values (for test mocking)
    if key in _env_values:
        value = _env_values[key]
        logger.debug(f"Found in _env_values: {value}")
    else:
        # Fall back to actual environment variables
        value = os.environ.get(key, default)
        logger.debug(f"Found in os.environ: {value}")
    
    logger.debug(f"get_env({key}) = {value} (default={default})")
    return value


def load_env_values():
    """Load environment variables from .env file.

    This function should be called before any notifier is created
    to ensure tests can mock the environment.
    """
    load_dotenv()
    # Copy env values to _env_values dict
    global _env_values
    _env_values = dict(os.environ)


# Load environment variables
load_dotenv()
logger.debug(f"Environment variables loaded: TELEGRAM_BOT_TOKEN={'set' if os.getenv('TELEGRAM_BOT_TOKEN') else 'not set'}, TELEGRAM_USER_ID={os.getenv('TELEGRAM_USER_ID')}")
logger.debug(f"All os.environ keys containing 'TELEGRAM': {[k for k in os.environ.keys() if 'TELEGRAM' in k]}")


def _resolve_chat_id(user_id: str):
    """Resolve user_id string to chat_id (int or string with @).
    
    Handles: numeric IDs, @usernames, bot names, and plain usernames.
    
    Args:
        user_id: Can be numeric string, @username, or bot name
        
    Returns:
        int for numeric IDs, string for @username or bot name
    """
    user_id = user_id.strip()
    if user_id.startswith("bot") or user_id.startswith("@"):
        return user_id
    # Check if purely numeric
    if user_id.isdigit():
        return int(user_id)
    # Assume username without @ - prepend it
    return f"@{user_id}"


class MockBot:
    """Mock Bot for testing TelegramNotifier."""

    def __init__(self, token: str):
        """Initialize mock bot.

        Args:
            token: Bot token (not validated)
        """
        self.token = token
        self._messages = []

    def send_message(self, chat_id: int, text: str, parse_mode=None):
        """Send a test message.

        Args:
            chat_id: Telegram user ID
            text: Message text
            parse_mode: Parse mode (HTML or Markdown)
        """
        self._messages.append({"chat_id": chat_id, "text": text, "parse_mode": parse_mode})
        return self

    def send_message_async(self, chat_id: int, text: str, parse_mode=None):
        """Async send message (mock).

        Args:
            chat_id: Telegram user ID
            text: Message text
            parse_mode: Parse mode (HTML or Markdown)
        """
        self.send_message(chat_id, text, parse_mode)
        return self


class ChangeNotifier:
    """Abstract base class for notification handlers."""

    def __init__(self):
        """Initialize notification handler."""
        pass

    def send_notification(self, account_id: str, case_id: str, error: Exception) -> None:
        """Base method for sending notifications.

        Args:
            account_id: Account identifier
            case_id: Case identifier
            error: Exception that triggered the notification
        """
        logger.error(f"Notification not implemented for {type(self).__name__}")

    def format_message(self, message_type: str, data: dict) -> str:
        """Base method for formatting notification messages.

        Args:
            message_type: Type of message (change or error)
            data: Data to format in message

        Returns:
            Formatted message string
        """
        return f"[Not implemented: {message_type}]"


class CaseInfo:
    """Container for case information used in notifications."""

    def __init__(
        self,
        case_id: str,
        account_id: str,
        case_type: str,
        person_first: str,
        changes: List[Change],
        total_changes: int,
        account_login: str = "",
        case_url: str = "",
        error_message: str = None,
        status: str = ""
    ):
        self.case_id = case_id
        self.account_id = account_id
        self.account_login = account_login
        self.case_type = case_type
        self.person_first = person_first
        self.changes = changes
        self.total_changes = total_changes
        self.case_url = case_url
        self.error_message = error_message
        self.status = status


class TelegramNotifier(ChangeNotifier):
    """Telegram notification handler using aiogram 3.x.

    Sends formatted Markdown messages for:
    - Change notifications (batched per account)
    - Error notifications
    """

    def __init__(self, token: str, storage: SnapshotRepository = None, base_url: str = "https://inpol.mazowieckie.pl"):
        """Initialize Telegram notifier.

        Args:
            token: Telegram bot token from .env
            storage: Optional SnapshotRepository for error context
            base_url: Base URL for building case hyperlinks
        """
        self.token = token
        self.storage = storage
        self.base_url = base_url
        self.message_count = 0
        self._cases_to_notify = []

        # Initialize email notifier if enabled
        try:
            self.email_enabled = get_email_enabled()
            logger.info(f"EMAIL_ENABLED check: {self.email_enabled}")
            if self.email_enabled:
                smtp_config = get_smtp_config()
                logger.info(f"SMTP config: {smtp_config}")
                self.email_notifier = EmailNotifier(smtp_config)
                logger.info(f"Email notifier enabled: {self.email_notifier.enabled}")
            else:
                self.email_notifier = None
        except Exception as e:
            logger.warning(f"Failed to initialize email notifier: {e}")
            self.email_enabled = False
            self.email_notifier = None

        # Initialize aiogram Bot instance (aiogram 3.x)
        # For testing, we use a mock that doesn't validate tokens
        if token.startswith("test:"):
            # Use mock for testing
            self.bot = MockBot(token=token)
        else:
            # Use real aiogram Bot for production
            from aiogram import Bot
            self.bot = Bot(token=token)

        # Store messages for testing
        self._messages_sent = []

        logger.info(f"TelegramNotifier initialized with token starting with {token[:8]}...")

    def on_change(
        self,
        account_id: str,
        account_login: str,
        case_id: str,
        changes: List[Change],
        case_type: str = "",
        person_first: str = "",
        case_url: str = "",
        error_message: str = None,
        status: str = ""
    ) -> None:
        """Callback invoked when changes are detected.

        Accumulates all cases and sends a single notification for all of them.

        Args:
            account_id: Account identifier (e.g., "account1")
            account_login: Account login email (e.g., "karol@test.org")
            case_id: Case identifier
            changes: List of detected changes for this case
            case_type: Type of case
            person_first: First name of person
            case_url: URL to case JSON endpoint
            status: Case status code
        """
        # Build case URL if not provided
        if not case_url:
            case_url = f"{self.base_url}/home/cases/{case_id}"

        case_info = CaseInfo(
            case_id=case_id,
            account_id=account_id,
            case_type=case_type,
            person_first=person_first,
            changes=changes,
            total_changes=len(changes),
            account_login=account_login,
            case_url=case_url,
            error_message=error_message,
            status=status
        )
        self._cases_to_notify.append(case_info)

    def send_all_notifications(self) -> None:
        """Send a single notification for all accumulated cases."""
        if not self._cases_to_notify:
            return

        # Build single message for all cases
        message = self._build_single_message(self._cases_to_notify)

        # Store message for testing
        self._messages_sent.append({
            "type": "change",
            "cases": [c.case_id for c in self._cases_to_notify],
            "message": message
        })

        # Send to Telegram - all authorized users
        target_users = get_authorized_telegram_users()
        if not target_users:
            target_users = [get_env("TELEGRAM_USER_ID", "1234567890")]

        from aiogram.enums import ParseMode
        import asyncio
        import concurrent.futures

        # Collect all results first
        results = []
        for user_id in target_users:
            try:
                chat_id = _resolve_chat_id(user_id)
                results.append((user_id, chat_id, None))
            except Exception as e:
                results.append((user_id, None, e))
        
        # Send all messages in a single coroutine
        if not isinstance(self.bot, MockBot):
            async def _send_all():
                for user_id, chat_id, err in results:
                    if err:
                        logger.error(f"Failed to send to {user_id}: {err}")
                        continue
                    try:
                        await self.bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.HTML)
                        logger.info(f"Combined notification sent for {len(self._cases_to_notify)} cases to user {user_id}")
                    except Exception as e:
                        logger.error(f"Failed to send combined notification to {user_id}: {e}")

            asyncio.run(_send_all())
        else:
            # Mock bot - send synchronously
            for user_id, chat_id, err in results:
                if err:
                    logger.error(f"Failed to send to {user_id}: {err}")
                    continue
                try:
                    self.bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")
                    logger.info(f"Combined notification sent for {len(self._cases_to_notify)} cases to user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to send combined notification to {user_id}: {e}")

        # Send email when enabled - single combined email (like Telegram)
        if self.email_enabled and self.email_notifier:
            logger.info(f"Email enabled, sending combined email for {len(self._cases_to_notify)} cases")

            # Build combined email content (same format as Telegram)
            html_body = self._build_single_message(self._cases_to_notify)

            # Collect account logins for email
            account_logins = []
            for c in self._cases_to_notify:
                login = c.account_login if c.account_login else c.account_id
                if login and login not in account_logins:
                    account_logins.append(login)

            # Send single email with summary
            result = self.email_notifier.send_combined_notification(
                account_logins=account_logins,
                cases=self._cases_to_notify,
                html_body=html_body,
            )
            logger.info(f"Combined email result: {result}")

        # Clear accumulated cases after sending
        self._cases_to_notify = []

    def on_error(self, account_id: str, case_id: str, error: Exception, error_type: str) -> None:
        """Callback invoked when an error occurs.

        Args:
            account_id: Account identifier
            case_id: Case identifier
            error: Exception that occurred
            error_type: Type of error
        """
        self.send_error_notification_sync(account_id, case_id, error, error_type)

    def reset(self) -> None:
        """Reset the notification aggregator for a new check cycle.

        Clears accumulated changes before a new check cycle.
        """
        self._cases_to_notify = []
        self._messages_sent = []

    async def close(self) -> None:
        """Close the bot session and clean up resources."""
        if hasattr(self.bot, 'session') and self.bot.session:
            await self.bot.session.close()

    async def send_change_notification(self, account_id: str, case_id: str, changes: List[Change], total_changes: int, case_type: str = "", person_first: str = "", status: str = "") -> None:
        """Send formatted change notification to Telegram.
        
        Args:
            account_id: Account identifier
            case_id: Case identifier
            changes: List of detected changes
            total_changes: Total number of changes
            case_type: Type of case (optional)
            person_first: First name of person (optional)
            status: Case status code (optional)
        """
        # Build formatted message
        message = self._build_change_message(account_id, case_id, changes, total_changes, case_type, person_first, status)
        
        # Always store message for testing
        self._messages_sent.append({
            "type": "change",
            "account_id": account_id,
            "case_id": case_id,
            "message": message
        })
        
        # Send to Telegram - all authorized users
        target_users = get_authorized_telegram_users()
        if not target_users:
            target_users = [get_env("TELEGRAM_USER_ID", "1234567890")]
        
        from aiogram.enums import ParseMode
        
        for user_id in target_users:
            try:
                chat_id = _resolve_chat_id(user_id)
                
                logger.debug(f"Attempting to send message to chat_id: {chat_id} (type: {type(chat_id)})")
                await self.bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.HTML)
                logger.info(f"Change notification sent for {case_id}: {total_changes} changes to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send change notification to {user_id}: {e}")

    def send_change_notification_sync(self, account_id: str, case_id: str, changes: List[Change], total_changes: int, case_type: str = "", person_first: str = "", status: str = "") -> None:
        """Synchronous wrapper for send_change_notification for backward compatibility.

        Args:
            account_id: Account identifier
            case_id: Case identifier
            changes: List of detected changes
            total_changes: Total number of changes
            case_type: Type of case (optional)
            person_first: First name of person (optional)
            status: Case status code (optional)
        """
        import asyncio
        telegram_success = True
        try:
            asyncio.run(self.send_change_notification(account_id, case_id, changes, total_changes, case_type, person_first, status))
        except Exception as e:
            logger.error(f"Failed to send change notification (sync): {e}")
            telegram_success = False

        # Send email when enabled - either as fallback (Telegram failed) or always (alternative mode)
        if self.email_enabled and self.email_notifier:
            # If EMAIL_ENABLED=true, always send email. If Telegram failed, always send fallback.
            # Current behavior: always send email when enabled (not just fallback)
            self.email_notifier.send_change_notification(
                account_id=account_id,
                case_id=case_id,
                case_type=case_type,
                person_first=person_first,
                changes=[{"type": str(c.type), "old_value": c.old_value, "new_value": c.new_value, "description": c.description} for c in changes],
                status=status
            )
            if not telegram_success:
                logger.info(f"Email fallback sent for case {case_id}")
            else:
                logger.info(f"Email notification sent for case {case_id}")

    async def send_error_notification(self, account_id: str, case_id: str, error: Exception, error_type: str) -> None:
        """Send formatted error notification to Telegram.
        
        Args:
            account_id: Account identifier
            case_id: Case identifier
            error: Exception that occurred
            error_type: Type of error
        """
        # Build error message
        message = self._build_error_message(account_id, case_id, error, error_type)
        
        # Store message for testing
        self._messages_sent.append({
            "type": "error",
            "account_id": account_id,
            "case_id": case_id,
            "message": message
        })
        
        # Send to Telegram - all authorized users
        target_users = get_authorized_telegram_users()
        if not target_users:
            target_users = [get_env("TELEGRAM_USER_ID", "1234567890")]
        
        for user_id in target_users:
            try:
                chat_id = _resolve_chat_id(user_id)
               
                logger.debug(f"Attempting to send message to chat_id: {chat_id} (type: {type(chat_id)})")
                await self.bot.send_message(chat_id=chat_id, text=message)
                logger.info(f"Error notification sent for {case_id}: {error_type} to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send error notification to {user_id}: {e}")
        
        self._send_error_fallback_email(account_id, case_id, str(error), error_type)

    def send_error_notification_sync(self, account_id: str, case_id: str, error: Exception, error_type: str) -> None:
        """Synchronous wrapper for send_error_notification for backward compatibility.
        
        Args:
            account_id: Account identifier
            case_id: Case identifier
            error: Exception that occurred
            error_type: Type of error
        """
        import asyncio
        telegram_success = True
        try:
            asyncio.run(self.send_error_notification(account_id, case_id, error, error_type))
        except Exception as e:
            logger.error(f"Failed to send error notification (sync): {e}")
            telegram_success = False

        if self.email_enabled and self.email_notifier:
            self._send_error_fallback_email(account_id, case_id, str(error), error_type)
            if not telegram_success:
                logger.info(f"Error email fallback sent for case {case_id}")
            else:
                logger.info(f"Error email notification sent for case {case_id}")

    def _build_change_message(self, account_id: str, case_id: str, changes: List[Change], total_changes: int, case_type: str = "", person_first: str = "", status: str = "") -> str:
        """Build HTML change notification message.

        Format uses HTML tags for Telegram compatibility.

        Args:
            account_id: Account identifier
            case_id: Case identifier
            changes: List of detected changes
            total_changes: Total number of changes
            case_type: Type of case (optional)
            person_first: First name of person (optional)
            status: Case status code (optional)

        Returns:
            Formatted HTML message string
        """
        def format_dt(value):
            if not value:
                return ""
            if isinstance(value, datetime):
                return value.strftime("%Y-%b-%d %H:%M")
            return str(value)
        
        case_type_html = f"<b>{case_type}</b>" if case_type else ""
        person_html = f"<b>{person_first}</b>" if person_first else ""
        
        header_parts = [f"[{case_id}]"]
        if case_type_html:
            header_parts.append(case_type_html)
        if person_html:
            header_parts.append(person_html)
        header = " / ".join(header_parts)
        
        message = f"{header} Changes Detected in {account_id} account\n"
        message += f"-----------------------------------\n"
        message += f"Summary: {total_changes} change(s)\n\n"
        message += f"Case Details:\n"

        if not changes:
            message += f"  (no changes)\n"
        for change in changes:
            if change.type == ChangeType.STATUS:
                message += f"  * Status: {change.old_value} -> {change.new_value}\n"
            elif change.type == ChangeType.NEW_DOCUMENT:
                message += f"  * New document: {change.new_value}\n"
            elif change.type == ChangeType.UPDATED_AT_CHANGE:
                old_val = format_dt(change.old_value)
                new_val = format_dt(change.new_value)
                message += f"  * Date change: {old_val} -> {new_val}\n"
            elif change.type == ChangeType.QUESTION_COUNT_CHANGE:
                message += f"  * {change.description}\n"
            elif change.type == ChangeType.NEW_QUESTION_DETAIL:
                message += f"  * {change.description}\n"
            elif change.type == ChangeType.QUESTION_ASKED:
                message += f"  * {change.description}\n"
            elif change.type == ChangeType.QUESTION_ANSWERED:
                message += f"  * {change.description}\n"
            else:
                message += f"  * {change.description}\n"

        message += f"\nCase ID: {case_id}\n"

        return message

    def _build_single_message(self, cases: List[CaseInfo]) -> str:
        """Build a single combined notification message for all cases.

        Args:
            cases: List of CaseInfo objects

        Returns:
            Formatted message string
        """
        from src.models import QUESTION_TITLES, QUESTION_STATUSES
        
        def format_dt(value):
            if not value:
                return ""
            if isinstance(value, datetime):
                if value.tzinfo is None:
                    value = value.replace(tzinfo=timezone.utc)
                local = value.astimezone()
                return local.strftime("%Y-%b-%d %H:%M")
            return str(value)
        
        def get_question_status_label(status_id):
            return QUESTION_STATUSES.get(str(status_id), f"Unknown ({status_id})")
        
        message = "Summary:\n"

        for case in cases:
            account_display = case.account_login if case.account_login else case.account_id
            if case.error_message:
                message += f"Unable to access the case <a href=\"{html.escape(case.case_url)}\">{html.escape(case.case_id)}</a> (<b>{html.escape(account_display)}</b>): {html.escape(case.error_message)}\n"
            else:
                message += f"<b>{case.total_changes}</b> change(s) in <a href=\"{html.escape(case.case_url)}\">{html.escape(case.case_id)}</a> (<b>{html.escape(account_display)}</b>)\n"

        message += "\nCase Details:\n"

        for case in cases:
            message += f"Case ID: {html.escape(case.case_id)}\n"
            if case.error_message:
                message += f"Error: {html.escape(case.error_message)}\n"
                message += "\n"
                continue
            message += f"Type: <b>{html.escape(case.case_type)}</b>\n"
            # Add status with translation using notification language
            status_label = _tn(f'Cases.States.{case.status}', case.status) if case.status else ""
            if case.status:
                message += f"Status: <b>{html.escape(case.status)} - {html.escape(status_label)}</b>\n"
            message += f"Person: <b>{html.escape(case.person_first)}</b>\n"

            if not case.changes:
                message += "(no changes)\n"
            else:
                for change in case.changes:
                    if change.type == ChangeType.STATUS:
                        message += f"* Status: {html.escape(change.old_value)} -> {html.escape(change.new_value)}\n"
                    elif change.type == ChangeType.NEW_DOCUMENT:
                        message += f"* New document: {html.escape(change.new_value)}\n"
                    elif change.type == ChangeType.UPDATED_AT_CHANGE:
                        old_val = format_dt(change.old_value)
                        new_val = format_dt(change.new_value)
                        message += f"* Date change: {old_val} -> {new_val}\n"
                    elif change.type == ChangeType.QUESTION_COUNT_CHANGE:
                        message += f"* {html.escape(change.description)}\n"
                    elif change.type == ChangeType.NEW_QUESTION_DETAIL:
                        message += f"* {html.escape(change.description)}\n"
                    elif change.type == ChangeType.QUESTION_ASKED:
                        message += f"* {html.escape(change.description)}\n"
                    elif change.type == ChangeType.QUESTION_ANSWERED:
                        message += f"* {html.escape(change.description)}\n"
                    else:
                        message += f"* {html.escape(change.description)}\n"

            message += "\n"

        return message

    def _build_error_message(self, account_id: str, case_id: str, error: Exception, error_type: str) -> str:
        """Build plain text error notification message.

        Args:
            account_id: Account identifier
            case_id: Case identifier
            error: Exception that occurred
            error_type: Type of error

        Returns:
            Formatted plain text error message string
        """
        message = f"[{case_id}] {_tn('Cases.Title', 'Check Failed')}\n"
        message += f"-----------------------------------\n"
        message += f"{_tn('Errors.Label', 'Error')}: {error_type}: {str(error)}\n"
        message += f"Time: {datetime.utcnow().isoformat()}\n"
        message += f"{_tn('Cases.Signature', 'Case ID')}: {case_id}"

        return message

    def _send_fallback_email(self, cases: List[CaseInfo], error: str = "") -> None:
        """Send email fallback when Telegram fails.

        Args:
            cases: List of CaseInfo objects
            error: Error message if Telegram failed
        """
        if not self.email_enabled or not self.email_notifier:
            return

        for case in cases:
            changes_dicts = [
                {"type": str(c.type), "old_value": c.old_value, "new_value": c.new_value, "description": c.description}
                for c in case.changes
            ]
            self.email_notifier.send_change_notification(
                account_id=case.account_id,
                case_id=case.case_id,
                case_type=case.case_type,
                person_first=case.person_first,
                changes=changes_dicts,
                status=case.status
            )
        logger.info(f"Email fallback sent for {len(cases)} cases")

    def _send_error_fallback_email(
        self, account_id: str, case_id: str, error_message: str, error_type: str
    ) -> None:
        """Send email fallback when Telegram error notification fails.

        Args:
            account_id: Account identifier
            case_id: Case identifier
            error_message: Error message
            error_type: Type of error
        """
        if not self.email_enabled or not self.email_notifier:
            return

        self.email_notifier.send_error_notification(
            account_id=account_id,
            case_id=case_id,
            error_message=error_message,
            error_type=error_type,
        )
        logger.info(f"Error email fallback sent for case {case_id}")

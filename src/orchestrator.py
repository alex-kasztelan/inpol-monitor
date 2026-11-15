"""Orchestrator for Inpol Monitor.

Coordinates the complete check cycle:
1. Authenticate to Inpol portal
2. Fetch current data for all cases
3. Compare with previous snapshots
4. Detect changes and send notifications
5. Save new snapshots
"""

import logging
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv

from src.config import load_credentials
from src.auth import authenticate_account
from src.session_manager import SessionManager
from src.scraper import InpolScraper
from src.storage import SnapshotRepository
from src.notifier import TelegramNotifier
from src.detector import detect_all_changes

logger = logging.getLogger(__name__)


def run_check():
    """Run a complete monitoring check cycle.

    Returns:
        Dictionary mapping account names to lists of changes
    """
    load_dotenv()

    # Get credentials
    credentials = load_credentials()
    if not credentials:
        logger.error("No credentials found")
        return None

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger.info("Starting Inpol Monitor check cycle")

    # Initialize storage and notifier with real credentials from .env
    storage = SnapshotRepository("data/snapshots.db")
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "test:token")
    notifier = TelegramNotifier(telegram_token)

    account_names = list(credentials.keys())
    
    account_case_ids = {}
    for account_name in account_names:
        account_case_ids[account_name] = credentials.get(account_name, {}).get("case_ids", [])

    logger.info(f"Accounts: {account_case_ids}")

    # Authenticate accounts (keep sessions open)
    logger.info("Authenticating accounts...")
    sessions = {}
    for account_name in account_names:
        account_creds = credentials.get(account_name)
        if not account_creds:
            continue
        case_ids = account_case_ids.get(account_name, [])
        if not case_ids:
            continue

        session = authenticate_account(account_name, account_creds)
        if session and session.logged_in:
            sessions[account_name] = session
        else:
            logger.error(f"Failed to authenticate {account_name}")

    # Detect changes (notifier receives per-case callbacks during detection)
    logger.info("Detecting changes for all cases...")
    results = detect_all_changes(
        storage=storage,
        sessions=sessions,
        credentials=credentials,
        notifier=notifier
    )

    # Send combined notification for all cases
    notifier.send_all_notifications()

    # Close Telegram bot session
    import asyncio
    try:
        asyncio.run(notifier.close())
    except Exception as e:
        logger.warning(f"Failed to close bot session: {e}")

    # Cleanup
    for session in sessions.values():
        session.close()

    # Print summary
    for account, changes in results.items():
        if changes:
            logger.info(f"Account {account}: {len(changes)} change(s) detected")
        else:
            logger.info(f"Account {account}: No changes detected")

    return results

    logger.info("Check cycle completed")

    return results


def main():
    """Main entry point for CLI."""
    try:
        results = run_check()

        # Print summary
        if results:
            for account, changes in results.items():
                if changes:
                    logger.info(f"Account {account}: {len(changes)} change(s) detected")
                else:
                    logger.info(f"Account {account}: No changes detected")

        return 0
    except Exception as e:
        logger.error(f"Check failed: {e}")
        # Send error notification with real credentials
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "test:token")
        notifier = TelegramNotifier(telegram_token)
        notifier.on_error("unknown", "unknown", e, "SYSTEM_ERROR")
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""CLI entry point for Inpol Monitor authentication flow.

Usage:
    python check.py              # Run with default logging (INFO)
    python check.py -v           # Run with verbose logging (DEBUG)
    python check.py --verbose    # Same as -v

This script authenticates to both inpol.mazowieckie.pl accounts
sequentially, processes cases for each account, and logs out.
"""

import argparse
import logging
import sys
from pathlib import Path

from src.auth import run_sequential_auth
from src.config import get_base_path, load_credentials, load_env


def setup_logging(verbose: bool = False) -> None:
    """Configure logging with appropriate level based on verbose flag.

    Args:
        verbose: If True, set level to DEBUG for detailed output.
                If False, set level to INFO for summary output.
    """
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt=datefmt,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    logger = logging.getLogger(__name__)
    logger.debug("Logging initialized at %s level", logging.getLevelName(level))


def main() -> int:
    """Main entry point for the CLI.

    Loads credentials and environment, then runs sequential authentication
    across all configured accounts. Logs processing information for each
    account and ensures explicit logout.

    Returns:
        Exit code: 0 for success, 1 for failure
    """
    parser = argparse.ArgumentParser(
        description="Inpol Monitor - Authentication flow checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python check.py              # Run with INFO logging
    python check.py -v           # Run with DEBUG logging (verbose)
    python check.py --verbose    # Same as -v
        """
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging output"
    )

    args = parser.parse_args()

    # Setup logging based on verbose flag
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    logger.info("=== Inpol Monitor Authentication ===")
    logger.info("Base path: %s", get_base_path())

    # Load environment variables
    logger.info("Loading environment configuration...")
    env_loaded = load_env()
    if env_loaded:
        logger.debug("Environment loaded from .env file")
    else:
        logger.info("No .env file found, continuing with defaults")

    # Load credentials
    logger.info("Loading credentials...")
    credentials = load_credentials()

    if not credentials:
        logger.error("No credentials loaded. Check credentials.json exists.")
        return 1

    # Count configured accounts
    account_count = sum(1 for k in credentials if credentials.get(k))
    logger.info("Loaded %d account(s)", account_count)

    if account_count == 0:
        logger.error("No accounts configured in credentials.json")
        return 1

    # Run sequential authentication
    logger.info("Starting sequential authentication...")
    auth_success = False

    try:
        for account_name, session in run_sequential_auth(credentials):
            # Log processing information as per task requirement
            # Count cases if available in credentials
            account_creds = credentials.get(account_name, {})
            case_ids = account_creds.get("case_ids", [])
            case_count = len(case_ids) if case_ids else "unknown"

            logger.info("Processing %s: %s cases", account_name, case_count)

            # Mark that we successfully authenticated at least one account
            auth_success = True

            # Note: session is automatically closed by run_sequential_auth
            # after the generator yields and before the next iteration
            logger.info("Session closed for %s", account_name)

    except Exception as e:
        logger.error("Authentication flow failed: %s", e)
        return 1

    if auth_success:
        logger.info("=== Authentication complete ===")
        return 0
    else:
        logger.error("No accounts authenticated successfully")
        return 1


if __name__ == "__main__":
    sys.exit(main())

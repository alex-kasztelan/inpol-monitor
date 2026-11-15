#!/usr/bin/env python3
"""Telegram bot entry point.

Run this script to start the interactive Telegram bot that responds
to user commands (/start, /help, /status, /check, /accounts).

Usage:
    python bot.py

The bot will run continuously and respond to commands from authorized users.
"""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.telegram_bot import TelegramBot
from src.orchestrator import run_check

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_check_callback():
    """Callback to trigger a check from bot command."""
    logger.info("Manual check triggered via bot")
    # Run check in a separate thread to avoid blocking
    import asyncio
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, run_check)
    return result


def get_status_callback():
    """Callback to get last check status."""
    # This would normally read from a status file or memory
    # For now, return a simple status
    from src.storage import SnapshotRepository
    storage = SnapshotRepository("data/snapshots.db")
    
    try:
        # Get latest snapshot timestamps
        snapshots = storage.get_all_snapshots(limit=10)
        if snapshots:
            latest = snapshots[0]
            return f"✅ Last check: {latest['timestamp']}"
        else:
            return "ℹ️ No snapshots found. Run /check first."
    except Exception as e:
        return f"⚠️ Error getting status: {e}"


async def main():
    """Main entry point."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set in .env")
        return 1
    
    logger.info("Starting Telegram bot...")
    
    try:
        bot = TelegramBot(
            token=token,
            orchestrator_callback=run_check_callback,
            status_callback=get_status_callback
        )
        
        logger.info("Bot initialized, starting polling...")
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
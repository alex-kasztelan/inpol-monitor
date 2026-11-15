#!/usr/bin/env python3
"""Test script to verify TelegramNotifier functionality"""

import os
import asyncio
import logging
from src.notifier import TelegramNotifier
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_notifier():
    """Test the TelegramNotifier with a simple message"""
    # Get token from env
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    user_id = os.getenv('TELEGRAM_USER_ID')

    if not token or not user_id:
        print("❌ Missing TELEGRAM_BOT_TOKEN or TELEGRAM_USER_ID in .env file")
        return

    # Create notifier
    notifier = TelegramNotifier(token=token)

    # Test change detection with a sample change
    from src.models import Change, ChangeType

    # Create a sample change
    change = Change(
        type=ChangeType.UPDATED_AT_CHANGE,
        old_value="2024-01-01 10:00:00",
        new_value="2024-01-11 22:08:00",
        description="Something is changed - the edit date has been updated"
    )

    try:
        print(f"📤 Sending test message to chat ID: {user_id}")

        # Add case to notifier (new pattern)
        notifier.on_change(
            account_id="unreal.test.org",
            case_id="NFEJOEN278743898439843SJKDSHKNK",
            changes=[change],
            case_type="Rezydent długoterminowy UE",
            person_first="Unreal Name",
            case_url="https://inpol.mazowieckie.pl/home/cases/NFEJOEN278743898439843SJKDSHKNK"
        )

        # Send all notifications
        notifier.send_all_notifications()

        print("✅ Test message sent successfully!")

    except Exception as e:
        print(f"❌ Failed to send message: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up resources
        await notifier.close()

if __name__ == "__main__":
    asyncio.run(test_notifier())
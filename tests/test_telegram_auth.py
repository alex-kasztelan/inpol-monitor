#!/usr/bin/env python3
"""Test script for Telegram bot authorization."""

import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from src.telegram_bot import TelegramBot, is_authorized
from src.config import get_authorized_telegram_users


def test_authorization():
    """Test authorization logic."""
    print("=== Testing Authorization ===")
    users = get_authorized_telegram_users()
    print(f"Authorized users from config: {users}")
    
    # Test authorization
    test_ids = ["123", "999", "a1exby", "1078357459"]
    for uid in test_ids:
        result = is_authorized(uid)
        print(f"  User {uid}: {'✅ Authorized' if result else '⛔ Not authorized'}")


def test_bot_creation():
    """Test bot creation."""
    print("\n=== Testing Bot Creation ===")
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ Missing TELEGRAM_BOT_TOKEN")
        return
    
    try:
        bot = TelegramBot(token)
        print(f"✅ Bot created successfully")
        print(f"  Authorized users: {bot._authorized_users}")
    except Exception as e:
        print(f"❌ Failed to create bot: {e}")


if __name__ == "__main__":
    test_authorization()
    test_bot_creation()

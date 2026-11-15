"""Telegram bot handler for inbound commands.

This module provides a Telegram bot that responds to user commands
with authorization checking against configured user IDs.
"""

import logging
import os
import asyncio
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message

from src.config import get_authorized_telegram_users

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def is_authorized(user_id: str) -> bool:
    """Check if user is authorized to interact with the bot.

    Args:
        user_id: Telegram user ID (string or int)

    Returns:
        True if user is authorized, False otherwise
    """
    authorized_users = get_authorized_telegram_users()
    if not authorized_users:
        logger.warning("No authorized users configured - allowing all users")
        return True
    
    user_str = str(user_id)
    return user_str in authorized_users


def format_user_id(user_id: int) -> str:
    """Format user ID for display."""
    return str(user_id)


class TelegramBot:
    """Telegram bot handler for inbound commands."""

    def __init__(self, token: str, orchestrator_callback=None, status_callback=None):
        """Initialize Telegram bot.

        Args:
            token: Telegram bot token
            orchestrator_callback: Optional async function to trigger check
            status_callback: Optional function to get last check status
        """
        self.token = token
        self.orchestrator_callback = orchestrator_callback
        self.status_callback = status_callback
        self._authorized_users = get_authorized_telegram_users()
        
        # Initialize aiogram Bot and Dispatcher
        # For test tokens, use mock
        if token.startswith("test:"):
            from unittest.mock import MagicMock
            self.bot = MagicMock()
        else:
            self.bot = Bot(token=token)
        
        self.dp = Dispatcher()
        self.router = Router()
        
        # Register command handlers
        self._register_handlers()
        
        # Add router to dispatcher
        self.dp.include_router(self.router)

    def _register_handlers(self):
        """Register command handlers with authorization check."""
        # Create authorization filter
        from aiogram.filters import BaseFilter
        
        class AuthorizedUserFilter(BaseFilter):
            """Filter to check if user is authorized."""
            
            def __init__(self, authorized_users: list):
                self.authorized_users = authorized_users
            
            async def __call__(self, message: Message) -> bool:
                user_id = str(message.from_user.id)
                
                # If no users configured, allow all
                if not self.authorized_users:
                    return True
                
                return user_id in self.authorized_users
        
        auth_filter = AuthorizedUserFilter(self._authorized_users)
        
        # Register commands (with authorization)
        self.router.message.register(self.cmd_start, Command("start"), auth_filter)
        self.router.message.register(self.cmd_help, Command("help"), auth_filter)
        self.router.message.register(self.cmd_status, Command("status"), auth_filter)
        self.router.message.register(self.cmd_check, Command("check"), auth_filter)
        self.router.message.register(self.cmd_accounts, Command("accounts"), auth_filter)
        
        # Unauthorized handler (no filter - catches everyone)
        self.router.message.register(self.cmd_unauthorized, ~auth_filter)

    async def cmd_start(self, message: Message) -> None:
        """Handle /start command - welcome message."""
        await message.answer(
            "👋 Welcome to Inpol Monitor!\n\n"
            "I monitor your case status on inpol.mazowieckie.pl\n"
            "and send notifications when changes are detected.\n\n"
            "Use /help to see available commands."
        )

    async def cmd_help(self, message: Message) -> None:
        """Handle /help command - show available commands."""
        await message.answer(
            "📋 Available commands:\n\n"
            "/start - Welcome message\n"
            "/help - Show this help message\n"
            "/status - Show last check status\n"
            "/check - Trigger a manual check\n"
            "/accounts - Show configured accounts"
        )

    async def cmd_status(self, message: Message) -> None:
        """Handle /status command - show last check status."""
        if self.status_callback:
            status = await self.status_callback()
            await message.answer(status)
        else:
            await message.answer("⏳ Status callback not configured")

    async def cmd_check(self, message: Message) -> None:
        """Handle /check command - trigger manual check."""
        if self.orchestrator_callback:
            await message.answer("🔄 Starting manual check...")
            try:
                result = await self.orchestrator_callback()
                await message.answer(f"✅ Check completed: {result}")
            except Exception as e:
                await message.answer(f"❌ Check failed: {e}")
        else:
            await message.answer("⏳ Check callback not configured")

    async def cmd_accounts(self, message: Message) -> None:
        """Handle /accounts command - show configured accounts."""
        from src.config import load_credentials
        credentials = load_credentials()
        
        if not credentials:
            await message.answer("⚠️ No accounts configured")
            return
        
        account_names = list(credentials.keys())
        account_list = []
        for account_name in account_names:
            if account_name in credentials:
                case_ids = credentials[account_name].get('case_ids', [])
                case_count = len(case_ids)
                account_list.append(f"• {account_name}: {case_count} case(s)")
        
        if account_list:
            await message.answer("📁 Configured accounts:\n" + "\n".join(account_list))
        else:
            await message.answer("⚠️ No accounts configured")

    async def cmd_unauthorized(self, message: Message) -> None:
        """Handle unauthorized users."""
        user_id = message.from_user.id
        logger.warning(f"Unauthorized access attempt from user {user_id}")
        await message.answer("⛔ Unauthorized")

    async def start(self) -> None:
        """Start polling for messages."""
        logger.info("Starting Telegram bot polling...")
        await self.dp.start_polling(self.bot)

    async def stop(self) -> None:
        """Stop the bot."""
        await self.bot.session.close()


def run_telegram_bot(
    token: str,
    orchestrator_callback=None,
    status_callback=None
) -> TelegramBot:
    """Create and return Telegram bot instance.

    Args:
        token: Telegram bot token
        orchestrator_callback: Optional callback for /check command
        status_callback: Optional callback for /status command

    Returns:
        TelegramBot instance
    """
    bot = TelegramBot(token, orchestrator_callback, status_callback)
    return bot


async def start_bot_polling(token: str) -> None:
    """Start bot in polling mode (blocking).

    Args:
        token: Telegram bot token
    """
    bot = TelegramBot(token)
    await bot.start()
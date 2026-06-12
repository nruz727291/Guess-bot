"""
client.py - Pyrogram Client factory.
Creates and returns the configured bot client.
"""

from pyrogram import Client
from bot.config import Config


def create_client() -> Client:
    """Create and return a configured Pyrogram Client."""
    return Client(
        name="guess_bot",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN,
        # These settings help with production performance
        sleep_threshold=60,         # Handle FloodWait up to 60s automatically
        max_concurrent_transmissions=1,
    )

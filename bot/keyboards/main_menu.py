"""
main_menu.py - Main menu keyboard builder.
"""

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.constants import (
    CB_CREATE_ROOM, CB_JOIN_ROOM, CB_QUICK_MATCH,
    CB_PROFILE, CB_LEADERBOARD, CB_DAILY, CB_RULES, CB_REFRESH
)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Build and return the main menu inline keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏠 Create Room", callback_data=CB_CREATE_ROOM),
            InlineKeyboardButton("🚪 Join Room", callback_data=CB_JOIN_ROOM),
        ],
        [
            InlineKeyboardButton("⚡ Quick Match", callback_data=CB_QUICK_MATCH),
        ],
        [
            InlineKeyboardButton("👤 Profile", callback_data=CB_PROFILE),
            InlineKeyboardButton("🏆 Leaderboard", callback_data=CB_LEADERBOARD),
        ],
        [
            InlineKeyboardButton("🎁 Daily Reward", callback_data=CB_DAILY),
            InlineKeyboardButton("📖 Rules", callback_data=CB_RULES),
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data=CB_REFRESH),
        ],
    ])

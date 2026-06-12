"""
start.py - Handles /start command and main menu display.
"""

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from bot.services import get_or_register
from bot.keyboards import main_menu_keyboard
from bot.constants import MSG_WELCOME, MSG_RULES, CB_RULES, CB_REFRESH, CB_MENU
from bot.middleware import is_flooding
from bot.utils.logger import logger


def register(app: Client):
    """Register all start/menu handlers onto the Pyrogram client."""

    @app.on_message(filters.command("start") & filters.private)
    async def start_cmd(client: Client, message: Message):
        """Handle /start command."""
        user = message.from_user
        
        if is_flooding(user.id):
            return
        
        # Register or update user
        await get_or_register(user.id, user.username or "", user.first_name or "")
        
        await message.reply_text(
            MSG_WELCOME,
            reply_markup=main_menu_keyboard()
        )
        logger.info(f"User {user.id} ({user.first_name}) started bot")

    @app.on_callback_query(filters.regex(f"^{CB_REFRESH}$|^{CB_MENU}$"))
    async def refresh_menu(client: Client, cb: CallbackQuery):
        """Refresh the main menu."""
        user = cb.from_user
        
        if is_flooding(user.id):
            await cb.answer("Slow down! ⏳", show_alert=False)
            return
        
        await get_or_register(user.id, user.username or "", user.first_name or "")
        
        try:
            await cb.message.edit_text(
                MSG_WELCOME,
                reply_markup=main_menu_keyboard()
            )
        except Exception:
            pass  # MessageNotModified or similar
        
        await cb.answer("Refreshed! ✅")

    @app.on_callback_query(filters.regex(f"^{CB_RULES}$"))
    async def show_rules(client: Client, cb: CallbackQuery):
        """Show game rules."""
        from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        back_btn = InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Back", callback_data=CB_MENU)
        ]])
        
        try:
            await cb.message.edit_text(MSG_RULES, reply_markup=back_btn)
        except Exception:
            pass
        
        await cb.answer()

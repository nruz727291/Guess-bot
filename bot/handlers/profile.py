"""
profile.py - Profile and leaderboard handlers.
"""

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from bot.services.user_service import format_profile, format_leaderboard
from bot.keyboards.game_kb import leaderboard_nav_keyboard
from bot.middleware import is_flooding
from db.users import get_user, get_leaderboard
from bot.constants import CB_PROFILE, CB_LEADERBOARD, CB_LEADERBOARD_PAGE, CB_MENU
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def register(app: Client):
    """Register profile & leaderboard handlers."""

    @app.on_callback_query(filters.regex(f"^{CB_PROFILE}$"))
    async def show_profile(client: Client, cb: CallbackQuery):
        """Show user's profile stats."""
        user = cb.from_user
        
        if is_flooding(user.id):
            await cb.answer("Slow down!")
            return
        
        await cb.answer()
        
        db_user = await get_user(user.id)
        if not db_user:
            await cb.answer("Profile not found. Send /start first!", show_alert=True)
            return
        
        profile_text = format_profile(db_user)
        
        back_btn = InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Back", callback_data=CB_MENU)
        ]])
        
        try:
            await cb.message.edit_text(profile_text, reply_markup=back_btn)
        except Exception:
            pass

    @app.on_callback_query(filters.regex(f"^{CB_LEADERBOARD}$"))
    async def show_leaderboard(client: Client, cb: CallbackQuery):
        """Show leaderboard (default: top winners)."""
        await cb.answer()
        await _display_leaderboard(cb, "wins", 0)

    @app.on_callback_query(filters.regex(f"^{CB_LEADERBOARD_PAGE}:"))
    async def leaderboard_page(client: Client, cb: CallbackQuery):
        """Handle leaderboard navigation."""
        if is_flooding(cb.from_user.id):
            await cb.answer("Slow down!")
            return
        
        parts = cb.data.split(":")
        if len(parts) != 3:
            await cb.answer("Invalid navigation!")
            return
        
        _, sort_by, page_str = parts
        page = max(0, int(page_str) if page_str.isdigit() else 0)
        
        await cb.answer()
        await _display_leaderboard(cb, sort_by, page)


async def _display_leaderboard(cb: CallbackQuery, sort_by: str, page: int):
    """Helper: fetch and display leaderboard page."""
    per_page = 10
    skip = page * per_page
    
    users = await get_leaderboard(sort_by=sort_by, skip=skip, limit=per_page)
    
    # Get total count for pagination
    from db.connection import get_db
    total = await get_db().users.count_documents({})
    
    text = format_leaderboard(users, sort_by, page, per_page)
    keyboard = leaderboard_nav_keyboard(sort_by, page, total, per_page)
    
    try:
        await cb.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        pass

"""
callbacks.py - Central callback router.
Catches unknown/stale callbacks to prevent errors.
"""

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from bot.middleware import is_flooding
from bot.utils.logger import logger


def register(app: Client):
    """Register catchall callback handler (must be registered LAST)."""

    @app.on_callback_query()
    async def unknown_callback(client: Client, cb: CallbackQuery):
        """
        Catch-all for unhandled callbacks.
        This handles stale buttons from old messages gracefully.
        """
        user = cb.from_user
        
        if is_flooding(user.id):
            await cb.answer("⏳", show_alert=False)
            return
        
        logger.debug(f"Unhandled callback: {cb.data!r} from user {user.id}")
        
        try:
            await cb.answer("⚠️ This button is no longer active.", show_alert=True)
        except Exception:
            pass

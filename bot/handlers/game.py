"""
game.py - In-game callback handlers (guess buttons).
"""

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from bot.services.game_service import process_guess
from bot.middleware import is_flooding
from bot.constants import CB_GUESS
from bot.utils.helpers import safe_int
from bot.utils.logger import logger


def register(app: Client):
    """Register in-game handlers."""

    @app.on_callback_query(filters.regex(f"^{CB_GUESS}:"))
    async def guess_callback(client: Client, cb: CallbackQuery):
        """
        Handle a player's guess.
        Callback format: "guess:ROOMCODE:42"
        """
        user = cb.from_user
        
        if is_flooding(user.id):
            await cb.answer("Too fast! ⏳")
            return
        
        # Parse callback data
        parts = cb.data.split(":")
        if len(parts) != 3:
            await cb.answer("Invalid guess!", show_alert=True)
            return
        
        _, room_code, guess_str = parts
        guess = safe_int(guess_str)
        
        if guess < 1 or guess > 100:
            await cb.answer("Invalid number!", show_alert=True)
            return
        
        await cb.answer(f"Guessing {guess}... 🎯")
        
        # Process the guess
        error = await process_guess(client, room_code, user.id, guess)
        
        if error:
            await cb.answer(error, show_alert=True)
        
        # Delete the keyboard message to keep chat clean
        try:
            await cb.message.delete()
        except Exception:
            pass

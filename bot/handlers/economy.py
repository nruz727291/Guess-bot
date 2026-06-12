"""
economy.py - Daily reward and economy handlers.
"""

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from db.users import claim_daily
from bot.middleware import is_flooding
from bot.constants import CB_DAILY, CB_MENU, MSG_DAILY_CLAIMED
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def register(app: Client):
    """Register economy handlers."""

    @app.on_callback_query(filters.regex(f"^{CB_DAILY}$"))
    async def daily_reward(client: Client, cb: CallbackQuery):
        """Handle daily reward claim."""
        user = cb.from_user
        
        if is_flooding(user.id):
            await cb.answer("Slow down!")
            return
        
        success, coins = await claim_daily(user.id)
        
        back_btn = InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Back", callback_data=CB_MENU)
        ]])
        
        if not success:
            await cb.answer(MSG_DAILY_CLAIMED, show_alert=True)
            return
        
        await cb.answer(f"🎁 Claimed {coins} coins!", show_alert=True)
        
        try:
            await cb.message.edit_text(
                f"🎁 **Daily Reward Claimed!**\n\n"
                f"💰 You received **{coins} coins**!\n\n"
                f"Come back tomorrow for more!",
                reply_markup=back_btn
            )
        except Exception:
            pass

"""
game_kb.py - In-game keyboards with number guess buttons.
"""

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.constants import CB_GUESS, CB_LEAVE_ROOM


def guess_keyboard(room_code: str, low: int = 1, high: int = 100) -> InlineKeyboardMarkup:
    """
    Create number guess buttons.
    Shows range hints based on previous guesses.
    Buttons: smaller ranges around the middle for UX.
    """
    mid = (low + high) // 2
    
    # Create 5 evenly spaced guess options
    step = max(1, (high - low) // 6)
    options = []
    
    current = low
    while current <= high and len(options) < 8:
        options.append(current)
        current += step
    
    if high not in options and high != options[-1]:
        options.append(high)
    
    # Build button rows (3 per row)
    buttons = [
        InlineKeyboardButton(str(n), callback_data=f"{CB_GUESS}:{room_code}:{n}")
        for n in options
    ]
    rows = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
    
    # Add leave button at bottom
    rows.append([
        InlineKeyboardButton("🚪 Leave Game", callback_data=f"{CB_LEAVE_ROOM}:{room_code}")
    ])
    
    return InlineKeyboardMarkup(rows)


def leaderboard_nav_keyboard(sort_by: str, page: int, total: int, per_page: int = 10) -> InlineKeyboardMarkup:
    """Pagination buttons for leaderboard."""
    from bot.constants import CB_LEADERBOARD_PAGE
    buttons = []
    
    # Category buttons
    categories = [("🏆 Wins", "wins"), ("💰 Coins", "coins"), ("🔥 Streak", "max_streak")]
    cat_row = [
        InlineKeyboardButton(
            f"{'▸ ' if sort_by == key else ''}{label}",
            callback_data=f"{CB_LEADERBOARD_PAGE}:{key}:0"
        )
        for label, key in categories
    ]
    buttons.append(cat_row)
    
    # Page navigation
    nav_row = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton("◀️ Prev", callback_data=f"{CB_LEADERBOARD_PAGE}:{sort_by}:{page-1}")
        )
    nav_row.append(
        InlineKeyboardButton(f"📄 {page+1}", callback_data=f"{CB_LEADERBOARD_PAGE}:{sort_by}:{page}")
    )
    if (page + 1) * per_page < total:
        nav_row.append(
            InlineKeyboardButton("▶️ Next", callback_data=f"{CB_LEADERBOARD_PAGE}:{sort_by}:{page+1}")
        )
    
    if nav_row:
        buttons.append(nav_row)
    
    return InlineKeyboardMarkup(buttons)

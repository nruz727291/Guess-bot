"""
room_kb.py - Room-related keyboards.
"""

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.constants import CB_ROOM_SIZE, CB_START_GAME, CB_LEAVE_ROOM, CB_JOIN_CODE


def room_size_keyboard() -> InlineKeyboardMarkup:
    """Let owner choose max players (2-5)."""
    buttons = [
        InlineKeyboardButton(f"{i} Players", callback_data=f"{CB_ROOM_SIZE}:{i}")
        for i in range(2, 6)
    ]
    # Put 2 per row
    rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(rows)


def room_lobby_keyboard(room_code: str, is_owner: bool) -> InlineKeyboardMarkup:
    """Room lobby buttons. Owner sees Start button, everyone sees Leave."""
    buttons = []
    
    if is_owner:
        buttons.append([
            InlineKeyboardButton("▶️ Start Game", callback_data=f"{CB_START_GAME}:{room_code}")
        ])
    
    buttons.append([
        InlineKeyboardButton("🚪 Leave Room", callback_data=f"{CB_LEAVE_ROOM}:{room_code}")
    ])
    
    return InlineKeyboardMarkup(buttons)


def join_room_keyboard(room_code: str) -> InlineKeyboardMarkup:
    """Quick join button for shared room links."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Join Room", callback_data=f"{CB_JOIN_CODE}:{room_code}")
    ]])


def cancel_queue_keyboard() -> InlineKeyboardMarkup:
    """Cancel button for quick match queue."""
    from bot.constants import CB_CANCEL_QUEUE
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ Cancel Queue", callback_data=CB_CANCEL_QUEUE)
    ]])

"""
room.py - Room creation, joining, leaving handlers.
"""

import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, ForceReply
from bot.services.room_service import create_room, join_room, leave_room
from bot.services.game_service import start_game, end_game
from bot.keyboards import (
    room_size_keyboard, room_lobby_keyboard, 
    join_room_keyboard, main_menu_keyboard
)
from bot.constants import (
    CB_CREATE_ROOM, CB_JOIN_ROOM, CB_ROOM_SIZE,
    CB_START_GAME, CB_LEAVE_ROOM, CB_JOIN_CODE, CB_MENU
)
from bot.middleware import is_flooding
from bot.utils.logger import logger
from bot.states import RoomState
import db.rooms as room_db
import db.games as game_db


def register(app: Client):
    """Register room handlers."""

    @app.on_callback_query(filters.regex(f"^{CB_CREATE_ROOM}$"))
    async def create_room_cb(client: Client, cb: CallbackQuery):
        """Ask user to select room size."""
        user = cb.from_user
        
        if is_flooding(user.id):
            await cb.answer("Slow down!", show_alert=False)
            return
        
        await cb.answer()
        
        try:
            await cb.message.edit_text(
                "🏠 **Create a Room**\n\nHow many players?",
                reply_markup=room_size_keyboard()
            )
        except Exception:
            pass

    @app.on_callback_query(filters.regex(f"^{CB_ROOM_SIZE}:"))
    async def room_size_selected(client: Client, cb: CallbackQuery):
        """User selected a room size, create the room."""
        user = cb.from_user
        
        if is_flooding(user.id):
            await cb.answer("Slow down!")
            return
        
        # Parse: "room_size:3" → 3
        try:
            max_players = int(cb.data.split(":")[1])
        except (IndexError, ValueError):
            await cb.answer("Invalid selection!", show_alert=True)
            return
        
        if not (2 <= max_players <= 5):
            await cb.answer("Invalid player count!", show_alert=True)
            return
        
        await cb.answer("Creating room... ⏳")
        
        room, error = await create_room(
            user.id,
            user.username or "",
            user.first_name or "Player",
            max_players
        )
        
        if error:
            try:
                await cb.message.edit_text(
                    f"{error}\n\nGo back to menu:",
                    reply_markup=main_menu_keyboard()
                )
            except Exception:
                pass
            return
        
        code = room["room_code"]
        msg = (
            f"✅ **Room Created!**\n\n"
            f"📋 Room Code: `{code}`\n"
            f"👥 Max Players: {max_players}\n"
            f"🟢 Status: Waiting...\n\n"
            f"Share this code with friends to let them join!\n"
            f"Min. {2} players needed to start."
        )
        
        try:
            await cb.message.edit_text(
                msg,
                reply_markup=room_lobby_keyboard(code, is_owner=True)
            )
        except Exception:
            pass

    @app.on_callback_query(filters.regex(f"^{CB_JOIN_ROOM}$"))
    async def join_room_prompt(client: Client, cb: CallbackQuery):
        """Ask user to send the room code."""
        user = cb.from_user
        await cb.answer()
        
        try:
            await cb.message.edit_text(
                "🚪 **Join a Room**\n\n"
                "Send the room code (e.g. `ABC123`):\n\n"
                "_Just type and send the 6-character code._",
            )
        except Exception:
            pass
        
        # Listen for next message with the room code
        # We'll use a simple state tracking with a dict
        _pending_joins[user.id] = True

    @app.on_callback_query(filters.regex(f"^{CB_JOIN_CODE}:"))
    async def join_by_code_button(client: Client, cb: CallbackQuery):
        """Join room via inline button (from shared room link)."""
        user = cb.from_user
        
        if is_flooding(user.id):
            await cb.answer("Slow down!")
            return
        
        try:
            code = cb.data.split(":")[1]
        except IndexError:
            await cb.answer("Invalid code!")
            return
        
        await cb.answer("Joining... ⏳")
        
        room, error = await join_room(code, user.id, user.first_name or "Player")
        
        if error:
            await cb.answer(error, show_alert=True)
            return
        
        await _show_room_lobby(client, cb.message, room, user.id)

    @app.on_message(filters.private & filters.text & ~filters.command(["start"]))
    async def handle_room_code_input(client: Client, message: Message):
        """Handle manual room code input."""
        user = message.from_user
        text = message.text.strip().upper()
        
        # Only process if user was prompted to enter a code
        if user.id not in _pending_joins:
            return
        
        if is_flooding(user.id):
            return
        
        # Validate: room codes are 6 uppercase alphanumeric chars
        if not (len(text) == 6 and text.isalnum()):
            await message.reply_text(
                "❌ Invalid room code format. Room codes are 6 characters (e.g. ABC123).\n"
                "Try again or use /start to go back."
            )
            return
        
        # Remove from pending
        _pending_joins.pop(user.id, None)
        
        room, error = await join_room(text, user.id, user.first_name or "Player")
        
        if error:
            await message.reply_text(
                f"{error}\n\nUse /start to go back to menu."
            )
            return
        
        await message.reply_text(
            f"✅ Joined room **{text}**!",
            reply_markup=room_lobby_keyboard(text, is_owner=False)
        )
        
        # Notify other players
        code = room["room_code"]
        for p in room["players"]:
            if p["user_id"] != user.id:
                try:
                    await client.send_message(
                        p["user_id"],
                        f"👤 **{user.first_name}** joined the room!\n"
                        f"Players: {len(room['players'])}/{room['max_players']}"
                    )
                except Exception:
                    pass

    @app.on_callback_query(filters.regex(f"^{CB_START_GAME}:"))
    async def start_game_cb(client: Client, cb: CallbackQuery):
        """Owner starts the game."""
        user = cb.from_user
        
        if is_flooding(user.id):
            await cb.answer("Slow down!")
            return
        
        try:
            room_code = cb.data.split(":")[1]
        except IndexError:
            await cb.answer("Invalid!")
            return
        
        room = await room_db.get_room(room_code)
        if not room:
            await cb.answer("Room not found!", show_alert=True)
            return
        
        if room["owner_id"] != user.id:
            await cb.answer("Only the room owner can start!", show_alert=True)
            return
        
        if room["state"] != RoomState.WAITING:
            await cb.answer("Game already started!", show_alert=True)
            return
        
        if len(room["players"]) < 2:
            await cb.answer("Need at least 2 players!", show_alert=True)
            return
        
        await cb.answer("Starting game! 🎮")
        
        try:
            await cb.message.edit_text("⏳ Starting game...")
        except Exception:
            pass
        
        success, msg = await start_game(client, room_code)
        
        if not success:
            await cb.message.reply_text(f"❌ {msg}")

    @app.on_callback_query(filters.regex(f"^{CB_LEAVE_ROOM}:"))
    async def leave_room_cb(client: Client, cb: CallbackQuery):
        """Player leaves a room."""
        user = cb.from_user
        
        if is_flooding(user.id):
            await cb.answer("Slow down!")
            return
        
        try:
            room_code = cb.data.split(":")[1]
        except IndexError:
            await cb.answer("Invalid!")
            return
        
        # Check if game is active (rage quit penalty)
        game = await game_db.get_game(room_code)
        if game and game["state"] == "active":
            # Apply rage quit penalty
            from bot.config import Config
            import db.users as user_db
            await user_db.add_coins(user.id, -Config.RAGEQUIT_PENALTY)
            await cb.answer(f"😡 Rage quit! -{Config.RAGEQUIT_PENALTY} coins", show_alert=True)
            
            # Remove from active game
            await game_db.eliminate_player(room_code, user.id)
            
            # Notify other players
            if game:
                from bot.services.game_service import broadcast_to_players
                await broadcast_to_players(
                    client,
                    game["players"],
                    f"😤 **{user.first_name}** rage quit! (-{Config.RAGEQUIT_PENALTY} coins penalty)"
                )
        else:
            await cb.answer("Left room.")
        
        updated_room, was_owner = await leave_room(room_code, user.id)
        
        try:
            await cb.message.edit_text(
                "You left the room. Use /start to go back to menu.",
                reply_markup=main_menu_keyboard()
            )
        except Exception:
            await cb.message.reply_text(
                "You left the room.",
                reply_markup=main_menu_keyboard()
            )
        
        # Notify remaining players
        if updated_room:
            for p in updated_room["players"]:
                try:
                    new_owner = updated_room["owner_id"] == p["user_id"]
                    msg = f"👤 **{user.first_name}** left the room."
                    if was_owner and new_owner:
                        msg += "\n👑 You are now the room owner!"
                    await client.send_message(
                        p["user_id"],
                        msg,
                        reply_markup=room_lobby_keyboard(room_code, is_owner=new_owner)
                    )
                except Exception:
                    pass


async def _show_room_lobby(client, message, room: dict, user_id: int):
    """Helper: show room lobby state."""
    code = room["room_code"]
    players = room["players"]
    player_list = "\n".join([
        f"  {'👑' if p['user_id'] == room['owner_id'] else '👤'} {p['name']}"
        for p in players
    ])
    
    text = (
        f"🏠 **Room: {code}**\n\n"
        f"Players ({len(players)}/{room['max_players']}):\n"
        f"{player_list}\n\n"
        f"{'⏳ Waiting for more players...' if len(players) < 2 else '✅ Ready to start!'}"
    )
    
    is_owner = room["owner_id"] == user_id
    
    try:
        await message.edit_text(
            text,
            reply_markup=room_lobby_keyboard(code, is_owner=is_owner)
        )
    except Exception:
        await message.reply_text(
            text,
            reply_markup=room_lobby_keyboard(code, is_owner=is_owner)
        )


# Track users waiting to input a room code
# Simple in-memory dict, cleared on bot restart (fine for UX)
_pending_joins: dict[int, bool] = {}

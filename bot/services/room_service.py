"""
room_service.py - Room management business logic.
Handles room creation, joining, leaving with proper validation.
"""

import asyncio
from typing import Optional, Tuple
from bot.config import Config
from bot.utils.logger import logger
from bot.states import RoomState
import db.rooms as room_db
import db.cooldowns as cd_db

# Per-room async locks to prevent race conditions
# e.g., two players joining simultaneously
_room_locks: dict[str, asyncio.Lock] = {}


def get_room_lock(room_code: str) -> asyncio.Lock:
    """Get or create a lock for a specific room."""
    if room_code not in _room_locks:
        _room_locks[room_code] = asyncio.Lock()
    return _room_locks[room_code]


def cleanup_room_lock(room_code: str):
    """Remove lock when room is deleted (memory cleanup)."""
    _room_locks.pop(room_code, None)


async def create_room(user_id: int, username: str, first_name: str, max_players: int) -> Tuple[Optional[dict], Optional[str]]:
    """
    Create a new room for the user.
    
    Returns: (room_doc, error_message)
    """
    # Check create cooldown
    remaining = await cd_db.check_cooldown(user_id, "create_room")
    if remaining:
        return None, f"⏳ Wait {remaining:.0f}s before creating another room."
    
    # Check user doesn't already have active room
    existing = await room_db.get_user_active_room(user_id)
    if existing:
        return None, f"⚠️ You already have room **{existing['room_code']}** open. Leave it first."
    
    room = await room_db.create_room(user_id, first_name, max_players)
    
    # Set cooldown
    await cd_db.set_cooldown(user_id, "create_room", Config.ROOM_CREATE_COOLDOWN)
    
    logger.info(f"Room created: {room['room_code']} by user {user_id}")
    return room, None


async def join_room(room_code: str, user_id: int, first_name: str) -> Tuple[Optional[dict], Optional[str]]:
    """
    Join an existing room.
    
    Returns: (room_doc, error_message)
    """
    room_code = room_code.upper().strip()
    
    # Get lock for this room (prevents simultaneous joins)
    async with get_room_lock(room_code):
        room = await room_db.get_room(room_code)
        
        if not room:
            return None, "❌ Room not found. Check the code."
        
        if room["state"] != RoomState.WAITING:
            return None, "❌ That game has already started."
        
        # Check if user already in this room
        player_ids = [p["user_id"] for p in room["players"]]
        if user_id in player_ids:
            return None, "⚠️ You're already in this room!"
        
        # Check if user is in another room
        other_room = await room_db.get_user_active_room(user_id)
        if other_room and other_room["room_code"] != room_code:
            return None, f"⚠️ You're in room **{other_room['room_code']}**. Leave it first."
        
        success = await room_db.add_player_to_room(room_code, user_id, first_name)
        
        if not success:
            return None, "❌ Room is full or you already joined."
        
        room = await room_db.get_room(room_code)
        logger.info(f"User {user_id} joined room {room_code}")
        return room, None


async def leave_room(room_code: str, user_id: int) -> Tuple[Optional[dict], bool]:
    """
    Leave a room.
    
    Returns: (updated_room_or_None, was_owner)
    """
    room = await room_db.get_room(room_code)
    if not room:
        return None, False
    
    was_owner = room["owner_id"] == user_id
    updated_room = await room_db.remove_player_from_room(room_code, user_id)
    
    if updated_room is None:
        # Room deleted (was empty)
        cleanup_room_lock(room_code)
    
    return updated_room, was_owner

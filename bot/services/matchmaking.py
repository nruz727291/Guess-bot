"""
matchmaking.py - Quick match queue system.
Players join queue and get auto-grouped into rooms.
"""

import asyncio
from datetime import timedelta
from typing import Optional
from bot.config import Config
from bot.utils.helpers import utc_now
from bot.utils.logger import logger
from db.connection import get_db
import db.rooms as room_db

# Lock to prevent race conditions in queue processing
_queue_lock = asyncio.Lock()


async def join_queue(user_id: int, username: str) -> tuple[bool, str]:
    """
    Add user to quick match queue.
    Returns (success, message)
    """
    db = get_db()
    
    # Check if already in queue
    existing = await db.quick_match_queue.find_one({"user_id": user_id})
    if existing:
        return False, "⚠️ You're already in the queue!"
    
    # Check if already in a room
    room = await room_db.get_user_active_room(user_id)
    if room:
        return False, f"⚠️ Leave room **{room['room_code']}** first."
    
    await db.quick_match_queue.insert_one({
        "user_id": user_id,
        "username": username,
        "joined_at": utc_now()
    })
    
    logger.info(f"User {user_id} joined quick match queue")
    return True, "✅ Added to queue!"


async def leave_queue(user_id: int) -> bool:
    """Remove user from queue. Returns True if they were in it."""
    result = await get_db().quick_match_queue.delete_one({"user_id": user_id})
    return result.deleted_count > 0


async def get_queue_count() -> int:
    """Get current number of players in queue."""
    return await get_db().quick_match_queue.count_documents({})


async def process_queue(client) -> Optional[dict]:
    """
    Check queue and create a room if enough players.
    Returns created room or None.
    Called by background task.
    """
    async with _queue_lock:
        db = get_db()
        count = await get_queue_count()
        
        if count < Config.MIN_PLAYERS:
            return None
        
        # Take up to max players from queue (oldest first)
        players = await db.quick_match_queue.find(
            {}
        ).sort("joined_at", 1).limit(Config.MAX_PLAYERS).to_list(length=Config.MAX_PLAYERS)
        
        if len(players) < Config.MIN_PLAYERS:
            return None
        
        # Remove them from queue
        player_ids = [p["user_id"] for p in players]
        await db.quick_match_queue.delete_many({"user_id": {"$in": player_ids}})
        
        # Create room with first player as owner
        first = players[0]
        room = await room_db.create_room(
            first["user_id"],
            first.get("username") or "Player",
            len(players)
        )
        
        # Add remaining players to room
        for p in players[1:]:
            await room_db.add_player_to_room(
                room["room_code"],
                p["user_id"],
                p.get("username") or "Player"
            )
        
        logger.info(f"Quick match created room {room['room_code']} with {len(players)} players")
        
        # Notify all players
        from bot.keyboards import room_lobby_keyboard
        for p in players:
            try:
                is_owner = p["user_id"] == first["user_id"]
                await client.send_message(
                    p["user_id"],
                    f"🎮 **Match Found!**\n\n"
                    f"Room Code: `{room['room_code']}`\n"
                    f"Players: {len(players)}\n\n"
                    f"{'▶️ You are the host! Press Start when ready.' if is_owner else '⏳ Waiting for host to start...'}",
                    reply_markup=room_lobby_keyboard(room["room_code"], is_owner)
                )
            except Exception as e:
                logger.warning(f"Failed to notify {p['user_id']} of match: {e}")
        
        return room


async def cleanup_old_queue_entries(max_wait_seconds: int = 120):
    """Remove queue entries older than max_wait_seconds."""
    cutoff = utc_now() - timedelta(seconds=max_wait_seconds)
    result = await get_db().quick_match_queue.delete_many({
        "joined_at": {"$lt": cutoff}
    })
    if result.deleted_count:
        logger.info(f"Cleaned {result.deleted_count} stale queue entries")
    return result.deleted_count

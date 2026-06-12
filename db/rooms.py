"""
db/rooms.py - Database operations for rooms collection.
"""

from typing import Optional
from bot.utils.helpers import utc_now, generate_room_code
from bot.states import RoomState
from db.connection import get_db


async def create_room(owner_id: int, owner_name: str, max_players: int) -> dict:
    """
    Create a new room in the database.
    Generates a unique room code (retries if collision).
    """
    db = get_db()
    
    # Try up to 5 times to get a unique code
    for _ in range(5):
        code = generate_room_code()
        existing = await db.rooms.find_one({"room_code": code})
        if not existing:
            break
    
    room = {
        "room_code": code,
        "owner_id": owner_id,
        "owner_name": owner_name,
        "max_players": max_players,
        "players": [{"user_id": owner_id, "name": owner_name}],
        "state": RoomState.WAITING,
        "created_at": utc_now(),
        "last_activity": utc_now(),
    }
    
    await db.rooms.insert_one(room)
    return room


async def get_room(room_code: str) -> Optional[dict]:
    """Fetch room by room code."""
    return await get_db().rooms.find_one({"room_code": room_code})


async def get_user_active_room(user_id: int) -> Optional[dict]:
    """Find any WAITING room where user is a player."""
    return await get_db().rooms.find_one({
        "players.user_id": user_id,
        "state": RoomState.WAITING
    })


async def add_player_to_room(room_code: str, user_id: int, name: str) -> bool:
    """
    Add a player to a room atomically.
    Returns True if successful, False if room is full or already joined.
    """
    db = get_db()
    
    # Atomic update: only add if player count < max_players AND user not already in
    result = await db.rooms.update_one(
        {
            "room_code": room_code,
            "state": RoomState.WAITING,
            "players.user_id": {"$ne": user_id},  # Not already in room
            "$expr": {
                "$lt": [{"$size": "$players"}, "$max_players"]  # Not full
            }
        },
        {
            "$push": {"players": {"user_id": user_id, "name": name}},
            "$set": {"last_activity": utc_now()}
        }
    )
    return result.modified_count > 0


async def remove_player_from_room(room_code: str, user_id: int) -> dict:
    """Remove a player from room. If owner leaves, transfer ownership or delete."""
    db = get_db()
    
    room = await get_room(room_code)
    if not room:
        return None
    
    # Remove player from list
    await db.rooms.update_one(
        {"room_code": room_code},
        {
            "$pull": {"players": {"user_id": user_id}},
            "$set": {"last_activity": utc_now()}
        }
    )
    
    # Refresh room data
    room = await get_room(room_code)
    
    if not room or len(room["players"]) == 0:
        # Room is empty, delete it
        await db.rooms.delete_one({"room_code": room_code})
        return None
    
    # If owner left, transfer to next player
    if room["owner_id"] == user_id:
        new_owner = room["players"][0]
        await db.rooms.update_one(
            {"room_code": room_code},
            {"$set": {
                "owner_id": new_owner["user_id"],
                "owner_name": new_owner["name"]
            }}
        )
    
    return await get_room(room_code)


async def update_room_state(room_code: str, state: str):
    """Update room state (waiting/started/finished)."""
    await get_db().rooms.update_one(
        {"room_code": room_code},
        {"$set": {"state": state, "last_activity": utc_now()}}
    )


async def delete_room(room_code: str):
    """Delete a room permanently."""
    await get_db().rooms.delete_one({"room_code": room_code})


async def cleanup_stale_rooms(idle_seconds: int = 300):
    """Delete WAITING rooms that have been idle too long."""
    from datetime import timedelta
    cutoff = utc_now() - timedelta(seconds=idle_seconds)
    
    result = await get_db().rooms.delete_many({
        "state": RoomState.WAITING,
        "last_activity": {"$lt": cutoff}
    })
    return result.deleted_count

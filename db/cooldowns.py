"""
db/cooldowns.py - Anti-spam cooldown system using MongoDB TTL.
Documents auto-delete when expires_at passes (MongoDB handles cleanup).
"""

from datetime import timedelta
from typing import Optional
from bot.utils.helpers import utc_now
from db.connection import get_db


async def check_cooldown(user_id: int, action: str) -> Optional[float]:
    """
    Check if user is on cooldown for an action.
    
    Returns:
        None if no cooldown active
        float: seconds remaining if on cooldown
    """
    doc = await get_db().cooldowns.find_one({
        "user_id": user_id,
        "action": action
    })
    
    if not doc:
        return None
    
    now = utc_now()
    expires_at = doc["expires_at"]
    
    # Make timezone-aware for comparison
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=now.tzinfo)
    
    remaining = (expires_at - now).total_seconds()
    return remaining if remaining > 0 else None


async def set_cooldown(user_id: int, action: str, seconds: float):
    """
    Set a cooldown for user+action.
    Overwrites existing cooldown.
    MongoDB TTL index auto-deletes expired docs.
    """
    expires_at = utc_now() + timedelta(seconds=seconds)
    
    await get_db().cooldowns.update_one(
        {"user_id": user_id, "action": action},
        {
            "$set": {
                "user_id": user_id,
                "action": action,
                "expires_at": expires_at
            }
        },
        upsert=True
    )


async def clear_cooldown(user_id: int, action: str):
    """Manually remove a cooldown (e.g., after game ends)."""
    await get_db().cooldowns.delete_one({
        "user_id": user_id,
        "action": action
    })

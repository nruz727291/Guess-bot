"""
db/users.py - All database operations for the users collection.
"""

from datetime import datetime, timezone
from typing import Optional
from bot.utils.helpers import utc_now
from db.connection import get_db


async def get_user(user_id: int) -> Optional[dict]:
    """Fetch a user document by Telegram user_id."""
    return await get_db().users.find_one({"user_id": user_id})


async def register_user(user_id: int, username: str, first_name: str) -> dict:
    """
    Register a new user OR update existing user's info.
    Uses upsert so it's safe to call on every /start.
    """
    db = get_db()
    now = utc_now()

    # $setOnInsert only runs when document is NEW (inserted)
    # $set always runs (updates username/name if changed)
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "username": username,
                "first_name": first_name,
                "last_seen": now,
            },
            "$setOnInsert": {
                "user_id": user_id,
                "coins": 100,           # Starting coins
                "wins": 0,
                "losses": 0,
                "games_played": 0,
                "streak": 0,
                "max_streak": 0,
                "daily_claimed": None,
                "created_at": now,
            }
        },
        upsert=True  # Create if doesn't exist
    )
    return await get_user(user_id)


async def update_last_seen(user_id: int):
    """Update last_seen timestamp (called on every message)."""
    await get_db().users.update_one(
        {"user_id": user_id},
        {"$set": {"last_seen": utc_now()}}
    )


async def add_coins(user_id: int, amount: int) -> int:
    """
    Add (or subtract with negative amount) coins to user.
    Returns new coin balance.
    Prevents going below 0 coins.
    """
    db = get_db()
    
    if amount < 0:
        # Ensure coins don't go below 0
        result = await db.users.find_one_and_update(
            {"user_id": user_id, "coins": {"$gte": abs(amount)}},
            {"$inc": {"coins": amount}},
            return_document=True
        )
        if not result:
            # User doesn't have enough coins, set to 0
            await db.users.update_one(
                {"user_id": user_id},
                {"$set": {"coins": 0}}
            )
            user = await get_user(user_id)
            return user["coins"] if user else 0
        return result["coins"]
    else:
        result = await db.users.find_one_and_update(
            {"user_id": user_id},
            {"$inc": {"coins": amount}},
            return_document=True
        )
        return result["coins"] if result else 0


async def record_win(user_id: int):
    """Record a win: increment wins, streak, games_played."""
    user = await get_user(user_id)
    if not user:
        return
    
    new_streak = user.get("streak", 0) + 1
    max_streak = max(user.get("max_streak", 0), new_streak)
    
    await get_db().users.update_one(
        {"user_id": user_id},
        {
            "$inc": {"wins": 1, "games_played": 1},
            "$set": {"streak": new_streak, "max_streak": max_streak}
        }
    )


async def record_loss(user_id: int):
    """Record a loss: reset streak, increment losses and games_played."""
    await get_db().users.update_one(
        {"user_id": user_id},
        {
            "$inc": {"losses": 1, "games_played": 1},
            "$set": {"streak": 0}
        }
    )


async def claim_daily(user_id: int) -> tuple[bool, int]:
    """
    Try to claim daily reward.
    Returns (success: bool, coins_added: int)
    """
    from bot.config import Config
    
    user = await get_user(user_id)
    if not user:
        return False, 0
    
    now = utc_now()
    last_claimed = user.get("daily_claimed")
    
    # Check if already claimed today (UTC day)
    if last_claimed:
        if isinstance(last_claimed, datetime):
            if last_claimed.date() == now.date():
                return False, 0  # Already claimed today
    
    # Calculate streak bonus
    streak = user.get("streak", 0)
    bonus = min(streak * Config.STREAK_BONUS, 100)  # Cap at 100 bonus
    total_reward = Config.DAILY_REWARD + bonus
    
    await get_db().users.update_one(
        {"user_id": user_id},
        {
            "$inc": {"coins": total_reward},
            "$set": {"daily_claimed": now}
        }
    )
    return True, total_reward


async def get_leaderboard(sort_by: str = "wins", skip: int = 0, limit: int = 10) -> list:
    """
    Get top players sorted by field.
    sort_by: 'wins', 'coins', or 'streak'
    """
    valid_fields = {"wins", "coins", "streak", "max_streak"}
    if sort_by not in valid_fields:
        sort_by = "wins"
    
    cursor = get_db().users.find(
        {},
        {"user_id": 1, "username": 1, "first_name": 1, sort_by: 1}
    ).sort(sort_by, -1).skip(skip).limit(limit)
    
    return await cursor.to_list(length=limit)

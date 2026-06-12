"""
db/games.py - Database operations for active_games collection.
Stores full game state for crash recovery.
"""

from typing import Optional
from bot.utils.helpers import utc_now
from bot.states import GameState
from db.connection import get_db


async def create_game(room_code: str, players: list, secret_number: int) -> dict:
    """
    Create a new game state document.
    
    players: list of {"user_id": int, "name": str}
    """
    game = {
        "room_code": room_code,
        "secret_number": secret_number,
        "players": players,          # All players
        "active_players": [p["user_id"] for p in players],  # Not yet eliminated
        "current_turn_index": 0,     # Index into active_players
        "guesses": [],               # History: [{"user_id": x, "guess": y, "result": z}]
        "state": GameState.ACTIVE,
        "winner_id": None,
        "created_at": utc_now(),
        "last_activity": utc_now(),
    }
    await get_db().active_games.insert_one(game)
    return game


async def get_game(room_code: str) -> Optional[dict]:
    """Fetch active game by room code."""
    return await get_db().active_games.find_one({"room_code": room_code})


async def get_all_active_games() -> list:
    """Get all games in ACTIVE state (used for crash recovery)."""
    cursor = get_db().active_games.find({"state": GameState.ACTIVE})
    return await cursor.to_list(length=None)


async def record_guess(room_code: str, user_id: int, guess: int, result: str):
    """
    Add a guess to game history.
    result: 'too_high', 'too_low', 'correct'
    """
    guess_entry = {
        "user_id": user_id,
        "guess": guess,
        "result": result,
        "timestamp": utc_now()
    }
    await get_db().active_games.update_one(
        {"room_code": room_code},
        {
            "$push": {"guesses": guess_entry},
            "$set": {"last_activity": utc_now()}
        }
    )


async def advance_turn(room_code: str, new_index: int):
    """Move to the next player's turn."""
    await get_db().active_games.update_one(
        {"room_code": room_code},
        {
            "$set": {
                "current_turn_index": new_index,
                "last_activity": utc_now()
            }
        }
    )


async def eliminate_player(room_code: str, user_id: int):
    """Remove a player from active_players (they missed their turn)."""
    await get_db().active_games.update_one(
        {"room_code": room_code},
        {
            "$pull": {"active_players": user_id},
            "$set": {"last_activity": utc_now()}
        }
    )


async def finish_game(room_code: str, winner_id: Optional[int]):
    """Mark game as finished and record winner."""
    await get_db().active_games.update_one(
        {"room_code": room_code},
        {
            "$set": {
                "state": GameState.FINISHED,
                "winner_id": winner_id,
                "finished_at": utc_now()
            }
        }
    )


async def cleanup_stale_games(idle_seconds: int = 600):
    """Delete games idle for too long."""
    from datetime import timedelta
    cutoff = utc_now() - timedelta(seconds=idle_seconds)
    
    result = await get_db().active_games.delete_many({
        "state": GameState.ACTIVE,
        "last_activity": {"$lt": cutoff}
    })
    return result.deleted_count

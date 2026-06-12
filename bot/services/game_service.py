"""
game_service.py - Core game logic.
"""

import asyncio
import random
from typing import Optional, Tuple
from pyrogram import Client
from bot.config import Config
from bot.utils.logger import logger
from bot.states import GameState, RoomState
from bot.keyboards import guess_keyboard
import db.games as game_db
import db.rooms as room_db
import db.users as user_db
import db.cooldowns as cd_db

# Track turn timeout tasks
_turn_timers: dict[str, asyncio.Task] = {}

# Track current guess range per room
_guess_ranges: dict[str, dict] = {}


async def start_game(client: Client, room_code: str) -> Tuple[bool, str]:
    """Start a game for a waiting room."""
    room = await room_db.get_room(room_code)
    if not room:
        return False, "Room not found."

    if room["state"] != RoomState.WAITING:
        return False, "Game already started."

    players = room["players"]
    if len(players) < Config.MIN_PLAYERS:
        return False, f"Need at least {Config.MIN_PLAYERS} players to start."

    secret = random.randint(Config.NUMBER_MIN, Config.NUMBER_MAX)

    # Create game document in DB
    game = await game_db.create_game(room_code, players, secret)

    # Update room state
    await room_db.update_room_state(room_code, RoomState.STARTED)

    # Initialize guess range tracker
    _guess_ranges[room_code] = {"low": Config.NUMBER_MIN, "high": Config.NUMBER_MAX}

    logger.info(f"Game started in room {room_code} | Secret: {secret} | Players: {len(players)}")

    # Broadcast game start to all players
    player_list = "\n".join([f"  • {p['name']}" for p in players])
    start_msg = (
        f"🎮 **GAME STARTED!**\n\n"
        f"Room: `{room_code}`\n"
        f"Players:\n{player_list}\n\n"
        f"🔢 I'm thinking of a number between "
        f"**{Config.NUMBER_MIN}** and **{Config.NUMBER_MAX}**\n\n"
        f"⏱ You have **{Config.TURN_TIMEOUT}** seconds per turn!"
    )

    await broadcast_to_players(client, players, start_msg)

    # Start first turn
    await start_turn(client, room_code)
    return True, "Game started!"


async def start_turn(client: Client, room_code: str):
    """Notify current player it's their turn."""
    game = await game_db.get_game(room_code)
    if not game or game["state"] != GameState.ACTIVE:
        return

    active = game["active_players"]
    if not active:
        await end_game(client, room_code, winner_id=None)
        return

    idx = game["current_turn_index"] % len(active)
    current_player_id = active[idx]

    # Find player name
    player_name = next(
        (p["name"] for p in game["players"] if p["user_id"] == current_player_id),
        "Player"
    )

    # Get current range
    rng = _guess_ranges.get(room_code, {"low": Config.NUMBER_MIN, "high": Config.NUMBER_MAX})

    # Send turn message to each player in DM
    all_players = game["players"]
    for p in all_players:
        try:
            if p["user_id"] == current_player_id:
                await client.send_message(
                    p["user_id"],
                    f"🎯 **It's YOUR turn!**\n\n"
                    f"📊 Range: **{rng['low']}** – **{rng['high']}**\n"
                    f"⏱ Guess in {Config.TURN_TIMEOUT}s!",
                    reply_markup=guess_keyboard(room_code, rng["low"], rng["high"])
                )
            else:
                await client.send_message(
                    p["user_id"],
                    f"⏳ Waiting for **{player_name}** to guess...\n"
                    f"📊 Range: **{rng['low']}** – **{rng['high']}**"
                )
        except Exception as e:
            logger.warning(f"Failed to send turn message to {p['user_id']}: {e}")

    # Start timeout timer
    _cancel_turn_timer(room_code)
    timer = asyncio.create_task(
        _turn_timeout(client, room_code, current_player_id)
    )
    _turn_timers[room_code] = timer


async def process_guess(client: Client, room_code: str, user_id: int, guess: int) -> Optional[str]:
    """Process a player's guess."""
    game = await game_db.get_game(room_code)
    if not game or game["state"] != GameState.ACTIVE:
        return "❌ No active game found."

    active = game["active_players"]
    idx = game["current_turn_index"] % len(active)
    current_player_id = active[idx]

    # Only current player can guess
    if user_id != current_player_id:
        return "⏳ It's not your turn!"

    # Check guess cooldown
    remaining = await cd_db.check_cooldown(user_id, "guess")
    if remaining:
        return f"⏳ Wait {remaining:.1f}s"

    await cd_db.set_cooldown(user_id, "guess", Config.GUESS_COOLDOWN)

    secret = game["secret_number"]
    rng = _guess_ranges.get(room_code, {"low": Config.NUMBER_MIN, "high": Config.NUMBER_MAX})

    # Evaluate guess
    if guess == secret:
        result = "correct"
    elif guess > secret:
        result = "too_high"
        rng["high"] = min(rng["high"], guess - 1)
    else:
        result = "too_low"
        rng["low"] = max(rng["low"], guess + 1)

    _guess_ranges[room_code] = rng

    # Record in DB
    await game_db.record_guess(room_code, user_id, guess, result)

    # Cancel turn timer
    _cancel_turn_timer(room_code)

    player_name = next(
        (p["name"] for p in game["players"] if p["user_id"] == user_id),
        "Player"
    )

    if result == "correct":
        await broadcast_to_players(
            client,
            game["players"],
            f"🎉 **{player_name} WINS!**\n\n"
            f"The number was **{secret}**! 🎯\n"
            f"Guess: **{guess}** ✅"
        )
        await end_game(client, room_code, winner_id=user_id)
    else:
        hint_emoji = "📈 Too High!" if result == "too_high" else "📉 Too Low!"
        await broadcast_to_players(
            client,
            game["players"],
            f"**{player_name}** guessed **{guess}** — {hint_emoji}\n"
            f"📊 New range: **{rng['low']}** – **{rng['high']}**"
        )

        # Advance to next turn
        new_idx = (idx + 1) % len(active)
        await game_db.advance_turn(room_code, new_idx)
        await start_turn(client, room_code)

    return None


async def end_game(client: Client, room_code: str, winner_id: Optional[int]):
    """End a game, distribute rewards, clean up."""
    game = await game_db.get_game(room_code)
    if not game:
        return

    _cancel_turn_timer(room_code)
    _guess_ranges.pop(room_code, None)

    await game_db.finish_game(room_code, winner_id)
    await room_db.update_room_state(room_code, RoomState.FINISHED)

    players = game["players"]

    for player in players:
        pid = player["user_id"]
        if pid == winner_id:
            await user_db.record_win(pid)
            user = await user_db.get_user(pid)
            streak = user.get("streak", 1)
            bonus = min((streak - 1) * Config.STREAK_BONUS, 100)
            total = Config.WIN_COINS + bonus

            await user_db.add_coins(pid, total)

            try:
                streak_msg = f"\n🔥 Streak bonus: +{bonus}" if bonus > 0 else ""
                await client.send_message(
                    pid,
                    f"🏆 **You Won!**\n"
                    f"💰 +{Config.WIN_COINS} coins{streak_msg}\n"
                    f"Total: **+{total} coins**"
                )
            except Exception:
                pass
        else:
            await user_db.record_loss(pid)
            await user_db.add_coins(pid, Config.LOSE_COINS)

            try:
                await client.send_message(
                    pid,
                    f"😔 Better luck next time!\n"
                    f"💰 +{Config.LOSE_COINS} coins (participation)\n\n"
                    f"The answer was **{game['secret_number']}**"
                )
            except Exception:
                pass

    logger.info(f"Game ended in room {room_code} | Winner: {winner_id}")


async def _turn_timeout(client: Client, room_code: str, player_id: int):
    """Called when a player's turn timer expires."""
    await asyncio.sleep(Config.TURN_TIMEOUT)

    game = await game_db.get_game(room_code)
    if not game or game["state"] != GameState.ACTIVE:
        return

    active = game["active_players"]
    if not active or player_id not in active:
        return

    idx = game["current_turn_index"] % len(active)
    if active[idx] != player_id:
        return

    player_name = next(
        (p["name"] for p in game["players"] if p["user_id"] == player_id),
        "A player"
    )

    await user_db.add_coins(player_id, -Config.INACTIVITY_PENALTY)
    await game_db.eliminate_player(room_code, player_id)

    await broadcast_to_players(
        client,
        game["players"],
        f"⏰ **{player_name}** timed out and was eliminated!\n"
        f"💸 -{Config.INACTIVITY_PENALTY} coins penalty"
    )

    game = await game_db.get_game(room_code)
    if game and len(game["active_players"]) <= 1:
        last_player = game["active_players"][0] if game["active_players"] else None
        await end_game(client, room_code, winner_id=last_player)
    elif game:
        new_idx = idx % len(game["active_players"])
        await game_db.advance_turn(room_code, new_idx)
        await start_turn(client, room_code)


def _cancel_turn_timer(room_code: str):
    """Cancel a running turn timer."""
    task = _turn_timers.pop(room_code, None)
    if task and not task.done():
        task.cancel()


async def broadcast_to_players(client: Client, players: list, message: str, chat_id: int = None):
    """Send message to all players in DM."""
    if chat_id:
        try:
            await client.send_message(chat_id, message)
            return
        except Exception as e:
            logger.warning(f"Group broadcast failed: {e}")

    for player in players:
        try:
            await client.send_message(player["user_id"], message)
        except Exception as e:
            logger.warning(f"Broadcast failed for user {player['user_id']}: {e}")

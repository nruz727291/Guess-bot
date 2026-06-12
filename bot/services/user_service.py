"""
user_service.py - Business logic for user operations.
Sits between handlers and database layer.
"""

from db.users import get_user, register_user, update_last_seen
from bot.utils.helpers import win_rate
from bot.constants import get_rank


async def get_or_register(user_id: int, username: str, first_name: str) -> dict:
    """Get existing user or create new one."""
    user = await get_user(user_id)
    if not user:
        user = await register_user(user_id, username or "unknown", first_name or "User")
    else:
        await update_last_seen(user_id)
    return user


def format_profile(user: dict) -> str:
    """Format user profile as a nice Telegram message."""
    wins = user.get("wins", 0)
    losses = user.get("losses", 0)
    games = user.get("games_played", 0)
    streak = user.get("streak", 0)
    max_streak = user.get("max_streak", 0)
    coins = user.get("coins", 0)
    name = user.get("first_name", "Player")
    username = user.get("username", "")
    rank = get_rank(wins)

    return (
        f"👤 **{name}**"
        + (f" (@{username})" if username else "")
        + f"\n\n"
        f"🏅 Rank: **{rank}**\n"
        f"💰 Coins: **{coins:,}**\n\n"
        f"📊 **Stats**\n"
        f"├ 🏆 Wins: {wins}\n"
        f"├ 💀 Losses: {losses}\n"
        f"├ 🎮 Games Played: {games}\n"
        f"├ 📈 Win Rate: {win_rate(wins, games)}\n"
        f"├ 🔥 Current Streak: {streak}\n"
        f"└ ⚡ Max Streak: {max_streak}\n"
    )


def format_leaderboard(users: list, sort_by: str, page: int, per_page: int = 10) -> str:
    """Format leaderboard as numbered list."""
    field_labels = {
        "wins": ("🏆 Top Winners", "wins"),
        "coins": ("💰 Richest Players", "coins"),
        "max_streak": ("🔥 Best Streaks", "max_streak"),
    }
    
    title, field = field_labels.get(sort_by, ("🏆 Leaderboard", "wins"))
    start_num = page * per_page + 1
    
    if not users:
        return f"{title}\n\nNo players found!"
    
    lines = [f"**{title}** (Page {page + 1})\n"]
    
    medals = {0: "🥇", 1: "🥈", 2: "🥉"}
    
    for i, user in enumerate(users):
        abs_pos = start_num + i - 1
        medal = medals.get(abs_pos, f"{abs_pos + 1}.")
        name = user.get("first_name") or user.get("username") or "Player"
        value = user.get(field, 0)
        lines.append(f"{medal} **{name}** — {value:,}")
    
    return "\n".join(lines)

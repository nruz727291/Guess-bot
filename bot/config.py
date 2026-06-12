"""
config.py - Configuration loader
Reads all environment variables and validates them on startup.
If any required variable is missing, bot will NOT start.
"""

import os
from dotenv import load_dotenv

# Load .env file (only works locally, Railway uses its own env vars)
load_dotenv()


class Config:
    """Central configuration class. All settings come from here."""

    # ── Telegram ──────────────────────────────────────────────
    API_ID: int = int(os.environ.get("API_ID", 0))
    API_HASH: str = os.environ.get("API_HASH", "")
    BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")

    # ── MongoDB ───────────────────────────────────────────────
    MONGO_URI: str = os.environ.get("MONGO_URI", "")
    DATABASE_NAME: str = os.environ.get("DATABASE_NAME", "guess_bot_db")

    # ── Bot Settings ──────────────────────────────────────────
    OWNER_ID: int = int(os.environ.get("OWNER_ID", 0))
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

    # ── Game Settings ─────────────────────────────────────────
    MIN_PLAYERS: int = 2
    MAX_PLAYERS: int = 5
    TURN_TIMEOUT: int = 30          # seconds per turn
    ROOM_IDLE_TIMEOUT: int = 300    # 5 min idle = auto delete
    GAME_IDLE_TIMEOUT: int = 600    # 10 min stale game cleanup
    NUMBER_MIN: int = 1
    NUMBER_MAX: int = 100

    # ── Economy ───────────────────────────────────────────────
    WIN_COINS: int = 50
    LOSE_COINS: int = 5             # participation reward
    DAILY_REWARD: int = 30
    STREAK_BONUS: int = 10          # extra per streak level
    RAGEQUIT_PENALTY: int = 15
    INACTIVITY_PENALTY: int = 10

    # ── Cooldowns (seconds) ───────────────────────────────────
    CALLBACK_COOLDOWN: float = 0.5
    ROOM_CREATE_COOLDOWN: int = 10
    GUESS_COOLDOWN: float = 1.0

    @classmethod
    def validate(cls):
        """Check all required env vars are set. Crash early if not."""
        errors = []
        if not cls.API_ID:
            errors.append("API_ID is missing")
        if not cls.API_HASH:
            errors.append("API_HASH is missing")
        if not cls.BOT_TOKEN:
            errors.append("BOT_TOKEN is missing")
        if not cls.MONGO_URI:
            errors.append("MONGO_URI is missing")
        if errors:
            raise EnvironmentError(
                f"Missing environment variables:\n" + "\n".join(errors)
          )

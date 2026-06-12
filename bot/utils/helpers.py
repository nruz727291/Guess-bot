"""
helpers.py - Utility functions used across the project.
"""

import random
import string
from datetime import datetime, timezone


def generate_room_code(length: int = 6) -> str:
    """Generate a random uppercase room code like 'ABC123'."""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


def format_coins(amount: int) -> str:
    """Format coin amount with emoji."""
    return f"💰 {amount:,}"


def safe_int(value, default: int = 0) -> int:
    """Safely convert value to int, return default on failure."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def truncate(text: str, max_len: int = 20) -> str:
    """Truncate long strings with ellipsis."""
    return text[:max_len] + "…" if len(text) > max_len else text


def win_rate(wins: int, total: int) -> str:
    """Calculate and format win rate percentage."""
    if total == 0:
        return "0%"
    rate = (wins / total) * 100
    return f"{rate:.1f}%"

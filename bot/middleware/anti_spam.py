"""
anti_spam.py - Anti-flood middleware.
Tracks message frequency per user and blocks spammers.
Uses in-memory tracking (resets on restart, which is fine for spam).
"""

import time
from collections import defaultdict
from bot.utils.logger import logger

# Track last message time per user: {user_id: last_timestamp}
_last_message: dict[int, float] = defaultdict(float)

# Message count in short window: {user_id: [timestamp1, timestamp2, ...]}
_message_counts: dict[int, list] = defaultdict(list)

# Flood threshold: max messages per window
MAX_MESSAGES = 5
WINDOW_SECONDS = 3.0
MIN_INTERVAL = 0.3  # Min seconds between any two messages


def is_flooding(user_id: int) -> bool:
    """
    Check if user is sending messages too fast.
    Returns True if user should be throttled.
    """
    now = time.time()
    
    # Check minimum interval
    if now - _last_message[user_id] < MIN_INTERVAL:
        return True
    
    _last_message[user_id] = now
    
    # Track message count in window
    counts = _message_counts[user_id]
    # Remove timestamps outside the window
    cutoff = now - WINDOW_SECONDS
    _message_counts[user_id] = [t for t in counts if t > cutoff]
    _message_counts[user_id].append(now)
    
    if len(_message_counts[user_id]) > MAX_MESSAGES:
        logger.warning(f"Flood detected from user {user_id}")
        return True
    
    return False

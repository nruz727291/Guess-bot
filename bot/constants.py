"""
constants.py - All text messages, emojis, and callback prefixes.
Centralizing messages here makes editing easy without touching logic.
"""

# ── Callback Data Prefixes ────────────────────────────────────────────────────
# These prefixes tell the callback router which handler to call

CB_MENU = "menu"
CB_CREATE_ROOM = "create_room"
CB_JOIN_ROOM = "join_room"
CB_QUICK_MATCH = "quick_match"
CB_PROFILE = "profile"
CB_LEADERBOARD = "leaderboard"
CB_DAILY = "daily_reward"
CB_RULES = "rules"
CB_REFRESH = "refresh"
CB_ROOM_SIZE = "room_size"          # room_size:3
CB_JOIN_CODE = "join_code"          # join_code:ABC123
CB_START_GAME = "start_game"        # start_game:ROOMCODE
CB_GUESS = "guess"                  # guess:ROOMCODE:42
CB_LEAVE_ROOM = "leave_room"        # leave_room:ROOMCODE
CB_LEADERBOARD_PAGE = "lb_page"     # lb_page:wins:0
CB_CANCEL_QUEUE = "cancel_queue"

# ── Rank Thresholds ───────────────────────────────────────────────────────────

RANKS = [
    (0,    "🥉 Beginner"),
    (5,    "🥈 Novice"),
    (15,   "🥇 Player"),
    (30,   "💎 Pro"),
    (60,   "🏆 Champion"),
    (100,  "👑 Legend"),
]


def get_rank(wins: int) -> str:
    """Return rank label based on number of wins."""
    rank = RANKS[0][1]
    for threshold, label in RANKS:
        if wins >= threshold:
            rank = label
    return rank


# ── Messages ──────────────────────────────────────────────────────────────────

MSG_WELCOME = """
👋 **Welcome to Guess The Number!**

🎮 A multiplayer number guessing game.
Compete with friends to guess the secret number first!

💡 Use the menu below to get started.
"""

MSG_RULES = """
📖 **How To Play**

1️⃣ One player **creates a room** and shares the code.
2️⃣ Others **join** using that code.
3️⃣ Once everyone's in, the host **starts the game**.
4️⃣ I pick a **secret number between 1 and 100**.
5️⃣ Players take turns guessing — I'll say 📈 Too High or 📉 Too Low.
6️⃣ First player to **guess exactly** wins! 🏆

⏱ Each player has **30 seconds** per turn.
💰 Winners earn **50 coins** + streak bonuses.
🚫 Rage quitting costs you **15 coins**!
"""

MSG_NO_ACTIVE_ROOM = "❌ You don't have an active room. Create one first!"
MSG_ALREADY_IN_ROOM = "⚠️ You're already in a room. Leave it first."
MSG_ROOM_FULL = "❌ That room is full."
MSG_ROOM_NOT_FOUND = "❌ Room not found. Check the code and try again."
MSG_GAME_STARTED = "⚠️ That game has already started."
MSG_NOT_YOUR_TURN = "⏳ It's not your turn yet!"
MSG_DAILY_CLAIMED = "✅ You already claimed your daily reward today!"
MSG_QUEUE_JOINED = "🔍 Looking for players... You're in the queue!\n\nUse /cancel or the button to leave queue."

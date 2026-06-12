"""
states.py - All possible states for rooms and games.
Using string constants prevents typos in comparisons.
"""


class RoomState:
    WAITING = "waiting"      # Room created, waiting for players
    STARTED = "started"      # Game in progress
    FINISHED = "finished"    # Game over


class GameState:
    ACTIVE = "active"        # Game is running
    FINISHED = "finished"    # Game completed
    ABANDONED = "abandoned"  # All players left

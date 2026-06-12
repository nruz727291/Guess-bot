"""
handlers/__init__.py - Register all handlers onto the Pyrogram client.
Import order matters: catchall callback must be LAST.
"""

from pyrogram import Client
from . import start, room, game, profile, economy, callbacks


def register_all(app: Client):
    """Call this once at startup to register all handlers."""
    start.register(app)
    room.register(app)
    game.register(app)
    profile.register(app)
    economy.register(app)
    callbacks.register(app)  # ← MUST BE LAST (catch-all)

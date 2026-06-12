"""
custom_filters.py - Custom Pyrogram filters.
"""

from pyrogram import filters
from bot.config import Config


# Filter: only owner can use admin commands
owner_filter = filters.user(Config.OWNER_ID) if Config.OWNER_ID else filters.user([])

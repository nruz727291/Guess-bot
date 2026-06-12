"""
background.py - Async background tasks.
These run continuously in the background to clean up stale data.
Each task is an infinite loop with a sleep interval.
"""

import asyncio
from pyrogram import Client
from bot.utils.logger import logger
from bot.services.matchmaking import process_queue, cleanup_old_queue_entries
import db.rooms as room_db
import db.games as game_db


async def room_cleanup_task():
    """
    Periodically delete stale WAITING rooms.
    Runs every 60 seconds.
    """
    logger.info("Background task started: room_cleanup")
    while True:
        try:
            await asyncio.sleep(60)
            deleted = await room_db.cleanup_stale_rooms(idle_seconds=300)
            if deleted:
                logger.info(f"[Cleanup] Deleted {deleted} stale rooms")
        except asyncio.CancelledError:
            break  # Bot is shutting down
        except Exception as e:
            logger.error(f"[Cleanup] Room cleanup error: {e}")


async def game_cleanup_task():
    """
    Periodically delete stale active games.
    Runs every 120 seconds.
    """
    logger.info("Background task started: game_cleanup")
    while True:
        try:
            await asyncio.sleep(120)
            deleted = await game_db.cleanup_stale_games(idle_seconds=600)
            if deleted:
                logger.info(f"[Cleanup] Deleted {deleted} stale games")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[Cleanup] Game cleanup error: {e}")


async def matchmaking_task(client: Client):
    """
    Periodically check the quick match queue and create rooms.
    Runs every 5 seconds.
    """
    logger.info("Background task started: matchmaking")
    while True:
        try:
            await asyncio.sleep(5)
            
            # Clean up old queue entries first
            await cleanup_old_queue_entries(max_wait_seconds=120)
            
            # Try to create a match
            room = await process_queue(client)
            if room:
                logger.info(f"[Matchmaking] Created room {room['room_code']}")
        
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[Matchmaking] Error: {e}")


async def start_background_tasks(client: Client) -> list:
    """
    Start all background tasks.
    Returns list of task objects (to cancel on shutdown).
    """
    tasks = [
        asyncio.create_task(room_cleanup_task()),
        asyncio.create_task(game_cleanup_task()),
        asyncio.create_task(matchmaking_task(client)),
    ]
    logger.info(f"✅ Started {len(tasks)} background tasks")
    return tasks


async def stop_background_tasks(tasks: list):
    """Cancel all background tasks gracefully."""
    for task in tasks:
        task.cancel()
    
    # Wait for tasks to finish canceling
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("Background tasks stopped.")

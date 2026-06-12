"""
main.py - Bot entry point.
This is the file Railway and Procfile will run.

Flow:
1. Validate environment variables
2. Connect to MongoDB
3. Create Pyrogram client
4. Register all handlers
5. Start background tasks
6. Run bot (blocking until stopped)
7. Graceful shutdown
"""

import asyncio
import signal
import sys

from bot.config import Config
from bot.utils.logger import logger, setup_logger
from bot.client import create_client
from bot.handlers import register_all
from bot.tasks import start_background_tasks, stop_background_tasks
from db.connection import Database


# Global list of background tasks for cleanup
_bg_tasks = []


async def main():
    """Main async entry point."""
    
    # ── Step 1: Setup Logger ──────────────────────────────────
    setup_logger("guess_bot", Config.LOG_LEVEL)
    logger.info("=" * 50)
    logger.info("🎮 Guess The Number Bot - Starting Up")
    logger.info("=" * 50)
    
    # ── Step 2: Validate Configuration ───────────────────────
    try:
        Config.validate()
        logger.info("✅ Configuration validated")
    except EnvironmentError as e:
        logger.critical(f"❌ Configuration error: {e}")
        sys.exit(1)
    
    # ── Step 3: Connect to MongoDB ────────────────────────────
    try:
        await Database.connect()
    except Exception as e:
        logger.critical(f"❌ Database connection failed: {e}")
        sys.exit(1)
    
    # ── Step 4: Create Pyrogram Client ────────────────────────
    client = create_client()
    
    # ── Step 5: Register All Handlers ────────────────────────
    register_all(client)
    logger.info("✅ All handlers registered")
    
    # ── Step 6: Start Bot ────────────────────────────────────
    try:
        await client.start()
        me = await client.get_me()
        logger.info(f"✅ Bot started as @{me.username} (ID: {me.id})")
        
        # ── Step 7: Start Background Tasks ───────────────────
        global _bg_tasks
        _bg_tasks = await start_background_tasks(client)
        
        logger.info("🟢 Bot is running! Press Ctrl+C to stop.")
        logger.info("=" * 50)
        
        # ── Step 8: Keep Bot Running ─────────────────────────
        # This blocks until the bot is stopped
        await asyncio.Event().wait()
    
    except KeyboardInterrupt:
        logger.info("⚠️ Keyboard interrupt received")
    
    except Exception as e:
        logger.critical(f"❌ Fatal error: {e}", exc_info=True)
    
    finally:
        # ── Step 9: Graceful Shutdown ─────────────────────────
        logger.info("Shutting down gracefully...")
        
        # Stop background tasks
        if _bg_tasks:
            await stop_background_tasks(_bg_tasks)
        
        # Stop Pyrogram client
        try:
            await client.stop()
        except Exception:
            pass
        
        # Disconnect MongoDB
        await Database.disconnect()
        
        logger.info("✅ Shutdown complete. Goodbye!")


if __name__ == "__main__":
    # Handle graceful shutdown on SIGTERM (Railway sends this on deploy)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    def handle_sigterm(*args):
        logger.info("SIGTERM received, shutting down...")
        for task in asyncio.all_tasks(loop):
            task.cancel()
    
    signal.signal(signal.SIGTERM, handle_sigterm)
    
    try:
        loop.run_until_complete(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        loop.close()

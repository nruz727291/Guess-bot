"""
connection.py - MongoDB Atlas async connection manager.
Uses Motor (async MongoDB driver).
Single connection instance shared across the app.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bot.config import Config
from bot.utils.logger import logger


class Database:
    """
    Singleton-style database manager.
    Call Database.connect() once at startup.
    Then use Database.db to access collections.
    """
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

    @classmethod
    async def connect(cls):
        """Initialize MongoDB connection and create indexes."""
        logger.info("Connecting to MongoDB Atlas...")
        try:
            cls.client = AsyncIOMotorClient(Config.MONGO_URI)
            cls.db = cls.client[Config.DATABASE_NAME]

            # Verify connection works
            await cls.client.admin.command("ping")
            logger.info(f"✅ Connected to MongoDB: {Config.DATABASE_NAME}")

            # Create all indexes for performance
            await cls._create_indexes()

        except Exception as e:
            logger.critical(f"❌ MongoDB connection failed: {e}")
            raise

    @classmethod
    async def disconnect(cls):
        """Close MongoDB connection on shutdown."""
        if cls.client:
            cls.client.close()
            logger.info("MongoDB connection closed.")

    @classmethod
    async def _create_indexes(cls):
        """Create database indexes for fast queries."""
        db = cls.db

        # Users collection indexes
        await db.users.create_index("user_id", unique=True)
        await db.users.create_index("coins")
        await db.users.create_index("wins")

        # Rooms collection indexes
        await db.rooms.create_index("room_code", unique=True)
        await db.rooms.create_index("state")
        await db.rooms.create_index("owner_id")
        # TTL index: auto-delete finished rooms after 1 hour
        await db.rooms.create_index(
            "created_at",
            expireAfterSeconds=3600
        )

        # Active games indexes
        await db.active_games.create_index("room_code", unique=True)
        await db.active_games.create_index("state")
        await db.active_games.create_index("last_activity")

        # Cooldowns TTL index: auto-expire
        await db.cooldowns.create_index(
            "expires_at",
            expireAfterSeconds=0  # TTL controlled by document's expires_at
        )

        # Quick match queue
        await db.quick_match_queue.create_index("user_id", unique=True)
        await db.quick_match_queue.create_index("joined_at")

        logger.info("✅ Database indexes created.")


# Convenience accessor
def get_db() -> AsyncIOMotorDatabase:
    """Get the database instance. Must call Database.connect() first."""
    if Database.db is None:
        raise RuntimeError("Database not connected. Call Database.connect() first.")
    return Database.db

"""Database configuration and connection management."""
import asyncpg
from typing import Optional
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """PostgreSQL database configuration and connection pool manager."""
    
    def __init__(self):
        """Initialize database configuration."""
        self.pool: Optional[asyncpg.Pool] = None
        self._initialized = False
    
    async def connect(self):
        """Create database connection pool."""
        if self._initialized:
            logger.warning("Database pool already initialized")
            return
        
        try:
            self.pool = await asyncpg.create_pool(
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                database=settings.POSTGRES_DB,
                min_size=settings.POSTGRES_MIN_POOL_SIZE,
                max_size=settings.POSTGRES_MAX_POOL_SIZE,
                command_timeout=60,
            )
            self._initialized = True
            logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise
    
    async def disconnect(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            self._initialized = False
            logger.info("Database connection pool closed")
    
    async def get_connection(self) -> asyncpg.Connection:
        """Get a connection from the pool."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        return await self.pool.acquire()
    
    async def release_connection(self, connection: asyncpg.Connection):
        """Release a connection back to the pool."""
        if self.pool:
            await self.pool.release(connection)
    
    async def health_check(self) -> bool:
        """Check if database is healthy."""
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database instance
db_config = DatabaseConfig()

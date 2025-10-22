"""Database query executor - raw SQL without ORM."""
from typing import Any, Optional, List, Dict
import asyncpg
import logging

from app.config.database import db_config

logger = logging.getLogger(__name__)


class QueryExecutor:
    """Execute raw SQL queries on PostgreSQL database."""
    
    def __init__(self):
        """Initialize query executor."""
        self.db = db_config
    
    async def execute(
        self, 
        query: str, 
        *args,
        timeout: Optional[float] = None
    ) -> str:
        """
        Execute a query that doesn't return data (INSERT, UPDATE, DELETE).
        
        Args:
            query: SQL query string
            *args: Query parameters
            timeout: Query timeout in seconds
            
        Returns:
            Query execution status
        """
        try:
            async with self.db.pool.acquire() as conn:
                result = await conn.execute(query, *args, timeout=timeout)
                logger.debug(f"Executed query: {query[:100]}... | Result: {result}")
                return result
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    async def fetch_one(
        self, 
        query: str, 
        *args,
        timeout: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a single row from the database.
        
        Args:
            query: SQL query string
            *args: Query parameters
            timeout: Query timeout in seconds
            
        Returns:
            Dictionary representing the row, or None
        """
        try:
            async with self.db.pool.acquire() as conn:
                row = await conn.fetchrow(query, *args, timeout=timeout)
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Fetch one failed: {e}")
            raise
    
    async def fetch_all(
        self, 
        query: str, 
        *args,
        timeout: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all rows from the database.
        
        Args:
            query: SQL query string
            *args: Query parameters
            timeout: Query timeout in seconds
            
        Returns:
            List of dictionaries representing rows
        """
        try:
            async with self.db.pool.acquire() as conn:
                rows = await conn.fetch(query, *args, timeout=timeout)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Fetch all failed: {e}")
            raise
    
    async def fetch_val(
        self, 
        query: str, 
        *args,
        column: int = 0,
        timeout: Optional[float] = None
    ) -> Any:
        """
        Fetch a single value from the database.
        
        Args:
            query: SQL query string
            *args: Query parameters
            column: Column index to fetch
            timeout: Query timeout in seconds
            
        Returns:
            Single value
        """
        try:
            async with self.db.pool.acquire() as conn:
                value = await conn.fetchval(query, *args, column=column, timeout=timeout)
                return value
        except Exception as e:
            logger.error(f"Fetch value failed: {e}")
            raise
    
    async def execute_many(
        self, 
        query: str, 
        args_list: List[tuple],
        timeout: Optional[float] = None
    ) -> None:
        """
        Execute a query multiple times with different parameters.
        
        Args:
            query: SQL query string
            args_list: List of parameter tuples
            timeout: Query timeout in seconds
        """
        try:
            async with self.db.pool.acquire() as conn:
                await conn.executemany(query, args_list, timeout=timeout)
                logger.debug(f"Executed {len(args_list)} queries")
        except Exception as e:
            logger.error(f"Execute many failed: {e}")
            raise
    
    async def transaction(self):
        """
        Get a transaction context manager.
        
        Usage:
            async with query_executor.transaction() as conn:
                await conn.execute("INSERT INTO ...")
                await conn.execute("UPDATE ...")
        """
        conn = await self.db.pool.acquire()
        return TransactionContext(conn, self.db)


class TransactionContext:
    """Context manager for database transactions."""
    
    def __init__(self, conn: asyncpg.Connection, db):
        """Initialize transaction context."""
        self.conn = conn
        self.db = db
        self.transaction = None
    
    async def __aenter__(self):
        """Enter transaction context."""
        self.transaction = self.conn.transaction()
        await self.transaction.start()
        return self.conn
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit transaction context."""
        try:
            if exc_type is not None:
                await self.transaction.rollback()
                logger.warning("Transaction rolled back due to error")
            else:
                await self.transaction.commit()
                logger.debug("Transaction committed")
        finally:
            await self.db.release_connection(self.conn)


# Global query executor instance
query_executor = QueryExecutor()

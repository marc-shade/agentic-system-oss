#!/usr/bin/env python3
"""
Database Connection Pool for Enhanced Memory MCP

Provides thread-safe SQLite connection pooling with:
- Busy timeout for lock handling
- Connection recycling
- Health monitoring
- Retry logic for locked operations
"""

import sqlite3
import threading
import time
import logging
from pathlib import Path
from contextlib import contextmanager
from collections import deque
from typing import Optional, Any, Generator

logger = logging.getLogger("db-pool")

# Configuration
SQLITE_BUSY_TIMEOUT = 30000  # 30 seconds
MAX_POOL_SIZE = 5
CONNECTION_TIMEOUT = 120  # seconds before recycling
MAX_RETRIES = 3
RETRY_DELAY = 0.5

# Default database path
DEFAULT_DB_PATH = Path.home() / ".claude" / "enhanced_memories" / "memory.db"


class DatabasePool:
    """Thread-safe SQLite connection pool with retry logic"""

    _instance: Optional['DatabasePool'] = None
    _lock = threading.Lock()

    def __new__(cls, db_path: Path = DEFAULT_DB_PATH):
        """Singleton pattern for global pool access"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        if getattr(self, '_initialized', False):
            return

        self.db_path = db_path
        self._pool: deque = deque()
        self._pool_lock = threading.Lock()
        self._connection_times: dict = {}
        self._initialized = True

        logger.info(f"Database pool initialized for {db_path}")

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with proper settings"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=SQLITE_BUSY_TIMEOUT / 1000,
            check_same_thread=False,
            isolation_level=None  # Autocommit mode
        )

        # Configure for concurrent access
        conn.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT}")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA cache_size = -64000")  # 64MB cache

        # Switch back to manual transaction mode
        conn.isolation_level = "DEFERRED"

        return conn

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a connection from the pool with automatic recycling"""
        conn = None
        conn_id = None

        with self._pool_lock:
            while self._pool:
                conn = self._pool.popleft()
                conn_id = id(conn)

                # Check if connection is too old
                creation_time = self._connection_times.get(conn_id, 0)
                if time.time() - creation_time > CONNECTION_TIMEOUT:
                    try:
                        conn.close()
                    except:
                        pass
                    self._connection_times.pop(conn_id, None)
                    conn = None
                    continue

                # Test connection is valid
                try:
                    conn.execute("SELECT 1")
                    break
                except:
                    try:
                        conn.close()
                    except:
                        pass
                    conn = None

            if conn is None:
                conn = self._create_connection()
                conn_id = id(conn)
                self._connection_times[conn_id] = time.time()

        try:
            yield conn
        finally:
            with self._pool_lock:
                if len(self._pool) < MAX_POOL_SIZE:
                    try:
                        conn.rollback()
                        self._pool.append(conn)
                    except:
                        try:
                            conn.close()
                        except:
                            pass
                        self._connection_times.pop(conn_id, None)
                else:
                    try:
                        conn.close()
                    except:
                        pass
                    self._connection_times.pop(conn_id, None)

    def execute_with_retry(self, sql: str, params: tuple = (),
                           fetch: str = 'none') -> Any:
        """Execute SQL with retry logic for locks

        Args:
            sql: SQL statement to execute
            params: Parameters for the SQL
            fetch: 'none', 'one', 'all', or 'lastrowid'

        Returns:
            Query result based on fetch type
        """
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(sql, params)

                    if fetch == 'one':
                        result = cursor.fetchone()
                    elif fetch == 'all':
                        result = cursor.fetchall()
                    elif fetch == 'lastrowid':
                        result = cursor.lastrowid
                    else:
                        result = None

                    conn.commit()
                    return result

            except sqlite3.OperationalError as e:
                last_error = e
                if "database is locked" in str(e):
                    if attempt < MAX_RETRIES - 1:
                        delay = RETRY_DELAY * (attempt + 1)
                        logger.warning(f"Database locked, retry {attempt + 1}/{MAX_RETRIES} after {delay}s")
                        time.sleep(delay)
                        continue
                raise

        if last_error:
            raise last_error

    def execute_many_with_retry(self, sql: str, params_list: list) -> int:
        """Execute many SQL statements with retry logic

        Returns:
            Number of rows affected
        """
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.executemany(sql, params_list)
                    conn.commit()
                    return cursor.rowcount

            except sqlite3.OperationalError as e:
                last_error = e
                if "database is locked" in str(e):
                    if attempt < MAX_RETRIES - 1:
                        delay = RETRY_DELAY * (attempt + 1)
                        logger.warning(f"Database locked, retry {attempt + 1}/{MAX_RETRIES}")
                        time.sleep(delay)
                        continue
                raise

        if last_error:
            raise last_error
        return 0

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for explicit transactions with retry"""
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                with self.get_connection() as conn:
                    conn.execute("BEGIN IMMEDIATE")
                    try:
                        yield conn
                        conn.commit()
                        return
                    except:
                        conn.rollback()
                        raise

            except sqlite3.OperationalError as e:
                last_error = e
                if "database is locked" in str(e):
                    if attempt < MAX_RETRIES - 1:
                        delay = RETRY_DELAY * (attempt + 1)
                        logger.warning(f"Transaction locked, retry {attempt + 1}/{MAX_RETRIES}")
                        time.sleep(delay)
                        continue
                raise

        if last_error:
            raise last_error

    def checkpoint_wal(self):
        """Force WAL checkpoint"""
        try:
            with self.get_connection() as conn:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                logger.info("WAL checkpoint complete")
        except Exception as e:
            logger.error(f"WAL checkpoint failed: {e}")

    def clear_pool(self):
        """Clear all pooled connections"""
        with self._pool_lock:
            while self._pool:
                conn = self._pool.popleft()
                try:
                    conn.close()
                except:
                    pass
            self._connection_times.clear()
            logger.info("Connection pool cleared")


# Global pool instance
_pool: Optional[DatabasePool] = None


def get_pool(db_path: Path = DEFAULT_DB_PATH) -> DatabasePool:
    """Get the global database pool instance"""
    global _pool
    if _pool is None:
        _pool = DatabasePool(db_path)
    return _pool


def get_connection():
    """Convenience function to get a connection from the global pool"""
    return get_pool().get_connection()


def execute_with_retry(sql: str, params: tuple = (), fetch: str = 'none') -> Any:
    """Convenience function for executing SQL with retry"""
    return get_pool().execute_with_retry(sql, params, fetch)


def transaction():
    """Convenience function for transactions"""
    return get_pool().transaction()

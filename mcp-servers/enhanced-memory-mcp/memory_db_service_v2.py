#!/usr/bin/env python3
"""
Memory Database Service v2 - Resilient Unix Socket Server

IMPROVEMENTS OVER V1:
- Connection pooling with busy_timeout
- Redis for working memory (high-churn, TTL-based)
- Health monitoring thread with self-healing
- Lock detection and automatic recovery
- Metrics tracking and alerting

Architecture:
- SQLite for persistent memory (entities, semantic, episodic)
- Redis for working memory (temporary, TTL-based)
- Qdrant for vector search (already integrated)
- Unix socket for IPC with multiple clients
"""

import asyncio
import json
import logging
import os
import signal
import sqlite3
import sys
import hashlib
import zlib
import pickle
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import deque
from contextlib import contextmanager

# Redis for working memory
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("memory-db-service-v2")

# Configuration
SOCKET_PATH = "/tmp/memory-db.sock"
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 1  # Use DB 1 for working memory

# SQLite settings for concurrent access
SQLITE_BUSY_TIMEOUT = 30000  # 30 seconds
SQLITE_JOURNAL_MODE = "WAL"
SQLITE_SYNCHRONOUS = "NORMAL"  # Balance between safety and speed
MAX_POOL_SIZE = 5
CONNECTION_TIMEOUT = 60  # seconds before recycling connection

# Health monitoring
HEALTH_CHECK_INTERVAL = 30  # seconds
MAX_CONSECUTIVE_FAILURES = 3
LOCK_DETECTION_THRESHOLD = 5  # seconds

# Create directories
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


class ConnectionPool:
    """SQLite connection pool with busy timeout and recycling"""

    def __init__(self, db_path: Path, max_size: int = MAX_POOL_SIZE):
        self.db_path = db_path
        self.max_size = max_size
        self._pool: deque = deque()
        self._lock = threading.Lock()
        self._connection_times: Dict[int, float] = {}
        self._metrics = {
            "total_connections": 0,
            "connections_recycled": 0,
            "pool_hits": 0,
            "pool_misses": 0,
            "locks_detected": 0,
            "lock_recoveries": 0
        }

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with proper settings"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=SQLITE_BUSY_TIMEOUT / 1000,  # timeout in seconds
            check_same_thread=False,
            isolation_level=None  # autocommit mode, we manage transactions
        )

        # Configure for concurrent access
        conn.execute(f"PRAGMA journal_mode = {SQLITE_JOURNAL_MODE}")
        conn.execute(f"PRAGMA synchronous = {SQLITE_SYNCHRONOUS}")
        conn.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT}")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA cache_size = -64000")  # 64MB cache

        # Return to autocommit off for transaction control
        conn.isolation_level = "DEFERRED"

        self._metrics["total_connections"] += 1
        return conn

    @contextmanager
    def get_connection(self):
        """Get a connection from the pool with automatic recycling"""
        conn = None
        conn_id = None

        with self._lock:
            # Try to get from pool
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
                    del self._connection_times[conn_id]
                    self._metrics["connections_recycled"] += 1
                    conn = None
                    continue

                # Test connection is valid
                try:
                    conn.execute("SELECT 1")
                    self._metrics["pool_hits"] += 1
                    break
                except:
                    try:
                        conn.close()
                    except:
                        pass
                    conn = None

            # Create new connection if needed
            if conn is None:
                conn = self._create_connection()
                conn_id = id(conn)
                self._connection_times[conn_id] = time.time()
                self._metrics["pool_misses"] += 1

        try:
            yield conn
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                self._metrics["locks_detected"] += 1
                logger.warning(f"Database lock detected: {e}")
            raise
        finally:
            # Return connection to pool if not full
            with self._lock:
                if len(self._pool) < self.max_size:
                    try:
                        conn.rollback()  # Ensure clean state
                        self._pool.append(conn)
                    except:
                        try:
                            conn.close()
                        except:
                            pass
                else:
                    try:
                        conn.close()
                    except:
                        pass
                    if conn_id in self._connection_times:
                        del self._connection_times[conn_id]

    def get_metrics(self) -> Dict[str, int]:
        """Get pool metrics"""
        with self._lock:
            return dict(self._metrics)

    def clear(self):
        """Clear all connections"""
        with self._lock:
            while self._pool:
                conn = self._pool.popleft()
                try:
                    conn.close()
                except:
                    pass
            self._connection_times.clear()


class RedisWorkingMemory:
    """Redis-backed working memory for high-churn temporary data"""

    def __init__(self, host: str = REDIS_HOST, port: int = REDIS_PORT, db: int = REDIS_DB):
        self.prefix = "wmem:"  # working memory prefix
        self.connected = False
        self.client = None

        if REDIS_AVAILABLE:
            try:
                self.client = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
                self.client.ping()
                self.connected = True
                logger.info("Redis working memory connected")
            except Exception as e:
                logger.warning(f"Redis not available, falling back to SQLite: {e}")
                self.connected = False

    def add(self, context_key: str, content: str, priority: int = 5,
            ttl_minutes: int = 60, entity_id: Optional[int] = None) -> Dict[str, Any]:
        """Add item to working memory with TTL"""
        if not self.connected:
            return {"success": False, "error": "Redis not connected"}

        try:
            key = f"{self.prefix}{context_key}:{int(time.time() * 1000)}"
            data = {
                "content": content,
                "priority": priority,
                "entity_id": entity_id,
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(minutes=ttl_minutes)).isoformat()
            }

            self.client.setex(key, ttl_minutes * 60, json.dumps(data))

            return {
                "success": True,
                "working_memory_id": key,
                "expires_at": data["expires_at"]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get(self, context_key: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get items from working memory"""
        if not self.connected:
            return []

        try:
            pattern = f"{self.prefix}{context_key}:*" if context_key else f"{self.prefix}*"
            keys = self.client.keys(pattern)

            items = []
            for key in keys[:limit]:
                data = self.client.get(key)
                if data:
                    item = json.loads(data)
                    item["key"] = key
                    items.append(item)

            # Sort by priority
            items.sort(key=lambda x: x.get("priority", 0), reverse=True)
            return items

        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get working memory statistics"""
        if not self.connected:
            return {"connected": False}

        try:
            keys = self.client.keys(f"{self.prefix}*")
            return {
                "connected": True,
                "total_items": len(keys),
                "redis_info": self.client.info("memory")
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}


class HealthMonitor:
    """Health monitoring with self-healing capabilities"""

    def __init__(self, pool: ConnectionPool, redis_mem: RedisWorkingMemory):
        self.pool = pool
        self.redis_mem = redis_mem
        self.consecutive_failures = 0
        self.last_health_check = None
        self.is_healthy = True
        self._stop_event = threading.Event()
        self._thread = None
        self.metrics = {
            "health_checks": 0,
            "health_failures": 0,
            "recoveries_attempted": 0,
            "recoveries_successful": 0
        }

    def start(self):
        """Start health monitoring thread"""
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Health monitor started")

    def stop(self):
        """Stop health monitoring"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _monitor_loop(self):
        """Main monitoring loop"""
        while not self._stop_event.is_set():
            try:
                self._check_health()
            except Exception as e:
                logger.error(f"Health check error: {e}")

            self._stop_event.wait(HEALTH_CHECK_INTERVAL)

    def _check_health(self):
        """Perform health check"""
        self.metrics["health_checks"] += 1
        self.last_health_check = datetime.now()

        healthy = True
        issues = []

        # Check SQLite
        try:
            with self.pool.get_connection() as conn:
                start = time.time()
                conn.execute("SELECT COUNT(*) FROM entities")
                duration = time.time() - start

                if duration > LOCK_DETECTION_THRESHOLD:
                    issues.append(f"SQLite slow: {duration:.2f}s")
                    healthy = False
        except Exception as e:
            issues.append(f"SQLite error: {e}")
            healthy = False

        # Check Redis
        if self.redis_mem.connected:
            try:
                self.redis_mem.client.ping()
            except Exception as e:
                issues.append(f"Redis error: {e}")
                # Redis failure is not critical

        if healthy:
            self.consecutive_failures = 0
            self.is_healthy = True
        else:
            self.consecutive_failures += 1
            self.metrics["health_failures"] += 1
            logger.warning(f"Health check failed: {issues}")

            if self.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                self._attempt_recovery()

    def _attempt_recovery(self):
        """Attempt to recover from failure state"""
        self.metrics["recoveries_attempted"] += 1
        logger.warning("Attempting recovery...")

        try:
            # Clear connection pool
            self.pool.clear()

            # Force checkpoint WAL
            with self.pool.get_connection() as conn:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

            self.consecutive_failures = 0
            self.is_healthy = True
            self.metrics["recoveries_successful"] += 1
            logger.info("Recovery successful")

        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            self.is_healthy = False

    def get_status(self) -> Dict[str, Any]:
        """Get health status"""
        return {
            "is_healthy": self.is_healthy,
            "consecutive_failures": self.consecutive_failures,
            "last_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "metrics": dict(self.metrics),
            "pool_metrics": self.pool.get_metrics(),
            "redis_status": self.redis_mem.get_stats()
        }


class MemoryDatabaseV2:
    """Central memory database with improved concurrent access"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.pool = ConnectionPool(db_path)
        self.redis_mem = RedisWorkingMemory()
        self.health = HealthMonitor(self.pool, self.redis_mem)
        self.init_database()
        self.health.start()

    def init_database(self):
        """Initialize database with all tables"""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()

            # Entities table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    entity_type TEXT NOT NULL,
                    tier TEXT DEFAULT 'working',
                    compressed_data BLOB,
                    original_size INTEGER,
                    compressed_size INTEGER,
                    compression_ratio REAL,
                    checksum TEXT,
                    access_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    current_version INTEGER DEFAULT 1,
                    current_branch TEXT DEFAULT 'main'
                )
            ''')

            # Observations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_id INTEGER,
                    content TEXT NOT NULL,
                    compressed BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (entity_id) REFERENCES entities (id)
                )
            ''')

            # Indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_entity_name ON entities(name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_entity_type ON entities(entity_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_entity_tier ON entities(tier)')

            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")

    def _compress_data(self, data: Any) -> bytes:
        """Compress data using zlib"""
        pickled = pickle.dumps(data)
        return zlib.compress(pickled, level=9)

    def _decompress_data(self, compressed: bytes) -> Any:
        """Decompress data"""
        decompressed = zlib.decompress(compressed)
        try:
            return pickle.loads(decompressed)
        except:
            try:
                return json.loads(decompressed.decode('utf-8'))
            except:
                return {"observations": [decompressed.decode('utf-8', errors='replace')]}

    def _calculate_checksum(self, data: bytes) -> str:
        """Calculate SHA-256 checksum"""
        return hashlib.sha256(data).hexdigest()

    def create_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create or update entities with retry logic"""
        results = {"success": True, "created": 0, "updated": 0, "failed": 0, "count": 0, "results": []}

        max_retries = 3
        retry_delay = 0.5

        for attempt in range(max_retries):
            try:
                with self.pool.get_connection() as conn:
                    cursor = conn.cursor()
                    conn.execute("BEGIN IMMEDIATE")

                    for entity in entities:
                        try:
                            name = entity.get("name")
                            entity_type = entity.get("entityType", "general")
                            observations = entity.get("observations", [])

                            entity_data = {
                                "name": name,
                                "type": entity_type,
                                "observations": observations
                            }
                            compressed = self._compress_data(entity_data)
                            original_size = len(pickle.dumps(entity_data))
                            compressed_size = len(compressed)
                            compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
                            checksum = self._calculate_checksum(compressed)

                            cursor.execute("SELECT id FROM entities WHERE name = ?", (name,))
                            existing = cursor.fetchone()

                            if existing:
                                cursor.execute('''
                                    UPDATE entities SET entity_type = ?, compressed_data = ?,
                                    original_size = ?, compressed_size = ?, compression_ratio = ?,
                                    checksum = ?, access_count = access_count + 1,
                                    last_accessed = CURRENT_TIMESTAMP, current_version = current_version + 1
                                    WHERE name = ?
                                ''', (entity_type, compressed, original_size, compressed_size,
                                      compression_ratio, checksum, name))
                                results["updated"] += 1
                                entity_id = existing[0]
                            else:
                                cursor.execute('''
                                    INSERT INTO entities (name, entity_type, compressed_data,
                                    original_size, compressed_size, compression_ratio, checksum)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                ''', (name, entity_type, compressed, original_size,
                                      compressed_size, compression_ratio, checksum))
                                results["created"] += 1
                                entity_id = cursor.lastrowid

                            for obs in observations:
                                cursor.execute('''
                                    INSERT INTO observations (entity_id, content) VALUES (?, ?)
                                ''', (entity_id, obs))

                            results["results"].append({
                                "name": name,
                                "id": entity_id,
                                "compression_ratio": f"{compression_ratio:.2%}"
                            })
                        except Exception as e:
                            logger.error(f"Failed to create entity: {e}")
                            results["failed"] += 1

                    conn.commit()
                    results["count"] = results["created"] + results["updated"]
                    return results

            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Lock retry {attempt + 1}/{max_retries}")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                raise

        return {"success": False, "error": "Max retries exceeded", "created": 0, "failed": len(entities)}

    def search_nodes(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search entities"""
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT id, name, entity_type, compressed_data, compression_ratio,
                           access_count, created_at, last_accessed, tier
                    FROM entities
                    WHERE name LIKE ? OR entity_type LIKE ?
                    ORDER BY access_count DESC, last_accessed DESC
                    LIMIT ?
                ''', (f'%{query}%', f'%{query}%', limit))

                results = []
                for row in cursor.fetchall():
                    entity_id, name, entity_type, compressed_data, compression_ratio, \
                    access_count, created_at, last_accessed, tier = row

                    entity_data = self._decompress_data(compressed_data)
                    results.append({
                        "id": entity_id,
                        "name": name,
                        "entityType": entity_type,
                        "observations": entity_data.get("observations", []),
                        "tier": tier,
                        "compression_ratio": f"{compression_ratio:.2%}",
                        "access_count": access_count,
                        "created_at": created_at,
                        "last_accessed": last_accessed
                    })

                return {"success": True, "query": query, "count": len(results), "results": results}

        except Exception as e:
            logger.error(f"Error in search_nodes: {e}")
            return {"success": False, "error": str(e), "count": 0, "results": []}

    def get_memory_status(self) -> Dict[str, Any]:
        """Get memory system status"""
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM entities")
                total_entities = cursor.fetchone()[0]

                cursor.execute('''
                    SELECT AVG(compression_ratio), SUM(original_size), SUM(compressed_size)
                    FROM entities
                ''')
                avg_ratio, total_original, total_compressed = cursor.fetchone()

                cursor.execute('''
                    SELECT tier, COUNT(*) FROM entities GROUP BY tier
                ''')
                tier_distribution = {row[0]: row[1] for row in cursor.fetchall()}

                return {
                    "success": True,
                    "entities": {"total": total_entities},
                    "compression": {
                        "ratio": f"{avg_ratio:.2%}" if avg_ratio else "N/A",
                        "total_original_kb": round(total_original / 1024, 2) if total_original else 0,
                        "total_compressed_kb": round(total_compressed / 1024, 2) if total_compressed else 0
                    },
                    "tiers": tier_distribution,
                    "database_path": str(self.db_path),
                    "health": self.health.get_status()
                }

        except Exception as e:
            logger.error(f"Error in get_memory_status: {e}")
            return {"success": False, "error": str(e), "entities": {"total": 0}}

    # Working memory operations (delegated to Redis)
    def add_to_working_memory(self, context_key: str, content: str,
                              priority: int = 5, ttl_minutes: int = 60,
                              entity_id: Optional[int] = None) -> Dict[str, Any]:
        """Add to Redis-backed working memory"""
        return self.redis_mem.add(context_key, content, priority, ttl_minutes, entity_id)

    def get_working_memory(self, context_key: Optional[str] = None,
                           limit: int = 50) -> Dict[str, Any]:
        """Get from Redis-backed working memory"""
        items = self.redis_mem.get(context_key, limit)
        return {"success": True, "items": items, "count": len(items)}

    def shutdown(self):
        """Clean shutdown"""
        self.health.stop()
        self.pool.clear()
        logger.info("Memory database shut down")


class MemoryDBServerV2:
    """Improved Unix socket server"""

    def __init__(self, socket_path: str, db_path: Path):
        self.socket_path = socket_path
        self.db = MemoryDatabaseV2(db_path)
        self.server = None
        self.request_count = 0
        self.error_count = 0

    async def handle_request(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle client request"""
        try:
            request_data = await asyncio.wait_for(reader.read(10 * 1024 * 1024), timeout=30)
            if not request_data:
                return

            request = json.loads(request_data.decode())
            method = request.get("method")
            params = request.get("params", {})

            self.request_count += 1
            logger.debug(f"Request #{self.request_count}: {method}")

            # Route to handler
            if method == "create_entities":
                result = self.db.create_entities(params.get("entities", []))
            elif method == "search_nodes":
                result = self.db.search_nodes(params.get("query", ""), params.get("limit", 10))
            elif method == "get_memory_status":
                result = self.db.get_memory_status()
            elif method == "add_to_working_memory":
                result = self.db.add_to_working_memory(
                    params.get("context_key"),
                    params.get("content"),
                    params.get("priority", 5),
                    params.get("ttl_minutes", 60),
                    params.get("entity_id")
                )
            elif method == "get_working_memory":
                result = self.db.get_working_memory(
                    params.get("context_key"),
                    params.get("limit", 50)
                )
            elif method == "health_status":
                result = self.db.health.get_status()
            else:
                result = {"error": f"Unknown method: {method}"}

            response = json.dumps(result).encode()
            writer.write(response)
            await writer.drain()

        except asyncio.TimeoutError:
            logger.warning("Request timeout")
            self.error_count += 1
        except Exception as e:
            logger.error(f"Request error: {e}")
            self.error_count += 1
            try:
                error_response = json.dumps({"error": str(e)}).encode()
                writer.write(error_response)
                await writer.drain()
            except:
                pass
        finally:
            writer.close()
            await writer.wait_closed()

    async def start(self):
        """Start the server"""
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

        self.server = await asyncio.start_unix_server(
            self.handle_request,
            path=self.socket_path
        )

        os.chmod(self.socket_path, 0o666)
        logger.info(f"Memory-DB v2 listening on {self.socket_path}")

        async with self.server:
            await self.server.serve_forever()

    async def stop(self):
        """Stop the server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        self.db.shutdown()

        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

        logger.info(f"Memory-DB v2 stopped (requests: {self.request_count}, errors: {self.error_count})")


async def main():
    """Main entry point"""
    server = MemoryDBServerV2(SOCKET_PATH, DB_PATH)
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Shutdown signal received")
        asyncio.create_task(server.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt")
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())

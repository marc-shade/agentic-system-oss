#!/usr/bin/env python3
"""
Memory Database Service - Unix Socket Server for Concurrent Access

Provides lock-free concurrent access to the memory database for multiple
MCP servers and subagents via Unix socket.

Architecture:
- Listens on /tmp/memory-db.sock
- Handles JSON-RPC style requests
- Manages SQLite database with proper locking
- Supports create_entities, search_nodes, get_memory_status operations
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
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("memory-db-service")

# Configuration
SOCKET_PATH = "/tmp/memory-db.sock"
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"

# Create directories
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


class MemoryDatabase:
    """Central memory database with concurrent access support"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize SQLite database with all required tables"""
        conn = sqlite3.connect(self.db_path)
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

        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entity_name ON entities(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entity_type ON entities(entity_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entity_tier ON entities(tier)')

        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")

    def _compress_data(self, data: Any) -> bytes:
        """Compress data using zlib"""
        pickled = pickle.dumps(data)
        compressed = zlib.compress(pickled, level=9)
        return compressed

    def _decompress_data(self, compressed: bytes) -> Any:
        """Decompress data"""
        decompressed = zlib.decompress(compressed)
        return pickle.loads(decompressed)

    def _calculate_checksum(self, data: bytes) -> str:
        """Calculate SHA-256 checksum"""
        return hashlib.sha256(data).hexdigest()

    def create_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create or update entities in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        results = {"success": True, "created": 0, "updated": 0, "failed": 0, "count": 0, "results": []}

        try:
            for entity in entities:
                try:
                    name = entity.get("name")
                    entity_type = entity.get("entityType", "general")
                    observations = entity.get("observations", [])

                    # Compress entity data
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

                    # Check if entity exists
                    cursor.execute("SELECT id FROM entities WHERE name = ?", (name,))
                    existing = cursor.fetchone()

                    if existing:
                        # Update existing entity
                        cursor.execute('''
                            UPDATE entities
                            SET entity_type = ?, compressed_data = ?, original_size = ?,
                                compressed_size = ?, compression_ratio = ?, checksum = ?,
                                access_count = access_count + 1, last_accessed = CURRENT_TIMESTAMP,
                                current_version = current_version + 1
                            WHERE name = ?
                        ''', (entity_type, compressed, original_size, compressed_size,
                              compression_ratio, checksum, name))
                        results["updated"] += 1
                        entity_id = existing[0]
                    else:
                        # Create new entity
                        cursor.execute('''
                            INSERT INTO entities
                            (name, entity_type, compressed_data, original_size, compressed_size,
                             compression_ratio, checksum)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (name, entity_type, compressed, original_size, compressed_size,
                              compression_ratio, checksum))
                        results["created"] += 1
                        entity_id = cursor.lastrowid

                    # Store observations
                    for obs in observations:
                        cursor.execute('''
                            INSERT INTO observations (entity_id, content)
                            VALUES (?, ?)
                        ''', (entity_id, obs))

                    results["results"].append({
                        "name": name,
                        "id": entity_id,
                        "compression_ratio": f"{compression_ratio:.2%}"
                    })

                except Exception as e:
                    logger.error(f"Failed to create entity: {e}")
                    results["failed"] += 1

            results["count"] = results["created"] + results["updated"]
            conn.commit()
            return results

        except Exception as e:
            conn.rollback()
            logger.error(f"Error in create_entities: {e}")
            return {"success": False, "error": str(e), "created": 0, "failed": len(entities), "count": 0}
        finally:
            conn.close()

    def search_nodes(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for entities matching the query"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Search by name or type
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

                # Decompress entity data
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

            # Update access count
            for entity in results:
                cursor.execute('''
                    UPDATE entities
                    SET access_count = access_count + 1, last_accessed = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (entity["id"],))

            conn.commit()
            return {"success": True, "query": query, "count": len(results), "results": results}

        except Exception as e:
            logger.error(f"Error in search_nodes: {e}")
            return {"success": False, "error": str(e), "count": 0, "results": []}
        finally:
            conn.close()

    def get_memory_status(self) -> Dict[str, Any]:
        """Get memory system status and statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get entity count
            cursor.execute("SELECT COUNT(*) FROM entities")
            total_entities = cursor.fetchone()[0]

            # Get compression stats
            cursor.execute('''
                SELECT
                    AVG(compression_ratio) as avg_ratio,
                    SUM(original_size) as total_original,
                    SUM(compressed_size) as total_compressed
                FROM entities
            ''')
            avg_ratio, total_original, total_compressed = cursor.fetchone()

            # Get tier distribution
            cursor.execute('''
                SELECT tier, COUNT(*) as count
                FROM entities
                GROUP BY tier
            ''')
            tier_distribution = {row[0]: row[1] for row in cursor.fetchall()}

            return {
                "success": True,
                "entities": {
                    "total": total_entities
                },
                "compression": {
                    "ratio": f"{avg_ratio:.2%}" if avg_ratio else "N/A",
                    "total_original_kb": round(total_original / 1024, 2) if total_original else 0,
                    "total_compressed_kb": round(total_compressed / 1024, 2) if total_compressed else 0
                },
                "tiers": tier_distribution,
                "database_path": str(self.db_path)
            }

        except Exception as e:
            logger.error(f"Error in get_memory_status: {e}")
            return {"success": False, "error": str(e), "entities": {"total": 0}}
        finally:
            conn.close()


class MemoryDBServer:
    """Unix socket server for memory database"""

    def __init__(self, socket_path: str, db_path: Path):
        self.socket_path = socket_path
        self.db = MemoryDatabase(db_path)
        self.server = None

    async def handle_request(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming client request"""
        try:
            # Read request
            request_data = await reader.read(10 * 1024 * 1024)  # 10MB max
            if not request_data:
                return

            request = json.loads(request_data.decode())
            method = request.get("method")
            params = request.get("params", {})

            logger.info(f"Received request: {method}")

            # Route to appropriate handler
            if method == "create_entities":
                result = self.db.create_entities(params.get("entities", []))
            elif method == "search_nodes":
                result = self.db.search_nodes(
                    params.get("query", ""),
                    params.get("limit", 10)
                )
            elif method == "get_memory_status":
                result = self.db.get_memory_status()
            else:
                result = {"error": f"Unknown method: {method}"}

            # Send response
            response = json.dumps(result).encode()
            writer.write(response)
            await writer.drain()

        except Exception as e:
            logger.error(f"Error handling request: {e}")
            error_response = json.dumps({"error": str(e)}).encode()
            writer.write(error_response)
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def start(self):
        """Start the Unix socket server"""
        # Remove existing socket file
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

        # Start server
        self.server = await asyncio.start_unix_server(
            self.handle_request,
            path=self.socket_path
        )

        # Set socket permissions
        os.chmod(self.socket_path, 0o666)

        logger.info(f"Memory-DB service listening on {self.socket_path}")

        async with self.server:
            await self.server.serve_forever()

    async def stop(self):
        """Stop the server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

        logger.info("Memory-DB service stopped")


async def main():
    """Main entry point"""
    server = MemoryDBServer(SOCKET_PATH, DB_PATH)

    # Handle shutdown signals
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(server.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())

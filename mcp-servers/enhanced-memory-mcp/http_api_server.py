#!/usr/bin/env python3
"""
Enhanced Memory REST API Server

Simple HTTP/JSON API for dashboard integration.
Direct SQLite access for maximum reliability (no socket dependency).

Port 8101 by default.

Endpoints:
    GET  /health              - Health check
    POST /search_nodes        - Search entities
    POST /create_entities     - Create new entities
    POST /get_episodes        - Get episodic memory
    GET  /get_memory_status   - Memory system status
"""

import os
import sys
import json
import sqlite3
import hashlib
import zlib
import base64
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.middleware.cors import CORSMiddleware
import uvicorn

# Database path
DB_PATH = Path.home() / ".claude" / "enhanced_memories" / "memory.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Entities table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            tier TEXT DEFAULT 'working',
            importance_score REAL DEFAULT 0.5,
            compressed_data BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Observations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id INTEGER,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entity_id) REFERENCES entities(id)
        )
    """)

    # Episodic memory table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS episodic_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            episode_data TEXT,
            significance_score REAL DEFAULT 0.5,
            emotional_valence REAL,
            tags TEXT,
            entity_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entity_id) REFERENCES entities(id)
        )
    """)

    conn.commit()
    conn.close()


# Initialize database
init_db()

# --- Endpoints ---

async def health(request):
    """Health check endpoint."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM entities")
        entity_count = cursor.fetchone()[0]
        conn.close()

        return JSONResponse({
            "status": "healthy",
            "service": "enhanced-memory-mcp",
            "port": 8101,
            "database": str(DB_PATH),
            "database_exists": DB_PATH.exists(),
            "entity_count": entity_count
        })
    except Exception as e:
        return JSONResponse({
            "status": "degraded",
            "error": str(e),
            "database": str(DB_PATH)
        }, status_code=500)


async def get_memory_status(request):
    """Get memory system status."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get entity counts by tier
        cursor.execute("""
            SELECT tier, COUNT(*) as count
            FROM entities
            GROUP BY tier
        """)
        tier_counts = {row['tier']: row['count'] for row in cursor.fetchall()}

        # Get total entity count
        cursor.execute("SELECT COUNT(*) FROM entities")
        total_entities = cursor.fetchone()[0]

        # Get episodic memory count
        cursor.execute("SELECT COUNT(*) FROM episodic_memory")
        episode_count = cursor.fetchone()[0]

        conn.close()

        return JSONResponse({
            "status": "operational",
            "total_entities": total_entities,
            "tier_counts": tier_counts,
            "episode_count": episode_count,
            "database": str(DB_PATH)
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def search_nodes(request):
    """Search for entities."""
    try:
        body = await request.json()
        query = body.get("query", "")
        limit = body.get("limit", 10)

        conn = get_db_connection()
        cursor = conn.cursor()

        # Search entities by name or type
        cursor.execute("""
            SELECT e.id, e.name, e.entity_type, e.tier, e.salience_score,
                   e.created_at, e.last_accessed
            FROM entities e
            WHERE e.name LIKE ? OR e.entity_type LIKE ?
            ORDER BY e.last_accessed DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))

        results = []
        for row in cursor.fetchall():
            # Get observations for this entity
            cursor.execute("""
                SELECT content FROM observations WHERE entity_id = ?
            """, (row['id'],))
            observations = [obs['content'] for obs in cursor.fetchall()]

            results.append({
                "id": row['id'],
                "name": row['name'],
                "entityType": row['entity_type'],
                "tier": row['tier'],
                "salience_score": row['salience_score'],
                "observations": observations,
                "created_at": row['created_at'],
                "last_accessed": row['last_accessed']
            })

        conn.close()

        return JSONResponse({
            "results": results,
            "count": len(results),
            "query": query
        })
    except Exception as e:
        return JSONResponse({"error": str(e), "results": []}, status_code=500)


async def create_entities(request):
    """Create new entities."""
    try:
        body = await request.json()
        entities = body.get("entities", [])

        conn = get_db_connection()
        cursor = conn.cursor()

        created_ids = []
        for entity in entities:
            name = entity.get("name", "unnamed")
            entity_type = entity.get("entityType", "general")
            observations = entity.get("observations", [])
            tier = entity.get("tier", "working")

            # Insert entity
            cursor.execute("""
                INSERT INTO entities (name, entity_type, tier)
                VALUES (?, ?, ?)
            """, (name, entity_type, tier))
            entity_id = cursor.lastrowid
            created_ids.append(entity_id)

            # Insert observations
            for obs in observations:
                cursor.execute("""
                    INSERT INTO observations (entity_id, content)
                    VALUES (?, ?)
                """, (entity_id, obs))

        conn.commit()
        conn.close()

        return JSONResponse({
            "success": True,
            "created": len(created_ids),
            "entity_ids": created_ids
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def get_episodes(request):
    """Get episodic memory entries."""
    try:
        body = await request.json()
        event_type = body.get("event_type")
        limit = body.get("limit", 50)
        min_significance = body.get("min_significance", 0)

        conn = get_db_connection()
        cursor = conn.cursor()

        if event_type:
            cursor.execute("""
                SELECT id, event_type, episode_data, significance_score,
                       emotional_valence, tags, created_at
                FROM episodic_memory
                WHERE event_type = ? AND significance_score >= ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (event_type, min_significance, limit))
        else:
            cursor.execute("""
                SELECT id, event_type, episode_data, significance_score,
                       emotional_valence, tags, created_at
                FROM episodic_memory
                WHERE significance_score >= ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (min_significance, limit))

        episodes = []
        for row in cursor.fetchall():
            episode_data = row['episode_data']
            if episode_data:
                try:
                    episode_data = json.loads(episode_data)
                except:
                    pass

            tags = row['tags']
            if tags:
                try:
                    tags = json.loads(tags)
                except:
                    tags = []

            episodes.append({
                "id": row['id'],
                "event_type": row['event_type'],
                "episode_data": episode_data,
                "significance_score": row['significance_score'],
                "emotional_valence": row['emotional_valence'],
                "tags": tags,
                "created_at": row['created_at']
            })

        conn.close()

        return JSONResponse({
            "episodes": episodes,
            "count": len(episodes)
        })
    except Exception as e:
        return JSONResponse({"error": str(e), "episodes": []}, status_code=500)


async def add_episode(request):
    """Add an episodic memory entry."""
    try:
        body = await request.json()
        event_type = body.get("event_type", "general")
        episode_data = body.get("episode_data", {})
        significance_score = body.get("significance_score", 0.5)
        tags = body.get("tags", [])
        emotional_valence = body.get("emotional_valence")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO episodic_memory
            (event_type, episode_data, significance_score, emotional_valence, tags)
            VALUES (?, ?, ?, ?, ?)
        """, (
            event_type,
            json.dumps(episode_data) if isinstance(episode_data, dict) else episode_data,
            significance_score,
            emotional_valence,
            json.dumps(tags) if isinstance(tags, list) else tags
        ))

        episode_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return JSONResponse({
            "success": True,
            "episode_id": episode_id,
            "event_type": event_type
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# --- App Setup ---

routes = [
    Route("/health", health, methods=["GET"]),
    Route("/get_memory_status", get_memory_status, methods=["GET", "POST"]),
    Route("/search_nodes", search_nodes, methods=["POST"]),
    Route("/create_entities", create_entities, methods=["POST"]),
    Route("/get_episodes", get_episodes, methods=["POST"]),
    Route("/add_episode", add_episode, methods=["POST"]),
]

app = Starlette(routes=routes)

# Add CORS middleware for dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Enhanced Memory REST API')
    parser.add_argument('--port', type=int, default=8101, help='Port (default: 8101)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host (default: 0.0.0.0)')
    args = parser.parse_args()

    print(f"[Enhanced Memory REST API] Starting on http://{args.host}:{args.port}")
    print(f"[Enhanced Memory REST API] Database: {DB_PATH}")
    print(f"[Enhanced Memory REST API] Endpoints:")
    print(f"  GET  /health")
    print(f"  GET  /get_memory_status")
    print(f"  POST /search_nodes")
    print(f"  POST /create_entities")
    print(f"  POST /get_episodes")
    print(f"  POST /add_episode")

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")

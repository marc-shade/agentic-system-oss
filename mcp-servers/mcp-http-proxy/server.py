#!/usr/bin/env python3
"""
MCP HTTP Proxy Server
Provides HTTP interface to enhanced-memory-mcp functions.
Enables AutoKitteh handlers and other HTTP clients to call memory operations.

Port: 8101
"""
import asyncio
import json
import sys
import platform
from pathlib import Path
from datetime import datetime
from aiohttp import web

# Add enhanced-memory-mcp to path
def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    system = platform.system()
    if system == "Darwin":
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
    return Path(__file__).parent.parent.parent

_STORAGE_BASE = _get_storage_base()
_MCP_PATH = _STORAGE_BASE / "mcp-servers" / "enhanced-memory-mcp"
sys.path.insert(0, str(_MCP_PATH))

# Import memory client for database operations
from memory_client import MemoryClient

# Database path
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"

# Global memory client
memory_client = None


async def init_memory_client():
    """Initialize memory client connection."""
    global memory_client
    memory_client = MemoryClient()
    return memory_client


# Route handlers

async def handle_health(request):
    """GET /health - Health check endpoint."""
    try:
        status = await memory_client.get_memory_status()
        return web.json_response({
            "status": "healthy",
            "entities": status.get("entities", {}).get("total", 0),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return web.json_response({
            "status": "unhealthy",
            "error": str(e)
        }, status=503)


async def handle_get_memory_status(request):
    """GET /get_memory_status - Get memory system status."""
    try:
        result = await memory_client.get_memory_status()
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_create_entities(request):
    """POST /create_entities - Create new entities."""
    try:
        data = await request.json()
        entities = data.get("entities", [])
        result = await memory_client.create_entities(entities)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_search_nodes(request):
    """POST /search_nodes - Search for entities."""
    try:
        data = await request.json()
        query = data.get("query", "")
        limit = data.get("limit", 10)
        result = await memory_client.search_nodes(query, limit)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_create_causal_link(request):
    """POST /create_causal_link - Create causal relationship."""
    try:
        data = await request.json()

        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Create causal_links table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS causal_links (
                id INTEGER PRIMARY KEY,
                cause_entity_id INTEGER NOT NULL,
                effect_entity_id INTEGER NOT NULL,
                relationship_type TEXT DEFAULT 'direct',
                strength REAL DEFAULT 0.5,
                typical_delay_seconds INTEGER,
                context_conditions TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cause_entity_id) REFERENCES entities(id),
                FOREIGN KEY (effect_entity_id) REFERENCES entities(id)
            )
        """)

        cursor.execute("""
            INSERT INTO causal_links
            (cause_entity_id, effect_entity_id, relationship_type, strength, typical_delay_seconds, context_conditions)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data.get("cause_entity_id"),
            data.get("effect_entity_id"),
            data.get("relationship_type", "direct"),
            data.get("strength", 0.5),
            data.get("typical_delay_seconds"),
            json.dumps(data.get("context_conditions")) if data.get("context_conditions") else None
        ))

        link_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return web.json_response({
            "status": "success",
            "link_id": link_id,
            "cause_id": data.get("cause_entity_id"),
            "effect_id": data.get("effect_entity_id"),
            "strength": data.get("strength", 0.5)
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_create_association(request):
    """POST /create_association - Create association between entities."""
    try:
        data = await request.json()

        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Create associations table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS associations (
                id INTEGER PRIMARY KEY,
                entity_a_id INTEGER NOT NULL,
                entity_b_id INTEGER NOT NULL,
                association_type TEXT DEFAULT 'semantic',
                association_strength REAL DEFAULT 0.5,
                bidirectional INTEGER DEFAULT 1,
                context_conditions TEXT,
                activation_count INTEGER DEFAULT 0,
                last_activated TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_a_id) REFERENCES entities(id),
                FOREIGN KEY (entity_b_id) REFERENCES entities(id)
            )
        """)

        cursor.execute("""
            INSERT INTO associations
            (entity_a_id, entity_b_id, association_type, association_strength, bidirectional, context_conditions)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data.get("entity_a_id"),
            data.get("entity_b_id"),
            data.get("association_type", "semantic"),
            data.get("association_strength", 0.5),
            1 if data.get("bidirectional", True) else 0,
            json.dumps(data.get("context_conditions")) if data.get("context_conditions") else None
        ))

        assoc_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return web.json_response({
            "status": "success",
            "association_id": assoc_id,
            "entity_a_id": data.get("entity_a_id"),
            "entity_b_id": data.get("entity_b_id"),
            "association_type": data.get("association_type", "semantic"),
            "strength": data.get("association_strength", 0.5)
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_update_salience(request):
    """POST /update_salience - Update entity importance."""
    try:
        data = await request.json()
        entity_id = data.get("entity_id")
        salience_delta = data.get("salience_delta", 0)
        reason = data.get("reason", "")

        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Update salience (stored in a metadata field or separate table)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entity_salience (
                entity_id INTEGER PRIMARY KEY,
                salience REAL DEFAULT 0.5,
                last_update TEXT,
                update_reason TEXT,
                FOREIGN KEY (entity_id) REFERENCES entities(id)
            )
        """)

        # Get current salience
        cursor.execute("SELECT salience FROM entity_salience WHERE entity_id = ?", (entity_id,))
        row = cursor.fetchone()
        current = row[0] if row else 0.5
        new_salience = max(0, min(1, current + salience_delta))

        cursor.execute("""
            INSERT OR REPLACE INTO entity_salience (entity_id, salience, last_update, update_reason)
            VALUES (?, ?, ?, ?)
        """, (entity_id, new_salience, datetime.now().isoformat(), reason))

        conn.commit()
        conn.close()

        return web.json_response({
            "status": "success",
            "entity_id": entity_id,
            "old_salience": current,
            "new_salience": new_salience
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_archive_entity(request):
    """POST /archive_entity - Archive/deprecate an entity."""
    try:
        data = await request.json()
        entity_id = data.get("entity_id")
        reason = data.get("reason", "")

        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Mark entity as archived
        cursor.execute("""
            UPDATE entities
            SET tier = 'archive',
                metadata = json_set(COALESCE(metadata, '{}'), '$.archived_at', ?, '$.archive_reason', ?)
            WHERE id = ?
        """, (datetime.now().isoformat(), reason, entity_id))

        conn.commit()
        conn.close()

        return web.json_response({
            "status": "success",
            "entity_id": entity_id,
            "archived": True
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_consolidate(request):
    """POST /consolidate - Run memory consolidation."""
    try:
        data = await request.json()
        time_window_hours = data.get("time_window_hours", 24)

        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Ensure required tables exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodic_memory (
                id INTEGER PRIMARY KEY,
                event_type TEXT NOT NULL,
                episode_data TEXT NOT NULL,
                significance_score REAL DEFAULT 0.5,
                emotional_valence REAL,
                tags TEXT,
                entity_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entity_salience (
                entity_id INTEGER PRIMARY KEY,
                salience REAL DEFAULT 0.5,
                last_update TEXT,
                update_reason TEXT,
                FOREIGN KEY (entity_id) REFERENCES entities(id)
            )
        """)
        conn.commit()

        # Count patterns in recent episodic memories
        cursor.execute("""
            SELECT COUNT(*) FROM episodic_memory
            WHERE created_at > datetime('now', '-' || ? || ' hours')
        """, (time_window_hours,))
        episodic_count = cursor.fetchone()[0]

        # Simple consolidation: promote frequent patterns
        cursor.execute("""
            SELECT entity_id, COUNT(*) as access_count
            FROM entity_salience
            WHERE last_update > datetime('now', '-' || ? || ' hours')
            GROUP BY entity_id
            HAVING access_count >= 3
        """, (time_window_hours,))
        patterns = cursor.fetchall()

        conn.close()

        return web.json_response({
            "pattern_extraction": {
                "patterns_found": len(patterns),
                "patterns_promoted": 0,
                "semantic_memories_created": 0,
                "sources_analyzed": {
                    "entities_episodic": episodic_count
                }
            },
            "causal_discovery": {
                "chains_created": 0,
                "links_created": 0,
                "hypotheses_generated": 0
            }
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_get_knowledge_gaps(request):
    """GET /get_knowledge_gaps - Get knowledge gaps for an agent."""
    try:
        agent_id = request.query.get("agent_id", "agi_claude")
        status = request.query.get("status", "open")

        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Create knowledge_gaps table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_gaps (
                id INTEGER PRIMARY KEY,
                agent_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                description TEXT NOT NULL,
                gap_type TEXT DEFAULT 'factual',
                severity REAL DEFAULT 0.5,
                status TEXT DEFAULT 'open',
                discovered_by TEXT DEFAULT 'self-reflection',
                learning_progress REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            SELECT id, domain, description, gap_type, severity, status, learning_progress
            FROM knowledge_gaps
            WHERE agent_id = ? AND status = ?
            ORDER BY severity DESC
        """, (agent_id, status))

        gaps = []
        for row in cursor.fetchall():
            gaps.append({
                "id": row[0],
                "domain": row[1],
                "description": row[2],
                "gap_type": row[3],
                "severity": row[4],
                "status": row[5],
                "learning_progress": row[6]
            })

        conn.close()

        return web.json_response({"gaps": gaps})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_add_episode(request):
    """POST /add_episode - Add episodic memory."""
    try:
        data = await request.json()

        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Create episodic_memory table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodic_memory (
                id INTEGER PRIMARY KEY,
                event_type TEXT NOT NULL,
                episode_data TEXT NOT NULL,
                significance_score REAL DEFAULT 0.5,
                emotional_valence REAL,
                tags TEXT,
                entity_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            INSERT INTO episodic_memory
            (event_type, episode_data, significance_score, emotional_valence, tags, entity_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data.get("event_type"),
            json.dumps(data.get("episode_data", {})),
            data.get("significance_score", 0.5),
            data.get("emotional_valence"),
            json.dumps(data.get("tags", [])),
            data.get("entity_id")
        ))

        episode_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return web.json_response({
            "episode_id": episode_id,
            "event_type": data.get("event_type"),
            "significance_score": data.get("significance_score", 0.5)
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_add_concept(request):
    """POST /add_concept - Add semantic concept."""
    try:
        data = await request.json()

        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Create semantic_memory table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS semantic_memory (
                id INTEGER PRIMARY KEY,
                concept_name TEXT UNIQUE NOT NULL,
                concept_type TEXT NOT NULL,
                definition TEXT NOT NULL,
                related_concepts TEXT,
                confidence_score REAL DEFAULT 0.5,
                access_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            INSERT OR REPLACE INTO semantic_memory
            (concept_name, concept_type, definition, related_concepts, confidence_score, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data.get("concept_name"),
            data.get("concept_type"),
            data.get("definition"),
            json.dumps(data.get("related_concepts", [])),
            data.get("confidence_score", 0.5),
            datetime.now().isoformat()
        ))

        concept_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return web.json_response({
            "concept_id": concept_id,
            "concept_name": data.get("concept_name"),
            "confidence_score": data.get("confidence_score", 0.5)
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def on_startup(app):
    """Initialize on app startup."""
    print(f"Starting MCP HTTP Proxy on port 8101...")
    print(f"Storage base: {_STORAGE_BASE}")
    print(f"Database: {DB_PATH}")
    await init_memory_client()
    print("Memory client initialized")


def create_app():
    """Create and configure the aiohttp application."""
    app = web.Application()

    # Register routes
    app.router.add_get("/health", handle_health)
    app.router.add_get("/get_memory_status", handle_get_memory_status)
    app.router.add_post("/create_entities", handle_create_entities)
    app.router.add_post("/search_nodes", handle_search_nodes)
    app.router.add_post("/create_causal_link", handle_create_causal_link)
    app.router.add_post("/create_association", handle_create_association)
    app.router.add_post("/update_salience", handle_update_salience)
    app.router.add_post("/archive_entity", handle_archive_entity)
    app.router.add_post("/consolidate", handle_consolidate)
    app.router.add_get("/get_knowledge_gaps", handle_get_knowledge_gaps)
    app.router.add_post("/add_episode", handle_add_episode)
    app.router.add_post("/add_concept", handle_add_concept)

    # Lifecycle hooks
    app.on_startup.append(on_startup)

    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=8101)

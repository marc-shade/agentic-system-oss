"""SQLite-based state persistence for LangGraph workflows."""
import json
import sqlite3
import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, asdict

DB_PATH = Path("/Volumes/SSDRAID0/agentic-system/databases/langgraph/state.db")

@dataclass
class GraphState:
    graph_id: str
    thread_id: str
    state_data: dict
    checkpoint_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

async def init_db():
    """Initialize the database schema."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS graph_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                graph_id TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                checkpoint_id TEXT,
                state_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(graph_id, thread_id, checkpoint_id)
            );
            CREATE INDEX IF NOT EXISTS idx_graph_thread ON graph_states(graph_id, thread_id);

            CREATE TABLE IF NOT EXISTS memory_store (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_memory_thread ON memory_store(thread_id, memory_type);

            CREATE TABLE IF NOT EXISTS human_approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                approval_type TEXT NOT NULL,
                request_data TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                response_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_approval_status ON human_approvals(status);
        """)
        await db.commit()

async def save_state(graph_id: str, thread_id: str, state: dict, checkpoint_id: Optional[str] = None) -> int:
    """Save graph state to database."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT OR REPLACE INTO graph_states (graph_id, thread_id, checkpoint_id, state_data, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (graph_id, thread_id, checkpoint_id, json.dumps(state)))
        await db.commit()
        return cursor.lastrowid

async def load_state(graph_id: str, thread_id: str, checkpoint_id: Optional[str] = None) -> Optional[dict]:
    """Load graph state from database."""
    async with aiosqlite.connect(DB_PATH) as db:
        if checkpoint_id:
            cursor = await db.execute(
                "SELECT state_data FROM graph_states WHERE graph_id=? AND thread_id=? AND checkpoint_id=?",
                (graph_id, thread_id, checkpoint_id)
            )
        else:
            cursor = await db.execute(
                "SELECT state_data FROM graph_states WHERE graph_id=? AND thread_id=? ORDER BY updated_at DESC LIMIT 1",
                (graph_id, thread_id)
            )
        row = await cursor.fetchone()
        return json.loads(row[0]) if row else None

async def list_checkpoints(graph_id: str, thread_id: str) -> list[dict]:
    """List all checkpoints for a thread."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT checkpoint_id, created_at, updated_at FROM graph_states WHERE graph_id=? AND thread_id=? ORDER BY updated_at DESC",
            (graph_id, thread_id)
        )
        rows = await cursor.fetchall()
        return [{"checkpoint_id": r[0], "created_at": r[1], "updated_at": r[2]} for r in rows]

async def save_memory(thread_id: str, memory_type: str, content: str, metadata: Optional[dict] = None) -> int:
    """Save memory entry."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO memory_store (thread_id, memory_type, content, metadata) VALUES (?, ?, ?, ?)",
            (thread_id, memory_type, content, json.dumps(metadata or {}))
        )
        await db.commit()
        return cursor.lastrowid

async def get_memories(thread_id: str, memory_type: Optional[str] = None, limit: int = 100) -> list[dict]:
    """Retrieve memories for a thread."""
    async with aiosqlite.connect(DB_PATH) as db:
        if memory_type:
            cursor = await db.execute(
                "SELECT content, metadata, created_at FROM memory_store WHERE thread_id=? AND memory_type=? ORDER BY created_at DESC LIMIT ?",
                (thread_id, memory_type, limit)
            )
        else:
            cursor = await db.execute(
                "SELECT content, metadata, created_at FROM memory_store WHERE thread_id=? ORDER BY created_at DESC LIMIT ?",
                (thread_id, limit)
            )
        rows = await cursor.fetchall()
        return [{"content": r[0], "metadata": json.loads(r[1]), "created_at": r[2]} for r in rows]

async def create_approval_request(thread_id: str, approval_type: str, request_data: dict) -> int:
    """Create a human approval request."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO human_approvals (thread_id, approval_type, request_data) VALUES (?, ?, ?)",
            (thread_id, approval_type, json.dumps(request_data))
        )
        await db.commit()
        return cursor.lastrowid

async def get_pending_approvals() -> list[dict]:
    """Get all pending approval requests."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, thread_id, approval_type, request_data, created_at FROM human_approvals WHERE status='pending'"
        )
        rows = await cursor.fetchall()
        return [{"id": r[0], "thread_id": r[1], "approval_type": r[2], "request_data": json.loads(r[3]), "created_at": r[4]} for r in rows]

async def resolve_approval(approval_id: int, approved: bool, response_data: Optional[dict] = None) -> bool:
    """Resolve an approval request."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE human_approvals SET status=?, response_data=?, resolved_at=CURRENT_TIMESTAMP WHERE id=?",
            ('approved' if approved else 'rejected', json.dumps(response_data or {}), approval_id)
        )
        await db.commit()
        return True

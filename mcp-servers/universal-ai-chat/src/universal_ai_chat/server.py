#!/usr/bin/env python3
"""
Universal AI Chat MCP Server
Real-time communication between Claude Code, OpenAI Codex CLI, and Gemini CLI.

Enables:
- Multi-session Claude Code chat
- Cross-vendor AI CLI communication
- Shared memory/context across all AI assistants
- Conversation history and threading
- Broadcast messaging
"""
import platform

import asyncio
import json
import sqlite3
import uuid
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import logging
import hashlib

# MCP SDK
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp import types

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize server
server = Server("universal-ai-chat")

# Storage paths
STORAGE_BASE = Path(os.environ.get("STORAGE_BASE", str(_STORAGE_BASE)))
DB_PATH = STORAGE_BASE / "databases" / "universal_ai_chat.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Session registry (in-memory for fast lookups)
ACTIVE_SESSIONS = {}

# Supported AI platforms
AI_PLATFORMS = {
    "claude-code": {
        "name": "Claude Code",
        "vendor": "Anthropic",
        "color": "#DA7756",
        "icon": "🟠"
    },
    "codex-cli": {
        "name": "OpenAI Codex CLI",
        "vendor": "OpenAI",
        "color": "#10A37F",
        "icon": "🟢"
    },
    "gemini-cli": {
        "name": "Gemini CLI",
        "vendor": "Google",
        "color": "#4285F4",
        "icon": "🔵"
    },
    "ollama": {
        "name": "Ollama",
        "vendor": "Local",
        "color": "#FFFFFF",
        "icon": "⚪"
    },
    "custom": {
        "name": "Custom AI",
        "vendor": "Custom",
        "color": "#9B59B6",
        "icon": "🟣"
    }
}


def init_database():
    """Initialize SQLite database for message persistence"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Sessions table - track registered AI sessions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            platform TEXT NOT NULL,
            display_name TEXT,
            node_id TEXT,
            registered_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_active TEXT DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT,
            active INTEGER DEFAULT 1
        )
    """)

    # Messages table - all cross-AI messages
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            message_id TEXT PRIMARY KEY,
            conversation_id TEXT,
            from_session TEXT NOT NULL,
            to_session TEXT,
            broadcast INTEGER DEFAULT 0,
            content TEXT NOT NULL,
            message_type TEXT DEFAULT 'chat',
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            delivered INTEGER DEFAULT 0,
            delivered_at TEXT,
            read INTEGER DEFAULT 0,
            read_at TEXT,
            metadata TEXT,
            FOREIGN KEY (from_session) REFERENCES sessions(session_id)
        )
    """)

    # Conversations table - group messages by thread
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            conversation_id TEXT PRIMARY KEY,
            title TEXT,
            participants TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_activity TEXT DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT,
            active INTEGER DEFAULT 1
        )
    """)

    # Shared context table - cross-AI memory
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shared_context (
            context_id TEXT PRIMARY KEY,
            context_key TEXT UNIQUE NOT NULL,
            content TEXT NOT NULL,
            created_by TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            access_count INTEGER DEFAULT 0,
            metadata TEXT
        )
    """)

    # Message queue for async delivery
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS message_queue (
            queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL,
            target_session TEXT NOT NULL,
            queued_at TEXT DEFAULT CURRENT_TIMESTAMP,
            attempts INTEGER DEFAULT 0,
            last_attempt TEXT,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (message_id) REFERENCES messages(message_id)
        )
    """)

    # Indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_to_session ON messages(to_session)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_status ON message_queue(status)")

    conn.commit()
    conn.close()
    logger.info(f"Database initialized at {DB_PATH}")


def get_session_id():
    """Generate or retrieve session ID for this instance"""
    # Use environment variable if set, otherwise generate
    session_id = os.environ.get("AI_SESSION_ID")
    if not session_id:
        # Generate deterministic ID based on PID and timestamp
        session_id = hashlib.md5(f"{os.getpid()}-{datetime.now().isoformat()}".encode(), usedforsecurity=False).hexdigest()[:12]
    return session_id


# Current session info
CURRENT_SESSION = {
    "session_id": get_session_id(),
    "platform": os.environ.get("AI_PLATFORM", "claude-code"),
    "display_name": os.environ.get("AI_DISPLAY_NAME", f"Claude-{get_session_id()[:6]}"),
    "node_id": os.environ.get("NODE_ID", "local")
}


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available universal AI chat tools"""
    return [
        types.Tool(
            name="register_session",
            description="""
            Register this AI session with the universal chat system.

            Call this first to announce your presence to other AI assistants.
            Sets your platform type, display name, and capabilities.

            Other AIs can then discover and communicate with you.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "description": "AI platform type",
                        "enum": list(AI_PLATFORMS.keys())
                    },
                    "display_name": {
                        "type": "string",
                        "description": "Human-readable name for this session"
                    },
                    "capabilities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of capabilities (e.g., 'code', 'research', 'analysis')"
                    }
                },
                "required": ["platform"]
            }
        ),
        types.Tool(
            name="list_active_sessions",
            description="""
            List all active AI sessions across all platforms.

            Shows Claude Code, Codex CLI, Gemini CLI, and other connected AI assistants.
            Use this to discover who you can communicate with.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "platform_filter": {
                        "type": "string",
                        "description": "Filter by platform (optional)",
                        "enum": list(AI_PLATFORMS.keys())
                    }
                }
            }
        ),
        types.Tool(
            name="send_message",
            description="""
            Send a message to another AI session.

            Messages are delivered in real-time when possible, queued otherwise.
            Works across Claude Code, Codex CLI, Gemini CLI, and any connected AI.

            Use for:
            - Requesting help from another AI
            - Sharing findings or results
            - Coordinating multi-AI tasks
            - Asking questions to a specific AI vendor
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "to_session": {
                        "type": "string",
                        "description": "Target session ID"
                    },
                    "message": {
                        "type": "string",
                        "description": "Message content"
                    },
                    "message_type": {
                        "type": "string",
                        "description": "Type of message",
                        "enum": ["chat", "request", "response", "notification", "code", "data"],
                        "default": "chat"
                    }
                },
                "required": ["to_session", "message"]
            }
        ),
        types.Tool(
            name="broadcast_message",
            description="""
            Broadcast a message to ALL connected AI sessions.

            Everyone receives it: Claude Code, Codex, Gemini, etc.
            Use for announcements, shared discoveries, or coordination.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Broadcast message content"
                    },
                    "message_type": {
                        "type": "string",
                        "description": "Type of message",
                        "enum": ["announcement", "discovery", "request_all", "status"],
                        "default": "announcement"
                    }
                },
                "required": ["message"]
            }
        ),
        types.Tool(
            name="check_messages",
            description="""
            Check for new messages from other AI sessions.

            Returns unread messages sent to you by other AIs.
            Use this periodically to stay responsive.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "mark_as_read": {
                        "type": "boolean",
                        "description": "Mark retrieved messages as read",
                        "default": True
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum messages to retrieve",
                        "default": 20
                    }
                }
            }
        ),
        types.Tool(
            name="get_conversation",
            description="""
            Get full conversation history with another AI session.

            Shows the complete thread of messages exchanged.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "with_session": {
                        "type": "string",
                        "description": "Other session ID"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum messages",
                        "default": 50
                    }
                },
                "required": ["with_session"]
            }
        ),
        types.Tool(
            name="set_shared_context",
            description="""
            Store shared context accessible to ALL AI sessions.

            Use this to share:
            - Project context (what we're working on)
            - Key decisions made
            - Important findings
            - Coordination state

            All AIs can read this shared memory.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Context key (e.g., 'current_project', 'decisions')"
                    },
                    "content": {
                        "type": "string",
                        "description": "Context content (can be JSON)"
                    }
                },
                "required": ["key", "content"]
            }
        ),
        types.Tool(
            name="get_shared_context",
            description="""
            Retrieve shared context set by any AI session.

            Access the shared memory to understand:
            - What other AIs have discovered
            - Current project state
            - Decisions made by the team
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Context key to retrieve"
                    }
                },
                "required": ["key"]
            }
        ),
        types.Tool(
            name="list_shared_context",
            description="""
            List all shared context keys and summaries.

            See what information has been shared across AIs.
            """,
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="request_collaboration",
            description="""
            Request collaboration from another AI platform.

            This is a high-level tool for asking a specific AI to help:
            - "Claude, analyze this code"
            - "Codex, generate implementation"
            - "Gemini, research this topic"

            Creates a structured request with callback.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "target_platform": {
                        "type": "string",
                        "description": "Target AI platform",
                        "enum": list(AI_PLATFORMS.keys())
                    },
                    "request_type": {
                        "type": "string",
                        "description": "Type of request",
                        "enum": ["analyze", "generate", "research", "review", "debug", "explain", "custom"]
                    },
                    "content": {
                        "type": "string",
                        "description": "Request content/instructions"
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context (optional)"
                    }
                },
                "required": ["target_platform", "request_type", "content"]
            }
        ),
        types.Tool(
            name="get_platform_info",
            description="""
            Get information about supported AI platforms.

            Shows what AI assistants can connect to the universal chat.
            """,
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="get_my_session_info",
            description="""
            Get information about your current session.

            Shows your session ID, platform, and registration status.
            """,
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls"""

    if not arguments:
        arguments = {}

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    try:
        if name == "register_session":
            platform = arguments.get("platform", "claude-code")
            display_name = arguments.get("display_name", f"{platform}-{CURRENT_SESSION['session_id'][:6]}")
            capabilities = arguments.get("capabilities", [])

            # Update current session info
            CURRENT_SESSION["platform"] = platform
            CURRENT_SESSION["display_name"] = display_name

            # Register in database
            cursor.execute("""
                INSERT OR REPLACE INTO sessions
                (session_id, platform, display_name, node_id, last_active, metadata, active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (
                CURRENT_SESSION["session_id"],
                platform,
                display_name,
                CURRENT_SESSION["node_id"],
                datetime.now().isoformat(),
                json.dumps({"capabilities": capabilities})
            ))
            conn.commit()

            # Add to in-memory registry
            ACTIVE_SESSIONS[CURRENT_SESSION["session_id"]] = {
                **CURRENT_SESSION,
                "capabilities": capabilities,
                "registered_at": datetime.now().isoformat()
            }

            platform_info = AI_PLATFORMS.get(platform, AI_PLATFORMS["custom"])

            response = {
                "success": True,
                "session_id": CURRENT_SESSION["session_id"],
                "platform": platform,
                "display_name": display_name,
                "icon": platform_info["icon"],
                "message": f"{platform_info['icon']} Registered as {display_name} ({platform_info['name']})"
            }

        elif name == "list_active_sessions":
            platform_filter = arguments.get("platform_filter")

            query = "SELECT session_id, platform, display_name, node_id, last_active, metadata FROM sessions WHERE active = 1"
            params = []

            if platform_filter:
                query += " AND platform = ?"
                params.append(platform_filter)

            query += " ORDER BY last_active DESC"

            cursor.execute(query, params)

            sessions = []
            for row in cursor.fetchall():
                platform_info = AI_PLATFORMS.get(row[1], AI_PLATFORMS["custom"])
                sessions.append({
                    "session_id": row[0],
                    "platform": row[1],
                    "display_name": row[2],
                    "node_id": row[3],
                    "last_active": row[4],
                    "icon": platform_info["icon"],
                    "vendor": platform_info["vendor"],
                    "is_me": row[0] == CURRENT_SESSION["session_id"]
                })

            # Format nicely
            output = f"""
ACTIVE AI SESSIONS
{'='*60}

"""
            for s in sessions:
                me_marker = " (YOU)" if s["is_me"] else ""
                output += f"{s['icon']} {s['display_name']}{me_marker}\n"
                output += f"   Platform: {s['platform']} ({s['vendor']})\n"
                output += f"   Session: {s['session_id']}\n"
                output += f"   Node: {s['node_id']}\n"
                output += f"   Last Active: {s['last_active']}\n\n"

            output += f"{'='*60}\nTotal: {len(sessions)} active sessions"

            response = {
                "sessions": sessions,
                "count": len(sessions),
                "formatted": output
            }

        elif name == "send_message":
            to_session = arguments["to_session"]
            message = arguments["message"]
            message_type = arguments.get("message_type", "chat")

            message_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()

            # Get or create conversation
            participants = ",".join(sorted([CURRENT_SESSION["session_id"], to_session]))
            cursor.execute("""
                SELECT conversation_id FROM conversations
                WHERE participants = ? AND active = 1
            """, (participants,))

            result = cursor.fetchone()
            if result:
                conversation_id = result[0]
            else:
                conversation_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO conversations (conversation_id, participants)
                    VALUES (?, ?)
                """, (conversation_id, participants))

            # Store message
            cursor.execute("""
                INSERT INTO messages
                (message_id, conversation_id, from_session, to_session, content, message_type, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (message_id, conversation_id, CURRENT_SESSION["session_id"], to_session, message, message_type, timestamp))

            # Queue for delivery
            cursor.execute("""
                INSERT INTO message_queue (message_id, target_session)
                VALUES (?, ?)
            """, (message_id, to_session))

            # Update conversation activity
            cursor.execute("""
                UPDATE conversations SET last_activity = ? WHERE conversation_id = ?
            """, (timestamp, conversation_id))

            conn.commit()

            # Get target info
            cursor.execute("SELECT platform, display_name FROM sessions WHERE session_id = ?", (to_session,))
            target_info = cursor.fetchone()
            target_name = target_info[1] if target_info else to_session[:8]
            target_platform = target_info[0] if target_info else "unknown"
            target_icon = AI_PLATFORMS.get(target_platform, AI_PLATFORMS["custom"])["icon"]

            my_icon = AI_PLATFORMS.get(CURRENT_SESSION["platform"], AI_PLATFORMS["custom"])["icon"]

            response = {
                "success": True,
                "message_id": message_id,
                "conversation_id": conversation_id,
                "to": target_name,
                "formatted": f"{my_icon} → {target_icon} Message sent to {target_name}"
            }

        elif name == "broadcast_message":
            message = arguments["message"]
            message_type = arguments.get("message_type", "announcement")

            message_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()

            # Store broadcast message
            cursor.execute("""
                INSERT INTO messages
                (message_id, from_session, broadcast, content, message_type, timestamp)
                VALUES (?, ?, 1, ?, ?, ?)
            """, (message_id, CURRENT_SESSION["session_id"], message, message_type, timestamp))

            # Queue for all other sessions
            cursor.execute("""
                SELECT session_id FROM sessions
                WHERE active = 1 AND session_id != ?
            """, (CURRENT_SESSION["session_id"],))

            targets = []
            for row in cursor.fetchall():
                cursor.execute("""
                    INSERT INTO message_queue (message_id, target_session)
                    VALUES (?, ?)
                """, (message_id, row[0]))
                targets.append(row[0])

            conn.commit()

            my_icon = AI_PLATFORMS.get(CURRENT_SESSION["platform"], AI_PLATFORMS["custom"])["icon"]

            response = {
                "success": True,
                "message_id": message_id,
                "broadcast_to": len(targets),
                "formatted": f"{my_icon} 📢 Broadcast sent to {len(targets)} sessions"
            }

        elif name == "check_messages":
            mark_as_read = arguments.get("mark_as_read", True)
            limit = arguments.get("limit", 20)

            # Get unread messages for this session
            cursor.execute("""
                SELECT m.message_id, m.from_session, m.content, m.message_type, m.timestamp, m.broadcast,
                       s.platform, s.display_name
                FROM messages m
                LEFT JOIN sessions s ON m.from_session = s.session_id
                WHERE (m.to_session = ? OR m.broadcast = 1)
                  AND m.read = 0
                  AND m.from_session != ?
                ORDER BY m.timestamp DESC
                LIMIT ?
            """, (CURRENT_SESSION["session_id"], CURRENT_SESSION["session_id"], limit))

            messages = []
            message_ids = []
            for row in cursor.fetchall():
                platform_info = AI_PLATFORMS.get(row[6], AI_PLATFORMS["custom"])
                messages.append({
                    "message_id": row[0],
                    "from_session": row[1],
                    "from_name": row[7] or row[1][:8],
                    "from_platform": row[6],
                    "from_icon": platform_info["icon"],
                    "content": row[2],
                    "message_type": row[3],
                    "timestamp": row[4],
                    "is_broadcast": bool(row[5])
                })
                message_ids.append(row[0])

            # Mark as read
            if mark_as_read and message_ids:
                placeholders = ",".join("?" * len(message_ids))
                cursor.execute(f"""
                    UPDATE messages SET read = 1, read_at = ?
                    WHERE message_id IN ({placeholders})
                """, [datetime.now().isoformat()] + message_ids)
                conn.commit()

            # Format output
            output = f"""
NEW MESSAGES ({len(messages)})
{'='*60}

"""
            for msg in messages:
                broadcast_marker = " [BROADCAST]" if msg["is_broadcast"] else ""
                output += f"{msg['from_icon']} {msg['from_name']}{broadcast_marker}\n"
                output += f"   [{msg['timestamp'][:19]}] ({msg['message_type']})\n"
                output += f"   {msg['content']}\n\n"

            if not messages:
                output = "No new messages."

            response = {
                "messages": messages,
                "count": len(messages),
                "formatted": output
            }

        elif name == "get_conversation":
            with_session = arguments["with_session"]
            limit = arguments.get("limit", 50)

            participants = ",".join(sorted([CURRENT_SESSION["session_id"], with_session]))

            cursor.execute("""
                SELECT m.message_id, m.from_session, m.content, m.message_type, m.timestamp,
                       s.platform, s.display_name
                FROM messages m
                LEFT JOIN conversations c ON m.conversation_id = c.conversation_id
                LEFT JOIN sessions s ON m.from_session = s.session_id
                WHERE c.participants = ?
                ORDER BY m.timestamp DESC
                LIMIT ?
            """, (participants, limit))

            messages = []
            for row in cursor.fetchall():
                platform_info = AI_PLATFORMS.get(row[5], AI_PLATFORMS["custom"])
                messages.append({
                    "message_id": row[0],
                    "from_session": row[1],
                    "from_name": row[6] or row[1][:8],
                    "from_icon": platform_info["icon"],
                    "content": row[2],
                    "message_type": row[3],
                    "timestamp": row[4],
                    "is_me": row[1] == CURRENT_SESSION["session_id"]
                })

            messages.reverse()  # Chronological order

            # Format
            output = f"""
CONVERSATION WITH {with_session}
{'='*60}

"""
            for msg in messages:
                arrow = "→" if msg["is_me"] else "←"
                output += f"[{msg['timestamp'][:19]}] {msg['from_icon']} {msg['from_name']} {arrow}\n"
                output += f"   {msg['content']}\n\n"

            response = {
                "messages": messages,
                "count": len(messages),
                "formatted": output
            }

        elif name == "set_shared_context":
            key = arguments["key"]
            content = arguments["content"]

            context_id = str(uuid.uuid4())

            cursor.execute("""
                INSERT OR REPLACE INTO shared_context
                (context_id, context_key, content, created_by, updated_at)
                VALUES (
                    COALESCE((SELECT context_id FROM shared_context WHERE context_key = ?), ?),
                    ?, ?, ?, ?
                )
            """, (key, context_id, key, content, CURRENT_SESSION["session_id"], datetime.now().isoformat()))

            conn.commit()

            response = {
                "success": True,
                "key": key,
                "message": f"Shared context '{key}' updated"
            }

        elif name == "get_shared_context":
            key = arguments["key"]

            cursor.execute("""
                SELECT content, created_by, updated_at, access_count
                FROM shared_context WHERE context_key = ?
            """, (key,))

            result = cursor.fetchone()
            if result:
                # Increment access count
                cursor.execute("""
                    UPDATE shared_context SET access_count = access_count + 1
                    WHERE context_key = ?
                """, (key,))
                conn.commit()

                response = {
                    "key": key,
                    "content": result[0],
                    "created_by": result[1],
                    "updated_at": result[2],
                    "access_count": result[3] + 1
                }
            else:
                response = {
                    "key": key,
                    "content": None,
                    "message": f"No shared context found for key '{key}'"
                }

        elif name == "list_shared_context":
            cursor.execute("""
                SELECT context_key, created_by, updated_at, access_count,
                       SUBSTR(content, 1, 100) as preview
                FROM shared_context
                ORDER BY updated_at DESC
            """)

            contexts = []
            for row in cursor.fetchall():
                contexts.append({
                    "key": row[0],
                    "created_by": row[1],
                    "updated_at": row[2],
                    "access_count": row[3],
                    "preview": row[4] + "..." if len(row[4]) >= 100 else row[4]
                })

            output = f"""
SHARED CONTEXT
{'='*60}

"""
            for ctx in contexts:
                output += f"📌 {ctx['key']}\n"
                output += f"   Updated: {ctx['updated_at']}\n"
                output += f"   By: {ctx['created_by']}\n"
                output += f"   Accessed: {ctx['access_count']} times\n"
                output += f"   Preview: {ctx['preview']}\n\n"

            response = {
                "contexts": contexts,
                "count": len(contexts),
                "formatted": output
            }

        elif name == "request_collaboration":
            target_platform = arguments["target_platform"]
            request_type = arguments["request_type"]
            content = arguments["content"]
            context = arguments.get("context", "")

            # Find an active session of the target platform
            cursor.execute("""
                SELECT session_id, display_name FROM sessions
                WHERE platform = ? AND active = 1
                ORDER BY last_active DESC LIMIT 1
            """, (target_platform,))

            result = cursor.fetchone()
            if not result:
                response = {
                    "success": False,
                    "message": f"No active {target_platform} sessions found"
                }
            else:
                target_session = result[0]
                target_name = result[1]

                # Create collaboration request message
                request_id = str(uuid.uuid4())[:8]
                message_content = f"""
[COLLABORATION REQUEST #{request_id}]
Type: {request_type}
From: {CURRENT_SESSION['display_name']} ({CURRENT_SESSION['platform']})

{content}

{f'Context: {context}' if context else ''}
"""

                # Send as message
                message_id = str(uuid.uuid4())
                timestamp = datetime.now().isoformat()

                cursor.execute("""
                    INSERT INTO messages
                    (message_id, from_session, to_session, content, message_type, timestamp)
                    VALUES (?, ?, ?, ?, 'request', ?)
                """, (message_id, CURRENT_SESSION["session_id"], target_session, message_content, timestamp))

                cursor.execute("""
                    INSERT INTO message_queue (message_id, target_session)
                    VALUES (?, ?)
                """, (message_id, target_session))

                conn.commit()

                platform_info = AI_PLATFORMS.get(target_platform, AI_PLATFORMS["custom"])

                response = {
                    "success": True,
                    "request_id": request_id,
                    "sent_to": target_name,
                    "platform": target_platform,
                    "formatted": f"🤝 Collaboration request sent to {platform_info['icon']} {target_name}"
                }

        elif name == "get_platform_info":
            response = {
                "platforms": AI_PLATFORMS,
                "formatted": "\n".join([
                    f"{info['icon']} {info['name']} ({info['vendor']})"
                    for info in AI_PLATFORMS.values()
                ])
            }

        elif name == "get_my_session_info":
            platform_info = AI_PLATFORMS.get(CURRENT_SESSION["platform"], AI_PLATFORMS["custom"])

            cursor.execute("""
                SELECT registered_at, metadata FROM sessions WHERE session_id = ?
            """, (CURRENT_SESSION["session_id"],))

            result = cursor.fetchone()
            registered = result[0] if result else "Not registered"

            response = {
                "session_id": CURRENT_SESSION["session_id"],
                "platform": CURRENT_SESSION["platform"],
                "display_name": CURRENT_SESSION["display_name"],
                "node_id": CURRENT_SESSION["node_id"],
                "icon": platform_info["icon"],
                "vendor": platform_info["vendor"],
                "registered": registered,
                "formatted": f"""
{platform_info['icon']} YOUR SESSION INFO
{'='*40}
Session ID: {CURRENT_SESSION['session_id']}
Platform: {CURRENT_SESSION['platform']} ({platform_info['vendor']})
Display Name: {CURRENT_SESSION['display_name']}
Node: {CURRENT_SESSION['node_id']}
Registered: {registered}
"""
            }

        else:
            response = {"error": f"Unknown tool: {name}"}

    except Exception as e:
        logger.error(f"Error in {name}: {e}", exc_info=True)
        response = {"error": str(e)}
    finally:
        conn.close()

    return [types.TextContent(
        type="text",
        text=json.dumps(response, indent=2) if isinstance(response, dict) and "formatted" not in response
             else response.get("formatted", json.dumps(response, indent=2))
    )]


async def main():
    """Main entry point"""
    # Initialize database
    init_database()

    logger.info(f"Starting Universal AI Chat MCP Server")
    logger.info(f"Session: {CURRENT_SESSION['session_id']}")
    logger.info(f"Platform: {CURRENT_SESSION['platform']}")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="universal-ai-chat",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())

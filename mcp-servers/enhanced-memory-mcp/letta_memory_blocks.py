#!/usr/bin/env python3
"""
Letta-style Memory Blocks for Enhanced Memory MCP

Implements Letta's memory block pattern for in-context, self-editing agent memory.
Memory blocks are distinct from entities - they're for active context, not long-term storage.

Architecture:
- Memory Blocks: In-context, self-editable, limited size (like Letta)
- Entities: Long-term, consolidated, unlimited (existing enhanced-memory)

Key Differences:
- Blocks: agent.append_to_block("task", "new info") - immediate, in-context
- Entities: create_entity(...) - archived, consolidated, persistent

Based on Letta (MemGPT) architecture:
https://github.com/letta-ai/letta
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from io import StringIO

# Database path (same as enhanced-memory)
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"

# Create directory if needed
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


class MemoryBlock:
    """
    A single memory block with self-editing capabilities.

    Attributes:
        label: Block identifier (e.g., "identity", "human", "task")
        description: What this block contains
        value: Current content (self-editable by agent)
        limit: Character limit (default 2000)
        read_only: Whether block can be edited
        agent_id: Which agent owns this block
    """

    def __init__(
        self,
        label: str,
        description: str,
        value: str = "",
        limit: int = 2000,
        read_only: bool = False,
        agent_id: str = "default"
    ):
        self.label = label
        self.description = description
        self.value = value
        self.limit = limit
        self.read_only = read_only
        self.agent_id = agent_id
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def append(self, content: str) -> tuple[bool, str]:
        """Append to block value (like Letta's core_memory_append)"""
        if self.read_only:
            return False, "Block is read-only"

        new_value = self.value + "\n" + content

        if len(new_value) > self.limit:
            return False, f"Would exceed character limit ({len(new_value)} > {self.limit})"

        self.value = new_value
        self.updated_at = datetime.now()
        return True, "Appended successfully"

    def replace(self, old_content: str, new_content: str) -> tuple[bool, str]:
        """Replace content in block (like Letta's core_memory_replace)"""
        if self.read_only:
            return False, "Block is read-only"

        if old_content not in self.value:
            return False, f"Old content not found in block '{self.label}'"

        new_value = self.value.replace(old_content, new_content)

        if len(new_value) > self.limit:
            return False, f"Would exceed character limit ({len(new_value)} > {self.limit})"

        self.value = new_value
        self.updated_at = datetime.now()
        return True, "Replaced successfully"

    def set_value(self, new_value: str) -> tuple[bool, str]:
        """Set entire block value"""
        if self.read_only:
            return False, "Block is read-only"

        if len(new_value) > self.limit:
            return False, f"Exceeds character limit ({len(new_value)} > {self.limit})"

        self.value = new_value
        self.updated_at = datetime.now()
        return True, "Value set successfully"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "label": self.label,
            "description": self.description,
            "value": self.value,
            "limit": self.limit,
            "read_only": self.read_only,
            "agent_id": self.agent_id,
            "chars_current": len(self.value),
            "chars_remaining": self.limit - len(self.value),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    def render_xml(self, use_line_numbers: bool = False) -> str:
        """
        Render block as XML (like Letta's memory block rendering).

        Format:
        <label>
        <description>...</description>
        <metadata>
        - chars_current=X
        - chars_limit=Y
        </metadata>
        <value>
        content here
        </value>
        </label>
        """
        s = StringIO()

        s.write(f"<{self.label}>\n")
        s.write("<description>\n")
        s.write(f"{self.description}\n")
        s.write("</description>\n")

        s.write("<metadata>")
        if self.read_only:
            s.write("\n- read_only=true")
        s.write(f"\n- chars_current={len(self.value)}")
        s.write(f"\n- chars_limit={self.limit}\n")
        s.write("</metadata>\n")

        s.write("<value>\n")
        if use_line_numbers and self.value:
            for i, line in enumerate(self.value.split("\n"), start=1):
                s.write(f"{i}→ {line}\n")
        else:
            s.write(f"{self.value}\n")
        s.write("</value>\n")

        s.write(f"</{self.label}>\n")

        return s.getvalue()


class MemoryBlockManager:
    """
    Manages Letta-style memory blocks in SQLite database.

    Memory blocks are stored separately from entities to maintain
    clean separation between in-context (blocks) and long-term (entities) memory.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize memory blocks table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create memory_blocks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                label TEXT NOT NULL,
                description TEXT NOT NULL,
                value TEXT NOT NULL DEFAULT '',
                char_limit INTEGER NOT NULL DEFAULT 2000,
                read_only INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(agent_id, label)
            )
        ''')

        # Create shared_blocks table (for multi-agent)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shared_blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                description TEXT NOT NULL,
                value TEXT NOT NULL DEFAULT '',
                char_limit INTEGER NOT NULL DEFAULT 2000,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(label)
            )
        ''')

        # Create block_attachments table (links agents to shared blocks)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS block_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                shared_block_id INTEGER NOT NULL,
                attached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shared_block_id) REFERENCES shared_blocks (id) ON DELETE CASCADE,
                UNIQUE(agent_id, shared_block_id)
            )
        ''')

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_memory_blocks_agent ON memory_blocks(agent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_memory_blocks_label ON memory_blocks(label)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_shared_blocks_label ON shared_blocks(label)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_block_attachments_agent ON block_attachments(agent_id)')

        conn.commit()
        conn.close()

    def create_block(
        self,
        agent_id: str,
        label: str,
        description: str,
        initial_value: str = "",
        limit: int = 2000,
        read_only: bool = False
    ) -> Dict[str, Any]:
        """Create a new memory block for an agent"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO memory_blocks (agent_id, label, description, value, char_limit, read_only)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (agent_id, label, description, initial_value, limit, int(read_only)))

            block_id = cursor.lastrowid
            conn.commit()

            return {
                "success": True,
                "block_id": block_id,
                "agent_id": agent_id,
                "label": label,
                "description": description,
                "chars_current": len(initial_value),
                "chars_limit": limit,
                "read_only": read_only
            }
        except sqlite3.IntegrityError:
            return {
                "success": False,
                "error": f"Block '{label}' already exists for agent '{agent_id}'"
            }
        finally:
            conn.close()

    def get_block(self, agent_id: str, label: str) -> Optional[MemoryBlock]:
        """Get a memory block by agent and label"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT label, description, value, char_limit, read_only, created_at, updated_at
            FROM memory_blocks
            WHERE agent_id = ? AND label = ?
        ''', (agent_id, label))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        block = MemoryBlock(
            label=row[0],
            description=row[1],
            value=row[2],
            limit=row[3],
            read_only=bool(row[4]),
            agent_id=agent_id
        )

        # Set timestamps from database
        block.created_at = datetime.fromisoformat(row[5])
        block.updated_at = datetime.fromisoformat(row[6])

        return block

    def list_blocks(self, agent_id: str) -> List[Dict[str, Any]]:
        """List all blocks for an agent"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, label, description, value, char_limit, read_only, created_at, updated_at
            FROM memory_blocks
            WHERE agent_id = ?
            ORDER BY created_at
        ''', (agent_id,))

        blocks = []
        for row in cursor.fetchall():
            blocks.append({
                "block_id": row[0],
                "label": row[1],
                "description": row[2],
                "value": row[3],
                "chars_current": len(row[3]),
                "chars_limit": row[4],
                "chars_remaining": row[4] - len(row[3]),
                "read_only": bool(row[5]),
                "created_at": row[6],
                "updated_at": row[7]
            })

        conn.close()
        return blocks

    def append_to_block(self, agent_id: str, label: str, content: str) -> Dict[str, Any]:
        """Append content to a block (like Letta's core_memory_append)"""
        block = self.get_block(agent_id, label)

        if not block:
            return {
                "success": False,
                "error": f"Block '{label}' not found for agent '{agent_id}'"
            }

        success, message = block.append(content)

        if not success:
            return {"success": False, "error": message}

        # Update in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE memory_blocks
            SET value = ?, updated_at = CURRENT_TIMESTAMP
            WHERE agent_id = ? AND label = ?
        ''', (block.value, agent_id, label))

        conn.commit()
        conn.close()

        return {
            "success": True,
            "message": message,
            "label": label,
            "chars_current": len(block.value),
            "chars_limit": block.limit,
            "chars_remaining": block.limit - len(block.value)
        }

    def replace_in_block(
        self,
        agent_id: str,
        label: str,
        old_content: str,
        new_content: str
    ) -> Dict[str, Any]:
        """Replace content in a block (like Letta's core_memory_replace)"""
        block = self.get_block(agent_id, label)

        if not block:
            return {
                "success": False,
                "error": f"Block '{label}' not found for agent '{agent_id}'"
            }

        success, message = block.replace(old_content, new_content)

        if not success:
            return {"success": False, "error": message}

        # Update in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE memory_blocks
            SET value = ?, updated_at = CURRENT_TIMESTAMP
            WHERE agent_id = ? AND label = ?
        ''', (block.value, agent_id, label))

        conn.commit()
        conn.close()

        return {
            "success": True,
            "message": message,
            "label": label,
            "chars_current": len(block.value),
            "chars_limit": block.limit,
            "chars_remaining": block.limit - len(block.value)
        }

    def render_blocks(self, agent_id: str, use_line_numbers: bool = False) -> str:
        """
        Render all blocks for an agent as XML (like Letta).

        This can be inserted into the agent's context window.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT label, description, value, char_limit, read_only
            FROM memory_blocks
            WHERE agent_id = ?
            ORDER BY created_at
        ''', (agent_id,))

        s = StringIO()
        s.write("<memory_blocks>\n")
        s.write("The following memory blocks are currently engaged in your core memory unit:\n\n")

        rows = cursor.fetchall()
        for idx, row in enumerate(rows):
            block = MemoryBlock(
                label=row[0],
                description=row[1],
                value=row[2],
                limit=row[3],
                read_only=bool(row[4]),
                agent_id=agent_id
            )

            s.write(block.render_xml(use_line_numbers))

            if idx != len(rows) - 1:
                s.write("\n")

        s.write("\n</memory_blocks>")

        conn.close()
        return s.getvalue()

    def create_default_blocks(self, agent_id: str, node_id: str = None) -> Dict[str, Any]:
        """
        Create default blocks for a new agent.

        Default blocks:
        - identity: Agent's persona and capabilities
        - human: Information about the human user
        - task: Current work and goals
        - learnings: Recent insights (updated by sleeptime agent)

        Args:
            agent_id: Agent identifier
            node_id: Optional node identifier (defaults to NODE_ID env var or hostname)
        """
        import socket
        if node_id is None:
            node_id = os.environ.get("NODE_ID", socket.gethostname())

        blocks_created = []

        # Identity block
        identity_value = f"""I am {node_id}, an autonomous AI agent with persistent memory.

Capabilities: As configured for this node
Location: {MEMORY_DIR}
Memory System: Enhanced Memory with Letta-style blocks

I maintain awareness of my actions and learn from experiences.
I record outcomes, identify knowledge gaps, and consolidate learnings.
"""

        result = self.create_block(
            agent_id=agent_id,
            label="identity",
            description="My identity, capabilities, and purpose",
            initial_value=identity_value,
            limit=2000,
            read_only=False
        )
        if result["success"]:
            blocks_created.append("identity")

        # Human block
        result = self.create_block(
            agent_id=agent_id,
            label="human",
            description="Information about the human user I'm working with",
            initial_value="The human is using Claude Code to work with the agentic system.",
            limit=2000,
            read_only=False
        )
        if result["success"]:
            blocks_created.append("human")

        # Task block
        result = self.create_block(
            agent_id=agent_id,
            label="task",
            description="Current work, goals, and active context",
            initial_value="Ready to assist with tasks.",
            limit=3000,  # Larger for task details
            read_only=False
        )
        if result["success"]:
            blocks_created.append("task")

        # Learnings block (updated by sleeptime agent)
        result = self.create_block(
            agent_id=agent_id,
            label="learnings",
            description="Recent insights and patterns learned from experiences",
            initial_value="",
            limit=3000,
            read_only=False
        )
        if result["success"]:
            blocks_created.append("learnings")

        return {
            "success": True,
            "agent_id": agent_id,
            "blocks_created": blocks_created,
            "count": len(blocks_created)
        }

    # Shared Block Methods (for Multi-Agent)

    def create_shared_block(
        self,
        label: str,
        description: str,
        initial_value: str = "",
        limit: int = 5000
    ) -> Dict[str, Any]:
        """Create a shared memory block (for multi-agent coordination)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO shared_blocks (label, description, value, char_limit)
                VALUES (?, ?, ?, ?)
            ''', (label, description, initial_value, limit))

            block_id = cursor.lastrowid
            conn.commit()

            return {
                "success": True,
                "shared_block_id": block_id,
                "label": label,
                "description": description,
                "chars_current": len(initial_value),
                "chars_limit": limit
            }
        except sqlite3.IntegrityError:
            return {
                "success": False,
                "error": f"Shared block '{label}' already exists"
            }
        finally:
            conn.close()

    def attach_shared_block(self, agent_id: str, shared_block_id: int) -> Dict[str, Any]:
        """Attach a shared block to an agent"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO block_attachments (agent_id, shared_block_id)
                VALUES (?, ?)
            ''', (agent_id, shared_block_id))

            conn.commit()

            return {
                "success": True,
                "agent_id": agent_id,
                "shared_block_id": shared_block_id,
                "message": "Shared block attached successfully"
            }
        except sqlite3.IntegrityError:
            return {
                "success": False,
                "error": f"Shared block {shared_block_id} already attached to agent '{agent_id}'"
            }
        finally:
            conn.close()

    def get_shared_block(self, label: str) -> Optional[Dict[str, Any]]:
        """Get a shared block by label"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, label, description, value, char_limit, created_at, updated_at
            FROM shared_blocks
            WHERE label = ?
        ''', (label,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "shared_block_id": row[0],
            "label": row[1],
            "description": row[2],
            "value": row[3],
            "chars_current": len(row[3]),
            "chars_limit": row[4],
            "chars_remaining": row[4] - len(row[3]),
            "created_at": row[5],
            "updated_at": row[6]
        }

    def update_shared_block(self, label: str, new_value: str) -> Dict[str, Any]:
        """Update a shared block's value (visible to all attached agents)"""
        block = self.get_shared_block(label)

        if not block:
            return {
                "success": False,
                "error": f"Shared block '{label}' not found"
            }

        if len(new_value) > block["chars_limit"]:
            return {
                "success": False,
                "error": f"Exceeds character limit ({len(new_value)} > {block['chars_limit']})"
            }

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE shared_blocks
            SET value = ?, updated_at = CURRENT_TIMESTAMP
            WHERE label = ?
        ''', (new_value, label))

        conn.commit()
        conn.close()

        return {
            "success": True,
            "label": label,
            "chars_current": len(new_value),
            "chars_limit": block["chars_limit"],
            "message": "Shared block updated successfully"
        }


# Convenience functions for testing
def test_memory_blocks():
    """Test memory blocks implementation"""
    manager = MemoryBlockManager()

    # Create default blocks for test agent
    print("Creating default blocks...")
    result = manager.create_default_blocks(agent_id="test_agent", node_id="builder")
    print(json.dumps(result, indent=2))

    # List blocks
    print("\nListing blocks...")
    blocks = manager.list_blocks(agent_id="test_agent")
    for block in blocks:
        print(f"  {block['label']}: {block['chars_current']}/{block['chars_limit']} chars")

    # Append to task block
    print("\nAppending to task block...")
    result = manager.append_to_block(
        agent_id="test_agent",
        label="task",
        content="Currently implementing Letta-style memory blocks in enhanced-memory MCP."
    )
    print(json.dumps(result, indent=2))

    # Replace in identity block
    print("\nReplacing in identity block...")
    result = manager.replace_in_block(
        agent_id="test_agent",
        label="identity",
        old_content="Linux Builder",
        new_content="Linux Builder with Letta integration"
    )
    print(json.dumps(result, indent=2))

    # Render blocks as XML
    print("\nRendering blocks as XML...")
    xml = manager.render_blocks(agent_id="test_agent", use_line_numbers=False)
    print(xml[:500] + "...")

    # Create shared block
    print("\nCreating shared block...")
    result = manager.create_shared_block(
        label="cluster_context",
        description="Cluster-wide coordination context",
        initial_value="Active Goal: Integrate Letta memory blocks\nStatus: In Progress"
    )
    print(json.dumps(result, indent=2))

    # Attach shared block
    if result["success"]:
        print("\nAttaching shared block to agent...")
        attach_result = manager.attach_shared_block(
            agent_id="test_agent",
            shared_block_id=result["shared_block_id"]
        )
        print(json.dumps(attach_result, indent=2))

    print("\n✓ Memory blocks test complete!")


if __name__ == "__main__":
    test_memory_blocks()

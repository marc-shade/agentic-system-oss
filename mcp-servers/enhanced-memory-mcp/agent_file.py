#!/usr/bin/env python3
"""
Agent File (.af) Format for Agent State Portability

Implements Letta's Agent File format for exporting and importing complete agent state.
Enables agent backup, transfer between nodes, and disaster recovery.

Agent File (.af) Format:
- JSON-based serialization
- Contains: memory blocks, entities, identity, skills, beliefs
- Compressed with gzip for efficiency
- Portable across cluster nodes

Use Cases:
- Checkpoint agent state before risky operations
- Transfer agent between nodes (builder → orchestrator)
- Backup cognitive state for disaster recovery
- Share trained agents with other clusters
"""

import json
import gzip
import sqlite3
import socket
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from letta_memory_blocks import MemoryBlockManager

logger = logging.getLogger(__name__)

# Database path
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


class AgentFileExporter:
    """Export agent state to .af format"""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.block_manager = MemoryBlockManager(db_path)

    def export_memory_blocks(self, agent_id: str) -> List[Dict[str, Any]]:
        """Export all memory blocks for an agent"""
        blocks = self.block_manager.list_blocks(agent_id)
        return blocks

    def export_entities(
        self,
        agent_id: str,
        include_tiers: List[str] = ["episodic", "semantic", "procedural", "working"]
    ) -> List[Dict[str, Any]]:
        """Export entities associated with agent"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get entities with observations
        cursor.execute('''
            SELECT e.id, e.name, e.entity_type, e.tier, e.created_at
            FROM entities e
            WHERE e.tier IN ({})
            ORDER BY e.created_at DESC
            LIMIT 1000
        '''.format(','.join(['?'] * len(include_tiers))), include_tiers)

        entities = []
        for row in cursor.fetchall():
            entity_id = row[0]

            # Get observations
            cursor.execute('''
                SELECT content, created_at
                FROM observations
                WHERE entity_id = ?
                ORDER BY created_at
            ''', (entity_id,))

            observations = [
                {"content": obs_row[0], "timestamp": obs_row[1]}
                for obs_row in cursor.fetchall()
            ]

            entities.append({
                "id": entity_id,
                "name": row[1],
                "entity_type": row[2],
                "tier": row[3],
                "created_at": row[4],
                "observations": observations
            })

        conn.close()
        return entities

    def export_agent(
        self,
        agent_id: str,
        include_entities: bool = True,
        entity_limit: int = 1000
    ) -> Dict[str, Any]:
        """
        Export complete agent state.

        Args:
            agent_id: Agent to export
            include_entities: Whether to include long-term entities (default True)
            entity_limit: Maximum entities to export (default 1000)

        Returns:
            Complete agent state dictionary
        """
        logger.info(f"📦 Exporting agent: {agent_id}")

        # Export memory blocks
        memory_blocks = self.export_memory_blocks(agent_id)
        logger.info(f"   Exported {len(memory_blocks)} memory blocks")

        # Export entities if requested
        entities = []
        if include_entities:
            entities = self.export_entities(agent_id)
            logger.info(f"   Exported {len(entities)} entities")

        # Build agent file
        agent_file = {
            "version": "1.0",
            "format": "letta-enhanced-memory",
            "exported_at": datetime.now().isoformat(),
            "agent": {
                "agent_id": agent_id,
                "memory_blocks": memory_blocks,
                "entities": entities,
                "entity_count": len(entities),
                "block_count": len(memory_blocks)
            },
            "metadata": {
                "exporter": "enhanced-memory-mcp",
                "database_path": str(self.db_path),
                "cluster_node": os.environ.get("NODE_ID", socket.gethostname())
            }
        }

        return agent_file

    def save_agent_file(
        self,
        agent_id: str,
        output_path: Path,
        compress: bool = True
    ) -> Dict[str, Any]:
        """
        Export agent and save to .af file.

        Args:
            agent_id: Agent to export
            output_path: Where to save .af file
            compress: Whether to gzip compress (default True)

        Returns:
            Export result with file size
        """
        # Export agent
        agent_data = self.export_agent(agent_id)

        # Serialize to JSON
        json_data = json.dumps(agent_data, indent=2)

        if compress:
            # Compress with gzip
            with gzip.open(output_path, 'wt', encoding='utf-8') as f:
                f.write(json_data)
        else:
            # Save uncompressed
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_data)

        file_size = output_path.stat().st_size

        logger.info(f"✅ Agent file saved: {output_path}")
        logger.info(f"   Size: {file_size / 1024:.2f} KB")

        return {
            "success": True,
            "agent_id": agent_id,
            "file_path": str(output_path),
            "file_size_bytes": file_size,
            "file_size_kb": file_size / 1024,
            "compressed": compress,
            "blocks_exported": agent_data["agent"]["block_count"],
            "entities_exported": agent_data["agent"]["entity_count"]
        }


class AgentFileImporter:
    """Import agent state from .af format"""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.block_manager = MemoryBlockManager(db_path)

    def load_agent_file(self, file_path: Path) -> Dict[str, Any]:
        """Load .af file and parse"""
        try:
            # Try gzip first
            with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                agent_data = json.load(f)
        except gzip.BadGzipFile:
            # Not compressed, load as plain JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                agent_data = json.load(f)

        logger.info(f"📥 Loaded agent file: {file_path}")
        logger.info(f"   Version: {agent_data.get('version', 'unknown')}")
        logger.info(f"   Format: {agent_data.get('format', 'unknown')}")

        return agent_data

    def import_memory_blocks(
        self,
        agent_id: str,
        memory_blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Import memory blocks for an agent"""
        imported = []
        skipped = []

        for block in memory_blocks:
            result = self.block_manager.create_block(
                agent_id=agent_id,
                label=block["label"],
                description=block.get("description", ""),
                initial_value=block.get("value", ""),
                limit=block.get("chars_limit", 2000),
                read_only=block.get("read_only", False)
            )

            if result["success"]:
                imported.append(block["label"])
            else:
                skipped.append({"label": block["label"], "reason": result.get("error", "unknown")})

        return {
            "imported": imported,
            "skipped": skipped,
            "count": len(imported)
        }

    def import_entities(
        self,
        entities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Import entities into database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        imported = []
        skipped = []

        for entity in entities:
            try:
                # Insert entity
                cursor.execute('''
                    INSERT INTO entities (name, entity_type, tier, created_at)
                    VALUES (?, ?, ?, ?)
                ''', (
                    entity["name"],
                    entity["entity_type"],
                    entity["tier"],
                    entity.get("created_at", datetime.now().isoformat())
                ))

                entity_id = cursor.lastrowid

                # Insert observations
                for obs in entity.get("observations", []):
                    cursor.execute('''
                        INSERT INTO observations (entity_id, content, created_at)
                        VALUES (?, ?, ?)
                    ''', (entity_id, obs["content"], obs.get("timestamp", datetime.now().isoformat())))

                imported.append(entity["name"])

            except sqlite3.IntegrityError as e:
                skipped.append({"name": entity["name"], "reason": str(e)})

        conn.commit()
        conn.close()

        return {
            "imported": imported,
            "skipped": skipped,
            "count": len(imported)
        }

    def import_agent(
        self,
        file_path: Path,
        new_agent_id: Optional[str] = None,
        import_entities: bool = True
    ) -> Dict[str, Any]:
        """
        Import complete agent from .af file.

        Args:
            file_path: Path to .af file
            new_agent_id: Optional new agent ID (defaults to original)
            import_entities: Whether to import entities (default True)

        Returns:
            Import result with statistics
        """
        # Load agent file
        agent_data = self.load_agent_file(file_path)

        original_agent_id = agent_data["agent"]["agent_id"]
        agent_id = new_agent_id or original_agent_id

        logger.info(f"📥 Importing agent: {original_agent_id} → {agent_id}")

        # Import memory blocks
        blocks_result = self.import_memory_blocks(
            agent_id=agent_id,
            memory_blocks=agent_data["agent"]["memory_blocks"]
        )

        logger.info(f"   Imported {blocks_result['count']} memory blocks")

        # Import entities if requested
        entities_result = {"imported": [], "skipped": [], "count": 0}
        if import_entities and agent_data["agent"]["entities"]:
            entities_result = self.import_entities(agent_data["agent"]["entities"])
            logger.info(f"   Imported {entities_result['count']} entities")

        return {
            "success": True,
            "original_agent_id": original_agent_id,
            "new_agent_id": agent_id,
            "file_path": str(file_path),
            "blocks_imported": blocks_result["count"],
            "blocks_skipped": len(blocks_result["skipped"]),
            "entities_imported": entities_result["count"],
            "entities_skipped": len(entities_result["skipped"])
        }


# Convenience functions for testing
def test_agent_file():
    """Test agent file export/import"""
    print("Testing Agent File (.af) export/import...")

    # Export
    exporter = AgentFileExporter()
    output_path = MEMORY_DIR / "test_agent.af"

    print("\nExporting agent...")
    export_result = exporter.save_agent_file(
        agent_id="test_agent",
        output_path=output_path,
        compress=True
    )
    print(json.dumps(export_result, indent=2))

    # Import
    importer = AgentFileImporter()

    print("\nImporting agent...")
    import_result = importer.import_agent(
        file_path=output_path,
        new_agent_id="test_agent_imported",
        import_entities=True
    )
    print(json.dumps(import_result, indent=2))

    print("\n✓ Agent file test complete!")


if __name__ == "__main__":
    test_agent_file()

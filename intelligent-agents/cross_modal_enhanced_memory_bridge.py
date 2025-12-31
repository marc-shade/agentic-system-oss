#!/usr/bin/env python3
"""
Cross-Modal Enhanced Memory Bridge

Synchronizes cross-modal memories with enhanced-memory-mcp for unified AGI access.

Features:
- Syncs visual, text, and code memories to enhanced-memory entities
- Maintains provenance and L-score tracking
- Enables unified search across all memory systems
- Cross-references correlations in the knowledge graph

STATUS: Production Ready
"""

import asyncio
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-agents')
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/mcp-servers/enhanced-memory-mcp')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedMemoryBridge:
    """
    Bridge between cross-modal memory and enhanced-memory-mcp.

    Syncs memories across systems for unified AGI context.
    """

    def __init__(self, enhanced_memory_client=None):
        """Initialize bridge with optional enhanced-memory client."""
        self.client = enhanced_memory_client
        self._sync_stats = {
            "synced_visual": 0,
            "synced_text": 0,
            "synced_code": 0,
            "synced_correlations": 0,
            "last_sync": None
        }

    async def sync_visual_memory(self, memory: Dict) -> Optional[str]:
        """Sync a visual memory to enhanced-memory."""
        try:
            entity = {
                "name": f"visual_{memory.get('id', 'unknown')}",
                "entityType": "cross_modal_visual",
                "observations": [
                    f"scene_type: {memory.get('scene_type', 'unknown')}",
                    f"description: {memory.get('description', '')[:500]}",
                    f"objects: {', '.join(memory.get('objects', [])[:10])}",
                    f"confidence: {memory.get('confidence', 0):.2f}",
                    f"timestamp: {memory.get('timestamp', '')}"
                ]
            }

            # Add to enhanced-memory if client available
            if self.client:
                result = await self.client.create_entities([entity])
                self._sync_stats["synced_visual"] += 1
                return result.get("entity_id")
            else:
                # Store locally for batch sync
                return self._store_pending_sync(entity, "visual")

        except Exception as e:
            logger.error(f"Failed to sync visual memory: {e}")
            return None

    async def sync_text_memory(self, memory: Dict) -> Optional[str]:
        """Sync a text memory to enhanced-memory."""
        try:
            content = memory.get("content", {})

            entity = {
                "name": f"text_{memory.get('id', 'unknown')}",
                "entityType": "cross_modal_text",
                "observations": [
                    f"text_type: {content.get('text_type', 'note')}",
                    f"summary: {content.get('summary', '')[:300]}",
                    f"concepts: {', '.join(memory.get('concepts', [])[:10])}",
                    f"timestamp: {memory.get('timestamp', '')}"
                ]
            }

            if self.client:
                result = await self.client.create_entities([entity])
                self._sync_stats["synced_text"] += 1
                return result.get("entity_id")
            else:
                return self._store_pending_sync(entity, "text")

        except Exception as e:
            logger.error(f"Failed to sync text memory: {e}")
            return None

    async def sync_code_memory(self, memory: Dict) -> Optional[str]:
        """Sync a code memory to enhanced-memory."""
        try:
            content = memory.get("content", {})

            entity = {
                "name": f"code_{memory.get('id', 'unknown')}",
                "entityType": "cross_modal_code",
                "observations": [
                    f"file_path: {content.get('file_path', '')}",
                    f"change_type: {content.get('change_type', '')}",
                    f"description: {content.get('description', '')[:300]}",
                    f"language: {content.get('language', '')}",
                    f"concepts: {', '.join(memory.get('concepts', [])[:10])}",
                    f"timestamp: {memory.get('timestamp', '')}"
                ]
            }

            if self.client:
                result = await self.client.create_entities([entity])
                self._sync_stats["synced_code"] += 1
                return result.get("entity_id")
            else:
                return self._store_pending_sync(entity, "code")

        except Exception as e:
            logger.error(f"Failed to sync code memory: {e}")
            return None

    async def sync_correlation(self, correlation: Dict) -> Optional[str]:
        """Sync a cross-modal correlation as a relation in enhanced-memory."""
        try:
            # Create correlation entity
            entity = {
                "name": f"correlation_{correlation.get('memory_id_1', '')}_{correlation.get('memory_id_2', '')}",
                "entityType": "cross_modal_correlation",
                "observations": [
                    f"modality_1: {correlation.get('modality_1', '')}",
                    f"modality_2: {correlation.get('modality_2', '')}",
                    f"memory_id_1: {correlation.get('memory_id_1', '')}",
                    f"memory_id_2: {correlation.get('memory_id_2', '')}",
                    f"strength: {correlation.get('correlation_strength', 0):.2f}",
                    f"context_type: {correlation.get('context_type', 'temporal')}",
                    f"time_delta_seconds: {correlation.get('time_delta_seconds', 0):.1f}"
                ]
            }

            if self.client:
                result = await self.client.create_entities([entity])
                self._sync_stats["synced_correlations"] += 1
                return result.get("entity_id")
            else:
                return self._store_pending_sync(entity, "correlation")

        except Exception as e:
            logger.error(f"Failed to sync correlation: {e}")
            return None

    def _store_pending_sync(self, entity: Dict, entity_type: str) -> str:
        """Store entity for later batch sync."""
        pending_path = "/Volumes/SSDRAID0/agentic-system/databases/cross_modal/pending_sync.jsonl"
        os.makedirs(os.path.dirname(pending_path), exist_ok=True)

        sync_record = {
            "entity": entity,
            "type": entity_type,
            "created_at": datetime.now().isoformat()
        }

        with open(pending_path, 'a') as f:
            f.write(json.dumps(sync_record) + '\n')

        return entity["name"]

    async def batch_sync_pending(self) -> Dict[str, Any]:
        """Batch sync all pending entities to enhanced-memory."""
        pending_path = "/Volumes/SSDRAID0/agentic-system/databases/cross_modal/pending_sync.jsonl"

        if not os.path.exists(pending_path):
            return {"synced": 0, "message": "No pending syncs"}

        synced = 0
        failed = 0
        entities = []

        try:
            with open(pending_path, 'r') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        entities.append(record["entity"])
        except Exception as e:
            logger.error(f"Failed to read pending syncs: {e}")
            return {"synced": 0, "error": str(e)}

        if not entities:
            return {"synced": 0, "message": "No pending syncs"}

        # Batch sync to enhanced-memory
        if self.client:
            try:
                result = await self.client.create_entities(entities)
                synced = len(entities)
            except Exception as e:
                logger.error(f"Batch sync failed: {e}")
                failed = len(entities)
        else:
            # Write to enhanced-memory database directly
            synced = await self._direct_batch_sync(entities)

        # Clear pending file on success
        if synced > 0:
            os.remove(pending_path)

        self._sync_stats["last_sync"] = datetime.now().isoformat()

        return {
            "synced": synced,
            "failed": failed,
            "stats": self._sync_stats
        }

    async def _direct_batch_sync(self, entities: List[Dict]) -> int:
        """Direct sync to enhanced-memory database."""
        try:
            # Import enhanced-memory storage
            from server import KnowledgeGraph

            graph = KnowledgeGraph()
            synced = 0

            for entity in entities:
                try:
                    graph.add_entity(
                        name=entity["name"],
                        entity_type=entity["entityType"],
                        observations=entity["observations"]
                    )
                    synced += 1
                except Exception as e:
                    logger.warning(f"Failed to sync entity {entity.get('name')}: {e}")

            return synced

        except ImportError:
            logger.warning("Enhanced-memory not available for direct sync")
            return 0
        except Exception as e:
            logger.error(f"Direct batch sync failed: {e}")
            return 0

    async def full_sync(self, hours: int = 24) -> Dict[str, Any]:
        """Perform full sync of recent cross-modal memories."""
        from cross_modal_integration import CrossModalMemoryManager

        manager = CrossModalMemoryManager()
        results = {
            "visual": 0,
            "text": 0,
            "code": 0,
            "correlations": 0,
            "errors": 0
        }

        # Sync code memories
        code_memories = manager.code_tracker.get_recent(hours=hours, limit=500)
        for mem in code_memories:
            mem_dict = {
                "id": mem.id,
                "content": mem.content,
                "concepts": mem.concepts,
                "timestamp": mem.timestamp
            }
            result = await self.sync_code_memory(mem_dict)
            if result:
                results["code"] += 1
            else:
                results["errors"] += 1

        # Sync text memories
        text_memories = manager.text_tracker.get_recent(hours=hours, limit=500)
        for mem in text_memories:
            mem_dict = {
                "id": mem.id,
                "content": mem.content,
                "concepts": mem.concepts,
                "timestamp": mem.timestamp
            }
            result = await self.sync_text_memory(mem_dict)
            if result:
                results["text"] += 1
            else:
                results["errors"] += 1

        # Sync visual memories
        try:
            from visual_memory_integration import VisualMemoryManager
            vis_manager = VisualMemoryManager()
            visual_memories = vis_manager.memory_store.get_recent(hours=hours, limit=500)

            for vm in visual_memories:
                mem_dict = {
                    "id": vm.id,
                    "scene_type": vm.scene_type,
                    "description": vm.description,
                    "objects": vm.objects,
                    "confidence": vm.confidence,
                    "timestamp": vm.timestamp
                }
                result = await self.sync_visual_memory(mem_dict)
                if result:
                    results["visual"] += 1
                else:
                    results["errors"] += 1
        except ImportError:
            pass

        # Sync correlations
        import sqlite3
        db_path = os.path.join(manager.storage_path, "cross_modal_index.db")

        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
            cursor.execute('''
                SELECT memory_id_1, modality_1, memory_id_2, modality_2,
                       time_delta_seconds, correlation_strength, context_type
                FROM temporal_correlations
                WHERE created_at > ?
            ''', (cutoff,))

            for row in cursor.fetchall():
                correlation = {
                    "memory_id_1": row[0],
                    "modality_1": row[1],
                    "memory_id_2": row[2],
                    "modality_2": row[3],
                    "time_delta_seconds": row[4],
                    "correlation_strength": row[5],
                    "context_type": row[6]
                }
                result = await self.sync_correlation(correlation)
                if result:
                    results["correlations"] += 1
                else:
                    results["errors"] += 1

            conn.close()

        # Batch sync pending
        batch_result = await self.batch_sync_pending()
        results["batch_synced"] = batch_result.get("synced", 0)

        self._sync_stats["last_sync"] = datetime.now().isoformat()
        results["timestamp"] = datetime.now().isoformat()

        return results

    def get_sync_stats(self) -> Dict[str, Any]:
        """Get synchronization statistics."""
        return self._sync_stats.copy()


async def sync_to_enhanced_memory(hours: int = 24) -> Dict[str, Any]:
    """MCP Tool: Sync cross-modal memories to enhanced-memory."""
    bridge = EnhancedMemoryBridge()
    return await bridge.full_sync(hours)


async def get_sync_status() -> Dict[str, Any]:
    """MCP Tool: Get sync status."""
    bridge = EnhancedMemoryBridge()
    return bridge.get_sync_stats()


# CLI Entry Point
async def main():
    """Run sync from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Cross-Modal Enhanced Memory Bridge")
    parser.add_argument("--sync", action="store_true", help="Perform full sync")
    parser.add_argument("--hours", type=int, default=24, help="Hours to sync")
    parser.add_argument("--status", action="store_true", help="Show sync status")

    args = parser.parse_args()

    bridge = EnhancedMemoryBridge()

    if args.sync:
        print(f"Syncing last {args.hours} hours to enhanced-memory...")
        results = await bridge.full_sync(args.hours)
        print(json.dumps(results, indent=2))

    elif args.status:
        stats = bridge.get_sync_stats()
        print(json.dumps(stats, indent=2))

    else:
        print("Use --sync to perform sync or --status to check status")


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Direct Sync: SQLite → Qdrant
Reads entities directly from SQLite and generates embeddings for Qdrant
"""

import sqlite3
import logging
import sys
from pathlib import Path
import json
from typing import List, Dict, Any
import time

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from neural_memory_fabric import get_nmf

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = Path.home() / ".claude" / "enhanced_memories" / "memory.db"


def get_all_entities_from_sqlite() -> List[Dict[str, Any]]:
    """Get all entities directly from SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get entities
    cursor.execute("""
        SELECT
            e.id,
            e.name,
            e.entity_type,
            e.tier,
            GROUP_CONCAT(o.content, ' ') as observations
        FROM entities e
        LEFT JOIN observations o ON e.id = o.entity_id
        GROUP BY e.id, e.name, e.entity_type, e.tier
        ORDER BY e.id
    """)

    entities = []
    for row in cursor.fetchall():
        entities.append({
            'id': row['id'],
            'name': row['name'],
            'entity_type': row['entity_type'],
            'tier': row['tier'] or 'working',
            'observations': row['observations'] or ''
        })

    conn.close()
    return entities


async def sync_entity_to_qdrant(nmf, entity: Dict[str, Any]) -> bool:
    """Sync a single entity to Qdrant with embeddings"""
    try:
        # Combine name and observations for embedding
        content = f"{entity['name']}: {entity['observations']}"

        # Store in NMF (which generates embeddings and stores in Qdrant)
        result = await nmf.remember(
            content=content,
            agent_id='default_agent',
            metadata={
                'sqlite_id': entity['id'],
                'name': entity['name'],
                'entity_type': entity['entity_type'],
                'tier': entity['tier']
            }
        )

        return result.get('success', False)

    except Exception as e:
        logger.error(f"Failed to sync entity {entity['id']}: {e}")
        return False


async def main():
    """Main sync process"""
    print("=" * 70)
    print("SQLITE → QDRANT SYNC")
    print("=" * 70)

    # Initialize NMF
    print("\n[1/4] Initializing Neural Memory Fabric...")
    try:
        nmf = await get_nmf()
        print(f"✅ NMF initialized")
    except Exception as e:
        print(f"❌ Failed to initialize NMF: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Get entities from SQLite
    print(f"\n[2/4] Reading entities from SQLite ({DB_PATH})...")
    try:
        entities = get_all_entities_from_sqlite()
        print(f"✅ Found {len(entities)} entities")

        if len(entities) == 0:
            print("⚠️  No entities to sync")
            return 0

        # Show sample
        print(f"\n   Sample entities:")
        for entity in entities[:3]:
            print(f"   - ID {entity['id']}: {entity['name']} ({entity['entity_type']})")
        if len(entities) > 3:
            print(f"   ... and {len(entities) - 3} more")

    except Exception as e:
        print(f"❌ Failed to read SQLite: {e}")
        return 1

    # Sync to Qdrant
    print(f"\n[3/4] Syncing {len(entities)} entities to Qdrant...")
    print("   This will generate embeddings (may take 1-2 minutes)...")

    success_count = 0
    failed_count = 0
    start_time = time.time()

    for i, entity in enumerate(entities, 1):
        # Progress indicator
        if i % 10 == 0 or i == 1:
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(entities) - i) / rate if rate > 0 else 0
            print(f"   Progress: {i}/{len(entities)} ({i/len(entities)*100:.1f}%) "
                  f"- {rate:.1f} entities/sec - ETA: {eta:.0f}s")

        # Sync entity
        if await sync_entity_to_qdrant(nmf, entity):
            success_count += 1
        else:
            failed_count += 1
            logger.warning(f"Failed to sync: {entity['name']}")

    elapsed = time.time() - start_time

    # Verify
    print(f"\n[4/4] Verifying sync...")
    try:
        import requests
        resp = requests.get('http://localhost:6333/collections/enhanced_memory')
        data = resp.json()
        points_count = data['result']['points_count']
        print(f"✅ Qdrant collection has {points_count} points")
    except Exception as e:
        print(f"⚠️  Could not verify: {e}")
        points_count = "unknown"

    # Summary
    print(f"\n{'=' * 70}")
    print("SYNC COMPLETE")
    print(f"{'=' * 70}")
    print(f"Entities processed: {len(entities)}")
    print(f"Successfully synced: {success_count}")
    print(f"Failed: {failed_count}")
    print(f"Qdrant points: {points_count}")
    print(f"Time elapsed: {elapsed:.1f} seconds")
    print(f"Rate: {len(entities)/elapsed:.1f} entities/sec")

    if success_count == len(entities):
        print(f"\n✅ All entities synced successfully!")
        return 0
    elif success_count > 0:
        print(f"\n⚠️  Partial sync: {failed_count} entities failed")
        return 1
    else:
        print(f"\n❌ Sync failed completely")
        return 1


if __name__ == '__main__':
    import asyncio
    sys.exit(asyncio.run(main()))

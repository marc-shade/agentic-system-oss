#!/usr/bin/env python3
"""
Fast Batch Sync: SQLite → Qdrant
Parallel embedding generation with direct Qdrant API
"""

import sqlite3
import logging
import sys
import asyncio
import aiohttp
from pathlib import Path
from typing import List, Dict, Any
import time
import uuid

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Reduced logging for speed
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = Path.home() / ".claude" / "enhanced_memories" / "memory.db"
# Cloud-first Ollama for embeddings (prefer GPU nodes)
# Set OLLAMA_HOST to your inference node (e.g., http://your-node:11434)
import os
OLLAMA_URL = os.environ.get('OLLAMA_HOST', 'http://localhost:11434') + "/api/embeddings"
# Qdrant configuration - use environment variable with fallback
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = os.environ.get("QDRANT_PORT", "6333")
QDRANT_BASE_URL = f"http://{QDRANT_HOST}:{QDRANT_PORT}"
QDRANT_URL = f"{QDRANT_BASE_URL}/collections/enhanced_memory/points"
BATCH_SIZE = 20  # Process 20 embeddings in parallel
MODEL = "nomic-embed-text"


def get_all_entities_from_sqlite() -> List[Dict[str, Any]]:
    """Get all entities directly from SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

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


async def generate_embedding(session: aiohttp.ClientSession, text: str) -> List[float]:
    """Generate embedding for text using Ollama"""
    try:
        async with session.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": text},
            timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get('embedding', [])
            else:
                logger.error(f"Ollama returned {resp.status}")
                return None
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return None


async def store_point_in_qdrant(
    session: aiohttp.ClientSession,
    entity_id: int,
    entity: Dict[str, Any],
    embedding: List[float]
) -> bool:
    """Store a single point in Qdrant"""
    try:
        point_id = str(uuid.uuid4())
        point = {
            "points": [{
                "id": point_id,
                "vector": embedding,
                "payload": {
                    "sqlite_id": entity_id,
                    "name": entity['name'],
                    "entity_type": entity['entity_type'],
                    "tier": entity['tier'],
                    "content": f"{entity['name']}: {entity['observations']}"
                }
            }]
        }

        async with session.put(
            f"{QDRANT_URL}?wait=true",
            json=point,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            return resp.status == 200
    except Exception as e:
        logger.error(f"Qdrant storage failed: {e}")
        return False


async def process_entity(
    session: aiohttp.ClientSession,
    entity: Dict[str, Any]
) -> bool:
    """Process a single entity: generate embedding + store in Qdrant"""
    try:
        # Generate content
        content = f"{entity['name']}: {entity['observations']}"

        # Generate embedding
        embedding = await generate_embedding(session, content)
        if not embedding:
            return False

        # Store in Qdrant
        success = await store_point_in_qdrant(session, entity['id'], entity, embedding)
        return success

    except Exception as e:
        logger.error(f"Failed to process entity {entity['name']}: {e}")
        return False


async def process_batch(
    session: aiohttp.ClientSession,
    entities: List[Dict[str, Any]]
) -> tuple:
    """Process a batch of entities in parallel"""
    tasks = [process_entity(session, entity) for entity in entities]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    success_count = sum(1 for r in results if r is True)
    failed_count = len(results) - success_count

    return success_count, failed_count


async def main():
    """Main sync process"""
    print("=" * 70)
    print("FAST BATCH SYNC: SQLITE → QDRANT")
    print("=" * 70)

    # Get entities
    print(f"\n[1/3] Reading entities from SQLite ({DB_PATH})...")
    entities = get_all_entities_from_sqlite()
    print(f"✅ Found {len(entities)} entities")

    if len(entities) == 0:
        print("⚠️  No entities to sync")
        return 0

    # Check current Qdrant count
    print(f"\n[2/3] Checking Qdrant status...")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{QDRANT_BASE_URL}/collections/enhanced_memory") as resp:
            data = await resp.json()
            initial_count = data['result']['points_count']
            print(f"✅ Qdrant has {initial_count} points currently")

        # Sync in batches
        print(f"\n[3/3] Syncing {len(entities)} entities (batch size: {BATCH_SIZE})...")
        print(f"   Embedding model: {MODEL}")
        print(f"   Parallel processing: {BATCH_SIZE} entities/batch\n")

        total_success = 0
        total_failed = 0
        start_time = time.time()

        for i in range(0, len(entities), BATCH_SIZE):
            batch = entities[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            total_batches = (len(entities) + BATCH_SIZE - 1) // BATCH_SIZE

            success, failed = await process_batch(session, batch)
            total_success += success
            total_failed += failed

            elapsed = time.time() - start_time
            rate = (i + len(batch)) / elapsed if elapsed > 0 else 0
            remaining = len(entities) - (i + len(batch))
            eta = remaining / rate if rate > 0 else 0

            print(f"   Batch {batch_num}/{total_batches}: {success}/{len(batch)} succeeded | "
                  f"Total: {total_success}/{i + len(batch)} | "
                  f"Rate: {rate:.1f}/s | ETA: {eta:.0f}s")

        elapsed = time.time() - start_time

        # Verify final count
        async with session.get(f"{QDRANT_BASE_URL}/collections/enhanced_memory") as resp:
            data = await resp.json()
            final_count = data['result']['points_count']

    # Summary
    print(f"\n{'=' * 70}")
    print("SYNC COMPLETE")
    print(f"{'=' * 70}")
    print(f"Entities processed: {len(entities)}")
    print(f"Successfully synced: {total_success}")
    print(f"Failed: {total_failed}")
    print(f"Qdrant points: {initial_count} → {final_count} (+{final_count - initial_count})")
    print(f"Time elapsed: {elapsed:.1f} seconds")
    print(f"Rate: {len(entities)/elapsed:.1f} entities/sec")

    if total_success == len(entities):
        print(f"\n✅ All entities synced successfully!")
        return 0
    elif total_success > 0:
        print(f"\n⚠️  Partial sync: {total_failed} entities failed")
        return 1
    else:
        print(f"\n❌ Sync failed completely")
        return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))

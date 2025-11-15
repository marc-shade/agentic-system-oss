#!/usr/bin/env python3
"""
Direct SQLite to Qdrant Migration
Bypasses memory-db service to migrate all 1,320 entities with vector embeddings
"""

import asyncio
import logging
import sqlite3
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from neural_memory_fabric import get_nmf

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database path from get_memory_status
DB_PATH = "/Users/marc/.claude/enhanced_memories/memory.db"


async def main():
    """Main migration function"""
    print("=" * 70)
    print("DIRECT SQLite → Qdrant MIGRATION")
    print("=" * 70)

    # Initialize NMF
    print("\n1. Initializing Neural Memory Fabric...")
    nmf = await get_nmf()
    print("✅ NMF initialized")

    # Connect to SQLite directly
    print("\n2. Connecting to SQLite database...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Count entities
    cursor.execute("SELECT COUNT(*) as count FROM entities")
    total = cursor.fetchone()['count']
    print(f"✅ Found {total} entities to migrate")

    if total == 0:
        print("❌ No entities found. Exiting.")
        return

    # Fetch all entities
    print("\n3. Fetching entities...")
    cursor.execute("""
        SELECT id, name, entity_type, compressed_data, tier
        FROM entities
        ORDER BY id
    """)

    entities = cursor.fetchall()
    print(f"✅ Loaded {len(entities)} entities")

    # Migrate entities
    print("\n4. Migrating entities to Qdrant with embeddings...")
    print(f"   This will take ~{len(entities) * 0.1:.0f} seconds")

    successful = 0
    failed = 0

    for i, entity in enumerate(entities, 1):
        try:
            # Decompress and unpickle data
            import zlib
            import pickle

            compressed_bytes = entity['compressed_data']

            # Skip if NULL
            if compressed_bytes is None:
                failed += 1
                logger.warning(f"Entity {entity['id']} ({entity['name']}) has NULL compressed_data")
                continue

            # Decompress and unpickle
            decompressed_bytes = zlib.decompress(compressed_bytes)
            entity_data = pickle.loads(decompressed_bytes)

            # Extract observations
            observations = entity_data.get('observations', [])

            # Create content for embedding
            content = f"Name: {entity['name']}\nType: {entity['entity_type']}\n"
            content += "\n".join(f"- {obs}" for obs in observations[:5])  # First 5 observations

            # Store in NMF (generates embeddings automatically)
            await nmf.remember(
                content=content,
                agent_id="migration",
                metadata={
                    "original_id": entity['id'],
                    "name": entity['name'],
                    "type": entity['entity_type'],
                    "tier": entity['tier'],
                    "tags": [entity['entity_type'], entity['tier']],  # Include tags in metadata
                    "source": "sqlite_migration"
                }
            )

            successful += 1

            # Progress update every 50 entities
            if i % 50 == 0:
                print(f"   Progress: {i}/{len(entities)} ({i/len(entities)*100:.1f}%) - {successful} successful")

        except Exception as e:
            failed += 1
            logger.error(f"Failed to migrate entity {entity['id']} ({entity['name']}): {e}")

    # Final report
    print("\n" + "=" * 70)
    print("MIGRATION COMPLETE")
    print("=" * 70)
    print(f"Total entities: {total}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"Success rate: {successful/total*100:.1f}%")

    conn.close()


if __name__ == "__main__":
    asyncio.run(main())

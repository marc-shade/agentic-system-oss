#!/usr/bin/env python3
"""
Direct Migration Script: SQLite → Qdrant with Embeddings
Direct database access for faster migration
"""

import asyncio
import logging
import sqlite3
import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from neural_memory_fabric import get_nmf

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fetch_all_entities_direct(db_path: str) -> List[Dict[str, Any]]:
    """Fetch all entities directly from SQLite database"""
    import zlib
    import pickle

    logger.info(f"Fetching entities from {db_path}...")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Fetch all entities with compressed data
    cursor.execute("""
        SELECT
            id,
            name,
            entity_type,
            tier,
            compressed_data,
            current_version,
            created_at
        FROM entities
    """)

    entities = []
    for row in cursor.fetchall():
        # Decompress data to get observations (pickle format, not JSON)
        observations = []
        if row['compressed_data']:
            try:
                decompressed = zlib.decompress(row['compressed_data'])
                data = pickle.loads(decompressed)  # Use pickle, not JSON
                observations = data.get('observations', [])
            except Exception as e:
                logger.warning(f"Could not decompress entity {row['name']}: {e}")

        entity = {
            'id': row['id'],
            'name': row['name'],
            'entityType': row['entity_type'],
            'tier': row['tier'],
            'version': row['current_version'],
            'created_at': row['created_at'],
            'observations': observations
        }
        entities.append(entity)

    conn.close()

    logger.info(f"Fetched {len(entities)} entities")
    return entities


def entity_to_content(entity: Dict[str, Any]) -> str:
    """Convert entity to content string for embedding"""
    parts = []

    if 'name' in entity:
        parts.append(f"Name: {entity['name']}")

    if 'entityType' in entity:
        parts.append(f"Type: {entity['entityType']}")

    if 'observations' in entity and entity['observations']:
        observations = entity['observations']
        if isinstance(observations, list):
            parts.append(f"Observations: {' '.join(observations)}")
        else:
            parts.append(f"Observations: {observations}")

    content = " | ".join(parts)

    # Minimum content check
    if len(content.strip()) < 10:
        return None

    return content


async def migrate_batch(nmf, entities: List[Dict[str, Any]], batch_num: int, total_batches: int):
    """Migrate a batch of entities"""
    successful = 0
    failed = 0
    providers_used = {}

    logger.info(f"Processing batch {batch_num}/{total_batches} ({len(entities)} entities)...")

    for entity in entities:
        try:
            content = entity_to_content(entity)
            if not content:
                failed += 1
                continue

            # Prepare metadata
            metadata = {
                "source": "memory-db",
                "entity_name": entity.get('name', 'unknown'),
                "entity_type": entity.get('entityType', 'unknown'),
                "entity_id": entity.get('id'),
                "version": entity.get('version', 1),
                "migrated_at": time.time()
            }

            # Extract tags and put them in metadata (remember() doesn't accept tags parameter)
            tags = []
            if 'entityType' in entity:
                tags.append(entity['entityType'])
            if 'name' in entity:
                name_parts = entity['name'].split('_')
                if name_parts:
                    tags.append(name_parts[0])

            # Add tags to metadata
            metadata['tags'] = tags

            # Store in NMF with embedding (tags go in metadata, not separate parameter)
            result = await nmf.remember(
                content=content,
                metadata=metadata,
                agent_id="migration"
            )

            if result.get('success'):
                successful += 1
                provider = result.get('embedding_provider', 'unknown')
                providers_used[provider] = providers_used.get(provider, 0) + 1
            else:
                failed += 1
                error = result.get('error', 'Unknown error')
                logger.warning(f"Failed to migrate '{entity.get('name')}': {error}")

        except Exception as e:
            failed += 1
            logger.error(f"Error migrating '{entity.get('name')}': {e}")

    logger.info(f"Batch {batch_num} complete: {successful}/{len(entities)} successful, {failed} failed")
    logger.info(f"Providers used: {providers_used}")

    return successful, failed, providers_used


async def main():
    """Main migration process"""
    import argparse

    parser = argparse.ArgumentParser(description='Migrate memory-db entities to Qdrant (direct access)')
    parser.add_argument('--batch-size', type=int, default=20, help='Batch size for migration')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of entities to migrate')
    parser.add_argument('--db-path', type=str, default=str(Path.home() / '.claude/enhanced_memories/memory.db'),
                        help='Path to memory database')
    args = parser.parse_args()

    print("=" * 70)
    print("DIRECT MIGRATION: MEMORY-DB → QDRANT WITH EMBEDDINGS")
    print("=" * 70)
    print()

    start_time = time.time()

    try:
        # Initialize NMF
        print("Initializing Neural Memory Fabric...")
        nmf = await get_nmf()
        print(f"✅ NMF initialized")

        if nmf.embedding_manager:
            providers = nmf.embedding_manager.get_available_providers()
            print(f"✅ {len(providers)} embedding providers available: {', '.join(providers)}")
        else:
            print("❌ No embedding manager available")
            return

        # Fetch all entities directly
        entities = fetch_all_entities_direct(args.db_path)

        if not entities:
            print("❌ No entities found in database")
            return

        # Apply limit if specified
        if args.limit:
            entities = entities[:args.limit]
            print(f"⚠️  Limited to first {args.limit} entities")

        print(f"📊 Migrating {len(entities)} entities")
        print()

        # Process in batches
        batch_size = args.batch_size
        total_successful = 0
        total_failed = 0
        all_providers = {}
        total_batches = (len(entities) + batch_size - 1) // batch_size

        for i in range(0, len(entities), batch_size):
            batch = entities[i:i + batch_size]
            batch_num = i // batch_size + 1

            successful, failed, providers = await migrate_batch(nmf, batch, batch_num, total_batches)
            total_successful += successful
            total_failed += failed

            # Merge provider counts
            for provider, count in providers.items():
                all_providers[provider] = all_providers.get(provider, 0) + count

            # Progress report every 10 batches
            if batch_num % 10 == 0:
                elapsed = time.time() - start_time
                rate = (total_successful + total_failed) / elapsed if elapsed > 0 else 0
                print()
                print(f"Progress: {total_successful + total_failed}/{len(entities)} processed")
                print(f"Success: {total_successful}, Failed: {total_failed}")
                print(f"Rate: {rate:.2f} entities/sec")
                print(f"Providers: {all_providers}")
                print()

        # Final report
        elapsed = time.time() - start_time
        rate = (total_successful + total_failed) / elapsed if elapsed > 0 else 0

        print()
        print("=" * 70)
        print("MIGRATION COMPLETE")
        print("=" * 70)
        print(f"Total Entities: {len(entities)}")
        print(f"Successful: {total_successful} ({total_successful/len(entities)*100:.1f}%)")
        print(f"Failed: {total_failed} ({total_failed/len(entities)*100:.1f}%)")
        print(f"Elapsed Time: {elapsed:.2f}s")
        print(f"Processing Rate: {rate:.2f} entities/sec")
        print()
        print("Embeddings by Provider:")
        for provider, count in sorted(all_providers.items()):
            print(f"  {provider}: {count} ({count/total_successful*100:.1f}%)")
        print("=" * 70)

        # Save results
        results_path = Path.home() / '.claude' / 'direct_migration_results.json'
        results = {
            'timestamp': time.time(),
            'total_entities': len(entities),
            'successful': total_successful,
            'failed': total_failed,
            'elapsed_time': elapsed,
            'rate': rate,
            'providers': all_providers
        }

        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n📄 Results saved to: {results_path}")

    except KeyboardInterrupt:
        print("\n⚠️  Migration interrupted by user")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        logger.exception("Migration error")


if __name__ == "__main__":
    asyncio.run(main())

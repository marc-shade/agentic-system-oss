#!/usr/bin/env python3
"""
Migration Script: Memory-DB → Qdrant with Embeddings
Migrates all 1,200+ entities from memory-db to Neural Memory Fabric with vector embeddings
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from neural_memory_fabric import get_nmf
from memory_client import MemoryClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationStats:
    """Track migration statistics"""
    def __init__(self):
        self.total_entities = 0
        self.processed = 0
        self.successful = 0
        self.failed = 0
        self.skipped = 0
        self.start_time = time.time()
        self.embeddings_by_provider = {}
        self.errors = []

    def add_success(self, provider: str):
        self.successful += 1
        self.processed += 1
        self.embeddings_by_provider[provider] = self.embeddings_by_provider.get(provider, 0) + 1

    def add_failure(self, error: str):
        self.failed += 1
        self.processed += 1
        self.errors.append(error)

    def add_skip(self, reason: str):
        self.skipped += 1
        self.processed += 1

    def elapsed_time(self) -> float:
        return time.time() - self.start_time

    def report(self) -> str:
        elapsed = self.elapsed_time()
        rate = self.processed / elapsed if elapsed > 0 else 0

        report = [
            "=" * 70,
            "MIGRATION STATISTICS",
            "=" * 70,
            f"Total Entities: {self.total_entities}",
            f"Processed: {self.processed}/{self.total_entities} ({self.processed/self.total_entities*100:.1f}%)",
            f"Successful: {self.successful}",
            f"Failed: {self.failed}",
            f"Skipped: {self.skipped}",
            f"Elapsed Time: {elapsed:.2f}s",
            f"Processing Rate: {rate:.2f} entities/sec",
            "",
            "Embeddings by Provider:",
        ]

        for provider, count in sorted(self.embeddings_by_provider.items()):
            report.append(f"  {provider}: {count} ({count/self.successful*100:.1f}%)")

        if self.errors:
            report.append("")
            report.append(f"Recent Errors ({min(5, len(self.errors))}):")
            for error in self.errors[-5:]:
                report.append(f"  - {error}")

        report.append("=" * 70)
        return "\n".join(report)


async def fetch_all_entities(client: MemoryClient) -> List[Dict[str, Any]]:
    """Fetch all entities from memory-db"""
    logger.info("Fetching entities from memory-db...")

    # Memory-db search_nodes doesn't support offset/pagination
    # Fetch all entities with a large limit (we have ~1,200 entities)
    result = await client.search_nodes("", limit=5000)

    if not result or 'results' not in result:
        logger.warning("No results from memory-db")
        return []

    entities = result['results']
    logger.info(f"Total entities fetched: {len(entities)}")
    return entities


def entity_to_content(entity: Dict[str, Any]) -> str:
    """Convert entity to content string for embedding"""
    # Combine entity name, type, and observations
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


async def migrate_entity(
    nmf,
    entity: Dict[str, Any],
    stats: MigrationStats,
    dry_run: bool = False
) -> bool:
    """Migrate a single entity to NMF with embeddings"""
    try:
        # Extract content
        content = entity_to_content(entity)
        if not content:
            stats.add_skip("No meaningful content")
            return False

        # Prepare metadata
        metadata = {
            "source": "memory-db",
            "entity_name": entity.get('name', 'unknown'),
            "entity_type": entity.get('entityType', 'unknown'),
            "version": entity.get('version', 1),
            "migrated_at": time.time()
        }

        # Extract tags if available
        tags = []
        if 'entityType' in entity:
            tags.append(entity['entityType'])
        if 'name' in entity:
            # Add first word of name as tag
            name_parts = entity['name'].split('_')
            if name_parts:
                tags.append(name_parts[0])

        if dry_run:
            logger.info(f"DRY RUN: Would migrate '{entity.get('name', 'unknown')}'")
            stats.add_success("dry-run")
            return True

        # Store in NMF with embedding
        result = await nmf.remember(
            content=content,
            metadata=metadata,
            tags=tags,
            agent_id="migration"
        )

        if result.get('success'):
            # Track which provider was used
            provider = result.get('embedding_provider', 'unknown')
            stats.add_success(provider)
            return True
        else:
            error = result.get('error', 'Unknown error')
            stats.add_failure(f"{entity.get('name', 'unknown')}: {error}")
            return False

    except Exception as e:
        stats.add_failure(f"{entity.get('name', 'unknown')}: {str(e)}")
        logger.error(f"Failed to migrate entity: {e}")
        return False


async def migrate_batch(
    nmf,
    entities: List[Dict[str, Any]],
    stats: MigrationStats,
    batch_num: int,
    total_batches: int,
    dry_run: bool = False
) -> None:
    """Migrate a batch of entities"""
    logger.info(f"Processing batch {batch_num}/{total_batches} ({len(entities)} entities)...")

    # Process entities in batch
    tasks = [migrate_entity(nmf, entity, stats, dry_run) for entity in entities]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Log progress
    success_count = sum(1 for r in results if r is True)
    logger.info(f"Batch {batch_num} complete: {success_count}/{len(entities)} successful")


async def main():
    """Main migration process"""
    import argparse

    parser = argparse.ArgumentParser(description='Migrate memory-db entities to Qdrant')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for migration')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of entities to migrate')
    parser.add_argument('--dry-run', action='store_true', help='Dry run without actual migration')
    parser.add_argument('--provider', type=str, default=None, help='Force specific embedding provider')
    args = parser.parse_args()

    print("=" * 70)
    print("MEMORY-DB TO QDRANT MIGRATION")
    print("=" * 70)

    if args.dry_run:
        print("⚠️  DRY RUN MODE - No actual changes will be made")
        print()

    stats = MigrationStats()

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

        # Initialize memory-db client
        print("Connecting to memory-db...")
        client = MemoryClient()
        print("✅ Connected to memory-db")

        # Fetch all entities
        entities = await fetch_all_entities(client)

        if not entities:
            print("❌ No entities found in memory-db")
            return

        stats.total_entities = len(entities)

        # Apply limit if specified
        if args.limit:
            entities = entities[:args.limit]
            stats.total_entities = len(entities)
            print(f"⚠️  Limited to first {args.limit} entities")

        print(f"📊 Found {stats.total_entities} entities to migrate")
        print()

        # Process in batches
        batch_size = args.batch_size
        total_batches = (len(entities) + batch_size - 1) // batch_size

        for i in range(0, len(entities), batch_size):
            batch = entities[i:i + batch_size]
            batch_num = i // batch_size + 1

            await migrate_batch(nmf, batch, stats, batch_num, total_batches, args.dry_run)

            # Print progress every 10 batches
            if batch_num % 10 == 0 or batch_num == total_batches:
                print()
                print(stats.report())
                print()

        # Final report
        print()
        print(stats.report())

        # Save detailed results
        results_path = Path.home() / '.claude' / 'migration_results.json'
        results = {
            'total_entities': stats.total_entities,
            'successful': stats.successful,
            'failed': stats.failed,
            'skipped': stats.skipped,
            'elapsed_time': stats.elapsed_time(),
            'rate': stats.processed / stats.elapsed_time() if stats.elapsed_time() > 0 else 0,
            'embeddings_by_provider': stats.embeddings_by_provider,
            'errors': stats.errors,
            'dry_run': args.dry_run
        }

        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"📄 Detailed results saved to: {results_path}")

    except KeyboardInterrupt:
        print("\n⚠️  Migration interrupted by user")
        print()
        print(stats.report())

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        logger.exception("Migration error")


if __name__ == "__main__":
    asyncio.run(main())

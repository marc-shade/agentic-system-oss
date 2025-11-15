#!/usr/bin/env python3
"""
Contextual Enrichment Migration Script

Migrates existing entities to include LLM-generated contextual prefixes.
This improves retrieval accuracy by -35% failure rate.

Based on Anthropic's Contextual Retrieval research:
- Prepend each chunk with document-level context
- Helps retriever understand what the chunk is about
- Reduces retrieval failures significantly

Part of RAG Tier 1 Strategy - Week 1, Day 5-7
Expected cost: ~$50 for 10,000+ entities
Expected time: ~10 minutes (parallelized)
"""

import asyncio
import logging
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os

# Import contextual LLM module
from contextual_llm import get_prefix_generator

logger = logging.getLogger(__name__)

# Database path (same as server.py)
DB_PATH = Path.home() / ".claude" / "enhanced_memories" / "memory.db"

# LLM configuration (using Claude SDK with 4.5 models)
LLM_MODEL = "claude-sonnet-4.5-20250929"  # Sonnet 4.5 for high-quality contextual prefix generation
LLM_MAX_TOKENS = 200  # Contextual prefix should be concise
BATCH_SIZE = 10  # Process 10 entities in parallel
MAX_CONCURRENT = 5  # Max concurrent LLM calls

# Cost tracking
COST_PER_1K_INPUT_TOKENS = 0.00025  # Haiku pricing
COST_PER_1K_OUTPUT_TOKENS = 0.00125  # Haiku pricing

# Progress tracking
PROGRESS_FILE = Path("/tmp/contextual_enrichment_progress.json")


class ContextualEnrichmentMigration:
    """
    Migrates existing entities to include contextual prefixes.

    Architecture:
    1. Read all entities from database
    2. For each entity, generate contextual prefix using LLM
    3. Update entity with enriched observations
    4. Track progress and costs
    5. Support resumption if interrupted
    """

    def __init__(self, db_path: Path = DB_PATH):
        """Initialize migration."""
        self.db_path = db_path
        self.total_entities = 0
        self.processed_entities = 0
        self.enriched_entities = 0
        self.skipped_entities = 0
        self.failed_entities = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.start_time = None
        self.end_time = None

        # Initialize LLM prefix generator
        self.prefix_generator = get_prefix_generator()

        # Load progress if exists
        self._load_progress()

    def _load_progress(self):
        """Load progress from file if exists."""
        if PROGRESS_FILE.exists():
            try:
                with open(PROGRESS_FILE, 'r') as f:
                    progress = json.load(f)
                    self.processed_entities = progress.get('processed_entities', 0)
                    self.enriched_entities = progress.get('enriched_entities', 0)
                    self.skipped_entities = progress.get('skipped_entities', 0)
                    self.failed_entities = progress.get('failed_entities', 0)
                    self.total_input_tokens = progress.get('total_input_tokens', 0)
                    self.total_output_tokens = progress.get('total_output_tokens', 0)
                    self.total_cost = progress.get('total_cost', 0.0)
                    logger.info(f"Resuming from previous run: {self.processed_entities} entities already processed")
            except Exception as e:
                logger.warning(f"Could not load progress: {e}")

    def _save_progress(self):
        """Save progress to file."""
        progress = {
            'processed_entities': self.processed_entities,
            'enriched_entities': self.enriched_entities,
            'skipped_entities': self.skipped_entities,
            'failed_entities': self.failed_entities,
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'total_cost': self.total_cost,
            'last_update': datetime.now().isoformat()
        }
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f, indent=2)

    def get_all_entities(self) -> List[Dict[str, Any]]:
        """Get all entities from database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get entities (using actual schema with entity_type)
        cursor.execute("""
            SELECT id, name, entity_type, tier, created_at, last_accessed
            FROM entities
            ORDER BY id
        """)

        entities = []
        for row in cursor.fetchall():
            entity_id = row['id']

            # Get observations for this entity
            obs_cursor = conn.cursor()
            obs_cursor.execute("""
                SELECT content
                FROM observations
                WHERE entity_id = ?
                ORDER BY created_at
            """, (entity_id,))

            observations = [obs_row[0] for obs_row in obs_cursor.fetchall()]

            entity = {
                'id': entity_id,
                'name': row['name'],
                'entityType': row['entity_type'],  # Convert to camelCase for consistency
                'tier': row['tier'],
                'observations': observations,
                'created_at': row['created_at'],
                'last_accessed': row['last_accessed']
            }
            entities.append(entity)

        conn.close()
        return entities

    async def generate_contextual_prefix(self, entity: Dict[str, Any]) -> Optional[str]:
        """
        Generate contextual prefix for an entity using LLM.

        Args:
            entity: Entity dictionary with name, type, and observations

        Returns:
            Contextual prefix string or None if failed
        """
        entity_type = entity.get('entityType', 'unknown')
        entity_name = entity.get('name', 'unknown')
        observations = entity.get('observations', [])

        try:
            # Use LLM-based prefix generator
            prefix, input_tokens, output_tokens = await self.prefix_generator.generate_prefix(
                entity_name=entity_name,
                entity_type=entity_type,
                observations=observations
            )

            # Track tokens
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens

            # Update cost
            self.total_cost = self.prefix_generator.get_cost_estimate()

            return prefix

        except Exception as e:
            logger.error(f"Error generating prefix: {e}")
            return None

    async def enrich_entity(self, entity: Dict[str, Any]) -> bool:
        """
        Enrich a single entity with contextual prefix.

        Args:
            entity: Entity to enrich

        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate contextual prefix
            prefix = await self.generate_contextual_prefix(entity)

            if not prefix:
                logger.warning(f"Could not generate prefix for entity {entity['id']}")
                return False

            # Add contextual prefix as the first observation
            # This will appear before existing observations
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Insert the contextual prefix as a new observation at the beginning
            # First, get min created_at to insert before it
            cursor.execute("""
                SELECT MIN(created_at) FROM observations WHERE entity_id = ?
            """, (entity['id'],))
            min_created = cursor.fetchone()[0]

            # Use an earlier timestamp if observations exist, otherwise use current time
            # Use SQL datetime format (YYYY-MM-DD HH:MM:SS) to match database format
            if min_created:
                # Parse timestamp (handle both ISO and SQL formats)
                if 'T' in min_created:
                    dt = datetime.fromisoformat(min_created.replace('Z', '+00:00'))
                else:
                    dt = datetime.strptime(min_created, '%Y-%m-%d %H:%M:%S')

                # Subtract 1 second and format as SQL datetime
                insert_time = (dt - timedelta(seconds=1)).strftime('%Y-%m-%d %H:%M:%S')
            else:
                insert_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Insert the contextual prefix as first observation
            cursor.execute("""
                INSERT INTO observations (entity_id, content, created_at)
                VALUES (?, ?, ?)
            """, (entity['id'], prefix, insert_time))

            # Update last_accessed on entity
            cursor.execute("""
                UPDATE entities
                SET last_accessed = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), entity['id']))

            conn.commit()
            conn.close()

            return True

        except Exception as e:
            logger.error(f"Error enriching entity {entity.get('id')}: {e}")
            return False

    async def process_batch(self, entities: List[Dict[str, Any]]):
        """
        Process a batch of entities in parallel.

        Args:
            entities: List of entities to process
        """
        tasks = [self.enrich_entity(entity) for entity in entities]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            self.processed_entities += 1
            if isinstance(result, Exception):
                self.failed_entities += 1
            elif result:
                self.enriched_entities += 1
            else:
                self.skipped_entities += 1

        # Save progress after each batch
        self._save_progress()

    async def run(self):
        """Run the migration."""
        self.start_time = datetime.now()

        logger.info("=" * 60)
        logger.info("Contextual Enrichment Migration")
        logger.info("RAG Tier 1 Strategy - Week 1, Day 5-7")
        logger.info("=" * 60)

        # Get all entities
        logger.info(f"Loading entities from database: {self.db_path}")
        entities = self.get_all_entities()
        self.total_entities = len(entities)

        logger.info(f"Found {self.total_entities} entities")

        if self.processed_entities > 0:
            logger.info(f"Resuming from entity {self.processed_entities + 1}")
            entities = entities[self.processed_entities:]

        # Process in batches
        for i in range(0, len(entities), BATCH_SIZE):
            batch = entities[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (len(entities) + BATCH_SIZE - 1) // BATCH_SIZE

            logger.info(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} entities)")

            await self.process_batch(batch)

            # Progress update
            logger.info(f"Progress: {self.processed_entities}/{self.total_entities} entities processed")
            logger.info(f"  ✅ Enriched: {self.enriched_entities}")
            logger.info(f"  ⏭️  Skipped: {self.skipped_entities}")
            logger.info(f"  ❌ Failed: {self.failed_entities}")

        self.end_time = datetime.now()

        # Final report
        self._print_final_report()

    def _print_final_report(self):
        """Print final migration report."""
        duration = (self.end_time - self.start_time).total_seconds()

        logger.info("\n" + "=" * 60)
        logger.info("Migration Complete")
        logger.info("=" * 60)
        logger.info(f"Total entities: {self.total_entities}")
        logger.info(f"Processed: {self.processed_entities}")
        logger.info(f"  ✅ Enriched: {self.enriched_entities}")
        logger.info(f"  ⏭️  Skipped: {self.skipped_entities}")
        logger.info(f"  ❌ Failed: {self.failed_entities}")
        logger.info(f"\nDuration: {duration:.1f} seconds")
        logger.info(f"Rate: {self.processed_entities / duration:.1f} entities/second")
        logger.info(f"\nEstimated cost: ${self.total_cost:.2f}")
        logger.info(f"Input tokens: {self.total_input_tokens:,}")
        logger.info(f"Output tokens: {self.total_output_tokens:,}")
        logger.info("\nExpected improvement: -35% retrieval failures")
        logger.info("=" * 60)


async def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    migration = ContextualEnrichmentMigration()
    await migration.run()


if __name__ == "__main__":
    asyncio.run(main())

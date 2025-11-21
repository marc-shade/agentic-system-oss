#!/usr/bin/env python3
"""
Add Contextual Enrichment to Claude Code Documentation

Adds LLM-generated contextual prefixes to all documentation entities
for improved retrieval with RAG Tier 1.
"""

import sqlite3
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

# Add contextual_llm to path
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-servers" / "enhanced-memory-mcp"))

from contextual_llm import get_prefix_generator

# Database path
DB_PATH = Path.home() / ".claude" / "enhanced_memories" / "memory.db"


def get_doc_entities():
    """Get all Claude Code documentation entities."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, entity_type
        FROM entities
        WHERE name LIKE 'ClaudeCodeDocs_%'
        ORDER BY id
    """)

    entities = []
    for row in cursor.fetchall():
        entity_id = row['id']

        # Get observations (skip if already has contextual prefix)
        obs_cursor = conn.cursor()
        obs_cursor.execute("""
            SELECT content
            FROM observations
            WHERE entity_id = ?
            ORDER BY created_at
        """, (entity_id,))

        observations = [obs_row[0] for obs_row in obs_cursor.fetchall()]

        # Check if first observation is already a contextual prefix
        if observations and observations[0].startswith('[Context:'):
            print(f"  ⏭️  {row['name']}: Already enriched")
            continue

        entities.append({
            'id': entity_id,
            'name': row['name'],
            'entity_type': row['entity_type'],
            'observations': observations
        })

    conn.close()
    return entities


async def add_contextual_prefix(entity):
    """Add contextual prefix to entity."""
    try:
        # Get prefix generator
        generator = get_prefix_generator()

        # Generate prefix (async call)
        prefix, input_tokens, output_tokens = await generator.generate_prefix(
            entity_name=entity['name'],
            entity_type=entity['entity_type'],
            observations=entity['observations'][:5]  # Use first 5 observations for context
        )

        # Open database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get earliest observation timestamp
        cursor.execute("""
            SELECT MIN(created_at) FROM observations WHERE entity_id = ?
        """, (entity['id'],))
        min_created = cursor.fetchone()[0]

        # Calculate earlier timestamp
        if min_created:
            if 'T' in min_created:
                from datetime import datetime
                dt = datetime.fromisoformat(min_created.replace('Z', '+00:00'))
            else:
                from datetime import datetime
                # Try with microseconds first, then without
                try:
                    dt = datetime.strptime(min_created, '%Y-%m-%d %H:%M:%S.%f')
                except ValueError:
                    dt = datetime.strptime(min_created, '%Y-%m-%d %H:%M:%S')

            insert_time = (dt - timedelta(seconds=1)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            insert_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Insert contextual prefix
        cursor.execute("""
            INSERT INTO observations (entity_id, content, created_at)
            VALUES (?, ?, ?)
        """, (entity['id'], prefix, insert_time))

        conn.commit()
        conn.close()

        return (True, input_tokens, output_tokens)

    except Exception as e:
        return (False, 0, 0, str(e))


async def main():
    """Main execution."""
    print("=" * 70)
    print("CONTEXTUAL ENRICHMENT - CLAUDE CODE DOCUMENTATION")
    print("=" * 70)

    # Get entities
    entities = get_doc_entities()

    print(f"\nFound {len(entities)} documentation entities to enrich")
    print()

    enriched = 0
    failed = 0
    total_input_tokens = 0
    total_output_tokens = 0

    for i, entity in enumerate(entities, 1):
        print(f"[{i}/{len(entities)}] {entity['name']}")

        result = await add_contextual_prefix(entity)

        if result[0]:
            enriched += 1
            total_input_tokens += result[1]
            total_output_tokens += result[2]
            print(f"  ✅ Enriched (tokens: in={result[1]}, out={result[2]})")
        else:
            failed += 1
            print(f"  ❌ Failed: {result[3] if len(result) > 3 else 'Unknown error'}")

    # Summary
    print("\n" + "=" * 70)
    print("ENRICHMENT COMPLETE")
    print("=" * 70)
    print(f"Total entities: {len(entities)}")
    print(f"  ✅ Enriched: {enriched}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📊 Success rate: {(enriched / len(entities) * 100) if entities else 0:.1f}%")
    print()
    print(f"Token usage:")
    print(f"  Input: {total_input_tokens:,}")
    print(f"  Output: {total_output_tokens:,}")
    print(f"  Cost (estimated): ${(total_input_tokens * 0.003 / 1000 + total_output_tokens * 0.015 / 1000):.4f}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Test script to verify automatic contextual enrichment on entity creation.
"""

import asyncio
import sys
import logging
from pathlib import Path
import sqlite3

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

logger = logging.getLogger(__name__)

async def test_auto_enrichment():
    """Test that new entities automatically get contextual prefixes."""

    print("=" * 60)
    print("Automatic Contextual Enrichment Test")
    print("=" * 60)

    try:
        # Import server components
        from server import DB_PATH, _enrich_new_entities
        from memory_client import MemoryClient

        # Create memory client
        memory_client = MemoryClient()

        # Create a test entity
        test_entity = {
            "name": "RAG_Auto_Enrichment_Test",
            "entityType": "test",
            "observations": [
                "This is a test entity to verify automatic contextual enrichment",
                "The entity should receive an LLM-generated contextual prefix",
                "This prefix should appear as the first observation"
            ]
        }

        print("\nCreating test entity via memory-db service...")
        print(f"  Name: {test_entity['name']}")
        print(f"  Type: {test_entity['entityType']}")
        print(f"  Observations: {len(test_entity['observations'])}")

        # Create entity using memory-db service
        create_result = await memory_client.create_entities([test_entity])

        if not create_result.get("success"):
            print(f"❌ Failed to create entity: {create_result.get('error')}")
            return False

        print("✅ Entity created via memory-db service")

        # Now test auto-enrichment
        print("\nApplying contextual enrichment...")
        result = await _enrich_new_entities([test_entity])

        print("\n✅ Enrichment completed!")
        print(f"  Enriched: {result.get('enriched', 0)}")
        print(f"  Failed: {result.get('failed', 0)}")
        print(f"  Using LLM: {result.get('using_llm', False)}")

        tokens = result.get('tokens', {})
        print(f"  Input tokens: {tokens.get('input', 0)}")
        print(f"  Output tokens: {tokens.get('output', 0)}")
        print(f"  Cost: ${result.get('cost_usd', 0.0):.4f}")

        # Verify contextual prefix was added
        print("\nVerifying contextual prefix in database...")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get entity ID
        cursor.execute('SELECT id FROM entities WHERE name = ?', (test_entity['name'],))
        entity_id_row = cursor.fetchone()
        if not entity_id_row:
            print("❌ Test entity not found in database!")
            return False

        entity_id = entity_id_row[0]

        # Get all observations ordered by created_at
        cursor.execute('''
            SELECT content, created_at
            FROM observations
            WHERE entity_id = ?
            ORDER BY created_at
        ''', (entity_id,))

        observations = cursor.fetchall()
        conn.close()

        print(f"\nTotal observations: {len(observations)}")
        print("\nFirst observation (should be contextual prefix):")
        first_obs = observations[0][0]
        print(f"  Content: {first_obs[:200]}...")
        print(f"  Timestamp: {observations[0][1]}")

        # Check if first observation looks like a contextual prefix
        is_prefix = first_obs.startswith("[Context:")
        if is_prefix:
            print("\n✅ Contextual prefix detected!")
        else:
            print("\n⚠️  First observation doesn't look like a contextual prefix")

        # Clean up test entity
        print("\nCleaning up test entity...")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM observations WHERE entity_id = ?', (entity_id,))
        cursor.execute('DELETE FROM entities WHERE id = ?', (entity_id,))
        conn.commit()
        conn.close()
        print("✅ Test entity cleaned up")

        print("\n" + "=" * 60)
        print("✅ TEST PASSED - Auto-enrichment working!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_auto_enrichment())
    sys.exit(0 if success else 1)

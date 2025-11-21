#!/usr/bin/env python3
"""
Test source attribution and new database features
The auto_extract_facts/detect_conflicts/resolve_conflict tools are MCP-layer features
that need to be tested via the actual MCP protocol (not direct client).

This tests the foundation: source tracking in database operations.
"""

import sys
sys.path.insert(0, '.')

from memory_client import MemoryClient
import asyncio
import json

async def test_source_attribution():
    """Test source attribution in entity creation"""
    client = MemoryClient()

    print("="*70)
    print("SOURCE ATTRIBUTION & DATABASE FEATURES TEST")
    print("="*70)
    print()

    # Test 1: Create entity with source attribution
    print("TEST 1: Entity Creation with Source Attribution")
    print("-" * 70)

    test_entity = {
        "name": "test-source-attribution-2025-11-12",
        "entityType": "test",
        "observations": [
            "Testing source_session field",
            "Testing extraction_method field",
            "Testing relevance_score field"
        ],
        "source_session": "test-session-001",
        "extraction_method": "auto",
        "relevance_score": 0.95
    }

    print("Creating test entity with source attribution...")

    result = await client.create_entities([test_entity])

    if result.get("success"):
        print(f"✅ Entity created successfully")
        print(f"   Entity ID: {result['results'][0]['id']}")
        print(f"   Compression: {result['results'][0]['compression_ratio']}")
        print()
    else:
        print(f"❌ Creation failed: {result.get('error')}")
        return

    # Test 2: Verify source attribution in database
    print("TEST 2: Database Schema Verification")
    print("-" * 70)

    import sqlite3
    conn = sqlite3.connect("/Users/marc/.claude/enhanced_memories/memory.db")
    cursor = conn.cursor()

    entity_id = result['results'][0]['id']

    cursor.execute('''
        SELECT source_session, source_timestamp, extraction_method,
               relevance_score, last_confirmed
        FROM entities WHERE id = ?
    ''', (entity_id,))

    row = cursor.fetchone()

    if row:
        print("✅ Source attribution fields populated:")
        print(f"   source_session: {row[0]}")
        print(f"   source_timestamp: {row[1]}")
        print(f"   extraction_method: {row[2]}")
        print(f"   relevance_score: {row[3]}")
        print(f"   last_confirmed: {row[4]}")
        print()
    else:
        print("❌ Entity not found in database")

    # Test 3: Verify conflicts table exists
    print("TEST 3: Conflicts Table Verification")
    print("-" * 70)

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conflicts'")
    if cursor.fetchone():
        print("✅ Conflicts table exists")

        cursor.execute("SELECT COUNT(*) FROM conflicts")
        count = cursor.fetchone()[0]
        print(f"   Current conflicts tracked: {count}")
        print()
    else:
        print("❌ Conflicts table not found")

    # Test 4: Check indexes
    print("TEST 4: Index Verification")
    print("-" * 70)

    cursor.execute('''
        SELECT name FROM sqlite_master
        WHERE type='index' AND name LIKE '%source%' OR name LIKE '%relevance%'
    ''')

    indexes = cursor.fetchall()
    if indexes:
        print("✅ Source/relevance indexes created:")
        for idx in indexes:
            print(f"   - {idx[0]}")
        print()
    else:
        print("⚠️  No source/relevance indexes found")

    conn.close()

    # Test 5: Memory status
    print("TEST 5: Memory System Status")
    print("-" * 70)

    status = await client.get_memory_status()

    if status.get("success"):
        print(f"✅ Total entities: {status['entities']['total']}")
        print(f"   Compression ratio: {status['compression']['ratio']}")
        print(f"   Storage: {status['compression']['total_compressed_kb']} KB compressed")
        print()

    print("="*70)
    print("FOUNDATION TEST COMPLETE")
    print()
    print("NOTE: auto_extract_facts, detect_conflicts, and resolve_conflict are")
    print("MCP-layer tools that need to be tested via the MCP protocol, not")
    print("directly through the Python client.")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_source_attribution())

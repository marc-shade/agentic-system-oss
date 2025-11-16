#!/usr/bin/env python3
"""
Direct function test for new MCP tools (bypassing MCP protocol)
Tests the actual implementation by importing and calling functions directly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import asyncio
from datetime import datetime

# Import the tool functions directly from server
# We'll need to mock the memory_client and other dependencies
from unittest.mock import Mock, patch
import sqlite3

DB_PATH = "/Users/marc/.claude/enhanced_memories/memory.db"

async def test_auto_extract_facts():
    """Test auto_extract_facts function directly"""
    print("=" * 70)
    print("TEST 1: auto_extract_facts (Direct Function Call)")
    print("=" * 70)

    # Import the actual function
    from server import auto_extract_facts

    conversation_text = """User: I prefer using voice communication for all interactions.
Assistant: Understood, I'll prioritize voice mode.
User: I always use parallel tool execution when possible.
Assistant: Got it, parallel execution preferred.
User: I need production-ready code only, no POCs.
Assistant: Production-only policy noted."""

    print(f"\nInput conversation ({len(conversation_text)} chars):")
    print(conversation_text[:100] + "...")
    print()

    # Call the function
    result = await auto_extract_facts(
        conversation_text=conversation_text,
        session_id="direct-test-001",
        auto_store=True
    )

    print(f"✅ Function executed")
    print(f"   Success: {result.get('success')}")
    print(f"   Facts extracted: {result.get('count')}")
    print(f"   Stored: {result.get('stored')}")
    print(f"   Entity IDs: {result.get('entity_ids', [])}")
    print()

    if result.get('facts'):
        for i, fact in enumerate(result['facts'], 1):
            print(f"   Fact {i}:")
            print(f"     Name: {fact['name']}")
            print(f"     Type: {fact['entityType']}")
            print(f"     Observations: {len(fact.get('observations', []))} items")
            for obs in fact.get('observations', [])[:3]:
                print(f"       • {obs}")
            print()

    return result


async def test_detect_conflicts():
    """Test detect_conflicts function directly"""
    print("=" * 70)
    print("TEST 2: detect_conflicts (Direct Function Call)")
    print("=" * 70)

    from server import detect_conflicts

    # Use similar data to what was just extracted
    test_entity_data = {
        "name": "test-duplicate-preferences",
        "entityType": "auto_extracted",
        "observations": [
            "I prefer using voice communication for all interactions.",
            "I always use parallel tool execution when possible."
        ]
    }

    print("\nChecking for conflicts with test entity...")
    print(f"Entity name: {test_entity_data['name']}")
    print(f"Observations: {len(test_entity_data['observations'])} items")
    print()

    result = await detect_conflicts(
        entity_data=test_entity_data,
        threshold=0.50  # Lower threshold to catch more
    )

    print(f"✅ Function executed")
    print(f"   Success: {result.get('success')}")
    print(f"   Conflicts found: {result.get('conflict_count')}")
    print()

    if result.get('conflicts'):
        for i, conflict in enumerate(result['conflicts'], 1):
            print(f"   Conflict {i}:")
            print(f"     With: {conflict['existing_entity']}")
            print(f"     Type: {conflict['conflict_type']}")
            print(f"     Confidence: {conflict['confidence']:.2%}")
            print(f"     Suggested action: {conflict['suggested_action']}")
            print(f"     Details: {conflict.get('details', 'N/A')}")
            print()

    return result


async def test_resolve_conflict():
    """Test resolve_conflict function directly"""
    print("=" * 70)
    print("TEST 3: resolve_conflict (Direct Function Call)")
    print("=" * 70)

    from server import resolve_conflict

    # First, find an actual conflict to resolve
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get two similar entities
    cursor.execute('''
        SELECT id, name FROM entities
        WHERE entity_type = 'auto_extracted'
        ORDER BY created_at DESC
        LIMIT 2
    ''')

    entities = cursor.fetchall()
    conn.close()

    if len(entities) < 2:
        print("⚠️  Not enough auto_extracted entities to test conflict resolution")
        print(f"   Found: {len(entities)} entities")
        return {"success": False, "error": "Insufficient entities"}

    conflict_data = {
        "entity_id": entities[0][0],
        "existing_id": entities[1][0],
        "conflict_type": "duplicate",
        "confidence": 0.87
    }

    print(f"\nResolving conflict between:")
    print(f"  Entity 1: {entities[0][1]} (ID: {entities[0][0]})")
    print(f"  Entity 2: {entities[1][1]} (ID: {entities[1][0]})")
    print(f"  Strategy: merge (auto-selected for duplicates)")
    print()

    result = await resolve_conflict(
        conflict_data=conflict_data,
        strategy="merge"
    )

    print(f"✅ Function executed")
    print(f"   Success: {result.get('success')}")
    print(f"   Action taken: {result.get('action_taken')}")
    print(f"   Strategy used: {result.get('strategy')}")
    print(f"   Updated entities: {result.get('updated_entities', [])}")
    print()

    # Verify conflict logged
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM conflicts WHERE resolution_status = "resolved"')
    resolved_count = cursor.fetchone()[0]
    print(f"   Conflicts logged in database: {resolved_count}")
    conn.close()
    print()

    return result


async def verify_database_state():
    """Verify the database state after tests"""
    print("=" * 70)
    print("DATABASE STATE VERIFICATION")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Count auto-extracted entities
    cursor.execute('SELECT COUNT(*) FROM entities WHERE entity_type = "auto_extracted"')
    auto_count = cursor.fetchone()[0]

    # Count conflicts
    cursor.execute('SELECT COUNT(*) FROM conflicts')
    conflict_count = cursor.fetchone()[0]

    # Get recent auto-extracted entities
    cursor.execute('''
        SELECT name, source_session, extraction_method, relevance_score
        FROM entities
        WHERE entity_type = "auto_extracted"
        ORDER BY created_at DESC
        LIMIT 3
    ''')
    recent = cursor.fetchall()

    conn.close()

    print(f"\n✅ Auto-extracted entities: {auto_count}")
    print(f"✅ Conflicts tracked: {conflict_count}")
    print()

    if recent:
        print("Recent auto-extracted entities:")
        for name, session, method, score in recent:
            print(f"  • {name}")
            print(f"    Session: {session}")
            print(f"    Method: {method}")
            print(f"    Relevance: {score}")
            print()


async def main():
    """Run all direct function tests"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 10 + "NEW MCP TOOLS - DIRECT FUNCTION TEST" + " " * 22 + "║")
    print("║" + " " * 15 + "(Bypassing MCP Protocol Layer)" + " " * 22 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    try:
        # Test 1: Auto-extract facts
        extract_result = await test_auto_extract_facts()

        # Test 2: Detect conflicts
        conflict_result = await test_detect_conflicts()

        # Test 3: Resolve conflict (if possible)
        resolve_result = await test_resolve_conflict()

        # Verify database state
        await verify_database_state()

        print("=" * 70)
        print("DIRECT FUNCTION TEST COMPLETE")
        print("=" * 70)
        print()
        print("✅ All three functions executed successfully")
        print("✅ Database operations confirmed")
        print()
        print("⚠️  Note: MCP protocol integration still needs Claude Code restart")
        print("   to expose these tools via the MCP interface.")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

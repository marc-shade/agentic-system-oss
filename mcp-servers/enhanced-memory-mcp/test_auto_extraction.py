#!/usr/bin/env python3
"""
Test automatic memory extraction and conflict resolution
"""

import sys
sys.path.insert(0, '.')

from memory_client import MemoryClient
import asyncio
import json

async def test_pipeline():
    """Test the complete auto-extraction and conflict resolution pipeline"""
    client = MemoryClient()

    print("="*70)
    print("AUTOMATIC MEMORY EXTRACTION & CONFLICT RESOLUTION TEST")
    print("="*70)
    print()

    # Test 1: Auto-extract facts from conversation
    print("TEST 1: Automatic Fact Extraction")
    print("-" * 70)

    sample_conversation = """
User: I prefer using voice communication for all interactions
Assistant: Understood. I'll prioritize voice mode.
User: I always use SSDRAID0 for active execution, never FILES
Assistant: Got it.
User: I need production-ready code only, no POCs or demos
Assistant: Production-only policy noted.
User: I like working with parallel tool execution when possible
Assistant: Will use parallel execution.
"""

    print(f"Extracting from conversation (length: {len(sample_conversation)} chars)...")

    extraction_result = await client.auto_extract_facts(
        conversation_text=sample_conversation,
        session_id="test-session-001",
        auto_store=True
    )

    if extraction_result.get("success"):
        print(f"✅ Extracted {extraction_result['count']} entities")
        print(f"   Stored: {extraction_result['stored']}")
        print(f"   Entity IDs: {extraction_result.get('entity_ids', [])}")
        print()

        for fact in extraction_result.get("facts", []):
            print(f"   - {fact['name']}")
            print(f"     Type: {fact['entityType']}")
            print(f"     Observations: {len(fact.get('observations', []))} items")
            for obs in fact.get('observations', [])[:3]:
                print(f"       • {obs}")
            print()
    else:
        print(f"❌ Extraction failed: {extraction_result.get('error')}")
        return

    # Test 2: Detect conflicts
    print()
    print("TEST 2: Conflict Detection")
    print("-" * 70)

    # Create a similar entity that should conflict
    test_entity = {
        "name": "test-duplicate-preferences",
        "entityType": "auto_extracted",
        "observations": [
            "I prefer using voice communication for all interactions",  # Duplicate
            "I always use SSDRAID0 for active execution"                # Duplicate
        ]
    }

    print("Checking for conflicts with test entity...")

    conflict_result = await client.detect_conflicts(
        entity_data=test_entity,
        threshold=0.50  # Lower threshold to catch more conflicts
    )

    if conflict_result.get("success"):
        print(f"✅ Found {conflict_result['conflict_count']} conflicts")
        print()

        for conflict in conflict_result.get("conflicts", []):
            print(f"   Conflict with: {conflict['existing_entity']}")
            print(f"   Type: {conflict['conflict_type']}")
            print(f"   Confidence: {conflict['confidence']:.2%}")
            print(f"   Suggested action: {conflict['suggested_action']}")
            print(f"   Details: {conflict['details']}")
            print()
    else:
        print(f"❌ Conflict detection failed: {conflict_result.get('error')}")

    # Test 3: Check source attribution
    print()
    print("TEST 3: Source Attribution Verification")
    print("-" * 70)

    # Search for auto-extracted entities
    search_result = await client.search_nodes("auto-extracted", limit=5)

    if search_result.get("success"):
        print(f"✅ Found {search_result['count']} auto-extracted entities")
        print()

        for entity in search_result.get("results", []):
            if "auto-extracted" in entity['name']:
                print(f"   {entity['name']}")
                print(f"   Source: {entity.get('source', 'unknown')}")
                print(f"   Observations: {len(entity.get('observations', []))} items")
                print()

    # Test 4: Memory status
    print()
    print("TEST 4: Memory System Status")
    print("-" * 70)

    status = await client.get_memory_status()

    if status.get("success"):
        print(f"✅ Total entities: {status['entities']['total']}")
        print(f"   Compression ratio: {status['compression']['ratio']}")
        print(f"   Storage: {status['compression']['total_compressed_kb']} KB compressed")
        print()

    print("="*70)
    print("PIPELINE TEST COMPLETE")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_pipeline())

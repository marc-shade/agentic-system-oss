#!/usr/bin/env python3
"""
Comprehensive Test for Letta Integration

Tests all 5 phases:
1. Memory Blocks (Letta-style in-context memory)
2. Sleeptime Agent (background consolidation)
3. Multi-Agent Shared Blocks (cluster coordination)
4. Agent File (.af export/import)
5. Filesystem Integration (simplified)
"""
import platform

import json
import os
import time
from pathlib import Path
from letta_memory_blocks import MemoryBlockManager

# Storage path from environment
AGENTIC_SYSTEM_PATH = os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE))
from sleeptime_agent import SleetimeAgent
from cluster_shared_blocks import setup_cluster_shared_blocks, update_cluster_context
from agent_file import AgentFileExporter, AgentFileImporter

# Database path
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


def test_phase1_memory_blocks():
    """Phase 1: Test Letta-style memory blocks"""
    print("\n" + "="*80)
    print("PHASE 1: Letta-style Memory Blocks")
    print("="*80)

    manager = MemoryBlockManager(DB_PATH)

    # Create default blocks
    print("\n1. Creating default memory blocks for 'macpro51_agent'...")
    result = manager.create_default_blocks(agent_id="macpro51_agent", node_id="macpro51")
    print(f"   ✓ Created {result['count']} blocks: {', '.join(result['blocks_created'])}")

    # Test core_memory_append
    print("\n2. Testing core_memory_append...")
    result = manager.append_to_block(
        agent_id="macpro51_agent",
        label="task",
        content="Running Letta integration test - Phase 1 memory blocks"
    )
    print(f"   ✓ Appended to 'task' block: {result['chars_current']}/{result['chars_limit']} chars")

    # Test core_memory_replace
    print("\n3. Testing core_memory_replace...")
    result = manager.replace_in_block(
        agent_id="macpro51_agent",
        label="identity",
        old_content="Linux Builder",
        new_content="Linux Builder with Letta integration (TEST MODE)"
    )
    print(f"   ✓ Replaced in 'identity' block: {result['chars_current']}/{result['chars_limit']} chars")

    # List all blocks
    print("\n4. Listing all memory blocks...")
    blocks = manager.list_blocks(agent_id="macpro51_agent")
    for block in blocks:
        print(f"   - {block['label']}: {block['chars_current']}/{block['chars_limit']} chars")

    # Render blocks as XML
    print("\n5. Rendering blocks as XML...")
    xml = manager.render_blocks(agent_id="macpro51_agent", use_line_numbers=False)
    print(f"   ✓ Generated {len(xml)} chars of XML")
    print(f"   Preview:\n{xml[:300]}...")

    print("\n✅ Phase 1 complete: Memory blocks working correctly")
    return True


def test_phase2_sleeptime_agent():
    """Phase 2: Test sleeptime agent consolidation"""
    print("\n" + "="*80)
    print("PHASE 2: Sleeptime Agent Background Consolidation")
    print("="*80)

    agent = SleetimeAgent(agent_id="macpro51_agent", db_path=DB_PATH)

    # Run consolidation cycle
    print("\n1. Running consolidation cycle...")
    result = agent.run_consolidation_cycle(time_window_hours=24)

    print(f"\nConsolidation Results:")
    print(f"   - Memories processed: {result['memories_processed']}")
    print(f"   - Patterns found: {result['patterns_found']}")
    print(f"   - Concepts created: {result['concepts_created']}")
    print(f"   - Causal chains: {result['causal_chains_discovered']}")
    print(f"   - Learnings updated: {result['learnings_updated']}")
    print(f"   - Duration: {result['duration_seconds']:.2f}s")

    print("\n✅ Phase 2 complete: Sleeptime agent operational")
    return True


def test_phase3_shared_blocks():
    """Phase 3: Test multi-agent shared blocks"""
    print("\n" + "="*80)
    print("PHASE 3: Multi-Agent Shared Memory Blocks")
    print("="*80)

    # Setup cluster shared blocks
    print("\n1. Setting up cluster shared blocks...")
    result = setup_cluster_shared_blocks()

    print(f"\nSetup Results:")
    print(f"   - Shared blocks created: {result['total_blocks']}")
    print(f"   - Attachments created: {result['total_attachments']}")

    # Update cluster context
    print("\n2. Updating cluster_context shared block...")
    update_result = update_cluster_context(
        "Letta integration test in progress - all phases operational",
        updated_by="macpro51"
    )
    print(f"   ✓ Update successful: {update_result['chars_current']}/{update_result['chars_limit']} chars")

    print("\n✅ Phase 3 complete: Shared blocks enable cluster coordination")
    return True


def test_phase4_agent_file():
    """Phase 4: Test agent file export/import"""
    print("\n" + "="*80)
    print("PHASE 4: Agent File (.af) Export/Import")
    print("="*80)

    exporter = AgentFileExporter(DB_PATH)
    importer = AgentFileImporter(DB_PATH)

    export_path = MEMORY_DIR / "test_export_macpro51.af"

    # Export agent
    print("\n1. Exporting agent state to .af file...")
    export_result = exporter.save_agent_file(
        agent_id="macpro51_agent",
        output_path=export_path,
        compress=True
    )

    print(f"\nExport Results:")
    print(f"   - File: {export_result['file_path']}")
    print(f"   - Size: {export_result['file_size_kb']:.2f} KB")
    print(f"   - Blocks exported: {export_result['blocks_exported']}")
    print(f"   - Entities exported: {export_result['entities_exported']}")
    print(f"   - Compressed: {export_result['compressed']}")

    # Import agent
    print("\n2. Importing agent from .af file...")
    import_result = importer.import_agent(
        file_path=export_path,
        new_agent_id="macpro51_agent_restored",
        import_entities=True
    )

    print(f"\nImport Results:")
    print(f"   - Original agent: {import_result['original_agent_id']}")
    print(f"   - New agent: {import_result['new_agent_id']}")
    print(f"   - Blocks imported: {import_result['blocks_imported']}")
    print(f"   - Entities imported: {import_result['entities_imported']}")

    print("\n✅ Phase 4 complete: Agent state is portable via .af files")
    return True


def test_phase5_filesystem():
    """Phase 5: Test filesystem integration (simplified)"""
    print("\n" + "="*80)
    print("PHASE 5: Filesystem Integration (Simplified)")
    print("="*80)

    import sqlite3

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()


    # Initialize filesystem tables
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agent_folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            folder_name TEXT NOT NULL,
            folder_path TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(agent_id, folder_name)
        )
    ''')

    # Create folder attachment
    print("\n1. Creating folder attachment...")
    try:
        cursor.execute('''
            INSERT INTO agent_folders (agent_id, folder_name, folder_path, description)
            VALUES (?, ?, ?, ?)
        ''', (
            "macpro51_agent",
            "architecture_docs",
            f"{AGENTIC_SYSTEM_PATH}/docs",
            "System architecture documentation"
        ))
        folder_id = cursor.lastrowid
        conn.commit()
        print(f"   ✓ Created folder: architecture_docs (ID: {folder_id})")
    except sqlite3.IntegrityError:
        print(f"   ℹ Folder already exists (skipping)")

    # List folders
    cursor.execute('''
        SELECT id, folder_name, folder_path, description
        FROM agent_folders
        WHERE agent_id = ?
    ''', ("macpro51_agent",))

    print("\n2. Listing attached folders...")
    for row in cursor.fetchall():
        print(f"   - {row[1]}: {row[2]}")
        print(f"     Description: {row[3]}")

    conn.close()

    print("\n✅ Phase 5 complete: Filesystem integration ready (simplified)")
    print("   Note: Full Qdrant vector search integration pending")
    return True


def run_comprehensive_test():
    """Run comprehensive test of all 5 phases"""
    print("\n" + "="*80)
    print("LETTA INTEGRATION COMPREHENSIVE TEST")
    print("="*80)
    print("\nTesting all 5 phases of Letta integration...")
    print(f"Database: {DB_PATH}")

    start_time = time.time()
    results = {}

    # Run all phases
    try:
        results["phase1"] = test_phase1_memory_blocks()
    except Exception as e:
        print(f"\n❌ Phase 1 failed: {e}")
        results["phase1"] = False

    try:
        results["phase2"] = test_phase2_sleeptime_agent()
    except Exception as e:
        print(f"\n❌ Phase 2 failed: {e}")
        results["phase2"] = False

    try:
        results["phase3"] = test_phase3_shared_blocks()
    except Exception as e:
        print(f"\n❌ Phase 3 failed: {e}")
        results["phase3"] = False

    try:
        results["phase4"] = test_phase4_agent_file()
    except Exception as e:
        print(f"\n❌ Phase 4 failed: {e}")
        results["phase4"] = False

    try:
        results["phase5"] = test_phase5_filesystem()
    except Exception as e:
        print(f"\n❌ Phase 5 failed: {e}")
        results["phase5"] = False

    # Summary
    duration = time.time() - start_time

    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"\nResults: {passed}/{total} phases passed")
    print(f"Duration: {duration:.2f}s\n")

    for phase, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status} - {phase}")

    if all(results.values()):
        print("\n🎉 ALL PHASES COMPLETE - LETTA INTEGRATION SUCCESSFUL!")
        print("\nNext Steps:")
        print("   1. Restart Claude Code to activate new MCP tools")
        print("   2. Use create_default_memory_blocks() for new agents")
        print("   3. Run run_memory_consolidation() periodically")
        print("   4. Create shared blocks for cluster coordination")
        print("   5. Export agents with export_agent_to_file()")
    else:
        print("\n⚠️  Some phases failed - review errors above")

    return all(results.values())


if __name__ == "__main__":
    success = run_comprehensive_test()
    exit(0 if success else 1)

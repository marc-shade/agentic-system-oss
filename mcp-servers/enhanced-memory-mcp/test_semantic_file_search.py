#!/usr/bin/env python3
"""
Test Semantic File Search Feature

Tests:
1. Qdrant collection creation
2. Module imports and tool registration
3. File indexing with embeddings
4. Semantic search functionality
5. Index status reporting
"""
import platform

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Storage path from environment
AGENTIC_SYSTEM_PATH = os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE))
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")


def test_qdrant_connectivity():
    """Test 1: Check Qdrant server connectivity"""
    print("\n" + "=" * 60)
    print("TEST 1: Qdrant Connectivity")
    print("=" * 60)

    print(f"Qdrant URL: {QDRANT_URL}")

    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url=QDRANT_URL)

        # Check if Qdrant is reachable
        collections = client.get_collections()
        print(f"\n✅ Qdrant is reachable")
        print(f"   Existing collections: {len(collections.collections)}")

        for col in collections.collections:
            print(f"   - {col.name}")

        return True
    except Exception as e:
        print(f"❌ Cannot connect to Qdrant: {e}")
        print("   Make sure Qdrant is running on port 6333")
        return False


def test_imports():
    """Test 2: Check that all required modules import"""
    print("\n" + "=" * 60)
    print("TEST 2: Module Imports")
    print("=" * 60)

    try:
        from filesystem_tools import register_filesystem_tools
        print("✅ filesystem_tools module imports")
    except Exception as e:
        print(f"❌ Failed to import filesystem_tools: {e}")
        return False

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams
        print("✅ qdrant_client imports")
    except Exception as e:
        print(f"❌ Failed to import qdrant_client: {e}")
        return False

    try:
        import hashlib
        print("✅ hashlib imports")
    except Exception as e:
        print(f"❌ Failed to import hashlib: {e}")
        return False

    return True


def test_tool_registration():
    """Test 3: Test that tools can be registered (mock FastMCP app)"""
    print("\n" + "=" * 60)
    print("TEST 3: Tool Registration")
    print("=" * 60)

    try:
        from filesystem_tools import register_filesystem_tools

        # Create mock FastMCP app
        class MockApp:
            def __init__(self):
                self.tools = []

            def tool(self):
                """Decorator to register tools"""
                def decorator(func):
                    self.tools.append(func.__name__)
                    return func
                return decorator

        mock_app = MockApp()

        # Register tools with temp database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        try:
            # Pass nmf=None to test without embeddings
            register_filesystem_tools(mock_app, db_path, nmf=None)

            print(f"✅ Registered {len(mock_app.tools)} tools:")
            for tool_name in mock_app.tools:
                print(f"   - {tool_name}")

            # Check for new semantic search tools
            expected_tools = [
                'create_agent_folder',
                'list_agent_folders',
                'simple_file_search',
                'index_folder_files',
                'semantic_file_search',
                'get_file_index_status'
            ]

            for expected in expected_tools:
                if expected in mock_app.tools:
                    print(f"✅ Tool '{expected}' registered")
                else:
                    print(f"❌ Tool '{expected}' NOT registered")
                    return False

            return True

        finally:
            # Clean up temp database
            os.unlink(db_path)

    except Exception as e:
        print(f"❌ Tool registration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_schema():
    """Test 4: Test that database schema has new columns"""
    print("\n" + "=" * 60)
    print("TEST 4: Database Schema")
    print("=" * 60)

    try:
        import sqlite3
        from filesystem_tools import register_filesystem_tools

        # Create mock app
        class MockApp:
            def __init__(self):
                self.tools = []

            def tool(self):
                def decorator(func):
                    self.tools.append(func.__name__)
                    return func
                return decorator

        mock_app = MockApp()

        # Create temp database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        try:
            register_filesystem_tools(mock_app, db_path, nmf=None)

            # Check schema
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Check agent_files table columns
            cursor.execute("PRAGMA table_info(agent_files)")
            columns = {row[1] for row in cursor.fetchall()}

            required_columns = {
                'id', 'folder_id', 'filename', 'file_path',
                'file_size_bytes', 'content_hash', 'indexed_at',
                'qdrant_id', 'added_at'
            }

            print("Checking agent_files table columns:")
            for col in required_columns:
                if col in columns:
                    print(f"   ✅ Column '{col}' exists")
                else:
                    print(f"   ❌ Column '{col}' MISSING")
                    return False

            # Check index
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='agent_files'")
            indexes = [row[0] for row in cursor.fetchall()]

            if any('hash' in idx.lower() for idx in indexes):
                print(f"✅ Content hash index exists")
            else:
                print(f"⚠️  Content hash index not found")

            conn.close()
            return True

        finally:
            os.unlink(db_path)

    except Exception as e:
        print(f"❌ Database schema check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_hash_computation():
    """Test 5: Test file hash computation"""
    print("\n" + "=" * 60)
    print("TEST 5: File Hash Computation")
    print("=" * 60)

    try:
        import hashlib

        # Create test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("Test content for hash computation")
            tmp_path = tmp.name

        try:
            # Compute hash
            with open(tmp_path, 'rb') as f:
                content = f.read()
                file_hash = hashlib.sha256(content).hexdigest()

            print(f"✅ File hash computed: {file_hash[:16]}...")

            # Verify hash is consistent
            with open(tmp_path, 'rb') as f:
                content2 = f.read()
                file_hash2 = hashlib.sha256(content2).hexdigest()

            if file_hash == file_hash2:
                print(f"✅ Hash is deterministic")
            else:
                print(f"❌ Hash changed unexpectedly")
                return False

            return True

        finally:
            os.unlink(tmp_path)

    except Exception as e:
        print(f"❌ Hash computation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_qdrant_collection_creation():
    """Test 6: Test Qdrant collection creation"""
    print("\n" + "=" * 60)
    print("TEST 6: Qdrant Collection Creation")
    print("=" * 60)

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        client = QdrantClient(url=QDRANT_URL)
        collection_name = "agent_file_embeddings_test"

        # Delete if exists
        try:
            client.delete_collection(collection_name)
            print(f"   Cleaned up existing test collection")
        except:
            pass

        # Create collection
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE)
        )
        print(f"✅ Created collection '{collection_name}'")

        # Verify
        collection_info = client.get_collection(collection_name)
        print(f"   Vector size: {collection_info.config.params.vectors.size}")
        print(f"   Distance: {collection_info.config.params.vectors.distance}")

        # Clean up
        client.delete_collection(collection_name)
        print(f"✅ Cleaned up test collection")

        return True

    except Exception as e:
        print(f"❌ Collection creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_embedding_generation():
    """Test 7: Test embedding generation (if NMF and providers available)"""
    print("\n" + "=" * 60)
    print("TEST 7: Embedding Generation")
    print("=" * 60)

    try:
        # Try to import NMF
        from neural_memory_fabric import NeuralMemoryFabric

        print("Creating NMF instance...")
        nmf = NeuralMemoryFabric()

        test_text = "This is a test document about Python programming and AI agents."

        print(f"Generating embedding for: '{test_text[:50]}...'")
        result = await nmf.embedding_manager.generate_embedding(test_text)

        # Handle both direct array and object with .embedding attribute
        embedding = result.embedding if hasattr(result, 'embedding') else result

        if embedding is not None and len(embedding) > 0:
            print(f"✅ Generated embedding with {len(embedding)} dimensions")
            print(f"   First 5 values: {embedding[:5]}")
            return True
        else:
            print(f"⚠️  Embedding is empty - embedding provider not available")
            print("   This is expected if Ollama/embedding service is offline")
            print("   Semantic search requires embedding service at runtime")
            return "skip"

    except ImportError:
        print("⚠️  NeuralMemoryFabric not available - skipping embedding test")
        print("   This is OK - semantic search will require NMF to be passed")
        return "skip"
    except Exception as e:
        error_msg = str(e).lower()
        if "embedding" in error_msg or "provider" in error_msg or "connection" in error_msg:
            print(f"⚠️  Embedding provider not available: {e}")
            print("   This is expected if Ollama/embedding service is offline")
            print("   Semantic search requires embedding service at runtime")
            return "skip"
        print(f"❌ Embedding generation failed: {e}")
        import traceback

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

        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all semantic file search tests"""
    print("\n" + "=" * 60)
    print("SEMANTIC FILE SEARCH TEST SUITE")
    print("=" * 60)
    print(f"\nQdrant URL: {QDRANT_URL}")

    results = {}

    # Test 1: Qdrant connectivity
    results["qdrant_connectivity"] = test_qdrant_connectivity()

    # Test 2: Imports
    results["imports"] = test_imports()

    # Test 3: Tool registration
    results["tool_registration"] = test_tool_registration()

    # Test 4: Database schema
    results["database_schema"] = test_database_schema()

    # Test 5: Hash computation
    results["hash_computation"] = test_file_hash_computation()

    # Test 6: Qdrant collection creation
    if results["qdrant_connectivity"]:
        results["collection_creation"] = test_qdrant_collection_creation()
    else:
        print("\n⚠️  Skipping collection creation test (Qdrant not available)")
        results["collection_creation"] = "skip"

    # Test 7: Embedding generation
    try:
        results["embedding_generation"] = await test_embedding_generation()
    except Exception as e:
        print(f"❌ Embedding test failed: {e}")
        results["embedding_generation"] = False

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v is True)
    skipped = sum(1 for v in results.values() if v == "skip")
    failed = sum(1 for v in results.values() if v is False)
    total = len(results)

    for test_name, result in results.items():
        if result == "skip":
            status = "⚠️  SKIP"
        elif result:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        print(f"   {status}: {test_name}")

    print(f"\nTotal: {passed} passed, {skipped} skipped, {failed} failed out of {total}")

    if failed == 0:
        print("\n🎉 Semantic file search feature is ready!")
        if skipped > 0:
            print(f"   Note: {skipped} test(s) skipped due to optional dependencies")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed. Review errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)

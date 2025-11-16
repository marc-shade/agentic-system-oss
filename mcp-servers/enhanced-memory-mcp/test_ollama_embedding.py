#!/usr/bin/env python3
"""
Test Ollama Embedding Model
Verifies that mxbai-embed-large model works correctly
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from embedding_providers import EmbeddingManager


async def test_ollama_embedding():
    """Test Ollama embedding generation"""
    print("=" * 70)
    print("OLLAMA EMBEDDING TEST")
    print("=" * 70)
    print()

    try:
        # Initialize provider manager
        print("Initializing embedding providers...")
        manager = EmbeddingManager()
        await manager.initialize()

        providers = manager.get_available_providers()
        print(f"✅ Available providers: {', '.join(providers)}")
        print()

        if 'ollama' not in providers:
            print("❌ Ollama provider not available")
            return False

        # Test embedding generation
        test_text = "This is a test of the Ollama embedding model with mxbai-embed-large"
        print(f"Test text: '{test_text}'")
        print()

        print("Generating embedding with Ollama...")
        result = await manager.generate_embedding(
            text=test_text,
            preferred_provider='ollama'
        )

        if result['success']:
            print(f"✅ Embedding generated successfully!")
            print(f"   Provider: {result['provider']}")
            print(f"   Model: {result.get('model', 'unknown')}")
            print(f"   Dimensions: {len(result['embedding'])}")
            print(f"   Latency: {result['latency_ms']:.2f}ms")
            print(f"   First 5 values: {result['embedding'][:5]}")
            print()
            return True
        else:
            print(f"❌ Embedding generation failed: {result.get('error')}")
            return False

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the test"""
    success = await test_ollama_embedding()

    print()
    print("=" * 70)
    if success:
        print("✅ OLLAMA EMBEDDING TEST PASSED")
    else:
        print("❌ OLLAMA EMBEDDING TEST FAILED")
    print("=" * 70)

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

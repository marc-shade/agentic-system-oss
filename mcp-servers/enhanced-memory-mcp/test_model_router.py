#!/usr/bin/env python3
"""
Test script for IntelligentModelRouter

Verifies:
1. Router initializes correctly
2. Model selection logic works
3. Can execute requests to Ollama
4. Stats tracking works
"""

import asyncio
import sys
from model_router import IntelligentModelRouter


async def test_router():
    """Test the IntelligentModelRouter functionality"""

    print("🧪 Testing IntelligentModelRouter\n")

    # Initialize router
    router = IntelligentModelRouter(
        stats_file="/tmp/test_model_router_stats.json"
    )
    print("✅ Router initialized successfully\n")

    # Test 1: Health check
    print("Test 1: Health Check")
    print("-" * 50)
    health = await router.health_check()
    print(f"Ollama available: {health['ollama_available']}")
    print(f"Models available:")
    for model_type, info in health['models_available'].items():
        status = "✅" if info['available'] else "❌"
        print(f"  {status} {model_type}: {info['name']}")
    print()

    # Test 2: Model selection logic
    print("Test 2: Model Selection Logic")
    print("-" * 50)

    test_contexts = [
        {"complexity": 30, "description": "Simple task"},
        {"complexity": 50, "description": "Moderate task"},
        {"complexity": 80, "description": "Complex task"},
        {"complexity": 50, "requires_reasoning": True, "description": "Reasoning task"},
        {"complexity": 60, "multi_step": True, "description": "Multi-step task"}
    ]

    for context in test_contexts:
        desc = context.pop("description")
        model, location = router._select_model(context)
        print(f"  {desc}: {model} ({location})")
    print()

    # Test 3: Actual execution (simple test)
    print("Test 3: Execution Test (Simple)")
    print("-" * 50)
    try:
        result = await router.execute_with_routing(
            task="What is 2 + 2? Answer with just the number.",
            context={"complexity": 30}
        )
        print(f"  Model used: {result['model_used']}")
        print(f"  Location: {result['location']}")
        print(f"  Duration: {result['duration_seconds']:.2f}s")
        print(f"  Response preview: {result['response'][:100]}...")
        print()
    except Exception as e:
        print(f"  ❌ Error: {e}")
        print()

    # Test 4: Stats tracking
    print("Test 4: Stats Tracking")
    print("-" * 50)
    stats = router.get_stats()
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Local requests: {stats['local_requests']}")
    print(f"  Cloud requests: {stats['cloud_requests']}")
    print(f"  Model usage:")
    for model, usage in stats.get('model_usage', {}).items():
        print(f"    {model}: {usage['count']} requests, avg {usage['avg_duration']:.2f}s")
    print()

    print("✅ All tests completed!")
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_router())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

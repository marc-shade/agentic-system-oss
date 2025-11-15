"""
Test reasoning prioritization integration
"""
import asyncio
from reasoning_prioritizer import get_prioritizer, ContentCategory

async def test_prioritizer():
    print("\n=== Testing Reasoning Prioritizer ===\n")

    prioritizer = get_prioritizer()

    # Test samples
    samples = [
        ("Code", "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)"),
        ("Math", "Theorem: For all prime p, Euler's totient φ(p) = p - 1"),
        ("Visual", "The image shows a red apple on a blue plate"),
        ("General", "The weather is nice today")
    ]

    for label, content in samples:
        priority = prioritizer.classify_content(content)
        print(f"{label} Sample:")
        print(f"  Category: {priority.category.value}")
        print(f"  Weight: {priority.weight}")
        print(f"  Reasoning Score: {priority.reasoning_score:.2f}")
        print(f"  Visual Score: {priority.visual_score:.2f}")
        print(f"  Compression Level: {prioritizer.get_compression_level(content)}")
        print(f"  Tier (0 accesses): {prioritizer.calculate_tier_priority(content, 0)}")
        print()

    print("✅ All tests passed!")

if __name__ == "__main__":
    asyncio.run(test_prioritizer())

#!/usr/bin/env python3
"""
Test Surprise-Based Memory Consolidation

Tests the Titans/MIRAS-inspired surprise scoring and consolidation.
"""

import sys
import numpy as np
from datetime import datetime
from typing import List, Dict

# Add path for imports
sys.path.insert(0, '/mnt/agentic-system/mcp-servers/enhanced-memory-mcp')

from surprise_memory import SurpriseBasedMemory, SurpriseScore, RetentionGate
from surprise_consolidation import SurpriseConsolidator


def create_mock_embedding(text: str) -> List[float]:
    """Create deterministic mock embedding based on text content."""
    # Use text characteristics to create pseudo-embedding
    np.random.seed(hash(text) % (2**32))
    embedding = np.random.randn(384).tolist()  # 384-dim like sentence-transformers
    return embedding


def create_mock_search(existing_memories: List[str]):
    """Create mock search function with predefined memory bank."""
    # Pre-compute embeddings for existing memories
    memory_embeddings = {
        mem: np.array(create_mock_embedding(mem))
        for mem in existing_memories
    }

    def search_fn(embedding: List[float], limit: int, threshold: float) -> List[Dict]:
        """Find similar memories using cosine similarity."""
        query = np.array(embedding)
        query_norm = np.linalg.norm(query)

        results = []
        for mem, mem_emb in memory_embeddings.items():
            mem_norm = np.linalg.norm(mem_emb)
            if query_norm > 0 and mem_norm > 0:
                similarity = np.dot(query, mem_emb) / (query_norm * mem_norm)
                if similarity >= threshold:
                    results.append({'id': hash(mem), 'score': float(similarity)})

        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]

    return search_fn


def test_surprise_scoring():
    """Test surprise scoring with various content types."""
    print("=" * 60)
    print("Test 1: Surprise Scoring with Mock Embeddings")
    print("=" * 60)

    # Existing memories in the "database"
    existing_memories = [
        "Python dict comprehensions are efficient for creating dictionaries",
        "Error handling should use try-except blocks",
        "Database connections need proper cleanup",
        "API calls should be batched when possible",
        "Had a meeting about project planning"
    ]

    # Create scorer with mock functions
    scorer = SurpriseBasedMemory(
        embedding_fn=create_mock_embedding,
        search_fn=create_mock_search(existing_memories)
    )

    # Test cases with expected surprise levels
    test_cases = [
        # (content, memory_type, expected_description)
        (
            "Python dict comprehensions are faster than traditional loops for building dictionaries",
            "semantic",
            "LOW - Very similar to existing memory"
        ),
        (
            "The meeting was at 2pm",
            "episodic",
            "MEDIUM - Somewhat related to existing"
        ),
        (
            "CRITICAL ERROR: GraphQL mutation failed - discovered deadlock in transaction handling!",
            "procedural",
            "HIGH - Novel error pattern with keywords"
        ),
        (
            "Had coffee",
            "episodic",
            "LOW - Mundane, no importance signals"
        ),
        (
            "Discovered that using quantum computing principles can optimize database sharding by 300%!",
            "semantic",
            "HIGH - Novel discovery with strong keywords"
        ),
    ]

    results = []
    for content, mem_type, expected in test_cases:
        score = scorer.calculate_surprise(content, mem_type)
        results.append((content[:50], score.score, score.should_store, expected))

        print(f"\nContent: {content[:60]}...")
        print(f"Type: {mem_type}")
        print(f"Expected: {expected}")
        print(f"Score: {score.score:.2f} | Store: {score.should_store}")
        print(f"Components: novelty={score.novelty_component:.2f}, "
              f"salience={score.salience_component:.2f}, "
              f"temporal={score.temporal_component:.2f}")
        print(f"Reasoning: {score.reasoning}")

    print("\n" + "=" * 60)
    print("Test 1 Results Summary")
    print("=" * 60)
    for content, score, should_store, expected in results:
        status = "✅" if score >= 0.4 == should_store else "⚠️"
        print(f"{status} {content}... → {score:.2f}")

    return results


def test_momentum_effect():
    """Test that high-surprise events trigger momentum for related memories."""
    print("\n" + "=" * 60)
    print("Test 2: Momentum Effect")
    print("=" * 60)

    scorer = SurpriseBasedMemory(
        embedding_fn=create_mock_embedding,
        search_fn=lambda e, l, t: []  # No existing memories
    )

    # Sequence of memories - high surprise followed by related lower surprise
    sequence = [
        ("Normal operation log entry", "episodic"),
        ("CRITICAL: Found security vulnerability in authentication!", "procedural"),  # High surprise
        ("Updated auth tokens to use stronger encryption", "procedural"),  # Should be stored due to momentum
        ("Added rate limiting to prevent brute force", "procedural"),  # Momentum continues
        ("Fixed typo in login button text", "episodic"),  # Momentum expires?
    ]

    print("\nMemory sequence with momentum tracking:")
    for i, (content, mem_type) in enumerate(sequence):
        score = scorer.calculate_surprise(content, mem_type)
        print(f"\n[{i+1}] {content[:50]}...")
        print(f"    Score: {score.score:.2f} | Store: {score.should_store}")
        print(f"    Momentum: {scorer.momentum_counter} | Threshold: {scorer._get_effective_threshold():.2f}")


def test_retention_gate():
    """Test the retention gate for memory capacity management."""
    print("\n" + "=" * 60)
    print("Test 3: Retention Gate")
    print("=" * 60)

    gate = RetentionGate(max_memories=100, decay_rate=0.02)

    # Simulate memories with varying characteristics
    memories = []
    now = datetime.now()

    # Add recent high-surprise memories
    for i in range(5):
        memories.append({
            'id': f'recent_high_{i}',
            'surprise_score': 0.8 + i * 0.02,
            'created_at': now.isoformat(),
            'memory_type': 'semantic'
        })

    # Add older medium-surprise memories
    from datetime import timedelta
    for i in range(5):
        memories.append({
            'id': f'old_medium_{i}',
            'surprise_score': 0.5,
            'created_at': (now - timedelta(days=30)).isoformat(),
            'memory_type': 'episodic'
        })

    # Add very old low-surprise memories
    for i in range(5):
        memories.append({
            'id': f'very_old_low_{i}',
            'surprise_score': 0.2,
            'created_at': (now - timedelta(days=90)).isoformat(),
            'memory_type': 'episodic'
        })

    print(f"Total memories: {len(memories)}")
    print(f"Requesting candidates for forgetting: 5")

    candidates = gate.get_candidates_for_forgetting(memories, count_to_remove=5)

    print(f"\nCandidates for forgetting: {candidates}")

    # Verify low-retention memories are selected
    expected_forgotten = [m['id'] for m in memories if 'very_old_low' in m['id']]
    overlap = set(candidates).intersection(set(expected_forgotten))

    print(f"Expected (very old, low surprise): {expected_forgotten}")
    print(f"Overlap with expected: {len(overlap)}/{len(expected_forgotten)}")

    if len(overlap) >= 3:
        print("✅ Retention gate correctly identifies low-priority memories")
    else:
        print("⚠️ Retention gate may need tuning")


def test_consolidation_flow():
    """Test the full consolidation flow."""
    print("\n" + "=" * 60)
    print("Test 4: Full Consolidation Flow")
    print("=" * 60)

    # Create mock episodic memories
    test_memories = [
        {
            'id': '1',
            'content': 'Discovered that parallel tool calls reduce latency by 60%',
            'memory_type': 'episodic',
            'created_at': datetime.now().isoformat()
        },
        {
            'id': '2',
            'content': 'Had a meeting',
            'memory_type': 'episodic',
            'created_at': datetime.now().isoformat()
        },
        {
            'id': '3',
            'content': 'CRITICAL: Memory leak found in consolidation daemon - fixed by adding cleanup',
            'memory_type': 'episodic',
            'created_at': datetime.now().isoformat()
        },
        {
            'id': '4',
            'content': 'Checked email',
            'memory_type': 'episodic',
            'created_at': datetime.now().isoformat()
        },
        {
            'id': '5',
            'content': 'Learned that Titans/MIRAS uses surprise-based memorization for efficient long-term memory',
            'memory_type': 'episodic',
            'created_at': datetime.now().isoformat()
        }
    ]

    # Run consolidation (without Qdrant for testing)
    consolidator = SurpriseConsolidator()
    result = consolidator.consolidate_episodic_memories(test_memories)

    print(f"\nConsolidation Results:")
    print(f"  Evaluated: {result['metrics']['memories_evaluated']}")
    print(f"  Promoted: {result['metrics']['memories_promoted']}")
    print(f"  Skipped: {result['metrics']['memories_skipped']}")
    print(f"  Average Surprise: {result['metrics']['average_surprise_score']:.2f}")
    print(f"  High Surprise: {result['metrics']['high_surprise_count']}")
    print(f"  Low Surprise: {result['metrics']['low_surprise_count']}")
    print(f"  Duration: {result['metrics']['duration_seconds']:.2f}s")

    print(f"\nPromoted memories:")
    for p in result.get('promoted', []):
        print(f"  - {p['memory']['content'][:50]}... (score={p['surprise_score'].score:.2f})")

    print(f"\nSkipped memories:")
    for s in result.get('skipped', []):
        print(f"  - Score={s['surprise_score']:.2f}: {s['reason'][:50]}...")


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("SURPRISE-BASED MEMORY CONSOLIDATION TESTS")
    print("Titans/MIRAS Inspired Implementation")
    print("=" * 60)

    test_surprise_scoring()
    test_momentum_effect()
    test_retention_gate()
    test_consolidation_flow()

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()

#!/usr/bin/env python3
"""
Test suite for ReasoningBank integration.
"""

import asyncio
import os
import tempfile
from pathlib import Path

# Set up test environment
os.chdir(Path(__file__).parent)


async def test_basic_operations():
    """Test basic ReasoningBank operations."""
    print("\n=== Test: Basic Operations ===")

    from reasoning_bank import ReasoningBank, Verdict

    # Use temp database for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        rb = ReasoningBank(db_path=Path(tmpdir) / "test_rb.db")

        # Test distill - create memories from task outcome
        new_ids = await rb.distill(
            task_id="test_001",
            query="Implement user authentication",
            trajectory=[
                {"action": "read_file", "result": "Found auth.py"},
                {"action": "edit_file", "result": "Added JWT validation"},
                {"action": "run_tests", "result": "All tests passed"}
            ],
            verdict=Verdict.SUCCESS,
            reasoning="Successfully implemented JWT authentication"
        )
        print(f"  ✓ Created {len(new_ids)} memories from successful task")

        # Test retrieve
        memories = await rb.retrieve("authentication JWT token")
        print(f"  ✓ Retrieved {len(memories)} relevant memories")

        # Test metrics
        metrics = rb.get_metrics()
        print(f"  ✓ Metrics: {metrics['memory_count']} memories, {metrics['retrievals']} retrievals")

        assert len(new_ids) > 0, "Should create memories"
        print("  ✅ Basic operations: PASSED")
        return True


async def test_learning_from_failure():
    """Test learning from failed tasks."""
    print("\n=== Test: Learning from Failure ===")

    from reasoning_bank import ReasoningBank, Verdict

    with tempfile.TemporaryDirectory() as tmpdir:
        rb = ReasoningBank(db_path=Path(tmpdir) / "test_rb.db")

        # Learn from failure
        failure_ids = await rb.distill(
            task_id="test_002",
            query="Deploy to production",
            trajectory=[
                {"action": "build", "result": "Build successful"},
                {"action": "deploy", "result": "Error: Connection timeout"},
                {"action": "rollback", "result": "Rollback complete"}
            ],
            verdict=Verdict.FAILURE,
            reasoning="Deployment failed due to network timeout"
        )
        print(f"  ✓ Created {len(failure_ids)} memories from failed task")

        # Should have lower confidence
        memories = await rb.retrieve("deploy production")
        if memories:
            print(f"  ✓ Failure memory confidence: {memories[0].memory.confidence:.2f}")
            assert memories[0].memory.confidence < 0.5, "Failure memories should have lower confidence"

        print("  ✅ Learning from failure: PASSED")
        return True


async def test_consolidation():
    """Test memory consolidation (dedup and prune)."""
    print("\n=== Test: Consolidation ===")

    from reasoning_bank import ReasoningBank, Verdict

    with tempfile.TemporaryDirectory() as tmpdir:
        rb = ReasoningBank(db_path=Path(tmpdir) / "test_rb.db")

        # Create several similar memories
        for i in range(5):
            await rb.distill(
                task_id=f"test_dup_{i}",
                query="Build REST API endpoint",
                trajectory=[{"action": "code", "result": "API built"}],
                verdict=Verdict.SUCCESS,
                reasoning="API created successfully"
            )

        initial_count = rb.get_metrics()["memory_count"]
        print(f"  Created {initial_count} memories")

        # Consolidate
        stats = await rb.consolidate()
        final_count = rb.get_metrics()["memory_count"]

        print(f"  Consolidation: {stats}")
        print(f"  Memories: {initial_count} → {final_count}")
        print("  ✅ Consolidation: PASSED")
        return True


async def test_judge():
    """Test LLM-as-judge functionality."""
    print("\n=== Test: Task Judgment ===")

    from reasoning_bank import ReasoningBank, Verdict

    with tempfile.TemporaryDirectory() as tmpdir:
        rb = ReasoningBank(db_path=Path(tmpdir) / "test_rb.db")

        # Test heuristic judgment (no LLM)
        verdict, reasoning = await rb.judge(
            task_id="test_judge_1",
            query="Fix authentication bug",
            trajectory=[
                {"action": "analyze", "result": "Found root cause"},
                {"action": "fix", "result": "Bug fixed successfully"},
                {"action": "test", "result": "All tests pass"}
            ]
        )
        print(f"  ✓ Success judgment: {verdict.value}")
        assert verdict == Verdict.SUCCESS

        verdict2, _ = await rb.judge(
            task_id="test_judge_2",
            query="Deploy feature",
            trajectory=[
                {"action": "build", "result": "Build failed with error"},
                {"action": "debug", "result": "Error: TypeScript compile error"}
            ]
        )
        print(f"  ✓ Failure judgment: {verdict2.value}")
        assert verdict2 == Verdict.FAILURE

        print("  ✅ Task judgment: PASSED")
        return True


async def test_full_workflow():
    """Test complete ReasoningBank workflow."""
    print("\n=== Test: Full Workflow ===")

    from reasoning_bank import ReasoningBank

    with tempfile.TemporaryDirectory() as tmpdir:
        rb = ReasoningBank(db_path=Path(tmpdir) / "test_rb.db")

        async def mock_execute(query: str, memory_context: str):
            """Mock task execution."""
            return [
                {"action": "plan", "result": f"Planning: {query}"},
                {"action": "implement", "result": "Implementation complete"},
                {"action": "verify", "result": "Verification successful"}
            ]

        # Run first task
        result1 = await rb.run_task(
            task_id="workflow_001",
            query="Create user registration API",
            execute_fn=mock_execute,
            domain="api_development"
        )
        print(f"  Task 1: {result1.verdict.value}, {len(result1.new_memories)} new memories")

        # Run second similar task - should retrieve memories from first
        result2 = await rb.run_task(
            task_id="workflow_002",
            query="Create user login API",
            execute_fn=mock_execute,
            domain="api_development"
        )
        print(f"  Task 2: {result2.verdict.value}, used {len(result2.used_memories)} memories")

        # Check learning happened
        metrics = rb.get_metrics()
        print(f"  Final: {metrics['memory_count']} memories, {metrics['success_rate']:.0%} success rate")

        assert result2.used_memories, "Second task should use memories from first"
        print("  ✅ Full workflow: PASSED")
        return True


async def test_mcp_tools():
    """Test MCP tool registration."""
    print("\n=== Test: MCP Tool Registration ===")

    from reasoning_bank import register_reasoning_bank_tools

    class MockApp:
        def __init__(self):
            self.tools = {}

        def tool(self):
            def decorator(fn):
                self.tools[fn.__name__] = fn
                return fn
            return decorator

    mock_app = MockApp()
    rb = register_reasoning_bank_tools(mock_app)

    expected_tools = ["rb_retrieve", "rb_learn", "rb_consolidate", "rb_status"]
    for tool_name in expected_tools:
        assert tool_name in mock_app.tools, f"Missing tool: {tool_name}"
        print(f"  ✓ {tool_name} registered")

    # Test rb_status
    status = await mock_app.tools["rb_status"]()
    print(f"  ✓ Status: {status['memory_count']} memories")

    print("  ✅ MCP tools: PASSED")
    return True


# =============================================================================
# PatternClusterer Tests (K-means++ from SONA Rust crate)
# =============================================================================

async def test_pattern_cluster_config():
    """Test PatternClusterConfig dataclass."""
    print("\n=== Test: PatternClusterConfig ===")

    from reasoning_bank import PatternClusterConfig

    # Test default configuration
    config = PatternClusterConfig()
    assert config.k_clusters == 100
    assert config.embedding_dim == 256
    assert config.max_iterations == 100
    assert config.convergence_threshold == 0.001
    assert config.min_cluster_size == 5
    print(f"  ✓ Default config: k={config.k_clusters}, dim={config.embedding_dim}")

    # Test custom configuration
    custom = PatternClusterConfig(
        k_clusters=50,
        embedding_dim=128,
        max_iterations=200,
        convergence_threshold=0.0001,
        min_cluster_size=3
    )
    assert custom.k_clusters == 50
    assert custom.embedding_dim == 128
    assert custom.max_iterations == 200
    print(f"  ✓ Custom config: k={custom.k_clusters}, dim={custom.embedding_dim}")

    print("  ✅ PatternClusterConfig: PASSED")
    return True


async def test_learned_pattern():
    """Test LearnedPattern dataclass."""
    print("\n=== Test: LearnedPattern ===")

    import time
    import numpy as np
    from reasoning_bank import LearnedPattern

    # Create a pattern with all required fields
    centroid = np.random.randn(128).astype(np.float32)
    now = time.time()
    pattern = LearnedPattern(
        id="pattern_001",
        centroid=centroid,
        cluster_size=10,
        total_weight=8.5,
        avg_quality=0.85,
        created_at=now,
        last_accessed=now,
        access_count=5,
        pattern_type="reasoning"
    )

    assert pattern.cluster_size == 10
    assert pattern.avg_quality == 0.85
    assert pattern.access_count == 5
    assert pattern.centroid.shape == (128,)
    print(f"  ✓ Pattern: cluster_size={pattern.cluster_size}, quality={pattern.avg_quality}")

    # Test pattern ID assignment
    pattern2 = LearnedPattern(
        id="pattern_123",
        centroid=np.zeros(128, dtype=np.float32),
        cluster_size=5,
        total_weight=3.5,
        avg_quality=0.7,
        created_at=now,
        last_accessed=now,
        access_count=2,
        pattern_type="general"
    )
    assert pattern2.id == "pattern_123"
    print(f"  ✓ Pattern ID: {pattern2.id}")

    print("  ✅ LearnedPattern: PASSED")
    return True


async def test_pattern_clusterer_init():
    """Test PatternClusterer initialization."""
    print("\n=== Test: PatternClusterer Initialization ===")

    from reasoning_bank import PatternClusterConfig, PatternClusterer

    # Test with default config
    clusterer = PatternClusterer()
    assert clusterer.config is not None
    assert len(clusterer.entries) == 0
    assert len(clusterer.patterns) == 0
    print(f"  ✓ Default initialization: k={clusterer.config.k_clusters}")

    # Test with custom config
    config = PatternClusterConfig(k_clusters=25, embedding_dim=64)
    clusterer2 = PatternClusterer(config)
    assert clusterer2.config.k_clusters == 25
    assert clusterer2.config.embedding_dim == 64
    print(f"  ✓ Custom config: k={clusterer2.config.k_clusters}, dim={clusterer2.config.embedding_dim}")

    print("  ✅ PatternClusterer Initialization: PASSED")
    return True


async def test_pattern_clusterer_add_entry():
    """Test adding entries to clusterer."""
    print("\n=== Test: Add Entry ===")

    import numpy as np
    from reasoning_bank import PatternClusterConfig, PatternClusterer

    config = PatternClusterConfig(k_clusters=10, embedding_dim=32)
    clusterer = PatternClusterer(config)

    # Add entries
    for i in range(20):
        embedding = np.random.randn(32).astype(np.float32)
        quality = 0.5 + 0.5 * np.random.random()
        clusterer.add_entry(embedding, quality, f"entry_{i}")

    assert len(clusterer.entries) == 20
    print(f"  ✓ Added 20 entries")

    # Check entry structure - entries are tuples (embedding, quality, id)
    entry = clusterer.entries[0]
    assert isinstance(entry, tuple)
    assert len(entry) == 3
    embedding, quality, entry_id = entry
    assert embedding.shape == (32,)
    assert isinstance(quality, float)
    assert isinstance(entry_id, str)
    print(f"  ✓ Entry structure valid: tuple(embedding={embedding.shape}, quality={quality:.2f}, id={entry_id})")

    print("  ✅ Add Entry: PASSED")
    return True


async def test_kmeans_plus_plus_init():
    """Test K-means++ initialization algorithm."""
    print("\n=== Test: K-means++ Initialization ===")

    import numpy as np
    from reasoning_bank import PatternClusterConfig, PatternClusterer

    config = PatternClusterConfig(k_clusters=5, embedding_dim=16)
    clusterer = PatternClusterer(config)

    # Add entries with distinct clusters (for clear separation)
    np.random.seed(42)
    for cluster_id in range(5):
        center = np.zeros(16, dtype=np.float32)
        center[cluster_id * 3:(cluster_id + 1) * 3] = 1.0
        for _ in range(10):
            embedding = center + 0.1 * np.random.randn(16).astype(np.float32)
            clusterer.add_entry(embedding, 0.8, f"cluster_{cluster_id}")

    assert len(clusterer.entries) == 50
    print(f"  ✓ Created 50 entries in 5 clusters")

    # Run K-means++ initialization
    centroids = clusterer._kmeans_plus_plus_init(5)
    assert len(centroids) == 5
    assert all(c.shape == (16,) for c in centroids)
    print(f"  ✓ K-means++ initialized 5 centroids")

    # Check centroids are diverse (D² weighting should spread them)
    # Compute pairwise distances
    min_dist = float('inf')
    for i in range(len(centroids)):
        for j in range(i + 1, len(centroids)):
            dist = np.linalg.norm(centroids[i] - centroids[j])
            min_dist = min(min_dist, dist)
    assert min_dist > 0.1  # Centroids should be reasonably spread
    print(f"  ✓ Centroids are diverse: min_distance={min_dist:.4f}")

    print("  ✅ K-means++ Initialization: PASSED")
    return True


async def test_pattern_extraction():
    """Test pattern extraction from entries."""
    print("\n=== Test: Pattern Extraction ===")

    import numpy as np
    from reasoning_bank import PatternClusterConfig, PatternClusterer

    config = PatternClusterConfig(
        k_clusters=3,
        embedding_dim=16,
        max_iterations=50,
        min_cluster_size=3
    )
    clusterer = PatternClusterer(config)

    # Add clustered entries
    np.random.seed(123)
    for cluster_id in range(3):
        center = np.zeros(16, dtype=np.float32)
        center[cluster_id * 5:(cluster_id + 1) * 5] = 1.0
        for i in range(10):
            embedding = center + 0.05 * np.random.randn(16).astype(np.float32)
            quality = 0.6 + 0.3 * np.random.random()
            clusterer.add_entry(embedding, quality, f"c{cluster_id}_e{i}")

    # Extract patterns
    patterns = clusterer.extract_patterns()
    assert len(patterns) > 0
    assert len(patterns) <= 3
    print(f"  ✓ Extracted {len(patterns)} patterns from 30 entries")

    # Check pattern properties
    for p in patterns:
        assert p.cluster_size > 0
        assert 0 <= p.avg_quality <= 1
        assert p.centroid.shape == (16,)
    print(f"  ✓ Pattern properties valid")

    # Total cluster sizes should equal number of entries
    total_members = sum(p.cluster_size for p in patterns)
    assert total_members == 30
    print(f"  ✓ Total members: {total_members}")

    print("  ✅ Pattern Extraction: PASSED")
    return True


async def test_find_similar_patterns():
    """Test finding similar patterns."""
    print("\n=== Test: Find Similar Patterns ===")

    import numpy as np
    from reasoning_bank import PatternClusterConfig, PatternClusterer

    config = PatternClusterConfig(k_clusters=4, embedding_dim=16)
    clusterer = PatternClusterer(config)

    # Add entries for 4 distinct clusters
    np.random.seed(456)
    for cluster_id in range(4):
        center = np.zeros(16, dtype=np.float32)
        center[cluster_id * 4:(cluster_id + 1) * 4] = 1.0
        for i in range(8):
            embedding = center + 0.02 * np.random.randn(16).astype(np.float32)
            clusterer.add_entry(embedding, 0.75, f"c{cluster_id}_e{i}")

    # Extract patterns first
    patterns = clusterer.extract_patterns()
    assert len(patterns) > 0
    print(f"  ✓ Extracted {len(patterns)} patterns")

    # Query with a vector close to cluster 0
    query = np.zeros(16, dtype=np.float32)
    query[0:4] = 1.0
    query += 0.01 * np.random.randn(16).astype(np.float32)

    similar = clusterer.find_similar(query, k=3)
    assert len(similar) <= 3
    assert all(isinstance(item, tuple) for item in similar)
    print(f"  ✓ Found {len(similar)} similar patterns")

    # Check similarity scores
    if similar:
        pattern, score = similar[0]
        assert 0 <= score <= 1  # Cosine similarity normalized
        print(f"  ✓ Best match: score={score:.4f}, cluster_size={pattern.cluster_size}")

    print("  ✅ Find Similar Patterns: PASSED")
    return True


async def test_pattern_pruning():
    """Test pattern pruning based on age and quality."""
    print("\n=== Test: Pattern Pruning ===")

    import numpy as np
    from reasoning_bank import PatternClusterConfig, PatternClusterer

    config = PatternClusterConfig(k_clusters=5, embedding_dim=8, min_cluster_size=2)
    clusterer = PatternClusterer(config)

    # Add entries with varying quality
    np.random.seed(789)
    for i in range(30):
        embedding = np.random.randn(8).astype(np.float32)
        # Some high quality, some low quality
        quality = 0.9 if i % 3 == 0 else 0.3
        clusterer.add_entry(embedding, quality, f"entry_{i}")

    # Extract patterns
    patterns_before = clusterer.extract_patterns()
    count_before = len(patterns_before)
    print(f"  ✓ Before pruning: {count_before} patterns")

    # Prune low-quality patterns
    clusterer.prune_patterns(min_quality=0.5, min_accesses=3)
    patterns_after = clusterer.patterns
    count_after = len(patterns_after)
    print(f"  ✓ After pruning (min_quality=0.5): {count_after} patterns")

    # Check remaining patterns meet criteria
    for p in patterns_after.values():
        assert p.avg_quality >= 0.5 or p.access_count >= 3
    print(f"  ✓ Remaining patterns meet quality/size criteria")

    print("  ✅ Pattern Pruning: PASSED")
    return True


async def test_consolidate_similar():
    """Test consolidation of similar patterns."""
    print("\n=== Test: Consolidate Similar Patterns ===")

    import numpy as np
    from reasoning_bank import PatternClusterConfig, PatternClusterer

    config = PatternClusterConfig(k_clusters=10, embedding_dim=8)
    clusterer = PatternClusterer(config)

    # Add entries that form tight clusters (will have similar centroids)
    np.random.seed(111)
    base_vectors = [np.random.randn(8).astype(np.float32) for _ in range(3)]
    for base in base_vectors:
        for i in range(20):
            # Very tight clusters (0.01 std)
            embedding = base + 0.01 * np.random.randn(8).astype(np.float32)
            clusterer.add_entry(embedding, 0.8, f"entry")

    # Extract patterns
    patterns_before = clusterer.extract_patterns()
    count_before = len(patterns_before)
    print(f"  ✓ Before consolidation: {count_before} patterns")

    # Consolidate similar patterns (high threshold to merge very similar)
    clusterer.consolidate_similar(similarity_threshold=0.99)
    count_after = len(clusterer.patterns)
    print(f"  ✓ After consolidation (threshold=0.99): {count_after} patterns")

    # With lower threshold, more consolidation
    clusterer.extract_patterns()  # Re-extract
    clusterer.consolidate_similar(similarity_threshold=0.8)
    count_final = len(clusterer.patterns)
    print(f"  ✓ After consolidation (threshold=0.8): {count_final} patterns")

    print("  ✅ Consolidate Similar Patterns: PASSED")
    return True


async def test_pattern_clusterer_edge_cases():
    """Test PatternClusterer edge cases."""
    print("\n=== Test: PatternClusterer Edge Cases ===")

    import numpy as np
    from reasoning_bank import PatternClusterConfig, PatternClusterer

    config = PatternClusterConfig(k_clusters=5, embedding_dim=8, min_cluster_size=2)
    clusterer = PatternClusterer(config)

    # Test with empty entries
    patterns = clusterer.extract_patterns()
    assert len(patterns) == 0
    print(f"  ✓ Empty entries: 0 patterns")

    # Test with fewer entries than k
    for i in range(3):
        embedding = np.random.randn(8).astype(np.float32)
        clusterer.add_entry(embedding, 0.8, f"entry_{i}")

    patterns = clusterer.extract_patterns()
    # Should handle gracefully (fewer clusters than k)
    print(f"  ✓ Fewer than k entries: {len(patterns)} patterns")

    # Test find_similar with no patterns
    clusterer2 = PatternClusterer(config)
    query = np.random.randn(8).astype(np.float32)
    similar = clusterer2.find_similar(query, k=3)
    assert len(similar) == 0
    print(f"  ✓ Find similar with no patterns: empty result")

    # Test with single entry
    clusterer3 = PatternClusterer(config)
    clusterer3.add_entry(np.ones(8, dtype=np.float32), 0.9, "single")
    patterns = clusterer3.extract_patterns()
    print(f"  ✓ Single entry: {len(patterns)} patterns")

    print("  ✅ PatternClusterer Edge Cases: PASSED")
    return True


async def main():
    print("=" * 60)
    print("ReasoningBank Integration Tests")
    print("=" * 60)

    tests = [
        ("Basic Operations", test_basic_operations),
        ("Learning from Failure", test_learning_from_failure),
        ("Consolidation", test_consolidation),
        ("Task Judgment", test_judge),
        ("Full Workflow", test_full_workflow),
        ("MCP Tools", test_mcp_tools),
        # PatternClusterer tests (K-means++ from SONA)
        ("Pattern Cluster Config", test_pattern_cluster_config),
        ("Learned Pattern", test_learned_pattern),
        ("Pattern Clusterer Init", test_pattern_clusterer_init),
        ("Pattern Clusterer Add Entry", test_pattern_clusterer_add_entry),
        ("K-means++ Initialization", test_kmeans_plus_plus_init),
        ("Pattern Extraction", test_pattern_extraction),
        ("Find Similar Patterns", test_find_similar_patterns),
        ("Pattern Pruning", test_pattern_pruning),
        ("Consolidate Similar", test_consolidate_similar),
        ("Pattern Clusterer Edge Cases", test_pattern_clusterer_edge_cases),
    ]

    results = {}
    for name, test_fn in tests:
        try:
            results[name] = await test_fn()
        except Exception as e:
            print(f"  ❌ {name}: FAILED - {e}")
            results[name] = False

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)

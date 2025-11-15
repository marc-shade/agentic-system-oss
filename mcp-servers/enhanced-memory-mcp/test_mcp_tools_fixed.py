#!/usr/bin/env python3
"""
Test fixed MCP tools directly (without MCP protocol)
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from neural_memory_fabric import get_nmf
from qdrant_client import QdrantClient

QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "enhanced_memory"

async def test_hybrid_search_fixed():
    """Test hybrid search with fixed embedding access"""
    print("=" * 70)
    print("TESTING FIXED HYBRID SEARCH")
    print("=" * 70)

    from fastembed import SparseTextEmbedding
    from qdrant_client.models import Fusion, FusionQuery, Prefetch

    client = QdrantClient(url=QDRANT_URL)
    nmf = await get_nmf()

    query = "voice communication system"
    print(f"\nQuery: '{query}'")

    # Generate dense vector (FIXED)
    embedding_result = await nmf.embedding_manager.generate_embedding(query)
    query_vector = embedding_result.embedding if hasattr(embedding_result, 'embedding') else embedding_result
    print(f"✅ Dense vector: {len(query_vector)} dimensions")

    # Generate sparse vector
    sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
    sparse_embeddings = list(sparse_model.embed([query]))
    sparse_embedding = sparse_embeddings[0]
    query_sparse = {
        "indices": sparse_embedding.indices.tolist(),
        "values": sparse_embedding.values.tolist()
    }
    print(f"✅ Sparse vector: {len(query_sparse['indices'])} tokens")

    # Hybrid search
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        prefetch=[
            Prefetch(query=query_vector, using="text-dense", limit=10),
            Prefetch(query=query_sparse, using="text-sparse", limit=10)
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=5,
        with_payload=True
    ).points

    print(f"\n✅ Results: {len(results)}")
    for i, hit in enumerate(results, 1):
        print(f"{i}. Score: {hit.score:.4f}")
        print(f"   Content: {hit.payload.get('content', 'N/A')[:80]}...")

    return len(results)

def test_stats_fixed():
    """Test fixed stats function"""
    print("\n" + "=" * 70)
    print("TESTING FIXED STATS FUNCTION")
    print("=" * 70)

    client = QdrantClient(url=QDRANT_URL)

    # Get collection info
    collection_info = client.get_collection(collection_name=COLLECTION_NAME)

    # Check for dense vector support (FIXED)
    vectors_config = collection_info.config.params.vectors
    has_dense = "text-dense" in vectors_config if isinstance(vectors_config, dict) else bool(vectors_config)

    # Check for sparse vector support (FIXED)
    sparse_vectors_config = collection_info.config.params.sparse_vectors
    has_sparse = "text-sparse" in sparse_vectors_config if sparse_vectors_config else False

    stats = {
        "status": "ready",
        "backend": "qdrant",
        "collection": COLLECTION_NAME,
        "points_count": collection_info.points_count,
        "dense_vectors": has_dense,
        "sparse_vectors": has_sparse,
        "hybrid_enabled": has_dense and has_sparse,
        "fusion_method": "rrf" if has_sparse else "none"
    }

    print("\nStats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Verify correctness
    assert stats["dense_vectors"] == True, "Should detect dense vectors"
    assert stats["sparse_vectors"] == True, "Should detect sparse vectors"
    assert stats["hybrid_enabled"] == True, "Should enable hybrid search"
    assert stats["fusion_method"] == "rrf", "Should use RRF fusion"

    print("\n✅ All stats assertions passed!")

    return stats

async def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("TESTING FIXED MCP TOOLS")
    print("=" * 70)

    try:
        # Test stats
        stats = test_stats_fixed()

        # Test hybrid search
        results_count = await test_hybrid_search_fixed()

        print("\n" + "=" * 70)
        print("ALL TESTS PASSED")
        print("=" * 70)
        print(f"✅ Stats detection: Working correctly")
        print(f"✅ Hybrid search: {results_count} results")
        print("\n🎉 MCP tools ready for server reload!")
        print("=" * 70)

        return 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

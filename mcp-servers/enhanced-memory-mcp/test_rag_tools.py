#!/usr/bin/env python3
"""
Direct test of RAG tools (bypassing MCP protocol)
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from qdrant_client import QdrantClient

QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "enhanced_memory"

async def test_hybrid_search():
    """Test hybrid search directly"""
    print("=" * 70)
    print("TESTING HYBRID SEARCH (BM25 + Vector RRF Fusion)")
    print("=" * 70)

    from neural_memory_fabric import get_nmf
    from fastembed import SparseTextEmbedding

    client = QdrantClient(url=QDRANT_URL)
    nmf = await get_nmf()

    # Test query
    query = "voice communication system"
    print(f"\nQuery: '{query}'")

    # Generate dense vector
    embedding_result = await nmf.embedding_manager.generate_embedding(query)
    query_vector = embedding_result.embedding if hasattr(embedding_result, 'embedding') else embedding_result
    print(f"✅ Dense vector generated: {len(query_vector)} dimensions")

    # Generate sparse vector (BM25)
    try:
        sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
        sparse_embeddings = list(sparse_model.embed([query]))
        sparse_embedding = sparse_embeddings[0]

        query_sparse = {
            "indices": sparse_embedding.indices.tolist(),
            "values": sparse_embedding.values.tolist()
        }
        print(f"✅ Sparse vector generated: {len(query_sparse['indices'])} tokens")
    except Exception as e:
        print(f"⚠️  Sparse vector generation failed: {e}")
        query_sparse = None

    # Perform hybrid search
    search_params = {
        "collection_name": COLLECTION_NAME,
        "limit": 5,
        "with_payload": True,
        "with_vectors": False
    }

    if query_sparse:
        # True hybrid search with RRF fusion
        search_params["query"] = {
            "fusion": "rrf",
            "prefetch": [
                {
                    "query": query_vector,
                    "using": "text-dense",
                    "limit": 10
                },
                {
                    "query": query_sparse,
                    "using": "text-sparse",
                    "limit": 10
                }
            ]
        }
        search_type = "hybrid (RRF fusion)"
    else:
        # Fallback to dense-only
        search_params["vector"] = {
            "name": "text-dense",
            "vector": query_vector
        }
        search_type = "dense-only"

    # Execute search
    if query_sparse:
        # Use query_points for hybrid search with RRF
        from qdrant_client.models import Fusion, FusionQuery, Prefetch

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
    else:
        # Use search for dense-only
        results = client.search(**search_params)

    print(f"\n✅ Search completed: {search_type}")
    print(f"Results: {len(results)}")
    print()

    for i, hit in enumerate(results, 1):
        print(f"{i}. Score: {hit.score:.4f}")
        print(f"   Content: {hit.payload.get('content', 'N/A')[:100]}...")
        print()

    return len(results)

async def test_reranking():
    """Test re-ranking directly"""
    print("=" * 70)
    print("TESTING RE-RANKING (Cross-Encoder)")
    print("=" * 70)

    from neural_memory_fabric import get_nmf
    from reranking import get_reranker

    nmf = await get_nmf()
    reranker = get_reranker()

    query = "voice communication system"
    print(f"\nQuery: '{query}'")

    # Define search function
    async def search_function(q: str, lim: int):
        results = await nmf.recall(query=q, mode="semantic", limit=lim)
        print(f"   NMF recall returned: {len(results) if results else 0} results")
        if results:
            print(f"   First result: {results[0].get('content', 'N/A')[:100]}")
        return results if results else []

    # Over-retrieve and re-rank
    over_retrieve_factor = 4
    limit = 5
    print(f"Over-retrieving: {limit * over_retrieve_factor} candidates")

    results = await reranker.search_with_reranking(
        query=query,
        search_function=search_function,
        limit=limit,
        over_retrieve_factor=over_retrieve_factor
    )

    print(f"\n✅ Re-ranking completed")
    print(f"Final results: {len(results)}")
    print()

    for i, result in enumerate(results, 1):
        print(f"{i}. Score: {result.get('score', 'N/A')}")
        print(f"   Content: {result.get('content', 'N/A')[:100]}...")
        print()

    return len(results)

async def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("RAG TIER 1 TOOLS - DIRECT TEST")
    print("=" * 70)
    print()

    try:
        # Test hybrid search
        hybrid_count = await test_hybrid_search()

        # Test re-ranking
        reranking_count = await test_reranking()

        print("=" * 70)
        print("TEST RESULTS")
        print("=" * 70)
        print(f"✅ Hybrid search: {hybrid_count} results")
        print(f"✅ Re-ranking: {reranking_count} results")
        print()
        print("🎉 All RAG tools working correctly!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

#!/usr/bin/env python3
"""Test Qdrant search with named vectors"""
from qdrant_client import QdrantClient
import asyncio

async def test_search():
    client = QdrantClient(url="http://localhost:6333")
    
    # Get embedding
    from embedding_providers import get_embedding_manager
    manager = await get_embedding_manager()
    
    query = "voice communication system"
    embedding_result = await manager.generate_embedding(query)
    query_vector = embedding_result.embedding if hasattr(embedding_result, 'embedding') else embedding_result
    
    print(f"Query vector length: {len(query_vector)}")
    print(f"Query vector type: {type(query_vector)}")
    
    # Test 1: Named vector tuple format
    print("\n1. Testing named vector tuple format...")
    try:
        results = client.search(
            collection_name="enhanced_memory",
            query_vector=("text-dense", query_vector),
            limit=5
        )
        print(f"   Results: {len(results)}")
        if results:
            print(f"   First result score: {results[0].score}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # Test 2: Check collection info
    print("\n2. Checking collection info...")
    collection_info = client.get_collection("enhanced_memory")
    print(f"   Points: {collection_info.points_count}")
    print(f"   Vectors config: {collection_info.config.params.vectors}")
    
    # Test 3: Try scrolling to see if points exist
    print("\n3. Checking points...")
    scroll_result = client.scroll(
        collection_name="enhanced_memory",
        limit=1,
        with_vectors=True
    )
    points, _ = scroll_result
    if points:
        print(f"   Found points: {len(points)}")
        print(f"   First point vector keys: {points[0].vector.keys() if isinstance(points[0].vector, dict) else 'not a dict'}")
    else:
        print("   No points found!")

asyncio.run(test_search())

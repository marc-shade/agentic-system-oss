#!/usr/bin/env python3
"""Simple Qdrant search test"""
from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")

# Check collection info
print("Collection info:")
collection_info = client.get_collection("enhanced_memory")
print(f"  Points: {collection_info.points_count}")
print(f"  Vectors config: {collection_info.config.params.vectors}")
print()

# Check if points have vectors
print("Checking first point:")
scroll_result = client.scroll(
    collection_name="enhanced_memory",
    limit=1,
    with_vectors=True,
    with_payload=True
)
points, _ = scroll_result
if points:
    point = points[0]
    print(f"  Point ID: {point.id}")
    print(f"  Vector type: {type(point.vector)}")
    if isinstance(point.vector, dict):
        print(f"  Vector keys: {list(point.vector.keys())}")
        for key in point.vector.keys():
            vec = point.vector[key]
            if vec:
                vec_len = len(vec) if hasattr(vec, '__len__') else 'N/A'
                print(f"    {key}: length {vec_len}")
    print(f"  Content: {point.payload.get('content', 'N/A')[:100]}")
else:
    print("  No points found!")

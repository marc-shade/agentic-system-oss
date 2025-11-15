#!/usr/bin/env python3
"""
Enable hybrid search (BM25 + Vector) in Qdrant collections.

Updates existing Qdrant collections to support hybrid search by adding
sparse vector configurations alongside existing dense vectors.

Part of RAG Tier 1 Strategy - Week 1, Day 3-4
Expected improvement: +20-30% recall with minimal latency overhead
"""

import sys
import requests
import json
from typing import List, Dict, Any

# Qdrant configuration
QDRANT_URL = "http://localhost:6333"

# Collections to enable hybrid search on
COLLECTIONS = [
    "enhanced_memory",
    "working_memory",
    "semantic_memory",
    "episodic_memory",
    "procedural_memory"
]

def check_collection_exists(collection_name: str) -> bool:
    """Check if a collection exists."""
    try:
        response = requests.get(f"{QDRANT_URL}/collections/{collection_name}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error checking collection {collection_name}: {e}")
        return False

def get_collection_info(collection_name: str) -> Dict[str, Any]:
    """Get collection configuration."""
    try:
        response = requests.get(f"{QDRANT_URL}/collections/{collection_name}")
        if response.status_code == 200:
            return response.json()
        return {}
    except Exception as e:
        print(f"Error getting collection info for {collection_name}: {e}")
        return {}

def has_sparse_vectors(collection_name: str) -> bool:
    """Check if collection already has sparse vectors configured."""
    info = get_collection_info(collection_name)
    if not info:
        return False

    config = info.get("result", {}).get("config", {})
    params = config.get("params", {})

    # Check for sparse_vectors in params
    return "sparse_vectors" in params

def enable_sparse_vectors(collection_name: str) -> bool:
    """
    Enable sparse vectors for a collection.

    Note: Qdrant allows adding sparse vectors to existing collections
    without data loss. Existing points will need to be re-indexed with
    sparse vectors, but dense vectors remain intact.
    """
    print(f"\nEnabling sparse vectors for: {collection_name}")

    # Check if already has sparse vectors
    if has_sparse_vectors(collection_name):
        print(f"  ✅ Collection already has sparse vectors enabled")
        return True

    # Get current collection info
    info = get_collection_info(collection_name)
    if not info:
        print(f"  ❌ Could not get collection info")
        return False

    points_count = info.get("result", {}).get("points_count", 0)
    print(f"  Current points: {points_count}")

    # Update collection to add sparse vectors
    # Qdrant API: PATCH /collections/{collection_name}
    update_payload = {
        "sparse_vectors": {
            "text": {}  # BM25-style sparse vectors for text
        }
    }

    try:
        response = requests.patch(
            f"{QDRANT_URL}/collections/{collection_name}",
            json=update_payload,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            print(f"  ✅ Sparse vectors enabled successfully")
            print(f"  Note: Existing {points_count} points will need sparse vector updates")
            return True
        else:
            print(f"  ❌ Failed to enable sparse vectors")
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.text}")
            return False

    except Exception as e:
        print(f"  ❌ Error enabling sparse vectors: {e}")
        return False

def verify_hybrid_search(collection_name: str) -> bool:
    """Verify that hybrid search is working."""
    info = get_collection_info(collection_name)
    if not info:
        return False

    config = info.get("result", {}).get("config", {})
    params = config.get("params", {})

    has_dense = "vectors" in params
    has_sparse = "sparse_vectors" in params

    print(f"\n  Verification for {collection_name}:")
    print(f"    Dense vectors: {'✅' if has_dense else '❌'}")
    print(f"    Sparse vectors: {'✅' if has_sparse else '❌'}")
    print(f"    Hybrid search ready: {'✅' if (has_dense and has_sparse) else '❌'}")

    return has_dense and has_sparse

def main():
    """Main execution."""
    print("=" * 60)
    print("Qdrant Hybrid Search Enablement")
    print("RAG Tier 1 Strategy - Week 1, Day 3-4")
    print("=" * 60)

    # Check Qdrant health
    try:
        response = requests.get(f"{QDRANT_URL}/healthz")
        if response.status_code != 200:
            print("❌ Qdrant is not healthy")
            sys.exit(1)
        print("✅ Qdrant is healthy\n")
    except Exception as e:
        print(f"❌ Cannot connect to Qdrant: {e}")
        sys.exit(1)

    # Process each collection
    results = {}
    for collection in COLLECTIONS:
        if not check_collection_exists(collection):
            print(f"⚠️  Collection '{collection}' does not exist, skipping")
            results[collection] = "skipped"
            continue

        success = enable_sparse_vectors(collection)
        results[collection] = "success" if success else "failed"

    # Verify all collections
    print("\n" + "=" * 60)
    print("Verification Results")
    print("=" * 60)

    all_verified = True
    for collection in COLLECTIONS:
        if results.get(collection) == "skipped":
            continue
        if not verify_hybrid_search(collection):
            all_verified = False

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    for collection, result in results.items():
        status_icon = {
            "success": "✅",
            "failed": "❌",
            "skipped": "⚠️"
        }.get(result, "❓")
        print(f"  {status_icon} {collection}: {result}")

    if all_verified:
        print("\n✅ Hybrid search successfully enabled on all collections!")
        print("\nNext steps:")
        print("  1. Update existing points with sparse vectors")
        print("  2. Use hybrid search in queries (combine dense + sparse)")
        print("  3. Expected improvement: +20-30% recall")
        sys.exit(0)
    else:
        print("\n⚠️  Some collections may need manual intervention")
        sys.exit(1)

if __name__ == "__main__":
    main()

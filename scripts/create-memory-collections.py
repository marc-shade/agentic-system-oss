#!/usr/bin/env python3
"""
Create Qdrant Collections for SAFLA Memory Types

Creates optimized vector collections for:
- Enhanced Memory (general memories)
- Working Memory (active context, short-term)
- Episodic Memory (experiences and events)
- Semantic Memory (concepts and relationships)
- Procedural Memory (skills and patterns)
"""

import sys
from pathlib import Path

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
except ImportError:
    print("❌ qdrant-client not installed")
    print("   Install with: pip install qdrant-client")
    sys.exit(1)

# Qdrant configuration
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333

# Vector dimensions for different embedding models
# Google text-embedding-004, OpenAI text-embedding-3-small
VECTOR_DIM = 768

def create_collection(client, collection_name, vector_dim, distance=Distance.COSINE):
    """Create a Qdrant collection with specified parameters"""
    try:
        # Check if collection already exists
        collections = client.get_collections()
        existing = [c.name for c in collections.collections]

        if collection_name in existing:
            print(f"⚠️  Collection '{collection_name}' already exists, skipping")
            return False

        # Create collection
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_dim,
                distance=distance
            )
        )

        print(f"✅ Created collection: {collection_name}")
        print(f"   Vector dimension: {vector_dim}")
        print(f"   Distance metric: {distance}")
        return True

    except Exception as e:
        print(f"❌ Failed to create collection '{collection_name}': {e}")
        return False

def main():
    print("=" * 60)
    print("Creating Qdrant Collections for SAFLA Memory Types")
    print("=" * 60)
    print()

    # Connect to Qdrant
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        print(f"✅ Connected to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
        print()
    except Exception as e:
        print(f"❌ Failed to connect to Qdrant: {e}")
        print("   Make sure Qdrant is running:")
        print("   /mnt/agentic-system/scripts/qdrant-monitor.sh status")
        return 1

    # Define collections to create
    collections = [
        {
            'name': 'enhanced_memory',
            'description': 'General memory storage with semantic search',
            'dim': VECTOR_DIM
        },
        {
            'name': 'working_memory',
            'description': 'Active context and temporary memories (TTL-based)',
            'dim': VECTOR_DIM
        },
        {
            'name': 'episodic_memory',
            'description': 'Time-bound experiences and events',
            'dim': VECTOR_DIM
        },
        {
            'name': 'semantic_memory',
            'description': 'Timeless concepts and relationships',
            'dim': VECTOR_DIM
        },
        {
            'name': 'procedural_memory',
            'description': 'Skills, procedures, and how-to knowledge',
            'dim': VECTOR_DIM
        }
    ]

    created_count = 0
    skipped_count = 0

    for col in collections:
        print(f"📦 {col['name']}")
        print(f"   {col['description']}")

        if create_collection(client, col['name'], col['dim']):
            created_count += 1
        else:
            skipped_count += 1

        print()

    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"✅ Created: {created_count} collections")
    print(f"⚠️  Skipped: {skipped_count} collections (already exist)")
    print()

    # List all collections
    all_collections = client.get_collections()
    print(f"📊 Total collections in Qdrant: {len(all_collections.collections)}")

    for col in all_collections.collections:
        info = client.get_collection(col.name)
        print(f"   - {col.name}: {info.points_count} points")

    print()
    print("🎉 Collection setup complete!")
    return 0

if __name__ == '__main__':
    sys.exit(main())

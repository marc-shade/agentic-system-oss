#!/usr/bin/env python3
"""
Initialize Qdrant collections for enhanced-memory-mcp.
"""

import sys

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams
except ImportError:
    print("Installing qdrant-client...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "qdrant-client"])
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams


def init_collections():
    """Initialize Qdrant collections for AGI memory."""
    client = QdrantClient(host="localhost", port=6333)

    # Vector dimension for sentence-transformers (all-MiniLM-L6-v2)
    VECTOR_SIZE = 384

    collections = [
        {
            "name": "semantic_memory",
            "description": "Timeless concepts, principles, and knowledge"
        },
        {
            "name": "episodic_memory",
            "description": "Time-bound experiences and events"
        },
        {
            "name": "procedural_memory",
            "description": "Skills, techniques, and how-to knowledge"
        },
        {
            "name": "working_memory",
            "description": "Active context and temporary information"
        },
        {
            "name": "research_papers",
            "description": "Extracted knowledge from academic papers"
        },
        {
            "name": "video_knowledge",
            "description": "Extracted knowledge from video transcripts"
        }
    ]

    for coll in collections:
        # Check if collection exists
        existing = client.get_collections().collections
        existing_names = [c.name for c in existing]

        if coll["name"] not in existing_names:
            client.create_collection(
                collection_name=coll["name"],
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance=Distance.COSINE
                )
            )
            print(f"  Created collection: {coll['name']}")
        else:
            print(f"  Collection exists: {coll['name']}")

    print("\nQdrant collections initialized!")
    print(f"Dashboard: http://localhost:6333/dashboard")


if __name__ == "__main__":
    try:
        init_collections()
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure Qdrant is running (docker-compose up -d)")
        sys.exit(1)

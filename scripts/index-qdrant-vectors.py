#!/usr/bin/env python3
"""
Index enhanced-memory entities into Qdrant for vector search.

This script:
1. Reads entities and their observations from enhanced-memory SQLite DB
2. Generates embeddings using sentence-transformers
3. Indexes them into Qdrant for semantic vector search
4. Provides progress tracking and verification

Usage:
    python index-qdrant-vectors.py [--batch-size 100] [--recreate]
"""

import sqlite3
import json
import time
import argparse
from typing import List, Dict, Tuple
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

# Configuration
DB_PATH = "/home/marc/.claude/enhanced_memories/memory.db"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION = "enhanced_memory"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # 384 dimensions, fast and efficient
BATCH_SIZE = 100
DEFAULT_VECTOR_SIZE = 384  # For all-MiniLM-L6-v2


def connect_to_databases():
    """Connect to SQLite and Qdrant."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Connecting to databases...")

    # SQLite
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    print(f"  ✓ Connected to SQLite: {DB_PATH}")

    # Qdrant
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    print(f"  ✓ Connected to Qdrant: {QDRANT_HOST}:{QDRANT_PORT}")

    return conn, client


def load_embedding_model():
    """Load sentence transformer model."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Loading embedding model: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)
    print(f"  ✓ Model loaded (dimension: {model.get_sentence_embedding_dimension()})")
    return model


def ensure_collection(client: QdrantClient, recreate: bool = False):
    """Create or verify Qdrant collection."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Setting up collection: {COLLECTION}")

    collections = [c.name for c in client.get_collections().collections]

    if COLLECTION in collections:
        if recreate:
            print(f"  ! Deleting existing collection for recreation...")
            client.delete_collection(COLLECTION)
        else:
            info = client.get_collection(COLLECTION)
            print(f"  ✓ Collection exists with {info.points_count} points")
            return

    # Create collection
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=DEFAULT_VECTOR_SIZE, distance=Distance.COSINE)
    )
    print(f"  ✓ Collection created (vector size: {DEFAULT_VECTOR_SIZE}, distance: Cosine)")


def fetch_entities(conn: sqlite3.Connection) -> List[Tuple]:
    """Fetch all entities with their observations."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching entities from database...")

    cursor = conn.execute("""
        SELECT
            e.id,
            e.name,
            e.entity_type,
            e.tier,
            e.salience_score,
            e.access_count,
            e.created_at,
            e.last_accessed,
            GROUP_CONCAT(o.content, ' ') as observations
        FROM entities e
        LEFT JOIN observations o ON e.id = o.entity_id
        GROUP BY e.id
        HAVING observations IS NOT NULL
        ORDER BY e.id
    """)

    entities = cursor.fetchall()
    print(f"  ✓ Found {len(entities)} entities with observations")
    return entities


def create_embedding_text(entity: sqlite3.Row) -> str:
    """Create text for embedding from entity data."""
    # Combine name, type, and observations for rich semantic representation
    observations = entity['observations'] or ""

    # Truncate observations if too long (to avoid excessive token usage)
    max_obs_length = 2000
    if len(observations) > max_obs_length:
        observations = observations[:max_obs_length] + "..."

    text = f"{entity['name']} ({entity['entity_type']}): {observations}"
    return text


def index_entities(
    entities: List[Tuple],
    model: SentenceTransformer,
    client: QdrantClient,
    batch_size: int = BATCH_SIZE
):
    """Index entities into Qdrant with progress tracking."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting indexing of {len(entities)} entities...")

    start_time = time.time()
    points = []
    indexed_count = 0

    for i, entity in enumerate(entities):
        # Create embedding text
        text = create_embedding_text(entity)

        # Generate embedding
        embedding = model.encode(text, convert_to_tensor=False).tolist()

        # Create point with rich payload
        point = PointStruct(
            id=entity['id'],
            vector=embedding,
            payload={
                "name": entity['name'],
                "entity_type": entity['entity_type'],
                "tier": entity['tier'],
                "salience_score": entity['salience_score'] or 0.5,
                "access_count": entity['access_count'] or 0,
                "created_at": entity['created_at'],
                "last_accessed": entity['last_accessed'],
                "observations_preview": (entity['observations'] or "")[:500]
            }
        )
        points.append(point)

        # Batch upsert
        if len(points) >= batch_size:
            client.upsert(collection_name=COLLECTION, points=points)
            indexed_count += len(points)

            # Progress update
            elapsed = time.time() - start_time
            rate = indexed_count / elapsed
            eta = (len(entities) - indexed_count) / rate if rate > 0 else 0

            print(f"  [{i+1:4d}/{len(entities)}] Indexed {indexed_count} entities "
                  f"({rate:.1f} entities/sec, ETA: {eta:.1f}s)")

            points = []

    # Index remaining points
    if points:
        client.upsert(collection_name=COLLECTION, points=points)
        indexed_count += len(points)

    elapsed = time.time() - start_time
    print(f"  ✓ Indexing complete: {indexed_count} entities in {elapsed:.2f}s "
          f"({indexed_count/elapsed:.1f} entities/sec)")


def verify_indexing(client: QdrantClient, expected_count: int):
    """Verify the indexing was successful."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Verifying indexing...")

    info = client.get_collection(COLLECTION)
    actual_count = info.points_count

    print(f"  Expected: {expected_count} entities")
    print(f"  Indexed:  {actual_count} points")

    if actual_count == expected_count:
        print(f"  ✓ Verification passed!")
    else:
        print(f"  ⚠ Count mismatch! Expected {expected_count}, got {actual_count}")

    return actual_count


def test_vector_search(client: QdrantClient, model: SentenceTransformer):
    """Test vector search with sample queries."""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Testing vector search...")

    test_queries = [
        "memory consolidation and sleep patterns",
        "AGI self-improvement capabilities",
        "neural networks and embeddings"
    ]

    for query in test_queries:
        print(f"\n  Query: '{query}'")

        # Generate query embedding
        query_vector = model.encode(query).tolist()

        # Search
        results = client.search(
            collection_name=COLLECTION,
            query_vector=query_vector,
            limit=3
        )

        # Display results
        for j, result in enumerate(results, 1):
            print(f"    {j}. [{result.score:.3f}] {result.payload['name']} "
                  f"({result.payload['entity_type']})")
            print(f"       Preview: {result.payload['observations_preview'][:100]}...")


def print_statistics(conn: sqlite3.Connection, client: QdrantClient):
    """Print comprehensive statistics."""
    print(f"\n{'='*80}")
    print(f"INDEXING STATISTICS")
    print(f"{'='*80}")

    # SQLite stats
    cursor = conn.execute("""
        SELECT
            COUNT(*) as total_entities,
            COUNT(DISTINCT entity_type) as entity_types,
            SUM(access_count) as total_accesses
        FROM entities
    """)
    stats = cursor.fetchone()

    print(f"\nSource Database (SQLite):")
    print(f"  Total entities: {stats['total_entities']}")
    print(f"  Entity types: {stats['entity_types']}")
    print(f"  Total accesses: {stats['total_accesses']}")

    cursor = conn.execute("""
        SELECT entity_type, COUNT(*) as count
        FROM entities
        GROUP BY entity_type
        ORDER BY count DESC
        LIMIT 10
    """)
    print(f"\n  Top entity types:")
    for row in cursor:
        print(f"    {row['entity_type']:30s}: {row['count']:4d}")

    # Qdrant stats
    info = client.get_collection(COLLECTION)
    print(f"\nVector Database (Qdrant):")
    print(f"  Collection: {COLLECTION}")
    print(f"  Points indexed: {info.points_count}")
    print(f"  Vector size: {info.config.params.vectors.size}")
    print(f"  Distance metric: {info.config.params.vectors.distance}")
    print(f"  Status: {info.status}")

    print(f"\n{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(description='Index enhanced-memory entities into Qdrant')
    parser.add_argument('--batch-size', type=int, default=BATCH_SIZE,
                        help=f'Batch size for indexing (default: {BATCH_SIZE})')
    parser.add_argument('--recreate', action='store_true',
                        help='Recreate collection (deletes existing data)')
    parser.add_argument('--test-only', action='store_true',
                        help='Only run test searches, skip indexing')
    args = parser.parse_args()

    print(f"\n{'='*80}")
    print(f"Enhanced Memory → Qdrant Vector Indexing")
    print(f"{'='*80}\n")

    # Connect
    conn, client = connect_to_databases()

    if args.test_only:
        model = load_embedding_model()
        test_vector_search(client, model)
        print_statistics(conn, client)
        return

    # Setup
    ensure_collection(client, recreate=args.recreate)
    model = load_embedding_model()

    # Fetch and index
    entities = fetch_entities(conn)
    if not entities:
        print("  ⚠ No entities with observations found. Nothing to index.")
        return

    index_entities(entities, model, client, batch_size=args.batch_size)

    # Verify
    verify_indexing(client, len(entities))

    # Test
    test_vector_search(client, model)

    # Stats
    print_statistics(conn, client)

    print(f"✓ Indexing complete!")
    print(f"\nVector search is now enabled for enhanced-memory entities.")
    print(f"Use the enhanced-memory MCP search tools to query semantically.\n")


if __name__ == "__main__":
    main()

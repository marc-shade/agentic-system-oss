#!/usr/bin/env python3
"""
Compare text-based search vs vector-based semantic search.

Demonstrates the power of vector embeddings for semantic understanding.
"""

import sqlite3
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

DB_PATH = "/home/marc/.claude/enhanced_memories/memory.db"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION = "enhanced_memory"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def text_search(conn, query, limit=5):
    """Traditional SQLite full-text search."""
    cursor = conn.execute("""
        SELECT
            e.name,
            e.entity_type,
            GROUP_CONCAT(o.content, ' ') as observations
        FROM entities e
        LEFT JOIN observations o ON e.id = o.entity_id
        WHERE e.name LIKE ? OR o.content LIKE ?
        GROUP BY e.id
        LIMIT ?
    """, (f"%{query}%", f"%{query}%", limit))
    return cursor.fetchall()


def vector_search(client, model, query, limit=5):
    """Semantic vector search using Qdrant."""
    query_vector = model.encode(query).tolist()
    results = client.search(
        collection_name=COLLECTION,
        query_vector=query_vector,
        limit=limit
    )
    return results


def main():
    print("\n" + "="*80)
    print("TEXT SEARCH vs VECTOR SEARCH COMPARISON")
    print("="*80 + "\n")

    # Connect
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    model = SentenceTransformer(EMBEDDING_MODEL)

    # Test queries
    test_queries = [
        "How does the system learn from experience?",
        "What are the key principles of recursive self-improvement?",
        "Explain pattern recognition in cognitive systems",
        "Memory optimization techniques"
    ]

    for query in test_queries:
        print(f"\n{'─'*80}")
        print(f"QUERY: {query}")
        print(f"{'─'*80}\n")

        # Text search
        print("📝 TEXT SEARCH (keyword matching):")
        text_results = text_search(conn, query)
        if text_results:
            for i, row in enumerate(text_results, 1):
                preview = (row['observations'] or "")[:100]
                print(f"  {i}. {row['name']} ({row['entity_type']})")
                print(f"     {preview}...")
        else:
            print("  ❌ No results found")

        print()

        # Vector search
        print("🔍 VECTOR SEARCH (semantic understanding):")
        vector_results = vector_search(client, model, query)
        for i, result in enumerate(vector_results, 1):
            print(f"  {i}. [{result.score:.3f}] {result.payload['name']} "
                  f"({result.payload['entity_type']})")
            print(f"     {result.payload['observations_preview'][:100]}...")

    print("\n" + "="*80)
    print("KEY DIFFERENCES:")
    print("="*80)
    print("""
📝 TEXT SEARCH:
   - Requires exact keyword matches
   - Misses semantically similar content
   - Can't understand synonyms or related concepts
   - Limited to literal string matching

🔍 VECTOR SEARCH:
   - Understands semantic meaning
   - Finds conceptually related content
   - Works with synonyms and paraphrases
   - Captures context and relationships
   - Provides similarity scores (0.0-1.0)

CONCLUSION: Vector search enables true semantic understanding, finding
relevant content even when exact keywords don't match.
    """)


if __name__ == "__main__":
    main()

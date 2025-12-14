# Vector Search Quick Start Guide

## What is Vector Search?

Vector search enables **semantic understanding** of content, finding conceptually similar information even when exact keywords don't match.

**Example**: Query "How does the system learn?" finds results about "Schema Theory of Learning", "Autonomous Learning Loop", and "Dual Process Theory" - none of which contain the exact words "how" or "system learns".

## Quick Commands

### Check Status
```bash
/mnt/agentic-system/scripts/qdrant-maintenance.sh status
```

### Re-index Entities
```bash
/mnt/agentic-system/scripts/qdrant-maintenance.sh reindex
```

### Test Search Quality
```bash
/mnt/agentic-system/scripts/qdrant-maintenance.sh test
```

### Compare Text vs Vector Search
```bash
/mnt/agentic-system/scripts/qdrant-maintenance.sh compare
```

## Python Usage

### Direct Search
```python
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# Connect
client = QdrantClient(host="localhost", port=6333)
model = SentenceTransformer("all-MiniLM-L6-v2")

# Search
query = "recursive self-improvement in cognitive systems"
vector = model.encode(query).tolist()
results = client.search(
    collection_name="enhanced_memory",
    query_vector=vector,
    limit=10
)

# Results
for result in results:
    print(f"[{result.score:.3f}] {result.payload['name']}")
    print(f"  Type: {result.payload['entity_type']}")
    print(f"  Preview: {result.payload['observations_preview'][:100]}")
```

### With Filters
```python
# Search only theorems
results = client.search(
    collection_name="enhanced_memory",
    query_vector=vector,
    limit=10,
    query_filter={
        "must": [
            {"key": "entity_type", "match": {"value": "theorem"}}
        ]
    }
)

# Search high-salience entities
results = client.search(
    collection_name="enhanced_memory",
    query_vector=vector,
    limit=10,
    query_filter={
        "must": [
            {"key": "salience_score", "range": {"gte": 0.7}}
        ]
    }
)
```

## Collection Details

- **Name**: `enhanced_memory`
- **URL**: http://localhost:6333
- **Vector Size**: 384 dimensions
- **Model**: all-MiniLM-L6-v2 (sentence-transformers)
- **Distance**: Cosine similarity
- **Points**: 911 entities with observations

## Payload Fields

Each indexed point contains:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Entity name |
| `entity_type` | string | Type classification |
| `tier` | string | Memory tier (working/episodic/semantic/procedural) |
| `salience_score` | float | Importance score (0.0-1.0) |
| `access_count` | int | Number of accesses |
| `created_at` | timestamp | Creation time |
| `last_accessed` | timestamp | Last access time |
| `observations_preview` | string | First 500 chars of content |

## Performance Tips

### 1. Batch Searches
```python
queries = ["query1", "query2", "query3"]
vectors = model.encode(queries).tolist()

for i, vector in enumerate(vectors):
    results = client.search(
        collection_name="enhanced_memory",
        query_vector=vector,
        limit=5
    )
    print(f"Results for: {queries[i]}")
    # Process results...
```

### 2. Score Thresholds
```python
# Only return highly relevant results
results = client.search(
    collection_name="enhanced_memory",
    query_vector=vector,
    limit=10,
    score_threshold=0.5  # Only scores >= 0.5
)
```

### 3. Filtered Retrieval
```python
# Search within specific entity types
results = client.search(
    collection_name="enhanced_memory",
    query_vector=vector,
    limit=10,
    query_filter={
        "should": [
            {"key": "entity_type", "match": {"value": "theorem"}},
            {"key": "entity_type", "match": {"value": "algorithm"}},
            {"key": "entity_type", "match": {"value": "technique"}}
        ]
    }
)
```

## Maintenance

### When to Re-index

Re-index when:
- New entities are added to enhanced-memory
- Existing entity observations are updated
- After memory consolidation runs
- After bulk imports

### Incremental Re-index
```bash
cd /mnt/agentic-system
source .venv/bin/activate
python scripts/index-qdrant-vectors.py
```

### Full Re-index (Recreate Collection)
```bash
cd /mnt/agentic-system
source .venv/bin/activate
python scripts/index-qdrant-vectors.py --recreate
```

## Troubleshooting

### No Results Found
- Check if collection exists: `curl http://localhost:6333/collections`
- Verify points indexed: `curl http://localhost:6333/collections/enhanced_memory`
- Try lower score threshold or broader query

### Dimension Mismatch Error
- Collection was created with wrong vector size
- Solution: Re-create collection with `--recreate` flag

### Slow Searches
- Model loading on first search is normal (~5s)
- Subsequent searches are fast (<100ms)
- For batch searches, reuse model instance

### Qdrant Not Running
```bash
docker ps | grep qdrant
docker start qdrant  # If stopped
```

## Integration Examples

### With Enhanced-Memory MCP
```python
# In enhanced-memory MCP server
def semantic_search(query: str, limit: int = 10):
    from qdrant_client import QdrantClient
    from sentence_transformers import SentenceTransformer

    client = QdrantClient(host="localhost", port=6333)
    model = SentenceTransformer("all-MiniLM-L6-v2")

    vector = model.encode(query).tolist()
    results = client.search(
        collection_name="enhanced_memory",
        query_vector=vector,
        limit=limit
    )

    # Convert to entity IDs for SQLite retrieval
    entity_ids = [r.id for r in results]
    return entity_ids
```

### With Agentic Workflows
```python
# Find relevant context for a task
task = "Implement recursive self-improvement"
context_entities = semantic_search(task, limit=5)

# Load full entity data from SQLite
conn = sqlite3.connect("/home/marc/.claude/enhanced_memories/memory.db")
for entity_id in context_entities:
    entity = load_entity(conn, entity_id)
    # Use entity data as context...
```

## Resources

- **Scripts**: `/mnt/agentic-system/scripts/`
  - `index-qdrant-vectors.py` - Indexing script
  - `compare-search-methods.py` - Search comparison demo
  - `qdrant-maintenance.sh` - Maintenance utilities
- **Report**: `/mnt/agentic-system/scripts/QDRANT_INDEXING_REPORT.md`
- **Qdrant Docs**: https://qdrant.tech/documentation/
- **Model Info**: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2

---

**Status**: ✅ Production Ready
**Last Indexed**: 2025-11-28
**Collection Health**: Green

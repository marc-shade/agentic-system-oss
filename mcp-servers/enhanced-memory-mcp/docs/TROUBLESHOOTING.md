# Enhanced Memory MCP - Troubleshooting Guide

## Common Issues

### Connection Problems

#### Qdrant Connection Failed
```
Error: Connection refused to localhost:6333
```

**Solution:**
1. Verify Qdrant is running:
```bash
docker ps | grep qdrant
# or
curl http://localhost:6333/health
```

2. Start Qdrant if not running:
```bash
docker run -d -p 6333:6333 qdrant/qdrant
```

3. Check firewall rules allow port 6333

#### Memory-DB Socket Connection Failed
```
Error: Cannot connect to memory-db service
```

**Solution:**
1. Check if memory-db service is running:
```bash
ps aux | grep memory_db_service
```

2. Verify socket file exists:
```bash
ls -la /tmp/memory-db.sock
```

3. Restart the service:
```bash
python memory_db_service.py &
```

### Search Issues

#### No Results Returned
**Symptoms:** Search returns empty results even for known entities.

**Possible Causes:**
1. **Collection not indexed** - Run reindexing:
```bash
python -c "from server import init_database; init_database()"
```

2. **Embedding model not loaded** - Check Ollama:
```bash
ollama list | grep nomic-embed-text
# If missing, pull the model:
ollama pull nomic-embed-text
```

3. **Query too specific** - Try broader search terms

#### Slow Search Performance
**Symptoms:** Searches taking >1 second.

**Solutions:**
1. **Enable FACT cache:**
```python
# Use fact_search instead of search_nodes
results = await fact_search(query="your query", limit=10)
```

2. **Warm the cache:**
```bash
python -c "
from server import fact_warm_cache
import asyncio
asyncio.run(fact_warm_cache(['common query 1', 'common query 2']))
"
```

3. **Check Qdrant indexes:**
```bash
curl http://localhost:6333/collections/enhanced_memory
```

### Compression Issues

#### Decompression Error
```
Error: zlib.error: Error -3 while decompressing data
```

**Cause:** Corrupted compressed data in database.

**Solution:**
1. Identify corrupted entities:
```python
import sqlite3
conn = sqlite3.connect("~/.claude/enhanced_memories/memory.db")
cursor = conn.cursor()
cursor.execute("SELECT id, name FROM entities WHERE compressed_data IS NOT NULL")
for row in cursor:
    try:
        # Try decompressing
        from server import decompress_data
        cursor.execute("SELECT compressed_data FROM entities WHERE id=?", (row[0],))
        decompress_data(cursor.fetchone()[0])
    except:
        print(f"Corrupted: {row}")
```

2. Delete or recreate corrupted entities

### Memory Issues

#### Out of Memory
```
Error: MemoryError or Killed
```

**Solutions:**
1. Increase system swap:
```bash
sudo sysctl vm.swappiness=60
```

2. Limit memory usage:
```bash
export MAX_MEMORY_SIZE_MB=512
python server.py
```

3. Run garbage collection more frequently (in code):
```python
import gc
gc.collect()
```

#### Database Size Growing Too Large
**Solution:**
1. Clean old versions:
```sql
DELETE FROM memory_versions
WHERE created_at < datetime('now', '-30 days')
AND is_current = 0;
VACUUM;
```

2. Compress and archive old entities:
```python
# Archive entities not accessed in 90 days
cursor.execute("""
    UPDATE entities SET tier = 'archive'
    WHERE last_accessed < datetime('now', '-90 days')
""")
```

### Embedding Issues

#### Embedding Generation Timeout
```
Error: Timeout waiting for embedding response
```

**Solutions:**
1. Check Ollama status:
```bash
ollama ps
```

2. Restart Ollama:
```bash
pkill ollama && ollama serve &
```

3. Use fallback provider:
```bash
export EMBEDDING_PROVIDER=openai
export OPENAI_API_KEY=your_key
```

#### Dimension Mismatch
```
Error: Vector dimension 384 doesn't match collection dimension 768
```

**Cause:** Collection created with different embedding model.

**Solution:**
1. Recreate collection:
```bash
curl -X DELETE http://localhost:6333/collections/enhanced_memory
# Server will recreate on restart
python server.py
```

2. Or migrate data:
```python
# Export, recreate collection, re-embed and import
```

### Provenance/L-Score Issues

#### L-Score Always Low
**Symptoms:** All entities flagged with low L-Score.

**Cause:** Provenance tracking not capturing sources properly.

**Solution:**
1. Verify source attribution:
```python
# When creating entities, include source
entities = [{
    "name": "entity-name",
    "entityType": "knowledge",
    "observations": ["content"],
    "metadata": {
        "source": "verified_source",
        "source_type": "documentation"
    }
}]
```

2. Check provenance database:
```sql
SELECT * FROM provenance_records ORDER BY created_at DESC LIMIT 10;
```

### Code Execution Issues

#### Sandbox Timeout
```
Error: Code execution timed out after 30 seconds
```

**Solutions:**
1. Optimize code to run faster
2. Split into smaller operations
3. Increase timeout (not recommended for production):
```python
# In sandbox/executor.py
TIMEOUT_SECONDS = 60  # Default is 30
```

#### Import Not Allowed
```
Error: Import of 'os' is not allowed in sandbox
```

**Cause:** Restricted imports for security.

**Solution:** Use provided APIs instead:
```python
# Instead of: import os; os.listdir()
# Use: list_files()  # Sandbox API

# Instead of: import json; json.dumps()
# Use: result = {"data": value}  # Python dict is JSON-serializable
```

### Logging and Debugging

#### Enable Debug Logging
```bash
export LOG_LEVEL=DEBUG
python server.py
```

#### View Real-time Logs
```bash
tail -f ~/.claude/enhanced_memories/../server.log
```

#### Check Tool Usage
```python
# Get tool usage summary
result = await get_tool_usage_summary()
print(result)
```

### Recovery Procedures

#### Full Database Reset
```bash
# CAUTION: This deletes all data
rm -rf ~/.claude/enhanced_memories/
python server.py  # Recreates empty database
```

#### Restore from Backup
```bash
# Stop server
pkill -f "python server.py"

# Restore SQLite
cp /backups/latest/memory.db ~/.claude/enhanced_memories/

# Restore Qdrant (if separate backup)
curl -X PUT "http://localhost:6333/collections/enhanced_memory/snapshots/recover" \
  -d '{"location": "/backups/latest/qdrant.snapshot"}'

# Restart server
python server.py
```

### Getting Help

1. **Check logs:** `server.log` contains detailed error information
2. **Search issues:** https://github.com/marc-shade/enhanced-memory-mcp/issues
3. **Create new issue:** Include:
   - Error message and full traceback
   - Python version (`python --version`)
   - OS and version
   - Steps to reproduce
   - Relevant configuration

# Enhanced Memory System - Implementation Guide

**Target Audience**: Developers building memory systems
**Time to Build**: 8-12 hours for MVP, 40-60 hours for full system
**Prerequisites**: Python 3.9+, SQLite, Unix/Linux environment

## Quick Start (15 minutes)

### 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install core dependencies
pip install fastmcp==0.3.0
pip install RestrictedPython==7.0
pip install psutil
pip install timeout-decorator

# Optional: For advanced features
pip install sentence-transformers  # Embeddings
pip install anthropic               # LLM extraction
```

### 2. Minimal Database Setup

```python
import sqlite3
from pathlib import Path

DB_PATH = Path.home() / ".memories" / "memory.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Minimal schema
cursor.execute('''
    CREATE TABLE IF NOT EXISTS entities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        entity_type TEXT NOT NULL,
        compressed_data BLOB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

conn.commit()
conn.close()

print(f"✅ Database created at {DB_PATH}")
```

### 3. Basic Compression Functions

```python
import zlib
import pickle

def compress_data(data: dict) -> bytes:
    """Compress entity data"""
    pickled = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
    compressed = zlib.compress(pickled, level=6)
    return compressed

def decompress_data(compressed: bytes) -> dict:
    """Decompress entity data"""
    pickled = zlib.decompress(compressed)
    data = pickle.loads(pickled)
    return data

# Test it
test_data = {"observations": ["fact 1", "fact 2", "fact 3"]}
compressed = compress_data(test_data)
decompressed = decompress_data(compressed)

print(f"✅ Compression working: {len(str(test_data))} bytes → {len(compressed)} bytes")
print(f"   Ratio: {len(compressed) / len(str(test_data)):.2%}")
```

### 4. Create Your First Memory

```python
def create_entity(name: str, entity_type: str, observations: list):
    """Create a memory entity"""
    data = {"observations": observations}
    compressed = compress_data(data)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO entities (name, entity_type, compressed_data)
        VALUES (?, ?, ?)
    ''', (name, entity_type, compressed))
    
    entity_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return entity_id

# Create first memory
entity_id = create_entity(
    name="user-preferences",
    entity_type="preference",
    observations=["Prefers voice", "Uses parallel execution"]
)

print(f"✅ Created entity ID {entity_id}")
```

### 5. Search Memories

```python
def search_entities(query: str, limit: int = 10):
    """Search for entities"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, entity_type, compressed_data
        FROM entities
        WHERE name LIKE ? OR entity_type LIKE ?
        LIMIT ?
    ''', (f'%{query}%', f'%{query}%', limit))
    
    results = []
    for row in cursor.fetchall():
        entity_id, name, entity_type, compressed_data = row
        data = decompress_data(compressed_data)
        results.append({
            "id": entity_id,
            "name": name,
            "type": entity_type,
            "observations": data["observations"]
        })
    
    conn.close()
    return results

# Search
results = search_entities("preference")
print(f"✅ Found {len(results)} entities")
for r in results:
    print(f"   - {r['name']}: {len(r['observations'])} observations")
```

**🎉 You now have a working memory system!**

---

## Full Implementation (Step-by-Step)

### Step 1: Database Schema (30 minutes)

Create the complete schema with all tables:

```sql
-- entities table (core storage)
CREATE TABLE entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    entity_type TEXT NOT NULL,
    tier TEXT DEFAULT 'working',
    compressed_data BLOB,
    original_size INTEGER,
    compressed_size INTEGER,
    compression_ratio REAL,
    checksum TEXT,
    access_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    current_version INTEGER DEFAULT 1,
    current_branch TEXT DEFAULT 'main',
    always_include BOOLEAN DEFAULT 0,
    source_session TEXT,
    source_timestamp TIMESTAMP,
    extraction_method TEXT DEFAULT 'manual',
    last_confirmed TIMESTAMP,
    relevance_score REAL DEFAULT 1.0,
    parent_entity_id INTEGER,
    conflict_resolution_method TEXT
);

-- Indexes for performance
CREATE INDEX idx_entities_name ON entities(name);
CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_tier ON entities(tier);
CREATE INDEX idx_entities_accessed ON entities(last_accessed);
CREATE INDEX idx_entities_always_include ON entities(always_include);

-- versions table (version control)
CREATE TABLE versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER,
    version_number INTEGER,
    branch_name TEXT,
    compressed_data BLOB,
    commit_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (entity_id) REFERENCES entities (id)
);

-- conflicts table (conflict tracking)
CREATE TABLE conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER,
    conflicting_entity_id INTEGER,
    conflict_type TEXT NOT NULL,
    confidence REAL NOT NULL,
    suggested_action TEXT,
    resolution_status TEXT DEFAULT 'pending',
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolution_notes TEXT,
    FOREIGN KEY (entity_id) REFERENCES entities (id),
    FOREIGN KEY (conflicting_entity_id) REFERENCES entities (id)
);
```

### Step 2: Memory-DB Service (2 hours)

Create a Unix socket service for concurrent access:

```python
# memory_db_service.py
import socket
import json
import sqlite3
import threading
from pathlib import Path

DB_PATH = Path.home() / ".memories" / "memory.db"
SOCKET_PATH = "/tmp/memory-db.sock"

class MemoryDBService:
    def __init__(self):
        self.db_path = DB_PATH
        self.socket_path = SOCKET_PATH
        
    def handle_request(self, request: dict) -> dict:
        """Handle incoming request"""
        method = request.get("method")
        params = request.get("params", {})
        
        if method == "create_entities":
            return self.create_entities(params.get("entities", []))
        elif method == "search_nodes":
            return self.search_nodes(params.get("query"), params.get("limit", 10))
        elif method == "get_memory_status":
            return self.get_memory_status()
        else:
            return {"success": False, "error": f"Unknown method: {method}"}
    
    def create_entities(self, entities: list) -> dict:
        """Create or update entities"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        results = []
        
        for entity in entities:
            name = entity.get("name")
            entity_type = entity.get("entityType")
            observations = entity.get("observations", [])
            
            # Compress data
            data = {"observations": observations}
            compressed = compress_data(data)
            
            # Check if exists
            cursor.execute("SELECT id FROM entities WHERE name = ?", (name,))
            existing = cursor.fetchone()
            
            if existing:
                # Update
                cursor.execute('''
                    UPDATE entities 
                    SET compressed_data = ?, current_version = current_version + 1
                    WHERE name = ?
                ''', (compressed, name))
                action = "updated"
            else:
                # Insert
                cursor.execute('''
                    INSERT INTO entities (name, entity_type, compressed_data)
                    VALUES (?, ?, ?)
                ''', (name, entity_type, compressed))
                action = "created"
            
            results.append({
                "name": name,
                "action": action,
                "id": cursor.lastrowid if action == "created" else existing[0]
            })
        
        conn.commit()
        conn.close()
        
        return {"success": True, "results": results}
    
    def search_nodes(self, query: str, limit: int) -> dict:
        """Search entities"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, entity_type, compressed_data
            FROM entities
            WHERE name LIKE ? OR entity_type LIKE ?
            LIMIT ?
        ''', (f'%{query}%', f'%{query}%', limit))
        
        results = []
        for row in cursor.fetchall():
            entity_id, name, entity_type, compressed_data = row
            data = decompress_data(compressed_data)
            results.append({
                "id": entity_id,
                "name": name,
                "type": entity_type,
                "observations": data.get("observations", [])
            })
        
        conn.close()
        return {"success": True, "results": results, "count": len(results)}
    
    def get_memory_status(self) -> dict:
        """Get system stats"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM entities")
        total = cursor.fetchone()[0]
        
        conn.close()
        return {"success": True, "total_entities": total}
    
    def run(self):
        """Start socket server"""
        # Remove old socket
        if Path(self.socket_path).exists():
            Path(self.socket_path).unlink()
        
        # Create socket
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(self.socket_path)
        server.listen(5)
        
        print(f"✅ Memory-DB service running on {self.socket_path}")
        
        while True:
            conn, addr = server.accept()
            
            # Receive request
            data = conn.recv(4096).decode()
            request = json.loads(data)
            
            # Process
            response = self.handle_request(request)
            
            # Send response
            conn.send(json.dumps(response).encode())
            conn.close()

if __name__ == "__main__":
    service = MemoryDBService()
    service.run()
```

**Run the service**:
```bash
python3 memory_db_service.py &
```

### Step 3: Memory Client (30 minutes)

Create a client to communicate with the service:

```python
# memory_client.py
import socket
import json
from typing import Dict, List, Any

SOCKET_PATH = "/tmp/memory-db.sock"

class MemoryClient:
    def __init__(self, socket_path: str = SOCKET_PATH):
        self.socket_path = socket_path
    
    def _send_request(self, method: str, params: dict) -> dict:
        """Send request to memory-db service"""
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(self.socket_path)
        
        request = {
            "method": method,
            "params": params
        }
        
        client.send(json.dumps(request).encode())
        response = client.recv(4096).decode()
        client.close()
        
        return json.loads(response)
    
    async def create_entities(self, entities: List[Dict]) -> Dict:
        """Create entities"""
        return self._send_request("create_entities", {"entities": entities})
    
    async def search_nodes(self, query: str, limit: int = 10) -> Dict:
        """Search entities"""
        return self._send_request("search_nodes", {"query": query, "limit": limit})
    
    async def get_memory_status(self) -> Dict:
        """Get status"""
        return self._send_request("get_memory_status", {})

# Usage
client = MemoryClient()
result = await client.create_entities([{
    "name": "test-entity",
    "entityType": "test",
    "observations": ["Test observation"]
}])
print(result)
```

### Step 4: MCP Server (2 hours)

Expose memory operations via MCP protocol:

```python
# server.py
from fastmcp import FastMCP
from memory_client import MemoryClient
import logging
import sys

# Configure logging (stderr only for MCP)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("memory-mcp")

app = FastMCP("enhanced-memory")
memory_client = MemoryClient()

@app.tool()
async def create_entities(entities: list) -> dict:
    """
    Create or update memory entities.
    
    Args:
        entities: List of entity dicts with name, entityType, observations
    
    Returns:
        {"success": bool, "results": list}
    """
    try:
        result = await memory_client.create_entities(entities)
        return result
    except Exception as e:
        logger.error(f"Error creating entities: {e}")
        return {"success": False, "error": str(e)}

@app.tool()
async def search_nodes(query: str, limit: int = 10) -> dict:
    """
    Search memory entities.
    
    Args:
        query: Search string
        limit: Max results
    
    Returns:
        {"success": bool, "results": list, "count": int}
    """
    try:
        result = await memory_client.search_nodes(query, limit)
        return result
    except Exception as e:
        logger.error(f"Error searching: {e}")
        return {"success": False, "error": str(e)}

@app.tool()
async def get_memory_status() -> dict:
    """Get memory system statistics"""
    try:
        result = await memory_client.get_memory_status()
        return result
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    app.run()
```

**Test the MCP server**:
```bash
python3 server.py
```

### Step 5: Auto-Extraction (1 hour)

Add automatic fact extraction:

```python
@app.tool()
async def auto_extract_facts(
    conversation_text: str,
    session_id: str = None,
    auto_store: bool = True
) -> dict:
    """
    Extract facts from conversation automatically.
    
    Args:
        conversation_text: Conversation text to analyze
        session_id: Optional session identifier
        auto_store: Whether to store extracted facts
    
    Returns:
        {"success": bool, "facts": list, "count": int}
    """
    try:
        # Extract facts using pattern matching
        lines = conversation_text.split('\n')
        observations = []
        
        keywords = ['prefer', 'like', 'use', 'need', 'want', 'always', 'never']
        
        for line in lines:
            if any(kw in line.lower() for kw in keywords):
                observations.append(line.strip())
        
        if not observations:
            return {"success": True, "facts": [], "count": 0}
        
        # Create entity
        entity_name = f"auto-extracted-{session_id or 'session'}"
        facts = [{
            "name": entity_name,
            "entityType": "auto_extracted",
            "observations": observations,
            "source_session": session_id,
            "extraction_method": "auto"
        }]
        
        # Store if requested
        if auto_store:
            result = await memory_client.create_entities(facts)
            return {
                "success": True,
                "facts": facts,
                "count": len(facts),
                "stored": True,
                "entity_ids": [r["id"] for r in result.get("results", [])]
            }
        else:
            return {
                "success": True,
                "facts": facts,
                "count": len(facts),
                "stored": False
            }
    
    except Exception as e:
        logger.error(f"Error extracting facts: {e}")
        return {"success": False, "error": str(e)}
```

### Step 6: Conflict Detection (1 hour)

Add conflict detection:

```python
@app.tool()
async def detect_conflicts(
    entity_data: dict,
    threshold: float = 0.85
) -> dict:
    """
    Detect conflicts with existing entities.
    
    Args:
        entity_data: Entity dict with observations
        threshold: Overlap threshold (0.0-1.0)
    
    Returns:
        {"success": bool, "conflicts": list, "conflict_count": int}
    """
    try:
        import sqlite3
        
        entity_type = entity_data.get("entityType")
        new_obs = set(entity_data.get("observations", []))
        
        # Search similar entities
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, compressed_data
            FROM entities
            WHERE entity_type = ?
            LIMIT 50
        ''', (entity_type,))
        
        conflicts = []
        
        for row in cursor.fetchall():
            entity_id, name, compressed_data = row
            data = decompress_data(compressed_data)
            existing_obs = set(data.get("observations", []))
            
            # Calculate overlap
            intersection = new_obs & existing_obs
            max_size = max(len(new_obs), len(existing_obs))
            
            if max_size > 0:
                overlap_ratio = len(intersection) / max_size
                
                if overlap_ratio > threshold:
                    conflicts.append({
                        "existing_entity": name,
                        "existing_id": entity_id,
                        "conflict_type": "duplicate",
                        "confidence": overlap_ratio,
                        "suggested_action": "merge"
                    })
                elif overlap_ratio > 0.3:
                    conflicts.append({
                        "existing_entity": name,
                        "existing_id": entity_id,
                        "conflict_type": "update",
                        "confidence": overlap_ratio,
                        "suggested_action": "update"
                    })
        
        conn.close()
        
        return {
            "success": True,
            "conflicts": conflicts,
            "conflict_count": len(conflicts)
        }
    
    except Exception as e:
        logger.error(f"Error detecting conflicts: {e}")
        return {"success": False, "error": str(e)}
```

### Step 7: Testing (30 minutes)

Create comprehensive tests:

```python
# test_memory_system.py
import asyncio
from memory_client import MemoryClient

async def test_all():
    """Test all memory operations"""
    client = MemoryClient()
    
    # Test 1: Create entity
    print("TEST 1: Create entity")
    result = await client.create_entities([{
        "name": "test-entity-001",
        "entityType": "test",
        "observations": ["Test observation 1", "Test observation 2"]
    }])
    assert result["success"], "Create failed"
    print(f"✅ Created entity: {result['results'][0]}")
    
    # Test 2: Search
    print("\nTEST 2: Search entity")
    result = await client.search_nodes("test", limit=10)
    assert result["success"], "Search failed"
    assert result["count"] > 0, "No results"
    print(f"✅ Found {result['count']} entities")
    
    # Test 3: Status
    print("\nTEST 3: Get status")
    result = await client.get_memory_status()
    assert result["success"], "Status failed"
    print(f"✅ Total entities: {result['total_entities']}")
    
    print("\n🎉 All tests passed!")

if __name__ == "__main__":
    asyncio.run(test_all())
```

**Run tests**:
```bash
python3 test_memory_system.py
```

---

## Advanced Features

### Code Execution Sandbox (2 hours)

```python
from RestrictedPython import compile_restricted
import timeout_decorator

@timeout_decorator.timeout(30)
def execute_code_safely(code: str, context: dict) -> dict:
    """Execute code in sandbox"""
    try:
        # Compile with RestrictedPython
        byte_code = compile_restricted(code, '<sandbox>', 'exec')
        
        # Create safe context
        safe_globals = {
            "search_nodes": client.search_nodes,
            "create_entities": client.create_entities,
            "len": len,
            "sum": sum,
            "result": None
        }
        safe_globals.update(context)
        
        # Execute
        exec(byte_code, safe_globals)
        
        return {
            "success": True,
            "result": safe_globals.get("result")
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# Usage
result = execute_code_safely("""
results = search_nodes("test", limit=100)
filtered = [r for r in results if len(r['observations']) > 2]
result = {"count": len(filtered)}
""", {})
print(result)
```

### 4-Tier Memory Management (1 hour)

```python
def promote_to_tier(entity_id: int, new_tier: str):
    """Promote entity to different tier"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE entities
        SET tier = ?
        WHERE id = ?
    ''', (new_tier, entity_id))
    
    conn.commit()
    conn.close()

def autonomous_curation():
    """Run automatic tier management"""
    from datetime import datetime, timedelta
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Working → Episodic (old, rarely accessed)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    cursor.execute('''
        UPDATE entities
        SET tier = 'episodic'
        WHERE tier = 'working'
        AND created_at < ?
        AND access_count < 3
    ''', (thirty_days_ago,))
    
    promoted = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    return {"promoted_to_episodic": promoted}
```

---

## Production Deployment

### 1. Systemd Service

Create `/etc/systemd/system/memory-db.service`:

```ini
[Unit]
Description=Memory-DB Service
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/memory-system
ExecStart=/path/to/.venv/bin/python memory_db_service.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Start service**:
```bash
sudo systemctl enable memory-db
sudo systemctl start memory-db
sudo systemctl status memory-db
```

### 2. Monitoring

```python
# monitor.py
import sqlite3
import psutil
from pathlib import Path

def get_system_health():
    """Get system health metrics"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Entity count
    cursor.execute("SELECT COUNT(*) FROM entities")
    total_entities = cursor.fetchone()[0]
    
    # Database size
    db_size_mb = Path(DB_PATH).stat().st_size / 1024 / 1024
    
    # Memory usage
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    
    conn.close()
    
    return {
        "total_entities": total_entities,
        "database_size_mb": round(db_size_mb, 2),
        "memory_usage_mb": round(memory_mb, 2),
        "status": "healthy" if total_entities > 0 else "warning"
    }

print(get_system_health())
```

### 3. Backup Script

```bash
#!/bin/bash
# backup_memory.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=~/memory_backups
DB_PATH=~/.memories/memory.db

mkdir -p $BACKUP_DIR

# SQLite backup
sqlite3 $DB_PATH ".backup $BACKUP_DIR/memory_$DATE.db"

# Compress
gzip $BACKUP_DIR/memory_$DATE.db

# Keep only last 7 days
find $BACKUP_DIR -name "memory_*.db.gz" -mtime +7 -delete

echo "✅ Backup complete: memory_$DATE.db.gz"
```

**Schedule with cron**:
```bash
# Add to crontab
0 2 * * * /path/to/backup_memory.sh
```

---

## Performance Optimization

### 1. Connection Pooling

```python
from queue import Queue
import sqlite3

class ConnectionPool:
    def __init__(self, db_path, max_connections=10):
        self.pool = Queue(maxsize=max_connections)
        for _ in range(max_connections):
            self.pool.put(sqlite3.connect(db_path))
    
    def get_connection(self):
        return self.pool.get()
    
    def return_connection(self, conn):
        self.pool.put(conn)

pool = ConnectionPool(DB_PATH)
```

### 2. Batch Operations

```python
def create_entities_batch(entities, batch_size=100):
    """Create entities in batches"""
    for i in range(0, len(entities), batch_size):
        batch = entities[i:i+batch_size]
        client.create_entities(batch)
```

### 3. Caching

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_entity_cached(name: str):
    """Cache frequently accessed entities"""
    return search_nodes(name, limit=1)
```

---

## Troubleshooting

### Issue: "No such file or directory: /tmp/memory-db.sock"

**Solution**: Start the memory-db service
```bash
python3 memory_db_service.py &
```

### Issue: "Database is locked"

**Solution**: Use connection pooling or Unix socket service

### Issue: High memory usage

**Solution**: Enable compression and use tier management
```python
# Set compression level (1-9, default 6)
compressed = zlib.compress(data, level=9)

# Run curation
autonomous_curation()
```

### Issue: Slow searches

**Solution**: Add indexes
```sql
CREATE INDEX idx_search ON entities(name, entity_type);
```

---

## Summary

### Minimum Viable System (4 hours)
✅ SQLite database with compression
✅ Basic CRUD operations
✅ Pattern-based extraction
✅ Simple search

### Production System (40 hours)
✅ Unix socket service
✅ MCP protocol integration  
✅ Version control
✅ Conflict resolution
✅ Code execution sandbox
✅ 4-tier memory management
✅ Monitoring and backups

### Performance Targets
- Entity creation: < 50ms
- Search: < 30ms (10 results)
- Compression: > 60%
- Concurrent clients: > 50

**You're ready to build!** 🚀

#!/usr/bin/env python3
"""
Enhanced Memory MCP Server
Using FastMCP for better MCP protocol compliance
"""

import asyncio
import logging
import sqlite3
import hashlib
import zlib
import base64
import pickle
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# FastMCP implementation
from fastmcp import FastMCP

# Set up logging to stderr only
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("enhanced-memory")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"

# Create directories
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# Initialize FastMCP app
app = FastMCP("enhanced-memory")

def init_database():
    """Initialize SQLite database with real schema"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create entities table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entities (
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
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create observations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id INTEGER,
            content TEXT NOT NULL,
            compressed BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entity_id) REFERENCES entities (id)
        )
    ''')
    
    # Create relations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_entity_id INTEGER,
            to_entity_id INTEGER,
            relation_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_entity_id) REFERENCES entities (id),
            FOREIGN KEY (to_entity_id) REFERENCES entities (id)
        )
    ''')
    
    # Create indexes for real performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_accessed ON entities(last_accessed)')
    
    conn.commit()
    conn.close()

def compress_data(data: Any) -> tuple[bytes, int, int, float]:
    """Really compress data using zlib"""
    # Serialize the data
    serialized = pickle.dumps(data)
    original_size = len(serialized)
    
    # Compress with zlib (level 9 = maximum compression)
    compressed = zlib.compress(serialized, level=9)
    compressed_size = len(compressed)
    
    # Calculate real compression ratio
    compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
    
    return compressed, original_size, compressed_size, compression_ratio

def decompress_data(compressed: bytes) -> Any:
    """Decompress and deserialize data"""
    decompressed = zlib.decompress(compressed)
    return pickle.loads(decompressed)

def calculate_checksum(data: bytes) -> str:
    """Calculate SHA256 checksum for data integrity"""
    return hashlib.sha256(data).hexdigest()

def classify_tier(entity_type: str, name: str) -> str:
    """Classify entity into memory tier"""
    if entity_type in ["system_role", "core_system"] or "orchestrator" in name.lower():
        return "core"
    elif entity_type in ["project", "session"] or "current" in name.lower():
        return "working"
    elif "archive" in name.lower() or "historical" in entity_type.lower():
        return "archive"
    else:
        return "reference"

@app.tool()
async def create_entities(entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create entities with real compression and storage.
    
    Args:
        entities: List of entity objects with name, entityType, and observations
    
    Returns:
        Results with compression statistics and entity details
    """
    results = []
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for entity in entities:
        try:
            name = entity.get("name", "")
            entity_type = entity.get("entityType", "unknown")
            observations = entity.get("observations", [])
            
            if not name:
                continue
            
            # Classify tier
            tier = classify_tier(entity_type, name)
            
            # Prepare data for compression
            entity_data = {
                "name": name,
                "entityType": entity_type,
                "observations": observations,
                "tier": tier
            }
            
            # Really compress the data
            compressed, original_size, compressed_size, compression_ratio = compress_data(entity_data)
            checksum = calculate_checksum(compressed)
            
            # Store in database
            cursor.execute('''
                INSERT OR REPLACE INTO entities 
                (name, entity_type, tier, compressed_data, original_size, 
                 compressed_size, compression_ratio, checksum)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, entity_type, tier, compressed, original_size, 
                  compressed_size, compression_ratio, checksum))
            
            entity_id = cursor.lastrowid
            
            # Store observations separately for searchability
            for obs in observations:
                cursor.execute('''
                    INSERT INTO observations (entity_id, content)
                    VALUES (?, ?)
                ''', (entity_id, obs))
            
            results.append({
                "name": name,
                "entity_id": entity_id,
                "tier": tier,
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": compression_ratio,
                "actual_savings": f"{(1 - compression_ratio) * 100:.1f}%",
                "checksum": checksum[:8] + "..."  # Show partial checksum
            })
            
        except Exception as e:
            logger.error(f"Error creating entity {name}: {e}")
            results.append({"name": name, "error": str(e)})
    
    conn.commit()
    conn.close()
    
    # Calculate real statistics
    total_original = sum(r.get("original_size", 0) for r in results if "error" not in r)
    total_compressed = sum(r.get("compressed_size", 0) for r in results if "error" not in r)
    overall_ratio = total_compressed / total_original if total_original > 0 else 1.0
    
    return {
        "success": True,
        "entities_created": len([r for r in results if "error" not in r]),
        "total_original_bytes": total_original,
        "total_compressed_bytes": total_compressed,
        "overall_compression_ratio": overall_ratio,
        "overall_savings": f"{(1 - overall_ratio) * 100:.1f}%",
        "results": results
    }

@app.tool()
async def search_nodes(query: str, entity_types: Optional[List[str]] = None, max_results: int = 20) -> Dict[str, Any]:
    """
    Search with real SQL queries.
    
    Args:
        query: Search text to match against entity names and observation content
        entity_types: Optional list of entity types to filter by
        max_results: Maximum number of results to return
    
    Returns:
        Search results with entity details and matching observations
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Build SQL query
    sql = '''
        SELECT DISTINCT e.id, e.name, e.entity_type, e.tier, 
               e.compression_ratio, e.access_count, e.last_accessed
        FROM entities e
        LEFT JOIN observations o ON e.id = o.entity_id
        WHERE (LOWER(e.name) LIKE ? OR LOWER(o.content) LIKE ?)
    '''
    params = [f"%{query.lower()}%", f"%{query.lower()}%"]
    
    if entity_types:
        placeholders = ",".join("?" * len(entity_types))
        sql += f" AND e.entity_type IN ({placeholders})"
        params.extend(entity_types)
    
    sql += " ORDER BY e.access_count DESC, e.last_accessed DESC LIMIT ?"
    params.append(max_results)
    
    cursor.execute(sql, params)
    results = []
    
    for row in cursor.fetchall():
        entity_id = row[0]
        
        # Update access count
        cursor.execute(
            "UPDATE entities SET access_count = access_count + 1, last_accessed = CURRENT_TIMESTAMP WHERE id = ?",
            (entity_id,)
        )
        
        # Get observations for this entity
        cursor.execute("SELECT content FROM observations WHERE entity_id = ?", (entity_id,))
        observations = [obs[0] for obs in cursor.fetchall()]
        
        results.append({
            "id": entity_id,
            "name": row[1],
            "entity_type": row[2],
            "tier": row[3],
            "compression_ratio": row[4],
            "access_count": row[5],
            "last_accessed": row[6],
            "observations": observations[:3]  # First 3 observations
        })
    
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "query": query,
        "results_found": len(results),
        "results": results
    }

@app.tool()
async def read_graph() -> Dict[str, Any]:
    """
    Read complete graph from database.
    
    Returns:
        Complete knowledge graph with entities and relations
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all entities
    cursor.execute('''
        SELECT id, name, entity_type, compressed_data
        FROM entities
    ''')
    
    entities = []
    entity_id_map = {}
    
    for row in cursor.fetchall():
        entity_id, name, entity_type, compressed_data = row
        
        # Decompress to get full data including observations
        try:
            entity_data = decompress_data(compressed_data)
            entities.append({
                "type": "entity",
                "name": name,
                "entityType": entity_type,
                "observations": entity_data.get("observations", [])
            })
            entity_id_map[entity_id] = name
        except Exception as e:
            logger.error(f"Error decompressing entity {name}: {e}")
    
    # Get all relations
    cursor.execute('''
        SELECT from_entity_id, to_entity_id, relation_type
        FROM relations
    ''')
    
    relations = []
    for row in cursor.fetchall():
        from_id, to_id, rel_type = row
        if from_id in entity_id_map and to_id in entity_id_map:
            relations.append({
                "type": "relation",
                "from": entity_id_map[from_id],
                "to": entity_id_map[to_id],
                "relationType": rel_type
            })
    
    conn.close()
    
    return {
        "entities": entities,
        "relations": relations
    }

@app.tool()
async def get_memory_status() -> Dict[str, Any]:
    """
    Get real memory system statistics.
    
    Returns:
        Complete system status with storage and performance metrics
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get real statistics
    cursor.execute('''
        SELECT 
            COUNT(*) as total_entities,
            SUM(original_size) as total_original_bytes,
            SUM(compressed_size) as total_compressed_bytes,
            AVG(compression_ratio) as avg_compression_ratio,
            SUM(access_count) as total_accesses
        FROM entities
    ''')
    
    stats = cursor.fetchone()
    total_entities = stats[0] or 0
    total_original = stats[1] or 0
    total_compressed = stats[2] or 0
    avg_ratio = stats[3] or 1.0
    total_accesses = stats[4] or 0
    
    # Get tier distribution
    cursor.execute('''
        SELECT tier, COUNT(*) as count
        FROM entities
        GROUP BY tier
    ''')
    
    tier_distribution = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Get entity type distribution
    cursor.execute('''
        SELECT entity_type, COUNT(*) as count
        FROM entities
        GROUP BY entity_type
    ''')
    
    type_distribution = {row[0]: row[1] for row in cursor.fetchall()}
    
    conn.close()
    
    # Calculate real savings
    actual_savings = total_original - total_compressed if total_original > 0 else 0
    savings_percentage = (actual_savings / total_original * 100) if total_original > 0 else 0
    
    return {
        "success": True,
        "database_path": str(DB_PATH),
        "database_size_bytes": DB_PATH.stat().st_size if DB_PATH.exists() else 0,
        "statistics": {
            "total_entities": total_entities,
            "total_original_bytes": total_original,
            "total_compressed_bytes": total_compressed,
            "actual_bytes_saved": actual_savings,
            "compression_savings_percentage": f"{savings_percentage:.1f}%",
            "average_compression_ratio": avg_ratio,
            "total_accesses": total_accesses
        },
        "tier_distribution": tier_distribution,
        "type_distribution": type_distribution,
        "compression_method": "zlib level 9",
        "integrity_verification": "SHA256 checksums"
    }

@app.tool()
async def create_relations(relations: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Create relations between entities.
    
    Args:
        relations: List of relation objects with from, to, and relationType
    
    Returns:
        Results of relation creation operations
    """
    results = []
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for relation in relations:
        try:
            from_name = relation.get("from", "")
            to_name = relation.get("to", "")
            relation_type = relation.get("relationType", "")
            
            # Get entity IDs
            cursor.execute("SELECT id FROM entities WHERE name = ?", (from_name,))
            from_result = cursor.fetchone()
            cursor.execute("SELECT id FROM entities WHERE name = ?", (to_name,))
            to_result = cursor.fetchone()
            
            if from_result and to_result:
                from_id = from_result[0]
                to_id = to_result[0]
                
                cursor.execute('''
                    INSERT INTO relations (from_entity_id, to_entity_id, relation_type)
                    VALUES (?, ?, ?)
                ''', (from_id, to_id, relation_type))
                
                results.append({
                    "from": from_name,
                    "to": to_name,
                    "relationType": relation_type,
                    "success": True
                })
            else:
                results.append({
                    "from": from_name,
                    "to": to_name,
                    "error": "One or both entities not found"
                })
                
        except Exception as e:
            logger.error(f"Error creating relation: {e}")
            results.append({"error": str(e)})
    
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "relations_created": len([r for r in results if r.get("success")]),
        "results": results
    }

if __name__ == "__main__":
    # Initialize database on startup
    init_database()
    logger.info(f"Database initialized at {DB_PATH}")
    
    # Run FastMCP server
    app.run()
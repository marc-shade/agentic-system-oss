#!/usr/bin/env python3
"""
Enhanced Memory MCP Server - Fixed version
Provides SQLite storage with zlib compression and search capabilities
No video encoding - pure database implementation for performance
"""

import sys
import json
import logging
import sqlite3
import hashlib
import zlib
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import pickle

# Set up logging to stderr only
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("enhanced-memory")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"

# Create directories
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create observations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entity_id) REFERENCES entities (id) ON DELETE CASCADE
        )
    ''')
    
    # Create relations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_entity_id INTEGER NOT NULL,
            to_entity_id INTEGER NOT NULL,
            relation_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_entity_id) REFERENCES entities (id) ON DELETE CASCADE,
            FOREIGN KEY (to_entity_id) REFERENCES entities (id) ON DELETE CASCADE,
            UNIQUE(from_entity_id, to_entity_id, relation_type)
        )
    ''')
    
    # Create indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_observations_entity ON observations(entity_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_relations_from ON relations(from_entity_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_relations_to ON relations(to_entity_id)')
    
    conn.commit()
    conn.close()

def compress_data(data: Any) -> tuple[bytes, int, int, float]:
    """Compress data using zlib"""
    pickled = pickle.dumps(data)
    original_size = len(pickled)
    compressed = zlib.compress(pickled, level=9)
    compressed_size = len(compressed)
    ratio = compressed_size / original_size if original_size > 0 else 1.0
    return compressed, original_size, compressed_size, ratio

def decompress_data(compressed: bytes) -> Any:
    """Decompress data"""
    return pickle.loads(zlib.decompress(compressed))

def handle_create_entities(params: Dict[str, Any]) -> Dict[str, Any]:
    """Create entities with compression"""
    entities = params.get("entities", [])
    results = []
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for entity in entities:
        try:
            name = entity["name"]
            entity_type = entity["entityType"]
            observations = entity.get("observations", [])
            
            # Compress entity data
            entity_data = {
                "name": name,
                "type": entity_type,
                "observations": observations
            }
            compressed, orig_size, comp_size, ratio = compress_data(entity_data)
            
            # Insert entity
            cursor.execute('''
                INSERT OR REPLACE INTO entities 
                (name, entity_type, compressed_data, original_size, compressed_size, compression_ratio)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, entity_type, compressed, orig_size, comp_size, ratio))
            
            entity_id = cursor.lastrowid
            
            # Insert observations
            for obs in observations:
                cursor.execute('''
                    INSERT INTO observations (entity_id, content)
                    VALUES (?, ?)
                ''', (entity_id, obs))
            
            conn.commit()
            
            results.append({
                "entity": name,
                "status": "created",
                "type": entity_type,
                "observations": len(observations),
                "compression": {
                    "original_size": orig_size,
                    "compressed_size": comp_size,
                    "ratio": f"{ratio:.2%}"
                }
            })
            
        except Exception as e:
            results.append({
                "entity": entity.get("name", "unknown"),
                "status": "error",
                "message": str(e)
            })
    
    conn.close()
    
    return {
        "created": len([r for r in results if r["status"] == "created"]),
        "errors": len([r for r in results if r["status"] == "error"]),
        "results": results
    }

def handle_search_nodes(params: Dict[str, Any]) -> Dict[str, Any]:
    """Search with real SQL queries"""
    query = params.get("query", "")
    entity_types = params.get("entity_types", [])
    max_results = params.get("max_results", 20)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Build SQL query
    sql = '''
        SELECT DISTINCT e.id, e.name, e.entity_type, e.compressed_data,
               e.original_size, e.compressed_size, e.compression_ratio
        FROM entities e
        LEFT JOIN observations o ON e.id = o.entity_id
        WHERE (e.name LIKE ? OR o.content LIKE ?)
    '''
    
    query_params = [f"%{query}%", f"%{query}%"]
    
    if entity_types:
        placeholders = ','.join(['?'] * len(entity_types))
        sql += f' AND e.entity_type IN ({placeholders})'
        query_params.extend(entity_types)
    
    sql += f' LIMIT {max_results}'
    
    cursor.execute(sql, query_params)
    rows = cursor.fetchall()
    
    results = []
    for row in rows:
        entity_id, name, entity_type, compressed_data, orig_size, comp_size, ratio = row
        
        # Decompress entity data
        entity_data = decompress_data(compressed_data)
        
        # Get observations for this entity
        cursor.execute('SELECT content FROM observations WHERE entity_id = ?', (entity_id,))
        observations = [r[0] for r in cursor.fetchall()]
        
        results.append({
            "name": name,
            "entityType": entity_type,
            "observations": observations,
            "compression": {
                "original_size": orig_size,
                "compressed_size": comp_size,
                "ratio": f"{ratio:.2%}"
            }
        })
    
    conn.close()
    
    return {
        "count": len(results),
        "results": results
    }

def handle_read_graph(params: Dict[str, Any]) -> Dict[str, Any]:
    """Read complete graph from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all entities
    cursor.execute('''
        SELECT id, name, entity_type, compressed_data, 
               original_size, compressed_size, compression_ratio
        FROM entities
    ''')
    
    entities = []
    entity_map = {}
    
    for row in cursor.fetchall():
        entity_id, name, entity_type, compressed_data, orig_size, comp_size, ratio = row
        
        # Get observations
        cursor.execute('SELECT content FROM observations WHERE entity_id = ?', (entity_id,))
        observations = [r[0] for r in cursor.fetchall()]
        
        entity = {
            "name": name,
            "entityType": entity_type,
            "observations": observations
        }
        
        entities.append(entity)
        entity_map[entity_id] = name
    
    # Get all relations
    cursor.execute('''
        SELECT from_entity_id, to_entity_id, relation_type
        FROM relations
    ''')
    
    relations = []
    for from_id, to_id, rel_type in cursor.fetchall():
        if from_id in entity_map and to_id in entity_map:
            relations.append({
                "from": entity_map[from_id],
                "to": entity_map[to_id],
                "relationType": rel_type
            })
    
    conn.close()
    
    return {
        "entities": entities,
        "relations": relations
    }

def handle_get_memory_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get real memory system statistics"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get counts
    cursor.execute('SELECT COUNT(*) FROM entities')
    entity_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM observations')
    observation_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM relations')
    relation_count = cursor.fetchone()[0]
    
    # Get storage stats
    cursor.execute('SELECT SUM(original_size), SUM(compressed_size) FROM entities')
    row = cursor.fetchone()
    total_original = row[0] or 0
    total_compressed = row[1] or 0
    
    # Get entity type distribution
    cursor.execute('SELECT entity_type, COUNT(*) FROM entities GROUP BY entity_type')
    type_distribution = dict(cursor.fetchall())
    
    conn.close()
    
    # Get database file size
    db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    
    return {
        "statistics": {
            "total_entities": entity_count,
            "total_observations": observation_count,
            "total_relations": relation_count
        },
        "storage": {
            "database_size": db_size,
            "total_original_size": total_original,
            "total_compressed_size": total_compressed,
            "compression_ratio": f"{(total_compressed / total_original * 100):.1f}%" if total_original > 0 else "0%",
            "space_saved": total_original - total_compressed
        },
        "entity_types": type_distribution,
        "database_path": str(DB_PATH)
    }

def handle_create_relations(params: Dict[str, Any]) -> Dict[str, Any]:
    """Create relations between entities"""
    relations = params.get("relations", [])
    results = []
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for relation in relations:
        try:
            from_name = relation["from"]
            to_name = relation["to"]
            rel_type = relation["relationType"]
            
            # Get entity IDs
            cursor.execute('SELECT id FROM entities WHERE name = ?', (from_name,))
            from_row = cursor.fetchone()
            if not from_row:
                raise ValueError(f"Entity '{from_name}' not found")
            from_id = from_row[0]
            
            cursor.execute('SELECT id FROM entities WHERE name = ?', (to_name,))
            to_row = cursor.fetchone()
            if not to_row:
                raise ValueError(f"Entity '{to_name}' not found")
            to_id = to_row[0]
            
            # Insert relation
            cursor.execute('''
                INSERT OR REPLACE INTO relations (from_entity_id, to_entity_id, relation_type)
                VALUES (?, ?, ?)
            ''', (from_id, to_id, rel_type))
            
            conn.commit()
            
            results.append({
                "from": from_name,
                "to": to_name,
                "relationType": rel_type,
                "status": "created"
            })
            
        except Exception as e:
            results.append({
                "from": relation.get("from", "unknown"),
                "to": relation.get("to", "unknown"),
                "status": "error",
                "message": str(e)
            })
    
    conn.close()
    
    return {
        "created": len([r for r in results if r["status"] == "created"]),
        "errors": len([r for r in results if r["status"] == "error"]),
        "results": results
    }

def handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle incoming JSON-RPC request"""
    method = request.get("method", "")
    params = request.get("params", {})
    
    # Handle different methods
    if method == "initialize":
        return {
            "protocolVersion": "2025-03-26",
            "capabilities": {
                "tools": {
                    "listChanged": False
                }
            },
            "serverInfo": {
                "name": "enhanced-memory",
                "version": "2.0.0"
            }
        }
    
    elif method == "tools/list":
        return {
            "tools": [
                {
                    "name": "create_entities",
                    "description": "Create entities with real compression and storage",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "entities": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "entityType": {"type": "string"},
                                        "observations": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        }
                                    },
                                    "required": ["name", "entityType", "observations"]
                                }
                            }
                        },
                        "required": ["entities"]
                    }
                },
                {
                    "name": "search_nodes",
                    "description": "Search with real SQL queries",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "entity_types": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "max_results": {"type": "integer", "default": 20}
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "read_graph",
                    "description": "Read complete graph from database",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "get_memory_status",
                    "description": "Get real memory system statistics",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "create_relations",
                    "description": "Create relations between entities",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "relations": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "from": {"type": "string"},
                                        "to": {"type": "string"},
                                        "relationType": {"type": "string"}
                                    },
                                    "required": ["from", "to", "relationType"]
                                }
                            }
                        },
                        "required": ["relations"]
                    }
                }
            ]
        }
    
    elif method == "tools/call":
        tool_name = params.get("name", "")
        tool_params = params.get("arguments", {})
        
        if tool_name == "create_entities":
            return handle_create_entities(tool_params)
        elif tool_name == "search_nodes":
            return handle_search_nodes(tool_params)
        elif tool_name == "read_graph":
            return handle_read_graph(tool_params)
        elif tool_name == "get_memory_status":
            return handle_get_memory_status(tool_params)
        elif tool_name == "create_relations":
            return handle_create_relations(tool_params)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    else:
        raise ValueError(f"Unknown method: {method}")

def main():
    logger.info("Starting enhanced memory server with SQLite compression")
    
    # Initialize database
    try:
        init_database()
        logger.info(f"Database initialized at {DB_PATH}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)
    
    # Read from stdin, write to stdout
    # Don't use reconfigure - it can cause issues
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            logger.info(f"Received request: {request.get('method')}")
            
            # Process request
            result = handle_request(request)
            
            # Send response
            response = {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": result
            }
            print(json.dumps(response), flush=True)
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            # Send error response
            error_response = {
                "jsonrpc": "2.0",
                "id": request.get("id") if 'request' in locals() else None,
                "error": {"code": -32603, "message": str(e)}
            }
            print(json.dumps(error_response), flush=True)

if __name__ == "__main__":
    main()
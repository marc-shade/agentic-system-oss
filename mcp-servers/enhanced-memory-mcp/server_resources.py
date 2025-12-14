#!/usr/bin/env python3
"""
Enhanced Memory MCP Server with Resources Support
Using FastMCP for better MCP protocol compliance with browseable memory resources
"""

import asyncio
import logging
import sqlite3
import hashlib
import zlib
import json
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

def simplify_schema(schema):
    """
    Simplify JSON schema for Claude Code compatibility.
    Converts anyOf constructs to simple types.
    """
    if not isinstance(schema, dict):
        return schema
    
    schema = schema.copy()
    
    # Handle properties
    if 'properties' in schema:
        for prop_name, prop_def in schema['properties'].items():
            if isinstance(prop_def, dict) and 'anyOf' in prop_def:
                # Extract the main type from anyOf
                any_of = prop_def['anyOf']
                main_type = None
                additional_props = {}
                
                for option in any_of:
                    if isinstance(option, dict) and option.get('type') != 'null':
                        main_type = option.get('type')
                        # Copy additional properties like 'items' for arrays
                        if 'items' in option:
                            additional_props['items'] = option['items']
                        if 'additionalProperties' in option:
                            additional_props['additionalProperties'] = option['additionalProperties']
                        break
                
                if main_type:
                    # Replace anyOf with simple type
                    simplified_prop = {
                        'type': main_type,
                        **additional_props
                    }
                    # Keep title and default if they exist
                    if 'title' in prop_def:
                        simplified_prop['title'] = prop_def['title']
                    if 'default' in prop_def:
                        simplified_prop['default'] = prop_def['default']
                    
                    schema['properties'][prop_name] = simplified_prop
    
    return schema

# Monkey patch FastMCP to use simplified schemas
original_add_tool = app._tool_manager.add_tool_from_fn

def patched_add_tool_from_fn(*args, **kwargs):
    result = original_add_tool(*args, **kwargs)
    # Simplify the schema after tool is added
    if hasattr(result, 'parameters'):
        result.parameters = simplify_schema(result.parameters)
    return result

app._tool_manager.add_tool_from_fn = patched_add_tool_from_fn

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

# ===== MCP RESOURCES IMPLEMENTATION =====

@app.resource("memory://entities")
async def get_entities_resource_endpoint() -> str:
    """Resource endpoint for browsing all knowledge entities"""
    result = await get_entities_resource()
    return result["contents"][0]["text"]

@app.resource("memory://relations")
async def get_relations_resource_endpoint() -> str:
    """Resource endpoint for browsing entity relationships"""
    result = await get_relations_resource()
    return result["contents"][0]["text"]

@app.resource("memory://projects")
async def get_projects_resource_endpoint() -> str:
    """Resource endpoint for browsing project contexts"""
    result = await get_projects_resource()
    return result["contents"][0]["text"]

@app.resource("memory://insights")
async def get_insights_resource_endpoint() -> str:
    """Resource endpoint for browsing pattern insights"""
    result = await get_insights_resource()
    return result["contents"][0]["text"]

@app.resource("memory://status")
async def get_status_resource_endpoint() -> str:
    """Resource endpoint for system status"""
    result = await get_status_resource()
    return result["contents"][0]["text"]

@app.resource("memory://search/{query}")
async def get_search_resource_endpoint(query: str) -> str:
    """Resource endpoint for searching knowledge graph"""
    result = await get_search_resource(query)
    return result["contents"][0]["text"]

# Helper function for backward compatibility in testing
async def list_resources() -> List[Dict[str, Any]]:
    """List available memory resources for testing purposes"""
    return [
        {
            "uri": "memory://entities",
            "name": "Knowledge Entities",
            "description": "Browse all knowledge entities in the memory graph",
            "mimeType": "application/json"
        },
        {
            "uri": "memory://relations",
            "name": "Entity Relations", 
            "description": "Browse relationships between knowledge entities",
            "mimeType": "application/json"
        },
        {
            "uri": "memory://projects",
            "name": "Project Contexts",
            "description": "Browse project-specific knowledge contexts",
            "mimeType": "application/json"
        },
        {
            "uri": "memory://insights",
            "name": "Pattern Insights",
            "description": "Browse discovered patterns and insights from memory analysis",
            "mimeType": "application/json"
        },
        {
            "uri": "memory://search/{query}",
            "name": "Search Results",
            "description": "Search through knowledge graph - replace {query} with search terms",
            "mimeType": "application/json"
        },
        {
            "uri": "memory://status",
            "name": "Memory System Status",
            "description": "Current status and statistics of the memory system",
            "mimeType": "application/json"
        }
    ]

# Helper function for backward compatibility in testing  
async def get_resource(uri: str) -> Dict[str, Any]:
    """Get resource content by URI"""
    
    # Parse URI
    if not uri.startswith("memory://"):
        raise ValueError(f"Invalid resource URI: {uri}")
    
    resource_path = uri[9:]  # Remove "memory://" prefix
    
    try:
        if resource_path == "entities":
            return await get_entities_resource()
        elif resource_path == "relations":
            return await get_relations_resource()
        elif resource_path == "projects":
            return await get_projects_resource()
        elif resource_path == "insights":
            return await get_insights_resource()
        elif resource_path == "status":
            return await get_status_resource()
        elif resource_path.startswith("search/"):
            query = resource_path[7:]  # Remove "search/" prefix
            return await get_search_resource(query)
        else:
            raise ValueError(f"Unknown resource path: {resource_path}")
            
    except Exception as e:
        logger.error(f"Error getting resource {uri}: {e}")
        return {
            "contents": [{
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps({
                    "error": f"Failed to load resource: {str(e)}",
                    "uri": uri,
                    "timestamp": datetime.now().isoformat()
                })
            }]
        }

async def get_entities_resource() -> Dict[str, Any]:
    """Get all entities formatted for resource browsing"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Get entities with metadata
        cursor.execute('''
            SELECT e.id, e.name, e.entity_type, e.tier, e.compressed_data,
                   e.access_count, e.created_at, e.last_accessed,
                   e.compression_ratio, e.original_size, e.compressed_size
            FROM entities e
            ORDER BY e.tier, e.access_count DESC, e.last_accessed DESC
        ''')
        
        entities = []
        for row in cursor.fetchall():
            entity_id, name, entity_type, tier, compressed_data, access_count, created_at, last_accessed, compression_ratio, original_size, compressed_size = row
            
            # Decompress entity data to get observations
            try:
                entity_data = decompress_data(compressed_data)
                observations = entity_data.get("observations", [])
            except Exception as e:
                logger.warning(f"Failed to decompress entity {name}: {e}")
                observations = []
            
            entities.append({
                "id": entity_id,
                "name": name,
                "entityType": entity_type,
                "tier": tier,
                "observations": observations,
                "metadata": {
                    "access_count": access_count,
                    "created_at": created_at,
                    "last_accessed": last_accessed,
                    "compression_ratio": compression_ratio,
                    "original_size": original_size,
                    "compressed_size": compressed_size,
                    "savings": f"{(1 - compression_ratio) * 100:.1f}%" if compression_ratio else "0%"
                }
            })
        
        result = {
            "total_entities": len(entities),
            "by_tier": {},
            "by_type": {},
            "entities": entities,
            "timestamp": datetime.now().isoformat()
        }
        
        # Calculate tier distribution
        for entity in entities:
            tier = entity["tier"]
            result["by_tier"][tier] = result["by_tier"].get(tier, 0) + 1
            
            entity_type = entity["entityType"]
            result["by_type"][entity_type] = result["by_type"].get(entity_type, 0) + 1
        
        return {
            "contents": [{
                "uri": "memory://entities",
                "mimeType": "application/json",
                "text": json.dumps(result, indent=2)
            }]
        }
        
    finally:
        conn.close()

async def get_relations_resource() -> Dict[str, Any]:
    """Get all relations formatted for resource browsing"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Get relations with entity names
        cursor.execute('''
            SELECT r.id, r.relation_type, r.created_at,
                   e1.name as from_name, e1.entity_type as from_type,
                   e2.name as to_name, e2.entity_type as to_type
            FROM relations r
            JOIN entities e1 ON r.from_entity_id = e1.id
            JOIN entities e2 ON r.to_entity_id = e2.id
            ORDER BY r.created_at DESC
        ''')
        
        relations = []
        relation_types = {}
        
        for row in cursor.fetchall():
            rel_id, relation_type, created_at, from_name, from_type, to_name, to_type = row
            
            relations.append({
                "id": rel_id,
                "from": {
                    "name": from_name,
                    "type": from_type
                },
                "to": {
                    "name": to_name,
                    "type": to_type
                },
                "relationType": relation_type,
                "created_at": created_at
            })
            
            # Count relation types
            relation_types[relation_type] = relation_types.get(relation_type, 0) + 1
        
        result = {
            "total_relations": len(relations),
            "relation_types": relation_types,
            "relations": relations,
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "contents": [{
                "uri": "memory://relations",
                "mimeType": "application/json",
                "text": json.dumps(result, indent=2)
            }]
        }
        
    finally:
        conn.close()

async def get_projects_resource() -> Dict[str, Any]:
    """Get project-specific contexts formatted for resource browsing"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Get entities that represent projects
        cursor.execute('''
            SELECT e.name, e.entity_type, e.compressed_data, e.created_at, e.access_count
            FROM entities e
            WHERE e.entity_type IN ('project', 'system', 'context_project')
               OR e.name LIKE '%project%' 
               OR e.name LIKE '%context%'
            ORDER BY e.access_count DESC, e.created_at DESC
        ''')
        
        projects = []
        for row in cursor.fetchall():
            name, entity_type, compressed_data, created_at, access_count = row
            
            try:
                entity_data = decompress_data(compressed_data)
                observations = entity_data.get("observations", [])
            except Exception:
                observations = []
            
            projects.append({
                "name": name,
                "entityType": entity_type,
                "observations": observations,
                "created_at": created_at,
                "access_count": access_count
            })
        
        result = {
            "total_projects": len(projects),
            "projects": projects,
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "contents": [{
                "uri": "memory://projects",
                "mimeType": "application/json",
                "text": json.dumps(result, indent=2)
            }]
        }
        
    finally:
        conn.close()

async def get_insights_resource() -> Dict[str, Any]:
    """Get pattern insights and analytics formatted for resource browsing"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Analyze memory patterns
        insights = {}
        
        # Most accessed entities
        cursor.execute('''
            SELECT name, entity_type, access_count, last_accessed
            FROM entities
            ORDER BY access_count DESC
            LIMIT 10
        ''')
        insights["most_accessed"] = [
            {"name": row[0], "type": row[1], "access_count": row[2], "last_accessed": row[3]}
            for row in cursor.fetchall()
        ]
        
        # Newest entities
        cursor.execute('''
            SELECT name, entity_type, created_at
            FROM entities
            ORDER BY created_at DESC
            LIMIT 10
        ''')
        insights["newest_entities"] = [
            {"name": row[0], "type": row[1], "created_at": row[2]}
            for row in cursor.fetchall()
        ]
        
        # Compression statistics
        cursor.execute('''
            SELECT 
                AVG(compression_ratio) as avg_compression,
                MIN(compression_ratio) as best_compression,
                MAX(compression_ratio) as worst_compression,
                SUM(original_size) as total_original,
                SUM(compressed_size) as total_compressed
            FROM entities
        ''')
        stats = cursor.fetchone()
        if stats[0] is not None:
            total_original, total_compressed = stats[3], stats[4]
            insights["compression_stats"] = {
                "average_ratio": stats[0],
                "best_ratio": stats[1],
                "worst_ratio": stats[2],
                "total_original_bytes": total_original,
                "total_compressed_bytes": total_compressed,
                "total_savings_bytes": total_original - total_compressed,
                "total_savings_percent": f"{((total_original - total_compressed) / total_original * 100):.1f}%" if total_original > 0 else "0%"
            }
        
        # Tier distribution analysis
        cursor.execute('''
            SELECT tier, COUNT(*) as count, AVG(access_count) as avg_access
            FROM entities
            GROUP BY tier
        ''')
        insights["tier_analysis"] = [
            {"tier": row[0], "count": row[1], "avg_access": row[2]}
            for row in cursor.fetchall()
        ]
        
        # Relation patterns
        cursor.execute('''
            SELECT relation_type, COUNT(*) as count
            FROM relations
            GROUP BY relation_type
            ORDER BY count DESC
        ''')
        insights["relation_patterns"] = [
            {"type": row[0], "count": row[1]}
            for row in cursor.fetchall()
        ]
        
        result = {
            "insights": insights,
            "generated_at": datetime.now().isoformat(),
            "summary": f"Analyzed {len(insights.get('newest_entities', []))} entities with {len(insights.get('relation_patterns', []))} relation types"
        }
        
        return {
            "contents": [{
                "uri": "memory://insights",
                "mimeType": "application/json",
                "text": json.dumps(result, indent=2)
            }]
        }
        
    finally:
        conn.close()

async def get_search_resource(query: str) -> Dict[str, Any]:
    """Get search results formatted for resource browsing"""
    if not query:
        return {
            "contents": [{
                "uri": f"memory://search/{query}",
                "mimeType": "application/json",
                "text": json.dumps({
                    "error": "Empty search query",
                    "usage": "Use memory://search/{your_search_terms}"
                })
            }]
        }
    
    # Use existing search functionality
    search_result = await search_nodes(query, max_results=50)
    
    # Format for resource browsing
    result = {
        "query": query,
        "results_found": search_result["results_found"],
        "search_results": search_result["results"],
        "timestamp": datetime.now().isoformat()
    }
    
    return {
        "contents": [{
            "uri": f"memory://search/{query}",
            "mimeType": "application/json",
            "text": json.dumps(result, indent=2)
        }]
    }

async def get_status_resource() -> Dict[str, Any]:
    """Get system status formatted for resource browsing"""
    status_result = await get_memory_status()
    
    return {
        "contents": [{
            "uri": "memory://status",
            "mimeType": "application/json",
            "text": json.dumps(status_result, indent=2)
        }]
    }

# ===== EXISTING TOOLS (Preserved) =====

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
    logger.info("🎯 Enhanced Memory MCP Server with Resources support starting...")
    logger.info("📊 Available resources:")
    logger.info("  - memory://entities - Browse all knowledge entities")
    logger.info("  - memory://relations - Browse entity relationships")
    logger.info("  - memory://projects - Browse project contexts")
    logger.info("  - memory://insights - Browse pattern insights")
    logger.info("  - memory://search/{query} - Search knowledge graph")
    logger.info("  - memory://status - System status")
    
    # Run FastMCP server
    app.run()
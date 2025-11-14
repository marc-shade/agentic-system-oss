# Server.py Integration Changes for Cluster Memory

## Overview
This document details the exact changes needed to integrate cluster memory into the enhanced-memory MCP server.

## Required Changes

### 1. Import Statement (Add after line 85)

```python
# Import cluster memory management
CLUSTER_MEMORY_AVAILABLE = False
try:
    from cluster_memory import ClusterMemoryManager
    CLUSTER_MEMORY_AVAILABLE = True
    logging.info("🌐 Cluster memory management loaded successfully")
except (ImportError, ModuleNotFoundError) as e:
    CLUSTER_MEMORY_AVAILABLE = False
    logging.info(f"📝 Cluster memory management not available: {e}")
```

### 2. Global Variable (Add after line 146)

```python
cluster_memory_manager = None  # Added for cluster memory support
```

### 3. Initialization in init_components() (Add in init_components function)

```python
# Initialize cluster memory manager
global cluster_memory_manager

if CLUSTER_MEMORY_AVAILABLE:
    try:
        await asyncio.sleep(0)  # Yield control
        node_config_path = Path.home() / ".claude" / "node-config.json"
        if node_config_path.exists():
            cluster_memory_manager = ClusterMemoryManager(node_config_path)
            logger.info(f"🌐 Cluster memory manager initialized for node: {cluster_memory_manager.node_id}")
        else:
            cluster_memory_manager = None
            logger.info("📝 Node configuration not found - cluster memory disabled")
    except Exception as e:
        logger.error(f"⚠️ Failed to initialize cluster memory manager: {e}")
        cluster_memory_manager = None
else:
    cluster_memory_manager = None
```

### 4. Feature Tracking (Add in init_components after other features)

```python
if cluster_memory_manager:
    specialized_features.append(f"Cluster Memory (node: {cluster_memory_manager.node_id})")
```

### 5. Tool Definitions (Add to tools/list endpoint, around line 1372)

```python
{
    "name": "create_cluster_entity",
    "description": "🌐 CLUSTER: Create entity with node attribution (personal or shared scope)",
    "inputSchema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Entity name"},
            "entityType": {"type": "string", "description": "Type of entity"},
            "observations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Observations about the entity"
            },
            "scope": {
                "type": "string",
                "enum": ["personal", "shared"],
                "default": "personal",
                "description": "Memory scope: personal (node-specific) or shared (cluster-wide)"
            }
        },
        "required": ["name", "entityType", "observations"]
    }
},
{
    "name": "search_cluster_memories",
    "description": "🌐 CLUSTER: Search memories across personal, shared, or all scopes",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "scope": {
                "type": "string",
                "enum": ["personal", "shared", "all"],
                "default": "all",
                "description": "Search scope: personal, shared, or all"
            },
            "node_filter": {
                "type": "string",
                "description": "Filter by specific node ID (for shared memories only)"
            }
        },
        "required": ["query"]
    }
},
{
    "name": "get_node_memories",
    "description": "🌐 CLUSTER: Get all shared memories created by a specific node",
    "inputSchema": {
        "type": "object",
        "properties": {
            "node_id": {
                "type": "string",
                "description": "Node ID to retrieve memories from"
            }
        },
        "required": ["node_id"]
    }
},
{
    "name": "sync_to_cluster",
    "description": "🌐 CLUSTER: Promote a personal memory to cluster-wide shared memory",
    "inputSchema": {
        "type": "object",
        "properties": {
            "entity_name": {
                "type": "string",
                "description": "Name of entity to sync to cluster"
            }
        },
        "required": ["entity_name"]
    }
},
{
    "name": "get_cluster_stats",
    "description": "🌐 CLUSTER: Get cluster memory statistics for this node",
    "inputSchema": {
        "type": "object",
        "properties": {}
    }
}
```

### 6. Tool Handlers (Add in tools/call handler, around line 2506)

```python
# 🌐 Cluster Memory Operations
elif tool_name == "create_cluster_entity":
    if cluster_memory_manager:
        try:
            name = arguments.get("name", "")
            entity_type = arguments.get("entityType", "unknown")
            observations = arguments.get("observations", [])
            scope = arguments.get("scope", "personal")

            success = cluster_memory_manager.create_entity(name, entity_type, observations, scope)

            result = {
                "success": success,
                "entity": {
                    "name": name,
                    "type": entity_type,
                    "scope": scope,
                    "node_id": cluster_memory_manager.node_id
                },
                "timestamp": datetime.now().isoformat()
            }
            return {"jsonrpc": "2.0", "id": id, "result": {"content": [{"type": "text", "text": json.dumps(result)}]}}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": id, "result": {"content": [{"type": "text", "text": json.dumps({"error": f"Create cluster entity failed: {str(e)}"})}]}}
    else:
        return {"jsonrpc": "2.0", "id": id, "result": {"content": [{"type": "text", "text": json.dumps({"error": "Cluster memory not available"})}]}}

elif tool_name == "search_cluster_memories":
    if cluster_memory_manager:
        try:
            query = arguments.get("query", "")
            scope = arguments.get("scope", "all")
            node_filter = arguments.get("node_filter", None)

            results = cluster_memory_manager.search_entities(query, scope, node_filter)

            result = {
                "query": query,
                "scope": scope,
                "results": results,
                "count": len(results),
                "current_node": cluster_memory_manager.node_id
            }
            return {"jsonrpc": "2.0", "id": id, "result": {"content": [{"type": "text", "text": json.dumps(result)}]}}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": id, "result": {"content": [{"type": "text", "text": json.dumps({"error": f"Search cluster memories failed: {str(e)}"})}]}}
    else:
        return {"jsonrpc": "2.0", "id": id, "result": {"content": [{"type": "text", "text": json.dumps({"error": "Cluster memory not available"})}]}}

elif tool_name == "get_node_memories":
    if cluster_memory_manager:
        try:
            node_id = arguments.get("node_id", "")
            if not node_id:
                return {"jsonrpc": "2.0", "id": id, "result": {"content": [{"type": "text", "text": json.dumps({"error": "node_id parameter required"})}]}}

            memories = cluster_memory_manager.get_node_memories(node_id)
            result = {
                "node_id": node_id,
                "memories": memories,
                "count": len(memories),
                "current_node": cluster_memory_manager.node_id
            }
            return {"jsonrpc": "2.0", "id": id, "result": {"content": [{"type": "text", "text": json.dumps(result)}]}}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": id, "result": {"content": [{"type": "text", "text": json.dumps({"error": f"Get node memories failed: {str(e)}"})}]}}
    else:
        return {"jsonrpc": "2.0", "id": id, "result": {"content": [{"type": "text", "text": json.dumps({"error": "Cluster memory not available"})}]}}

elif tool_name == "sync_to_cluster":
    if cluster_memory_manager:
        try:
            entity_name = arguments.get("entity_name", "")
            if not entity_name:
                return {"jsonrpc": "2.0", "id": id, "result": {"content": [{"type": "text", "text": json.dumps({"error": "entity_name parameter required"})}]}}

            success = cluster_memory_manager.sync_to_cluster(entity_name)
            result = {
                "success": success,
                "entity_name": entity_name,
                "node_id": cluster_memory_manager.node_id,
                "message": f"Entity '{entity_name}' synced to cluster" if success else "Sync failed"
            }
            return {"jsonrpc": "2.0", "id": id, "result": {"content": [{"type": "text", "text": json.dumps(result)}]}}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": id, "result": {"content": [{"type": "text", "text": json.dumps({"error": f"Sync to cluster failed: {str(e)}"})}]}}
    else:
        return {"jsonrpc": "2.0", "id": id, "result": {"content": [{"type": "text", "text": json.dumps({"error": "Cluster memory not available"})}]}}

elif tool_name == "get_cluster_stats":
    if cluster_memory_manager:
        try:
            stats = cluster_memory_manager.get_cluster_stats()
            return {"jsonrpc": "2.0", "id": id, "result": {"content": [{"type": "text", "text": json.dumps(stats)}]}}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": id, "result": {"content": [{"type": "text", "text": json.dumps({"error": f"Get cluster stats failed: {str(e)}"})}]}}
    else:
        return {"jsonrpc": "2.0", "id": id, "result": {"content": [{"type": "text", "text": json.dumps({"error": "Cluster memory not available"})}]}}
```

## Integration Checklist

- [ ] Import statement added
- [ ] Global variable declared
- [ ] Initialization code added to init_components()
- [ ] Feature tracking updated
- [ ] 5 tool definitions added to tools/list
- [ ] 5 tool handlers added to tools/call
- [ ] cluster_memory.py copied to MCP directory
- [ ] Node configuration created at ~/.claude/node-config.json
- [ ] Test script runs successfully
- [ ] Claude Code restarted

## Automated Integration

For macbook-air (Researcher), these changes have already been applied to:
`/Users/marc/Documents/Cline/MCP/enhanced-memory-mcp/server.py`

For other nodes, you can either:
1. Manually apply these changes to their server.py files
2. Copy the updated server.py from macbook-air to shared storage and then to other nodes

## Quick Copy Method

On macbook-air:
```bash
cp ~/Documents/Cline/MCP/enhanced-memory-mcp/server.py \
   /Volumes/SSDRAID0/agentic-system/cluster-deployment/server.py.integrated
```

On other nodes:
```bash
cp /Volumes/SSDRAID0/agentic-system/cluster-deployment/server.py.integrated \
   ~/Documents/Cline/MCP/enhanced-memory-mcp/server.py
```

**⚠️ Warning**: Only use the copy method if all nodes have the same base version of enhanced-memory-mcp. Otherwise, manually apply the changes.

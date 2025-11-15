#!/usr/bin/env python3
"""
MCP Protocol wrapper for enhanced-memory server
Implements proper MCP JSON-RPC protocol
"""

import sys
import json
import logging
from pathlib import Path

# Import the core server functionality
from server import (
    init_database_sync, create_entities, search_nodes,
    read_graph, get_memory_status, create_relations,
    DB_PATH
)

# Import context compression system
try:
    from compressed_context_integration import CompressedContextManager
    CONTEXT_COMPRESSION_AVAILABLE = True
    logging.info("🗜️ Context compression system loaded in wrapper")
except ImportError as e:
    CONTEXT_COMPRESSION_AVAILABLE = False
    logging.warning(f"⚠️ Context compression not available in wrapper: {e}")

# Set up logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("enhanced-memory-mcp")

# MCP Server info
SERVER_INFO = {
    "name": "enhanced-memory",
    "version": "1.0.0"
}

# Tool definitions
TOOLS = [
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
                "max_results": {"type": "integer"}
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

def handle_request(request):
    """Handle MCP protocol request with improved error handling and separation"""
    try:
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        # Core MCP protocol handlers (essential for communication)
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": SERVER_INFO
                }
            }
        
        elif method == "notifications/initialized":
            # No response needed for notifications
            return None
            
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": TOOLS}
            }
            
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            try:
                # CORE TOOL EXECUTION - Always succeeds (MCP protocol separation)
                result = execute_core_tool(tool_name, arguments)
                
                # OPTIONAL ENHANCEMENTS - Failures don't crash server
                result = apply_optional_enhancements(tool_name, result)
                
                if result is None:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Unknown tool: {tool_name}"
                        }
                    }
                    
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }]
                    }
                }
                
            except Exception as e:
                logger.error(f"Error calling tool {tool_name}: {e}")
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    except Exception as e:
        logger.error(f"Request handling error: {e}")
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "error": {
                "code": -32603,
                "message": "Internal error"
            }
        }

def main():
    """Main entry point"""
    logger.info("Starting enhanced memory MCP server")
    
    # Initialize database
    try:
        init_database_sync()
        logger.info(f"Database initialized at {DB_PATH}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)
    
    # Process requests from stdin
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            response = handle_request(request)
            
            # Only send response if not None (for notifications)
            if response is not None:
                print(json.dumps(response))
                sys.stdout.flush()
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                }
            }
            print(json.dumps(error_response))
            sys.stdout.flush()
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
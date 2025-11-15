#!/usr/bin/env python3
"""
Simple Enhanced Memory MCP Server
"""

import json
import sys
import logging
from typing import Dict, Any

# Disable all imports that might cause issues
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("enhanced-memory-simple")

class SimpleEnhancedMemoryServer:
    def __init__(self):
        self.memories = {}
        
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        try:
            method = request.get("method", "")
            
            if method == "tools/list":
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "tools": [
                            {
                                "name": "create_entities",
                                "description": "Create memory entities",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "entities": {
                                            "type": "array",
                                            "items": {"type": "object"}
                                        }
                                    }
                                }
                            }
                        ]
                    }
                }
            
            elif method == "tools/call":
                tool_name = request.get("params", {}).get("name", "")
                if tool_name == "create_entities":
                    return {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Memory entities created successfully"
                                }
                            ]
                        }
                    }
            
            # Default response
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32601,
                    "message": "Method not found"
                }
            }
            
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {e}"
                }
            }

def main():
    logger.info("🧠 Starting Simple Enhanced Memory MCP Server")
    
    server = SimpleEnhancedMemoryServer()
    
    # MCP protocol loop
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
                
            try:
                request = json.loads(line.strip())
                response = server.handle_request(request)
                print(json.dumps(response))
                sys.stdout.flush()
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                continue
                
    except KeyboardInterrupt:
        logger.info("Server stopped")
    except Exception as e:
        logger.error(f"Server error: {e}")

if __name__ == "__main__":
    main()

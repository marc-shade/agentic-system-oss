#!/usr/bin/env python3
"""
Debug version of enhanced memory server - minimal initialization
"""
import sys
import json
import logging

# Set up logging to stderr only
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("debug-memory")

def handle_request(request):
    """Handle MCP request - simplified"""
    method = request.get("method")
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "debug-enhanced-memory",
                    "version": "1.0.0"
                }
            }
        }
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0", 
            "id": request.get("id"),
            "result": {"tools": []}
        }
    else:
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }

def main():
    """Debug main loop - no background initialization"""
    logger.info("🐛 Debug server starting")
    
    # Ensure stdio is unbuffered for MCP communication
    sys.stdin.reconfigure(encoding='utf-8', newline='')
    sys.stdout.reconfigure(encoding='utf-8', newline='')
    
    logger.info("🎯 Debug server ready - listening for requests")
    
    # Process MCP requests in simple blocking loop
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            logger.info(f"Received request: {request.get('method')}")
            
            response = handle_request(request)
            
            if response:
                print(json.dumps(response))
                sys.stdout.flush()
                logger.info(f"Sent response for: {request.get('method')}")
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "id": request.get("id") if 'request' in locals() else 1,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
            print(json.dumps(error_response))
            sys.stdout.flush()

if __name__ == "__main__":
    main()
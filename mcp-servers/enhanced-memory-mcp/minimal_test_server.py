#!/usr/bin/env python3
"""
Minimal test server to isolate MCP communication issues
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
logger = logging.getLogger("minimal-test")

def handle_request(request):
    """Handle MCP requests"""
    method = request.get("method")
    request_id = request.get("id")
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2025-03-26",
                "capabilities": {
                    "tools": {"listChanged": True}
                },
                "serverInfo": {"name": "minimal-test", "version": "1.0.0"}
            }
        }
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": []}
        }
    elif method == "notifications/initialized":
        # No response needed for notifications
        return None
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        }

def main():
    """Main server loop"""
    logger.info("🚀 Minimal test server starting")
    
    # Ensure stdio is unbuffered for MCP communication
    sys.stdin.reconfigure(encoding='utf-8', newline='')
    sys.stdout.reconfigure(encoding='utf-8', newline='')
    
    logger.info("🎯 Server ready - listening for requests")
    
    # Process MCP requests
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            logger.info(f"Received request: {request.get('method')}")
            
            response = handle_request(request)
            if response is not None:
                print(json.dumps(response), flush=True)
                sys.stdout.flush()
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            continue
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(e)}
            }
            print(json.dumps(error_response))
            sys.stdout.flush()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("🛑 Server shutting down gracefully")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        sys.exit(1)
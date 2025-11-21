#!/usr/bin/env python
import asyncio
import json
import sys
import os
import datetime
from typing import Dict, Any, List
from loguru import logger

# Set up logging
log_dir = os.path.expanduser('~/.mcp/logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f'notification_manager_server_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

# Configure loguru logger
logger.remove()
logger.configure(handlers=[
    {"sink": sys.stderr, "level": "WARNING"},
    {"sink": log_file, "level": "WARNING", "rotation": "10 MB"}
])

logger.info("Notification Manager Server starting")

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.notification_manager import NotificationManager

class NotificationManagerServer:
    def __init__(self):
        self._running = False
        self._manager = None

    async def start(self):
        self._manager = NotificationManager()
        self._running = True

    async def stop(self):
        if self._manager:
            await self._manager.cleanup()
        self._running = False

    def is_running(self):
        return self._running

async def mcp_server():
    """Simple MCP server implementation that reads from stdin and writes to stdout."""
    try:
        logger.info("Starting notification manager server")
        
        # Create notification manager instance
        logger.debug("Creating NotificationManager instance")
        notification_manager = NotificationManager()
        logger.info("NotificationManager instance created successfully")
        
        # Get all tools
        logger.debug("Getting tools from NotificationManager")
        tools = notification_manager.get_tools()
        logger.info(f"Retrieved {len(tools)} tools from NotificationManager")
        for tool in tools:
            logger.debug(f"Tool: {tool.get('name')} - {tool.get('description')}")
        
        # Create a mapping of tool names to their handlers
        logger.debug("Creating tool handlers mapping")
        tool_handlers = {}
        
        # Add support for JSON-RPC initialize method
        def handle_initialize(protocolVersion=None, capabilities=None, clientInfo=None):
            logger.info(f"Handling initialize request: protocolVersion={protocolVersion}, clientInfo={clientInfo}")
            return {
                "serverInfo": {
                    "name": "Notification Manager MCP Server",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "notificationSupport": True
                }
            }
        
        # Add the initialize method handler
        tool_handlers['initialize'] = handle_initialize
        
        # Explicitly map the tool names from the MCP configuration to the handler methods
        tool_handlers['tool_send_notification'] = notification_manager.tool_send_notification
        tool_handlers['tool_get_notifications'] = notification_manager.tool_get_notifications
        tool_handlers['tool_get_active_subscriptions'] = notification_manager.tool_get_active_subscriptions
        
        logger.info(f"Mapped {len(tool_handlers)} tool handlers")
        for method_name in tool_handlers:
            logger.debug(f"Handler mapped: {method_name}")
            
        # Signal readiness by sending an empty line to stdout
        print("", flush=True)
    
        # Main server loop
        logger.info("Starting main server loop")
        while True:
            # Read a line from stdin
            logger.debug("Waiting for input from stdin")
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                logger.warning("Received empty line from stdin, exiting")
                break
            
            logger.debug(f"Received input: {line.strip()}")
                
            try:
                # Parse the JSON request
                request = json.loads(line)
                request_id = request.get('id')
                method = request.get('method')
                params = request.get('params', {})
                
                # Find and call the handler for the requested method
                handler = tool_handlers.get(method)
                if handler:
                    logger.info(f"Found handler for method: {method}")
                    try:
                        # Check if the handler is a coroutine function (async)
                        if asyncio.iscoroutinefunction(handler):
                            logger.debug(f"Executing async handler for {method}")
                            result = await handler(**params)
                        else:
                            logger.debug(f"Executing sync handler for {method}")
                            result = handler(**params)
                        
                        logger.debug(f"Handler result: {result}")
                        response = {
                            'id': request_id,
                            'result': result
                        }
                    except Exception as e:
                        # Provide detailed error information
                        logger.error(f"Error executing {method}: {str(e)}", exc_info=True)
                        response = {
                            'id': request_id,
                            'error': f'Error executing {method}: {str(e)}'
                        }
                else:
                    logger.warning(f"Method not found: {method}")
                    logger.debug(f"Available methods: {list(tool_handlers.keys())}")
                    response = {
                        'id': request_id,
                        'error': f'Method not found: {method}'
                    }
                    
                # Send the response
                logger.debug(f"Sending response: {response}")
                print(json.dumps(response), flush=True)
                logger.info("Response sent successfully")
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON request: {line.strip()}", exc_info=True)
                error_response = {
                    'id': None,
                    'error': 'Invalid JSON request'
                }
                logger.debug(f"Sending error response: {error_response}")
                print(json.dumps(error_response), flush=True)
                continue
    except Exception as e:
        logger.error(f"Unhandled exception in MCP server: {str(e)}", exc_info=True)
        # Try to send an error response to stdout
        try:
            error_response = {
                'id': None,
                'error': f'Unhandled server error: {str(e)}'
            }
            print(json.dumps(error_response), flush=True)
        except:
            pass  # If we can't even send an error response, just continue to cleanup
                
    finally:
        # Clean up resources
        await notification_manager.cleanup()

if __name__ == "__main__":
    # Run the server
    asyncio.run(mcp_server())

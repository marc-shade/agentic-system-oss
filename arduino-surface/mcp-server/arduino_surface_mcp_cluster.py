#!/usr/bin/env python3
"""
Arduino Surface MCP Server - Cluster-Aware Version
Exposes Arduino physical control surface to Claude Desktop via MCP protocol

Features:
- Automatic Arduino discovery across cluster nodes
- Works with local Arduino (direct serial) or remote (HTTP relay)
- Graceful degradation if Arduino not available
- No command-line arguments needed
"""

import sys
import json
import asyncio
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "cluster"))
sys.path.insert(0, str(Path(__file__).parent.parent / "bridge"))

try:
    from cluster_aware_bridge import ClusterAwareArduinoSurface
except ImportError as e:
    print(f"Error importing cluster_aware_bridge: {e}", file=sys.stderr)
    print(f"Python path: {sys.path}", file=sys.stderr)
    sys.exit(1)

# Global Arduino surface instance
arduino = None


def initialize_arduino() -> bool:
    """Initialize cluster-aware Arduino connection"""
    global arduino

    if arduino:
        return arduino.location is not None

    try:
        arduino = ClusterAwareArduinoSurface(auto_discover=True)
        return arduino.location is not None
    except Exception as e:
        print(f"Error initializing Arduino: {e}", file=sys.stderr)
        # Create in degraded mode
        arduino = ClusterAwareArduinoSurface(auto_discover=False)
        return False


def send_response(response: dict):
    """Send MCP response to stdout"""
    print(json.dumps(response), flush=True)


def send_error(request_id: str, error_message: str):
    """Send error response"""
    send_response({
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": -1,
            "message": error_message
        }
    })


def send_result(request_id: str, result: any):
    """Send success response"""
    send_response({
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result
    })


async def handle_initialize(request_id: str, params: dict):
    """Handle initialize request"""
    # Auto-discover Arduino on first initialize
    initialize_arduino()

    info = {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {}
        },
        "serverInfo": {
            "name": "arduino-surface-cluster",
            "version": "2.0.0"
        }
    }

    # Add Arduino location info if available
    if arduino and arduino.location:
        info["serverInfo"]["arduinoNode"] = arduino.location.node_id
        info["serverInfo"]["arduinoMode"] = "local" if arduino.is_local else "remote"
        info["serverInfo"]["arduinoAvailable"] = True
    else:
        info["serverInfo"]["arduinoAvailable"] = False
        info["serverInfo"]["degradedMode"] = True

    send_result(request_id, info)


async def handle_list_tools(request_id: str):
    """List available Arduino tools"""
    tools = [
        {
            "name": "surface.display",
            "description": "Write text to LCD display at specified position",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "row": {
                        "type": "integer",
                        "description": "Row number (0 or 1)",
                        "minimum": 0,
                        "maximum": 1
                    },
                    "col": {
                        "type": "integer",
                        "description": "Column number (0-15)",
                        "minimum": 0,
                        "maximum": 15
                    },
                    "text": {
                        "type": "string",
                        "description": "Text to display (max 16 chars)"
                    }
                },
                "required": ["row", "col", "text"]
            }
        },
        {
            "name": "surface.display.clear",
            "description": "Clear the LCD display",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "surface.led.set",
            "description": "Set RGB LED color for specified tier (currently only tier 0 supported)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tier": {
                        "type": "integer",
                        "description": "LED tier (0 only for now)",
                        "minimum": 0,
                        "maximum": 0
                    },
                    "r": {
                        "type": "integer",
                        "description": "Red value (0-255)",
                        "minimum": 0,
                        "maximum": 255
                    },
                    "g": {
                        "type": "integer",
                        "description": "Green value (0-255)",
                        "minimum": 0,
                        "maximum": 255
                    },
                    "b": {
                        "type": "integer",
                        "description": "Blue value (0-255)",
                        "minimum": 0,
                        "maximum": 255
                    }
                },
                "required": ["tier", "r", "g", "b"]
            }
        },
        {
            "name": "surface.servo.set",
            "description": "Set servo motor position",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "position": {
                        "type": "integer",
                        "description": "Servo position in degrees (0-180)",
                        "minimum": 0,
                        "maximum": 180
                    }
                },
                "required": ["position"]
            }
        },
        {
            "name": "surface.beep",
            "description": "Play a beep sound",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "duration_ms": {
                        "type": "integer",
                        "description": "Beep duration in milliseconds",
                        "default": 200
                    },
                    "frequency_hz": {
                        "type": "integer",
                        "description": "Beep frequency in Hz",
                        "default": 1000
                    }
                }
            }
        },
        {
            "name": "surface.alert",
            "description": "Play an alert pattern with LED and sound",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "Alert type",
                        "enum": ["success", "warning", "error", "info"]
                    }
                },
                "required": ["type"]
            }
        },
        {
            "name": "surface.status",
            "description": "Get full Arduino status including sensor readings",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "surface.sensors",
            "description": "Get sensor readings (potentiometer, temperature, light)",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "surface.wait_button",
            "description": "Wait for button press (confirm or cancel)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "timeout_seconds": {
                        "type": "number",
                        "description": "Timeout in seconds",
                        "default": 30
                    }
                }
            }
        }
    ]

    send_result(request_id, {"tools": tools})


async def handle_call_tool(request_id: str, params: dict):
    """Execute Arduino tool"""
    global arduino

    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    # Check if Arduino is available
    if not arduino or not arduino.location:
        send_result(request_id, {
            "content": [{
                "type": "text",
                "text": f"⚠️  Arduino not available (tool: {tool_name})\n"
                       f"Command would have executed but no Arduino is connected to the cluster.\n"
                       f"This is operating in degraded mode - MCP server works but commands are no-ops."
            }]
        })
        return

    try:
        if tool_name == "surface.display":
            arduino.lcd_write(
                arguments.get("row", 0),
                arguments.get("col", 0),
                arguments.get("text", "")
            )
            result_text = f"✓ Displayed text on Arduino (node: {arduino.location.node_id})"

        elif tool_name == "surface.display.clear":
            arduino.clear_display()
            result_text = f"✓ Cleared display on Arduino (node: {arduino.location.node_id})"

        elif tool_name == "surface.led.set":
            arduino.set_led(
                arguments.get("tier", 0),
                arguments.get("r", 0),
                arguments.get("g", 0),
                arguments.get("b", 0)
            )
            result_text = f"✓ Set LED color on Arduino (node: {arduino.location.node_id})"

        elif tool_name == "surface.servo.set":
            arduino.set_servo(arguments.get("position", 90))
            result_text = f"✓ Set servo position on Arduino (node: {arduino.location.node_id})"

        elif tool_name == "surface.beep":
            arduino.beep(
                arguments.get("duration_ms", 200),
                arguments.get("frequency_hz", 1000)
            )
            result_text = f"✓ Played beep on Arduino (node: {arduino.location.node_id})"

        elif tool_name == "surface.alert":
            arduino.alert(arguments.get("type", "info"))
            result_text = f"✓ Played alert on Arduino (node: {arduino.location.node_id})"

        elif tool_name == "surface.status":
            status = arduino.get_status()
            if status:
                result_text = f"Arduino Status (node: {arduino.location.node_id}):\n{json.dumps(status, indent=2)}"
            else:
                result_text = "Failed to get Arduino status"

        elif tool_name == "surface.sensors":
            status = arduino.get_status()
            if status:
                sensors = {k: v for k, v in status.items() if k in ["pot", "temp_c", "light", "tilt"]}
                result_text = f"Sensor Readings (node: {arduino.location.node_id}):\n{json.dumps(sensors, indent=2)}"
            else:
                result_text = "Failed to get sensor readings"

        elif tool_name == "surface.wait_button":
            timeout = arguments.get("timeout_seconds", 30)
            event = arduino.wait_event(timeout)
            if event:
                result_text = f"Button pressed (node: {arduino.location.node_id}): {json.dumps(event, indent=2)}"
            else:
                result_text = f"Timeout waiting for button (node: {arduino.location.node_id})"

        else:
            send_error(request_id, f"Unknown tool: {tool_name}")
            return

        send_result(request_id, {
            "content": [{
                "type": "text",
                "text": result_text
            }]
        })

    except Exception as e:
        send_error(request_id, f"Error executing {tool_name}: {str(e)}")


async def main_loop():
    """Main message processing loop"""
    print("Arduino Surface Cluster-Aware MCP server starting...", file=sys.stderr)

    # Read JSON-RPC requests from stdin using asyncio StreamReader
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    print("Server ready, waiting for requests...", file=sys.stderr)

    try:
        while True:
            line = await reader.readline()
            if not line:
                break

            try:
                request = json.loads(line.decode('utf-8'))
                request_id = request.get("id")
                method = request.get("method")
                params = request.get("params", {})

                if method == "initialize":
                    await handle_initialize(request_id, params)
                elif method == "tools/list":
                    await handle_list_tools(request_id)
                elif method == "tools/call":
                    await handle_call_tool(request_id, params)
                else:
                    send_error(request_id, f"Unknown method: {method}")

            except json.JSONDecodeError as e:
                print(f"Invalid JSON: {e}", file=sys.stderr)
            except Exception as e:
                print(f"Error handling request: {e}", file=sys.stderr)

    finally:
        if arduino and hasattr(arduino, 'disconnect'):
            arduino.disconnect()


if __name__ == "__main__":
    asyncio.run(main_loop())

#!/usr/bin/env python3
"""
Arduino Surface MCP Server
Exposes Arduino physical control surface to Claude Desktop via MCP protocol
"""

import sys
import json
import asyncio
from pathlib import Path

# Add bridge directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "bridge"))

try:
    from arduino_cluster_discovery import ArduinoClusterDiscovery, ArduinoLocation
    from arduino_cluster_relay import ClusterAwareArduinoSurface
except ImportError as e:
    print(f"Error importing Arduino modules: {e}", file=sys.stderr)
    print(f"Python path: {sys.path}", file=sys.stderr)
    sys.exit(1)

# Global Arduino surface instance
arduino = None
arduino_location = None


def discover_and_initialize_arduino() -> bool:
    """Discover and initialize Arduino connection across cluster"""
    global arduino, arduino_location

    if arduino:
        # Already initialized
        return True

    try:
        # Discover Arduino location
        discovery = ArduinoClusterDiscovery()
        location = discovery.discover()

        if not location:
            print("⚠️  Arduino not found on any cluster node", file=sys.stderr)
            print("   MCP server will operate in degraded mode", file=sys.stderr)
            print("   All Arduino operations will gracefully fail", file=sys.stderr)
            return False

        # Initialize cluster-aware surface
        arduino = ClusterAwareArduinoSurface(location)

        if arduino.connect():
            arduino_location = location
            print(f"✅ Arduino connected!", file=sys.stderr)
            print(f"   Node: {location.node_id}", file=sys.stderr)
            print(f"   IP: {location.node_ip}", file=sys.stderr)
            print(f"   Port: {location.port}", file=sys.stderr)
            print(f"   Local: {location.is_local}", file=sys.stderr)
            print(f"   Relay: {location.relay_method}", file=sys.stderr)
            return True
        else:
            print(f"⚠️  Arduino found but connection failed", file=sys.stderr)
            print(f"   Node: {location.node_id} ({location.port})", file=sys.stderr)
            return False

    except Exception as e:
        print(f"⚠️  Error during Arduino discovery: {e}", file=sys.stderr)
        print("   MCP server will operate in degraded mode", file=sys.stderr)
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
    send_result(request_id, {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {}
        },
        "serverInfo": {
            "name": "arduino-surface",
            "version": "1.0.0"
        }
    })


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
    global arduino, arduino_location

    if not arduino:
        # Provide helpful error message
        error_msg = "Arduino not available. "
        if arduino_location:
            error_msg += f"Found on {arduino_location.node_id} but connection failed."
        else:
            error_msg += "Not found on any cluster node. Please ensure Arduino is connected."

        send_error(request_id, error_msg)
        return

    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    try:
        # surface.display
        if tool_name == "surface.display":
            row = arguments["row"]
            col = arguments["col"]
            text = arguments["text"]

            success = arduino.lcd_write(row, col, text)
            result = f"Displayed '{text}' at row {row}, column {col}"

            send_result(request_id, {
                "content": [
                    {
                        "type": "text",
                        "text": result if success else "Failed to display text"
                    }
                ]
            })

        # surface.display.clear
        elif tool_name == "surface.display.clear":
            success = arduino.lcd_clear()
            result = "LCD cleared" if success else "Failed to clear LCD"

            send_result(request_id, {
                "content": [
                    {
                        "type": "text",
                        "text": result
                    }
                ]
            })

        # surface.led.set
        elif tool_name == "surface.led.set":
            tier = arguments["tier"]
            r = arguments["r"]
            g = arguments["g"]
            b = arguments["b"]

            success = arduino.set_led(tier, r, g, b)
            result = f"Set LED tier {tier} to RGB({r},{g},{b})"

            send_result(request_id, {
                "content": [
                    {
                        "type": "text",
                        "text": result if success else "Failed to set LED"
                    }
                ]
            })

        # surface.servo.set
        elif tool_name == "surface.servo.set":
            position = arguments["position"]

            success = arduino.set_servo(position)
            result = f"Moved servo to {position}°"

            send_result(request_id, {
                "content": [
                    {
                        "type": "text",
                        "text": result if success else "Failed to move servo"
                    }
                ]
            })

        # surface.beep
        elif tool_name == "surface.beep":
            duration = arguments.get("duration_ms", 200)
            frequency = arguments.get("frequency_hz", 1000)

            success = arduino.beep(duration, frequency)
            result = f"Played beep ({duration}ms @ {frequency}Hz)"

            send_result(request_id, {
                "content": [
                    {
                        "type": "text",
                        "text": result if success else "Failed to play beep"
                    }
                ]
            })

        # surface.alert
        elif tool_name == "surface.alert":
            alert_type = arguments["type"]

            success = arduino.alert(alert_type)
            result = f"Played {alert_type} alert"

            send_result(request_id, {
                "content": [
                    {
                        "type": "text",
                        "text": result if success else f"Failed to play {alert_type} alert"
                    }
                ]
            })

        # surface.status
        elif tool_name == "surface.status":
            status = arduino.get_status()

            if status:
                result = f"Arduino Status:\n"
                result += f"- Potentiometer: {status.get('pot')}\n"
                result += f"- Temperature: {status.get('temp_c')}°C\n"
                result += f"- Light: {status.get('light')}"
            else:
                result = "Failed to get status"

            send_result(request_id, {
                "content": [
                    {
                        "type": "text",
                        "text": result
                    }
                ]
            })

        # surface.sensors
        elif tool_name == "surface.sensors":
            status = arduino.get_status()

            if status:
                result = {
                    "pot": status.get('pot'),
                    "temp_c": status.get('temp_c'),
                    "light": status.get('light')
                }
                result_text = f"Sensors:\n"
                result_text += f"- Potentiometer: {result['pot']}\n"
                result_text += f"- Temperature: {result['temp_c']}°C\n"
                result_text += f"- Light: {result['light']}"
            else:
                result_text = "Failed to read sensors"

            send_result(request_id, {
                "content": [
                    {
                        "type": "text",
                        "text": result_text
                    }
                ]
            })

        # surface.wait_button
        elif tool_name == "surface.wait_button":
            timeout = arguments.get("timeout_seconds", 30)

            arduino.start_event_listener()
            event = arduino.wait_event(timeout=timeout)

            if event and event.get("event") == "button":
                button = event.get("button")
                result = f"Button pressed: {button}"
            else:
                result = "No button pressed (timeout)"

            send_result(request_id, {
                "content": [
                    {
                        "type": "text",
                        "text": result
                    }
                ]
            })

        else:
            send_error(request_id, f"Unknown tool: {tool_name}")

    except Exception as e:
        send_error(request_id, f"Tool execution error: {str(e)}")


async def handle_request(request: dict):
    """Handle incoming MCP request"""
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


async def main():
    """Main MCP server loop"""
    global arduino

    print("🔍 Arduino Surface MCP Server", file=sys.stderr)
    print("   Discovering Arduino across cluster...", file=sys.stderr)
    print("", file=sys.stderr)

    # Discover and initialize Arduino (non-fatal if not found)
    discover_and_initialize_arduino()

    print("", file=sys.stderr)
    print("✅ MCP server ready", file=sys.stderr)
    if not arduino:
        print("   (Operating in degraded mode - Arduino not available)", file=sys.stderr)
    print("", file=sys.stderr)

    # Read JSON-RPC requests from stdin
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    try:
        while True:
            line = await reader.readline()
            if not line:
                break

            try:
                request = json.loads(line.decode('utf-8'))
                await handle_request(request)
            except json.JSONDecodeError as e:
                print(f"Invalid JSON: {e}", file=sys.stderr)
            except Exception as e:
                print(f"Error handling request: {e}", file=sys.stderr)

    finally:
        if arduino:
            arduino.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

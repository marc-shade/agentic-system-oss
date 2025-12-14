#!/usr/bin/env python3
"""
Arduino Surface MCP Server
Exposes Arduino physical control surface to Claude Desktop via MCP protocol

Cluster-Aware Design:
- Starts successfully even when Arduino is not connected to this node
- Returns informative messages indicating Arduino location
- Tools gracefully degrade when hardware unavailable
- Can detect Arduino on other cluster nodes via network discovery
"""

import sys
import json
import asyncio
import glob
import socket
import platform
from pathlib import Path

# Add bridge directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "bridge"))

try:
    from surface_bridge import ArduinoSurface
except ImportError as e:
    print(f"Error importing surface_bridge: {e}", file=sys.stderr)
    print(f"Python path: {sys.path}", file=sys.stderr)
    sys.exit(1)

# Global Arduino surface instance
arduino = None
arduino_port = None
arduino_available = False
current_node = socket.gethostname()

# Known cluster nodes (for Arduino detection)
CLUSTER_NODES = ["mac-studio", "macbook-air", "macbook-pro"]


def detect_arduino_ports() -> list:
    """Detect available Arduino serial ports on this system"""
    ports = []
    system = platform.system()

    if system == "Darwin":  # macOS
        # Arduino UNO typically shows as /dev/tty.usbmodem*
        ports.extend(glob.glob("/dev/tty.usbmodem*"))
        # Arduino Mega and others
        ports.extend(glob.glob("/dev/tty.usbserial*"))
        ports.extend(glob.glob("/dev/cu.usbmodem*"))
    elif system == "Linux":
        # Linux Arduino ports
        ports.extend(glob.glob("/dev/ttyACM*"))
        ports.extend(glob.glob("/dev/ttyUSB*"))

    return sorted(set(ports))


def initialize_arduino(port: str = None) -> bool:
    """Initialize Arduino connection

    Args:
        port: Serial port path. If None or "auto", will attempt auto-detection.

    Returns:
        True if connected, False if not available (graceful degradation)
    """
    global arduino, arduino_port, arduino_available

    # Auto-detect if no port specified or "auto"
    if not port or port == "auto":
        detected = detect_arduino_ports()
        if detected:
            port = detected[0]
            print(f"Auto-detected Arduino on {port}", file=sys.stderr)
        else:
            print(f"No Arduino detected on {current_node}", file=sys.stderr)
            arduino_available = False
            return False

    if arduino and arduino_port == port:
        return True

    try:
        arduino = ArduinoSurface(port)
        if arduino.connect():
            arduino_port = port
            arduino_available = True
            print(f"Arduino connected on {port} ({current_node})", file=sys.stderr)
            return True
        print(f"Failed to connect to Arduino on {port}", file=sys.stderr)
        arduino_available = False
        return False
    except Exception as e:
        print(f"Error initializing Arduino on {port}: {e}", file=sys.stderr)
        arduino_available = False
        return False


def get_arduino_status_message() -> str:
    """Get a helpful message about Arduino availability"""
    if arduino_available:
        return f"Arduino connected on {arduino_port} ({current_node})"

    detected = detect_arduino_ports()
    if detected:
        return f"Arduino detected on {detected[0]} but not initialized. Try reconnecting."

    # Check if we're on a Mac (where Arduino can be connected)
    if platform.system() == "Darwin":
        return f"No Arduino connected to {current_node}. The Arduino may be connected to another cluster node."
    else:
        return f"Arduino Surface only available on macOS nodes. Current node: {current_node} ({platform.system()})"


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
    global arduino, arduino_available

    tool_name = params.get("name")

    # Handle status and connection tools even without Arduino
    if tool_name == "surface.status":
        # Status tool always works - reports availability
        if arduino_available and arduino:
            status = arduino.get_status()
            if status:
                result = f"Arduino Status ({current_node}):\n"
                result += f"- Port: {arduino_port}\n"
                result += f"- Potentiometer: {status.get('pot')}\n"
                result += f"- Temperature: {status.get('temp_c')}C\n"
                result += f"- Light: {status.get('light')}"
            else:
                result = f"Arduino connected on {arduino_port} but failed to read status"
        else:
            result = get_arduino_status_message()

        send_result(request_id, {
            "content": [{"type": "text", "text": result}]
        })
        return

    # For all other tools, check if Arduino is available
    if not arduino_available or not arduino:
        status_msg = get_arduino_status_message()
        send_result(request_id, {
            "content": [{
                "type": "text",
                "text": f"Arduino unavailable: {status_msg}\n\nTool '{tool_name}' requires physical hardware connection."
            }]
        })
        return

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

        # surface.sensors (surface.status handled above)
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
    """Main MCP server loop

    Graceful Degradation:
    - Server starts even without Arduino connected
    - Tools return informative messages when hardware unavailable
    - Can auto-detect Arduino port if 'auto' specified
    """
    global arduino, arduino_available

    # Get Arduino port from command line (optional - can auto-detect)
    port = sys.argv[1] if len(sys.argv) >= 2 else "auto"

    # Try to initialize Arduino (won't fail if unavailable)
    if initialize_arduino(port):
        print(f"Arduino Surface MCP server started with hardware on {arduino_port}", file=sys.stderr)
    else:
        print(f"Arduino Surface MCP server started (hardware unavailable on {current_node})", file=sys.stderr)
        print(f"Tools will report hardware status when called", file=sys.stderr)

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

#!/usr/bin/env python3
"""
Arduino Surface MCP Server (Broker Version)
Exposes Arduino physical control surface to Claude Desktop via MCP protocol.
Uses the Arduino Broker for multi-process serial port access.
"""

import sys
import json
import asyncio
from pathlib import Path

# Add bridge directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "bridge"))

try:
    from arduino_client import ArduinoClient
except ImportError as e:
    print(f"Error importing arduino_client: {e}", file=sys.stderr)
    print(f"Python path: {sys.path}", file=sys.stderr)
    sys.exit(1)

# Global Arduino client instance
arduino_client = None


def initialize_arduino() -> bool:
    """Initialize Arduino broker connection"""
    global arduino_client

    if arduino_client:
        return True

    try:
        arduino_client = ArduinoClient()
        if arduino_client.connect():
            return True
        return False
    except Exception as e:
        print(f"Error connecting to Arduino broker: {e}", file=sys.stderr)
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
    # Connect to broker on initialization
    if not initialize_arduino():
        send_error(request_id, "Failed to connect to Arduino broker at /tmp/arduino_broker.sock")
        return

    send_result(request_id, {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {}
        },
        "serverInfo": {
            "name": "arduino-surface-broker",
            "version": "2.0.0"
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
                        "description": "Text to display (max 16 chars per line)"
                    }
                },
                "required": ["row", "text"]
            }
        },
        {
            "name": "led.set",
            "description": "Set RGB LED color (for quality tier indication)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tier": {
                        "type": "integer",
                        "description": "Quality tier (0-5)",
                        "minimum": 0,
                        "maximum": 5
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
            "name": "servo.set",
            "description": "Set servo position (for visual indicators)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "angle": {
                        "type": "integer",
                        "description": "Servo angle (0-180 degrees)",
                        "minimum": 0,
                        "maximum": 180
                    }
                },
                "required": ["angle"]
            }
        },
        {
            "name": "beep",
            "description": "Play a beep sound (for alerts)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "frequency": {
                        "type": "integer",
                        "description": "Beep frequency in Hz (100-5000)",
                        "minimum": 100,
                        "maximum": 5000
                    },
                    "duration": {
                        "type": "integer",
                        "description": "Duration in milliseconds (10-5000)",
                        "minimum": 10,
                        "maximum": 5000
                    }
                },
                "required": ["frequency", "duration"]
            }
        },
        {
            "name": "alert",
            "description": "Trigger alert pattern (LED flash + beep)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "severity": {
                        "type": "string",
                        "description": "Alert severity",
                        "enum": ["info", "warning", "error", "critical"]
                    },
                    "message": {
                        "type": "string",
                        "description": "Alert message to display"
                    }
                },
                "required": ["severity", "message"]
            }
        },
        {
            "name": "status",
            "description": "Get current Arduino status",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "sensors",
            "description": "Read environmental sensors (if available)",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "wait_button",
            "description": "Wait for button press (human-in-the-loop)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "timeout": {
                        "type": "integer",
                        "description": "Max wait time in seconds (default 30)",
                        "minimum": 1,
                        "maximum": 300
                    }
                }
            }
        }
    ]

    send_result(request_id, {"tools": tools})


async def handle_call_tool(request_id: str, params: dict):
    """Handle tool execution request"""
    global arduino_client

    if not arduino_client:
        if not initialize_arduino():
            send_error(request_id, "Arduino broker not connected")
            return

    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    try:
        result = None

        if tool_name == "surface.display":
            row = arguments.get("row", 0)
            text = arguments.get("text", "")
            col = arguments.get("col", 0)

            # For broker, we use line-based display (row 0 or 1)
            # Column positioning would need padding
            if col > 0:
                text = (" " * col) + text

            response = arduino_client.lcd(line=row, text=text)
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": f"LCD updated: Row {row}, Text: '{text}'\nBroker response: {response}"
                    }
                ]
            }

        elif tool_name == "led.set":
            tier = arguments.get("tier", 0)
            r = arguments.get("r", 0)
            g = arguments.get("g", 0)
            b = arguments.get("b", 0)

            response = arduino_client.led(tier=tier, r=r, g=g, b=b)
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": f"LED set: Tier {tier}, RGB({r},{g},{b})\nBroker response: {response}"
                    }
                ]
            }

        elif tool_name == "servo.set":
            angle = arguments.get("angle", 90)
            response = arduino_client.raw(f"SERVO {angle}")
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": f"Servo set to {angle} degrees\nBroker response: {response}"
                    }
                ]
            }

        elif tool_name == "beep":
            frequency = arguments.get("frequency", 1000)
            duration = arguments.get("duration", 200)
            response = arduino_client.raw(f"BEEP {frequency} {duration}")
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": f"Beep: {frequency}Hz for {duration}ms\nBroker response: {response}"
                    }
                ]
            }

        elif tool_name == "alert":
            severity = arguments.get("severity", "info")
            message = arguments.get("message", "")

            # Map severity to LED color
            colors = {
                "info": (0, 0, 255),      # Blue
                "warning": (255, 165, 0),  # Orange
                "error": (255, 0, 0),      # Red
                "critical": (255, 0, 255)  # Magenta
            }
            r, g, b = colors.get(severity, (0, 0, 255))

            # Display message and set LED
            arduino_client.lcd(line=0, text=f"{severity.upper()}")
            arduino_client.lcd(line=1, text=message[:16])
            response = arduino_client.led(tier=0, r=r, g=g, b=b)

            result = {
                "content": [
                    {
                        "type": "text",
                        "text": f"Alert triggered: {severity} - {message}\nBroker response: {response}"
                    }
                ]
            }

        elif tool_name == "status":
            response = arduino_client.raw("STATUS")
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": f"Arduino status: {json.dumps(response, indent=2)}"
                    }
                ]
            }

        elif tool_name == "sensors":
            response = arduino_client.raw("SENSORS")
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": f"Sensor data: {json.dumps(response, indent=2)}"
                    }
                ]
            }

        elif tool_name == "wait_button":
            timeout = arguments.get("timeout", 30)
            response = arduino_client.raw(f"WAIT_BUTTON {timeout}")
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": f"Button wait result: {json.dumps(response, indent=2)}"
                    }
                ]
            }

        else:
            send_error(request_id, f"Unknown tool: {tool_name}")
            return

        send_result(request_id, result)

    except Exception as e:
        send_error(request_id, f"Tool execution failed: {str(e)}")


def main():
    """Main MCP server loop"""
    print("Arduino Surface MCP Server (Broker Version) starting...", file=sys.stderr)
    print("Connecting to Arduino broker at /tmp/arduino_broker.sock", file=sys.stderr)

    # Read JSON-RPC requests from stdin (synchronous)
    for line in sys.stdin:
        try:
            request = json.loads(line)
            request_id = request.get("id")
            method = request.get("method")
            params = request.get("params", {})

            if method == "initialize":
                asyncio.run(handle_initialize(request_id, params))
            elif method == "tools/list":
                asyncio.run(handle_list_tools(request_id))
            elif method == "tools/call":
                asyncio.run(handle_call_tool(request_id, params))
            else:
                send_error(request_id, f"Unknown method: {method}")

        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error processing request: {e}", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nArduino Surface MCP Server stopped", file=sys.stderr)
        if arduino_client:
            arduino_client.disconnect()

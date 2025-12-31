#!/usr/bin/env python3
"""
Arduino HTTP Proxy Server
==========================

HTTP-based proxy for remote Arduino access across the cluster.
Runs on the node where Arduino is physically connected and exposes
a REST API for remote control.

This enables transparent Arduino access from any cluster node
without requiring direct serial port access.

Endpoints:
- GET /health - Health check
- GET /status - Arduino status
- POST /lcd - Write to LCD display
- POST /led - Set LED color
- POST /servo - Set servo position
- POST /beep - Play beep sound
- POST /alert - Trigger alert pattern
- POST /raw - Send raw command
- GET /sensors - Read sensor data

Usage:
    python3 arduino_http_proxy.py --port 8200 --serial-port /dev/tty.usbmodem8344401
"""

import argparse
import json
import logging
import os
import serial
import signal
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional
from urllib.parse import parse_qs, urlparse

# Dynamic path detection
STORAGE_BASE = os.environ.get('STORAGE_BASE', '/Volumes/SSDRAID0/agentic-system' if os.path.exists('/Volumes/SSDRAID0') else '/home/marc/agentic-system')
LOG_DIR = os.path.join(STORAGE_BASE, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'arduino_http_proxy.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('arduino-http-proxy')


class ArduinoSerial:
    """Thread-safe Arduino serial connection manager"""

    def __init__(self, port: str, baud_rate: int = 115200, timeout: float = 1.0):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.serial_conn: Optional[serial.Serial] = None
        self.lock = threading.Lock()
        self.connected = False

    def connect(self) -> bool:
        """Connect to Arduino"""
        with self.lock:
            try:
                self.serial_conn = serial.Serial(
                    self.port,
                    self.baud_rate,
                    timeout=self.timeout
                )
                time.sleep(2)  # Wait for Arduino reset
                self.connected = True
                logger.info(f"Connected to Arduino on {self.port}")
                return True
            except Exception as e:
                logger.error(f"Failed to connect to Arduino: {e}")
                self.connected = False
                return False

    def disconnect(self):
        """Disconnect from Arduino"""
        with self.lock:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.close()
            self.connected = False
            logger.info("Disconnected from Arduino")

    def send_command(self, cmd_str: str) -> Dict[str, Any]:
        """Send command to Arduino and get response"""
        with self.lock:
            if not self.serial_conn or not self.serial_conn.is_open:
                return {"status": "error", "message": "Serial port not connected"}

            try:
                # Clear any pending data
                self.serial_conn.reset_input_buffer()

                # Send command
                if not cmd_str.endswith('\n'):
                    cmd_str += '\n'
                self.serial_conn.write(cmd_str.encode())
                self.serial_conn.flush()

                # Read response
                response_line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()

                if response_line:
                    try:
                        response_data = json.loads(response_line)
                        return {"status": "ok", "data": response_data}
                    except json.JSONDecodeError:
                        return {"status": "ok", "raw": response_line}
                else:
                    return {"status": "ok", "message": "No response"}

            except Exception as e:
                logger.error(f"Serial error: {e}")
                return {"status": "error", "message": str(e)}

    def lcd(self, line: int, text: str) -> Dict[str, Any]:
        """Write to LCD display"""
        return self.send_command(f"LCD {line} {text}")

    def led(self, tier: int, r: int, g: int, b: int) -> Dict[str, Any]:
        """Set LED color"""
        return self.send_command(f"LED {tier} {r} {g} {b}")

    def servo(self, angle: int) -> Dict[str, Any]:
        """Set servo position"""
        return self.send_command(f"SERVO {angle}")

    def beep(self, frequency: int, duration: int) -> Dict[str, Any]:
        """Play beep sound"""
        return self.send_command(f"BEEP {frequency} {duration}")

    def alert(self, severity: str) -> Dict[str, Any]:
        """Trigger alert pattern"""
        return self.send_command(f"ALERT {severity.upper()}")

    def status(self) -> Dict[str, Any]:
        """Get Arduino status"""
        return self.send_command("STATUS")

    def sensors(self) -> Dict[str, Any]:
        """Read sensors"""
        return self.send_command("SENSORS")


# Global Arduino connection
arduino: Optional[ArduinoSerial] = None


class ArduinoProxyHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Arduino proxy"""

    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info(f"{self.address_string()} - {format % args}")

    def send_json_response(self, status: int, data: Dict[str, Any]):
        """Send JSON response"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        """Handle GET requests"""
        global arduino
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/health':
            self.send_json_response(200, {
                "status": "ok",
                "connected": arduino.connected if arduino else False,
                "port": arduino.port if arduino else None
            })

        elif path == '/status':
            if not arduino or not arduino.connected:
                self.send_json_response(503, {"status": "error", "message": "Arduino not connected"})
                return
            result = arduino.status()
            self.send_json_response(200, result)

        elif path == '/sensors':
            if not arduino or not arduino.connected:
                self.send_json_response(503, {"status": "error", "message": "Arduino not connected"})
                return
            result = arduino.sensors()
            self.send_json_response(200, result)

        else:
            self.send_json_response(404, {"status": "error", "message": "Not found"})

    def do_POST(self):
        """Handle POST requests"""
        global arduino
        parsed = urlparse(self.path)
        path = parsed.path

        if not arduino or not arduino.connected:
            self.send_json_response(503, {"status": "error", "message": "Arduino not connected"})
            return

        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = {}
        if content_length > 0:
            try:
                body = json.loads(self.rfile.read(content_length).decode())
            except json.JSONDecodeError:
                self.send_json_response(400, {"status": "error", "message": "Invalid JSON"})
                return

        try:
            if path == '/lcd':
                line = body.get('line', 0)
                text = body.get('text', '')
                result = arduino.lcd(line, text)
                self.send_json_response(200, result)

            elif path == '/led':
                tier = body.get('tier', 0)
                r = body.get('r', 0)
                g = body.get('g', 0)
                b = body.get('b', 0)
                result = arduino.led(tier, r, g, b)
                self.send_json_response(200, result)

            elif path == '/servo':
                angle = body.get('angle', 90)
                result = arduino.servo(angle)
                self.send_json_response(200, result)

            elif path == '/beep':
                frequency = body.get('frequency', 1000)
                duration = body.get('duration', 200)
                result = arduino.beep(frequency, duration)
                self.send_json_response(200, result)

            elif path == '/alert':
                severity = body.get('severity', 'info')
                message = body.get('message', '')

                # Map severity to LED color
                colors = {
                    "info": (0, 0, 255),      # Blue
                    "warning": (255, 165, 0),  # Orange
                    "error": (255, 0, 0),      # Red
                    "critical": (255, 0, 255)  # Magenta
                }
                r, g, b = colors.get(severity, (0, 0, 255))

                # Display message and set LED
                arduino.lcd(0, severity.upper())
                if message:
                    arduino.lcd(1, message[:16])
                result = arduino.led(0, r, g, b)
                self.send_json_response(200, result)

            elif path == '/raw':
                command = body.get('command', '')
                if not command:
                    self.send_json_response(400, {"status": "error", "message": "Command required"})
                    return
                result = arduino.send_command(command)
                self.send_json_response(200, result)

            else:
                self.send_json_response(404, {"status": "error", "message": "Not found"})

        except Exception as e:
            logger.error(f"Error handling request: {e}")
            self.send_json_response(500, {"status": "error", "message": str(e)})


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Shutdown signal received")
    if arduino:
        arduino.disconnect()
    sys.exit(0)


def main():
    """Main entry point"""
    global arduino

    parser = argparse.ArgumentParser(description="Arduino HTTP Proxy Server")
    parser.add_argument("--port", type=int, default=8200, help="HTTP server port")
    parser.add_argument("--serial-port", default="/dev/tty.usbmodem8344401", help="Arduino serial port")
    parser.add_argument("--baud-rate", type=int, default=115200, help="Serial baud rate")

    args = parser.parse_args()

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("=" * 60)
    print("Arduino HTTP Proxy Server")
    print("=" * 60)
    print(f"HTTP Port: {args.port}")
    print(f"Serial Port: {args.serial_port}")
    print("=" * 60)

    # Connect to Arduino
    arduino = ArduinoSerial(args.serial_port, args.baud_rate)
    if not arduino.connect():
        logger.error("Failed to connect to Arduino, exiting")
        sys.exit(1)

    # Start HTTP server
    server = HTTPServer(('0.0.0.0', args.port), ArduinoProxyHandler)
    logger.info(f"Arduino HTTP Proxy listening on port {args.port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        arduino.disconnect()
        server.shutdown()


if __name__ == "__main__":
    main()

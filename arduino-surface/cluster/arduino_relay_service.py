#!/usr/bin/env python3
"""
Arduino Relay Service
Runs on the node with physical Arduino connection
Exposes Arduino functionality via HTTP for cluster-wide access
"""

import json
import sys
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

# Add bridge to path
sys.path.insert(0, str(Path(__file__).parent.parent / "bridge"))
from surface_bridge import ArduinoSurface


class ArduinoRelayHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Arduino relay"""

    arduino: ArduinoSurface = None

    def do_GET(self):
        """Handle GET requests"""
        parsed = urlparse(self.path)

        # Health check
        if parsed.path == "/health":
            self.send_json({"status": "ok", "arduino_connected": self.arduino is not None})
            return

        # Status endpoint
        if parsed.path == "/status":
            if self.arduino:
                status = self.arduino.get_status()
                self.send_json({"success": True, "status": status})
            else:
                self.send_json({"success": False, "error": "Arduino not connected"}, 503)
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        """Handle POST requests for Arduino commands"""
        parsed = urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rq.read(content_length).decode('utf-8') if content_length > 0 else "{}"

        try:
            params = json.loads(body)
        except json.JSONDecodeError:
            self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            return

        if not self.arduino:
            self.send_json({"success": False, "error": "Arduino not connected"}, 503)
            return

        # Route commands
        try:
            if parsed.path == "/lcd":
                self.arduino.lcd_write(
                    params.get("row", 0),
                    params.get("col", 0),
                    params.get("text", "")
                )
                self.send_json({"success": True})

            elif parsed.path == "/lcd/clear":
                self.arduino.clear_display()
                self.send_json({"success": True})

            elif parsed.path == "/led":
                self.arduino.set_led(
                    params.get("tier", 0),
                    params.get("r", 0),
                    params.get("g", 0),
                    params.get("b", 0)
                )
                self.send_json({"success": True})

            elif parsed.path == "/servo":
                self.arduino.set_servo(params.get("position", 90))
                self.send_json({"success": True})

            elif parsed.path == "/beep":
                self.arduino.beep(
                    params.get("duration_ms", 100),
                    params.get("freq_hz", 1000)
                )
                self.send_json({"success": True})

            elif parsed.path == "/alert":
                self.arduino.alert(params.get("type", "info"))
                self.send_json({"success": True})

            elif parsed.path == "/wait_button":
                event = self.arduino.wait_event(params.get("timeout", 30))
                self.send_json({"success": True, "event": event})

            else:
                self.send_error(404, "Unknown command")

        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 500)

    def send_json(self, data: dict, status=200):
        """Send JSON response"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


def run_relay_service(port: str, relay_port: int = 8200):
    """
    Start Arduino relay service

    Args:
        port: Serial port for Arduino (/dev/tty.usbmodem*)
        relay_port: HTTP port for relay service (default: 8200)
    """
    print(f"🔌 Connecting to Arduino on {port}...")

    arduino = ArduinoSurface(port)
    if not arduino.connect():
        print(f"❌ Failed to connect to Arduino on {port}")
        sys.exit(1)

    print(f"✅ Arduino connected")

    # Set Arduino instance on handler class
    ArduinoRelayHandler.arduino = arduino

    # Start HTTP server
    server = HTTPServer(('0.0.0.0', relay_port), ArduinoRelayHandler)
    print(f"🌐 Arduino relay service running on port {relay_port}")
    print(f"   Other cluster nodes can access Arduino via this service")
    print(f"   Health check: http://localhost:{relay_port}/health")
    print(f"\nPress Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down relay service")
        arduino.close()
        server.shutdown()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Arduino Relay Service for cluster-wide access")
    parser.add_argument("port", help="Serial port (e.g., /dev/tty.usbmodem14101)")
    parser.add_argument("--relay-port", type=int, default=8200, help="HTTP relay port (default: 8200)")

    args = parser.parse_args()
    run_relay_service(args.port, args.relay_port)

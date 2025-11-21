#!/usr/bin/env python3
"""
Send System Status to Arduino via Broker
Reads the status file and sends it to the Arduino broker for display
"""

import socket
import json
import sys

SOCKET_PATH = "/tmp/arduino_broker.sock"
STATUS_FILE = "/tmp/arduino-system-status.json"

def send_to_arduino(message, color="WHITE"):
    """Send message to Arduino via broker"""
    try:
        # Connect to broker
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(SOCKET_PATH)

        # Send command
        command = {
            "action": "display",
            "message": message,
            "color": color
        }

        sock.sendall(json.dumps(command).encode('utf-8'))

        # Wait for response
        response = sock.recv(4096)
        result = json.loads(response.decode('utf-8'))

        sock.close()
        return result

    except Exception as e:
        print(f"Error: {e}")
        return {"status": "error", "message": str(e)}

def main():
    # Read status file
    try:
        with open(STATUS_FILE, 'r') as f:
            status = json.load(f)

        message = status['message']
        color = status['color']

        # Send to Arduino
        result = send_to_arduino(message, color)
        print(f"Sent to Arduino: {result}")

    except FileNotFoundError:
        print(f"Status file not found: {STATUS_FILE}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

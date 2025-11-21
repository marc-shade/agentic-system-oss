#!/usr/bin/env python3
"""
Arduino Broker Client Library
Simple interface for processes to communicate with Arduino through the broker.

Usage:
    from arduino_client import ArduinoClient

    client = ArduinoClient()

    # Send LCD message
    client.lcd(line=0, text="Hello World")

    # Control LED
    client.led(tier=0, r=255, g=100, b=0)

    # Send raw command
    client.raw("STATUS")
"""

import socket
import json
from typing import Dict, Any, Optional

SOCKET_PATH = "/tmp/arduino_broker.sock"

class ArduinoClient:
    """Client for communicating with Arduino through the broker"""

    def __init__(self, socket_path: str = SOCKET_PATH):
        self.socket_path = socket_path
        self.sock: Optional[socket.socket] = None

    def connect(self) -> bool:
        """Connect to the broker"""
        try:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.connect(self.socket_path)
            self.sock.settimeout(5.0)
            return True
        except Exception as e:
            print(f"Failed to connect to broker: {e}")
            return False

    def disconnect(self):
        """Disconnect from the broker"""
        if self.sock:
            self.sock.close()
            self.sock = None

    def send_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Send a command to Arduino through the broker"""
        if not self.sock:
            if not self.connect():
                return {"status": "error", "message": "Not connected to broker"}

        try:
            # Send command
            self.sock.sendall(json.dumps(command).encode('utf-8'))

            # Receive response
            response_data = self.sock.recv(4096)
            if response_data:
                return json.loads(response_data.decode('utf-8'))
            else:
                return {"status": "error", "message": "No response from broker"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def lcd(self, line: int, text: str) -> Dict[str, Any]:
        """Display text on LCD"""
        return self.send_command({
            "type": "lcd",
            "line": line,
            "text": text
        })

    def led(self, tier: int = 0, r: int = 0, g: int = 0, b: int = 0) -> Dict[str, Any]:
        """Set LED color"""
        return self.send_command({
            "type": "led",
            "tier": tier,
            "r": r,
            "g": g,
            "b": b
        })

    def raw(self, command: str) -> Dict[str, Any]:
        """Send raw command to Arduino"""
        return self.send_command({
            "type": "raw",
            "command": command
        })

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


# Convenience functions for one-off commands
def lcd(line: int, text: str) -> Dict[str, Any]:
    """Quick LCD update"""
    with ArduinoClient() as client:
        return client.lcd(line, text)

def led(tier: int = 0, r: int = 0, g: int = 0, b: int = 0) -> Dict[str, Any]:
    """Quick LED update"""
    with ArduinoClient() as client:
        return client.led(tier, r, g, b)

def raw(command: str) -> Dict[str, Any]:
    """Quick raw command"""
    with ArduinoClient() as client:
        return client.raw(command)


if __name__ == "__main__":
    # Test the client
    print("Testing Arduino Broker Client...")

    with ArduinoClient() as client:
        # Test LCD
        result = client.lcd(0, "Broker Test")
        print(f"LCD: {result}")

        # Test LED
        result = client.led(0, 255, 165, 0)  # Orange
        print(f"LED: {result}")

        # Test raw
        result = client.raw("STATUS")
        print(f"STATUS: {result}")

    print("Test complete!")

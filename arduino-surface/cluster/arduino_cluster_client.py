#!/usr/bin/env python3
"""
Arduino Cluster Client
======================

Cluster-aware Arduino client that transparently routes commands
to wherever the Arduino is physically connected.

If Arduino is local:
    → Uses local Unix socket broker

If Arduino is remote:
    → Uses HTTP proxy on the remote node

Usage:
    from arduino_cluster_client import ClusterArduinoClient

    # Automatically finds Arduino across cluster
    client = ClusterArduinoClient()

    # Use the same interface regardless of location
    client.lcd(0, "Hello World")
    client.led(0, 0, 255, 0)  # Green LED
"""

import json
import os
import socket
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Import discovery service
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from arduino_cluster_discovery import (
        get_discovery_service,
        ArduinoLocation,
        CLUSTER_NODES
    )
except ImportError:
    # Fallback if imported from different location
    pass


STORAGE_BASE = os.environ.get('STORAGE_BASE', '/Volumes/SSDRAID0/agentic-system' if os.path.exists('/Volumes/SSDRAID0') else '/home/marc/agentic-system')


class LocalArduinoClient:
    """Client for local Arduino via Unix socket broker"""

    SOCKET_PATH = "/tmp/arduino_broker.sock"

    def __init__(self, socket_path: str = None):
        self.socket_path = socket_path or self.SOCKET_PATH
        self.sock: Optional[socket.socket] = None

    def connect(self) -> bool:
        """Connect to local broker"""
        try:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.connect(self.socket_path)
            self.sock.settimeout(5.0)
            return True
        except Exception as e:
            print(f"Failed to connect to local broker: {e}")
            return False

    def disconnect(self):
        """Disconnect from broker"""
        if self.sock:
            self.sock.close()
            self.sock = None

    def send_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Send command to local Arduino"""
        if not self.sock:
            if not self.connect():
                return {"status": "error", "message": "Not connected to local broker"}

        try:
            self.sock.sendall(json.dumps(command).encode('utf-8'))
            response_data = self.sock.recv(4096)
            if response_data:
                return json.loads(response_data.decode('utf-8'))
            return {"status": "error", "message": "No response"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


class RemoteArduinoClient:
    """Client for remote Arduino via HTTP proxy"""

    def __init__(self, host: str, port: int = 8200):
        self.base_url = f"http://{host}:{port}"
        self.timeout = 5.0

    def _http_request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make HTTP request to remote Arduino proxy"""
        url = f"{self.base_url}{endpoint}"

        try:
            if method == "GET":
                req = urllib.request.Request(url)
            else:  # POST
                req = urllib.request.Request(
                    url,
                    data=json.dumps(data).encode() if data else None,
                    headers={'Content-Type': 'application/json'}
                )
                req.get_method = lambda: 'POST'

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode())

        except urllib.error.HTTPError as e:
            return {"status": "error", "message": f"HTTP {e.code}: {e.reason}"}
        except urllib.error.URLError as e:
            return {"status": "error", "message": f"URL error: {e.reason}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def send_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Send command via HTTP proxy"""
        cmd_type = command.get('type')

        if cmd_type == 'lcd':
            return self._http_request('POST', '/lcd', {
                'line': command.get('line', 0),
                'text': command.get('text', '')
            })
        elif cmd_type == 'led':
            return self._http_request('POST', '/led', {
                'tier': command.get('tier', 0),
                'r': command.get('r', 0),
                'g': command.get('g', 0),
                'b': command.get('b', 0)
            })
        elif cmd_type == 'servo':
            return self._http_request('POST', '/servo', {
                'angle': command.get('angle', 90)
            })
        elif cmd_type == 'beep':
            return self._http_request('POST', '/beep', {
                'frequency': command.get('frequency', 1000),
                'duration': command.get('duration', 200)
            })
        elif cmd_type == 'alert':
            return self._http_request('POST', '/alert', {
                'severity': command.get('severity', 'info'),
                'message': command.get('message', '')
            })
        elif cmd_type == 'raw':
            return self._http_request('POST', '/raw', {
                'command': command.get('command', '')
            })
        elif cmd_type == 'status':
            return self._http_request('GET', '/status')
        elif cmd_type == 'sensors':
            return self._http_request('GET', '/sensors')
        else:
            return {"status": "error", "message": f"Unknown command type: {cmd_type}"}


class ClusterArduinoClient:
    """
    Cluster-aware Arduino client.

    Automatically discovers Arduino location and routes commands
    appropriately whether Arduino is local or remote.
    """

    def __init__(self, auto_discover: bool = True, start_remote_proxy: bool = True):
        """
        Initialize cluster Arduino client.

        Args:
            auto_discover: Automatically discover Arduino location
            start_remote_proxy: Start HTTP proxy on remote node if needed
        """
        self.location: Optional[ArduinoLocation] = None
        self.local_client: Optional[LocalArduinoClient] = None
        self.remote_client: Optional[RemoteArduinoClient] = None
        self.discovery_service = None
        self.connected = False

        if auto_discover:
            self.discover_and_connect(start_remote_proxy)

    def discover_and_connect(self, start_remote_proxy: bool = True) -> bool:
        """Discover Arduino and establish connection"""
        try:
            self.discovery_service = get_discovery_service()
            self.location = self.discovery_service.get_arduino_location()

            if not self.location:
                print("Arduino not found on any cluster node")
                return False

            if self.location.is_local:
                # Connect via local broker
                self.local_client = LocalArduinoClient()
                if self.local_client.connect():
                    self.connected = True
                    print(f"Connected to Arduino locally at {self.location.port}")
                    return True
                else:
                    print("Failed to connect to local broker")
                    return False
            else:
                # Connect via HTTP proxy on remote node
                node = CLUSTER_NODES.get(self.location.node_id)
                if not node:
                    print(f"Unknown node: {self.location.node_id}")
                    return False

                # Optionally start the remote proxy
                if start_remote_proxy and not self.location.broker_running:
                    self.discovery_service.start_remote_broker(self.location)

                self.remote_client = RemoteArduinoClient(node.ip, self.location.broker_port)

                # Test connection
                result = self.remote_client._http_request('GET', '/health')
                if result.get('status') == 'ok':
                    self.connected = True
                    print(f"Connected to Arduino remotely on {self.location.node_id} ({node.ip}:{self.location.broker_port})")
                    return True
                else:
                    print(f"Remote proxy not available: {result}")
                    return False

        except Exception as e:
            print(f"Error discovering/connecting: {e}")
            return False

    def send_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Send command to Arduino (local or remote)"""
        if not self.connected:
            return {"status": "error", "message": "Not connected to Arduino"}

        if self.local_client:
            return self.local_client.send_command(command)
        elif self.remote_client:
            return self.remote_client.send_command(command)
        else:
            return {"status": "error", "message": "No client available"}

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

    def servo(self, angle: int) -> Dict[str, Any]:
        """Set servo position"""
        return self.send_command({
            "type": "servo",
            "angle": angle
        })

    def beep(self, frequency: int = 1000, duration: int = 200) -> Dict[str, Any]:
        """Play beep sound"""
        return self.send_command({
            "type": "beep",
            "frequency": frequency,
            "duration": duration
        })

    def alert(self, severity: str = "info", message: str = "") -> Dict[str, Any]:
        """Trigger alert pattern"""
        return self.send_command({
            "type": "alert",
            "severity": severity,
            "message": message
        })

    def status(self) -> Dict[str, Any]:
        """Get Arduino status"""
        return self.send_command({"type": "status"})

    def sensors(self) -> Dict[str, Any]:
        """Read sensors"""
        return self.send_command({"type": "sensors"})

    def raw(self, command: str) -> Dict[str, Any]:
        """Send raw command"""
        return self.send_command({
            "type": "raw",
            "command": command
        })

    def disconnect(self):
        """Disconnect from Arduino"""
        if self.local_client:
            self.local_client.disconnect()
        self.connected = False

    def get_location_info(self) -> Dict[str, Any]:
        """Get information about Arduino location"""
        if not self.location:
            return {"connected": False, "location": None}

        return {
            "connected": self.connected,
            "location": {
                "node_id": self.location.node_id,
                "port": self.location.port,
                "is_local": self.location.is_local,
                "broker_running": self.location.broker_running
            }
        }

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


# Convenience functions
def get_client() -> ClusterArduinoClient:
    """Get a connected cluster Arduino client"""
    return ClusterArduinoClient()


def lcd(line: int, text: str) -> Dict[str, Any]:
    """Quick LCD update"""
    with ClusterArduinoClient() as client:
        return client.lcd(line, text)


def led(tier: int = 0, r: int = 0, g: int = 0, b: int = 0) -> Dict[str, Any]:
    """Quick LED update"""
    with ClusterArduinoClient() as client:
        return client.led(tier, r, g, b)


def alert(severity: str = "info", message: str = "") -> Dict[str, Any]:
    """Quick alert"""
    with ClusterArduinoClient() as client:
        return client.alert(severity, message)


if __name__ == "__main__":
    print("=" * 60)
    print("Arduino Cluster Client Test")
    print("=" * 60)

    client = ClusterArduinoClient()

    if client.connected:
        info = client.get_location_info()
        print(f"\nConnection Info: {json.dumps(info, indent=2)}")

        print("\nTesting LCD...")
        result = client.lcd(0, "Cluster Test")
        print(f"LCD: {result}")

        print("\nTesting LED (green)...")
        result = client.led(0, 0, 255, 0)
        print(f"LED: {result}")

        print("\nGetting status...")
        result = client.status()
        print(f"Status: {result}")

        client.disconnect()
    else:
        print("\nFailed to connect to Arduino on any cluster node")

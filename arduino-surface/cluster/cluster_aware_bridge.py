#!/usr/bin/env python3
"""
Cluster-Aware Arduino Bridge
Automatically discovers Arduino location and provides unified interface
Works with both local Arduino and remote relay
"""

import json
import sys
from pathlib import Path
from typing import Optional, Dict
import urllib.request
import urllib.error

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "bridge"))
sys.path.insert(0, str(Path(__file__).parent))

from surface_bridge import ArduinoSurface
from arduino_discovery import ArduinoClusterDiscovery, ArduinoLocation


class ClusterAwareArduinoSurface:
    """
    Unified Arduino interface that works across cluster

    Automatically:
    - Discovers Arduino location (local or remote node)
    - Connects via serial (local) or HTTP relay (remote)
    - Provides same interface regardless of location
    """

    def __init__(self, auto_discover: bool = True):
        """
        Initialize cluster-aware Arduino bridge

        Args:
            auto_discover: Automatically discover Arduino (default: True)
        """
        self.location: Optional[ArduinoLocation] = None
        self.arduino: Optional[ArduinoSurface] = None
        self.is_local: bool = False
        self.relay_url: Optional[str] = None

        if auto_discover:
            self.discover_and_connect()

    def discover_and_connect(self) -> bool:
        """
        Discover Arduino and establish connection

        Returns:
            True if Arduino found and connected, False otherwise
        """
        discovery = ArduinoClusterDiscovery()
        self.location = discovery.discover()

        if not self.location:
            print("⚠️  Arduino not found on any cluster node", file=sys.stderr)
            print("   Operating in degraded mode (commands will be no-ops)", file=sys.stderr)
            return False

        # Determine if local or remote
        if self.location.host == "localhost":
            # Local Arduino - use direct serial connection
            self.is_local = True
            self.arduino = ArduinoSurface(self.location.serial_port)
            success = self.arduino.connect()

            if success:
                print(f"✅ Connected to local Arduino on {self.location.serial_port}", file=sys.stderr)
            else:
                print(f"❌ Failed to connect to local Arduino", file=sys.stderr)

            return success

        else:
            # Remote Arduino - use HTTP relay
            self.is_local = False
            self.relay_url = f"http://{self.location.host}:{self.location.relay_port}"

            # Test connection
            try:
                self._relay_request("GET", "/health")
                print(f"✅ Connected to Arduino via relay on {self.location.node_id}", file=sys.stderr)
                return True
            except Exception as e:
                print(f"❌ Failed to connect to relay: {e}", file=sys.stderr)
                return False

    def _relay_request(self, method: str, path: str, data: Optional[Dict] = None) -> Dict:
        """Make HTTP request to relay service"""
        url = self.relay_url + path

        if method == "GET":
            with urllib.request.urlopen(url, timeout=5) as response:
                return json.loads(response.read().decode())

        elif method == "POST":
            req = urllib.request.Request(
                url,
                data=json.dumps(data or {}).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                return json.loads(response.read().decode())

    def lcd_write(self, row: int, col: int, text: str):
        """Write text to LCD display"""
        if not self.location:
            return  # No-op in degraded mode

        if self.is_local:
            self.arduino.lcd_write(row, col, text)
        else:
            self._relay_request("POST", "/lcd", {"row": row, "col": col, "text": text})

    def clear_display(self):
        """Clear LCD display"""
        if not self.location:
            return

        if self.is_local:
            self.arduino.clear_display()
        else:
            self._relay_request("POST", "/lcd/clear")

    def set_led(self, tier: int, r: int, g: int, b: int):
        """Set LED color"""
        if not self.location:
            return

        if self.is_local:
            self.arduino.set_led(tier, r, g, b)
        else:
            self._relay_request("POST", "/led", {"tier": tier, "r": r, "g": g, "b": b})

    def set_servo(self, position: int):
        """Set servo position (0-180°)"""
        if not self.location:
            return

        if self.is_local:
            self.arduino.set_servo(position)
        else:
            self._relay_request("POST", "/servo", {"position": position})

    def beep(self, duration_ms: int, freq_hz: int):
        """Play beep sound"""
        if not self.location:
            return

        if self.is_local:
            self.arduino.beep(duration_ms, freq_hz)
        else:
            self._relay_request("POST", "/beep", {"duration_ms": duration_ms, "freq_hz": freq_hz})

    def alert(self, alert_type: str):
        """Play alert pattern"""
        if not self.location:
            return

        if self.is_local:
            self.arduino.alert(alert_type)
        else:
            self._relay_request("POST", "/alert", {"type": alert_type})

    def get_status(self) -> Optional[Dict]:
        """Get full Arduino status including sensors"""
        if not self.location:
            return None

        if self.is_local:
            return self.arduino.get_status()
        else:
            result = self._relay_request("GET", "/status")
            return result.get("status")

    def wait_event(self, timeout: float = 30.0) -> Optional[Dict]:
        """Wait for button press or sensor event"""
        if not self.location:
            return None

        if self.is_local:
            return self.arduino.wait_event(timeout)
        else:
            result = self._relay_request("POST", "/wait_button", {"timeout": timeout})
            return result.get("event")

    def close(self):
        """Close connection"""
        if self.is_local and self.arduino:
            self.arduino.close()


if __name__ == "__main__":
    # Test cluster-aware bridge
    surface = ClusterAwareArduinoSurface()

    if surface.location:
        print(f"\n📍 Arduino Location:")
        print(f"   Node: {surface.location.node_id}")
        print(f"   Port: {surface.location.serial_port}")
        print(f"   Mode: {'Local' if surface.is_local else 'Remote relay'}")

        # Test commands
        surface.lcd_write(0, 0, "Cluster Test")
        surface.lcd_write(1, 0, "Success!")
        surface.set_led(0, 0, 255, 0)  # Green

        import time
        time.sleep(2)

        surface.close()
    else:
        print("\n❌ Arduino not available on cluster")

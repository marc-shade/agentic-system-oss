#!/usr/bin/env python3
"""
Arduino Cluster Relay
Relay Arduino commands through remote cluster nodes
"""

import json
import subprocess
import socket
from typing import Optional, Dict
from pathlib import Path
from arduino_cluster_discovery import ArduinoLocation


class ArduinoClusterRelay:
    """Relay Arduino commands through remote nodes"""

    def __init__(self, location: ArduinoLocation):
        """
        Initialize relay

        Args:
            location: Arduino location information
        """
        self.location = location
        self.bridge_path = Path(__file__).parent / "surface_bridge.py"

    def send_command(self, command: str) -> Optional[Dict]:
        """
        Send command to Arduino (local or remote)

        Args:
            command: Arduino command string

        Returns:
            Parsed JSON response or None
        """
        if self.location.is_local:
            return self._send_local(command)
        elif self.location.relay_method == "ssh":
            return self._send_via_ssh(command)
        elif self.location.relay_method == "telnet":
            return self._send_via_telnet(command)
        else:
            raise ValueError(f"Unknown relay method: {self.location.relay_method}")

    def _send_local(self, command: str) -> Optional[Dict]:
        """
        Send command to local Arduino

        Args:
            command: Arduino command string

        Returns:
            Parsed JSON response or None
        """
        # Import locally to avoid circular dependency
        from surface_bridge import ArduinoSurface

        try:
            surface = ArduinoSurface(self.location.port)
            if not surface.connect():
                return None

            response = surface._send_command(command)
            surface.disconnect()
            return response

        except Exception as e:
            print(f"Local command error: {e}")
            return None

    def _send_via_ssh(self, command: str) -> Optional[Dict]:
        """
        Send command via SSH using raw serial communication

        Args:
            command: Arduino command string

        Returns:
            Parsed JSON response or None
        """
        # Use base64 to avoid quoting issues
        import base64

        python_script = f"""import serial
import json
import time

try:
    ser = serial.Serial('{self.location.port}', 115200, timeout=2)
    time.sleep(3)  # Wait for Arduino reset

    # Read and discard startup messages
    time.sleep(0.5)
    while ser.in_waiting:
        line = ser.readline().decode('utf-8', errors='ignore').strip()

    # Send command
    ser.write(b'{command}\\n')
    ser.flush()

    # Wait for response
    start = time.time()
    response_found = False
    while time.time() - start < 2.0:
        if ser.in_waiting:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                try:
                    response = json.loads(line)
                    print(json.dumps(response))
                    response_found = True
                    break
                except:
                    pass
        time.sleep(0.01)

    ser.close()

    if not response_found:
        print(json.dumps({{"status": "error", "message": "timeout"}}))
except Exception as e:
    print(json.dumps({{"status": "error", "message": str(e)}}))
"""

        # Base64 encode the script
        encoded_script = base64.b64encode(python_script.encode()).decode()

        try:
            # Execute via SSH with base64 decoding
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
                 f"marc@{self.location.node_ip}",
                 f"echo {encoded_script} | base64 -d | python3"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                try:
                    return json.loads(result.stdout.strip())
                except json.JSONDecodeError:
                    print(f"Failed to parse response: {result.stdout}")
                    return None

            if result.stderr:
                print(f"SSH stderr: {result.stderr}")

            return None

        except Exception as e:
            print(f"SSH relay error: {e}")
            return None

    def _send_via_telnet(self, command: str) -> Optional[Dict]:
        """
        Send command via telnet command listener

        Args:
            command: Arduino command string

        Returns:
            Parsed JSON response or None
        """
        # Build remote Python command
        python_cmd = f"""
import sys
import json
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/arduino-surface/bridge')

from surface_bridge import ArduinoSurface

surface = ArduinoSurface('{self.location.port}')
if not surface.connect():
    print(json.dumps({{"status": "error", "message": "connection_failed"}}))
    sys.exit(1)

response = surface._send_command('{command}')
surface.disconnect()

if response:
    print(json.dumps(response))
else:
    print(json.dumps({{"status": "error", "message": "no_response"}}))
"""

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((self.location.node_ip, 9999))

            # Read welcome message
            sock.recv(1024)

            # Send Python command
            exec_cmd = f"exec python3 -c {repr(python_cmd)}\n"
            sock.send(exec_cmd.encode())

            # Read response
            response_data = b""
            while True:
                try:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response_data += chunk
                    # Check if we have a complete JSON response
                    try:
                        json.loads(response_data.decode('utf-8'))
                        break
                    except:
                        continue
                except socket.timeout:
                    break

            sock.send(b"quit\n")
            sock.close()

            # Parse JSON from response
            response_text = response_data.decode('utf-8')
            for line in response_text.split('\n'):
                if line.strip() and line.strip().startswith('{'):
                    return json.loads(line.strip())

            return None

        except Exception as e:
            print(f"Telnet relay error: {e}")
            return None


class ClusterAwareArduinoSurface:
    """
    Cluster-aware Arduino Surface wrapper
    Transparently handles local and remote Arduino control
    """

    def __init__(self, location: ArduinoLocation):
        """
        Initialize cluster-aware surface

        Args:
            location: Arduino location information
        """
        self.location = location
        self.relay = ArduinoClusterRelay(location)

    def connect(self) -> bool:
        """Test connection to Arduino"""
        response = self.relay.send_command("PING")
        return response is not None and response.get("status") == "ok"

    def disconnect(self):
        """Disconnect (no-op for remote, cleanup for local)"""
        pass

    # ==================== LCD METHODS ====================

    def lcd_write(self, row: int, col: int, text: str) -> bool:
        """Write text to LCD display"""
        max_length = 16 - col
        text = text[:max_length]

        command = f"LCD {row} {col} {text}"
        response = self.relay.send_command(command)
        return response is not None and response.get("status") == "ok"

    def lcd_clear(self) -> bool:
        """Clear LCD display"""
        response = self.relay.send_command("CLEAR")
        return response is not None and response.get("status") == "ok"

    # ==================== LED METHODS ====================

    def set_led(self, tier: int, r: int, g: int, b: int) -> bool:
        """Set RGB LED color"""
        command = f"LED {tier} {r} {g} {b}"
        response = self.relay.send_command(command)
        return response is not None and response.get("status") == "ok"

    # ==================== SERVO METHODS ====================

    def set_servo(self, position: int) -> bool:
        """Set servo position"""
        command = f"SERVO {position}"
        response = self.relay.send_command(command)
        return response is not None and response.get("status") == "ok"

    # ==================== BUZZER METHODS ====================

    def beep(self, duration_ms: int = 200, frequency_hz: int = 1000) -> bool:
        """Play beep sound"""
        command = f"BEEP {duration_ms} {frequency_hz}"
        response = self.relay.send_command(command)
        return response is not None and response.get("status") == "ok"

    def alert(self, alert_type: str) -> bool:
        """Play alert pattern"""
        command = f"ALERT {alert_type}"
        response = self.relay.send_command(command)
        return response is not None and response.get("status") == "ok"

    # ==================== STATUS METHODS ====================

    def get_status(self) -> Optional[Dict]:
        """Get full status including sensor readings"""
        return self.relay.send_command("STATUS")

    # ==================== EVENT METHODS ====================

    def start_event_listener(self):
        """Start background event listener"""
        # Note: Event listening not supported for remote nodes
        if not self.location.is_local:
            print("Warning: Event listening only supported for local Arduino")

    def stop_event_listener(self):
        """Stop background event listener"""
        pass

    def register_handler(self, event_type: str, handler):
        """Register event handler"""
        if not self.location.is_local:
            print("Warning: Event handlers only supported for local Arduino")

    def wait_event(self, timeout: float = 10.0) -> Optional[Dict]:
        """Wait for single event (blocking)"""
        if not self.location.is_local:
            print("Warning: Event waiting only supported for local Arduino")
            return None

        # For local Arduino, import and use direct bridge
        from surface_bridge import ArduinoSurface

        try:
            surface = ArduinoSurface(self.location.port)
            if not surface.connect():
                return None

            event = surface.wait_event(timeout)
            surface.disconnect()
            return event

        except Exception as e:
            print(f"Event wait error: {e}")
            return None


def main():
    """CLI testing interface"""
    from arduino_cluster_discovery import ArduinoClusterDiscovery

    print("🔍 Discovering Arduino across cluster...\n")

    discovery = ArduinoClusterDiscovery()
    location = discovery.discover()

    if not location:
        print("❌ Arduino not found on any cluster node")
        return

    print(f"✅ Arduino found!")
    print(f"   Node: {location.node_id}")
    print(f"   IP: {location.node_ip}")
    print(f"   Port: {location.port}")
    print(f"   Local: {location.is_local}")
    print(f"   Relay: {location.relay_method}\n")

    # Test connection
    print("🔌 Testing connection...")
    surface = ClusterAwareArduinoSurface(location)

    if surface.connect():
        print("✅ Connected!\n")

        # Test LCD
        print("📺 Testing LCD...")
        if surface.lcd_write(0, 0, "Cluster Test"):
            print("✅ LCD write successful")

        # Test LED
        print("💡 Testing LED...")
        if surface.set_led(0, 0, 255, 0):
            print("✅ LED set successful")

        # Test beep
        print("🔔 Testing beep...")
        if surface.beep(200, 1000):
            print("✅ Beep successful")

        # Test status
        print("📊 Testing status...")
        status = surface.get_status()
        if status:
            print(f"✅ Status: {status}")

        surface.disconnect()
    else:
        print("❌ Connection failed")


if __name__ == "__main__":
    main()

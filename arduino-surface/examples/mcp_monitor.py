#!/usr/bin/env python3
"""
MCP Infrastructure Monitoring Display
Real-time visualization of MCP server health on Arduino Surface

Displays:
- Tier0 LED → enhanced-memory + voice-mode + arduino-surface + safla status
- LCD Line 0 → Active MCP count and status
- LCD Line 1 → Current health check result
- Servo → Overall system activity level (0-180°)

Color codes:
- Green (0,255,0) → All services healthy
- Yellow (255,255,0) → Partial services (1-3 down)
- Orange (255,128,0) → Degraded services (4-5 down)
- Red (255,0,0) → Critical (all down)
"""

import sys
import time
import json
import subprocess
from pathlib import Path

# Add bridge directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "bridge"))

try:
    from surface_bridge import ArduinoSurface
except ImportError as e:
    print(f"Error importing surface_bridge: {e}", file=sys.stderr)
    print(f"Python path: {sys.path}", file=sys.stderr)
    sys.exit(1)


class MCPMonitor:
    """Monitor MCP servers and display status on Arduino Surface"""

    def __init__(self, port: str):
        """
        Initialize MCP monitor

        Args:
            port: Arduino serial port (e.g., /dev/tty.usbmodem8344401)
        """
        self.arduino = ArduinoSurface(port)
        self.mcp_servers = [
            "enhanced-memory",
            "voice-mode",
            "arduino-surface",
            "safla",
            "agent-runtime",
            "sequential-thinking"
        ]
        self.tier_names = {
            0: "Essential",
            1: "Cognitive",
            2: "Reasoning"
        }

    def connect(self) -> bool:
        """Connect to Arduino"""
        return self.arduino.connect()

    def check_mcp_status(self) -> dict:
        """
        Check status of all MCP servers

        Returns:
            dict: {
                'total': int,
                'running': int,
                'servers': {
                    'server_name': bool (running status)
                },
                'health': str ('healthy', 'degraded', 'critical')
            }
        """
        status = {
            'total': len(self.mcp_servers),
            'running': 0,
            'servers': {},
            'health': 'critical'
        }

        for server in self.mcp_servers:
            try:
                # Check if process is running
                result = subprocess.run(
                    ['ps', 'aux'],
                    capture_output=True,
                    text=True
                )
                is_running = server in result.stdout and 'grep' not in result.stdout
                status['servers'][server] = is_running
                if is_running:
                    status['running'] += 1
            except Exception as e:
                print(f"Error checking {server}: {e}", file=sys.stderr)
                status['servers'][server] = False

        # Determine overall health
        if status['running'] == status['total']:
            status['health'] = 'healthy'
        elif status['running'] >= status['total'] * 0.5:
            status['health'] = 'degraded'
        else:
            status['health'] = 'critical'

        return status

    def update_display(self, status: dict):
        """
        Update Arduino display with MCP status

        Args:
            status: MCP status dict from check_mcp_status()
        """
        # Update LCD Line 0: MCP count and health
        line0 = f"MCP: {status['running']}/{status['total']}"
        if status['health'] == 'healthy':
            line0 += " OK"
        elif status['health'] == 'degraded':
            line0 += " WARN"
        else:
            line0 += " CRIT"

        self.arduino.lcd_write(0, 0, line0.ljust(16))

        # Update LCD Line 1: Detailed status
        tier0_count = sum(1 for s in ['enhanced-memory', 'voice-mode', 'arduino-surface', 'safla']
                          if status['servers'].get(s, False))
        line1 = f"T0:{tier0_count}/4 "

        if status['health'] == 'healthy':
            line1 += "All OK"
        elif status['health'] == 'degraded':
            line1 += "Partial"
        else:
            line1 += "DOWN"

        self.arduino.lcd_write(1, 0, line1.ljust(16))

        # Update LED color based on health
        if status['health'] == 'healthy':
            self.arduino.set_led(0, 0, 255, 0)  # Green
        elif status['health'] == 'degraded':
            self.arduino.set_led(0, 255, 255, 0)  # Yellow
        else:
            self.arduino.set_led(0, 255, 0, 0)  # Red

        # Update servo based on running percentage
        running_pct = status['running'] / status['total']
        servo_pos = int(running_pct * 180)
        self.arduino.set_servo(servo_pos)

    def monitor_loop(self, interval: int = 60):
        """
        Continuous monitoring loop

        Args:
            interval: Seconds between checks (default: 60)
        """
        print(f"Starting MCP monitoring (checking every {interval}s)...")
        print("Press Ctrl+C to stop")

        try:
            while True:
                # Check MCP status
                status = self.check_mcp_status()

                # Update display
                self.update_display(status)

                # Print status to console
                print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}]")
                print(f"MCP Status: {status['health'].upper()}")
                print(f"Running: {status['running']}/{status['total']}")
                for server, is_running in status['servers'].items():
                    symbol = "✅" if is_running else "❌"
                    print(f"  {symbol} {server}")

                # Play alert if degraded or critical
                if status['health'] == 'degraded':
                    self.arduino.alert('warning')
                elif status['health'] == 'critical':
                    self.arduino.alert('error')

                # Wait for next check
                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")
            # Clear display
            self.arduino.lcd_clear()
            self.arduino.lcd_write(0, 0, "Monitoring")
            self.arduino.lcd_write(1, 0, "Stopped")
            self.arduino.set_led(0, 0, 0, 255)  # Blue
            time.sleep(2)
            self.arduino.lcd_clear()

    def run_once(self) -> dict:
        """
        Run a single health check and update display

        Returns:
            dict: MCP status
        """
        status = self.check_mcp_status()
        self.update_display(status)
        return status

    def disconnect(self):
        """Disconnect from Arduino"""
        if self.arduino:
            self.arduino.disconnect()


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: mcp_monitor.py <serial_port> [--once|--interval SECONDS]")
        print("\nExamples:")
        print("  # Continuous monitoring (default: 60s interval)")
        print("  python3 mcp_monitor.py /dev/tty.usbmodem8344401")
        print()
        print("  # Single check and exit")
        print("  python3 mcp_monitor.py /dev/tty.usbmodem8344401 --once")
        print()
        print("  # Custom interval")
        print("  python3 mcp_monitor.py /dev/tty.usbmodem8344401 --interval 30")
        sys.exit(1)

    port = sys.argv[1]

    # Parse options
    run_once = '--once' in sys.argv
    interval = 60  # Default
    if '--interval' in sys.argv:
        try:
            idx = sys.argv.index('--interval')
            interval = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            print("Error: --interval requires a number")
            sys.exit(1)

    # Initialize monitor
    monitor = MCPMonitor(port)

    if not monitor.connect():
        print(f"Error: Failed to connect to Arduino on {port}")
        sys.exit(1)

    print(f"Connected to Arduino on {port}")

    try:
        if run_once:
            # Single check
            status = monitor.run_once()
            print("\nMCP Status:")
            print(json.dumps(status, indent=2))
        else:
            # Continuous monitoring
            monitor.monitor_loop(interval=interval)
    finally:
        monitor.disconnect()


if __name__ == "__main__":
    main()

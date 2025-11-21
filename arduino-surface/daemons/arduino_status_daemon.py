#!/usr/bin/env python3
"""
Arduino Status Daemon
Persistent background process that monitors agentic system state and updates Arduino display
"""

import sys
import time
import signal
from pathlib import Path
from datetime import datetime

# Add bridge to path
sys.path.insert(0, str(Path(__file__).parent.parent / "bridge"))

from surface_bridge import ArduinoSurface


class ArduinoStatusDaemon:
    """Daemon that monitors system state and updates Arduino"""

    def __init__(self, port='/dev/tty.usbmodem8344401'):
        self.port = port
        self.surface = None
        self.running = True
        self.last_state = None
        self.last_update = 0
        self.connection_retries = 0
        self.max_retries = 5

        # Register signal handlers
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def connect(self):
        """Connect to Arduino with retry logic"""
        try:
            self.surface = ArduinoSurface(self.port)
            if self.surface.connect():
                print(f"✓ Arduino daemon connected on {self.port}")
                self.connection_retries = 0
                return True
            return False
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False

    def shutdown(self, signum, frame):
        """Graceful shutdown"""
        print("\n✓ Shutting down Arduino daemon...")
        self.running = False

        if self.surface:
            try:
                self.surface.lcd_clear()
                self.surface.lcd_write(0, 0, "Daemon Stopped")
                self.surface.set_led(0, 0, 0, 0)  # Off
                self.surface.disconnect()
            except:
                pass

        sys.exit(0)

    def get_system_state(self):
        """
        Get current system state

        This is a simple implementation. In production, this would:
        - Query enhanced-memory for recent agent activity
        - Check MCP server health
        - Monitor agent-runtime-mcp for active tasks
        - Track file operations, git status, etc.
        """

        # For now, return a basic state
        # TODO: Integrate with enhanced-memory-mcp, agent-runtime-mcp

        hour = datetime.now().hour

        if 9 <= hour < 17:
            time_of_day = "Day"
        elif 17 <= hour < 22:
            time_of_day = "Evening"
        else:
            time_of_day = "Night"

        return {
            'agent': 'Ready',
            'status': f'{time_of_day}',
            'health': 'healthy',
            'time': datetime.now().strftime("%H:%M")
        }

    def get_system_health(self):
        """
        Determine overall system health

        Returns: 'healthy', 'warning', 'error'

        This would check:
        - MCP server availability
        - Memory usage
        - Disk space
        - Recent error rates
        """
        # TODO: Implement health checks
        return 'healthy'

    def update_display(self, state):
        """Update LCD and LED based on state"""
        if not self.surface:
            return

        try:
            # Update LCD
            line1 = f"Agent: {state['agent'][:10]}"
            line2 = f"{state['status'][:11]} {state['time']}"

            self.surface.lcd_write(0, 0, line1)
            self.surface.lcd_write(1, 0, line2)

            # Update LED based on health
            led_colors = {
                'healthy': (0, 255, 0),    # Green
                'warning': (255, 255, 0),  # Yellow
                'error': (255, 0, 0)       # Red
            }

            color = led_colors.get(state['health'], (0, 0, 255))  # Default blue
            self.surface.set_led(0, *color)

        except Exception as e:
            print(f"✗ Display update error: {e}")
            self.connection_retries += 1
            if self.connection_retries > self.max_retries:
                print(f"✗ Max retries exceeded, reconnecting...")
                self.surface = None
                self.connection_retries = 0

    def run(self):
        """Main daemon loop"""
        print("✓ Arduino Status Daemon starting...")

        # Initial connection
        if not self.connect():
            print("✗ Initial connection failed, will retry...")

        # Main loop
        while self.running:
            try:
                # Reconnect if needed
                if not self.surface:
                    if self.connect():
                        self.surface.lcd_clear()
                        self.surface.lcd_write(0, 0, "Daemon Started")
                        time.sleep(2)
                    else:
                        time.sleep(5)
                        continue

                # Get current state
                current_state = self.get_system_state()
                current_time = time.time()

                # Update if state changed or 5 seconds elapsed
                if (current_state != self.last_state or
                    current_time - self.last_update > 5):

                    self.update_display(current_state)
                    self.last_state = current_state
                    self.last_update = current_time

                # Sleep 1 second between checks
                time.sleep(1)

            except Exception as e:
                print(f"✗ Daemon loop error: {e}")
                time.sleep(5)


def main():
    """Entry point"""
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        port = '/dev/tty.usbmodem8344401'

    daemon = ArduinoStatusDaemon(port)

    try:
        daemon.run()
    except Exception as e:
        print(f"✗ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

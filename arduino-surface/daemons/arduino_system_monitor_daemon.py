#!/usr/bin/env python3
"""
Arduino System Monitor Daemon
Displays real Claude Code quality metrics on Arduino
"""

import sys
import time
import signal
import math
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "bridge"))
sys.path.insert(0, str(Path(__file__).parent.parent / "ember_integration"))

from surface_bridge import ArduinoSurface
from system_monitor import SystemMonitor


class SystemMonitorDaemon:
    """Daemon that displays system quality metrics on Arduino"""

    def __init__(self, port):
        self.port = port
        self.surface = ArduinoSurface(port)
        self.monitor = SystemMonitor()
        self.running = False
        self.current_mode = 0  # Start with violation monitor
        self.mode_names = ["Violations", "Quality", "Learning", "System"]

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)

    def shutdown(self, signum, frame):
        """Graceful shutdown"""
        print("\n🔥 System Monitor shutting down...")
        self.running = False
        if self.surface:
            self.surface.lcd_clear()
            self.surface.set_led(0, 0, 0, 0)  # Turn off LED
            self.surface.disconnect()
        sys.exit(0)

    def update_display(self):
        """Update LCD with current mode"""
        try:
            line1, line2 = self.monitor.get_display_for_mode(self.current_mode)

            # Write to LCD
            self.surface.lcd_write(0, 0, line1)
            self.surface.lcd_write(1, 0, line2)

        except Exception as e:
            print(f"Display update error: {e}")

    def update_led(self, t):
        """Update LED based on quality score"""
        try:
            led = self.monitor.get_led_for_quality()
            color = led["color"]
            pattern = led["pattern"]

            # Calculate brightness based on pattern
            brightness = self.get_led_brightness(pattern, t)

            r = int(color[0] * brightness)
            g = int(color[1] * brightness)
            b = int(color[2] * brightness)

            self.surface.set_led(0, r, g, b)

        except Exception as e:
            print(f"LED update error: {e}")

    def get_led_brightness(self, pattern, t):
        """Calculate LED brightness for animation patterns"""
        if pattern == 'solid':
            return 1.0
        elif pattern == 'slow_pulse':
            # 2 second pulse
            return 0.3 + 0.7 * (math.sin(t * math.pi) + 1) / 2
        elif pattern == 'fast_pulse':
            # 0.5 second pulse
            return 0.3 + 0.7 * (math.sin(t * 4 * math.pi) + 1) / 2
        elif pattern == 'flash':
            # 0.25 second flash
            return 1.0 if (t % 0.5) < 0.25 else 0.0
        return 1.0

    def cycle_mode(self):
        """Cycle to next display mode"""
        self.current_mode = (self.current_mode + 1) % 4
        mode_name = self.mode_names[self.current_mode]

        # Show mode change briefly
        self.surface.lcd_clear()
        self.surface.lcd_write(0, 0, f"Mode: {mode_name}")
        self.surface.beep(100, 1000)  # Brief beep
        time.sleep(1)

        # Update display immediately
        self.update_display()

    def run(self):
        """Main daemon loop"""
        print("=" * 50)
        print("🔥 System Monitor Daemon Starting 🔥")
        print("=" * 50)
        print()

        # Connect to Arduino
        if not self.surface.connect():
            print(f"❌ Failed to connect to {self.port}")
            return 1

        print(f"✓ Connected to Arduino on {self.port}")
        print(f"✓ Starting with mode: {self.mode_names[self.current_mode]}")
        print()
        print("Display Modes (cycle with SELECT button):")
        for i, name in enumerate(self.mode_names):
            print(f"  {i}: {name}")
        print()
        print("Press Ctrl+C to stop")
        print()

        self.running = True
        last_display_update = 0
        start_time = time.time()

        try:
            while self.running:
                current_time = time.time()
                elapsed = current_time - start_time

                # Update display every 5 seconds
                if current_time - last_display_update >= 5.0:
                    self.update_display()
                    last_display_update = current_time

                # Update LED every 100ms for smooth animation
                self.update_led(elapsed)

                time.sleep(0.1)

        except KeyboardInterrupt:
            self.shutdown(None, None)

        return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: arduino_system_monitor_daemon.py <port>")
        print("Example: arduino_system_monitor_daemon.py /dev/tty.usbmodem8344401")
        sys.exit(1)

    port = sys.argv[1]
    daemon = SystemMonitorDaemon(port)
    sys.exit(daemon.run())

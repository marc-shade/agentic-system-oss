#!/usr/bin/env python3
"""
Arduino Enhanced Status Daemon
Persistent background process with LED patterns, display modes, and intelligent updates
"""

import sys
import time
import math
import signal
from pathlib import Path
from datetime import datetime

# Add bridge to path
sys.path.insert(0, str(Path(__file__).parent.parent / "bridge"))

from surface_bridge import ArduinoSurface


# LED State Definitions
LED_STATES = {
    'healthy': {
        'color': (0, 255, 0),      # Green
        'pattern': 'solid',
        'priority': 0
    },
    'processing': {
        'color': (0, 0, 255),      # Blue
        'pattern': 'slow_pulse',   # 2s cycle
        'priority': 1
    },
    'intensive': {
        'color': (0, 0, 255),      # Blue
        'pattern': 'fast_pulse',   # 0.5s cycle
        'priority': 2
    },
    'waiting': {
        'color': (128, 0, 128),    # Purple
        'pattern': 'slow_pulse',
        'priority': 3
    },
    'warning': {
        'color': (255, 255, 0),    # Yellow
        'pattern': 'slow_pulse',
        'priority': 4
    },
    'error': {
        'color': (255, 0, 0),      # Red
        'pattern': 'flash',        # 0.25s on/off
        'priority': 5
    }
}


class ArduinoEnhancedDaemon:
    """Enhanced daemon with LED patterns and display modes"""

    def __init__(self, port='/dev/tty.usbmodem8344401'):
        self.port = port
        self.surface = None
        self.running = True

        # Display state
        self.current_mode = 'agent_status'
        self.display_modes = ['agent_status', 'system_health', 'time', 'performance']
        self.last_lcd_update = 0
        self.last_led_update = 0
        self.last_state = None

        # LED state
        self.led_state = 'healthy'
        self.led_pattern_start = time.time()

        # Connection tracking
        self.connection_retries = 0
        self.max_retries = 5

        # Update intervals
        self.MIN_LCD_UPDATE = 2.0    # Don't update LCD more than every 2 seconds
        self.IDLE_UPDATE = 30.0       # Update time every 30 seconds when idle
        self.LED_UPDATE = 0.1         # Update LED pattern every 100ms

        # Register signal handlers
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def connect(self):
        """Connect to Arduino with retry logic"""
        try:
            self.surface = ArduinoSurface(self.port)
            if self.surface.connect():
                print(f"✓ Enhanced daemon connected on {self.port}")
                self.connection_retries = 0
                return True
            return False
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False

    def shutdown(self, signum, frame):
        """Graceful shutdown"""
        print("\n✓ Shutting down enhanced daemon...")
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

    def get_led_brightness(self, pattern, t):
        """Calculate LED brightness based on pattern and time"""
        if pattern == 'solid':
            return 1.0

        elif pattern == 'slow_pulse':
            # 2 second sine wave (30 BPM breathing)
            return 0.3 + 0.7 * (math.sin(t * math.pi) + 1) / 2

        elif pattern == 'fast_pulse':
            # 0.5 second sine wave (120 BPM rapid)
            return 0.3 + 0.7 * (math.sin(t * 4 * math.pi) + 1) / 2

        elif pattern == 'flash':
            # 0.25 second on/off (240 BPM alert)
            return 1.0 if (t % 0.5) < 0.25 else 0.0

        return 1.0

    def update_led_pattern(self):
        """Update LED with current pattern"""
        if not self.surface:
            return

        try:
            t = time.time() - self.led_pattern_start
            state = LED_STATES[self.led_state]

            brightness = self.get_led_brightness(state['pattern'], t)

            r, g, b = state['color']
            self.surface.set_led(0,
                int(r * brightness),
                int(g * brightness),
                int(b * brightness)
            )

        except Exception as e:
            print(f"✗ LED update error: {e}")

    def cycle_display_mode(self):
        """Cycle to next display mode"""
        current_idx = self.display_modes.index(self.current_mode)
        self.current_mode = self.display_modes[(current_idx + 1) % len(self.display_modes)]
        print(f"✓ Display mode: {self.current_mode}")

        # Force immediate LCD update
        self.last_lcd_update = 0

    def get_system_state(self):
        """
        Get current system state

        This is a simple implementation. In production, this would:
        - Query enhanced-memory for recent agent activity
        - Check MCP server health
        - Monitor agent-runtime-mcp for active tasks
        - Track file operations, git status, etc.
        """

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
            'time': datetime.now().strftime("%H:%M"),
            'tasks_done': 0,
            'tasks_total': 0,
            'progress': 0
        }

    def get_display_for_mode(self, state):
        """Get LCD content for current display mode"""

        if self.current_mode == 'agent_status':
            return self.get_agent_status_display(state)

        elif self.current_mode == 'system_health':
            return self.get_system_health_display(state)

        elif self.current_mode == 'time':
            return self.get_time_display(state)

        elif self.current_mode == 'performance':
            return self.get_performance_display(state)

        return ("Unknown Mode", "")

    def get_agent_status_display(self, state):
        """Agent Status Display Mode"""
        agent = state['agent'][:16]

        if state['tasks_total'] > 0:
            progress = f"{state['tasks_done']}/{state['tasks_total']} | {state['progress']}%"
        else:
            progress = state['status'][:16]

        return (f"Agent: {agent}", progress)

    def get_system_health_display(self, state):
        """System Health Display Mode"""
        # TODO: Query actual MCP server status
        return ("MCP: 5/5 OK", "Mem: Ready")

    def get_time_display(self, state):
        """Time Display Mode"""
        time_str = datetime.now().strftime("%H:%M:%S")
        date_str = datetime.now().strftime("%a %b %d")
        return (time_str, date_str)

    def get_performance_display(self, state):
        """Performance Display Mode"""
        # TODO: Track actual performance metrics
        return ("Session Stats", "Tasks: 0 | 0s")

    def update_display(self, state):
        """Update LCD based on current state and mode"""
        if not self.surface:
            return

        try:
            line1, line2 = self.get_display_for_mode(state)

            # Pad lines to 16 chars for clean display
            line1 = line1[:16].ljust(16)
            line2 = line2[:16].ljust(16)

            self.surface.lcd_write(0, 0, line1)
            self.surface.lcd_write(1, 0, line2)

        except Exception as e:
            print(f"✗ Display update error: {e}")
            self.connection_retries += 1
            if self.connection_retries > self.max_retries:
                print(f"✗ Max retries exceeded, reconnecting...")
                self.surface = None
                self.connection_retries = 0

    def should_update_lcd(self, current_state, current_time):
        """Determine if LCD should be updated"""

        # Enforce minimum update interval
        if current_time - self.last_lcd_update < self.MIN_LCD_UPDATE:
            return False

        # State changed - update immediately
        if current_state != self.last_state:
            return True

        # Idle mode - update every 30 seconds for time
        if self.current_mode == 'time':
            if current_time - self.last_lcd_update >= self.IDLE_UPDATE:
                return True

        return False

    def run(self):
        """Main daemon loop"""
        print("✓ Arduino Enhanced Daemon starting...")
        print(f"✓ Display modes: {', '.join(self.display_modes)}")

        # Initial connection
        if not self.connect():
            print("✗ Initial connection failed, will retry...")

        # Startup display
        if self.surface:
            self.surface.lcd_clear()
            self.surface.lcd_write(0, 0, "Enhanced Daemon")
            self.surface.lcd_write(1, 0, "Starting...")
            time.sleep(2)

        # Main loop
        while self.running:
            try:
                current_time = time.time()

                # Reconnect if needed
                if not self.surface:
                    if self.connect():
                        self.surface.lcd_clear()
                        self.surface.lcd_write(0, 0, "Reconnected")
                        time.sleep(1)
                    else:
                        time.sleep(5)
                        continue

                # Get current state
                current_state = self.get_system_state()

                # Update LCD if needed
                if self.should_update_lcd(current_state, current_time):
                    self.update_display(current_state)
                    self.last_state = current_state
                    self.last_lcd_update = current_time

                # Update LED pattern (more frequent for smooth animation)
                if current_time - self.last_led_update >= self.LED_UPDATE:
                    self.update_led_pattern()
                    self.last_led_update = current_time

                # Sleep briefly
                time.sleep(0.05)

            except Exception as e:
                print(f"✗ Daemon loop error: {e}")
                time.sleep(5)


def main():
    """Entry point"""
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        port = '/dev/tty.usbmodem8344401'

    daemon = ArduinoEnhancedDaemon(port)

    try:
        daemon.run()
    except Exception as e:
        print(f"✗ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

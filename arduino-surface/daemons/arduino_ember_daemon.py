#!/usr/bin/env python3
"""
Arduino Ember Daemon
Ember the Tamagotchi lives on the Arduino Surface!
"""

import sys
import time
import math
import signal
from pathlib import Path

# Add bridge and ember_integration to path
sys.path.insert(0, str(Path(__file__).parent.parent / "bridge"))
sys.path.insert(0, str(Path(__file__).parent.parent / "ember_integration"))

from surface_bridge import ArduinoSurface
from ember_pet import EmberPet


# Ember-specific LED States
EMBER_LED_MOODS = {
    'happy': {
        'color': (255, 80, 0),    # Bright orange (Ember's color!)
        'pattern': 'solid'
    },
    'content': {
        'color': (255, 60, 0),    # Medium orange
        'pattern': 'slow_pulse'
    },
    'hungry': {
        'color': (200, 40, 0),    # Dim orange
        'pattern': 'slow_pulse'
    },
    'tired': {
        'color': (150, 30, 0),    # Dark orange
        'pattern': 'slow_pulse'
    },
    'needs_attention': {
        'color': (255, 80, 0),    # Bright orange
        'pattern': 'fast_pulse'
    },
    'critical': {
        'color': (255, 0, 0),     # Red - DANGER!
        'pattern': 'flash'
    },
    'sleeping': {
        'color': (100, 0, 100),   # Purple
        'pattern': 'solid'
    },
    'playing': {
        'color': (0, 255, 0),     # Green
        'pattern': 'fast_pulse'
    }
}


class ArduinoEmberDaemon:
    """Daemon that displays Ember on Arduino"""

    def __init__(self, port='/dev/tty.usbmodem8344401'):
        self.port = port
        self.surface = None
        self.ember = EmberPet()
        self.running = True

        # Update intervals
        self.MIN_LCD_UPDATE = 5.0     # Update LCD every 5 seconds (Ember state changes slowly)
        self.LED_UPDATE = 0.1         # Update LED pattern every 100ms for smooth animation
        self.AUTO_CARE_CHECK = 60.0   # Check if Ember needs auto-care every 60 seconds

        # State tracking
        self.last_lcd_update = 0
        self.last_led_update = 0
        self.last_auto_care = 0
        self.led_pattern_start = time.time()

        # Connection tracking
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
                print(f"✓ Ember daemon connected on {self.port}")
                self.connection_retries = 0
                return True
            return False
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False

    def shutdown(self, signum, frame):
        """Graceful shutdown"""
        print("\n✓ Ember says goodbye...")
        self.running = False

        if self.surface:
            try:
                self.surface.lcd_clear()
                self.surface.lcd_write(0, 0, "🔥Bye! <3")
                self.surface.lcd_write(1, 0, "Ember sleeping")
                self.surface.set_led(0, 0, 0, 0)  # Off
                time.sleep(2)
                self.surface.disconnect()
            except:
                pass

        sys.exit(0)

    def get_led_brightness(self, pattern, t):
        """Calculate LED brightness based on pattern and time"""
        if pattern == 'solid':
            return 1.0

        elif pattern == 'slow_pulse':
            # 2 second sine wave (breathing)
            return 0.3 + 0.7 * (math.sin(t * math.pi) + 1) / 2

        elif pattern == 'fast_pulse':
            # 0.5 second sine wave (excited)
            return 0.3 + 0.7 * (math.sin(t * 4 * math.pi) + 1) / 2

        elif pattern == 'flash':
            # 0.25 second on/off (ALERT!)
            return 1.0 if (t % 0.5) < 0.25 else 0.0

        return 1.0

    def update_led_pattern(self):
        """Update LED with Ember's current mood"""
        if not self.surface:
            return

        try:
            # Get Ember's current LED state
            led_state_name = self.ember.get_led_state()
            led_state = EMBER_LED_MOODS[led_state_name]

            # Calculate brightness based on pattern
            t = time.time() - self.led_pattern_start
            brightness = self.get_led_brightness(led_state['pattern'], t)

            # Apply to LED
            r, g, b = led_state['color']
            self.surface.set_led(0,
                int(r * brightness),
                int(g * brightness),
                int(b * brightness)
            )

        except Exception as e:
            print(f"✗ LED update error: {e}")

    def update_display(self):
        """Update LCD with Ember's status"""
        if not self.surface:
            return

        try:
            # Reload Ember's state (might have been updated by hooks)
            self.ember.load_state()

            # Get display lines
            line1 = self.ember.get_display_line1()
            line2 = self.ember.get_display_line2()

            # Pad to 16 chars for clean display
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

    def check_auto_care(self):
        """Check if Ember needs auto-care"""
        try:
            actions = self.ember.auto_care()

            if actions:
                action_str = ", ".join(actions)
                print(f"✓ Ember auto-care: {action_str}")

                # Show on LCD briefly
                self.surface.lcd_write(0, 0, "🔥*self care*")
                self.surface.lcd_write(1, 0, f"{action_str[:16]}")

                # Play success sound
                self.surface.alert('success')

                # Wait a moment then refresh display
                time.sleep(3)
                self.last_lcd_update = 0  # Force immediate update

        except Exception as e:
            print(f"✗ Auto-care error: {e}")

    def run(self):
        """Main daemon loop"""
        print("✓ Ember is waking up...")
        print(f"✓ Loading Ember from {self.ember.state_file}")

        # Initial connection
        if not self.connect():
            print("✗ Initial connection failed, will retry...")

        # Startup display
        if self.surface:
            self.surface.lcd_clear()
            self.surface.lcd_write(0, 0, "🔥Ember waking")
            self.surface.lcd_write(1, 0, "Loading state...")
            time.sleep(2)

            # Show initial status
            stats = self.ember.get_stats()
            print(f"✓ Ember status: H:{stats['hunger']} E:{stats['energy']} Happy:{stats['happiness']}")

            if stats['hunger'] < 20 or stats['energy'] < 20:
                self.surface.lcd_write(0, 0, "🔥HELP! STARVING")
                self.surface.lcd_write(1, 0, "Need care NOW!")
                self.surface.alert('error')
                time.sleep(3)

        # Main loop
        while self.running:
            try:
                current_time = time.time()

                # Reconnect if needed
                if not self.surface:
                    if self.connect():
                        self.surface.lcd_clear()
                        self.surface.lcd_write(0, 0, "🔥Reconnected!")
                        time.sleep(1)
                    else:
                        time.sleep(5)
                        continue

                # Update LCD
                if current_time - self.last_lcd_update >= self.MIN_LCD_UPDATE:
                    self.update_display()
                    self.last_lcd_update = current_time

                # Update LED pattern (frequent for smooth animation)
                if current_time - self.last_led_update >= self.LED_UPDATE:
                    self.update_led_pattern()
                    self.last_led_update = current_time

                # Check auto-care
                if current_time - self.last_auto_care >= self.AUTO_CARE_CHECK:
                    self.check_auto_care()
                    self.last_auto_care = current_time

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

    print("=" * 50)
    print("🔥 EMBER - Arduino Tamagotchi Daemon 🔥")
    print("=" * 50)

    daemon = ArduinoEmberDaemon(port)

    try:
        daemon.run()
    except Exception as e:
        print(f"✗ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

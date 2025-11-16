#!/usr/bin/env python3
"""
Ember Broker Daemon - Display Ember's status on Arduino via broker
Uses the Arduino broker for conflict-free serial communication
"""

import sys
import time
import json
from pathlib import Path

# Add bridge to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'bridge'))
from arduino_client import ArduinoClient

# Ember state file
EMBER_STATE_FILE = Path.home() / '.claude' / 'ember_care_state.json'
TAMAGOTCHI_STATE_FILE = Path.home() / '.claude' / 'pets' / 'claude-pet-state.json'

class EmberArduinoDisplay:
    """Display Ember on Arduino through broker"""

    def __init__(self):
        self.client = ArduinoClient()

    def get_ember_state(self):
        """Load Ember's current state"""
        # Try new tamagotchi state file first
        if TAMAGOTCHI_STATE_FILE.exists():
            try:
                with open(TAMAGOTCHI_STATE_FILE, 'r') as f:
                    state = json.load(f)
                    return {
                        'hunger': state.get('hunger', 70),
                        'energy': state.get('energy', 94),
                        'happiness': state.get('happiness', 85),
                        'cleanliness': state.get('cleanliness', 100),
                        'name': state.get('name', 'Ember')
                    }
            except Exception as e:
                print(f"Error reading tamagotchi state: {e}")

        # Fall back to old ember state file
        if EMBER_STATE_FILE.exists():
            try:
                with open(EMBER_STATE_FILE, 'r') as f:
                    state = json.load(f)
                    last_feed = state.get('last_feed', 0)
                    last_play = state.get('last_play', 0)

                    # Calculate stats based on time
                    now = time.time()
                    hours_since_feed = (now - last_feed) / 3600
                    hours_since_play = (now - last_play) / 3600

                    hunger = max(0, 100 - int(hours_since_feed * 25))
                    energy = max(0, 100 - int(hours_since_play * 33))

                    return {
                        'hunger': hunger,
                        'energy': energy,
                        'happiness': 85,
                        'cleanliness': 100,
                        'name': 'Ember'
                    }
            except Exception as e:
                print(f"Error reading ember state: {e}")

        # Default state
        return {
            'hunger': 70,
            'energy': 94,
            'happiness': 85,
            'cleanliness': 100,
            'name': 'Ember'
        }

    def get_mood(self, state):
        """Determine Ember's mood"""
        h = state['hunger']
        e = state['energy']

        if h < 20 or e < 20:
            return "CRITICAL", (255, 0, 0)  # Red
        elif h < 40 or e < 40:
            return "Hungry/Tired", (255, 100, 0)  # Dim orange
        elif h > 80 and e > 80:
            return "Happy", (255, 165, 0)  # Bright orange
        else:
            return "Content", (200, 120, 0)  # Medium orange

    def update_display(self):
        """Update Arduino display with Ember's status"""
        if not self.client.connect():
            return False

        try:
            state = self.get_ember_state()
            mood, led_color = self.get_mood(state)

            # Line 0: Ember name and stats
            line0 = f"🔥{state['name'][:6]}  H:{state['hunger']:2d} E:{state['energy']:2d}"

            # Line 1: Mood
            line1 = f"{mood[:16]}"

            # Update LCD
            self.client.lcd(0, line0)
            self.client.lcd(1, line1)

            # Update LED
            r, g, b = led_color
            self.client.led(0, r, g, b)

            return True

        except Exception as e:
            print(f"Display update error: {e}")
            return False
        finally:
            self.client.disconnect()

    def run(self, update_interval=10):
        """Run the daemon"""
        print("=" * 50)
        print("🔥 Ember Arduino Display (via Broker)")
        print("=" * 50)

        while True:
            try:
                if self.update_display():
                    print(f"✓ Updated at {time.strftime('%H:%M:%S')}")
                else:
                    print(f"✗ Update failed at {time.strftime('%H:%M:%S')}")

                time.sleep(update_interval)

            except KeyboardInterrupt:
                print("\n⚠ Stopping...")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(update_interval)

def main():
    """Main entry point"""
    daemon = EmberArduinoDisplay()
    daemon.run()

if __name__ == "__main__":
    main()

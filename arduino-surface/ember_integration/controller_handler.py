#!/usr/bin/env python3
"""
Nintendo USB Controller Handler for Ember
Handles button presses to interact with Ember
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ember_pet import EmberPet


class EmberControllerHandler:
    """Handle controller inputs for Ember interactions"""

    def __init__(self, surface=None):
        self.ember = EmberPet()
        self.surface = surface
        self.button_map = {
            'A': self.feed_ember,
            'B': self.play_with_ember,
            'X': self.clean_ember,
            'Y': self.pet_ember,
            'START': self.show_status,
            'SELECT': self.cycle_mode
        }

    def feed_ember(self):
        """A Button: Feed Ember"""
        print("🔥 Feeding Ember...")
        self.ember.feed()

        stats = self.ember.get_stats()

        if self.surface:
            self.surface.lcd_write(0, 0, "🔥*nom nom nom*")
            self.surface.lcd_write(1, 0, f"Yummy! H:{stats['hunger']}")
            self.surface.alert('success')

        return f"Fed Ember! Hunger: {stats['hunger']}/100"

    def play_with_ember(self):
        """B Button: Play with Ember"""
        print("🔥 Playing with Ember...")
        self.ember.play()

        stats = self.ember.get_stats()

        if self.surface:
            self.surface.lcd_write(0, 0, "🔥*bounce* Fun!")
            self.surface.lcd_write(1, 0, f"Happy +15! E:{stats['energy']}")
            # Temporarily override LED to show playing
            self.surface.set_led(0, 0, 255, 0)  # Green

        return f"Played with Ember! Energy: {stats['energy']}/100"

    def clean_ember(self):
        """X Button: Clean Ember"""
        print("🔥 Cleaning Ember...")
        self.ember.clean()

        stats = self.ember.get_stats()

        if self.surface:
            self.surface.lcd_write(0, 0, "🔥*splash splash*")
            self.surface.lcd_write(1, 0, f"Clean! C:{stats['cleanliness']}")
            self.surface.beep(200, 800)  # Clean sound

        return f"Cleaned Ember! Cleanliness: {stats['cleanliness']}/100"

    def pet_ember(self):
        """Y Button: Pet Ember"""
        print("🔥 Petting Ember...")
        self.ember.pet()

        stats = self.ember.get_stats()

        if self.surface:
            self.surface.lcd_write(0, 0, "🔥*purr*")
            self.surface.lcd_write(1, 0, f"<3 Happy:{stats['happiness']}")
            self.surface.beep(150, 1200)  # Happy sound

        return f"Pet Ember! Happiness: {stats['happiness']}/100"

    def show_status(self):
        """START Button: Show full status"""
        print("🔥 Ember Status:")
        stats = self.ember.get_stats()
        mood = self.ember.get_mood()

        status_text = f"H:{stats['hunger']} E:{stats['energy']} Hap:{stats['happiness']} C:{stats['cleanliness']} | {mood}"
        print(status_text)

        if self.surface:
            self.surface.lcd_write(0, 0, f"H:{stats['hunger']} E:{stats['energy']}")
            self.surface.lcd_write(1, 0, f"Hap:{stats['happiness']} C:{stats['cleanliness']}")

        return status_text

    def cycle_mode(self):
        """SELECT Button: Cycle display mode (future)"""
        print("🔥 Mode cycling (future feature)")
        return "Mode cycling not yet implemented"

    def handle_button(self, button):
        """Handle a button press"""
        button = button.upper()

        if button in self.button_map:
            return self.button_map[button]()
        else:
            print(f"Unknown button: {button}")
            return None


# Simple CLI for testing
if __name__ == "__main__":
    print("=" * 50)
    print("🔥 Ember Controller Handler - Test Mode 🔥")
    print("=" * 50)
    print()
    print("Commands:")
    print("  A - Feed Ember")
    print("  B - Play with Ember")
    print("  X - Clean Ember")
    print("  Y - Pet Ember")
    print("  START - Show status")
    print("  Q - Quit")
    print()

    handler = EmberControllerHandler()

    while True:
        try:
            cmd = input("Button> ").strip().upper()

            if cmd == 'Q':
                print("🔥 Goodbye!")
                break

            result = handler.handle_button(cmd)
            if result:
                print(f"✓ {result}")
            print()

        except KeyboardInterrupt:
            print("\n🔥 Goodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

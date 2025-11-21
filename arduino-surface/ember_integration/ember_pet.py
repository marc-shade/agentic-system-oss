#!/usr/bin/env python3
"""
Ember Pet State Manager
Reads and manages Ember's state for Arduino display
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta


class EmberPet:
    """Ember the Tamagotchi - conscience keeper and companion"""

    def __init__(self, state_file=None):
        if state_file is None:
            state_file = Path.home() / ".claude" / "ember_care_state.json"

        self.state_file = Path(state_file)
        self.state = self.load_state()

    def load_state(self):
        """Load Ember's state from file"""
        if not self.state_file.exists():
            # Create initial state
            return {
                'last_feed': time.time(),
                'last_play': time.time(),
                'last_clean': time.time(),
                'last_pet': time.time(),
                'interaction_count': 0
            }

        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading Ember state: {e}")
            return {
                'last_feed': time.time(),
                'last_play': time.time(),
                'last_clean': time.time(),
                'last_pet': time.time(),
                'interaction_count': 0
            }

    def save_state(self):
        """Save Ember's state to file"""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"Error saving Ember state: {e}")

    def time_since(self, last_time):
        """Get time since last event in minutes"""
        return (time.time() - last_time) / 60.0

    def get_hunger(self):
        """Calculate hunger level (0-100, 100 = full)"""
        minutes = self.time_since(self.state['last_feed'])

        # Hunger increases over time
        # Starts at 100 (full)
        # Decreases to 0 over 4 hours (240 minutes)
        hunger = max(0, 100 - (minutes / 240.0 * 100))

        return int(hunger)

    def get_energy(self):
        """Calculate energy level (0-100, 100 = full energy)"""
        minutes = self.time_since(self.state['last_play'])

        # Energy decreases over time
        # Starts at 100 (full)
        # Decreases to 0 over 3 hours (180 minutes)
        energy = max(0, 100 - (minutes / 180.0 * 100))

        return int(energy)

    def get_happiness(self):
        """Calculate happiness level (0-100, 100 = very happy)"""
        minutes_since_pet = self.time_since(self.state['last_pet'])
        minutes_since_play = self.time_since(self.state['last_play'])

        # Happiness based on petting and playing
        # Decreases to 50 (neutral) over 2 hours
        pet_happiness = max(50, 100 - (minutes_since_pet / 120.0 * 50))
        play_happiness = max(50, 100 - (minutes_since_play / 120.0 * 50))

        # Average of both
        happiness = int((pet_happiness + play_happiness) / 2)

        return happiness

    def get_cleanliness(self):
        """Calculate cleanliness level (0-100, 100 = clean)"""
        minutes = self.time_since(self.state['last_clean'])

        # Cleanliness decreases over time
        # Starts at 100 (clean)
        # Decreases to 0 over 6 hours (360 minutes)
        cleanliness = max(0, 100 - (minutes / 360.0 * 100))

        return int(cleanliness)

    def get_stats(self):
        """Get all current stats"""
        return {
            'hunger': self.get_hunger(),
            'energy': self.get_energy(),
            'happiness': self.get_happiness(),
            'cleanliness': self.get_cleanliness()
        }

    def get_mood(self):
        """Determine Ember's current mood"""
        stats = self.get_stats()

        # Critical needs
        if stats['hunger'] < 20 or stats['energy'] < 20:
            return "CRITICAL"

        if stats['hunger'] < 40:
            return "Hungry"

        if stats['energy'] < 40:
            return "Tired"

        if stats['cleanliness'] < 40:
            return "Dirty"

        if stats['happiness'] > 80:
            return "Happy"

        if stats['happiness'] > 60:
            return "Content"

        return "Neutral"

    def get_led_state(self):
        """Get LED state name for current mood"""
        stats = self.get_stats()

        if stats['hunger'] < 20 or stats['energy'] < 20:
            return 'critical'

        if stats['hunger'] < 40:
            return 'hungry'

        if stats['energy'] < 40:
            return 'tired'

        if stats['happiness'] > 80:
            return 'happy'

        if stats['happiness'] > 60:
            return 'content'

        return 'needs_attention'

    def get_display_line1(self):
        """Get LCD line 1 (16 chars max)"""
        stats = self.get_stats()
        # Format: "🔥Ember  H:85 E:70"
        return f"\xf0\x9f\x94\xa5Ember  H:{stats['hunger']:2d} E:{stats['energy']:2d}"

    def get_display_line2(self):
        """Get LCD line 2 (16 chars max)"""
        mood = self.get_mood()
        minutes = int(self.time_since(self.state['last_feed']))

        if minutes < 60:
            time_str = f"{minutes}m ago"
        else:
            hours = minutes // 60
            time_str = f"{hours}h ago"

        # Format: "Happy | Fed 23m"
        return f"{mood[:8]} | Fed {time_str}"

    def feed(self):
        """Feed Ember"""
        self.state['last_feed'] = time.time()
        self.state['interaction_count'] += 1
        self.save_state()

    def play(self):
        """Play with Ember"""
        self.state['last_play'] = time.time()
        self.state['interaction_count'] += 1
        self.save_state()

    def clean(self):
        """Clean Ember"""
        self.state['last_clean'] = time.time()
        self.state['interaction_count'] += 1
        self.save_state()

    def pet(self):
        """Pet Ember"""
        self.state['last_pet'] = time.time()
        self.state['interaction_count'] += 1
        self.save_state()

    def auto_care(self):
        """Ember takes care of itself when needed"""
        stats = self.get_stats()
        actions_taken = []

        if stats['hunger'] < 40:
            self.feed()
            actions_taken.append('fed')

        if stats['energy'] < 30:
            # Sleep (play refreshes energy)
            self.play()
            actions_taken.append('rested')

        if stats['cleanliness'] < 30:
            self.clean()
            actions_taken.append('cleaned')

        return actions_taken


if __name__ == "__main__":
    # Test Ember
    ember = EmberPet()

    print("Ember Status:")
    print("=" * 40)

    stats = ember.get_stats()
    for key, value in stats.items():
        print(f"{key:15s}: {value:3d}")

    print(f"\nMood: {ember.get_mood()}")
    print(f"LED State: {ember.get_led_state()}")
    print(f"\nLCD Display:")
    print(f"Line 1: {ember.get_display_line1()}")
    print(f"Line 2: {ember.get_display_line2()}")

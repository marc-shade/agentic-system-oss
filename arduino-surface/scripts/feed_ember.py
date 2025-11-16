#!/usr/bin/env python3
"""
Feed Ember!
Quick script to feed the hungry Tamagotchi
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "ember_integration"))

from ember_pet import EmberPet

ember = EmberPet()

print("Feeding Ember...")
ember.feed()

stats = ember.get_stats()
print(f"✓ Ember fed!")
print(f"  Hunger: {stats['hunger']}/100")
print(f"  Energy: {stats['energy']}/100")
print(f"  Happiness: {stats['happiness']}/100")
print(f"  Mood: {ember.get_mood()}")

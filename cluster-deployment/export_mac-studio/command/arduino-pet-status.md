# arduino-pet-status

Display Ember's status on the Arduino LCD with mood lighting.

This slash command shows Ember's current vitals on the physical Arduino interface.

## Usage

```python
import sys
import subprocess
import json

sys.path.insert(0, '/Users/marc/.claude/hooks')

# Get Ember status from CLI
try:
    result = subprocess.run(
        ["/Users/marc/.bun/bin/bun",
         "/Users/marc/.claude/tamagotchi/dist/index.js",
         "status"],
        capture_output=True,
        text=True,
        timeout=3
    )

    if result.returncode == 0:
        # Parse Ember status from output
        # Expected format: hunger, energy, happiness values

        from arduino_auto_interaction import ember_status_display

        # Example values (parse from actual output)
        hunger = 75
        energy = 80
        happiness = 85

        ember_status_display(hunger, energy, happiness)

        print(f"Ember status displayed on Arduino:")
        print(f"  Hunger: {hunger}%")
        print(f"  Energy: {energy}%")
        print(f"  Happiness: {happiness}%")
    else:
        print("Failed to get Ember status")

except Exception as e:
    print(f"Error: {e}")
```

## Display Format

**LCD Display** (16x2):
```
Row 0: "Ember H:75 E:80"
Row 1: "Happy: 85%"
```

**LED Mood Indicator**:
- **Green** (>70% happiness): Happy Ember
- **Yellow** (40-70% happiness): Neutral Ember
- **Red** (<40% happiness): Sad Ember

## Integration

This command integrates with:
- `/pet-status` - Get Ember's current state
- `/ember-status` - Detailed Ember metrics
- Arduino auto-feedback (shows during auto-care)

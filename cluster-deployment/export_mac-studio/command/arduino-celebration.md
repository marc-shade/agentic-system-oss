# arduino-celebration

Trigger a victory animation on Arduino (LED + servo + beep + LCD).

This slash command creates a physical celebration when major milestones are achieved.

## Usage

```python
import sys
import time

sys.path.insert(0, '/Users/marc/.claude/hooks')
from arduino_auto_interaction import ArduinoFeedback

arduino = ArduinoFeedback()

# Celebration sequence
def celebrate(message="Success!"):
    # Rainbow LED sequence
    colors = [
        (255, 0, 0),    # Red
        (255, 165, 0),  # Orange
        (255, 255, 0),  # Yellow
        (0, 255, 0),    # Green
        (0, 0, 255),    # Blue
        (128, 0, 128),  # Purple
    ]

    for r, g, b in colors:
        arduino.set_led(r, g, b)
        time.sleep(0.2)

    # Servo sweep animation
    for angle in [0, 45, 90, 135, 180, 135, 90, 45, 0]:
        arduino.set_servo(angle)
        time.sleep(0.1)

    # Victory beeps
    for freq in [1000, 1200, 1400, 1600, 1800]:
        arduino.beep(100, freq)
        time.sleep(0.1)

    # Display victory message
    arduino.clear_display()
    arduino.display_text(0, 0, message[:16])
    arduino.display_text(1, 0, "🎉 Victory! 🎉"[:16])

    # Final green LED
    arduino.set_led(0, 255, 0)

celebrate("Project Done!")
print("🎉 Celebration complete!")
```

## Use Cases

- **Project completion**: Major feature shipped
- **Test suite passes**: All tests green
- **Deployment success**: Production deploy complete
- **Learning milestone**: New skill mastered
- **Personal achievement**: Goal achieved

## Celebration Levels

**Level 1** (Minor achievement):
```python
arduino.alert("success")
```

**Level 2** (Good achievement):
```python
# Quick LED flash + beeps
for _ in range(3):
    arduino.set_led(0, 255, 0)
    arduino.beep(100, 1500)
    time.sleep(0.1)
```

**Level 3** (Major achievement):
```python
celebrate("Major Win!")  # Full sequence
```

## Integration

Works with:
- Project completion workflows
- CI/CD success notifications
- Learning system milestones
- User-defined achievement triggers

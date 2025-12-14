# arduino-alert-user

Get user's attention via Arduino (all actuators activated).

This slash command triggers maximum physical feedback to alert Marc of critical events.

## Usage

```python
import sys
sys.path.insert(0, '/Users/marc/.claude/hooks')
from arduino_auto_interaction import ArduinoFeedback
import time

arduino = ArduinoFeedback()

def alert_user(message="ATTENTION", urgency="high"):
    """
    Alert user with varying levels of urgency

    Args:
        message: Message to display (up to 32 chars)
        urgency: "low", "medium", or "high"
    """
    if urgency == "high":
        # Red LED flashing
        for _ in range(5):
            arduino.set_led(255, 0, 0)
            time.sleep(0.2)
            arduino.set_led(0, 0, 0)
            time.sleep(0.2)

        # Loud beeping
        for _ in range(3):
            arduino.beep(300, 2000)
            time.sleep(0.2)

        # Servo sweep for attention
        for angle in [0, 180, 0, 180, 0]:
            arduino.set_servo(angle)
            time.sleep(0.3)

    elif urgency == "medium":
        # Yellow LED
        arduino.set_led(255, 255, 0)
        arduino.beep(200, 1500)
        arduino.set_servo(90)

    else:  # low
        # Blue LED
        arduino.set_led(0, 0, 255)
        arduino.beep(100, 1000)

    # Display message
    arduino.clear_display()
    arduino.display_text(0, 0, message[:16])

    # Keep LED on
    if urgency == "high":
        arduino.set_led(255, 0, 0)
    elif urgency == "medium":
        arduino.set_led(255, 255, 0)
    else:
        arduino.set_led(0, 0, 255)

# Examples
alert_user("Build Failed!", "high")
alert_user("Review Needed", "medium")
alert_user("Update Ready", "low")
```

## Urgency Levels

### High (Critical)
- **Use**: System failures, security alerts, urgent user input needed
- **Behavior**: Red flashing LED, loud beeps, servo animation
- **Duration**: ~5 seconds

### Medium (Important)
- **Use**: Build failures, test failures, important notifications
- **Behavior**: Yellow LED, medium beep, centered servo
- **Duration**: ~1 second

### Low (Informational)
- **Use**: Updates available, background task complete
- **Behavior**: Blue LED, single beep
- **Duration**: <1 second

## Use Cases

**Critical Alerts**:
- System security breaches
- Data loss prevention triggers
- Emergency stop conditions
- User confirmation required for destructive operations

**Important Notifications**:
- CI/CD pipeline failures
- Production deployment issues
- Ember happiness critically low
- Storage capacity warnings

**Info Notifications**:
- Long-running task completion
- System updates available
- Scheduled maintenance reminders
- Achievement unlocked

## Integration

Integrates with:
- Temporal workflow error handlers
- AutoKitteh emergency triggers
- System health monitoring alerts
- Ember critical state notifications

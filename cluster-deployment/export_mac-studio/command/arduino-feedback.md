# arduino-feedback

Send manual feedback to Arduino Surface (LED + LCD + beep).

This slash command provides manual control over Arduino feedback for user-triggered events.

## Usage

Specify the feedback type and optional message:

**Success feedback**:
```python
import sys
sys.path.insert(0, '/Users/marc/.claude/hooks')
from arduino_auto_interaction import tool_success_feedback
tool_success_feedback("Operation Complete")
```

**Error feedback**:
```python
import sys
sys.path.insert(0, '/Users/marc/.claude/hooks')
from arduino_auto_interaction import tool_failure_feedback
tool_failure_feedback("Operation Failed")
```

**Custom feedback**:
```python
import sys
sys.path.insert(0, '/Users/marc/.claude/hooks')
from arduino_auto_interaction import ArduinoFeedback

arduino = ArduinoFeedback()

# Set LED color
arduino.set_led(255, 0, 255)  # Purple

# Display message
arduino.clear_display()
arduino.display_text(0, 0, "Custom Message")
arduino.display_text(1, 0, "Line 2")

# Play beep
arduino.beep(200, 1500)
```

## Feedback Types

- **Success**: Green LED + ascending beeps + "✓" on LCD
- **Error**: Red LED + descending beeps + "✗" on LCD
- **Warning**: Yellow LED + mid-tone beep
- **Info**: Blue LED + single beep

## Use Cases

- Manual celebrations after completing complex tasks
- User-triggered alerts for important events
- Testing Arduino hardware
- Debugging physical interface

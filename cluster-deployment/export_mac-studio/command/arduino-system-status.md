# arduino-system-status

Display system metrics on Arduino LCD.

This slash command shows current system status on the physical interface.

## Usage

```python
import sys
import psutil

sys.path.insert(0, '/Users/marc/.claude/hooks')
from arduino_auto_interaction import system_status_display, ArduinoFeedback

arduino = ArduinoFeedback()

# Get system metrics
cpu_percent = psutil.cpu_percent(interval=1)
memory = psutil.virtual_memory()
mem_percent = memory.percent

# Display on Arduino
arduino.clear_display()
arduino.display_text(0, 0, f"CPU: {cpu_percent:.0f}%")
arduino.display_text(1, 0, f"MEM: {mem_percent:.0f}%")

# Set LED based on load
if cpu_percent > 80:
    arduino.set_led(255, 0, 0)  # Red - high load
elif cpu_percent > 50:
    arduino.set_led(255, 255, 0)  # Yellow - medium load
else:
    arduino.set_led(0, 255, 0)  # Green - low load

print(f"System status displayed:")
print(f"  CPU: {cpu_percent:.1f}%")
print(f"  Memory: {mem_percent:.1f}%")
```

## Display Options

**CPU + Memory**:
```
Row 0: "CPU: 45%"
Row 1: "MEM: 62%"
```

**Services Status**:
```
Row 0: "Temporal: OK"
Row 1: "AutoKitteh: OK"
```

**Storage Status**:
```
Row 0: "Hot: 1.5GB"
Row 1: "Cold: 500MB"
```

## LED Color Guide

- **Green**: All systems nominal (<50% load)
- **Yellow**: Moderate load (50-80%)
- **Red**: High load (>80%)
- **Blue**: Services starting/restarting
- **Purple**: Memory operations in progress

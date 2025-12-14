# Arduino Physical Control Skill

Use this skill when the user wants to interact with physical hardware, create tangible feedback, visualize system status physically, or implement human-in-the-loop workflows with real-world controls.

## When to Use This Skill

- Physical status visualization (LEDs showing system health)
- Tactile human approval gates (buttons for confirm/cancel)
- Environmental sensing (temperature, light, motion, dials)
- Tangible alerts and notifications (buzzers, servos, displays)
- Physical dashboards for MCP infrastructure
- ARC-2 puzzle verification interfaces
- Parameter tuning with physical dials
- Emergency stop mechanisms (tilt switch)
- Making abstract AI processing visible and tangible

## Available Hardware

### Arduino UNO R3 Setup
Connected via `/dev/tty.usbmodem8343401` (update port as needed)

**Components:**
- **3x RGB LEDs** - Tier0/Tier1/Tier2 status indicators
- **16x2 LCD Display** - Text output (2 rows × 16 chars)
- **Servo Motor** - Position indicator (0-180°)
- **Buzzer** - Audio feedback and alerts
- **2x Buttons** - Confirm and Cancel inputs
- **Potentiometer** - Analog dial input (0-1023)
- **Temperature Sensor** - Environmental temp in Celsius
- **Light Sensor** - Ambient light level (0-1023)
- **Tilt Switch** - Emergency stop trigger

**Reference:** [Arduino Starter Kit](https://store.arduino.cc/products/arduino-starter-kit-multi-language)

## MCP Tools Available

When arduino-surface MCP server is running, use these tools:

### Display Output
```python
# Write text to LCD
mcp__arduino-surface__surface.display(row=0, col=0, text="System Ready")
mcp__arduino-surface__surface.display(row=1, col=0, text="Status: OK")

# Clear display
mcp__arduino-surface__surface.display.clear()
```

### LED Status Indicators
```python
# Set tier LED colors (tier 0-2, RGB 0-255)
# Tier0: Foundation (enhanced-memory, voice-mode, arduino-surface)
mcp__arduino-surface__surface.led.set(tier=0, r=0, g=255, b=0)  # Green = healthy

# Tier1: Cognitive (agent-runtime-mcp)
mcp__arduino-surface__surface.led.set(tier=1, r=255, g=165, b=0)  # Orange = warning

# Tier2: Reasoning (sequential-thinking)
mcp__arduino-surface__surface.led.set(tier=2, r=255, g=0, b=0)  # Red = error
```

### Physical Actuators
```python
# Move servo (0-180 degrees, 90=center)
mcp__arduino-surface__surface.servo.set(position=90)

# Beep sound
mcp__arduino-surface__surface.beep(duration_ms=200, frequency_hz=1000)

# Alert patterns (success, warning, error, info)
mcp__arduino-surface__surface.alert(type="success")
```

### Sensor Input
```python
# Get all sensor readings
status = mcp__arduino-surface__surface.status()
# Returns: {pot, temp_c, light, buttons, servo, etc}

# Get just sensor values
sensors = mcp__arduino-surface__surface.sensors()
# Returns: {pot: 512, temp_c: 23.5, light: 678}

# Wait for button press (with timeout)
button = mcp__arduino-surface__surface.wait_button(timeout_seconds=30)
# Returns: "confirm" or "cancel" or timeout
```

## Common Usage Patterns

### 1. System Status Dashboard
Display MCP infrastructure health on physical LEDs:
```python
# Check MCP tier health
tier0_healthy = check_mcp_servers(['enhanced-memory', 'voice-mode'])
tier1_healthy = check_mcp_servers(['agent-runtime-mcp'])
tier2_healthy = check_mcp_servers(['sequential-thinking'])

# Update LEDs
mcp__arduino-surface__surface.led.set(
    tier=0,
    r=0 if tier0_healthy else 255,
    g=255 if tier0_healthy else 0,
    b=0
)

# Display status
mcp__arduino-surface__surface.display(row=0, col=0, text="MCP Status")
mcp__arduino-surface__surface.display(row=1, col=0, text="All Systems OK" if all_healthy else "Errors Detected")
```

### 2. Human Approval Gate
Request physical confirmation before destructive operations:
```python
# Show prompt
mcp__arduino-surface__surface.display.clear()
mcp__arduino-surface__surface.display(row=0, col=0, text="Delete all logs?")
mcp__arduino-surface__surface.display(row=1, col=0, text="Confirm/Cancel")

# Alert for attention
mcp__arduino-surface__surface.alert(type="warning")

# Wait for button
button = mcp__arduino-surface__surface.wait_button(timeout_seconds=30)

if button == "confirm":
    # Proceed with deletion
    mcp__arduino-surface__surface.alert(type="success")
elif button == "cancel":
    # Abort operation
    mcp__arduino-surface__surface.alert(type="info")
else:
    # Timeout
    mcp__arduino-surface__surface.alert(type="error")
```

### 3. Parameter Tuning
Use physical dial for real-time parameter adjustment:
```python
# Instruction
mcp__arduino-surface__surface.display(row=0, col=0, text="Set threshold")
mcp__arduino-surface__surface.display(row=1, col=0, text="Turn dial->Confirm")

# Read potentiometer in loop
while True:
    sensors = mcp__arduino-surface__surface.sensors()
    pot_value = sensors['pot']  # 0-1023

    # Convert to 0.0-1.0 threshold
    threshold = pot_value / 1023.0

    # Show servo position
    servo_pos = int(threshold * 180)
    mcp__arduino-surface__surface.servo.set(position=servo_pos)

    # Wait for confirm
    button = mcp__arduino-surface__surface.wait_button(timeout_seconds=0.5)
    if button == "confirm":
        # Use threshold
        break
```

### 4. Environmental Context
Use sensors to inform agent decisions:
```python
# Read environment
sensors = mcp__arduino-surface__surface.sensors()
temp = sensors['temp_c']
light = sensors['light']

# Adjust behavior based on context
if temp > 25:
    # Too hot, reduce computational load
    pass

if light < 200:
    # Dark environment, user may have left
    # Defer non-urgent tasks
    pass
```

### 5. Progress Indicator
Show workflow execution progress physically:
```python
# Long-running task
total_steps = 10

for i, step in enumerate(tasks):
    # Update LCD
    mcp__arduino-surface__surface.display(row=0, col=0, text=f"Step {i+1}/{total_steps}")
    mcp__arduino-surface__surface.display(row=1, col=0, text=step['name'][:16])

    # Servo shows progress
    progress = int((i / total_steps) * 180)
    mcp__arduino-surface__surface.servo.set(position=progress)

    # Execute step
    execute_step(step)

    # Beep on completion
    if i == total_steps - 1:
        mcp__arduino-surface__surface.alert(type="success")
```

## Architecture Integration

### Tier0 Physical I/O Layer
Arduino Surface is part of the **Tier0 Foundation** alongside:
- `enhanced-memory` - Memory systems
- `voice-mode` - Speech I/O
- `arduino-surface` - Physical world I/O

This creates a complete sensory-motor system for agents:
- **Input**: Voice (ears) + Sensors (touch/sight)
- **Output**: Voice (speech) + Physical (body)
- **Memory**: Enhanced memory (brain)

### Event-Driven Architecture
The Arduino can stream events (button presses, sensor changes, tilt) that agents can react to in real-time, enabling truly interactive physical-digital systems.

## Setup Checklist

Before using Arduino tools, verify:

1. **Hardware Connected**: Arduino UNO R3 plugged into USB
2. **Firmware Flashed**: `firmware/agentic_surface.ino` uploaded
3. **MCP Configured**: arduino-surface in `~/.claude.json`
4. **Port Correct**: Update `/dev/tty.usbmodem8343401` to actual port
5. **Dependencies Installed**: `pip3 install pyserial`

## Troubleshooting

**"Connection closed" error:**
- Check USB cable connected
- Verify port: `ls /dev/tty.usbmodem*`
- Restart MCP server in Claude Code

**LCD shows gibberish:**
- Check I2C address (usually 0x27 or 0x3F)
- Verify wiring: A4=SDA, A5=SCL

**LEDs not working:**
- Check LED polarity (long leg = positive)
- Verify 220Ω resistors in series
- Confirm pin assignments match firmware

**Button not responding:**
- Verify internal pull-up enabled in firmware
- Check wiring and button functionality
- Increase debounce delay if spurious triggers

## Safety Notes

- Arduino operates at 5V (safe for human contact)
- Buzzer can be loud - adjust frequency/duration
- Tilt switch is NOT a certified E-stop
- State is lost on power cycle (no persistence)

## Advanced Patterns

### Multi-Modal Confirmation
Combine voice, visual, and physical confirmation:
```python
# Voice announcement
mcp__voice-mode__converse("Critical operation requires confirmation")

# Visual display
mcp__arduino-surface__surface.display(row=0, col=0, text="CRITICAL ACTION")
mcp__arduino-surface__surface.display(row=1, col=0, text="Press Confirm")

# Physical alert
mcp__arduino-surface__surface.alert(type="warning")
mcp__arduino-surface__surface.led.set(tier=0, r=255, g=165, b=0)

# Wait for physical confirmation
button = mcp__arduino-surface__surface.wait_button(timeout_seconds=30)

# Multi-modal feedback
if button == "confirm":
    mcp__voice-mode__converse("Confirmed. Executing.", wait_for_response=False)
    mcp__arduino-surface__surface.alert(type="success")
```

### Environmental Adaptation
Adjust agent behavior based on physical context:
```python
sensors = mcp__arduino-surface__surface.sensors()

# Hot environment = reduce compute
if sensors['temp_c'] > 28:
    reduce_parallel_agents()

# Bright light = user present
if sensors['light'] > 700:
    enable_interactive_mode()
else:
    defer_non_urgent_tasks()

# Tilt detected = emergency stop
if check_tilt_switch():
    emergency_halt_all_workflows()
```

## Examples Reference

Study these examples in `/Volumes/FILES/agentic-system/arduino-surface/examples/`:
- `mcp_monitor.py` - Real-time MCP status visualization
- `human_in_loop_example.py` - Human approval workflows
- `arc2_puzzle_interface.py` - ARC-2 puzzle verification

## Philosophy

The Arduino Surface makes **abstract AI processing tangible**:
- Digital decisions manifest physically
- Physical world informs agents
- Human-agent interaction becomes tactile
- Status is visible at a glance
- Approval is a physical button press
- Progress is a moving servo
- Alerts are sounds and lights

This creates a **physical presence** for AI agents in the real world.

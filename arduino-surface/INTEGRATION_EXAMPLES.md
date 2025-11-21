# Arduino Surface Integration Examples

Real-world integration patterns for using the Arduino physical control surface with Claude Code agentic AI infrastructure.

## Example 1: MCP Server Health Dashboard

**Use Case**: At-a-glance monitoring of your MCP infrastructure

### Setup
```bash
python3 examples/mcp_monitor.py /dev/tty.usbmodem14101 5
```

### Physical Mapping
```
┌─────────────────────────────────────────────────┐
│ Arduino Physical Surface                        │
├─────────────────────────────────────────────────┤
│ LED Tier0 (Red/Green/Blue)                      │
│   → enhanced-memory + voice-mode status         │
│                                                  │
│ LED Tier1 (Red/Green/Blue)                      │
│   → agent-runtime-mcp status                    │
│                                                  │
│ LED Tier2 (Red/Green/Blue)                      │
│   → sequential-thinking status                  │
│                                                  │
│ Servo (0-180°)                                   │
│   → Workflow + worker activity level            │
│                                                  │
│ LCD Line 0: "MCP: X/3 ok"                       │
│ LCD Line 1: "Flows: X  Wkr: X"                  │
└─────────────────────────────────────────────────┘
```

### Color Codes
- **Green**: All tier servers running
- **Orange**: Some servers running
- **Red**: All servers stopped

### What You'll See
1. **Normal Operation**: All 3 tiers green, servo moving gently
2. **Partial Failure**: One tier orange/red, buzzer alerts
3. **High Activity**: Servo at 120-180°, LCD shows workflow count
4. **Idle System**: Servo at 0°, minimal LED activity

---

## Example 2: Agent Confirmation Workflow

**Use Case**: Agent needs human approval before destructive operation

### Claude Workflow
```
User: "Delete all error logs from the past week"

Claude: I need to confirm this destructive operation.
        Let me use the Arduino surface for physical confirmation.

[Uses MCP tool: surface.display(0, 0, "Delete logs?")]
[Uses MCP tool: surface.display(1, 0, "Confirm=Yes")]
[Uses MCP tool: surface.led.set(0, 255, 255, 0)]  # Yellow warning
[Uses MCP tool: surface.beep(100, 1000)]          # Attention beep
[Uses MCP tool: surface.wait_button(timeout=30)]  # Wait for human

Human presses CONFIRM button physically →

Claude: Confirmation received. Proceeding with deletion...
        [Deletes logs]
        Deleted 1,247 error log files from the past week.

[Uses MCP tool: surface.display(0, 0, "Logs deleted")]
[Uses MCP tool: surface.alert("success")]         # Success pattern
```

### Code Implementation
```python
from surface_bridge import ArduinoSurface

surface = ArduinoSurface("/dev/tty.usbmodem14101")
surface.connect()

# Display question
surface.lcd_write(0, 0, "Delete logs?")
surface.lcd_write(1, 0, "Confirm=Yes")

# Visual/audio attention
surface.set_led(0, 255, 255, 0)  # Yellow
surface.beep(100, 1000)

# Wait for physical confirmation
event = surface.wait_event(timeout=30)

if event and event["button"] == "confirm":
    # Human approved - proceed
    delete_logs()
    surface.alert("success")
else:
    # Human cancelled or timeout
    surface.alert("error")
```

---

## Example 3: Real-Time Parameter Tuning

**Use Case**: Adjust agent confidence threshold while monitoring results

### Physical Setup
1. Start agent processing task
2. Turn potentiometer to adjust threshold (0.0 - 1.0)
3. Servo shows current threshold visually
4. LCD displays numeric value
5. Press CONFIRM to lock in value

### Workflow
```python
from surface_bridge import ArduinoSurface

surface = ArduinoSurface("/dev/tty.usbmodem14101")
surface.connect()

surface.lcd_write(0, 0, "Adjust threshold")

while True:
    status = surface.get_status()
    threshold = status["pot"] / 1023.0  # Normalize to 0.0-1.0

    # Update display
    surface.lcd_write(1, 0, f"Value: {threshold:.2f}")

    # Visual feedback via servo
    servo_pos = int(threshold * 180)
    surface.set_servo(servo_pos)

    # Check for confirmation
    event = surface.wait_event(timeout=0.1)
    if event and event["button"] == "confirm":
        break

# Use threshold in agent processing
agent.set_confidence_threshold(threshold)
```

### What You Experience
- Turn knob left = lower threshold (more cautious)
- Turn knob right = higher threshold (more aggressive)
- Servo moves to show position
- LCD shows exact numeric value
- Press button to lock in

---

## Example 4: Environmental Context for Agents

**Use Case**: Agent adapts behavior based on physical environment

### Scenario 1: Temperature-Based Throttling
```python
status = surface.get_status()

if status["temp_c"] > 30:
    # Room is hot - reduce CPU-intensive operations
    agent.set_processing_mode("low_power")
    surface.lcd_write(0, 0, "Hot room")
    surface.lcd_write(1, 0, "Throttling CPU")
    surface.set_led(0, 255, 165, 0)  # Orange
```

### Scenario 2: Light-Based Scheduling
```python
status = surface.get_status()

if status["light"] < 100:
    # It's dark - probably nighttime
    # Defer non-urgent tasks to morning
    agent.schedule_task("backup", "08:00")
    surface.lcd_write(0, 0, "Night mode")
    surface.lcd_write(1, 0, "Deferred tasks")
```

### Scenario 3: Motion-Based Presence
```python
# If tilt switch used as motion sensor alternative
event = surface.wait_event(timeout=0.1)

if event and event["event"] == "tilt":
    # Human entered room
    agent.pause_loud_operations()
    surface.lcd_write(0, 0, "Human present")
    surface.lcd_write(1, 0, "Quiet mode")
```

---

## Example 5: ARC-2 Puzzle Verification

**Use Case**: Human-in-the-loop verification of AI-generated puzzle solutions

### Workflow
1. Agent generates ARC-2 puzzle solution
2. Solution displayed on screen (terminal or GUI)
3. Human reviews solution visually
4. Human uses Arduino buttons: CONFIRM=correct, CANCEL=incorrect
5. Optionally rate solution quality via potentiometer
6. Results stored for agent learning

### Implementation
```python
from arc2_puzzle_interface import ARC2VerificationInterface

interface = ARC2VerificationInterface(surface)

# Display puzzle info
interface.display_puzzle_info("f8ff0b80", "3x3")

# Generate and display solution (on screen)
solution = agent.generate_arc2_solution("f8ff0b80")
display_solution_visually(solution)

# Request physical verification
verification = interface.request_verification(
    puzzle_id="f8ff0b80",
    solution_num=1,
    timeout=60
)

if verification["correct"]:
    # Get quality rating
    quality = interface.rate_solution_quality(duration=10)

    # Store learning
    agent.store_success_pattern(solution, quality)
else:
    # Store failure for learning
    agent.store_failure_pattern(solution)
```

### Statistics Tracking
```python
# Get session stats
stats = interface.get_verification_stats()
# {
#   "correct": 4,
#   "total": 5,
#   "accuracy": 80.0,
#   "average_time_seconds": 12.3
# }

# Display stats on Arduino
interface.display_statistics(stats)

# Save log for analysis
interface.save_verification_log("arc2_session_log.json")
```

---

## Example 6: Emergency Stop Integration

**Use Case**: Physical interrupt for runaway workflows

### Setup
```python
from surface_bridge import ArduinoSurface

surface = ArduinoSurface("/dev/tty.usbmodem14101")
surface.connect()

def emergency_stop_handler(event):
    """Called when tilt switch triggered"""
    if event.get("triggered"):
        print("🚨 EMERGENCY STOP!")

        # Stop all running workflows
        temporal_client.cancel_all_workflows()

        # Stop MCP servers gracefully
        shutdown_all_mcp_servers()

        # Visual feedback
        for tier in range(3):
            surface.set_led(tier, 255, 0, 0)  # All red

        surface.lcd_clear()
        surface.lcd_write(0, 0, "EMERGENCY STOP!")
        surface.lcd_write(1, 0, "All systems halt")

        # Loud alert
        for _ in range(5):
            surface.beep(200, 500)
            time.sleep(0.1)

# Register handler
surface.start_event_listener()
surface.register_handler("tilt", emergency_stop_handler)

# Agent continues working...
# Tilt Arduino to trigger emergency stop at any time
```

---

## Example 7: Multi-Agent Coordination Display

**Use Case**: Visual representation of parallel agent activity

### Setup
```python
# Map agents to tier LEDs
agent_mapping = {
    "research-coordinator": 0,    # Tier0 LED
    "web-analyst": 1,             # Tier1 LED
    "documentation-researcher": 2 # Tier2 LED
}

# Spawn parallel agents
agents = [
    spawn_agent("research-coordinator"),
    spawn_agent("web-analyst"),
    spawn_agent("documentation-researcher")
]

# Update LEDs as agents work
for agent_name, agent_task in agents.items():
    tier = agent_mapping[agent_name]

    if agent_task.status == "running":
        surface.set_led(tier, 0, 0, 255)  # Blue = working
    elif agent_task.status == "completed":
        surface.set_led(tier, 0, 255, 0)  # Green = done
    elif agent_task.status == "failed":
        surface.set_led(tier, 255, 0, 0)  # Red = error

# Servo shows overall progress
progress = sum(1 for a in agents if a.status == "completed") / len(agents)
surface.set_servo(int(progress * 180))

# LCD shows current focus
surface.lcd_write(0, 0, f"Active: {len([a for a in agents if a.status == 'running'])}")
surface.lcd_write(1, 0, f"Done: {len([a for a in agents if a.status == 'completed'])}/{len(agents)}")
```

---

## Example 8: Cost-Gating for Expensive Operations

**Use Case**: Require human approval for operations over $100

### Workflow
```python
def execute_with_cost_gate(operation, estimated_cost):
    """Execute operation with cost approval if > $100"""

    if estimated_cost > 100:
        # Show cost on LCD
        surface.lcd_clear()
        surface.lcd_write(0, 0, f"Cost: ${estimated_cost:.2f}")
        time.sleep(2)

        # Request approval
        surface.lcd_write(0, 0, "Proceed w/ API?")
        surface.lcd_write(1, 0, "Confirm=Yes")
        surface.set_led(0, 255, 255, 0)  # Yellow warning
        surface.beep(100, 1000)

        event = surface.wait_event(timeout=30)

        if event and event["button"] == "confirm":
            # Approved
            result = operation()
            surface.alert("success")
            return result
        else:
            # Denied or timeout
            surface.alert("error")
            surface.lcd_write(0, 0, "Operation")
            surface.lcd_write(1, 0, "cancelled")
            return None
    else:
        # Cost under threshold - execute directly
        return operation()

# Usage
result = execute_with_cost_gate(
    lambda: expensive_api_call(),
    estimated_cost=125.50
)
```

---

## Example 9: Voice + Physical Feedback

**Use Case**: Combine voice notifications with physical indicators

### Integration
```python
from voice_mode import speak

# Agent starting complex task
speak("Starting data analysis workflow")
surface.lcd_write(0, 0, "Data analysis")
surface.lcd_write(1, 0, "Starting...")
surface.set_led(0, 0, 0, 255)  # Blue = working
surface.beep(100, 1500)

# Agent encounters error
speak("Error detected in data validation")
surface.lcd_write(0, 0, "ERROR")
surface.lcd_write(1, 0, "Data validation")
surface.set_led(0, 255, 0, 0)  # Red = error
surface.alert("error")  # Audio pattern

# Agent completes successfully
speak("Analysis complete with 95 percent confidence")
surface.lcd_write(0, 0, "Complete!")
surface.lcd_write(1, 0, "Conf: 95%")
surface.set_led(0, 0, 255, 0)  # Green = success
surface.alert("success")
```

---

## Example 10: Temporal Workflow Monitoring

**Use Case**: Physical visualization of long-running Temporal workflows

### Integration
```python
import asyncio
from temporalio.client import Client

async def monitor_workflow_on_surface():
    """Monitor Temporal workflow and update Arduino surface"""

    client = await Client.connect("localhost:7233")

    while True:
        # Get workflow list
        workflows = await client.list_workflows()

        running_count = sum(1 for w in workflows if w.status == "Running")
        completed_count = sum(1 for w in workflows if w.status == "Completed")

        # Update LCD
        surface.lcd_clear()
        surface.lcd_write(0, 0, f"Running: {running_count}")
        surface.lcd_write(1, 0, f"Done: {completed_count}")

        # Update servo (activity level)
        activity = min(180, running_count * 30)
        surface.set_servo(activity)

        # LED color based on status
        if running_count > 0:
            surface.set_led(0, 0, 255, 0)  # Green = active
        else:
            surface.set_led(0, 255, 255, 0)  # Yellow = idle

        await asyncio.sleep(5)

# Run monitor
asyncio.run(monitor_workflow_on_surface())
```

---

## Physical Design Patterns

### Pattern 1: Progressive Indication
Use multiple indicators to show state at different granularities:
- **LED Color**: Coarse state (red/yellow/green)
- **Servo Position**: Continuous value (0-180°)
- **LCD Text**: Precise details

### Pattern 2: Attention Hierarchy
Different urgency levels:
- **Info**: Blue LED + single beep
- **Success**: Green LED + ascending beep pattern
- **Warning**: Yellow LED + mid beep
- **Error**: Red LED + loud descending beeps
- **Critical**: All red LEDs + rapid beeping + LCD alert

### Pattern 3: Human-in-Loop
Always provide timeout and fallback:
```python
event = surface.wait_event(timeout=30)
if event:
    # Human responded
    handle_response(event)
else:
    # Timeout - use safe default
    handle_timeout()
```

### Pattern 4: Environmental Context
Use sensors to adapt behavior:
```python
status = surface.get_status()

# Temperature influences processing
if status["temp_c"] > 30:
    throttle_cpu()

# Light influences scheduling
if status["light"] < 100:
    defer_to_morning()

# Potentiometer provides real-time control
threshold = status["pot"] / 1023.0
agent.set_threshold(threshold)
```

---

## Best Practices

### 1. Non-Blocking Operations
Always use timeouts to prevent agent hanging:
```python
event = surface.wait_event(timeout=10)  # Don't wait forever
```

### 2. Graceful Degradation
Handle Arduino disconnection gracefully:
```python
try:
    surface.lcd_write(0, 0, "Status OK")
except:
    # Fall back to voice or logging
    speak("Status OK")
```

### 3. Visual Feedback
Always provide immediate feedback for physical input:
```python
# User presses button
if event["button"] == "confirm":
    # Immediate acknowledgment
    surface.beep(50, 1500)
    surface.set_led(0, 0, 255, 0)
    # Then process
    handle_confirmation()
```

### 4. State Persistence
Remember that Arduino has no persistent storage:
```python
# Save state externally
with open("arduino_state.json", "w") as f:
    json.dump({"last_threshold": threshold}, f)

# Restore on reconnect
if os.path.exists("arduino_state.json"):
    with open("arduino_state.json") as f:
        state = json.load(f)
        surface.set_servo(int(state["last_threshold"] * 180))
```

### 5. Error Recovery
Handle serial communication errors:
```python
def safe_lcd_write(row, col, text):
    """LCD write with automatic retry"""
    for attempt in range(3):
        try:
            if surface.lcd_write(row, col, text):
                return True
        except:
            time.sleep(0.1)
    return False
```

---

## Troubleshooting Integration Issues

### Issue: MCP Monitor Shows All Red
**Diagnosis**: MCP servers not running or not detected
**Solution**:
```bash
# Check MCP servers
ps aux | grep mcp

# Check Temporal workers
ps aux | grep temporal

# Restart MCP servers
# Restart Temporal workers
```

### Issue: Buttons Not Responding
**Diagnosis**: Event listener not started
**Solution**:
```python
# Must start event listener before waiting
surface.start_event_listener()
event = surface.wait_event(timeout=10)
```

### Issue: Servo Jittering
**Diagnosis**: Insufficient power
**Solution**:
- Use external 5V power supply
- Add 100µF capacitor across servo power
- Reduce update frequency

### Issue: LCD Displays Garbage
**Diagnosis**: I2C address mismatch
**Solution**:
- Run I2C scanner to find address
- Update firmware: `LiquidCrystal_I2C lcd(0x27, 16, 2);`
- Try 0x3F if 0x27 doesn't work

---

## Performance Characteristics

| Operation | Latency | Notes |
|-----------|---------|-------|
| LCD Update | ~20ms | Relatively slow, batch updates |
| LED Update | <5ms | Fast, can update frequently |
| Servo Move | 100-500ms | Physical movement takes time |
| Buzzer Beep | Variable | Blocking during beep |
| Button Read | <1ms | Very fast when polled |
| Sensor Read | ~1ms | Fast analog read |
| Serial Command | 10-50ms | Depends on baud rate |

**Optimization Tips**:
- Batch LCD updates (clear once, write both lines)
- Minimize servo movements (only on significant changes)
- Use non-blocking patterns where possible
- Cache status reads (don't query every millisecond)

---

## Future Enhancement Ideas

1. **OLED Display**: Richer graphics and faster updates
2. **NeoPixel Strip**: More expressive LED animations
3. **Rotary Encoder**: Precise value selection with button
4. **SD Card**: Local data logging
5. **WiFi Module**: Network independence
6. **Speaker**: Text-to-speech audio feedback
7. **E-Ink Display**: Low-power persistent display
8. **Matrix Keyboard**: More input options

---

## Resources

- **Setup Guide**: `ARDUINO_SURFACE_GUIDE.md`
- **Quick Start**: `README.md`
- **Code Examples**: `examples/*.py`
- **Hardware Test**: `test_hardware.py`
- **MCP Integration**: `mcp-server/arduino_surface_mcp.py`

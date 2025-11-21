# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The Arduino Surface is a **physical control interface for agentic AI systems**, providing tangible I/O primitives that bridge the digital and physical worlds. It transforms abstract AI processing into physical reality through LEDs, servo motors, LCD displays, buttons, and sensors.

**Core Purpose**: Enable AI agents to interact with the physical world through a standardized hardware interface, creating ambient system monitoring, human-in-the-loop workflows, and environmental context for agent decision-making.

## Architecture

### Three-Layer Stack

```
┌─────────────────────────────────────────────┐
│ Physical World (sensors, buttons, LEDs)    │
└────────────────┬────────────────────────────┘
                 │ Serial (115200 baud)
┌────────────────▼────────────────────────────┐
│ Arduino Firmware (agentic_surface.ino)     │
│ - JSON protocol                             │
│ - Command parsing                           │
│ - Event generation                          │
└────────────────┬────────────────────────────┘
                 │ Serial
┌────────────────▼────────────────────────────┐
│ Python Bridge (surface_bridge.py)          │
│ - pyserial communication                    │
│ - Event listener                            │
│ - Command wrappers                          │
└────────────────┬────────────────────────────┘
                 │ JSON-RPC
┌────────────────▼────────────────────────────┐
│ MCP Server (arduino_surface_mcp.py)        │
│ - Claude Desktop integration                │
│ - Tool exposure                             │
└─────────────────────────────────────────────┘
```

### Hardware Components (Arduino UNO R3)

**Actuators (Output)**:
- 1x RGB LED (Tier0 status indicator) - pins 2, 3, 4
- 16x2 LCD Display (Parallel mode) - pins 7, 8, 9, 10, 11, 12
- Servo Motor (0-180° position) - pin 5
- Piezo Buzzer (audio feedback) - pin 6

**Sensors (Input)**:
- 2x Pushbuttons (Confirm on pin 13, Cancel on A0)
- Potentiometer (A1) - real-time parameter adjustment
- TMP36 Temperature Sensor (A2)
- Photoresistor (A3) - ambient light detection
- Tilt Switch (A6) - emergency stop trigger

**Note**: Currently only 1 RGB LED (Tier0) is implemented due to pin constraints. Tier1 and Tier2 LEDs can be added with I2C expander or by using analog pins as digital outputs.

### Communication Protocol

**Commands (Host → Arduino)**:
```
LCD row col text           → Display text
LED tier r g b             → Set LED color (tier 0-2)
SERVO position             → Set servo (0-180°)
BEEP duration_ms freq_hz   → Play tone
ALERT type                 → Pattern (success/warning/error/info)
CLEAR                      → Clear LCD
STATUS                     → Get full status
PING                       → Connection test
```

**Events (Arduino → Host)**:
```json
{"cmd": "lcd", "status": "ok"}
{"event": "button", "button": "confirm", "state": "pressed"}
{"event": "sensors", "pot": 512, "temp_c": 23.5, "light": 678}
{"event": "tilt", "triggered": true}
```

## Development Workflows

### Testing Hardware

**Complete Hardware Test**:
```bash
python3 test_hardware.py /dev/tty.usbmodem14101
```

Tests all components systematically: serial connection, LCD, LEDs, servo, buzzer, buttons, sensors, tilt switch.

**Manual Command Testing**:
```bash
cd bridge
python3 surface_bridge.py --port /dev/tty.usbmodem14101 lcd 0 0 "Test"
python3 surface_bridge.py --port /dev/tty.usbmodem14101 led 0 0 255 0
python3 surface_bridge.py --port /dev/tty.usbmodem14101 servo 90
python3 surface_bridge.py --port /dev/tty.usbmodem14101 status
```

**Interactive Mode**:
```bash
python3 bridge/surface_bridge.py --port /dev/tty.usbmodem14101
> lcd 0 0 "Hello"
> led 0 0 255 0
> servo 45
> quit
```

**Event Listening**:
```bash
python3 bridge/surface_bridge.py --port /dev/tty.usbmodem14101 listen
# Press buttons, adjust sensors - events printed as JSON
```

### Firmware Development

**Location**: `firmware/agentic_surface/agentic_surface.ino` ✓ **IMPLEMENTED**

**Dependencies**:
- LiquidCrystal library (built-in) - for parallel LCD
- Servo library (built-in)

**Upload Process**:
```
1. Open firmware/agentic_surface.ino in Arduino IDE
2. Tools → Board → Arduino UNO
3. Tools → Port → /dev/tty.usbmodem[xxxx]
4. Upload (→ button)
5. Verify startup: LEDs cycle, servo sweeps, buzzer beeps, LCD shows "Ready"
```

**Serial Monitor Verification**:
```
Baud: 115200
Expected: {"status":"ready","device":"arduino_uno_r3"}
```

### Python Bridge Development

**Location**: `bridge/surface_bridge.py` ✓ **IMPLEMENTED**

**Key Class**: `ArduinoSurface`
- `connect()` - Establish serial connection
- `lcd_write(row, col, text)` - Display text
- `set_led(tier, r, g, b)` - Control LED
- `set_servo(position)` - Move servo
- `beep(duration_ms, freq_hz)` - Play tone
- `alert(type)` - Pattern alert
- `get_status()` - Read all sensors
- `wait_event(timeout)` - Wait for button/tilt
- `start_event_listener()` - Background event monitoring

**Dependencies**:
```bash
pip3 install pyserial>=3.5
```

### MCP Server Development

**Location**: `mcp-server/arduino_surface_mcp.py` ✓ **IMPLEMENTED**

**Exposed Tools**:
- `surface.display` - Write text to LCD
- `surface.display.clear` - Clear LCD
- `surface.led.set` - Set tier LED color
- `surface.servo.set` - Set servo position
- `surface.beep` - Play beep sound
- `surface.alert` - Play alert pattern
- `surface.status` - Get full status
- `surface.sensors` - Get sensor readings
- `surface.wait_button` - Wait for button press

**Integration**: Add to `~/.claude.json`:
```json
{
  "mcpServers": {
    "arduino-surface": {
      "command": "python3",
      "args": [
        "/Volumes/SSDRAID0/agentic-system/arduino-surface/mcp-server/arduino_surface_mcp.py",
        "/dev/tty.usbmodem8344401"
      ],
      "env": {
        "PYTHONPATH": "/Volumes/SSDRAID0/agentic-system/arduino-surface/bridge"
      },
      "disabled": false
    }
  }
}
```

**Status**: ✓ **CONFIGURED** - MCP server is active and integrated with Claude Desktop. Restart Claude Desktop to use the tools.

## Common Use Cases

### 1. MCP Infrastructure Monitoring

**Example**: `examples/mcp_monitor.py` (NOT PRESENT - needs to be created)

Real-time visualization of MCP server health:
- Tier0 LED → enhanced-memory + voice-mode status
- Tier1 LED → agent-runtime-mcp status
- Tier2 LED → sequential-thinking status
- Servo → Workflow activity level
- LCD → Active workflow counts

Color codes: Green (healthy), Orange (partial), Red (down)

### 2. Human-in-the-Loop Workflows

**Example**: `examples/human_in_loop_example.py`

Physical approval gates for critical agent decisions:
- Destructive operations (delete files) → button confirmation
- Expensive API calls (>$100) → cost display + confirmation
- Parameter tuning → potentiometer adjustment + visual servo feedback
- Emergency stop → tilt switch interrupt

### 3. ARC-2 Puzzle Verification

**Example**: `examples/arc2_puzzle_interface.py`

Physical interface for verifying AI-generated puzzle solutions:
- Agent generates solution → display on terminal
- Human reviews → press Confirm (correct) or Cancel (incorrect)
- Quality rating → potentiometer (0-100%)
- Session statistics → accuracy tracking, time logging

### 4. Environmental Context

Use physical sensors to inform agent decisions:
```python
status = surface.get_status()

if status["temp_c"] > 30:
    # Room hot - throttle CPU operations
    agent.set_processing_mode("low_power")

if status["light"] < 100:
    # Dark/nighttime - defer non-urgent tasks
    agent.schedule_task("backup", "08:00")
```

## Code Patterns

### Pattern 1: Request Confirmation
```python
agent.surface.lcd_write(0, 0, "Delete logs?")
agent.surface.lcd_write(1, 0, "Confirm=Yes")
agent.surface.set_led(0, 255, 255, 0)  # Yellow warning
agent.surface.beep(100, 1000)

event = agent.surface.wait_event(timeout=30)

if event and event["button"] == "confirm":
    proceed_with_deletion()
else:
    cancel_operation()
```

### Pattern 2: Real-Time Parameter Adjustment
```python
while adjusting:
    status = surface.get_status()
    value = min_val + (status["pot"] / 1023.0) * (max_val - min_val)

    surface.lcd_write(1, 0, f"Val: {value:.2f}")
    surface.set_servo(int((status["pot"] / 1023.0) * 180))

    event = surface.wait_event(timeout=0.1)
    if event and event["button"] == "confirm":
        break
```

### Pattern 3: Progressive Indication
Use multiple indicators for different granularities:
- LED color → Coarse state (red/yellow/green)
- Servo position → Continuous value (0-180°)
- LCD text → Precise details

### Pattern 4: Attention Hierarchy
Different urgency levels:
- **Info**: Blue LED + single beep
- **Success**: Green LED + ascending beeps
- **Warning**: Yellow LED + mid beep
- **Error**: Red LED + loud descending beeps
- **Critical**: All red LEDs + rapid beeping

## File Structure

```
arduino-surface/
├── firmware/
│   └── agentic_surface/
│       └── agentic_surface.ino   # Arduino UNO R3 firmware ✓
├── bridge/
│   └── surface_bridge.py         # Python serial bridge ✓
├── mcp-server/
│   └── arduino_surface_mcp.py    # MCP server ✓
├── examples/
│   ├── mcp_monitor.py            # MCP status monitor (TODO)
│   ├── human_in_loop_example.py  # Approval workflows ✓
│   └── arc2_puzzle_interface.py  # ARC-2 verification ✓
├── test_hardware.py              # Hardware test suite ✓
├── requirements.txt              # Python dependencies ✓
├── README.md                     # Quick start guide ✓
├── ARDUINO_SURFACE_GUIDE.md      # Complete setup ✓
├── INTEGRATION_EXAMPLES.md       # Usage patterns ✓
├── QUICKSTART_CHECKLIST.md       # Setup checklist ✓
└── CLAUDE.md                     # AI assistant guidance ✓
```

**Implementation Status**:
- ✓ Core system fully implemented and tested
- ✓ Firmware uploaded and operational
- ✓ Python bridge working with proper timing
- ✓ MCP server integrated with Claude Desktop
- ✓ LCD displaying text: "Hello Marc!" / "From Claude Code"
- ✓ LED control verified (RGB 0,255,0 = green)
- ✓ Servo movement tested (90° position)
- ✓ Alert system working (success pattern with beeps)

## Troubleshooting

### Arduino Not Detected
```bash
# Find port
ls /dev/tty.usbmodem*  # macOS
ls /dev/ttyACM*        # Linux

# Permissions (Linux)
sudo usermod -a -G dialout $USER
```

### LCD Shows Garbage or Blinking Cursor
- **Blinking cursor only**: Firmware not uploaded or wrong firmware
- **Garbage characters**: Check contrast pot (V0 pin) - adjust 10K potentiometer
- **Parallel vs I2C**: This project uses parallel LCD (6 data pins), NOT I2C
- **Wiring check**: Verify pins 7, 8, 9, 10, 11, 12 match firmware definitions

### Serial Timeout
- Verify baud: 115200
- Check USB cable (must support data)
- Try different USB port

### LEDs Not Lighting
- Check LED polarity (long leg = anode)
- Verify 220Ω resistors in series
- Test with simple blink sketch

## Performance Notes

- **Serial Latency**: 10-50ms per command (depends on baud rate)
- **Sensor Update Rate**: 100ms interval (firmware configurable)
- **Button Debounce**: 50ms (prevents false triggers)
- **LCD Update**: ~20ms (batch updates for efficiency)
- **Servo Movement**: 100-500ms for large position changes

## Critical Implementation Notes

1. **✓ Core System Complete**: All essential files are implemented and tested:
   - ✓ `firmware/agentic_surface/agentic_surface.ino` - Arduino firmware (parallel LCD)
   - ✓ `bridge/surface_bridge.py` - Python serial bridge (3s reset wait)
   - ✓ `mcp-server/arduino_surface_mcp.py` - MCP server (9 tools)
   - TODO: `examples/mcp_monitor.py` - MCP monitoring script (future enhancement)

2. **Serial Port**: Current port is `/dev/tty.usbmodem8344401` (changes when replugged - use `ls /dev/tty.usbmodem*`)

3. **LCD Configuration**: Uses **parallel mode** (6 data pins), NOT I2C. Hardware has 16 pins (VSS, VDD, VO, RS, R/W, E, DB0-DB7, LED+, LED-)

4. **Arduino Reset Timing**: Wait 3 seconds after opening serial connection for Arduino reset and initialization

5. **Non-Blocking Operations**: Always use timeouts to prevent agent hanging:
   ```python
   event = surface.wait_event(timeout=10)  # Don't wait forever
   ```

6. **Graceful Degradation**: Handle Arduino disconnection gracefully

7. **State Persistence**: Arduino has no persistent storage - save state externally

8. **Pin Constraints**: Only 1 RGB LED implemented (Tier0) due to limited pins. Tier1/Tier2 require I2C expander.

## Integration with MCP Tier System

The Arduino Surface serves as **Tier0** in the MCP architecture:

- **Tier0 (Foundation)**: enhanced-memory, voice-mode, **arduino-surface** ← Physical I/O
- **Tier1 (Cognitive)**: agent-runtime-mcp → Task orchestration
- **Tier2 (Reasoning)**: sequential-thinking → Deep reasoning

Physical world → Arduino → Serial → Python Bridge → MCP Server → Claude Agent → Physical actions

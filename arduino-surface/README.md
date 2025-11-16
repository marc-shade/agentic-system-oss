# Arduino Physical Control Surface for Agentic AI

Physical world I/O primitives for Claude Code agentic AI infrastructure.

## Overview

The Arduino Surface transforms abstract AI processing into tangible reality:
- **LEDs glow** when MCP servers are healthy
- **Servo moves** when workflows execute
- **LCD displays** current agent tasks
- **Buttons provide** human approval gates
- **Sensors inform** agent decisions with environmental context

This creates a **physical-digital bridge** where:
- Digital decisions manifest physically
- Physical world informs agents
- Human-agent interaction becomes tactile

## Quick Start

### 1. Hardware Setup
Wire your Arduino UNO R3 according to the pin assignments in `ARDUINO_SURFACE_GUIDE.md`:
- 3x RGB LEDs (pins 2-10)
- 16x2 LCD with I2C (A4/A5)
- Servo motor (pin 11)
- Buzzer (pin 12)
- 2 buttons (pin 13, A0)
- Sensors: pot (A1), temp (A2), light (A3), tilt (A6)

### 2. Flash Firmware
```bash
# Open in Arduino IDE
open firmware/agentic_surface.ino

# Upload to Arduino UNO R3
# Board: Arduino UNO
# Port: /dev/tty.usbmodem[xxxx]
```

### 3. Install Python Dependencies
```bash
pip3 install -r requirements.txt
```

### 4. Test Connection
```bash
cd bridge
python3 surface_bridge.py --port /dev/tty.usbmodem14101
```

### 5. Run MCP Monitor
```bash
cd examples
python3 mcp_monitor.py /dev/tty.usbmodem14101 5
```

Watch your MCP infrastructure status visualized in real-time on physical hardware!

## Directory Structure

```
arduino-surface/
├── firmware/
│   └── agentic_surface.ino       # Arduino UNO R3 firmware
├── bridge/
│   └── surface_bridge.py         # Python serial communication
├── mcp-server/
│   └── arduino_surface_mcp.py    # Tier0 MCP server
├── examples/
│   ├── mcp_monitor.py            # MCP status visualization
│   ├── human_in_loop_example.py  # Human approval workflows
│   └── arc2_puzzle_interface.py  # ARC-2 puzzle verification
├── ARDUINO_SURFACE_GUIDE.md      # Complete setup guide
├── README.md                      # This file
└── requirements.txt               # Python dependencies
```

## Use Cases

### 1. MCP Status Dashboard
Real-time visualization of MCP server health:
```bash
python3 examples/mcp_monitor.py /dev/tty.usbmodem14101
```
- **Tier0 LED**: enhanced-memory + voice-mode
- **Tier1 LED**: agent-runtime-mcp
- **Tier2 LED**: sequential-thinking
- **Servo**: Workflow activity level
- **LCD**: Active workflows and workers

### 2. Human-in-the-Loop Workflows
Agent requests human confirmation for critical decisions:
```bash
python3 examples/human_in_loop_example.py /dev/tty.usbmodem14101 all
```
- Destructive operations (delete files)
- High-cost decisions (expensive API calls)
- Parameter tuning (potentiometer adjustment)
- Emergency stop (tilt switch)

### 3. ARC-2 Puzzle Verification
Physical interface for verifying ARC-2 puzzle solutions:
```bash
python3 examples/arc2_puzzle_interface.py /dev/tty.usbmodem14101
```
- Agent generates solution
- Human reviews visually
- Physical button verification (Confirm/Cancel)
- Quality rating via potentiometer

### 4. MCP Server Integration
Expose Arduino as Tier0 MCP server for Claude Desktop:

Add to `~/.claude.json`:
```json
{
  "mcpServers": {
    "arduino-surface": {
      "command": "python3",
      "args": [
        "/Volumes/SSDRAID0/agentic-system/arduino-surface/mcp-server/arduino_surface_mcp.py",
        "/dev/tty.usbmodem14101"
      ],
      "disabled": false
    }
  }
}
```

Then in Claude Desktop:
```
Display "System Ready" on the Arduino LCD
```

Claude will use: `surface.display(row=0, col=0, text="System Ready")`

## MCP Tools

When configured as MCP server, these tools are available:

| Tool | Description |
|------|-------------|
| `surface.display` | Write text to LCD (row, col, text) |
| `surface.display.clear` | Clear LCD display |
| `surface.led.set` | Set tier LED color (tier, r, g, b) |
| `surface.servo.set` | Set servo position (0-180°) |
| `surface.beep` | Play beep sound (duration_ms, frequency_hz) |
| `surface.alert` | Play alert pattern (success/warning/error/info) |
| `surface.status` | Get full status (sensors, buttons, servo) |
| `surface.sensors` | Get sensor readings (pot, temp, light) |
| `surface.wait_button` | Wait for button press (timeout_seconds) |

## Architecture Integration

### Tier0 Foundation Layer
The Arduino Surface serves as **Tier0** in the MCP architecture:

```
┌─────────────────────────────────────────────────┐
│ Tier0 (Foundation)                              │
│ • enhanced-memory    → Episodic/semantic memory │
│ • voice-mode         → Speech I/O               │
│ • arduino-surface    → Physical world I/O       │ ← NEW
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│ Tier1 (Cognitive)                               │
│ • agent-runtime-mcp  → Task orchestration       │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│ Tier2 (Reasoning)                               │
│ • sequential-thinking → Deep reasoning          │
└─────────────────────────────────────────────────┘
```

### Event Flow
```
┌──────────────┐
│ Physical     │
│ World        │
│ (sensors,    │
│  buttons)    │
└──────┬───────┘
       │
       ↓ Serial
┌──────────────┐
│ Arduino      │
│ Firmware     │
│ (JSON        │
│  protocol)   │
└──────┬───────┘
       │
       ↓ Serial
┌──────────────┐
│ Python       │
│ Bridge       │
│ (pyserial)   │
└──────┬───────┘
       │
       ↓ JSON-RPC
┌──────────────┐
│ MCP Server   │
│ (stdio)      │
└──────┬───────┘
       │
       ↓ MCP Protocol
┌──────────────┐
│ Claude Code  │
│ Agent        │
└──────┬───────┘
       │
       ↓ Actions
┌──────────────┐
│ Physical     │
│ World        │
│ (LEDs, LCD,  │
│  servo)      │
└──────────────┘
```

## Command Protocol

The Arduino firmware uses a JSON-based serial protocol (115200 baud):

### Commands (Host → Arduino)
```
LCD row col text           → Display text on LCD
LED tier r g b             → Set LED color (tier 0-2)
SERVO position             → Set servo position (0-180)
BEEP duration_ms freq_hz   → Play tone
ALERT type                 → Alert pattern (success/warning/error/info)
CLEAR                      → Clear LCD
STATUS                     → Get full status
PING                       → Connection test
```

### Responses (Arduino → Host)
```json
{"cmd": "lcd", "status": "ok"}
{"cmd": "led", "tier": 0, "status": "ok"}
{"event": "button", "button": "confirm", "state": "pressed"}
{"event": "sensors", "pot": 512, "temp_c": 23.5, "light": 678}
{"event": "tilt", "triggered": true}
```

## Hardware Specifications

### Arduino UNO R3
- **Microcontroller**: ATmega328P
- **Operating Voltage**: 5V
- **Digital I/O Pins**: 14 (6 PWM)
- **Analog Input Pins**: 6
- **Flash Memory**: 32 KB
- **SRAM**: 2 KB
- **Clock Speed**: 16 MHz

### Pin Capabilities
- **PWM Pins**: 3, 5, 6, 9, 10, 11 (for LED brightness, servo control)
- **I2C Pins**: A4 (SDA), A5 (SCL) (for LCD communication)
- **Analog Pins**: A0-A7 (10-bit resolution, 0-1023)
- **Internal Pull-up**: Available on all digital pins

## Troubleshooting

### Arduino Not Detected
```bash
# Check USB connection
ls /dev/tty.usbmodem*

# Check permissions (Linux)
sudo usermod -a -G dialout $USER

# Try different USB port
```

### LCD Not Working
```bash
# Scan I2C address
# Tools → Examples → Wire → i2c_scanner

# Common addresses: 0x27, 0x3F
# Update in firmware if needed
```

### LEDs Not Lighting
- Verify pin assignments match wiring
- Check LED polarity (longer leg = anode)
- Confirm 220Ω resistors in series
- Test with simple blink sketch

### Serial Timeout
- Verify baud rate: 115200
- Check USB cable (must support data)
- Try different serial port
- Check for other programs using port

## Examples Gallery

### Example 1: System Status Monitoring
```python
# Real-time MCP infrastructure visualization
python3 examples/mcp_monitor.py /dev/tty.usbmodem14101
```
**Result**: LEDs show tier health (green/orange/red), servo indicates activity, LCD displays workflow count.

### Example 2: Destructive Operation Approval
```python
# Agent requests confirmation before deletion
python3 examples/human_in_loop_example.py /dev/tty.usbmodem14101 1
```
**Result**: LCD asks "Delete all logs?", human presses Confirm or Cancel button.

### Example 3: Parameter Tuning
```python
# Real-time confidence threshold adjustment
python3 examples/human_in_loop_example.py /dev/tty.usbmodem14101 2
```
**Result**: Turn potentiometer to adjust threshold (0.0-1.0), servo shows position, press Confirm to set.

### Example 4: ARC-2 Puzzle Verification
```python
# Physical verification of AI-generated puzzle solutions
python3 examples/arc2_puzzle_interface.py /dev/tty.usbmodem14101
```
**Result**: Review puzzle solution visually, press Confirm if correct, Cancel if incorrect, then rate quality.

## Development

### Testing Commands Manually
```bash
cd bridge
python3 surface_bridge.py --port /dev/tty.usbmodem14101 lcd 0 0 "Hello"
python3 surface_bridge.py --port /dev/tty.usbmodem14101 led 0 0 255 0
python3 surface_bridge.py --port /dev/tty.usbmodem14101 servo 90
python3 surface_bridge.py --port /dev/tty.usbmodem14101 beep 200 1000
python3 surface_bridge.py --port /dev/tty.usbmodem14101 status
```

### Interactive Mode
```bash
cd bridge
python3 surface_bridge.py --port /dev/tty.usbmodem14101

> lcd 0 0 "Testing"
> led 0 255 0 0
> servo 45
> beep
> status
> quit
```

### Event Listening
```bash
cd bridge
python3 surface_bridge.py --port /dev/tty.usbmodem14101 listen

# Press buttons, adjust sensors, tilt Arduino
# Events printed in real-time as JSON
```

## Advanced Customization

### Add Custom Sensors
1. Wire sensor to available analog pin (A7)
2. Add reading to `readSensors()` in firmware
3. Update MCP server to expose new sensor data
4. Restart and test

### Create Custom Alert Patterns
Edit `handleAlert()` in firmware:
```cpp
else if (args == "critical") {
    // All LEDs red
    setLED(0, 255, 0, 0);
    setLED(1, 255, 0, 0);
    setLED(2, 255, 0, 0);

    // Rapid beeping
    for (int i = 0; i < 5; i++) {
        tone(BUZZER_PIN, 800, 100);
        delay(150);
    }
}
```

### Multi-Arduino Setup
For larger installations:
1. Connect multiple Arduinos to different USB ports
2. Note each serial port
3. Create multiple MCP server instances with unique names
4. Assign different responsibilities (one for status, one for input, etc.)

## Performance Considerations

- **Serial Latency**: ~10-50ms per command (depends on baud rate)
- **Sensor Update Rate**: 100ms interval (adjustable in firmware)
- **Button Debounce**: 50ms (prevents false triggers)
- **LCD Update**: Relatively slow (~20ms), batch updates when possible
- **Servo Movement**: Smooth but takes time for large position changes

## Safety Notes

- ⚡ Arduino UNO R3 operates at 5V - safe for human contact
- 🔊 Buzzer can be loud - adjust volume or frequency if needed
- 🔥 LEDs and resistors can get warm with prolonged use
- 🛡️ Tilt switch is **not** a certified emergency stop device
- 💾 No persistent storage - state lost on power cycle

## Future Enhancements

Potential additions for v2:
- [ ] OLED display for richer graphics
- [ ] NeoPixel RGB LED strip for more visual feedback
- [ ] Rotary encoder for precise parameter adjustment
- [ ] SD card for local data logging
- [ ] WiFi/Ethernet shield for network independence
- [ ] Motion sensor for presence detection
- [ ] Relay module for controlling external devices
- [ ] Speaker for text-to-speech audio feedback

## Resources

- **Documentation**: `ARDUINO_SURFACE_GUIDE.md` (complete setup guide)
- **Firmware**: `firmware/agentic_surface.ino` (Arduino code)
- **Bridge**: `bridge/surface_bridge.py` (Python serial interface)
- **MCP Server**: `mcp-server/arduino_surface_mcp.py` (Claude integration)
- **Examples**: `examples/*.py` (usage demonstrations)

## License

Part of the agentic-system framework.

## Credits

Created for physical-digital bridging in Claude Code agentic AI infrastructure.

**Hardware**: Arduino UNO R3 (ATmega328P)
**Integration**: MCP (Model Context Protocol)
**Purpose**: Making abstract AI processing tangible

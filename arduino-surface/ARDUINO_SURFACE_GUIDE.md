# Arduino Physical Control Surface - Complete Setup Guide

## Overview

The Arduino Surface provides physical world I/O for the agentic AI stack, creating a tangible interface where:
- **Digital decisions manifest physically** (LEDs, servo, LCD, buzzer)
- **Physical world informs agents** (sensors, buttons, environment)
- **Human-agent interaction** becomes tactile and ambient

## Hardware Requirements

### Core Components
- **Arduino UNO R3** (ATmega328P, 5V, 14 digital pins, 6 analog pins)
- **16x2 LCD Display (I2C)** - Address 0x27
- **3x RGB LEDs** (common cathode or separate R/G/B LEDs)
- **Servo Motor** (standard hobby servo, 0-180°)
- **Piezo Buzzer** (active or passive)
- **2x Pushbuttons** (normally open)
- **Potentiometer** (10kΩ linear)
- **TMP36 Temperature Sensor**
- **Photoresistor** (with 10kΩ pull-down resistor)
- **Tilt Switch** (ball-type or mercury-free)

### Supporting Components
- Resistors: 220Ω (x9 for LEDs), 10kΩ (x3 for buttons/sensors)
- Breadboard and jumper wires
- USB cable (Type A to Type B)
- 5V power supply (optional, for standalone operation)

## Pin Assignments

```
Digital Pins:
  2  → LED Tier0 Red
  3  → LED Tier0 Green (PWM)
  4  → LED Tier0 Blue
  5  → LED Tier1 Red (PWM)
  6  → LED Tier1 Green (PWM)
  7  → LED Tier1 Blue
  8  → LED Tier2 Red
  9  → LED Tier2 Green (PWM)
  10 → LED Tier2 Blue (PWM)
  11 → Servo Signal (PWM)
  12 → Buzzer
  13 → Button Confirm (built-in LED shared)

Analog Pins:
  A0 → Button Cancel
  A1 → Potentiometer
  A2 → Temperature Sensor (TMP36)
  A3 → Photoresistor
  A4 → I2C SDA (LCD)
  A5 → I2C SCL (LCD)
  A6 → Tilt Switch

Power:
  5V  → Power rail (LCD, sensors)
  GND → Ground rail
```

## Wiring Diagram

### RGB LEDs (x3)
```
Each LED (common cathode):
  Red cathode   → 220Ω → Digital pin (2, 5, 8)
  Green cathode → 220Ω → Digital pin (3, 6, 9)
  Blue cathode  → 220Ω → Digital pin (4, 7, 10)
  Common anode  → 5V
```

### LCD (I2C)
```
LCD Module:
  VCC → 5V
  GND → GND
  SDA → A4
  SCL → A5
```

### Servo
```
Servo:
  Signal (yellow/white) → Pin 11
  VCC (red)            → 5V
  GND (black/brown)    → GND
```

### Buttons
```
Confirm Button:
  One terminal → Pin 13
  Other terminal → GND
  (Internal pullup resistor enabled)

Cancel Button:
  One terminal → A0
  Other terminal → GND
  (Internal pullup resistor enabled)
```

### Sensors
```
Potentiometer:
  Left terminal → GND
  Center wiper  → A1
  Right terminal → 5V

TMP36 Temperature Sensor:
  Pin 1 (left, flat side facing) → 5V
  Pin 2 (center) → A2
  Pin 3 (right) → GND

Photoresistor:
  One terminal → 5V
  Other terminal → A3 and 10kΩ resistor to GND

Tilt Switch:
  One terminal → A6
  Other terminal → GND
  (Internal pullup resistor enabled)
```

### Buzzer
```
Buzzer:
  Positive (+) → Pin 12
  Negative (-) → GND
```

## Firmware Installation

### Step 1: Install Arduino IDE
1. Download from https://www.arduino.cc/en/software
2. Install for your operating system
3. Launch Arduino IDE

### Step 2: Install Required Libraries
Go to **Sketch → Include Library → Manage Libraries** and install:
- **LiquidCrystal I2C** by Frank de Brabander (v1.1.2+)
- **Servo** (built-in, should be available)

### Step 3: Flash Firmware
1. Open `firmware/agentic_surface.ino` in Arduino IDE
2. Connect Arduino UNO R3 via USB
3. Select **Tools → Board → Arduino UNO**
4. Select **Tools → Port → /dev/tty.usbmodem[xxxx]** (Mac) or **COM[x]** (Windows)
5. Click **Upload** (→ button)
6. Wait for "Done uploading" message

### Step 4: Verify Startup
Open **Tools → Serial Monitor** (115200 baud):
- You should see: `{"status":"ready","device":"arduino_uno_r3"}`
- LCD displays: "Ready"
- LEDs cycle through colors
- Servo sweeps 0-180°
- Buzzer plays startup sequence

## Python Bridge Setup

### Step 1: Install Dependencies
```bash
pip3 install pyserial
```

### Step 2: Find Serial Port
```bash
# macOS
ls /dev/tty.usbmodem*

# Linux
ls /dev/ttyACM*

# Windows
# Check Device Manager → Ports (COM & LPT)
```

### Step 3: Test Connection
```bash
cd /Volumes/SSDRAID0/agentic-system/arduino-surface/bridge

# Interactive mode
python3 surface_bridge.py --port /dev/tty.usbmodem14101

# Single command test
python3 surface_bridge.py --port /dev/tty.usbmodem14101 lcd 0 0 "Hello AI"
```

### Step 4: Test Commands
In interactive mode:
```
> lcd 0 0 "Tier0: Ready"
> led 0 0 255 0
> servo 90
> beep 200 1000
> alert success
> status
> listen
```

## MCP Server Integration

### Step 1: Configure MCP Server

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
      "env": {
        "PYTHONPATH": "/Volumes/SSDRAID0/agentic-system/arduino-surface/bridge"
      },
      "disabled": false
    }
  }
}
```

### Step 2: Restart Claude Desktop
Quit and relaunch Claude Desktop to load the MCP server.

### Step 3: Verify MCP Tools
In Claude Desktop, check for these tools:
- `surface.display` - Display text on LCD
- `surface.display.clear` - Clear LCD
- `surface.led.set` - Set tier LED color
- `surface.servo.set` - Set servo position
- `surface.beep` - Play beep sound
- `surface.alert` - Play alert pattern
- `surface.status` - Get full status
- `surface.sensors` - Get sensor readings
- `surface.wait_button` - Wait for button press

## Testing the Integration

### Test 1: Basic Display
Ask Claude: "Display 'System Ready' on the Arduino LCD"

Claude should use: `surface.display(row=0, col=0, text="System Ready")`

### Test 2: Status Indicators
Ask Claude: "Set tier 0 to green, tier 1 to orange, tier 2 to red"

Claude should use:
```
surface.led.set(tier=0, r=0, g=255, b=0)
surface.led.set(tier=1, r=255, g=165, b=0)
surface.led.set(tier=2, r=255, g=0, b=0)
```

### Test 3: Alert System
Ask Claude: "Send an error alert to the Arduino"

Claude should use: `surface.alert(type="error")`

### Test 4: Human Interaction
Ask Claude: "Wait for me to press the confirm button on the Arduino"

Claude should use: `surface.wait_button(timeout_seconds=30)`

## MCP Monitor Setup

The MCP Monitor provides real-time visualization of your MCP server infrastructure status on the Arduino display.

### Step 1: Install Temporal CLI (if needed)
```bash
brew install temporal
```

### Step 2: Run Monitor
```bash
cd /Volumes/SSDRAID0/agentic-system/arduino-surface/examples

python3 mcp_monitor.py /dev/tty.usbmodem14101 5
```

This updates every 5 seconds showing:
- **Tier0 LED**: enhanced-memory + voice-mode status
- **Tier1 LED**: agent-runtime-mcp status
- **Tier2 LED**: sequential-thinking status
- **Servo**: Activity level (workflows + workers)
- **LCD Line 0**: "MCP: X/3 ok"
- **LCD Line 1**: "Flows: X  Wkr: X"

Colors:
- **Green**: All servers in tier running
- **Orange**: Some servers running
- **Red**: All servers stopped

## Use Cases

### 1. Ambient System Monitoring
The Arduino surface provides at-a-glance status:
- Green LEDs = healthy system
- Servo movement = active processing
- LCD shows current task

### 2. Human-in-the-Loop Workflows
Agents can request human confirmation:
```python
# Agent displays question on LCD
surface.display(0, 0, "Delete all logs?")
surface.display(1, 0, "Confirm=Yes")

# Agent waits for physical button press
response = surface.wait_button(timeout_seconds=30)

if response["button"] == "confirm":
    # Proceed with deletion
```

### 3. Environmental Context
Physical sensors inform agent decisions:
```python
# Check room conditions
sensors = surface.sensors()

if sensors["temp_c"] > 30:
    # Reduce CPU-intensive operations
    agent.throttle_processing()

if sensors["light"] < 100:
    # It's nighttime, defer non-urgent tasks
    agent.schedule_for_morning()
```

### 4. Emergency Stop
Tilt switch provides physical interrupt:
```python
# Agent monitors for emergency stop
event = surface.wait_event(timeout=0.1)

if event and event["event"] == "tilt":
    # Stop all workflows immediately
    agent.emergency_stop()
    surface.display(0, 0, "EMERGENCY STOP!")
```

### 5. Parameter Adjustment
Potentiometer provides real-time tuning:
```python
# Agent reads potentiometer for threshold adjustment
status = surface.status()
threshold = status["pot"] / 1023.0  # Normalize to 0.0-1.0

agent.set_confidence_threshold(threshold)
surface.display(0, 0, f"Threshold: {threshold:.2f}")
```

## Troubleshooting

### LCD Not Working
1. Check I2C address: Run I2C scanner sketch
2. Common addresses: 0x27, 0x3F
3. Adjust in firmware: `LiquidCrystal_I2C lcd(0x27, 16, 2);`
4. Check wiring: SDA to A4, SCL to A5
5. Check contrast: Adjust potentiometer on LCD module

### LEDs Not Lighting
1. Verify pin assignments match wiring
2. Check LED polarity (longer leg = anode)
3. Test with simple blink sketch
4. Verify 220Ω resistors in series

### Servo Jittering
1. Use external 5V power supply (Arduino USB may be insufficient)
2. Add 100µF capacitor across servo power pins
3. Check servo position commands (0-180 range)

### Serial Communication Timeout
1. Verify baud rate: 115200 in code and Serial Monitor
2. Check USB cable (data + power, not just power)
3. Try different USB port
4. Check port permissions (Linux): `sudo usermod -a -G dialout $USER`

### Temperature Sensor Incorrect
1. TMP36 formula: `tempC = (voltage - 0.5) * 100.0`
2. Verify 5V reference voltage
3. Check pin orientation (flat side facing you: 5V, Signal, GND)
4. Calibrate by comparing to known thermometer

## Architecture Integration

### Tier Mapping
The Arduino Surface serves as **Tier0** in the MCP architecture:

```
Tier0 (Foundation):
  - enhanced-memory    → Episodic/semantic storage
  - voice-mode         → Speech I/O
  - arduino-surface    → Physical world I/O ← NEW

Tier1 (Cognitive):
  - agent-runtime-mcp  → Task orchestration

Tier2 (Reasoning):
  - sequential-thinking → Deep reasoning
```

### Event Flow
```
Physical World → Arduino Sensors → Serial → Python Bridge → MCP Server → Agent

Agent → MCP Server → Python Bridge → Serial → Arduino Actuators → Physical World
```

### Temporal Workflow Integration
The MCP Monitor uses Temporal CLI to check workflow status:
```python
result = subprocess.run(
    ["temporal", "workflow", "list", "--limit", "10"],
    capture_output=True
)
running_count = result.stdout.count("Running")
```

This count drives the servo position, providing physical feedback on system activity.

## Advanced Customization

### Custom Alert Patterns
Edit `handleAlert()` in firmware to create custom patterns:
```cpp
else if (args == "critical") {
    setLED(0, 255, 0, 0);  // Red
    setLED(1, 255, 0, 0);
    setLED(2, 255, 0, 0);
    // Rapid beeping
    for (int i = 0; i < 5; i++) {
        tone(BUZZER_PIN, 800, 100);
        delay(150);
    }
}
```

### Add New Sensors
1. Wire sensor to available analog pin
2. Add reading code to `readSensors()`:
```cpp
int sensorValue = analogRead(A7);
Serial.print(",\"custom_sensor\":");
Serial.print(sensorValue);
```
3. Update MCP server to expose new sensor data

### Multi-Arduino Setup
For larger installations, chain multiple Arduinos:
1. Assign unique serial ports
2. Create multiple MCP server instances
3. Use naming convention: `arduino-surface-1`, `arduino-surface-2`

## Next Steps

1. **Test Basic Commands**: Verify all hardware components respond correctly
2. **Run MCP Monitor**: See real-time system status visualization
3. **Create Agent Workflows**: Build workflows that use physical I/O
4. **Customize Alerts**: Tailor patterns to your notification preferences
5. **Add Sensors**: Extend with motion, sound, or other environmental sensors

## References

- Firmware: `firmware/agentic_surface.ino`
- Python Bridge: `bridge/surface_bridge.py`
- MCP Server: `mcp-server/arduino_surface_mcp.py`
- Monitor Example: `examples/mcp_monitor.py`
- Human-in-Loop Example: `examples/human_in_loop_example.py`
- ARC-2 Puzzle Example: `examples/arc2_puzzle_interface.py`

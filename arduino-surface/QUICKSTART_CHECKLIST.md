# Arduino Surface Quick Start Checklist

Step-by-step checklist to get your Arduino control surface running.

## Prerequisites

- [ ] Arduino UNO R3 (ATmega328P)
- [ ] USB cable (Type A to Type B)
- [ ] All hardware components (see ARDUINO_SURFACE_GUIDE.md)
- [ ] Breadboard and jumper wires
- [ ] Arduino IDE installed
- [ ] Python 3.7+ installed

---

## Phase 1: Hardware Assembly (30-60 minutes)

### Step 1: Gather Components
- [ ] Arduino UNO R3
- [ ] 16x2 LCD with I2C module
- [ ] 3x RGB LEDs (common cathode or 9 individual LEDs)
- [ ] 9x 220Ω resistors (for LEDs)
- [ ] 1x Servo motor
- [ ] 1x Piezo buzzer
- [ ] 2x Pushbuttons
- [ ] 3x 10kΩ resistors (for pulldowns/pullups)
- [ ] 1x Potentiometer (10kΩ)
- [ ] 1x TMP36 temperature sensor
- [ ] 1x Photoresistor + 10kΩ resistor
- [ ] 1x Tilt switch
- [ ] Breadboard
- [ ] Jumper wires (male-male, male-female)

### Step 2: Wire Components
Follow pin assignments from ARDUINO_SURFACE_GUIDE.md:

**LEDs (Tier 0, 1, 2)**:
- [ ] Tier0 Red → Pin 2 (via 220Ω resistor)
- [ ] Tier0 Green → Pin 3 (via 220Ω resistor)
- [ ] Tier0 Blue → Pin 4 (via 220Ω resistor)
- [ ] Tier1 Red → Pin 5 (via 220Ω resistor)
- [ ] Tier1 Green → Pin 6 (via 220Ω resistor)
- [ ] Tier1 Blue → Pin 7 (via 220Ω resistor)
- [ ] Tier2 Red → Pin 8 (via 220Ω resistor)
- [ ] Tier2 Green → Pin 9 (via 220Ω resistor)
- [ ] Tier2 Blue → Pin 10 (via 220Ω resistor)
- [ ] All LED anodes → 5V

**LCD (I2C)**:
- [ ] LCD VCC → 5V
- [ ] LCD GND → GND
- [ ] LCD SDA → A4
- [ ] LCD SCL → A5

**Servo**:
- [ ] Servo signal (yellow/white) → Pin 11
- [ ] Servo VCC (red) → 5V
- [ ] Servo GND (black/brown) → GND

**Buzzer**:
- [ ] Buzzer positive → Pin 12
- [ ] Buzzer negative → GND

**Buttons**:
- [ ] Confirm button: One terminal → Pin 13, other → GND
- [ ] Cancel button: One terminal → A0, other → GND

**Sensors**:
- [ ] Potentiometer: Left → GND, Center → A1, Right → 5V
- [ ] TMP36: Left (facing flat) → 5V, Center → A2, Right → GND
- [ ] Photoresistor: One → 5V, Other → A3 + 10kΩ to GND
- [ ] Tilt switch: One → A6, Other → GND

**Power Rails**:
- [ ] Power rail connected to Arduino 5V
- [ ] Ground rail connected to Arduino GND

### Step 3: Verify Connections
- [ ] No short circuits (5V not touching GND directly)
- [ ] All LEDs have resistors in series
- [ ] All components firmly connected
- [ ] USB cable ready to connect

---

## Phase 2: Firmware Installation (10-15 minutes)

### Step 4: Install Arduino IDE
- [ ] Downloaded from https://www.arduino.cc/en/software
- [ ] Installed and launched

### Step 5: Install Libraries
In Arduino IDE: **Sketch → Include Library → Manage Libraries**
- [ ] Installed: **LiquidCrystal I2C** by Frank de Brabander
- [ ] Verified: **Servo** library (built-in)

### Step 6: Open and Upload Firmware
- [ ] Opened `firmware/agentic_surface.ino` in Arduino IDE
- [ ] Selected **Tools → Board → Arduino UNO**
- [ ] Connected Arduino via USB
- [ ] Selected **Tools → Port → /dev/tty.usbmodem[xxxx]** (or COM[x] on Windows)
- [ ] Clicked **Upload** (→ button)
- [ ] Waited for "Done uploading"
- [ ] Observed startup sequence:
  - [ ] LEDs cycle through colors
  - [ ] Servo sweeps 0-180°
  - [ ] Buzzer plays 3-tone sequence
  - [ ] LCD displays "Ready"

### Step 7: Verify Serial Communication
- [ ] Opened **Tools → Serial Monitor**
- [ ] Set baud rate to **115200**
- [ ] Saw: `{"status":"ready","device":"arduino_uno_r3"}`

**If LCD shows garbage**: I2C address may be wrong
- [ ] Run I2C scanner sketch to find address
- [ ] Update firmware line 41: `LiquidCrystal_I2C lcd(0x27, 16, 2);`
- [ ] Try 0x3F if 0x27 doesn't work
- [ ] Re-upload firmware

---

## Phase 3: Python Setup (5-10 minutes)

### Step 8: Install Python Dependencies
```bash
cd /Volumes/SSDRAID0/agentic-system/arduino-surface
pip3 install -r requirements.txt
```
- [ ] Ran command
- [ ] Verified: `pyserial>=3.5` installed

### Step 9: Find Serial Port
**macOS**:
```bash
ls /dev/tty.usbmodem*
```
- [ ] Found port: ______________________

**Linux**:
```bash
ls /dev/ttyACM*
```
- [ ] Found port: ______________________

**Windows**:
- [ ] Checked Device Manager → Ports (COM & LPT)
- [ ] Found port: ______________________

### Step 10: Test Python Bridge
```bash
cd bridge
python3 surface_bridge.py --port [YOUR_PORT] lcd 0 0 "Hello"
```
- [ ] Ran command with your port
- [ ] LCD displayed "Hello"

**Troubleshooting**:
- If "Permission denied" (Linux): `sudo usermod -a -G dialout $USER` then logout/login
- If timeout: Check baud rate, try different USB port
- If garbage on LCD: Verify I2C address

---

## Phase 4: Hardware Verification (10 minutes)

### Step 11: Run Complete Hardware Test
```bash
cd /Volumes/SSDRAID0/agentic-system/arduino-surface
python3 test_hardware.py [YOUR_PORT]
```

Expected results:
- [ ] **Test 1**: Serial connection ✅
- [ ] **Test 2**: LCD display ✅ (text appears on both lines)
- [ ] **Test 3**: RGB LEDs ✅ (all 3 tiers cycle through colors)
- [ ] **Test 4**: Servo motor ✅ (moves smoothly 0-180°)
- [ ] **Test 5**: Buzzer ✅ (hear tones and alert patterns)
- [ ] **Test 6**: Buttons ✅ (press confirm and cancel when prompted)
- [ ] **Test 7**: Sensors ✅ (readings displayed)
- [ ] **Test 8**: Tilt switch ✅ (tilt Arduino to trigger)

**If any test fails**: See ARDUINO_SURFACE_GUIDE.md troubleshooting section

---

## Phase 5: MCP Integration (5 minutes)

### Step 12: Configure MCP Server
Edit `~/.claude.json` and add:
```json
{
  "mcpServers": {
    "arduino-surface": {
      "command": "python3",
      "args": [
        "/Volumes/SSDRAID0/agentic-system/arduino-surface/mcp-server/arduino_surface_mcp.py",
        "[YOUR_PORT]"
      ],
      "env": {
        "PYTHONPATH": "/Volumes/SSDRAID0/agentic-system/arduino-surface/bridge"
      },
      "disabled": false
    }
  }
}
```
- [ ] Added configuration with your serial port
- [ ] Saved file

### Step 13: Restart Claude Desktop
- [ ] Quit Claude Desktop completely
- [ ] Relaunch Claude Desktop
- [ ] Wait for MCP servers to load

### Step 14: Verify MCP Tools
In Claude Desktop, ask: "What tools do you have for the arduino-surface?"

Expected tools:
- [ ] `surface.display`
- [ ] `surface.display.clear`
- [ ] `surface.led.set`
- [ ] `surface.servo.set`
- [ ] `surface.beep`
- [ ] `surface.alert`
- [ ] `surface.status`
- [ ] `surface.sensors`
- [ ] `surface.wait_button`

### Step 15: Test MCP Integration
In Claude Desktop, ask: "Display 'System Ready' on the Arduino LCD"

- [ ] Claude used `surface.display` tool
- [ ] LCD shows "System Ready"

**If tools not available**:
- Check `~/.claude.json` syntax (must be valid JSON)
- Check serial port path is correct
- Check Python path includes bridge directory
- Restart Claude Desktop again

---

## Phase 6: Run Examples (5-10 minutes each)

### Example 1: MCP Status Monitor
```bash
cd examples
python3 mcp_monitor.py [YOUR_PORT] 5
```
- [ ] Script running
- [ ] LEDs show tier status (should be green if MCP servers running)
- [ ] Servo moves with workflow activity
- [ ] LCD shows "MCP: X/3 ok" and workflow counts
- [ ] Press Ctrl+C to stop

**What this shows**: Real-time visualization of your MCP infrastructure health

### Example 2: Human-in-the-Loop
```bash
cd examples
python3 human_in_loop_example.py [YOUR_PORT] all
```
- [ ] Example 1: Confirm/cancel destructive operation
- [ ] Example 2: Adjust parameter with potentiometer
- [ ] Example 3: Approve expensive API call
- [ ] Example 4: Test emergency stop with tilt switch

**What this shows**: Physical approval gates for critical agent decisions

### Example 3: ARC-2 Puzzle Verification
```bash
cd examples
python3 arc2_puzzle_interface.py [YOUR_PORT]
```
- [ ] Review puzzle solutions visually
- [ ] Press CONFIRM for correct, CANCEL for incorrect
- [ ] Rate quality with potentiometer
- [ ] View session statistics

**What this shows**: Physical verification interface for AI-generated solutions

---

## Phase 7: Create Your First Integration (10 minutes)

### Step 16: Test from Claude Desktop

**Simple Test**:
Ask Claude: "Use the Arduino surface to show that you're thinking"

Claude should:
- [ ] Set LED to blue (thinking color)
- [ ] Display "Thinking..." on LCD

**Interactive Test**:
Ask Claude: "Ask me a yes/no question using the Arduino"

Claude should:
- [ ] Display question on LCD
- [ ] Wait for button press
- [ ] Respond based on your physical input

**Sensor Test**:
Ask Claude: "What's the temperature reading from the Arduino?"

Claude should:
- [ ] Read sensor data
- [ ] Report temperature in Celsius

### Step 17: Create Custom Workflow

Edit a new file: `my_workflow.py`
```python
from surface_bridge import ArduinoSurface
import time

surface = ArduinoSurface("[YOUR_PORT]")
surface.connect()

# Your custom code here
surface.lcd_write(0, 0, "My Workflow")
surface.set_led(0, 0, 255, 0)  # Green
surface.beep(200, 1000)

time.sleep(3)
surface.disconnect()
```
- [ ] Created file
- [ ] Ran: `python3 my_workflow.py`
- [ ] Observed expected behavior

---

## Completion Checklist

### Hardware
- [ ] All components wired correctly
- [ ] Firmware uploaded and running
- [ ] All hardware tests passing
- [ ] Serial communication working

### Software
- [ ] Python dependencies installed
- [ ] Bridge tested and working
- [ ] MCP server configured
- [ ] Claude Desktop recognizes tools

### Integration
- [ ] Can control Arduino from Claude Desktop
- [ ] Can read sensors from Claude Desktop
- [ ] Can wait for button presses
- [ ] Examples run successfully

### Understanding
- [ ] Know how to update LCD
- [ ] Know how to control LEDs
- [ ] Know how to read sensors
- [ ] Know how to wait for input
- [ ] Understand MCP tool usage

---

## Next Steps

Now that your Arduino Surface is operational:

1. **Monitor MCP Infrastructure**
   - Run `mcp_monitor.py` to watch system health
   - Leave it running for ambient awareness

2. **Add to Agent Workflows**
   - Have agents display status on LCD
   - Use buttons for approval gates
   - Read sensors for environmental context

3. **Create Custom Alerts**
   - Edit firmware `handleAlert()` for custom patterns
   - Create specific LED colors for different states

4. **Add More Sensors**
   - Wire additional sensors to A7 or other available pins
   - Add reading code to firmware
   - Update MCP server to expose new data

5. **Explore Examples**
   - Study `INTEGRATION_EXAMPLES.md` for patterns
   - Adapt examples to your use cases
   - Share your creations!

---

## Quick Reference Card

### Common Commands

**Test LCD**:
```bash
python3 bridge/surface_bridge.py --port [PORT] lcd 0 0 "Test"
```

**Test LED** (tier 0, red):
```bash
python3 bridge/surface_bridge.py --port [PORT] led 0 255 0 0
```

**Test Servo** (center position):
```bash
python3 bridge/surface_bridge.py --port [PORT] servo 90
```

**Get Status**:
```bash
python3 bridge/surface_bridge.py --port [PORT] status
```

**Interactive Mode**:
```bash
python3 bridge/surface_bridge.py --port [PORT]
> lcd 0 0 "Hello"
> led 0 0 255 0
> servo 45
> quit
```

### Troubleshooting

| Problem | Solution |
|---------|----------|
| Arduino not detected | Check USB cable, try different port |
| LCD shows garbage | Wrong I2C address, run scanner |
| LEDs not lighting | Check polarity, resistors, wiring |
| Servo jittering | Needs external power or capacitor |
| Serial timeout | Check baud rate (115200) |
| Permission denied (Linux) | Add user to dialout group |

### Pin Quick Reference

| Component | Pins |
|-----------|------|
| LCD | A4 (SDA), A5 (SCL) |
| LEDs Tier0 | 2 (R), 3 (G), 4 (B) |
| LEDs Tier1 | 5 (R), 6 (G), 7 (B) |
| LEDs Tier2 | 8 (R), 9 (G), 10 (B) |
| Servo | 11 |
| Buzzer | 12 |
| Button Confirm | 13 |
| Button Cancel | A0 |
| Potentiometer | A1 |
| Temperature | A2 |
| Light | A3 |
| Tilt | A6 |

---

## Support

- **Complete Guide**: `ARDUINO_SURFACE_GUIDE.md`
- **Integration Examples**: `INTEGRATION_EXAMPLES.md`
- **Hardware Test**: `test_hardware.py`
- **Code Examples**: `examples/*.py`

---

**Congratulations!** Your Arduino physical control surface is now operational. You've bridged the digital and physical worlds, giving your AI agents tangible presence. 🎉

**Next**: Run `mcp_monitor.py` and watch your agentic AI infrastructure come to life on physical hardware!

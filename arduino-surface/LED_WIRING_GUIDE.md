# RGB LED Wiring Guide

## Components Needed
- 1x RGB LED (common cathode)
- 3x 220Ω resistors (for current limiting)
- Breadboard and jumper wires

## RGB LED Pin Identification

### Common Cathode RGB LED (4 pins)
```
Looking at the LED flat side up:
┌─────────────┐
│   Flat Side │
├─┬─┬─┬─┬─────┤
│R│-│G│B│     │  (longest pin is cathode/ground)
└─┴─┴─┴─┴─────┘
 1 2 3 4

Pin 1: Red anode
Pin 2: Common cathode (GND) - LONGEST PIN
Pin 3: Green anode
Pin 4: Blue anode
```

**Important**: If your LED has a different pinout, check the datasheet or test with a 3V coin cell battery.

## Wiring Instructions

### Arduino Pin Assignments (from firmware)
- **Pin 2** → Red LED (through 220Ω resistor)
- **Pin 3** → Green LED (through 220Ω resistor)
- **Pin 4** → Blue LED (through 220Ω resistor)
- **GND** → Common cathode (longest pin of LED)

### Step-by-Step Wiring

1. **Insert RGB LED into breadboard**
   - Orient so you can identify which pin is which
   - Longest pin (cathode) should be in a position you can wire to GND

2. **Connect resistors**
   - Red anode → 220Ω resistor → Arduino Pin 2
   - Green anode → 220Ω resistor → Arduino Pin 3
   - Blue anode → 220Ω resistor → Arduino Pin 4

3. **Connect common cathode to GND**
   - LED common cathode (longest pin) → Arduino GND

### Visual Diagram
```
Arduino                RGB LED
                    (Common Cathode)
Pin 2 ----[220Ω]---- Red (Pin 1)
Pin 3 ----[220Ω]---- Green (Pin 3)
Pin 4 ----[220Ω]---- Blue (Pin 4)
GND ----------------- Cathode (Pin 2, longest)

[220Ω] = 220 ohm resistor
```

## Testing the LED

### Test 1: Red Only
```bash
python3 bridge/surface_bridge.py /dev/tty.usbmodem8344401 led 0 255 0 0
```
**Expected**: LED glows red

### Test 2: Green Only
```bash
python3 bridge/surface_bridge.py /dev/tty.usbmodem8344401 led 0 0 255 0
```
**Expected**: LED glows green

### Test 3: Blue Only
```bash
python3 bridge/surface_bridge.py /dev/tty.usbmodem8344401 led 0 0 0 255
```
**Expected**: LED glows blue

### Test 4: White (All Colors)
```bash
python3 bridge/surface_bridge.py /dev/tty.usbmodem8344401 led 0 255 255 255
```
**Expected**: LED glows white

### Test 5: Yellow (Red + Green)
```bash
python3 bridge/surface_bridge.py /dev/tty.usbmodem8344401 led 0 255 255 0
```
**Expected**: LED glows yellow

### Test 6: Off
```bash
python3 bridge/surface_bridge.py /dev/tty.usbmodem8344401 led 0 0 0 0
```
**Expected**: LED turns off

### Test 7: Alert Patterns

**Success Alert** (Green LED + ascending beeps):
```bash
python3 bridge/surface_bridge.py /dev/tty.usbmodem8344401 alert success
```

**Warning Alert** (Yellow LED + mid beeps):
```bash
python3 bridge/surface_bridge.py /dev/tty.usbmodem8344401 alert warning
```

**Error Alert** (Red LED + descending beeps):
```bash
python3 bridge/surface_bridge.py /dev/tty.usbmodem8344401 alert error
```

**Info Alert** (Blue LED + single beep):
```bash
python3 bridge/surface_bridge.py /dev/tty.usbmodem8344401 alert info
```

## Troubleshooting

### LED doesn't light at all
- Check LED polarity (longest pin = cathode = GND)
- Verify resistors are connected (220Ω)
- Check Arduino is powered and running firmware
- Test with multimeter: should see ~2-3V across LED when on

### Wrong colors
- LED might be common anode instead of common cathode
- For common anode: connect longest pin to 5V instead of GND, and invert all values in code
- Check pinout - Red/Green/Blue order varies by manufacturer

### LED very dim
- Resistors might be too high (should be 220Ω, not 2.2kΩ)
- Check connections are secure

### LED too bright
- Resistors might be too low or missing
- Add resistors or use higher values (330Ω or 470Ω)

### Only some colors work
- Check individual connections for each color
- One or more resistors might be loose
- LED might be damaged (test each color with 3V battery)

## Common Cathode vs Common Anode

### Common Cathode (Used in this project)
- Longest pin → GND
- R, G, B pins → HIGH voltage through resistors

### Common Anode (Alternative)
- Longest pin → 5V
- R, G, B pins → GND through resistors
- Requires firmware change: invert all LED values

## Notes
- Current firmware expects **common cathode** RGB LED
- If you have common anode, you'll need to modify the firmware `setLED()` function
- Resistors protect both LED and Arduino pins from overcurrent
- PWM on pins 2, 3, 4 controls brightness (analogWrite 0-255)

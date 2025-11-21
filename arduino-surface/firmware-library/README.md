# Arduino Firmware Library - Hot-Swappable Programs

## Philosophy: Arduino as a Dynamic Endpoint

The Arduino is **not** a static device with sacred firmware. It's a **hot-swappable display endpoint** that can be reprogrammed on-the-fly to show different information based on current needs.

### Key Principles

1. **No Space Constraints** - Since we can flash new firmware anytime, we're not limited by Arduino's 32KB flash memory. We can maintain dozens of specialized programs on disk.

2. **Iterative Display Programs** - Need to show different metrics? Flash a new program optimized for that specific display scenario.

3. **Context-Aware Firmware** - Different firmware for different operational modes:
   - Development mode: Detailed debugging info
   - Production mode: Clean status display
   - Demo mode: Eye-catching visualizations
   - Maintenance mode: Diagnostic details

4. **Agents Control Firmware** - Any agent can request a firmware swap via the Arduino Manager Agent

## Firmware Library Structure

```
firmware-library/
├── README.md (this file)
├── flash_firmware.sh (auto-flash script)
├── v1_basic_status/
│   ├── agentic_surface.ino
│   ├── README.md
│   └── features.txt
├── v2_detailed_metrics/
│   ├── detailed_metrics.ino
│   ├── README.md
│   └── features.txt
├── v3_minimal_display/
│   ├── minimal.ino
│   ├── README.md
│   └── features.txt
├── v4_agent_comms/
│   └── (future)
├── v5_graphical_advanced/
│   └── (future - for upgraded hardware)
└── custom/
    └── (one-off specialized programs)
```

## Firmware Versions

### v1_basic_status (Current Production)
**Purpose**: General-purpose system status display
**Features**:
- 16x2 LCD text display (2 lines x 16 chars)
- 1x RGB LED (Tier0 status - green/yellow/red)
- Servo motor (0-180° for visual indicators)
- Piezo buzzer (audio alerts)
- 2x Buttons (Confirm/Cancel for human-in-loop)
- 4x Sensors (Pot, Temp, Light, Tilt)

**Use When**: Standard operations, balanced feature set
**Memory**: ~15KB (plenty of room for enhancements)

### v2_detailed_metrics (Future)
**Purpose**: Maximum information density on LCD
**Features**:
- Scrolling text (auto-scroll long messages)
- Smaller font emulation (custom characters)
- Multi-page display (button to advance pages)
- Real-time metrics dashboard

**Use When**: Debugging, deep monitoring, troubleshooting
**Memory Target**: ~20KB

### v3_minimal_display (Future)
**Purpose**: Power-efficient, essential-only
**Features**:
- LED only (no LCD updates unless critical)
- Servo disabled (unless needed)
- Low-power sensor polling
- Simple binary status

**Use When**: Battery operation, overnight monitoring, low-priority tasks
**Memory Target**: ~8KB

### v4_agent_comms (Future)
**Purpose**: Inter-agent messaging display
**Features**:
- Message queue display (show last 8 messages)
- Agent identification (color-coded LEDs)
- Priority indicators (urgent messages blink)
- Message history navigation

**Use When**: Multi-agent coordination, swarm operations
**Memory Target**: ~18KB

### v5_graphical_advanced (Future - Hardware Upgrade)
**Purpose**: For when we upgrade to graphical LCD
**Features**:
- 128x64 pixel display
- Charts/graphs
- Icons and symbols
- Smooth animations

**Use When**: Advanced visualizations, presentations
**Hardware**: Requires graphical LCD replacement

## Usage Patterns

### Pattern 1: Status Check → Flash Appropriate Firmware

```python
# Agent needs detailed debugging info
arduino_manager.flash_firmware("v2_detailed_metrics")
time.sleep(5)  # Wait for flash + Arduino reset
arduino_manager.display_system_metrics()
```

### Pattern 2: Mode-Based Auto-Selection

```python
if system.mode == "debug":
    current_firmware = "v2_detailed_metrics"
elif system.mode == "production":
    current_firmware = "v1_basic_status"
elif system.mode == "power_save":
    current_firmware = "v3_minimal_display"

if arduino_manager.get_current_firmware() != current_firmware:
    arduino_manager.flash_firmware(current_firmware)
```

### Pattern 3: Time-Based Rotation

```python
# Different firmware for different times of day
hour = datetime.now().hour

if 9 <= hour <= 17:  # Business hours
    firmware = "v1_basic_status"
elif 18 <= hour <= 22:  # Evening monitoring
    firmware = "v2_detailed_metrics"
else:  # Overnight
    firmware = "v3_minimal_display"
```

### Pattern 4: Event-Driven Swap

```python
# Emergency → detailed view
if system.detect_critical_error():
    arduino_manager.flash_firmware("v2_detailed_metrics")
    arduino_manager.display_error_details()

# Back to normal → standard view
if system.error_resolved():
    arduino_manager.flash_firmware("v1_basic_status")
```

## Flash Process

### Manual Flash
```bash
cd /Volumes/SSDRAID0/agentic-system/arduino-surface/firmware-library
./flash_firmware.sh v2_detailed_metrics /dev/tty.usbmodem8344401
```

### Programmatic Flash (Python)
```python
from arduino_manager import ArduinoManager

manager = ArduinoManager(port="/dev/tty.usbmodem8344401")
manager.flash_firmware("v2_detailed_metrics")
# Automatically waits for flash completion + Arduino reset
```

### From Claude Code (via MCP)
```
Use the arduino_manager.flash_firmware tool:
firmware_version = "v2_detailed_metrics"
```

## Creating New Firmware Variants

1. **Copy Base**: Start from `v1_basic_status` as template
   ```bash
   cp -r v1_basic_status vX_new_variant
   ```

2. **Modify**: Edit `.ino` file for your specific use case
   - Keep same pin assignments (unless hardware changes)
   - Keep same serial protocol (JSON at 115200 baud)
   - Add features or optimize as needed

3. **Document**: Create `README.md` and `features.txt`
   - What problem does this variant solve?
   - When should it be used?
   - What are the trade-offs?

4. **Test**: Flash and verify
   ```bash
   ./flash_firmware.sh vX_new_variant /dev/tty.usbmodem8344401
   python3 ../test_hardware.py /dev/tty.usbmodem8344401
   ```

5. **Add to Manager**: Update arduino_manager.py with new variant

## Memory Budget Guidelines

- **Tight** (<10KB): Minimal features, efficient code
- **Moderate** (10-20KB): Standard feature set
- **Comfortable** (20-28KB): Rich features, debugging
- **Maximum** (28KB): Leaves 4KB for bootloader

Always check compiled size in Arduino IDE:
```
Sketch uses XXXXX bytes (XX%) of program storage space.
```

## Backup Strategy

All firmware variants are maintained in git:
- **Primary**: `/Volumes/SSDRAID0/agentic-system/arduino-surface/firmware-library/`
- **Backup**: Automatically synced to FILES drive

If Arduino brick, any variant can be reflashed to restore operation.

## Performance Characteristics

| Firmware | Flash Time | Startup | LCD Update | Memory | Power |
|----------|-----------|---------|------------|--------|-------|
| v1_basic | 5-7s | 3s | 20ms | 15KB | Normal |
| v2_detailed | 6-8s | 3s | 25ms | 20KB | Normal |
| v3_minimal | 3-5s | 2s | N/A | 8KB | Low |
| v4_comms | 5-7s | 3s | 30ms | 18KB | Normal |

## Best Practices

1. **Document Changes**: Every variant should have clear documentation
2. **Test Before Deploy**: Always test new firmware before using in production
3. **Version Control**: Commit firmware changes to git
4. **Name Descriptively**: Use clear, purpose-driven names
5. **Keep Protocol Consistent**: All variants should use same serial protocol
6. **Plan for Rollback**: Always keep working v1_basic_status available

## Future Enhancements

- **Auto-detect Hardware**: Firmware auto-adapts to connected components
- **OTA Updates**: Flash new firmware without USB connection
- **Firmware Telemetry**: Track which firmware is running, uptime, errors
- **A/B Testing**: Run two firmware variants, compare effectiveness
- **Compression**: Compress rarely-used firmware on disk

---

**Philosophy**: The Arduino is not a constraint - it's a canvas. Flash new "paintings" whenever you need a different view of your system.

#!/bin/bash
#
# Arduino Auto-Detection Script
# Detects if an Arduino is connected and returns the device path
# Works across Linux and macOS nodes
#

# Check for Arduino by common device paths and USB IDs
detect_arduino() {
    # Linux: Check /dev/ttyACM* (most common for Arduino)
    if [ -e /dev/ttyACM0 ]; then
        echo "/dev/ttyACM0"
        return 0
    fi

    # Linux: Check /dev/ttyUSB* (some Arduino clones)
    if [ -e /dev/ttyUSB0 ]; then
        echo "/dev/ttyUSB0"
        return 0
    fi

    # Check by-id for Arduino (more reliable)
    ARDUINO_DEV=$(ls /dev/serial/by-id/*Arduino* 2>/dev/null | head -1)
    if [ -n "$ARDUINO_DEV" ]; then
        readlink -f "$ARDUINO_DEV"
        return 0
    fi

    # macOS: Check /dev/tty.usbmodem* or /dev/cu.usbmodem*
    MACOS_DEV=$(ls /dev/tty.usbmodem* 2>/dev/null | head -1)
    if [ -n "$MACOS_DEV" ]; then
        echo "$MACOS_DEV"
        return 0
    fi

    MACOS_CU=$(ls /dev/cu.usbmodem* 2>/dev/null | head -1)
    if [ -n "$MACOS_CU" ]; then
        echo "$MACOS_CU"
        return 0
    fi

    # No Arduino found
    return 1
}

# Main execution
if ARDUINO_PATH=$(detect_arduino); then
    echo "$ARDUINO_PATH"
    exit 0
else
    echo "No Arduino detected" >&2
    exit 1
fi

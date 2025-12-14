#!/bin/bash
#
# Arduino Broker Startup Wrapper
# Auto-detects Arduino and starts broker with correct device path
#

# Detect Arduino device
ARDUINO_DEV=$(/mnt/agentic-system/scripts/detect-arduino.sh)

if [ $? -ne 0 ]; then
    echo "ERROR: No Arduino detected. Exiting." >&2
    exit 1
fi

echo "Arduino detected at: $ARDUINO_DEV"
cd /mnt/agentic-system/arduino-surface || exit 1

# Start broker with detected device
exec /usr/bin/python3 bridge/arduino_broker.py "$ARDUINO_DEV"

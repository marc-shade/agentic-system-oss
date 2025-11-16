#!/bin/bash
set -e

VARIANT="$1"
PORT="${2:-$(ls /dev/tty.usbmodem* 2>/dev/null | head -1)}"
FIRMWARE_LIB="/mnt/agentic-system/arduino-surface/firmware-library"

if [ -z "$VARIANT" ] || [ ! -d "$FIRMWARE_LIB/$VARIANT" ]; then
    echo "Usage: $0 <variant> [port]"
    echo "Available: $(ls -1 $FIRMWARE_LIB | grep ^v | tr '\n' ' ')"
    exit 1
fi

INO_FILE=$(find "$FIRMWARE_LIB/$VARIANT" -name "*.ino" | head -1)
echo "Flashing $VARIANT to $PORT..."

if command -v arduino-cli &> /dev/null; then
    arduino-cli compile --fqbn arduino:avr:uno "$INO_FILE"
    arduino-cli upload -p "$PORT" --fqbn arduino:avr:uno "$INO_FILE"
    echo "Flash complete. Waiting for reset..."
    sleep 3
else
    echo "Install arduino-cli or use Arduino IDE to flash: $INO_FILE"
fi

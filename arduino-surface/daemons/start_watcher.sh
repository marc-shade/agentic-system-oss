#!/bin/bash
# Wrapper script for Arduino Ready Watcher
# Ensures proper environment for launchd

cd /mnt/agentic-system/arduino-surface/daemons

# Log start
echo "$(date): Starting Arduino Ready Watcher" >> /mnt/agentic-system/arduino-surface/logs/wrapper.log

# Run the watcher
exec /opt/homebrew/Caskroom/miniconda/base/bin/python3 \
    arduino_ready_watcher.py \
    --port /dev/tty.usbmodem8344401 \
    >> /mnt/agentic-system/arduino-surface/logs/watcher-stdout.log \
    2>> /mnt/agentic-system/arduino-surface/logs/watcher-stderr.log

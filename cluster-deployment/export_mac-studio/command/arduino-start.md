# arduino-start

Start the Arduino Surface agentic stack (daemon + web API).

Run the startup script:

```bash
/Volumes/SSDRAID0/agentic-system/arduino-surface/scripts/start_agentic_stack.sh
```

This will:
1. Start the Arduino daemon for hardware communication
2. Start the Ember web API on port 5001
3. Verify both services are running
4. Display PID and log file locations

After starting, use `/arduino-status` to verify everything is running properly.

The Arduino port is auto-detected as `/dev/tty.usbmodem8344401` (or the first available Arduino UNO R3).

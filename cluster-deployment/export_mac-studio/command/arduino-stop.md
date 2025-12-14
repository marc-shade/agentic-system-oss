# arduino-stop

Stop the Arduino Surface agentic stack (daemon + web API).

Run the shutdown script:

```bash
/Volumes/SSDRAID0/agentic-system/arduino-surface/scripts/stop_agentic_stack.sh
```

This will:
1. Stop the Arduino daemon
2. Stop the Ember web API
3. Clean up PID files
4. Force kill if graceful shutdown fails

Use `/arduino-status` after stopping to verify services are fully stopped.

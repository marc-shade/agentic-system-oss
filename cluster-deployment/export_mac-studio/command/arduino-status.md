# arduino-status

Check the status of Arduino Surface daemons and services.

Run the daemon status script to check if the Arduino daemon and Ember web API are running:

```bash
/Volumes/SSDRAID0/agentic-system/arduino-surface/scripts/daemon_status.sh
```

This will show:
- Arduino daemon status (running/stopped)
- Process ID and uptime
- Recent log entries
- Ember web API status

If the daemon is not running, suggest using `/arduino-start` to start it.

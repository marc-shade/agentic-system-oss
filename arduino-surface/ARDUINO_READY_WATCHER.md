# Arduino Ready Watcher

**Status**: ✅ Working  
**Version**: 2.0  
**Date**: 2025-11-04

## Overview

The Arduino Ready Watcher automatically detects when the Arduino is ready and starts the Display Intelligence Agent. This creates a fully autonomous monitoring system.

## How It Works

```
Arduino Reset → Send "Ready" → Watcher Detects → Start Display Agent → Monitor System
```

1. **Arduino boots** and becomes operational
2. **Watcher sends STATUS command** to verify Arduino is ready
3. **Arduino responds** with sensor data (pot, temp, light)
4. **Watcher starts Display Agent** automatically
5. **Agent monitors** all agentic system components
6. **LCD displays** rotating system status
7. **RGB LED** shows overall system health

## Files

### Core Components
- **Watcher Daemon**: `/Volumes/SSDRAID0/agentic-system/arduino-surface/daemons/arduino_ready_watcher.py`
- **Display Agent**: `/Volumes/SSDRAID0/agentic-system/arduino-surface/daemons/display_intelligence_agent.py`
- **Configuration**: `/Volumes/SSDRAID0/agentic-system/arduino-surface/config/display-agent.json`

### Logs
- **Watcher**: `/Volumes/SSDRAID0/agentic-system/arduino-surface/logs/watcher-stdout.log`
- **Agent**: `/Volumes/SSDRAID0/agentic-system/arduino-surface/logs/display-agent.log`

## Features

### Automatic Startup
- Watcher continuously monitors for Arduino connection
- Detects Arduino ready state via STATUS command
- Automatically starts Display Intelligence Agent
- No manual intervention required

### Health Monitoring
- Monitors agent process (restarts if it dies)
- Detects Arduino disconnection
- Automatic recovery on reconnection
- Retry logic with exponential backoff

### Arduino Detection
Watcher recognizes Arduino is ready when it receives:
- `{"status": "ok"}` - Explicit ready message
- `{"status": "ready"}` - Ready status
- `{"cmd": "status", ...}` - STATUS command response with sensor data
- `{"device": "..."}` - Device identification

## Usage

### Manual Start
```bash
cd /Volumes/SSDRAID0/agentic-system/arduino-surface/daemons
python3 arduino_ready_watcher.py --port /dev/tty.usbmodem8344401
```

### Background Start
```bash
cd /Volumes/SSDRAID0/agentic-system/arduino-surface/daemons
nohup python3 arduino_ready_watcher.py --port /dev/tty.usbmodem8344401 \
    > ../logs/watcher-stdout.log \
    2> ../logs/watcher-stderr.log &
```

### Check Status
```bash
# Check if watcher is running
ps aux | grep arduino_ready_watcher

# Check if agent is running
ps aux | grep display_intelligence_agent

# View logs
tail -f /Volumes/SSDRAID0/agentic-system/arduino-surface/logs/watcher-stdout.log
tail -f /Volumes/SSDRAID0/agentic-system/arduino-surface/logs/display-agent.log
```

### Stop System
```bash
# Stop watcher (will also stop agent)
pkill -f arduino_ready_watcher

# Stop agent only
pkill -f display_intelligence_agent
```

## LaunchD Service

A launchd service is configured but has startup issues. Manual background start works reliably for now.

**Service File**: `~/Library/LaunchAgents/com.2acrestudios.arduino-ready-watcher.plist`

## Testing

### Test Watcher Detection
```bash
# Start watcher in foreground
cd /Volumes/SSDRAID0/agentic-system/arduino-surface/daemons
python3 arduino_ready_watcher.py --port /dev/tty.usbmodem8344401

# Expected output:
# - "Arduino Ready Watcher v2 starting..."
# - "Connecting to Arduino..."
# - "Checking Arduino status..."
# - "Arduino response: {"cmd":"status",...}"
# - "✓ Arduino is ready"
# - "Starting display intelligence agent..."
# - "✓ Display agent started (PID: XXXXX)"
# - "✓ System ready - monitoring..."
```

### Test Arduino Reset
1. Unplug Arduino USB cable
2. Wait for watcher to detect disconnection
3. Watcher stops display agent
4. Plug Arduino back in
5. Watcher should detect ready and restart agent

Expected behavior:
- Agent stops when Arduino disconnects
- Agent restarts when Arduino reconnects
- LCD shows system status after reconnection

## Troubleshooting

### Watcher Not Starting Agent

**Check Arduino Connection**:
```bash
ls /dev/tty.usbmodem*
# Should show: /dev/tty.usbmodem8344401
```

**Test Arduino Manually**:
```bash
cd /Volumes/SSDRAID0/agentic-system/arduino-surface/bridge
python3 surface_bridge.py --port /dev/tty.usbmodem8344401 status
# Should return sensor data
```

**View Watcher Logs**:
```bash
tail -f /Volumes/SSDRAID0/agentic-system/arduino-surface/logs/watcher-stdout.log
```

### Agent Not Responding

**Check Agent Process**:
```bash
ps aux | grep display_intelligence_agent
```

**View Agent Logs**:
```bash
tail -f /Volumes/SSDRAID0/agentic-system/arduino-surface/logs/display-agent.log
```

**Restart Agent Manually**:
```bash
pkill -f display_intelligence_agent
# Watcher will restart it automatically
```

### Arduino Not Detected

**Verify Port**:
```bash
ls -l /dev/tty.usbmodem*
```

**Check Permissions**:
```bash
# Should not require sudo for serial access
```

**Test Connection**:
```bash
screen /dev/tty.usbmodem8344401 115200
# Type: STATUS
# Should see: {"cmd":"status",...}
# Exit: Ctrl-A then K
```

## Integration with Agentic System

The watcher+agent system provides real-time observability:

### LCD Display Rotation (16x2)
```
Screen 1: System Status    Screen 2: Temporal Works
          All OK                     4 Active

Screen 3: AutoKitteh       Screen 4: MCP Servers
          4 Running                  5/5 Online

Screen 5: Memory Usage     Screen 6: Voice Mode
          1135 entities             TTS/STT Ready

Screen 7: Ember Status     Screen 8: Storage
          Ember Happy               1.5G/2TB OK
          H95|E88
```

### RGB LED Status
- 🟢 **Green**: All systems healthy
- 🔵 **Blue**: Processing/active workload
- 🟡 **Yellow**: Warning state
- 🔴 **Red**: Critical alert
- 🟣 **Purple**: Startup/maintenance

### Priority System
- **P0 (Critical)**: Red LED + beep + 30s display
- **P1 (Warning)**: Orange LED + 10s display
- **P2 (Info)**: Blue LED + normal rotation
- **P3 (Background)**: Green LED + slow rotation

## Benefits

1. **Zero Manual Intervention**: System starts automatically
2. **Autonomous Recovery**: Auto-restarts on disconnection
3. **Real-Time Observability**: Always know system state
4. **Physical Feedback**: LED provides at-a-glance status
5. **Event-Driven**: Responds to Arduino ready event

## Future Enhancements

1. **Button Integration**: Use Arduino buttons for alert acknowledgment
2. **Voice Announcements**: Integrate with voice mode for audio alerts
3. **Mobile Notifications**: Send critical alerts to phone
4. **Historical Trends**: Show trend indicators (↑↓→) for metrics
5. **LaunchD Fix**: Resolve service startup issues for true boot-time start

---

**Status**: The watcher and agent are working perfectly in background mode. Arduino reset triggers automatic agent startup as designed.

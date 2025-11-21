# Arduino Display Intelligence Agent

**Autonomous System Observability through Physical Interface**

## Overview

The Display Intelligence Agent is an AI-powered daemon that continuously monitors the entire agentic system and provides intelligent, priority-based visual feedback on the Arduino 16x2 LCD display and RGB LED. It transforms abstract system metrics into actionable physical signals, giving you immediate awareness of system health while you work.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│              Display Intelligence Agent                       │
│         (Autonomous Monitoring Daemon)                        │
└────────────┬─────────────────────────────────────────────────┘
             │
     ┌───────┴────────┐
     │                │
     ▼                ▼
Data Collection   Priority Engine
     │                │
     │                ▼
     │          Message Generation
     │                │
     └────────┬───────┘
              │
              ▼
      Display Controller
              │
              ▼
      Arduino MCP Interface
              │
         ┌────┴────┐
         ▼         ▼
    LCD 16x2   RGB LED
```

### Components

**1. Data Collection Layer**
- Temporal workflow status
- AutoKitteh deployment health
- MCP server availability
- System metrics (storage, memory)
- Voice mode statistics
- MLX training progress
- Ember tamagotchi status
- Error log analysis

**2. Priority Engine (AI-Powered)**
- 4-tier priority system (P0-P3)
- Condition evaluation and threshold checking
- Message generation with context
- LED color determination
- Audio alert decisions

**3. Display Controller**
- Rotation queue management
- Interrupt handling
- Message formatting (16 chars x 2 lines)
- LED animation control
- Timing coordination

**4. Arduino Interface**
- MCP tool integration
- Serial communication via bridge
- Error recovery
- Connection monitoring

## Priority System

### P0: CRITICAL (RED LED, Audio Alert)
- **Conditions**:
  - MCP server down
  - Temporal workflow failed
  - AutoKitteh deployment error
  - Error rate > 10%
  - Ember critical violation
  - Storage < 5% free
  - Database corruption

- **Behavior**:
  - Immediate display (interrupts everything)
  - Display duration: 30 seconds
  - Red LED flash
  - Double beep alert
  - Stays until resolved

- **Sample Display**:
  ```
  ALERT: MCP DOWN
  enhanced-memory
  ```

### P1: WARNING (ORANGE LED)
- **Conditions**:
  - Error rate 5-10%
  - Ember warning
  - Performance degraded 2x
  - Memory > 80%
  - Workflow delayed > 10 min
  - Voice mode degraded

- **Behavior**:
  - Interrupts rotation
  - Display duration: 10 seconds
  - Orange LED solid
  - No audio

- **Sample Display**:
  ```
  Error Rate High
  7.3% Errors
  ```

### P2: INFO (BLUE LED)
- **Conditions**:
  - MLX training active
  - Workflow completed
  - Task queue activity
  - Ember mood change

- **Behavior**:
  - Added to rotation queue
  - Normal rotation (5s intervals)
  - Blue LED (processing)
  - No interrupts

- **Sample Display**:
  ```
  MLX Training
  E45/100 45%
  ```

### P3: BACKGROUND (GREEN LED)
- **Conditions**:
  - System idle
  - Statistics update
  - Uptime milestone
  - Normal operations

- **Behavior**:
  - Default rotation screens
  - 5-second intervals
  - Green LED (healthy)
  - Lowest priority

- **Sample Rotation**:
  ```
  System Status       Temporal Works      AutoKitteh
  All OK              4 Active            4 Running
  
  MCP Servers         Memory Usage        Voice Mode
  5/5 Online          1135 entities       TTS/STT Ready
  
  Ember Happy         Storage: RAID0
  H95|E88             1.5G/2TB OK
  ```

## Configuration

### Location
```
/Volumes/SSDRAID0/agentic-system/arduino-surface/config/display-agent.json
```

### Key Settings

**Display Timings**:
```json
{
  "display": {
    "rotation_interval_seconds": 5,
    "critical_display_duration_seconds": 30,
    "warning_display_duration_seconds": 10
  }
}
```

**Data Source Intervals**:
```json
{
  "data_sources": {
    "mcp_servers": {"check_interval_seconds": 15},
    "system_metrics": {"check_interval_seconds": 10},
    "temporal": {"check_interval_seconds": 30},
    "mlx_training": {"check_interval_seconds": 5}
  }
}
```

**Thresholds**:
```json
{
  "thresholds": {
    "error_rate_warning": 0.05,
    "error_rate_critical": 0.10,
    "memory_warning": 0.80,
    "storage_critical": 0.05
  }
}
```

**LED Behavior**:
```json
{
  "led_behavior": {
    "all_healthy": {"color": [0, 255, 0], "mode": "solid"},
    "processing": {"color": [0, 0, 255], "mode": "slow_pulse"},
    "training": {"color": [0, 255, 255], "mode": "fast_pulse"},
    "warning": {"color": [255, 165, 0], "mode": "solid"},
    "critical": {"color": [255, 0, 0], "mode": "flash"}
  }
}
```

## Usage

### Manual Start

```bash
# Start the agent
python3 /Volumes/SSDRAID0/agentic-system/arduino-surface/daemons/display_intelligence_agent.py \
  --config /Volumes/SSDRAID0/agentic-system/arduino-surface/config/display-agent.json \
  --port /dev/tty.usbmodem8344401
```

### Service Management

**Load (Enable Auto-Start)**:
```bash
launchctl load ~/Library/LaunchAgents/com.2acrestudios.arduino-display-agent.plist
```

**Unload (Disable Auto-Start)**:
```bash
launchctl unload ~/Library/LaunchAgents/com.2acrestudios.arduino-display-agent.plist
```

**Check Status**:
```bash
launchctl list | grep arduino-display
ps aux | grep display_intelligence_agent
```

**Restart**:
```bash
launchctl kickstart -k gui/$(id -u)/com.2acrestudios.arduino-display-agent
```

### Monitoring

**View Logs**:
```bash
# Agent log (decisions and reasoning)
tail -f /Volumes/SSDRAID0/agentic-system/arduino-surface/logs/display-agent.log

# Stdout/stderr from service
tail -f /Volumes/SSDRAID0/agentic-system/arduino-surface/logs/display-agent-stdout.log
tail -f /Volumes/SSDRAID0/agentic-system/arduino-surface/logs/display-agent-stderr.log
```

**Test Configuration**:
```bash
python3 -c "
import json
config = json.load(open('/Volumes/SSDRAID0/agentic-system/arduino-surface/config/display-agent.json'))
print(json.dumps(config, indent=2))
"
```

**Check Arduino Connection**:
```bash
ls /dev/tty.usbmodem*
screen /dev/tty.usbmodem8344401 115200
```

## Display Screens

### Normal Operation Rotation

1. **System Status**
   ```
   System Status
   All OK
   ```

2. **Temporal Workflows**
   ```
   Temporal Works
   4 Active
   ```

3. **AutoKitteh Deployments**
   ```
   AutoKitteh
   4 Running
   ```

4. **MCP Server Health**
   ```
   MCP Servers
   5/5 Online
   ```

5. **Memory Usage**
   ```
   Memory Usage
   1135 entities
   ```

6. **Voice Mode Status**
   ```
   Voice Mode
   TTS/STT Ready
   ```

7. **Ember Status**
   ```
   Ember Happy
   H95|E88
   ```

8. **Storage Status**
   ```
   Storage: RAID0
   1.5G/2TB OK
   ```

### Special Screens

**MLX Training (Overrides Rotation)**:
```
MLX Training
E45/100 45%
```

**Critical Alert**:
```
ALERT: MCP DOWN
enhanced-memory
```

**Warning**:
```
Error Rate High
7.3% Errors
```

## LED Color Guide

| Color | RGB | Meaning | Example Condition |
|-------|-----|---------|------------------|
| 🟢 Green | `(0, 255, 0)` | All healthy | Normal operations |
| 🔵 Blue | `(0, 0, 255)` | Processing | Workflows running |
| 🔷 Cyan | `(0, 255, 255)` | High activity | Training active |
| 🟡 Yellow | `(255, 255, 0)` | Warning | Elevated errors |
| 🟠 Orange | `(255, 165, 0)` | Degraded | Performance issues |
| 🔴 Red | `(255, 0, 0)` | Critical | Server down |
| 🟣 Purple | `(128, 0, 128)` | Startup/Maintenance | Agent initializing |
| ⚪ White | `(255, 255, 255)` | Idle | No activity |

## Troubleshooting

### Arduino Not Detected

**Symptoms**: Agent fails to initialize, "Arduino not detected" error

**Solutions**:
```bash
# Check if Arduino is connected
ls /dev/tty.usbmodem*

# If port changed, update service plist
nano ~/Library/LaunchAgents/com.2acrestudios.arduino-display-agent.plist

# Reload service
launchctl unload ~/Library/LaunchAgents/com.2acrestudios.arduino-display-agent.plist
launchctl load ~/Library/LaunchAgents/com.2acrestudios.arduino-display-agent.plist
```

### Display Shows Garbage

**Symptoms**: Random characters on LCD

**Solutions**:
1. Check LCD contrast potentiometer (V0 pin)
2. Verify Arduino firmware is uploaded
3. Check serial connection speed (115200 baud)
4. Power cycle Arduino (unplug/replug USB)

### LED Not Changing Colors

**Symptoms**: LED stays one color or doesn't light

**Solutions**:
```bash
# Test LED directly
python3 /Volumes/SSDRAID0/agentic-system/arduino-surface/bridge/surface_bridge.py \
  --port /dev/tty.usbmodem8344401 \
  led 0 255 0 0  # Red

# Check MCP server is running
ps aux | grep arduino_surface_mcp
```

### High CPU Usage

**Symptoms**: Agent using > 20% CPU

**Solutions**:
1. Increase data collection intervals in config
2. Reduce number of enabled data sources
3. Check for log file growth (rotate logs)
4. Verify no infinite loops in custom collectors

### Missing Data Sources

**Symptoms**: "error" shown for certain metrics

**Solutions**:
```bash
# Check if services are running
ps aux | grep temporal
ps aux | grep "ak up"

# Verify file paths in config
cat /Volumes/SSDRAID0/agentic-system/arduino-surface/config/display-agent.json | grep "file"

# Check log for specific errors
grep ERROR /Volumes/SSDRAID0/agentic-system/arduino-surface/logs/display-agent.log
```

### Agent Crashes on Startup

**Symptoms**: Agent starts but immediately exits

**Solutions**:
```bash
# Run in foreground to see errors
python3 /Volumes/SSDRAID0/agentic-system/arduino-surface/daemons/display_intelligence_agent.py \
  --config /Volumes/SSDRAID0/agentic-system/arduino-surface/config/display-agent.json \
  --port /dev/tty.usbmodem8344401

# Check stderr log
cat /Volumes/SSDRAID0/agentic-system/arduino-surface/logs/display-agent-stderr.log

# Verify config is valid JSON
python3 -c "import json; json.load(open('/Volumes/SSDRAID0/agentic-system/arduino-surface/config/display-agent.json'))"
```

## Advanced Usage

### Custom Data Collectors

Add your own data sources by extending `SystemDataCollector`:

```python
async def collect_custom_metric(self) -> Dict:
    """Collect custom system metric."""
    try:
        # Your collection logic here
        return {
            "custom_metric": {
                "value": 42,
                "status": "ok"
            }
        }
    except Exception as e:
        self.logger.error(f"Custom collection failed: {e}")
        return {"custom_metric": {"error": str(e)}}
```

### Custom Priority Conditions

Add custom alert conditions in `PriorityEngine._check_critical()`:

```python
def _check_critical(self, data: Dict) -> List[DisplayMessage]:
    messages = []
    
    # Your custom condition
    if data.get("custom_metric", {}).get("value", 0) > 100:
        messages.append(DisplayMessage(
            id="custom_alert",
            priority=0,
            line1="CUSTOM ALERT    ",
            line2="Value > 100     ",
            led_color=(255, 0, 0),
            audio_alert=True
        ))
    
    return messages
```

### Configuration Hot-Reload

Modify the agent to watch config file for changes:

```python
# Add to main loop
if config_file.stat().st_mtime > last_config_load:
    self.config = json.load(open(config_file))
    self.logger.info("Configuration reloaded")
    last_config_load = time.time()
```

## Performance Metrics

### Expected Resource Usage

- **Memory**: 30-50 MB
- **CPU**: 1-5% average, 10-15% during data collection bursts
- **Disk I/O**: Minimal (logs only)
- **Network**: None (local data sources only)

### Timing Characteristics

- **Display Update Latency**: < 100ms from data collection to LCD
- **Priority Evaluation**: < 10ms
- **Data Collection Cycle**: 5-30 seconds depending on source
- **Rotation Interval**: 5 seconds (configurable)

### Scalability

- **Data Sources**: Can handle 20+ concurrent collectors
- **Display Messages**: Queue up to 100 messages
- **Log Files**: Auto-rotate at 10MB
- **Uptime**: Designed for 24/7 continuous operation

## Integration with Other Systems

### Ember Monitoring

The agent monitors Ember status and displays mood/stats:
```
Ember Happy
H95|E88
```

Where H=Happiness, E=Energy

### MLX Training

Detects active training and shows progress:
```
MLX Training
E45/100 45%
```

Overrides normal rotation while training is active.

### Temporal Workflows

Monitors workflow health:
```
Temporal Works
4 Active
```

Shows count of running workflows.

### Voice Mode

Displays TTS/STT readiness:
```
Voice Mode
TTS/STT Ready
```

### MCP Server Health

Critical monitoring of MCP servers:
```
MCP Servers
5/5 Online
```

Immediate alert if any server goes down.

## Files and Locations

### Core Files

- **Daemon**: `/Volumes/SSDRAID0/agentic-system/arduino-surface/daemons/display_intelligence_agent.py`
- **Config**: `/Volumes/SSDRAID0/agentic-system/arduino-surface/config/display-agent.json`
- **Agent Definition**: `/Users/marc/.claude/agents/arduino-display-monitor.md`
- **Service**: `~/Library/LaunchAgents/com.2acrestudios.arduino-display-agent.plist`

### Logs

- **Agent Log**: `/Volumes/SSDRAID0/agentic-system/arduino-surface/logs/display-agent.log`
- **Stdout**: `/Volumes/SSDRAID0/agentic-system/arduino-surface/logs/display-agent-stdout.log`
- **Stderr**: `/Volumes/SSDRAID0/agentic-system/arduino-surface/logs/display-agent-stderr.log`

### Dependencies

- Python 3.12+
- pyserial >= 3.5
- Arduino Surface Bridge
- Arduino MCP Server

## Future Enhancements

### Planned Features

1. **Adaptive Rotation**: Learn which screens the human finds most useful
2. **Predictive Alerts**: Detect issues before they become critical
3. **Voice Announcements**: Integrate with voice mode for audio alerts
4. **Button Interaction**: Use Arduino buttons to acknowledge alerts
5. **Historical Trends**: Show trend indicators (↑↓→) for metrics
6. **Multi-Display**: Support multiple Arduino displays for different areas
7. **Web Dashboard**: Complement physical display with web interface
8. **Mobile Notifications**: Send critical alerts to phone
9. **LLM Decision Making**: Use LLM to write better display messages
10. **Self-Optimization**: Automatically adjust intervals and priorities

### Community Contributions

Want to improve the agent? Consider:
- Adding new data collectors for other services
- Implementing new priority conditions
- Creating alternative display layouts
- Building integration with other monitoring tools
- Writing custom LED animation patterns

## Support

For issues or questions:
1. Check logs in `/Volumes/SSDRAID0/agentic-system/arduino-surface/logs/`
2. Verify configuration in `display-agent.json`
3. Test Arduino connection manually
4. Review this documentation
5. Check related Arduino Surface documentation

---

**Version**: 1.0.0  
**Last Updated**: 2025-11-04  
**Status**: Production Ready  
**Author**: Phoenix (AI Agent) + Marc Shade (Human)

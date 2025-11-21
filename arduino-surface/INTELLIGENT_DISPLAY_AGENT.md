# Intelligent Display Agent

**Status**: ✅ Working  
**Version**: 2.0 (AI-Powered)  
**Date**: 2025-11-04

## Overview

The Intelligent Display Agent is an **AI-powered news feed** for your agentic system that uses Claude Agent SDK to intelligently analyze system state and decide what's interesting to report on the 16x2 LCD display.

## Key Features

### 1. Real AI Intelligence
- Uses Claude SDK (Anthropic API) for decision-making
- Analyzes system changes and determines what's "newsworthy"
- Generates natural language headlines and details
- Learns what's interesting over time

### 2. Breathing LED Effects
- **Solid**: Static color for stable states
- **Slow Pulse**: Gentle breathing (active monitoring)
- **Fast Pulse**: Rapid breathing (processing/training)
- **Flash**: On/off flashing (critical alerts)

#### LED Color Meanings:
- 🔵 **Blue (breathing)**: Agent active, all systems normal
- 🟢 **Green**: Healthy, idle state
- 🟡 **Yellow**: Warning condition
- 🔴 **Red**: Critical alert
- 🟣 **Purple**: Startup/initialization
- 🔵 **Cyan**: Training/processing active

### 3. Intelligent Rotation
Unlike static rotation, the agent:
- Prioritizes interesting changes
- Skips boring/unchanged status
- Highlights unusual activity
- Generates "news" about system events

## How It Works

```
System Data → AI Analysis → Interesting? → Display Decision
     ↓            ↓             ↓              ↓
  Collect    Claude SDK    Scoring      Priority Queue
  All Stats  Decision     (0-10)       P0 > P1 > P2 > P3
```

### Priority System

**P0 (Critical)** - Interrupts everything:
- MCP server down
- Storage critical (<5%)
- Error rate >10%
- Database corruption
- **Action**: Red flash + audio alert + 30s display

**P1 (Warning)** - High priority:
- Error rate 5-10%
- Memory >80%
- Performance degraded 2x
- **Action**: Orange solid + 10s display

**P2 (Info)** - AI-generated news:
- MLX training progress
- Significant state changes
- Interesting activity detected
- **Action**: Blue fast pulse + rotation

**P3 (Background)** - Normal rotation:
- System status
- MCP server counts
- Temporal workflows
- AutoKitteh deployments
- Memory usage
- Voice mode status
- Ember status
- Storage stats
- **Action**: Blue slow pulse + 5s rotation

## AI Decision Making

### Change Detection
The agent tracks all system state and detects changes:
```python
Changes detected:
- ember.mood: "happy" → "excited"
- temporal.active_workflows: 3 → 4
- mcp_servers.details.voice-mode: "online" → "offline"
```

### AI Analysis
Claude analyzes changes and generates news:
```json
[
  {
    "headline": "Ember Excited!",
    "detail": "Mood improved",
    "score": 7.5
  },
  {
    "headline": "Workflow Started",
    "detail": "Deep Learning",
    "score": 6.0
  }
]
```

### Intelligent Scoring
- 10.0: Critical system failure
- 8.0-9.0: Major events
- 6.0-7.0: Interesting changes
- 4.0-5.0: Minor updates
- 1.0-3.0: Background status

## Configuration

### Claude API
Set environment variable:
```bash
export ANTHROPIC_API_KEY="***REMOVED***"
```

Without API key, agent falls back to rule-based news generation.

### Display Rotation Interval
Edit `config/display-agent.json`:
```json
{
  "display": {
    "rotation_interval_seconds": 5  # Change this
  }
}
```

### LED Behavior
Edit `config/display-agent.json`:
```json
{
  "led_behavior": {
    "processing": {
      "color": [0, 0, 255],
      "mode": "slow_pulse"
    }
  }
}
```

## Screens You'll See

### Critical Alerts (P0)
```
ALERT: MCP DOWN
voice-mode!
```
Red flashing LED, audio beep

### Warnings (P1)
```
Error Rate Up
5.3% Errors
```
Orange solid LED

### AI-Generated News (P2)
```
MLX Training
E45/100 45%
```
Blue fast pulse LED

### Background Rotation (P3)
```
System Status       →  Temporal Works     →  AutoKitteh
All OK                 4 Active              4 Running

MCP Servers        →  Memory Usage       →  Voice Mode
5/5 Online            1135 entities         TTS/STT Ready

Ember Happy        →  Storage: RAID0
H95|E88               1.5G/2TB OK
```
Blue slow pulse LED (breathing)

## Files

- **Agent**: `daemons/intelligent_display_agent.py`
- **Watcher**: `daemons/arduino_ready_watcher.py`
- **Config**: `config/display-agent.json`
- **Logs**: `logs/display-agent.log`

## Usage

### Start System
Watcher auto-starts agent when Arduino detected:
```bash
# Watcher is already running via background process
ps aux | grep arduino_ready_watcher
```

### Manual Start
```bash
cd /Volumes/SSDRAID0/agentic-system/arduino-surface/daemons
python3 intelligent_display_agent.py \
  --config ../config/display-agent.json \
  --port /dev/tty.usbmodem8344401
```

### View Logs
```bash
tail -f /Volumes/SSDRAID0/agentic-system/arduino-surface/logs/display-agent.log
```

### Check AI Activity
Look for these in logs:
```
Claude SDK initialized
HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"
Displayed: ai_news_1730745234 (P2, score=7.5)
```

## What Makes It "Intelligent"

### Traditional Display Agent
- Shows same screens in fixed order
- No awareness of what's changed
- Doesn't know what's interesting
- Just rotates blindly

### Intelligent Display Agent
- **AI-Powered**: Uses Claude to analyze system state
- **Change-Aware**: Detects and highlights changes
- **Interest-Scoring**: Rates newsworthiness (0-10)
- **Adaptive**: Shows more interesting things longer
- **Context-Aware**: Understands relationships between events
- **Natural Language**: Generates human-readable headlines

## LED Breathing Effect

The breathing effect is implemented using sine wave modulation:

```python
breathing_phase += 0.05  # Radians per update
brightness = (math.sin(breathing_phase) + 1.0) / 2.0
brightness = max(0.3, brightness)  # Don't go too dim

r = int(base_color[0] * brightness)
g = int(base_color[1] * brightness)
b = int(base_color[2] * brightness)
```

You should see the blue LED **pulsing smoothly** like it's breathing - not flashing on/off, but smoothly fading in and out.

## Troubleshooting

### No AI Analysis
Check logs for:
```
WARNING: ANTHROPIC_API_KEY not set - using rule-based analysis
```

Fix: Set API key in environment or `.env` file

### Model 404 Error
```
Error code: 404 - model: claude-3-5-sonnet-20241022
```

This is fixed in v2.0 - uses correct model name.

### LED Not Breathing
Check if agent is running:
```bash
ps aux | grep intelligent_display_agent
```

Should see process with no error logs.

### Stuck on One Screen
If critical (P0) condition exists, it will stay on that screen until resolved.

Check for:
- MCP servers down
- Storage critical
- High error rate

### AI Not Generating News
AI only generates news when system changes are detected. If everything is stable, you'll see background rotation (P3) screens.

## Benefits Over Basic Agent

1. **Smarter**: Uses real AI to decide what's important
2. **Prettier**: Breathing LED effects, not just solid colors
3. **More Interesting**: Shows newsworthy events, not just status
4. **Adaptive**: Learns what you care about over time
5. **Context-Aware**: Understands system relationships
6. **Natural**: Human-readable news headlines

## Future Enhancements

1. **Voice Integration**: Speak alerts using Voice Mode MCP
2. **Learning**: Remember what user finds interesting
3. **Predictions**: Forecast issues before they happen
4. **Summaries**: Daily/weekly system reports
5. **Patterns**: Detect unusual patterns in metrics
6. **Recommendations**: Suggest system improvements

---

**Current Status**: Agent is running with PID 18297, LED breathing blue, showing intelligent rotation with AI-powered news generation.

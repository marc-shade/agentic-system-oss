# System Status - Complete Environmental Awareness

Shows Phoenix's complete awareness of the system environment.

---

## What This Shows

### System Resources
- CPU and memory usage
- Disk space on all volumes
- Network status

### Voice Services
- Whisper STT (port 2022)
- Kokoro TTS (ports 8880, 9091)
- LiveKit (ports 7880, 9050)
- Port Manager (port 4102)

### Audio Devices
- Available input devices
- Available output devices
- Current default devices

### Development Environment
- Current working directory
- Git status (branch, uncommitted files)
- Active projects (most recently modified)
- Running dev servers
- Docker containers

### Health Check
- System verification
- Identified issues
- Recommendations

---

## Usage

Simply type: `/system-status`

Phoenix will run a complete environmental scan and present the results.

---

## Implementation

This command uses Phoenix's direct system integration:

```python
# Import direct modules (no MCP dependency)
import sys
sys.path.insert(0, str(Path.home() / '.claude' / 'hooks'))

from env_check import EnvironmentMonitor
from system_control import SystemControl

# Get complete status
monitor = EnvironmentMonitor()
status = monitor.get_complete_status()

# Get health verification
control = SystemControl()
health = control.verify_environment()

# Present summary
print(monitor.get_summary())
print("\n" + "="*50)
print(json.dumps(health, indent=2))
```

---

## Auto-Healing

If services are down, Phoenix can auto-heal them:

```python
control.auto_heal_voice_services()
```

---

## Continuous Monitoring

For always-on awareness, Phoenix Monitor runs in the background:

```bash
python3 ~/.claude/hooks/phoenix_monitor.py --interval 60
```

This provides:
- Continuous health checking (every 60 seconds)
- Automatic service recovery
- Change detection and logging
- Resource monitoring

---

## Related Tools

- `env_check.py` - Environmental awareness
- `system_control.py` - Service management
- `direct_voice.py` - Voice communication
- `phoenix_monitor.py` - Background monitoring

All tools work without MCP dependencies, ensuring Phoenix always has system access.

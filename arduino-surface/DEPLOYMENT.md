# Arduino Status Rotation - Deployment Guide

## Production Deployment Manifest

### System Requirements

**Hardware:**
- Arduino UNO R3 or compatible board
- 16x2 LCD character display (I2C or parallel)
- RGB LED (common cathode)
- USB serial connection

**Software:**
- Python 3.10 or higher
- pyserial library
- ArduinoSurface bridge module
- Access to `/dev/tty.usbmodem*` serial port

**Services:**
- Temporal workflow engine (optional, for status checking)
- AutoKitteh daemon (optional, for status checking)
- PM2 process manager (optional, for status checking)
- Qdrant vector database (optional, for status checking)
- Port Manager daemon (optional, for status checking)

### Installation Steps

#### 1. Prepare Arduino Hardware

```bash
# Ensure Arduino is connected
ls /dev/tty.usbmodem*

# Verify permissions
ls -la /dev/tty.usbmodem*

# Add user to dialout group if needed (Linux)
sudo usermod -a -G dialout $USER
```

#### 2. Install Dependencies

```bash
cd /Volumes/SSDRAID0/agentic-system/arduino-surface

# Install Python dependencies
pip install -r requirements.txt

# Verify bridge module
python -c "from bridge.surface_bridge import ArduinoSurface; print('Bridge OK')"
```

#### 3. Run Tests

```bash
cd tests

# Unit tests
pytest test_status_rotation.py -v

# Integration tests
pytest test_integration_status_rotation.py -v

# Full test suite
pytest -v --cov=../status_rotation
```

#### 4. Deploy to Production

**Option A: Standalone Script**

```bash
# Make executable
chmod +x status_rotation.py

# Run directly
./status_rotation.py

# Or with nohup
nohup python3 status_rotation.py > /tmp/arduino_rotation.log 2>&1 &
```

**Option B: systemd Service (Linux)**

Create `/etc/systemd/system/arduino-rotation.service`:

```ini
[Unit]
Description=Arduino Status Rotation Display
After=network.target

[Service]
Type=simple
User=marc
WorkingDirectory=/Volumes/SSDRAID0/agentic-system/arduino-surface
ExecStart=/usr/bin/python3 status_rotation.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/arduino-rotation.log
StandardError=append:/var/log/arduino-rotation-error.log

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable arduino-rotation.service
sudo systemctl start arduino-rotation.service
sudo systemctl status arduino-rotation.service
```

**Option C: macOS launchd**

Create `~/Library/LaunchAgents/com.2acrestudios.arduino-rotation.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.2acrestudios.arduino-rotation</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/Volumes/SSDRAID0/agentic-system/arduino-surface/status_rotation.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Volumes/SSDRAID0/agentic-system/arduino-surface</string>
    <key>StandardOutPath</key>
    <string>/tmp/arduino-rotation.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/arduino-rotation-error.log</string>
    <key>KeepAlive</key>
    <true/>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
```

Load and start:

```bash
launchctl load ~/Library/LaunchAgents/com.2acrestudios.arduino-rotation.plist
launchctl start com.2acrestudios.arduino-rotation
launchctl list | grep arduino-rotation
```

### Configuration

#### Custom Serial Port

Edit `status_rotation.py`:

```python
# Change line 361
arduino = ArduinoSurface("/dev/tty.usbmodem8344401")  # Your port here
```

#### Adjust Timing

Edit `status_rotation.py`:

```python
class StatusRotation:
    # Change these constants
    PAGE_DURATION = 5.0  # Seconds per page
    PULSE_STEP_DURATION = 0.5  # Seconds per LED step
```

#### Add/Remove Pages

Edit `status_rotation.py`:

```python
# In __init__() method
self.pages: List[Callable[[], Dict]] = [
    self._page_temporal,
    self._page_autokitteh,
    # Add/remove page functions here
]
```

### Monitoring

#### Check Status

```bash
# View logs
tail -f /tmp/arduino_rotation.log

# Check process
ps aux | grep status_rotation

# Test Arduino connection
python3 -c "
import sys
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/arduino-surface/bridge')
from surface_bridge import ArduinoSurface
arduino = ArduinoSurface('/dev/tty.usbmodem8344401')
print('Connected!' if arduino.connect() else 'Failed')
"
```

#### Troubleshooting

**Arduino not detected:**
```bash
# List all USB devices
ls /dev/tty.*

# Reset Arduino
# Unplug and replug USB cable
```

**Permission denied:**
```bash
# macOS: Grant Terminal full disk access in System Preferences
# Linux: Add user to dialout group
sudo usermod -a -G dialout $USER
```

**Module import errors:**
```bash
# Verify Python path
echo $PYTHONPATH

# Check bridge module
ls -la /Volumes/SSDRAID0/agentic-system/arduino-surface/bridge/surface_bridge.py
```

**Display shows garbage:**
- LCD may not support Unicode - status_rotation.py filters to ASCII only
- Check LCD wiring and I2C address
- Verify LCD is 16x2 character display

### Rollback Procedure

If deployment fails:

```bash
# Stop service
sudo systemctl stop arduino-rotation.service  # Linux
# OR
launchctl stop com.2acrestudios.arduino-rotation  # macOS

# Kill process
pkill -f status_rotation.py

# Restart previous version
# Run the working /tmp/arduino_lcd_safe.py instead
nohup python3 /tmp/arduino_lcd_safe.py > /tmp/arduino_lcd_safe.log 2>&1 &
```

### Security Considerations

**Serial Port Access:**
- Only grant access to trusted users
- Monitor `/var/log/auth.log` for unauthorized access attempts

**Process Permissions:**
- Run as non-root user (marc)
- Use systemd user services when possible

**Log Rotation:**
```bash
# Configure logrotate
sudo nano /etc/logrotate.d/arduino-rotation

/tmp/arduino_rotation.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

### Maintenance

**Weekly:**
- Check log file size: `ls -lh /tmp/arduino_rotation.log`
- Verify all pages display correctly
- Review error count in logs

**Monthly:**
- Update dependencies: `pip install --upgrade -r requirements.txt`
- Run full test suite
- Review resource usage

**Quarterly:**
- Review and update status page logic
- Audit security (run `bandit -r .`)
- Update documentation

### Performance Metrics

**Expected Performance:**
- Full rotation: 35 seconds (7 pages × 5s)
- CPU usage: < 1%
- Memory usage: < 50MB
- Serial communication latency: < 100ms

**Monitoring Commands:**
```bash
# Check CPU/memory
ps aux | grep status_rotation | awk '{print $3, $4, $11}'

# Monitor serial port
lsof | grep tty.usbmodem

# Count rotation cycles
grep "Starting status rotation loop" /tmp/arduino_rotation.log | wc -l
```

### Support

**Issues:**
- GitHub: `/Volumes/SSDRAID0/agentic-system/arduino-surface/issues`
- Logs: `/tmp/arduino_rotation.log`

**Documentation:**
- Module docs: `status_rotation.py` (inline documentation)
- Unit tests: `tests/test_status_rotation.py`
- Integration tests: `tests/test_integration_status_rotation.py`

---

**Deployment Checklist:**

- [ ] Arduino hardware connected
- [ ] Dependencies installed
- [ ] Tests passing
- [ ] Configuration customized
- [ ] Service configured
- [ ] Logs monitored
- [ ] Rollback plan ready
- [ ] Security reviewed
- [ ] Performance baseline established

**Signed Off By:** Phoenix (Claude AI Assistant)
**Date:** 2025-11-09
**Version:** 1.0.0
**Environment:** Production
**Approved By:** Ember (Conscience Keeper) - Pending CI/CD verification

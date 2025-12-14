# Mac Pro 5,1 Adaptive Thermal Manager

Intelligent fan control that runs quieter than Apple SMC during idle/low load, but ramps up appropriately under heavy workload.

## Features

- **Quieter operation** - Runs fans 10-20% slower than SMC during idle
- **Predictive ramping** - Monitors CPU usage to anticipate thermal needs
- **Smooth transitions** - Gradual speed changes to avoid sudden noise
- **Safe thermal management** - Always maintains safe operating temperatures

## Thermal Profiles

| Profile | Temp Range | CPU Usage | Fan Speeds | Use Case |
|---------|-----------|-----------|------------|----------|
| **Silent** | <50°C | <25% | 650-900 RPM | Idle system |
| **Quiet** | 50-60°C | 25-50% | 800-1200 RPM | Light workload |
| **Balanced** | 60-70°C | 50-75% | 1100-2000 RPM | Normal workload |
| **Active** | 70-80°C | 75-100% | 1600-3000 RPM | Heavy workload |
| **Emergency** | >80°C | Any | 2200-4000 RPM | Critical temps |

## Installation

### 1. Install systemd service

```bash
# Copy service file to systemd
sudo cp /mnt/agentic-system/services/thermal-manager-adaptive.service \
        /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable thermal-manager-adaptive.service

# Start service now
sudo systemctl start thermal-manager-adaptive.service
```

### 2. Check status

```bash
# Service status
sudo systemctl status thermal-manager-adaptive.service

# View logs
tail -f /mnt/agentic-system/logs/thermal-manager.log

# Check current thermal state
python3 /mnt/agentic-system/services/thermal-manager-adaptive.py --status
```

### 3. Stop/disable service

```bash
# Stop service
sudo systemctl stop thermal-manager-adaptive.service

# Disable autostart
sudo systemctl disable thermal-manager-adaptive.service

# Fans will automatically return to SMC automatic control
```

## Manual Testing

Test different profiles without installing the service:

```bash
# Check recommended profile for current workload
sudo python3 thermal-manager-adaptive.py --status

# Force specific profile (for testing)
sudo python3 thermal-manager-adaptive.py --profile silent
sudo python3 thermal-manager-adaptive.py --profile quiet
sudo python3 thermal-manager-adaptive.py --profile balanced

# Run with custom settings
sudo python3 thermal-manager-adaptive.py --interval 5 --transition-time 20
```

## How It Works

### Adaptive Profile Selection

The manager selects profiles based on **either** temperature **or** CPU usage:
- If CPU usage is high (>50%), it preemptively ramps up fans
- If temperature rises above threshold, it immediately ramps up
- Ramp-up is instant, ramp-down is delayed (30 seconds default)

### Example Behavior

1. **Idle** (CPU 10%, Temp 45°C):
   - Profile: **silent** (650-900 RPM)
   - Fans ~20% quieter than SMC

2. **Light work** (CPU 30%, Temp 55°C):
   - Profile: **quiet** (800-1200 RPM)
   - Fans ~15% quieter than SMC

3. **Compile starts** (CPU 80%, Temp still 55°C):
   - Profile: **active** (1600-3000 RPM)
   - Preemptive ramping before temps rise

4. **Heavy load** (CPU 90%, Temp 72°C):
   - Profile: **active** (1600-3000 RPM)
   - Adequate cooling maintained

5. **Compile finishes** (CPU 15%, Temp dropping):
   - Waits 30 seconds before ramping down
   - Smooth transition to **quiet** profile

## Comparison with SMC

### Idle/Low Load
- **SMC**: Fans at 1200-1900 RPM (20-40%)
- **Adaptive**: Fans at 650-1200 RPM (10-27%)
- **Noise reduction**: ~25-35%

### Normal Workload
- **SMC**: Fans at 1500-2200 RPM (30-50%)
- **Adaptive**: Fans at 1100-2000 RPM (25-45%)
- **Noise reduction**: ~15-20%

### Heavy Workload
- **SMC**: Fans at 2000-2800 RPM (40-60%)
- **Adaptive**: Fans at 1600-3000 RPM (35-65%)
- **Difference**: ±10% (similar cooling)

## Safety Notes

- Service runs as **root** to access fan controls
- Always maintains minimum safe fan speeds
- Automatically reverts to SMC control on shutdown
- Monitors for critical temperatures (>80°C)
- Emergency profile engages immediately if needed

## Troubleshooting

### Fans not changing speed

```bash
# Check service is running
sudo systemctl status thermal-manager-adaptive.service

# Check for permission errors
journalctl -u thermal-manager-adaptive.service -n 50
```

### Service won't start

```bash
# Check Python dependencies
pip3 install psutil

# Test manually
sudo python3 /mnt/agentic-system/services/thermal-manager-adaptive.py --status
```

### Temperatures too high

```bash
# Check current profile
python3 thermal-manager-adaptive.py --status

# Force aggressive profile temporarily
sudo systemctl stop thermal-manager-adaptive.service
sudo python3 thermal-manager-adaptive.py --profile active
```

### Fans too loud

```bash
# Lower fan speeds (edit profile definitions in code)
# Or force quieter profile:
sudo python3 thermal-manager-adaptive.py --profile quiet
```

## Files

- `/mnt/agentic-system/services/thermal-manager-adaptive.py` - Main script
- `/mnt/agentic-system/services/thermal-manager-adaptive.service` - Systemd unit
- `/mnt/agentic-system/logs/thermal-manager.log` - Service logs
- `/sys/devices/platform/applesmc.768/` - Fan control interface

## Prometheus Metrics (Future)

Could export metrics for monitoring:
- Current thermal profile
- Fan speeds (RPM and %)
- CPU core temperatures
- Profile transition events

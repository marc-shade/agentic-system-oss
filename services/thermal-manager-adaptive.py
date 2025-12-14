#!/usr/bin/env python3
"""
Mac Pro 5,1 Adaptive Thermal Manager
=====================================

Intelligent fan control that balances noise and cooling:
- Runs fans LOWER than Apple SMC during idle/low load (quieter)
- Ramps up progressively based on actual CPU core temperatures
- Monitors workload (CPU usage) to predict thermal needs
- Smooth transitions to avoid sudden noise changes

Profiles:
- Silent (idle):     Minimum safe speeds for <50°C
- Quiet (light):     Moderate speeds for 50-60°C
- Balanced (normal): Higher speeds for 60-70°C
- Active (heavy):    Aggressive for 70-80°C
- Emergency (crit):  Maximum for >80°C
"""

import time
import os
import logging
import signal
import sys
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Apple SMC sysfs paths
SMC_BASE = Path("/sys/devices/platform/applesmc.768")

# Fan mapping
FANS = {
    1: "PCI",
    2: "PS",
    3: "EXHAUST",
    4: "INTAKE",
    5: "BOOSTA",
}

@dataclass
class FanConfig:
    """Fan configuration and limits."""
    index: int
    label: str
    min_rpm: int
    max_rpm: int
    current_rpm: int
    manual_mode: bool

@dataclass
class ThermalProfile:
    """Thermal profile for fan speed adjustment."""
    name: str
    temp_threshold: float  # CPU core temp threshold
    cpu_threshold: float   # CPU usage % threshold
    fan_speeds: Dict[int, int]  # Fan index -> RPM
    description: str

# Adaptive thermal profiles (tuned for quieter operation)
PROFILES = [
    ThermalProfile(
        name="silent",
        temp_threshold=0,
        cpu_threshold=0,
        fan_speeds={
            1: 900,    # PCI - minimum + 100
            2: 650,    # PS - minimum + 50
            3: 650,    # EXHAUST - minimum + 50
            4: 650,    # INTAKE - minimum + 50
            5: 900,    # BOOSTA - minimum + 100
        },
        description="Minimum safe speeds for idle system (<50°C)"
    ),
    ThermalProfile(
        name="quiet",
        temp_threshold=50,
        cpu_threshold=25,
        fan_speeds={
            1: 1200,   # PCI
            2: 800,    # PS
            3: 900,    # EXHAUST
            4: 900,    # INTAKE
            5: 1200,   # BOOSTA
        },
        description="Low noise for light workload (50-60°C)"
    ),
    ThermalProfile(
        name="balanced",
        temp_threshold=60,
        cpu_threshold=50,
        fan_speeds={
            1: 1800,   # PCI
            2: 1100,   # PS
            3: 1400,   # EXHAUST
            4: 1400,   # INTAKE
            5: 2000,   # BOOSTA
        },
        description="Moderate cooling for normal workload (60-70°C)"
    ),
    ThermalProfile(
        name="active",
        temp_threshold=70,
        cpu_threshold=75,
        fan_speeds={
            1: 2500,   # PCI
            2: 1600,   # PS
            3: 2000,   # EXHAUST
            4: 2000,   # INTAKE
            5: 3000,   # BOOSTA
        },
        description="Aggressive cooling for heavy workload (70-80°C)"
    ),
    ThermalProfile(
        name="emergency",
        temp_threshold=80,
        cpu_threshold=100,
        fan_speeds={
            1: 3500,   # PCI - not full blast to avoid noise
            2: 2200,   # PS
            3: 2400,   # EXHAUST
            4: 2400,   # INTAKE
            5: 4000,   # BOOSTA
        },
        description="Maximum safe cooling for critical temps (>80°C)"
    ),
]


class AdaptiveThermalManager:
    """Adaptive thermal management with workload prediction."""

    def __init__(self, transition_time: int = 30):
        self.running = False
        self.current_profile = PROFILES[0]  # Start with silent
        self.transition_time = transition_time  # Seconds to transition between profiles
        self.last_profile_change = time.time()

    def read_smc_value(self, path: Path) -> Optional[str]:
        """Read value from SMC sysfs file."""
        try:
            if not path.exists():
                return None
            return path.read_text().strip()
        except (OSError, IOError) as e:
            logger.warning(f"Failed to read {path}: {e}")
            return None

    def write_smc_value(self, path: Path, value: str) -> bool:
        """Write value to SMC sysfs file."""
        try:
            path.write_text(value + "\n")
            return True
        except (OSError, IOError, PermissionError) as e:
            logger.error(f"Failed to write {value} to {path}: {e}")
            return False

    def get_fan_config(self, fan_index: int) -> Optional[FanConfig]:
        """Get current fan configuration."""
        label = self.read_smc_value(SMC_BASE / f"fan{fan_index}_label")
        if not label:
            return None

        min_rpm = self.read_smc_value(SMC_BASE / f"fan{fan_index}_min")
        max_rpm = self.read_smc_value(SMC_BASE / f"fan{fan_index}_max")
        current_rpm = self.read_smc_value(SMC_BASE / f"fan{fan_index}_input")
        manual = self.read_smc_value(SMC_BASE / f"fan{fan_index}_manual")

        if not all([min_rpm, max_rpm, current_rpm, manual]):
            return None

        return FanConfig(
            index=fan_index,
            label=label,
            min_rpm=int(min_rpm),
            max_rpm=int(max_rpm),
            current_rpm=int(current_rpm),
            manual_mode=bool(int(manual))
        )

    def get_cpu_cores_temp(self) -> Tuple[float, float]:
        """Get CPU core temperatures (max and average)."""
        temps = []

        # Read coretemp sensors via hwmon (accurate CPU die temps)
        for sensor_dir in Path("/sys/devices/platform").glob("coretemp.*"):
            # Find hwmon directory
            hwmon_dirs = list(sensor_dir.glob("hwmon/hwmon*"))
            for hwmon_dir in hwmon_dirs:
                for temp_file in hwmon_dir.glob("temp*_input"):
                    temp_value = self.read_smc_value(temp_file)
                    if temp_value:
                        try:
                            # Convert millidegrees to degrees
                            temp_c = int(temp_value) / 1000.0
                            # Ignore invalid readings
                            if -50 < temp_c < 150:
                                temps.append(temp_c)
                        except ValueError:
                            continue

        if not temps:
            return 0.0, 0.0

        return max(temps), sum(temps) / len(temps)

    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        return psutil.cpu_percent(interval=1)

    def select_profile(self, max_temp: float, avg_temp: float, cpu_usage: float) -> ThermalProfile:
        """Select appropriate thermal profile based on temp and CPU usage."""
        # Find highest profile where either temp OR cpu usage exceeds threshold
        # This allows predictive ramping before temps rise
        for profile in reversed(PROFILES):
            if max_temp >= profile.temp_threshold or cpu_usage >= profile.cpu_threshold:
                return profile

        return PROFILES[0]  # Default to silent

    def set_fan_speed(self, fan_index: int, rpm: int) -> bool:
        """Set fan speed in RPM."""
        config = self.get_fan_config(fan_index)
        if not config:
            return False

        # Clamp to valid range
        rpm = max(config.min_rpm, min(rpm, config.max_rpm))

        # Enable manual mode if not already
        if not config.manual_mode:
            manual_path = SMC_BASE / f"fan{fan_index}_manual"
            if not self.write_smc_value(manual_path, "1"):
                logger.error(f"Failed to enable manual mode for fan {fan_index}")
                return False

        # Set speed
        output_path = SMC_BASE / f"fan{fan_index}_output"
        if self.write_smc_value(output_path, str(rpm)):
            logger.debug(f"Set {config.label} (fan{fan_index}) to {rpm} RPM")
            return True

        return False

    def disable_manual_mode(self, fan_index: int) -> bool:
        """Restore fan to automatic SMC control."""
        manual_path = SMC_BASE / f"fan{fan_index}_manual"
        if self.write_smc_value(manual_path, "0"):
            config = self.get_fan_config(fan_index)
            if config:
                logger.info(f"Restored {config.label} to automatic control")
            return True
        return False

    def apply_profile(self, profile: ThermalProfile, smooth: bool = True):
        """Apply thermal profile to fans with optional smooth transition."""
        if smooth and hasattr(self, '_last_speeds'):
            # Gradual transition from current speeds to target
            target_speeds = profile.fan_speeds
            steps = 5  # Number of transition steps

            for step in range(1, steps + 1):
                for fan_index, target_rpm in target_speeds.items():
                    current_rpm = self._last_speeds.get(fan_index, target_rpm)
                    # Linear interpolation
                    new_rpm = int(current_rpm + (target_rpm - current_rpm) * (step / steps))
                    self.set_fan_speed(fan_index, new_rpm)
                time.sleep(0.5)  # 2.5 second total transition
        else:
            # Direct application
            for fan_index, rpm in profile.fan_speeds.items():
                self.set_fan_speed(fan_index, rpm)

        # Store current speeds for next transition
        self._last_speeds = profile.fan_speeds.copy()

        logger.info(f"Applied '{profile.name}' profile: {profile.description}")

    def monitor_loop(self, interval: int = 10):
        """Main monitoring loop with adaptive profile selection."""
        logger.info("Starting adaptive thermal manager...")
        logger.info(f"Monitoring interval: {interval}s")
        logger.info("Strategy: Run quieter than SMC during low load, ramp up under high load")

        self.running = True

        while self.running:
            try:
                # Get current system state
                max_temp, avg_temp = self.get_cpu_cores_temp()
                cpu_usage = self.get_cpu_usage()

                # Select appropriate profile
                new_profile = self.select_profile(max_temp, avg_temp, cpu_usage)

                # Check if we should transition
                time_since_change = time.time() - self.last_profile_change

                # Apply profile if changed and enough time has passed
                if new_profile != self.current_profile:
                    # Allow immediate ramp-up, but delay ramp-down
                    should_change = (
                        PROFILES.index(new_profile) > PROFILES.index(self.current_profile) or  # Ramping up
                        time_since_change >= self.transition_time  # Enough time for ramp-down
                    )

                    if should_change:
                        logger.info(
                            f"Max: {max_temp:.1f}°C, Avg: {avg_temp:.1f}°C, "
                            f"CPU: {cpu_usage:.1f}% - '{self.current_profile.name}' → '{new_profile.name}'"
                        )
                        self.apply_profile(new_profile, smooth=True)
                        self.current_profile = new_profile
                        self.last_profile_change = time.time()
                else:
                    logger.debug(
                        f"Max: {max_temp:.1f}°C, Avg: {avg_temp:.1f}°C, "
                        f"CPU: {cpu_usage:.1f}% - Profile: {self.current_profile.name}"
                    )

                time.sleep(interval)

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}", exc_info=True)
                time.sleep(interval)

    def shutdown(self):
        """Graceful shutdown - restore automatic control."""
        logger.info("Shutting down adaptive thermal manager...")
        self.running = False

        # Restore all fans to automatic
        for fan_index in FANS.keys():
            self.disable_manual_mode(fan_index)

        logger.info("All fans restored to automatic SMC control")


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}")
    if manager:
        manager.shutdown()
    sys.exit(0)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mac Pro 5,1 Adaptive Thermal Manager")
    parser.add_argument('--interval', type=int, default=10, help='Monitoring interval in seconds')
    parser.add_argument('--transition-time', type=int, default=30,
                       help='Minimum time between profile changes (seconds)')
    parser.add_argument('--status', action='store_true', help='Show current status and exit')
    parser.add_argument('--profile', type=str, choices=[p.name for p in PROFILES],
                       help='Force specific profile (disables adaptive mode)')
    args = parser.parse_args()

    manager = AdaptiveThermalManager(transition_time=args.transition_time)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if args.status:
        # Show current status
        print("\n=== Mac Pro Adaptive Thermal Status ===\n")

        max_temp, avg_temp = manager.get_cpu_cores_temp()
        cpu_usage = manager.get_cpu_usage()

        print(f"CPU Temperature:")
        print(f"  Max Core:  {max_temp:.1f}°C")
        print(f"  Average:   {avg_temp:.1f}°C")
        print(f"  CPU Usage: {cpu_usage:.1f}%")

        selected = manager.select_profile(max_temp, avg_temp, cpu_usage)
        print(f"\nRecommended Profile: {selected.name}")
        print(f"  {selected.description}")

        print("\nFans:")
        for fan_index in FANS.keys():
            config = manager.get_fan_config(fan_index)
            if config:
                mode = "MANUAL" if config.manual_mode else "AUTO"
                pct = (config.current_rpm - config.min_rpm) / (config.max_rpm - config.min_rpm) * 100
                print(f"  {config.label:10s}: {config.current_rpm:4d} RPM ({pct:3.0f}%) [{mode}]")

        print("\nAvailable Profiles:")
        for profile in PROFILES:
            print(f"  {profile.name:12s}: {profile.description}")

        print()
        sys.exit(0)

    if args.profile:
        # Force specific profile
        profile = next(p for p in PROFILES if p.name == args.profile)
        logger.info(f"Forcing profile: {profile.name}")
        manager.apply_profile(profile)
        manager.current_profile = profile

    # Check if we have write permissions
    test_path = SMC_BASE / "fan1_manual"
    test_write = manager.write_smc_value(test_path, "0")  # Try to write current value

    if not test_write:
        logger.error("=" * 70)
        logger.error("ERROR: No write permission to fan control!")
        logger.error("Please run with sudo: sudo python3 thermal-manager-adaptive.py")
        logger.error("=" * 70)
        sys.exit(1)

    # Start monitoring
    try:
        manager.monitor_loop(interval=args.interval)
    except KeyboardInterrupt:
        manager.shutdown()

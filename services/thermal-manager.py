#!/usr/bin/env python3
"""
Mac Pro 5,1 Thermal Manager
============================

Monitors temperatures and adjusts fan speeds to prevent overheating.
Addresses elevated temps: TMTG 75°C, TN0D 75.5°C, TCBG 80°C, TeGG 85°C

Features:
- Monitors Apple SMC temperature sensors
- Adjusts fan speeds based on thermal zones
- Prevents CPU CRIT conditions
- Smooth transitions to avoid noise
- Automatic fallback to SMC control
"""

import time
import os
import logging
import signal
import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Apple SMC sysfs paths
SMC_BASE = Path("/sys/devices/platform/applesmc.768")

# Fan mapping (1-indexed in sysfs, 0 doesn't exist)
FANS = {
    1: "PCI",
    2: "PS",
    3: "EXHAUST",
    4: "INTAKE",
    5: "BOOSTA",
    # Note: fan5 (BOOSTB) may not be present on all configurations
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
    temp_threshold: float  # Activate when any sensor exceeds this
    fan_speeds: Dict[int, int]  # Fan index -> RPM

# Thermal profiles (conservative to aggressive)
PROFILES = [
    ThermalProfile(
        name="auto",
        temp_threshold=0,
        fan_speeds={}  # Let SMC handle it
    ),
    ThermalProfile(
        name="quiet",
        temp_threshold=60,
        fan_speeds={
            1: 1200,   # PCI
            2: 900,    # PS
            3: 1200,   # EXHAUST
            4: 1200,   # INTAKE
            5: 1200,   # BOOSTA
        }
    ),
    ThermalProfile(
        name="balanced",
        temp_threshold=70,
        fan_speeds={
            1: 2000,   # PCI
            2: 1400,   # PS
            3: 1800,   # EXHAUST
            4: 1800,   # INTAKE
            5: 2500,   # BOOSTA
        }
    ),
    ThermalProfile(
        name="performance",
        temp_threshold=75,
        fan_speeds={
            1: 3000,   # PCI
            2: 2000,   # PS
            3: 2400,   # EXHAUST
            4: 2400,   # INTAKE
            5: 3500,   # BOOSTA
        }
    ),
    ThermalProfile(
        name="emergency",
        temp_threshold=80,
        fan_speeds={
            1: 4000,   # PCI
            2: 2500,   # PS
            3: 2800,   # EXHAUST
            4: 2800,   # INTAKE
            5: 4500,   # BOOSTA
        }
    ),
]


class ThermalManager:
    """Mac Pro thermal management system."""

    def __init__(self):
        self.running = False
        self.current_profile = PROFILES[0]  # Start with auto

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

    def get_all_fans(self) -> Dict[int, FanConfig]:
        """Get all fan configurations."""
        fans = {}
        for fan_index in FANS.keys():
            config = self.get_fan_config(fan_index)
            if config:
                fans[fan_index] = config
        return fans

    def get_temperatures(self) -> Dict[str, float]:
        """Get all temperature sensors."""
        temps = {}

        # Read all temp* files
        for temp_file in SMC_BASE.glob("temp*_input"):
            # Get sensor label
            label_file = temp_file.parent / temp_file.name.replace("_input", "_label")
            label = self.read_smc_value(label_file)
            if not label:
                continue

            # Read temperature (in millidegrees)
            temp_value = self.read_smc_value(temp_file)
            if temp_value:
                try:
                    temps[label] = int(temp_value) / 1000.0
                except ValueError:
                    continue

        return temps

    def get_max_temp(self) -> float:
        """Get highest temperature across all sensors."""
        temps = self.get_temperatures()
        return max(temps.values()) if temps else 0.0

    def select_profile(self, max_temp: float) -> ThermalProfile:
        """Select appropriate thermal profile based on temperature."""
        # Find highest profile where temp exceeds threshold
        for profile in reversed(PROFILES):
            if max_temp >= profile.temp_threshold:
                return profile
        return PROFILES[0]  # Default to auto

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
            logger.info(f"Set {config.label} (fan{fan_index}) to {rpm} RPM")
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

    def apply_profile(self, profile: ThermalProfile):
        """Apply thermal profile to fans."""
        if profile.name == "auto":
            # Restore all fans to automatic
            for fan_index in FANS.keys():
                self.disable_manual_mode(fan_index)
            logger.info("Restored all fans to automatic SMC control")
        else:
            # Set manual speeds
            for fan_index, rpm in profile.fan_speeds.items():
                self.set_fan_speed(fan_index, rpm)
            logger.info(f"Applied '{profile.name}' thermal profile")

    def monitor_loop(self, interval: int = 10):
        """Main monitoring loop."""
        logger.info("Starting thermal manager...")
        logger.info(f"Monitoring interval: {interval}s")

        self.running = True

        while self.running:
            try:
                # Get current temps
                temps = self.get_temperatures()
                max_temp = max(temps.values()) if temps else 0.0

                # Select appropriate profile
                new_profile = self.select_profile(max_temp)

                # Apply profile if changed
                if new_profile != self.current_profile:
                    logger.info(f"Max temp: {max_temp:.1f}°C - Switching to '{new_profile.name}' profile")
                    self.apply_profile(new_profile)
                    self.current_profile = new_profile
                else:
                    logger.debug(f"Max temp: {max_temp:.1f}°C - Profile: {self.current_profile.name}")

                # Log critical temps
                for sensor, temp in temps.items():
                    if temp >= 85:
                        logger.warning(f"CRITICAL: {sensor} at {temp:.1f}°C!")
                    elif temp >= 80:
                        logger.warning(f"HIGH: {sensor} at {temp:.1f}°C")

                time.sleep(interval)

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}", exc_info=True)
                time.sleep(interval)

    def shutdown(self):
        """Graceful shutdown - restore automatic control."""
        logger.info("Shutting down thermal manager...")
        self.running = False

        # Restore all fans to automatic
        for fan_index in FANS.keys():
            self.disable_manual_mode(fan_index)

        logger.info("All fans restored to automatic control")


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}")
    if manager:
        manager.shutdown()
    sys.exit(0)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mac Pro 5,1 Thermal Manager")
    parser.add_argument('--interval', type=int, default=10, help='Monitoring interval in seconds')
    parser.add_argument('--profile', type=str, choices=[p.name for p in PROFILES],
                       help='Force specific profile (disables auto-switching)')
    parser.add_argument('--status', action='store_true', help='Show current status and exit')
    args = parser.parse_args()

    manager = ThermalManager()

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if args.status:
        # Show current status
        print("\n=== Mac Pro Thermal Status ===\n")

        temps = manager.get_temperatures()
        print("Temperatures:")
        for sensor, temp in sorted(temps.items()):
            status = "CRIT" if temp >= 85 else "HIGH" if temp >= 80 else "OK"
            print(f"  {sensor:10s}: {temp:5.1f}°C [{status}]")

        print(f"\nMax Temperature: {max(temps.values()):.1f}°C")

        print("\nFans:")
        fans = manager.get_all_fans()
        for fan_index, config in fans.items():
            mode = "MANUAL" if config.manual_mode else "AUTO"
            pct = (config.current_rpm - config.min_rpm) / (config.max_rpm - config.min_rpm) * 100
            print(f"  {config.label:10s}: {config.current_rpm:4d} RPM ({pct:3.0f}%) [{mode}] (range: {config.min_rpm}-{config.max_rpm})")

        print()
        sys.exit(0)

    if args.profile:
        # Force specific profile
        profile = next(p for p in PROFILES if p.name == args.profile)
        logger.info(f"Forcing profile: {profile.name}")
        manager.apply_profile(profile)
        manager.current_profile = profile

    # Start monitoring
    try:
        manager.monitor_loop(interval=args.interval)
    except KeyboardInterrupt:
        manager.shutdown()

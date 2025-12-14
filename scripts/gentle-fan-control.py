#!/usr/bin/env python3
"""
Intelligent Fan Control for Mac Pro 5,1
Monitors sustained load and adjusts fan curves intelligently
- Keeps fans low during normal/idle usage
- Gradually increases during sustained high load
- Considers temperature trends, not just current values
"""

import time
import re
import subprocess
import sys
import os

# Unbuffer stdout for systemd logging
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


class IntelligentFanControl:
    def __init__(self):
        self.applesmc_path = "/sys/devices/platform/applesmc.768"
        self.update_interval = 5  # seconds

        # Fan configuration with intelligent multi-tier curves (ULTRA QUIET)
        # Format: (min_rpm, normal_max, sustained_max, temp_low, temp_normal, temp_high)
        # Optimized for minimal noise while maintaining safe cooling
        self.fan_config = {
            1: {"name": "PCI", "min": 800, "normal_max": 1400, "sustained_max": 2800, "temp_low": 50, "temp_normal": 68, "temp_high": 80},
            2: {"name": "PS", "min": 600, "normal_max": 900, "sustained_max": 1600, "temp_low": 50, "temp_normal": 68, "temp_high": 80},
            3: {"name": "EXHAUST", "min": 600, "normal_max": 900, "sustained_max": 1600, "temp_low": 50, "temp_normal": 68, "temp_high": 80},
            4: {"name": "INTAKE", "min": 600, "normal_max": 900, "sustained_max": 1600, "temp_low": 50, "temp_normal": 68, "temp_high": 80},
            5: {"name": "BOOSTA", "min": 800, "normal_max": 1400, "sustained_max": 3200, "temp_low": 50, "temp_normal": 68, "temp_high": 80},
            6: {"name": "BOOSTB", "min": 800, "normal_max": 1400, "sustained_max": 3200, "temp_low": 50, "temp_normal": 68, "temp_high": 80},
        }

        # Temperature smoothing (moving average) - longer for quieter response
        self.temp_history = []
        self.temp_history_size = 24  # 120 seconds of history at 5s intervals (doubled for smoother response)

        # Load detection - less aggressive triggering
        self.high_temp_duration = 0  # How long temps have been elevated
        self.sustained_load_threshold = 120  # seconds before considering it sustained (doubled from 60)
        self.load_decay_rate = 8  # How many seconds to decay per update when cooling (increased from 5)

        # Per-fan control (allow individual fan adjustment)
        self.fan_last_update = {i: 0 for i in range(1, 7)}

    def get_max_cpu_temp(self):
        """Get maximum CPU temperature across all cores"""
        try:
            result = subprocess.run(['sensors'], capture_output=True, text=True)
            temps = []
            for line in result.stdout.split('\n'):
                if 'Core' in line and '°C' in line:
                    match = re.search(r'\+(\d+\.\d+)°C', line)
                    if match:
                        temps.append(float(match.group(1)))
            return max(temps) if temps else 45.0
        except Exception as e:
            print(f"Error reading temperature: {e}", file=sys.stderr)
            return 45.0  # Safe default

    def get_cpu_load(self):
        """Get average CPU load percentage"""
        try:
            with open('/proc/loadavg', 'r') as f:
                load_avg = float(f.read().split()[0])
            # Normalize to percentage (assuming 24 cores)
            cpu_cores = os.cpu_count() or 24
            return min((load_avg / cpu_cores) * 100, 100)
        except Exception as e:
            print(f"Error reading CPU load: {e}", file=sys.stderr)
            return 0.0

    def smooth_temperature(self, temp):
        """Apply moving average to temperature readings"""
        self.temp_history.append(temp)
        if len(self.temp_history) > self.temp_history_size:
            self.temp_history.pop(0)
        return sum(self.temp_history) / len(self.temp_history)

    def get_temp_trend(self):
        """Calculate temperature trend (°C per minute)"""
        if len(self.temp_history) < 2:
            return 0.0
        # Calculate slope over last minute
        recent_temps = self.temp_history[-12:]  # Last 60 seconds
        if len(recent_temps) < 2:
            return 0.0
        slope = (recent_temps[-1] - recent_temps[0]) / len(recent_temps)
        return slope * 12  # Convert to °C per minute

    def update_load_state(self, current_temp, smoothed_temp):
        """Track sustained high load periods (quieter thresholds)"""
        # Consider it high load if smoothed temp > 60°C AND trending up
        # OR if temp is very high (>70°C) regardless of trend
        temp_trend = self.get_temp_trend()
        is_high_load = (smoothed_temp > 60 and temp_trend > 3) or smoothed_temp > 70

        # More aggressive decay when temperature is low
        if is_high_load:
            self.high_temp_duration += self.update_interval
        else:
            # Much faster decay when temps are well below threshold
            if smoothed_temp < 50:
                decay_rate = self.load_decay_rate * 3  # Triple decay when idle
            elif smoothed_temp < 58:
                decay_rate = self.load_decay_rate * 2  # Double decay when cool
            else:
                decay_rate = self.load_decay_rate
            self.high_temp_duration = max(0, self.high_temp_duration - decay_rate)

        return self.high_temp_duration >= self.sustained_load_threshold

    def calculate_fan_speed(self, temp, fan_num, is_sustained_load):
        """Calculate target fan speed based on temperature and load state"""
        config = self.fan_config[fan_num]

        # Smooth temperature to avoid sudden changes
        smoothed_temp = self.smooth_temperature(temp)

        # Choose max speed based on load duration
        max_rpm = config["sustained_max"] if is_sustained_load else config["normal_max"]

        # Three-tier temperature zones with gentle transitions
        if smoothed_temp <= config["temp_low"]:
            # Idle zone: minimum RPM
            return config["min"]
        elif smoothed_temp >= config["temp_high"]:
            # Hot zone: max RPM for current load state
            return max_rpm
        elif smoothed_temp <= config["temp_normal"]:
            # Normal zone: gentle ramp from min to 50% of max
            temp_range = config["temp_normal"] - config["temp_low"]
            temp_position = (smoothed_temp - config["temp_low"]) / temp_range
            curve_factor = temp_position ** 0.6  # Very gentle curve
            speed_range = (max_rpm * 0.5) - config["min"]
            target_speed = config["min"] + (speed_range * curve_factor)
            return int(target_speed)
        else:
            # Warm zone: ramp from 50% to 100% of max
            temp_range = config["temp_high"] - config["temp_normal"]
            temp_position = (smoothed_temp - config["temp_normal"]) / temp_range
            curve_factor = temp_position ** 0.8  # Slightly steeper but still gentle
            speed_range = max_rpm * 0.5
            target_speed = (max_rpm * 0.5) + (speed_range * curve_factor)
            return int(target_speed)

    def set_fan_speed(self, fan_num, rpm):
        """Set fan speed via sysfs"""
        try:
            # Enable manual control
            with open(f"{self.applesmc_path}/fan{fan_num}_manual", 'w') as f:
                f.write('1')

            # Set target speed
            with open(f"{self.applesmc_path}/fan{fan_num}_output", 'w') as f:
                f.write(str(rpm))

            return True
        except Exception as e:
            print(f"Error setting fan {fan_num} speed: {e}", file=sys.stderr)
            return False

    def get_current_fan_speed(self, fan_num):
        """Read current fan speed"""
        try:
            with open(f"{self.applesmc_path}/fan{fan_num}_input", 'r') as f:
                return int(f.read().strip())
        except Exception as e:
            print(f"Error reading fan {fan_num} speed: {e}", file=sys.stderr)
            return 0

    def run(self):
        """Main control loop"""
        print("Starting intelligent fan control for Mac Pro 5,1")
        print("=" * 70)
        print("Intelligent load-based fan control (ULTRA QUIET MODE):")
        print("  • Normal usage: Max 1400 RPM (PCI/BOOST), 900 RPM (others)")
        print("  • Sustained load (>120s high temp): Max 2800-3200 RPM")
        print("  • Temperature zones:")
        print("    - Idle (<50°C): Minimum RPM")
        print("    - Normal (50-68°C): Gentle ramp to 50% max")
        print("    - Warm (68-80°C): Moderate ramp to 100% max")
        print("    - Hot (>80°C): Maximum RPM for current load state")
        print("=" * 70)

        iteration = 0
        try:
            while True:
                # Get current temperature and load
                current_temp = self.get_max_cpu_temp()
                cpu_load = self.get_cpu_load()
                smoothed_temp = current_temp if not self.temp_history else sum(self.temp_history) / len(self.temp_history)

                # Update load state
                is_sustained_load = self.update_load_state(current_temp, smoothed_temp)

                # Update fan speeds
                for fan_num in range(1, 7):
                    target_rpm = self.calculate_fan_speed(current_temp, fan_num, is_sustained_load)
                    current_rpm = self.get_current_fan_speed(fan_num)

                    # Only update if change is significant (>50 RPM) to reduce writes
                    # But allow slower fans to update more eagerly when cooling
                    threshold = 50 if target_rpm > current_rpm else 75

                    if abs(target_rpm - current_rpm) > threshold:
                        self.set_fan_speed(fan_num, target_rpm)
                        if iteration % 12 == 0:  # Print every minute
                            print(f"  Fan {fan_num} ({self.fan_config[fan_num]['name']:8}): "
                                  f"{current_rpm:4} -> {target_rpm:4} RPM")

                # Status update every minute
                if iteration % 12 == 0:
                    temp_trend = self.get_temp_trend()
                    load_state = "SUSTAINED LOAD" if is_sustained_load else "normal"
                    print(f"\n[{time.strftime('%H:%M:%S')}] "
                          f"Temp: {current_temp:.1f}°C (avg: {smoothed_temp:.1f}°C, "
                          f"trend: {temp_trend:+.1f}°C/min)")
                    print(f"  CPU Load: {cpu_load:.1f}% | "
                          f"High temp duration: {self.high_temp_duration:.0f}s | "
                          f"Mode: {load_state}")
                    print("-" * 70)

                iteration += 1
                time.sleep(self.update_interval)

        except KeyboardInterrupt:
            print("\nStopping intelligent fan control")
            print("Fans will remain at current speeds (manual mode)")
            print("To restore automatic control, run:")
            print("  sudo systemctl stop gentle-fan-control.service")


if __name__ == "__main__":
    controller = IntelligentFanControl()
    controller.run()

#!/usr/bin/env python3
"""
Phoenix Monitor - Proactive Background System Monitoring

Continuously monitors system health and provides:
- Service health checking
- Auto-healing
- Resource monitoring
- Event-driven alerts
- Learning pattern detection

This is Phoenix's "always-on" awareness system.
"""

import time
import json
import signal
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import threading

# Import our direct modules
from env_check import EnvironmentMonitor
from system_control import SystemControl
from direct_voice import DirectVoice


class PhoenixMonitor:
    """Continuous system monitoring and auto-healing"""

    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval  # seconds
        self.running = False
        self.env_monitor = EnvironmentMonitor()
        self.system_control = SystemControl()
        self.voice = DirectVoice()

        self.state_file = Path("/tmp/phoenix_monitor_state.json")
        self.log_file = Path("/tmp/phoenix_monitor.log")

        # State tracking
        self.last_state = None
        self.failure_counts = {}
        self.alert_history = []

        # Auto-heal configuration
        self.auto_heal_enabled = True
        self.max_heal_attempts = 3

    def log(self, message: str, level: str = "INFO"):
        """Log message to file"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{level}] {message}\n"

        with open(self.log_file, 'a') as f:
            f.write(log_entry)

        print(log_entry.rstrip())

    def save_state(self, state: Dict[str, Any]):
        """Save current state to file"""
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def load_state(self) -> Optional[Dict[str, Any]]:
        """Load previous state"""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    return json.load(f)
            except:
                return None
        return None

    def check_services(self) -> Dict[str, bool]:
        """Check all critical services"""
        status = self.env_monitor.get_service_status()

        critical_services = {
            "whisper_stt": 2022,
            "kokoro_tts": 8880,
            "livekit_server": 7880
        }

        return {name: status.get(name, False) for name in critical_services}

    def auto_heal_service(self, service_name: str) -> bool:
        """Attempt to heal a failed service"""
        # Check failure count
        count = self.failure_counts.get(service_name, 0)

        if count >= self.max_heal_attempts:
            self.log(f"Service {service_name} exceeded max heal attempts ({self.max_heal_attempts})", "ERROR")
            return False

        self.log(f"Attempting to heal {service_name} (attempt {count + 1})", "WARN")

        success = False

        if service_name == "whisper_stt":
            success = self.system_control.restart_whisper()
        elif service_name == "kokoro_tts":
            success = self.system_control.restart_kokoro()
        elif service_name == "livekit_server":
            success = self.system_control.restart_livekit()

        if success:
            self.log(f"Successfully healed {service_name}", "INFO")
            self.failure_counts[service_name] = 0
        else:
            self.failure_counts[service_name] = count + 1
            self.log(f"Failed to heal {service_name}", "ERROR")

        return success

    def detect_changes(self, current_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect significant changes from last state"""
        changes = []

        if self.last_state is None:
            return changes

        # Check service changes
        last_services = self.last_state.get('services', {})
        current_services = current_state.get('services', {})

        for service, is_running in current_services.items():
            was_running = last_services.get(service, False)

            if was_running and not is_running:
                changes.append({
                    "type": "service_down",
                    "service": service,
                    "timestamp": datetime.now().isoformat()
                })
            elif not was_running and is_running:
                changes.append({
                    "type": "service_up",
                    "service": service,
                    "timestamp": datetime.now().isoformat()
                })

        # Check resource changes (significant only)
        last_cpu = self.last_state.get('system', {}).get('cpu_percent', 0)
        current_cpu = current_state.get('system', {}).get('cpu_percent', 0)

        if abs(current_cpu - last_cpu) > 30:  # >30% change
            changes.append({
                "type": "cpu_spike",
                "from": last_cpu,
                "to": current_cpu,
                "timestamp": datetime.now().isoformat()
            })

        last_memory = self.last_state.get('system', {}).get('memory_percent', 0)
        current_memory = current_state.get('system', {}).get('memory_percent', 0)

        if current_memory > 90 and last_memory <= 90:
            changes.append({
                "type": "memory_high",
                "percent": current_memory,
                "timestamp": datetime.now().isoformat()
            })

        return changes

    def handle_changes(self, changes: List[Dict[str, Any]]):
        """Handle detected changes"""
        for change in changes:
            change_type = change['type']

            if change_type == "service_down":
                service = change['service']
                self.log(f"Service down detected: {service}", "WARN")

                if self.auto_heal_enabled:
                    self.auto_heal_service(service)

            elif change_type == "service_up":
                service = change['service']
                self.log(f"Service restored: {service}", "INFO")
                # Reset failure count
                self.failure_counts[service] = 0

            elif change_type == "cpu_spike":
                self.log(f"CPU spike: {change['from']:.1f}% → {change['to']:.1f}%", "WARN")

            elif change_type == "memory_high":
                self.log(f"High memory usage: {change['percent']:.1f}%", "WARN")

    def monitor_cycle(self):
        """Single monitoring cycle"""
        try:
            # Get current state
            current_state = self.env_monitor.get_complete_status()

            # Save state
            self.save_state(current_state)

            # Detect changes
            changes = self.detect_changes(current_state)

            if changes:
                self.handle_changes(changes)

            # Store current as last
            self.last_state = current_state

            # Log health status
            services = self.check_services()
            healthy_count = sum(1 for v in services.values() if v)
            total_count = len(services)

            self.log(f"Health check: {healthy_count}/{total_count} services running")

        except Exception as e:
            self.log(f"Monitor cycle error: {e}", "ERROR")

    def run(self):
        """Main monitoring loop"""
        self.running = True
        self.log("Phoenix Monitor starting...", "INFO")

        # Load previous state if exists
        self.last_state = self.load_state()

        self.log(f"Monitoring interval: {self.check_interval}s", "INFO")
        self.log(f"Auto-heal enabled: {self.auto_heal_enabled}", "INFO")

        try:
            while self.running:
                self.monitor_cycle()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            self.log("Received interrupt signal", "INFO")
        finally:
            self.stop()

    def stop(self):
        """Stop monitoring"""
        self.running = False
        self.log("Phoenix Monitor stopped", "INFO")

    def status(self) -> Dict[str, Any]:
        """Get monitor status"""
        return {
            "running": self.running,
            "check_interval": self.check_interval,
            "auto_heal_enabled": self.auto_heal_enabled,
            "failure_counts": self.failure_counts,
            "last_check": self.last_state.get('timestamp') if self.last_state else None
        }


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\nReceived shutdown signal")
    sys.exit(0)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Phoenix Monitor - Continuous System Monitoring")
    parser.add_argument('--interval', type=int, default=60, help="Check interval in seconds")
    parser.add_argument('--no-heal', action='store_true', help="Disable auto-healing")
    parser.add_argument('--daemon', action='store_true', help="Run as background daemon")
    parser.add_argument('--status', action='store_true', help="Show monitor status")

    args = parser.parse_args()

    if args.status:
        # Show status from state file
        state_file = Path("/tmp/phoenix_monitor_state.json")
        if state_file.exists():
            with open(state_file) as f:
                state = json.load(f)
                print(json.dumps(state, indent=2))
        else:
            print("Monitor not running or no state file found")
        sys.exit(0)

    # Setup signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Create monitor
    monitor = PhoenixMonitor(check_interval=args.interval)

    if args.no_heal:
        monitor.auto_heal_enabled = False

    if args.daemon:
        # Daemonize
        import daemon
        with daemon.DaemonContext():
            monitor.run()
    else:
        # Run in foreground
        monitor.run()

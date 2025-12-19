#!/usr/bin/env python3
"""
System Control Module
Direct service management and self-healing for Phoenix

Provides Phoenix with ability to:
- Restart services
- Check logs
- Manage ports
- Self-heal issues
- Autonomous maintenance
"""

import subprocess
import requests
import socket
import time
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


class SystemControl:
    """Direct system control without MCP dependencies"""

    def __init__(self):
        self.home = Path.home()
        self.voicemode_home = self.home / ".voicemode"
        self.logs_dir = self.voicemode_home / "logs"
        self.services_dir = self.voicemode_home / "services"

    # ==================== SERVICE MANAGEMENT ====================

    def restart_whisper(self) -> bool:
        """Restart Whisper STT service"""
        try:
            # Check if service file exists
            service_plist = self.home / "Library/LaunchAgents/com.voicemode.whisper.plist"

            if service_plist.exists():
                # Use launchctl
                subprocess.run(['launchctl', 'stop', 'com.voicemode.whisper'], timeout=5)
                time.sleep(1)
                subprocess.run(['launchctl', 'start', 'com.voicemode.whisper'], timeout=5)
                time.sleep(2)
            else:
                # Direct restart - find and kill, then start
                self.kill_port(2022)
                time.sleep(1)
                self.start_whisper()

            # Verify it's running
            time.sleep(2)
            return self.check_port(2022)
        except Exception as e:
            print(f"❌ Failed to restart Whisper: {e}")
            return False

    def start_whisper(self) -> bool:
        """Start Whisper service"""
        try:
            whisper_bin = self.services_dir / "whisper" / "server"

            if whisper_bin.exists():
                subprocess.Popen(
                    [str(whisper_bin), '--port', '2022', '--model', 'ggml-small.bin'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                time.sleep(3)
                return self.check_port(2022)
        except Exception as e:
            print(f"❌ Failed to start Whisper: {e}")
            return False

    def restart_kokoro(self, port: int = 8880) -> bool:
        """Restart Kokoro TTS service"""
        try:
            service_name = f"com.voicemode.kokoro.{port}"
            service_plist = self.home / f"Library/LaunchAgents/{service_name}.plist"

            if service_plist.exists():
                subprocess.run(['launchctl', 'stop', service_name], timeout=5)
                time.sleep(1)
                subprocess.run(['launchctl', 'start', service_name], timeout=5)
                time.sleep(2)
            else:
                self.kill_port(port)
                time.sleep(1)
                # Kokoro restart would need specific command

            time.sleep(2)
            return self.check_port(port)
        except Exception as e:
            print(f"❌ Failed to restart Kokoro: {e}")
            return False

    def restart_livekit(self) -> bool:
        """Restart LiveKit server"""
        try:
            service_name = "com.voicemode.livekit"
            service_plist = self.home / f"Library/LaunchAgents/{service_name}.plist"

            if service_plist.exists():
                subprocess.run(['launchctl', 'stop', service_name], timeout=5)
                time.sleep(1)
                subprocess.run(['launchctl', 'start', service_name], timeout=5)
                time.sleep(2)
            else:
                self.kill_port(7880)

            time.sleep(2)
            return self.check_port(7880)
        except Exception as e:
            print(f"❌ Failed to restart LiveKit: {e}")
            return False

    # ==================== LOG MANAGEMENT ====================

    def get_service_logs(self, service_name: str, lines: int = 50) -> List[str]:
        """Get recent logs for a service"""
        log_file = self.logs_dir / service_name / "current.log"

        if not log_file.exists():
            # Try alternate locations
            alt_log = self.logs_dir / f"{service_name}.log"
            if alt_log.exists():
                log_file = alt_log
            else:
                return [f"Log file not found: {log_file}"]

        try:
            with open(log_file) as f:
                all_lines = f.readlines()
                return all_lines[-lines:] if len(all_lines) > lines else all_lines
        except Exception as e:
            return [f"Error reading logs: {e}"]

    def tail_logs(self, service_name: str, lines: int = 20):
        """Print recent logs for a service"""
        logs = self.get_service_logs(service_name, lines)
        print(f"\n=== {service_name} logs (last {lines} lines) ===\n")
        for line in logs:
            print(line.rstrip())

    # ==================== PORT MANAGEMENT ====================

    def check_port(self, port: int, timeout: float = 0.5) -> bool:
        """Check if port is listening"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                return s.connect_ex(('127.0.0.1', port)) == 0
        except:
            return False

    def kill_port(self, port: int) -> bool:
        """Kill process listening on port"""
        try:
            # Use lsof to find process
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True,
                timeout=5
            )

            if result.returncode == 0:
                pids = result.stdout.decode().strip().split('\n')
                for pid in pids:
                    if pid:
                        subprocess.run(['kill', '-9', pid], timeout=2)
                        print(f"✅ Killed process {pid} on port {port}")
                return True
            else:
                print(f"ℹ️  No process found on port {port}")
                return True
        except Exception as e:
            print(f"❌ Failed to kill port {port}: {e}")
            return False

    def find_available_port(self, start: int = 9000, end: int = 9999) -> Optional[int]:
        """Find first available port in range"""
        try:
            # Try Port Manager API first
            response = requests.get(
                'http://localhost:4102/api/ports/find',
                params={'start': start, 'end': end},
                timeout=2
            )
            if response.ok:
                return response.json().get('port')
        except:
            pass

        # Fallback: manual check
        for port in range(start, end + 1):
            if not self.check_port(port, timeout=0.1):
                return port

        return None

    def get_port_info(self, port: int) -> Optional[Dict[str, Any]]:
        """Get info about what's using a port"""
        try:
            result = subprocess.run(
                ['lsof', '-i', f':{port}', '-n', '-P'],
                capture_output=True,
                timeout=5
            )

            if result.returncode == 0:
                lines = result.stdout.decode().strip().split('\n')
                if len(lines) > 1:
                    # Parse lsof output
                    header = lines[0]
                    data = lines[1].split()
                    return {
                        "command": data[0],
                        "pid": int(data[1]),
                        "user": data[2],
                        "listening": True
                    }
        except:
            pass

        return None

    # ==================== SELF-HEALING ====================

    def auto_heal_voice_services(self) -> Dict[str, bool]:
        """Check and restart any failed voice services"""
        results = {}

        # Check Whisper
        if not self.check_port(2022):
            print("🔧 Whisper down, attempting restart...")
            results['whisper'] = self.restart_whisper()
        else:
            results['whisper'] = True

        # Check Kokoro
        if not self.check_port(8880):
            print("🔧 Kokoro down, attempting restart...")
            results['kokoro'] = self.restart_kokoro(8880)
        else:
            results['kokoro'] = True

        # Check LiveKit
        if not self.check_port(7880):
            print("🔧 LiveKit down, attempting restart...")
            results['livekit'] = self.restart_livekit()
        else:
            results['livekit'] = True

        return results

    def verify_environment(self) -> Dict[str, Any]:
        """Comprehensive environment verification"""
        issues = []
        recommendations = []

        # Check voice services
        services = {
            "whisper": 2022,
            "kokoro": 8880,
            "livekit": 7880
        }

        for name, port in services.items():
            if not self.check_port(port):
                issues.append(f"{name} not running on port {port}")
                recommendations.append(f"Run: self.restart_{name}()")

        # Check audio devices
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            input_devices = sum(1 for i in range(p.get_device_count())
                              if p.get_device_info_by_index(i)['maxInputChannels'] > 0)
            p.terminate()

            if input_devices == 0:
                issues.append("No audio input devices found")
                recommendations.append("Check audio device connections")
        except:
            issues.append("PyAudio not available")

        # Check disk space
        try:
            import psutil
            for partition in psutil.disk_partitions():
                usage = psutil.disk_usage(partition.mountpoint)
                if usage.percent > 90:
                    issues.append(f"{partition.mountpoint} disk usage at {usage.percent}%")
                    recommendations.append(f"Free up space on {partition.mountpoint}")
        except:
            pass

        return {
            "timestamp": datetime.now().isoformat(),
            "healthy": len(issues) == 0,
            "issues": issues,
            "recommendations": recommendations
        }

    # ==================== AUTONOMOUS MAINTENANCE ====================

    def perform_maintenance(self) -> Dict[str, Any]:
        """Perform routine maintenance tasks"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "tasks": []
        }

        # 1. Clean old logs (older than 7 days)
        try:
            result = subprocess.run(
                ['find', str(self.logs_dir), '-name', '*.log', '-mtime', '+7', '-delete'],
                capture_output=True,
                timeout=10
            )
            results['tasks'].append({
                "name": "clean_old_logs",
                "success": result.returncode == 0,
                "message": "Cleaned logs older than 7 days"
            })
        except Exception as e:
            results['tasks'].append({
                "name": "clean_old_logs",
                "success": False,
                "error": str(e)
            })

        # 2. Check and heal services
        heal_results = self.auto_heal_voice_services()
        results['tasks'].append({
            "name": "heal_services",
            "success": all(heal_results.values()),
            "details": heal_results
        })

        # 3. Verify environment
        env_check = self.verify_environment()
        results['tasks'].append({
            "name": "verify_environment",
            "success": env_check['healthy'],
            "issues": env_check['issues'],
            "recommendations": env_check['recommendations']
        })

        return results


# ==================== CONVENIENCE FUNCTIONS ====================

def quick_restart_voice() -> Dict[str, bool]:
    """Quick function to restart all voice services"""
    control = SystemControl()
    return control.auto_heal_voice_services()


def quick_maintenance() -> Dict[str, Any]:
    """Quick function for maintenance"""
    control = SystemControl()
    return control.perform_maintenance()


def quick_verify() -> Dict[str, Any]:
    """Quick function for environment verification"""
    control = SystemControl()
    return control.verify_environment()


if __name__ == '__main__':
    import sys
    import json

    control = SystemControl()

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 system_control.py restart whisper|kokoro|livekit")
        print("  python3 system_control.py heal            # Auto-heal all services")
        print("  python3 system_control.py verify          # Verify environment")
        print("  python3 system_control.py maintenance     # Perform maintenance")
        print("  python3 system_control.py logs <service>  # View logs")
        print("  python3 system_control.py port <port>     # Check port info")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'restart':
        if len(sys.argv) < 3:
            print("Specify service: whisper, kokoro, or livekit")
            sys.exit(1)

        service = sys.argv[2]
        if service == 'whisper':
            success = control.restart_whisper()
        elif service == 'kokoro':
            success = control.restart_kokoro()
        elif service == 'livekit':
            success = control.restart_livekit()
        else:
            print(f"Unknown service: {service}")
            sys.exit(1)

        print(f"{'✅' if success else '❌'} Restart {'successful' if success else 'failed'}")

    elif command == 'heal':
        results = control.auto_heal_voice_services()
        print("\nAuto-Heal Results:")
        for service, success in results.items():
            print(f"  {'✅' if success else '❌'} {service}")

    elif command == 'verify':
        results = control.verify_environment()
        print(json.dumps(results, indent=2))

    elif command == 'maintenance':
        results = control.perform_maintenance()
        print(json.dumps(results, indent=2))

    elif command == 'logs':
        if len(sys.argv) < 3:
            print("Specify service name")
            sys.exit(1)
        control.tail_logs(sys.argv[2])

    elif command == 'port':
        if len(sys.argv) < 3:
            print("Specify port number")
            sys.exit(1)
        port_info = control.get_port_info(int(sys.argv[2]))
        print(json.dumps(port_info, indent=2) if port_info else "Port not in use")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

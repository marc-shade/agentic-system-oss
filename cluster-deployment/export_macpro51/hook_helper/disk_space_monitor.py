#!/usr/bin/env python3
"""
Disk Space Monitoring Daemon
Monitors disk usage and triggers cleanup when thresholds are exceeded
Integrates with health daemon
"""

import subprocess
import time
import json
import os
from datetime import datetime
from pathlib import Path

class DiskSpaceMonitor:
    def __init__(self):
        self.home = Path.home()
        self.claude_home = self.home / ".claude"
        self.status_file = self.claude_home / "disk_space_status.json"
        self.log_file = self.claude_home / "disk_space_monitor.log"

        # Thresholds
        self.warning_threshold = 80  # percent
        self.critical_threshold = 90  # percent
        self.cleanup_threshold = 85  # percent

        # Check interval
        self.check_interval = 300  # 5 minutes

        # Auto-cleanup enabled
        self.auto_cleanup = True

    def log(self, message):
        """Log message to file"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {message}\n"
        with open(self.log_file, 'a') as f:
            f.write(log_entry)
        print(log_entry.strip())

    def get_disk_usage(self, path="/"):
        """Get disk usage percentage for a path"""
        try:
            result = subprocess.run(
                ['df', '-h', path],
                capture_output=True,
                text=True,
                timeout=5
            )
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                usage_str = parts[4].strip('%')
                return int(usage_str)
        except:
            return -1

    def get_directory_sizes(self):
        """Get sizes of key directories"""
        sizes = {}
        directories = {
            'claude_total': self.home / ".claude",
            'file_history': self.home / ".claude" / "file-history",
            'qdrant': self.home / ".claude" / "qdrant_storage",
            'phoenix_voice': self.home / ".claude" / "phoenix-voice",
            'voicemode_total': self.home / ".voicemode",
            'audio': self.home / ".voicemode" / "audio",
            'logs': self.home / ".voicemode" / "logs",
        }

        for name, path in directories.items():
            if path.exists():
                try:
                    result = subprocess.run(
                        ['du', '-sh', str(path)],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    size_str = result.stdout.split('\t')[0]
                    sizes[name] = size_str
                except:
                    sizes[name] = "unknown"
            else:
                sizes[name] = "0B"

        return sizes

    def run_cleanup(self):
        """Run cleanup script with proper failure detection (Codex Review Fix)"""
        cleanup_script = self.claude_home / "disk_cleanup.sh"
        if cleanup_script.exists():
            try:
                self.log("🧹 Running automatic cleanup...")
                result = subprocess.run(
                    ['bash', str(cleanup_script)],
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                # Check exit code (Codex Review Fix)
                if result.returncode != 0:
                    self.log(f"❌ Cleanup failed with exit code {result.returncode}")
                    if result.stderr:
                        self.log(f"stderr: {result.stderr[:500]}")  # Limit stderr output
                    self.emit_alert("cleanup_failed", {
                        "exit_code": result.returncode,
                        "stderr": result.stderr[:500] if result.stderr else ""
                    })
                    return False

                self.log(f"✅ Cleanup completed successfully")
                # Log amount of space freed if available in stdout
                if "Total freed:" in result.stdout:
                    for line in result.stdout.split('\n'):
                        if "Total freed:" in line:
                            self.log(f"📊 {line.strip()}")
                            break
                return True

            except subprocess.TimeoutExpired:
                self.log(f"⚠️ Cleanup timed out after 300s")
                self.emit_alert("cleanup_timeout", {"timeout": 300})
                return False
            except Exception as e:
                self.log(f"❌ Cleanup exception: {e}")
                self.emit_alert("cleanup_exception", {"error": str(e)})
                return False
        else:
            self.log(f"⚠️ Cleanup script not found: {cleanup_script}")
            self.emit_alert("cleanup_script_missing", {"path": str(cleanup_script)})
            return False

    def emit_alert(self, alert_type, data):
        """Emit alert for critical events (Codex/Gemini Review Fix)"""
        alert_msg = f"🚨 ALERT [{alert_type.upper()}]: {data}"
        self.log(alert_msg)

        # Write alert to separate alert log for monitoring
        alert_log = self.claude_home / "disk_alerts.log"
        try:
            with open(alert_log, 'a') as f:
                timestamp = datetime.now().isoformat()
                f.write(f"[{timestamp}] {alert_type}: {data}\n")
        except Exception as e:
            self.log(f"⚠️ Could not write to alert log: {e}")

    def check_and_act(self):
        """Check disk usage and take action"""
        usage = self.get_disk_usage("/")

        if usage < 0:
            self.log("❌ Failed to get disk usage")
            return

        status = {
            'timestamp': datetime.now().isoformat(),
            'usage_percent': usage,
            'status': 'healthy',
            'last_cleanup': None,
            'directories': self.get_directory_sizes()
        }

        # Determine status
        if usage >= self.critical_threshold:
            status['status'] = 'critical'
            self.log(f"🚨 CRITICAL: Disk usage at {usage}%")

            if self.auto_cleanup:
                if self.run_cleanup():
                    status['last_cleanup'] = datetime.now().isoformat()
                    # Re-check after cleanup
                    usage = self.get_disk_usage("/")
                    status['usage_percent'] = usage
                    self.log(f"After cleanup: {usage}%")

        elif usage >= self.cleanup_threshold:
            status['status'] = 'high'
            self.log(f"⚠️ HIGH: Disk usage at {usage}% - triggering cleanup")

            if self.auto_cleanup:
                if self.run_cleanup():
                    status['last_cleanup'] = datetime.now().isoformat()
                    usage = self.get_disk_usage("/")
                    status['usage_percent'] = usage

        elif usage >= self.warning_threshold:
            status['status'] = 'warning'
            self.log(f"⚠️ WARNING: Disk usage at {usage}%")

        else:
            status['status'] = 'healthy'
            # Only log periodically when healthy
            if hasattr(self, 'last_healthy_log'):
                if (datetime.now() - self.last_healthy_log).seconds < 3600:
                    pass  # Don't log
                else:
                    self.log(f"✅ Disk usage healthy: {usage}%")
                    self.last_healthy_log = datetime.now()
            else:
                self.log(f"✅ Disk usage healthy: {usage}%")
                self.last_healthy_log = datetime.now()

        # Save status
        with open(self.status_file, 'w') as f:
            json.dump(status, f, indent=2)

    def monitor(self):
        """Main monitoring loop"""
        self.log("🚀 Starting Disk Space Monitor")
        self.log(f"Warning threshold: {self.warning_threshold}%")
        self.log(f"Cleanup threshold: {self.cleanup_threshold}%")
        self.log(f"Critical threshold: {self.critical_threshold}%")
        self.log(f"Check interval: {self.check_interval}s")

        while True:
            try:
                self.check_and_act()
                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                self.log("👋 Shutting down Disk Space Monitor")
                break
            except Exception as e:
                self.log(f"❌ Error in monitoring loop: {e}")
                time.sleep(self.check_interval)

if __name__ == "__main__":
    monitor = DiskSpaceMonitor()
    monitor.monitor()

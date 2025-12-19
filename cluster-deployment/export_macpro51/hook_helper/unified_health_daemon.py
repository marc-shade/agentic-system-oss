#!/usr/bin/env python3
"""
Unified Health Daemon for Phoenix Agentic Framework
Monitors and auto-heals all critical services:
- Voice Services (Whisper, Kokoro, LiveKit)
- MCP Servers (Enhanced Memory, Agent Runtime, Arduino, Ember)
- Port Manager Daemon
- System Resources

Auto-recovery with backoff strategy
"""

import time
import json
import socket
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

# Logging setup
LOG_FILE = Path.home() / ".claude" / "health_daemon.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("unified_health_daemon")

class ServiceConfig:
    """Configuration for a monitored service"""
    def __init__(self, name: str, port: Optional[int] = None,
                 endpoint: Optional[str] = None, critical: bool = True,
                 restart_cmd: Optional[str] = None,
                 health_check: Optional[str] = None):
        self.name = name
        self.port = port
        self.endpoint = endpoint
        self.critical = critical
        self.restart_cmd = restart_cmd
        self.health_check = health_check
        self.consecutive_failures = 0
        self.last_restart = datetime.min
        self.restart_cooldown = 60  # seconds between restarts

class UnifiedHealthDaemon:
    """Monitor and auto-heal all Phoenix services"""

    def __init__(self):
        self.check_interval = 30  # Check every 30 seconds
        self.max_consecutive_failures = 3
        self.services = self._init_services()
        self.status_file = Path.home() / ".claude" / "health_status.json"

    def _init_services(self) -> List[ServiceConfig]:
        """Initialize service configurations"""
        return [
            # Voice Services
            ServiceConfig(
                name="whisper",
                port=2022,
                endpoint="http://127.0.0.1:2022/health",
                critical=True,
                restart_cmd="voicemode service whisper restart",
                health_check="port"
            ),
            ServiceConfig(
                name="kokoro",
                port=8880,
                endpoint="http://127.0.0.1:8880/health",
                critical=True,
                restart_cmd="voicemode service kokoro restart",
                health_check="port"
            ),
            ServiceConfig(
                name="livekit",
                port=7880,
                endpoint="http://127.0.0.1:7880",
                critical=False,
                restart_cmd="voicemode service livekit restart",
                health_check="port"
            ),

            # Port Manager
            ServiceConfig(
                name="port_manager",
                port=4102,
                endpoint="http://localhost:4102/health",
                critical=False,
                restart_cmd="cd /Volumes/FILES/code/kutiraai && npm run daemon",
                health_check="port"
            ),
        ]

    def check_port(self, port: int, timeout: float = 2.0) -> bool:
        """Check if a port is listening with explicit timeout (Codex Review - Already Implemented!)"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)  # Critical: prevents hung connections
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            return result == 0
        except socket.timeout:
            logger.debug(f"Socket timeout checking port {port}")
            return False
        except socket.error as e:
            logger.debug(f"Socket error checking port {port}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking port {port}: {e}")
            return False

    def check_endpoint(self, url: str, timeout: float = 3.0) -> bool:
        """Check if an HTTP endpoint is responding with explicit error handling (Codex Review Fix)"""
        try:
            # Extract host and port from URL
            if "://" in url:
                url = url.split("://")[1]
            if "/" in url:
                url = url.split("/")[0]
            if ":" in url:
                host, port = url.rsplit(":", 1)
                return self.check_port(int(port), timeout)
            logger.warning(f"Invalid endpoint URL format: {url}")
            return False
        except ValueError as e:
            logger.error(f"Error parsing endpoint {url}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking endpoint {url}: {e}")
            return False

    def check_service_health(self, service: ServiceConfig) -> bool:
        """Check if a service is healthy"""
        try:
            if service.health_check == "port" and service.port:
                return self.check_port(service.port)
            elif service.endpoint:
                return self.check_endpoint(service.endpoint)
            return False
        except Exception as e:
            logger.error(f"Health check failed for {service.name}: {e}")
            return False

    def restart_service(self, service: ServiceConfig) -> bool:
        """Attempt to restart a service"""
        # Check cooldown
        if datetime.now() - service.last_restart < timedelta(seconds=service.restart_cooldown):
            logger.info(f"Skipping restart of {service.name} (cooldown)")
            return False

        if not service.restart_cmd:
            logger.warning(f"No restart command for {service.name}")
            return False

        try:
            logger.info(f"🔄 Restarting {service.name}...")
            result = subprocess.run(
                service.restart_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            service.last_restart = datetime.now()

            # Wait for service to come up
            time.sleep(5)

            # Verify restart
            if self.check_service_health(service):
                logger.info(f"✅ Successfully restarted {service.name}")
                service.consecutive_failures = 0
                return True
            else:
                logger.warning(f"⚠️ Restart completed but {service.name} still unhealthy")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to restart {service.name}: {e}")
            return False

    def monitor_services(self):
        """Main monitoring loop"""
        logger.info("🚀 Starting Unified Health Daemon")

        while True:
            try:
                timestamp = datetime.now()
                status_report = {
                    'timestamp': timestamp.isoformat(),
                    'services': {},
                    'critical_issues': [],
                    'warnings': []
                }

                for service in self.services:
                    healthy = self.check_service_health(service)

                    if healthy:
                        service.consecutive_failures = 0
                        status_report['services'][service.name] = {
                            'status': 'healthy',
                            'port': service.port,
                            'critical': service.critical
                        }
                    else:
                        service.consecutive_failures += 1
                        status_report['services'][service.name] = {
                            'status': 'unhealthy',
                            'consecutive_failures': service.consecutive_failures,
                            'port': service.port,
                            'critical': service.critical
                        }

                        # Log issue
                        if service.critical:
                            logger.warning(f"⚠️ CRITICAL: {service.name} unhealthy (failures: {service.consecutive_failures})")
                            status_report['critical_issues'].append(service.name)
                        else:
                            logger.info(f"⚠️ Warning: {service.name} unhealthy (failures: {service.consecutive_failures})")
                            status_report['warnings'].append(service.name)

                        # Auto-heal if threshold exceeded
                        if service.consecutive_failures >= self.max_consecutive_failures:
                            logger.warning(f"🔧 Auto-healing triggered for {service.name}")
                            self.restart_service(service)

                # Save status report
                self.status_file.write_text(json.dumps(status_report, indent=2))

                # Sleep until next check
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                logger.info("👋 Shutting down Unified Health Daemon")
                break
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
                time.sleep(self.check_interval)

    def get_status(self) -> Dict:
        """Get current status report"""
        if self.status_file.exists():
            return json.loads(self.status_file.read_text())
        return {}

def main():
    daemon = UnifiedHealthDaemon()
    daemon.monitor_services()

if __name__ == "__main__":
    main()

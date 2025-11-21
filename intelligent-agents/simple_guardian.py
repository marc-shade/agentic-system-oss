#!/usr/bin/env python3
"""
Simple System Guardian - Rule-based service health monitoring
No AI required - just checks and fixes services that are down
"""

import os
import sys
import subprocess
import time
import logging
import psutil
import requests
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Configure logging
LOG_DIR = Path("/home/marc/agentic-system/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            LOG_DIR / "simple_guardian.log",
            maxBytes=10*1024*1024,
            backupCount=5
        ),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("SimpleGuardian")


class SimpleSystemGuardian:
    """
    Simple guardian that keeps agentic services running
    Uses rules instead of AI for reliability
    """

    def __init__(self):
        self.services = {
            "temporal": {
                "check": self.check_temporal,
                "start": self.start_temporal,
                "port": 7233,
                "priority": "critical"
            },
            "memory-db": {
                "check": self.check_memory_db,
                "start": self.start_memory_db,
                "socket": "/tmp/memory-db.sock",
                "priority": "critical"
            },
            "autokitteh": {
                "check": self.check_autokitteh,
                "start": self.start_autokitteh,
                "port": 9980,
                "priority": "high"  # Workflow automation platform
            },
            "ollama": {
                "check": self.check_ollama,
                "start": self.start_ollama,
                "port": 11434,
                "priority": "critical"
            },
            "qdrant": {
                "check": self.check_qdrant,
                "start": self.start_qdrant,
                "port": 6333,
                "priority": "high"
            },
            "temporal-workers": {
                "check": self.check_temporal_workers,
                "start": self.start_temporal_workers,
                "priority": "critical"  # Autonomous workflows
            }
        }

        self.failure_counts = {service: 0 for service in self.services}

    def check_temporal(self) -> bool:
        try:
            result = subprocess.run(["pgrep", "-f", "temporal"], capture_output=True, timeout=5)
            return result.returncode == 0 and result.stdout.strip()
        except Exception:
            return False

    def check_memory_db(self) -> bool:
        try:
            return os.path.exists("/tmp/memory-db.sock")
        except Exception:
            return False

    def check_autokitteh(self) -> bool:
        try:
            result = subprocess.run(["pgrep", "-f", "autokitteh"], capture_output=True, timeout=5)
            return result.returncode == 0 and result.stdout.strip()
        except Exception:
            return False

    def check_ollama(self) -> bool:
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=3)
            return response.status_code == 200
        except Exception:
            return False

    def check_qdrant(self) -> bool:
        try:
            response = requests.get("http://localhost:6333/", timeout=3)
            return response.status_code == 200
        except Exception:
            return False

    def start_temporal(self) -> bool:
        try:
            script_path = "/home/marc/agentic-system/scripts/start-temporal.sh"
            subprocess.Popen([script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            time.sleep(3)
            return self.check_temporal()
        except Exception as e:
            logger.error(f"Error starting Temporal: {e}")
            return False

    def start_memory_db(self) -> bool:
        try:
            service_path = "/home/marc/agentic-system/mcp-servers/enhanced-memory-mcp/memory_db_service.py"
            subprocess.Popen(
                ["python3", service_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            time.sleep(2)
            return self.check_memory_db()
        except Exception as e:
            logger.error(f"Error starting memory-db: {e}")
            return False

    def start_autokitteh(self) -> bool:
        try:
            script_path = "/home/marc/agentic-system/scripts/start-autokitteh.sh"
            subprocess.Popen([script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            time.sleep(2)
            return self.check_autokitteh()
        except Exception as e:
            logger.error(f"Error starting AutoKitteh: {e}")
            return False

    def start_ollama(self) -> bool:
        try:
            subprocess.run(["sudo", "systemctl", "start", "ollama"], capture_output=True, timeout=10)
            time.sleep(2)
            return self.check_ollama()
        except Exception as e:
            logger.error(f"Error starting Ollama: {e}")
            return False

    def start_qdrant(self) -> bool:
        try:
            script_path = "/home/marc/agentic-system/scripts/start-qdrant.sh"
            subprocess.Popen([script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            time.sleep(2)
            return self.check_qdrant()
        except Exception as e:
            logger.error(f"Error starting Qdrant: {e}")
            return False

    def check_temporal_workers(self) -> bool:
        try:
            result = subprocess.run(["pgrep", "-f", "start_all_workers"], capture_output=True, timeout=5)
            return result.returncode == 0 and result.stdout.strip()
        except Exception:
            return False

    def start_temporal_workers(self) -> bool:
        try:
            subprocess.Popen(
                ["python3", "/home/marc/agentic-system/workflows/temporal/start_all_workers.py"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                cwd="/home/marc/agentic-system/workflows/temporal"
            )
            time.sleep(3)
            return self.check_temporal_workers()
        except Exception as e:
            logger.error(f"Error starting Temporal workers: {e}")
            return False

    def run_check(self):
        """Run one health check cycle"""
        logger.info("Running health check...")

        for service_name, service_info in self.services.items():
            try:
                is_healthy = service_info["check"]()

                if not is_healthy:
                    priority = service_info["priority"]
                    logger.warning(f"{service_name} is DOWN ({priority} priority)")

                    # Auto-restart critical and high priority services
                    if priority in ["critical", "high"]:
                        logger.info(f"Attempting to restart {service_name}...")
                        success = service_info["start"]()

                        if success:
                            logger.info(f"✓ Successfully restarted {service_name}")
                            self.failure_counts[service_name] = 0
                        else:
                            self.failure_counts[service_name] += 1
                            logger.error(f"✗ Failed to restart {service_name} (failures: {self.failure_counts[service_name]})")
                else:
                    if self.failure_counts[service_name] > 0:
                        logger.info(f"{service_name} is healthy again")
                        self.failure_counts[service_name] = 0

            except Exception as e:
                logger.error(f"Error checking {service_name}: {e}")

    def run(self, check_interval: int = 30):
        """Run the guardian loop"""
        logger.info("Simple System Guardian starting...")

        while True:
            try:
                self.run_check()
                time.sleep(check_interval)
            except KeyboardInterrupt:
                logger.info("Guardian stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in guardian loop: {e}")
                time.sleep(check_interval)


def main():
    guardian = SimpleSystemGuardian()
    guardian.run(check_interval=30)


if __name__ == "__main__":
    main()

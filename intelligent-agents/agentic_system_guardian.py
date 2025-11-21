#!/usr/bin/env python3
"""
Agentic System Guardian - Keeps all agentic services healthy and running

Monitors and auto-heals:
- Temporal workflow engine
- AutoKitteh event automation
- n8n visual workflows
- MCP servers (enhanced-memory, agent-runtime, etc.)
- Qdrant vector database
- Ollama inference engine
- Monitoring stack (Prometheus, Loki, Grafana)

Uses Ollama for free AI-powered decision making
"""

import os
import sys
import subprocess
import time
import logging
import psutil
import requests
import json
from pathlib import Path
from typing import Dict, Any, List
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Add SDK agents to path
sys.path.insert(0, str(Path(__file__).parent / "sdk_agents"))
from ollama_agent import OllamaAgent, AgentPurpose

# Configure logging
LOG_DIR = Path("/home/marc/agentic-system/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            LOG_DIR / "agentic_guardian.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        ),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("AgenticGuardian")


class AgenticSystemGuardian(OllamaAgent):
    """
    Intelligent guardian that keeps all agentic services running
    """

    def __init__(self):
        # Define critical services to monitor
        self.services = {
            "temporal": {
                "check": self.check_temporal,
                "start": self.start_temporal,
                "port": 7233,
                "priority": "critical"
            },
            "autokitteh": {
                "check": self.check_autokitteh,
                "start": self.start_autokitteh,
                "port": 9980,
                "priority": "high"
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
            "prometheus": {
                "check": self.check_prometheus,
                "start": self.start_prometheus,
                "port": 9700,
                "priority": "medium"
            },
            "loki": {
                "check": self.check_loki,
                "start": self.start_loki,
                "port": 9900,
                "priority": "medium"
            },
            "grafana": {
                "check": self.check_grafana,
                "start": self.start_grafana,
                "port": 9500,
                "priority": "low"
            }
        }

        # Define agent purpose
        purpose = AgentPurpose(
            name="Agentic System Guardian",
            description="Monitors and maintains health of all agentic services",
            primary_goal="Keep 100% uptime on critical services, auto-heal failures",
            decision_criteria=[
                "Critical services (Temporal, Ollama) must restart immediately",
                "High priority services restart within 30 seconds",
                "Medium/low priority services can wait up to 2 minutes",
                "Avoid restart loops - track failure counts",
                "Alert on persistent failures (3+ in 5 minutes)"
            ],
            tools_needed=["systemctl", "pgrep", "curl", "subprocess"]
        )

        tools = [
            {"name": "check_service", "description": "Check if service is running"},
            {"name": "start_service", "description": "Start a stopped service"},
            {"name": "restart_service", "description": "Restart a failing service"},
            {"name": "alert", "description": "Send alert about critical issues"}
        ]

        # Initialize with Ollama
        super().__init__(purpose, tools, model="llama3.2:latest")

        # Track failures
        self.failure_counts = {service: 0 for service in self.services}
        self.last_failure_time = {service: None for service in self.services}

    def gather_observations(self) -> Dict[str, Any]:
        """Gather current state of all services"""
        observations = {
            "timestamp": datetime.now().isoformat(),
            "services": {},
            "system_health": {}
        }

        # Check each service
        for service_name, service_info in self.services.items():
            try:
                is_healthy = service_info["check"]()
                observations["services"][service_name] = {
                    "status": "healthy" if is_healthy else "down",
                    "priority": service_info["priority"],
                    "port": service_info.get("port"),
                    "failure_count": self.failure_counts[service_name]
                }
            except Exception as e:
                logger.error(f"Error checking {service_name}: {e}")
                observations["services"][service_name] = {
                    "status": "error",
                    "error": str(e)
                }

        # System resource usage
        observations["system_health"] = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "load_avg": os.getloadavg()[0]
        }

        return observations

    def execute_decision(self, decision) -> bool:
        """Execute the agent's decision"""
        try:
            logger.info(f"Decision: {decision.decision}")
            logger.info(f"Reasoning: {decision.reasoning}")

            # Parse decision to see if we need to restart services
            decision_text = decision.decision.lower()

            for service_name in self.services.keys():
                if service_name in decision_text and ("restart" in decision_text or "start" in decision_text):
                    logger.info(f"Attempting to start {service_name}")
                    success = self.services[service_name]["start"]()

                    if success:
                        logger.info(f"Successfully started {service_name}")
                        self.failure_counts[service_name] = 0
                    else:
                        logger.error(f"Failed to start {service_name}")
                        self.failure_counts[service_name] += 1
                        self.last_failure_time[service_name] = datetime.now()

            return True

        except Exception as e:
            logger.error(f"Error executing decision: {e}")
            return False

    # Service check methods
    def check_temporal(self) -> bool:
        """Check if Temporal is running"""
        try:
            result = subprocess.run(
                ["pgrep", "-f", "temporal"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0 and result.stdout.strip()
        except Exception:
            return False

    def check_autokitteh(self) -> bool:
        """Check if AutoKitteh is running"""
        try:
            result = subprocess.run(
                ["pgrep", "-f", "autokitteh"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0 and result.stdout.strip()
        except Exception:
            return False

    def check_ollama(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def check_qdrant(self) -> bool:
        """Check if Qdrant is running"""
        try:
            response = requests.get("http://localhost:6333/", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def check_prometheus(self) -> bool:
        """Check if Prometheus is running"""
        try:
            response = requests.get("http://localhost:9700/-/healthy", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def check_loki(self) -> bool:
        """Check if Loki is running"""
        try:
            response = requests.get("http://localhost:9900/ready", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def check_grafana(self) -> bool:
        """Check if Grafana is running"""
        try:
            response = requests.get("http://localhost:9500/api/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    # Service start methods
    def start_temporal(self) -> bool:
        """Start Temporal server"""
        try:
            script_path = "/home/marc/agentic-system/scripts/start-temporal.sh"
            subprocess.Popen(
                [script_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            time.sleep(3)  # Give it time to start
            return self.check_temporal()
        except Exception as e:
            logger.error(f"Error starting Temporal: {e}")
            return False

    def start_autokitteh(self) -> bool:
        """Start AutoKitteh server"""
        try:
            script_path = "/home/marc/agentic-system/scripts/start-autokitteh.sh"
            subprocess.Popen(
                [script_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            time.sleep(2)
            return self.check_autokitteh()
        except Exception as e:
            logger.error(f"Error starting AutoKitteh: {e}")
            return False

    def start_ollama(self) -> bool:
        """Start Ollama service"""
        try:
            result = subprocess.run(
                ["sudo", "systemctl", "start", "ollama"],
                capture_output=True,
                timeout=10
            )
            time.sleep(2)
            return self.check_ollama()
        except Exception as e:
            logger.error(f"Error starting Ollama: {e}")
            return False

    def start_qdrant(self) -> bool:
        """Start Qdrant vector database"""
        try:
            script_path = "/home/marc/agentic-system/scripts/start-qdrant.sh"
            subprocess.Popen(
                [script_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            time.sleep(2)
            return self.check_qdrant()
        except Exception as e:
            logger.error(f"Error starting Qdrant: {e}")
            return False

    def start_prometheus(self) -> bool:
        """Start Prometheus"""
        try:
            script_path = "/home/marc/agentic-system/monitoring/start-prometheus.sh"
            subprocess.Popen(
                [script_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            time.sleep(2)
            return self.check_prometheus()
        except Exception as e:
            logger.error(f"Error starting Prometheus: {e}")
            return False

    def start_loki(self) -> bool:
        """Start Loki"""
        try:
            script_path = "/home/marc/agentic-system/monitoring/start-loki.sh"
            subprocess.Popen(
                [script_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            time.sleep(2)
            return self.check_loki()
        except Exception as e:
            logger.error(f"Error starting Loki: {e}")
            return False

    def start_grafana(self) -> bool:
        """Start Grafana"""
        try:
            script_path = "/home/marc/agentic-system/monitoring/start-grafana.sh"
            subprocess.Popen(
                [script_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            time.sleep(2)
            return self.check_grafana()
        except Exception as e:
            logger.error(f"Error starting Grafana: {e}")
            return False

    def run(self, check_interval: int = 30):
        """
        Run the guardian loop

        Args:
            check_interval: Seconds between health checks
        """
        logger.info("Agentic System Guardian starting...")
        self.start()

        while self.running:
            try:
                # Run one iteration
                self.run_iteration()

                # Sleep until next check
                time.sleep(check_interval)

            except KeyboardInterrupt:
                logger.info("Guardian stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in guardian loop: {e}")
                time.sleep(check_interval)


def main():
    """Main entry point"""
    guardian = AgenticSystemGuardian()

    # Run with 30-second checks
    guardian.run(check_interval=30)


if __name__ == "__main__":
    main()

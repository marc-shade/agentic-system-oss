#!/usr/bin/env python3
"""
System Remediation Agent - Autonomous fix executor

This agent works WITH the System Health Guardian:
- Health Guardian: Detects issues and makes recommendations
- Remediation Agent: Executes fixes based on recommendations

Observer-Actor Pattern:
- Observer (Guardian): "Temporal is down"
- Actor (Remediation): Starts Temporal

Benefits:
- Separation of concerns
- Safety: Can review recommendations before executing
- Testability: Can test fix logic independently
- Audit trail: Clear distinction between detection and action
"""
import platform

import os
import sys
import json
import time
import socket
import datetime
import subprocess
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "sdk_agents"))
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

from cli_agent import CLIAgent, AgentPurpose
from agent_memory import AgentMemory
from secure_ipc import (

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

    read_recommendations,
    write_recommendations,
    save_crash_history,
    load_crash_history,
    SECURE_LOG_DIR
)


class SystemRemediationAgent(CLIAgent):
    """
    Autonomous remediation agent that executes fixes

    Reads recommendations from System Health Guardian and takes action
    """

    def __init__(self):
        # Define what this agent is for
        purpose = AgentPurpose(
            name="System Remediation Agent",
            description="Executes system fixes based on health guardian recommendations",
            primary_goal="Automatically fix system issues with crash loop protection and health verification",
            decision_criteria=[
                "Read recommendations from health guardian via secure IPC",
                "Verify fix is safe to execute",
                "Check crash history to prevent loops",
                "Execute fix and verify service health",
                "Persist crash history to survive restarts",
                "Log all actions with rotation"
            ],
            tools_needed=["subprocess", "service_restart", "crash_detection", "health_checks"]
        )

        # Initialize CLI agent
        super().__init__(
            purpose=purpose,
            tools=self._get_tool_definitions(),
            cli_tool="gemini"
        )

        # CRITICAL-FIX: CRITICAL-4 - Log rotation with Python logging
        self.logger = logging.getLogger("SystemRemediationAgent")
        handler = RotatingFileHandler(
            f"{SECURE_LOG_DIR}/remediation_agent.log",
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=5  # Keep 5 backup files
        )
        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        # CRITICAL-FIX: CRITICAL-6 - Load crash history from persistent storage
        self.crash_history = load_crash_history()
        self.max_restarts_per_hour = 3
        self.logger.info(f"Loaded crash history: {len(self.crash_history)} services tracked")

        # Memory integration - Remember remediation actions and learn from patterns
        self.memory = AgentMemory("system_remediation_agent")
        if self.memory.is_enabled():
            self.logger.info("✅ Memory integration enabled")
        else:
            self.logger.warning("⚠️  Memory integration disabled")

    def _get_tool_definitions(self) -> list:
        """Define tools this agent can use"""
        return [
            {
                "name": "execute_service_restart",
                "description": "Restart a failed service",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "service_name": {
                            "type": "string",
                            "enum": ["temporal", "autokitteh", "pm2", "qdrant"]
                        }
                    }
                }
            },
            {
                "name": "investigate_logs",
                "description": "Investigate service logs for root cause",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "service_name": {"type": "string"}
                    }
                }
            }
        ]

    def gather_observations(self) -> Dict[str, Any]:
        """
        Read recommendations from health guardian via secure IPC

        CRITICAL-FIX: CRITICAL-1 & CRITICAL-2 - Use secure IPC for reading recommendations
        """
        observations = {
            "timestamp": datetime.datetime.now().isoformat(),
            "iteration": self.iteration_count,
            "pending_recommendations": []
        }

        # CRITICAL-FIX: CRITICAL-1 & CRITICAL-2 - Use secure_ipc module
        try:
            recommendations = read_recommendations()
            observations["pending_recommendations"] = recommendations
            if recommendations:
                self.logger.info(f"Read {len(recommendations)} recommendations via secure IPC")
        except Exception as e:
            self.logger.error(f"Failed to read recommendations: {e}")
            observations["read_error"] = str(e)

        # Check memory for similar past remediations
        if self.memory.is_enabled():
            try:
                query_parts = []
                if recommendations:
                    for rec in recommendations:
                        service = rec.get("service", "")
                        if service:
                            query_parts.append(f"{service} restart")

                if query_parts:
                    query = " ".join(query_parts[:2])  # Limit to first 2 services
                    similar_remediations = self.memory.recall(query, limit=3)
                    if similar_remediations:
                        observations["similar_past_fixes"] = len(similar_remediations)
                        self.logger.info(f"Found {len(similar_remediations)} similar past remediations")
            except Exception as e:
                self.logger.error(f"Memory recall failed: {e}")

        return observations

    def _should_restart_service(self, service_name: str) -> bool:
        """
        Check if service should be restarted or needs investigation

        CRITICAL-FIX: CRITICAL-6 - Persist crash history after updates
        """
        now = datetime.datetime.now()
        one_hour_ago = now - datetime.timedelta(hours=1)

        if service_name not in self.crash_history:
            self.crash_history[service_name] = []

        # Clean up old crashes
        self.crash_history[service_name] = [
            ts for ts in self.crash_history[service_name]
            if ts > one_hour_ago
        ]

        # Check if too many recent crashes
        recent_crashes = len(self.crash_history[service_name])
        if recent_crashes >= self.max_restarts_per_hour:
            return False  # Don't restart - investigate instead

        # Record this crash
        self.crash_history[service_name].append(now)

        # CRITICAL-FIX: CRITICAL-6 - Persist crash history to disk
        save_crash_history(self.crash_history)

        return True

    def _verify_service_health(self, service_name: str, port: int, timeout_seconds: int = 30) -> bool:
        """
        CRITICAL-FIX: CRITICAL-5 - Verify service health by checking if port is listening

        Args:
            service_name: Name of the service
            port: Port number to check
            timeout_seconds: Maximum seconds to wait for service to start

        Returns:
            True if service is healthy (port listening), False otherwise
        """
        self.logger.info(f"Verifying {service_name} health on port {port} (timeout: {timeout_seconds}s)")

        for attempt in range(timeout_seconds):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                sock.close()

                if result == 0:
                    self.logger.info(f"✓ {service_name} is healthy (port {port} listening)")
                    return True
            except Exception as e:
                self.logger.debug(f"Health check attempt {attempt + 1} failed: {e}")

            time.sleep(1)

        self.logger.error(f"✗ {service_name} failed to start within {timeout_seconds}s")
        return False

    def _restart_service(self, service_name: str) -> Dict[str, Any]:
        """
        Restart a specific service and verify it started successfully

        CRITICAL-FIX: CRITICAL-5 - Added health checks after restart
        CRITICAL-FIX: HIGH-1 - Removed hardcoded PM2 path
        """
        self.logger.info(f"🔄 Restarting {service_name}...")

        port = None  # Port to verify for health check

        try:
            if service_name == "temporal":
                subprocess.Popen(
                    ["nohup", "temporal", "server", "start-dev",
                     "--db-filename", "/tmp/temporal.db",
                     "--ui-port", "8233"],
                    stdout=open("/tmp/temporal_server.log", "w"),
                    stderr=subprocess.STDOUT
                )
                port = 7233  # Temporal gRPC port

            elif service_name == "autokitteh":
                subprocess.Popen(
                    ["nohup", "ak", "up", "--mode", "dev"],
                    stdout=open("/tmp/autokitteh.log", "w"),
                    stderr=subprocess.STDOUT,
                    cwd=str(_STORAGE_BASE)
                )
                port = 9980  # AutoKitteh port

            elif service_name == "qdrant":
                result = subprocess.run(
                    [str(_STORAGE_BASE / "scripts/qdrant-monitor.sh"), "start"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    return {"success": False, "error": result.stderr}
                port = 6333  # Qdrant HTTP port

            elif service_name == "pm2":
                # CRITICAL-FIX: HIGH-1 - Use PATH instead of hardcoded path
                result = subprocess.run(
                    ["pm2", "resurrect"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    return {"success": False, "error": result.stderr}
                # PM2 doesn't have a single port to check

            else:
                return {"success": False, "error": f"Unknown service: {service_name}"}

            # CRITICAL-FIX: CRITICAL-5 - Verify service health
            if port is not None:
                success = self._verify_service_health(service_name, port, timeout_seconds=30)
                if success:
                    return {"success": True, "verified": True}
                else:
                    return {"success": False, "error": "Service did not start within 30s", "verified": False}
            else:
                # PM2 or services without health check
                return {"success": True, "verified": False, "note": "No health check available"}

        except Exception as e:
            self.logger.error(f"Failed to restart {service_name}: {e}")
            return {"success": False, "error": str(e)}

    def _investigate_service_failure(self, service_name: str) -> str:
        """Investigate why a service keeps failing"""
        findings = []

        log_paths = {
            "temporal": "/tmp/temporal_server.log",
            "autokitteh": "/tmp/autokitteh.log",
            "qdrant": str(_STORAGE_BASE / "logs/qdrant-error.log")
        }

        log_path = log_paths.get(service_name)
        if not log_path:
            return f"No log path configured for {service_name}"

        try:
            if os.path.exists(log_path):
                result = subprocess.run(
                    ["tail", "-50", log_path],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                log_content = result.stdout

                # Look for common error patterns
                if "port already in use" in log_content.lower():
                    findings.append("PORT CONFLICT: Service port already in use")
                if "permission denied" in log_content.lower():
                    findings.append("PERMISSION ERROR: Check file permissions")
                if "out of memory" in log_content.lower() or "oom" in log_content.lower():
                    findings.append("MEMORY ERROR: System running out of memory")
                if "connection refused" in log_content.lower():
                    findings.append("CONNECTION ERROR: Cannot connect to dependency")
                if "timeout" in log_content.lower():
                    findings.append("TIMEOUT ERROR: Operations timing out")

                if not findings:
                    findings.append(f"Check log at {log_path} - no obvious error patterns")
            else:
                findings.append(f"Log file not found: {log_path}")

        except Exception as e:
            findings.append(f"Investigation error: {str(e)}")

        return " | ".join(findings)

    def execute_decision(self, decision: Any, observations: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute remediation based on decision

        CRITICAL-FIX: CRITICAL-4 - Use logger for all audit logging
        CRITICAL-FIX: CRITICAL-5 - Restart results now include health verification
        """
        result = {"status": "executed", "actions": []}

        # Parse decision for action
        decision_lower = decision.decision.lower()

        # Check for service restart recommendation
        for service in ["temporal", "autokitteh", "pm2", "qdrant"]:
            if service in decision_lower and ("restart" in decision_lower or "down" in decision_lower):
                # Check if safe to restart
                if self._should_restart_service(service):
                    restart_result = self._restart_service(service)
                    if restart_result["success"]:
                        result["actions"].append(f"restarted_{service}")
                        verified = restart_result.get("verified", False)
                        self.logger.info(f"AUTO-RESTART: {service} - {decision.reasoning[:100]} (verified={verified})")
                    else:
                        result["actions"].append(f"restart_failed_{service}")
                        error = restart_result.get('error', 'Unknown')
                        self.logger.error(f"RESTART-FAILED: {service} - {error}")
                else:
                    # Too many crashes - investigate
                    investigation = self._investigate_service_failure(service)
                    result["actions"].append(f"investigated_{service}")
                    self.logger.warning(f"INVESTIGATION: {service} - {investigation}")

        # Log execution
        self.logger.info(f"Remediation executed: {decision.decision} | Actions: {result['actions']}")

        # Store remediation action in memory for learning
        if self.memory.is_enabled() and observations:
            try:
                self.memory.remember({
                    "type": "service_remediation",
                    "decision": decision.decision,
                    "confidence": decision.confidence,
                    "actions": ",".join(result["actions"]),
                    "pending_recs": len(observations.get("pending_recommendations", [])),
                    "success": "failed" not in str(result["actions"]).lower()
                })
            except Exception as mem_error:
                self.logger.error(f"Memory storage failed: {mem_error}")

        return result

    # CRITICAL-FIX: CRITICAL-4 - Removed _audit_log method
    # All logging now done through self.logger with rotation

    def start(self, check_interval: int = 60):
        """
        Start the remediation agent

        CRITICAL-FIX: All security improvements implemented
        """
        print("=" * 60)
        print("🔧 System Remediation Agent Starting 🔧")
        print("=" * 60)
        print(f"CLI Tool: {self.cli_tool}")
        print(f"Recommendations: /run/recommendations.json (secure IPC)")
        print(f"Log file: {SECURE_LOG_DIR}/remediation_agent.log (10MB rotation)")
        print(f"Check interval: {check_interval}s")
        print(f"Crash history: {len(self.crash_history)} services tracked (persistent)")
        print()
        print("🚀 AUTONOMOUS REMEDIATION WITH SECURITY")
        print("   • Reads recommendations via secure IPC (file locking)")
        print("   • Executes safe fixes automatically")
        print("   • Health verification after each restart (30s timeout)")
        print("   • Crash detection: Max 3 restarts/hour per service")
        print("   • Persistent crash history (survives restarts)")
        print("   • Investigates crash-looping services")
        print()

        self.logger.info("System Remediation Agent started")

        # Run the remediation loop
        self.run_loop(interval_seconds=check_interval)

        return 0


def main():
    """
    Main entry point

    CRITICAL-FIX: All security improvements applied
    - CRITICAL-1 & 2: Secure IPC with file locking
    - CRITICAL-4: Log rotation (10MB, 5 backups)
    - CRITICAL-5: Health checks after restart (30s timeout)
    - CRITICAL-6: Persistent crash history
    - HIGH-1: No hardcoded paths
    """
    # Create and start the remediation agent
    agent = SystemRemediationAgent()
    agent.start(check_interval=60)


if __name__ == "__main__":
    main()

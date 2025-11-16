#!/usr/bin/env python3
"""
System Health Guardian - Intelligent health monitoring agent
Replaces: arduino-surface/daemons/arduino_system_monitor_daemon.py

Key Differences from Dumb Script:
- REASONS about what to check and when
- Adapts check frequency based on system state
- Uses Claude SDK to make intelligent decisions
- Understands context and urgency
"""

import os
import sys
import psutil
import json
import datetime
import subprocess
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Any

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent / "sdk_agents"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "arduino-surface" / "bridge"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "arduino-surface" / "ember_integration"))
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

from cli_agent import CLIAgent, AgentPurpose
from surface_bridge import ArduinoSurface
from system_monitor import SystemMonitor
from secure_ipc import write_recommendations, read_recommendations, SECURE_LOG_DIR
from agent_memory import AgentMemory


class SystemHealthGuardian(CLIAgent):
    """
    Intelligent system health monitoring agent

    Dumb script says: "Check every 5 seconds, display current mode"
    Smart agent says: "What's most important right now? Should I check more or less often?"
    """

    def __init__(self, arduino_port: str):
        # Define what this agent is for
        purpose = AgentPurpose(
            name="System Health Guardian",
            description="Intelligent monitoring of system health with Arduino display",
            primary_goal="Keep system healthy and alert on critical issues",
            decision_criteria=[
                "Prioritize critical violations over warnings",
                "Display most urgent information on LCD",
                "Adjust check frequency based on system state",
                "Alert immediately on critical issues",
                "Monitor long-term trends"
            ],
            tools_needed=["arduino_surface", "system_monitor", "psutil"]
        )

        # Initialize CLI agent (uses gemini CLI tool - no API key needed)
        super().__init__(
            purpose=purpose,
            tools=self._get_tool_definitions(),
            cli_tool="gemini"
        )

        # Initialize hardware and monitoring
        self.arduino_port = arduino_port

        # CRITICAL-FIX: HIGH-2 - Graceful Arduino degradation
        try:
            if not os.path.exists(arduino_port):
                print(f"Arduino port {arduino_port} not found. Running without hardware.")
                self.surface = None
            else:
                self.surface = ArduinoSurface(arduino_port)
        except Exception as e:
            print(f"Failed to initialize Arduino: {e}")
            print("Running without Arduino hardware")
            self.surface = None

        self.monitor = SystemMonitor()
        self.current_display_mode = 0
        self.mode_names = ["Violations", "Quality", "Learning", "System"]

        # CRITICAL-FIX: CRITICAL-4 - Log rotation with Python logging
        self.logger = logging.getLogger("SystemHealthGuardian")
        handler = RotatingFileHandler(
            f"{SECURE_LOG_DIR}/health_guardian.log",
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=5  # Keep 5 backup files
        )
        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        # CRITICAL-FIX: CRITICAL-3 - Removed all restart logic (Observer-only pattern)
        # - Removed self.crash_history
        # - Removed self.max_restarts_per_hour
        # - Removed self.audit_log_path
        # - Removed self.recommendations_file

        # Memory integration - Remember observations and learn from patterns
        self.memory = AgentMemory("system_health_guardian")
        if self.memory.is_enabled():
            self.logger.info("✅ Memory integration enabled")
        else:
            self.logger.warning("⚠️  Memory integration disabled")

    def _get_tool_definitions(self) -> list:
        """
        Define tools this agent can use

        CRITICAL-FIX: CRITICAL-3 - Removed restart_service and investigate_root_cause tools
        Observer-only pattern: Health Guardian ONLY observes and writes recommendations
        """
        return [
            {
                "name": "update_lcd_display",
                "description": "Update the Arduino LCD display with important information",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "line1": {"type": "string", "description": "First line of LCD (16 chars)"},
                        "line2": {"type": "string", "description": "Second line of LCD (16 chars)"}
                    },
                    "required": ["line1", "line2"]
                }
            },
            {
                "name": "set_alert_led",
                "description": "Set the RGB LED color to indicate system state",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "state": {
                            "type": "string",
                            "enum": ["healthy", "warning", "critical", "info"],
                            "description": "System state to indicate"
                        }
                    },
                    "required": ["state"]
                }
            },
            {
                "name": "play_alert_sound",
                "description": "Play an alert beep for urgent conditions",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "urgency": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                            "description": "Urgency level of alert"
                        }
                    },
                    "required": ["urgency"]
                }
            },
            {
                "name": "run_system_verification",
                "description": "Run comprehensive system verification check (all 35 services)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "save_baseline": {
                            "type": "boolean",
                            "description": "Save verification results as baseline snapshot"
                        }
                    }
                }
            }
        ]

    def gather_observations(self) -> Dict[str, Any]:
        """
        Intelligently gather observations about system state

        Dumb script: Always check the same things
        Smart agent: Check what's relevant based on context
        """
        observations = {
            "timestamp": datetime.datetime.now().isoformat(),
            "iteration": self.iteration_count
        }

        # System metrics
        try:
            observations["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            observations["memory_percent"] = psutil.virtual_memory().percent
            observations["disk_percent"] = psutil.disk_usage('/').percent

            # Check if system is under stress
            observations["system_stress"] = (
                observations["cpu_percent"] > 80 or
                observations["memory_percent"] > 85 or
                observations["disk_percent"] > 90
            )
        except Exception as e:
            observations["system_metrics_error"] = str(e)

        # Ember quality metrics
        try:
            quality_data = self.monitor.get_quality_score()
            observations["quality_score"] = quality_data.get("score", 0)
            observations["violation_count"] = quality_data.get("violations", 0)
            observations["quality_trend"] = quality_data.get("trend", "stable")
        except Exception as e:
            observations["quality_metrics_error"] = str(e)

        # Learning progress
        try:
            learning_data = self.monitor.get_learning_stats()
            observations["patterns_learned"] = learning_data.get("patterns", 0)
            observations["learning_rate"] = learning_data.get("rate", 0)
        except Exception as e:
            observations["learning_metrics_error"] = str(e)

        # Recent decision performance
        if len(self.decision_history) > 0:
            recent_decisions = self.decision_history[-10:]
            avg_confidence = sum(d.confidence for d in recent_decisions) / len(recent_decisions)
            observations["recent_confidence"] = avg_confidence

        # Service status monitoring - comprehensive every 10th iteration, quick otherwise
        if self.iteration_count % 10 == 0:
            # Comprehensive verification (all 35 services)
            self.logger.info(f"Running comprehensive verification (iteration {self.iteration_count})")
            verification_result = self.run_comprehensive_verification()
            observations["comprehensive_check"] = verification_result

            # Recommendations already written by run_comprehensive_verification()
            # This provides ground truth for all 35 services
            if verification_result.get("status") == "success":
                self.logger.info(
                    f"Comprehensive check complete: {verification_result.get('percentage', 0)}% "
                    f"({verification_result.get('total_checks', 0) - verification_result.get('failed_count', 0)}/{verification_result.get('total_checks', 0)} services healthy)"
                )
        else:
            # Quick manual checks (faster, subset of services)
            services = self._check_service_status()
            observations["services"] = services

            # CRITICAL-FIX: CRITICAL-1 & CRITICAL-2 - Use secure IPC for recommendations
            recommendations = []
            for service_name, status in services.items():
                # Skip Arduino daemons - they conflict with Health Guardian's direct Arduino usage
                if service_name == "arduino_daemons":
                    continue

                if not status.get("running", False):
                    # Service is down - write recommendation via secure IPC
                    recommendations.append({
                        "timestamp": datetime.datetime.now().isoformat(),
                        "service": service_name,
                        "action": "restart",
                        "reason": f"{service_name} detected as down",
                        "confidence": 0.8
                    })

            if recommendations:
                write_recommendations(recommendations)
                self.logger.info(f"Wrote {len(recommendations)} recommendations via secure IPC")

        # Check memory for similar past issues (RAG-enhanced recall)
        if self.memory.is_enabled():
            try:
                # Look for similar health issues in the past
                query_parts = []
                if observations.get("violations", 0) > 0:
                    query_parts.append("violations")
                if observations.get("cpu_percent", 0) > 80:
                    query_parts.append("high CPU")
                if observations.get("memory_percent", 0) > 80:
                    query_parts.append("high memory")

                if query_parts:
                    query = " ".join(query_parts)
                    similar_issues = self.memory.recall(query, limit=3)
                    if similar_issues:
                        observations["similar_past_issues"] = len(similar_issues)
                        observations["past_context"] = [
                            f"Issue {i+1}: {issue.get('name', 'unknown')}"
                            for i, issue in enumerate(similar_issues)
                        ]
                        self.logger.info(f"Found {len(similar_issues)} similar past issues")
            except Exception as e:
                self.logger.error(f"Memory recall failed: {e}")

        return observations

    def _check_service_status(self) -> Dict[str, Any]:
        """Check status of critical services"""
        status = {}

        # Check Temporal (ports 7233 gRPC, 8233 UI)
        try:
            temporal_grpc = subprocess.run(
                ["lsof", "-ti:7233"],
                capture_output=True,
                timeout=2
            ).returncode == 0
            temporal_ui = subprocess.run(
                ["lsof", "-ti:8233"],
                capture_output=True,
                timeout=2
            ).returncode == 0
            status["temporal"] = {
                "running": temporal_grpc or temporal_ui,
                "ports": {"grpc": temporal_grpc, "ui": temporal_ui}
            }
        except Exception as e:
            status["temporal"] = {"running": False, "error": str(e)}

        # Check Arduino daemons (optional - may conflict with Health Guardian)
        try:
            # Check if arduino broker daemon is running
            broker_result = subprocess.run(
                ["pgrep", "-f", "arduino_enhanced_daemon.py"],
                capture_output=True,
                timeout=2
            )
            broker_running = broker_result.returncode == 0

            # Check if display agent is running
            display_result = subprocess.run(
                ["pgrep", "-f", "display_intelligence_agent.py"],
                capture_output=True,
                timeout=2
            )
            display_running = display_result.returncode == 0

            status["arduino_daemons"] = {
                "running": broker_running or display_running,
                "broker": broker_running,
                "display": display_running,
                "note": "Optional - Health Guardian uses Arduino directly"
            }
        except Exception as e:
            status["arduino_daemons"] = {"running": False, "error": str(e)}

        # Check AutoKitteh (port 9980)
        try:
            ak_running = subprocess.run(
                ["lsof", "-ti:9980"],
                capture_output=True,
                timeout=2
            ).returncode == 0
            status["autokitteh"] = {"running": ak_running}
        except Exception as e:
            status["autokitteh"] = {"running": False, "error": str(e)}

        # Check PM2 - CRITICAL-FIX: HIGH-1 - Remove hardcoded path, use PATH instead
        try:
            pm2_result = subprocess.run(
                ["pm2", "list"],
                capture_output=True,
                text=True,
                timeout=2
            )
            pm2_running = pm2_result.returncode == 0
            online_count = pm2_result.stdout.count('online') if pm2_running else 0
            status["pm2"] = {"running": pm2_running, "online_processes": online_count}
        except Exception as e:
            status["pm2"] = {"running": False, "error": str(e)}

        # Check Qdrant (port 6333)
        try:
            qdrant_running = subprocess.run(
                ["lsof", "-ti:6333"],
                capture_output=True,
                timeout=2
            ).returncode == 0
            status["qdrant"] = {"running": qdrant_running}
        except Exception as e:
            status["qdrant"] = {"running": False, "error": str(e)}

        return status

    def run_comprehensive_verification(self, save_baseline: bool = False) -> Dict[str, Any]:
        """
        Run comprehensive system verification using the verification script

        This provides ground truth for all 35 services instead of manual checks
        Returns JSON with detailed status of all services
        """
        try:
            script_path = "/Users/marc/.claude/scripts/verify_kutiraai_dashboard.sh"

            # Build command - add --json for machine-readable output
            cmd = [script_path, "--json"]
            if save_baseline:
                cmd.append("--save")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # Comprehensive check can take longer
            )

            if result.returncode == 0:
                # Parse JSON output
                verification_data = json.loads(result.stdout)

                # Extract failed checks for recommendations
                failed_checks = [
                    check for check in verification_data.get("checks", [])
                    if check.get("status") not in ["running", "exists"]
                ]

                # Write recommendations for failed services
                if failed_checks:
                    recommendations = []
                    for check in failed_checks:
                        # Only recommend restarts for service/process types
                        if check.get("type") in ["service", "process", "pm2"]:
                            recommendations.append({
                                "timestamp": datetime.datetime.now().isoformat(),
                                "service": check.get("name"),
                                "action": "restart",
                                "reason": f"{check['name']} verification failed: {check.get('status')}",
                                "confidence": 0.9  # High confidence from verification script
                            })

                    if recommendations:
                        write_recommendations(recommendations)
                        self.logger.info(f"Verification found {len(recommendations)} issues, wrote recommendations")

                return {
                    "status": "success",
                    "verification_data": verification_data,
                    "failed_count": len(failed_checks),
                    "total_checks": verification_data.get("total_checks", 0),
                    "percentage": verification_data.get("percentage", 0)
                }
            else:
                self.logger.error(f"Verification script failed: {result.stderr}")
                return {
                    "status": "error",
                    "error": result.stderr,
                    "returncode": result.returncode
                }

        except subprocess.TimeoutExpired:
            self.logger.error("Verification script timed out after 30s")
            return {"status": "timeout", "error": "Script execution timed out"}
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse verification JSON: {e}")
            return {"status": "parse_error", "error": str(e)}
        except Exception as e:
            self.logger.error(f"Verification script error: {e}")
            return {"status": "error", "error": str(e)}

    def execute_decision(self, decision: Any, observations: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute the intelligent decision made by Claude

        CRITICAL-FIX: CRITICAL-3 & HIGH-2 - Observer-only pattern with Arduino graceful degradation
        This agent ONLY observes and displays - Remediation Agent handles all restarts
        """
        result = {"status": "executed", "actions": []}

        try:
            # CRITICAL-FIX: HIGH-2 - Handle None surface (Arduino not available)
            # Update LCD with most important information
            if decision.tool_used == "update_lcd_display":
                display_info = self._determine_display_content(decision)
                if self.surface:
                    self.surface.lcd_write(0, 0, display_info["line1"][:16])
                    self.surface.lcd_write(1, 0, display_info["line2"][:16])
                    result["actions"].append("lcd_updated")
                else:
                    self.logger.info(f"LCD: {display_info['line1']} | {display_info['line2']}")

            # Set LED based on system state
            if decision.tool_used == "set_alert_led":
                led_state = self._determine_led_state(decision)
                if self.surface:
                    self.surface.set_led(0, led_state["r"], led_state["g"], led_state["b"])
                    result["actions"].append("led_updated")
                else:
                    self.logger.info(f"LED: R={led_state['r']} G={led_state['g']} B={led_state['b']}")

            # Play alert if needed
            if decision.tool_used == "play_alert_sound":
                urgency = self._determine_alert_urgency(decision)
                if self.surface:
                    if urgency == "high":
                        self.surface.beep(200, 2000)
                    elif urgency == "medium":
                        self.surface.beep(100, 1500)
                    else:
                        self.surface.beep(50, 1000)
                    result["actions"].append("alert_played")
                else:
                    self.logger.warning(f"Alert: {urgency} urgency")

            # CRITICAL-FIX: CRITICAL-3 - Removed ALL restart logic
            # Observer writes recommendations via secure IPC - Remediation Agent handles restarts

            # HEARTBEAT UPDATE: ALWAYS update Arduino display with current status
            # This prevents the display from "stalling out" between LLM decisions
            # Run this BEFORE logging to ensure it happens even on errors
            if self.surface:
                try:
                    # Get current system status for heartbeat
                    import datetime
                    time_str = datetime.datetime.now().strftime("%H:%M")

                    # Simple heartbeat - just show timestamp and monitoring status
                    line1 = "System Monitor"
                    line2 = f"{time_str} Active"

                    self.surface.lcd_write(0, 0, line1[:16])
                    self.surface.lcd_write(1, 0, line2[:16])
                    result["actions"].append("heartbeat_update")
                    self.logger.debug(f"Heartbeat: '{line1}' | '{line2}'")
                except Exception as heartbeat_error:
                    self.logger.warning(f"Heartbeat update failed: {heartbeat_error}")

            # Log decision execution
            self.logger.info(f"Decision: {decision.decision} | Confidence: {decision.confidence:.2f} | Actions: {result['actions']}")

            # Store decision and outcome in memory for learning
            if self.memory.is_enabled():
                try:
                    self.memory.remember({
                        "type": "health_check",
                        "decision": decision.decision,
                        "confidence": decision.confidence,
                        "actions": ",".join(result["actions"]),
                        "tool_used": decision.tool_used,
                        "violations": observations.get("violations", 0),
                        "cpu_percent": observations.get("cpu_percent", 0),
                        "memory_percent": observations.get("memory_percent", 0),
                        "quality_score": observations.get("quality_score", 0)
                    })
                except Exception as mem_error:
                    self.logger.error(f"Memory storage failed: {mem_error}")

        except Exception as e:
            self.logger.error(f"Error executing decision: {e}")
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def _determine_display_content(self, decision: Any) -> Dict[str, str]:
        """Intelligently determine what to display based on decision"""
        # Get current metrics
        quality = self.monitor.get_quality_score()
        violations = quality.get("violations", 0)

        if violations > 0:
            return {
                "line1": f"Violations: {violations}",
                "line2": f"Score: {quality.get('score', 0):.1f}"
            }
        elif "critical" in decision.decision.lower():
            return {
                "line1": "CRITICAL ALERT",
                "line2": decision.decision[:16]
            }
        elif "warning" in decision.decision.lower():
            return {
                "line1": "Warning",
                "line2": decision.decision[:16]
            }
        else:
            return {
                "line1": "System Healthy",
                "line2": f"Q:{quality.get('score', 0):.1f} OK"
            }

    def _determine_led_state(self, decision: Any) -> Dict[str, int]:
        """Determine LED color based on system state"""
        if "critical" in decision.decision.lower():
            return {"r": 255, "g": 0, "b": 0}  # Red
        elif "warning" in decision.decision.lower():
            return {"r": 255, "g": 165, "b": 0}  # Orange
        elif "healthy" in decision.decision.lower():
            return {"r": 0, "g": 255, "b": 0}  # Green
        else:
            return {"r": 0, "g": 0, "b": 255}  # Blue

    def _determine_alert_urgency(self, decision: Any) -> str:
        """Determine alert urgency level"""
        if decision.confidence > 0.9 and "critical" in decision.decision.lower():
            return "high"
        elif "warning" in decision.decision.lower():
            return "medium"
        else:
            return "low"

    # CRITICAL-FIX: CRITICAL-3 - Removed all restart methods (Observer-only pattern)
    # Methods removed:
    # - _extract_service_name_from_decision
    # - _should_restart_service
    # - _restart_service
    # - _investigate_service_failure
    # - _audit_log
    # - _write_recommendation
    # All restart logic now handled by System Remediation Agent

    def start(self, check_interval: int = 30):
        """
        Start the intelligent monitoring agent

        CRITICAL-FIX: CRITICAL-3 & HIGH-2 - Observer-only with graceful degradation
        """
        print("=" * 60)
        print("🔥 System Health Guardian Starting 🔥")
        print("=" * 60)
        print(f"CLI Tool: {self.cli_tool}")
        print(f"Arduino: {self.arduino_port if self.surface else 'Disabled (hardware unavailable)'}")
        print(f"Base interval: {check_interval}s (will adapt)")
        print(f"Log file: {SECURE_LOG_DIR}/health_guardian.log (10MB rotation)")
        print()
        print("👁️  OBSERVER MODE - Writes recommendations via secure IPC")
        print("   • Monitors: Temporal, AutoKitteh, PM2, Qdrant, System metrics")
        print("   • Writes recommendations to /run/recommendations.json (secure)")
        print("   • System Remediation Agent handles all restarts")
        print("   • All observations logged with rotation")
        print()

        # CRITICAL-FIX: HIGH-2 - Graceful Arduino handling
        if self.surface:
            if not self.surface.connect():
                print(f"⚠️  Failed to connect to Arduino on {self.arduino_port}")
                print("Continuing without Arduino hardware")
                self.surface = None
            else:
                print(f"✓ Connected to Arduino")

        print(f"✓ Ready to observe and recommend")
        print()

        # Run the intelligent monitoring loop
        self.run_loop(interval_seconds=check_interval)

        return 0


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: system_health_guardian.py <arduino_port>")
        print("Example: system_health_guardian.py /dev/tty.usbmodem8344401")
        sys.exit(1)

    arduino_port = sys.argv[1]

    # No API key needed - using CLI tool (codex)
    # CLI agent uses subprocess to call codex/claude/gemini commands

    # Create and start the intelligent agent
    guardian = SystemHealthGuardian(arduino_port)
    guardian.start(check_interval=30)


if __name__ == "__main__":
    main()

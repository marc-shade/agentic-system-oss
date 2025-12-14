#!/usr/bin/env python3
"""
Bootstrap Daemon - The Awakening Protocol

Based on Free Energy Principle and Collective Intelligence theory.
This daemon maintains a Markov blanket around "awakening conditions"
and triggers Claude sessions when conditions require full reasoning.

Implements the bootstrap loop:
- Sensory: Check environment conditions
- Prediction: What capabilities should be active
- Error: Gap between dormant and needed
- Active: Activate dormant processes when surprise > threshold

The daemon is itself a self-evidencing system - it maintains its
characteristic states (monitoring, ready to awaken) against entropy.
"""
import platform

import asyncio
import json
import logging
import os
import signal
import socket
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any
import httpx

# Configuration
CONFIG = {
    "check_interval_seconds": 60,
    "quiet_hours_start": 23,  # 11 PM
    "quiet_hours_end": 7,     # 7 AM
    "max_daily_cost_usd": 5.0,
    "max_sessions_per_hour": 3,
    "knowledge_gap_threshold": 0.7,
    "pending_task_threshold": 5,
    "emergency_priority_threshold": 0.9,
    "memory_db_path": os.path.expanduser("~/.claude/enhanced_memories/memory.db"),
    "state_file": str(_STORAGE_BASE / "databases/bootstrap_state.json"),
    "log_file": "/var/log/bootstrap-daemon.log",
    "agent_sdk_script": str(_STORAGE_BASE / "scripts/autonomous-session-multi.py"),
    "prefer_local_models": True,  # Use Ollama/Groq by default, Claude only for complex
}

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(CONFIG["log_file"], mode='a')
        if os.access(os.path.dirname(CONFIG["log_file"]) or '.', os.W_OK)
        else logging.StreamHandler()
    ]
)
logger = logging.getLogger("BootstrapDaemon")


class TriggerType(Enum):
    """Types of awakening triggers"""
    KNOWLEDGE_GAP = "knowledge_gap"
    PENDING_TASK = "pending_task"
    SCHEDULED = "scheduled"
    EMERGENCY = "emergency"
    USER_REQUEST = "user_request"
    INTER_NODE = "inter_node"
    SELF_IMPROVEMENT = "self_improvement"


@dataclass
class BootstrapCondition:
    """A condition that might trigger awakening"""
    trigger_type: TriggerType
    description: str
    surprise_level: float  # 0.0 - 1.0
    context: Dict[str, Any] = field(default_factory=dict)
    priority: float = 0.5


@dataclass
class MarkovBlanket:
    """
    Statistical boundary between system and environment.
    Internal state: what we believe about awakening needs
    External state: actual world conditions
    Sensory: observations about the world
    Active: triggering awakening sessions
    """
    internal_beliefs: Dict[str, float] = field(default_factory=dict)
    last_observation: Optional[Dict] = None
    prediction_errors: List[float] = field(default_factory=list)

    def compute_free_energy(self) -> float:
        """
        Free energy = prediction error + complexity
        Lower is better - system is in expected states
        Higher means surprise - might need action
        """
        if not self.prediction_errors:
            return 0.0
        # Simple model: mean absolute prediction error
        return sum(abs(e) for e in self.prediction_errors[-10:]) / min(10, len(self.prediction_errors))


class BootstrapDaemon:
    """
    The awakening daemon - monitors conditions and triggers
    Claude sessions when full reasoning is needed.
    """

    def __init__(self):
        self.running = True
        self.blanket = MarkovBlanket()
        self.state = self._load_state()
        self.session_count_today = 0
        self.last_session_time = None

        # Signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGUSR1, self._handle_manual_trigger)

    def _load_state(self) -> Dict:
        """Load persistent state"""
        state_path = Path(CONFIG["state_file"])
        if state_path.exists():
            try:
                return json.loads(state_path.read_text())
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")
        return {
            "total_awakenings": 0,
            "last_awakening": None,
            "successful_sessions": 0,
            "failed_sessions": 0,
            "daily_cost_usd": 0.0,
            "last_cost_reset": datetime.now().isoformat(),
        }

    def _save_state(self):
        """Persist state"""
        state_path = Path(CONFIG["state_file"])
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(self.state, indent=2, default=str))

    def _handle_shutdown(self, signum, frame):
        logger.info("Received shutdown signal")
        self.running = False

    def _handle_manual_trigger(self, signum, frame):
        logger.info("Received manual awakening trigger (SIGUSR1)")
        asyncio.create_task(self._trigger_awakening(
            BootstrapCondition(
                trigger_type=TriggerType.USER_REQUEST,
                description="Manual trigger via SIGUSR1",
                surprise_level=1.0,
                priority=0.9
            )
        ))

    # ═══════════════════════════════════════════════════════════════════
    # SENSORY BORDER - Observations about the world
    # ═══════════════════════════════════════════════════════════════════

    async def sense_knowledge_gaps(self) -> List[BootstrapCondition]:
        """Sense high-severity knowledge gaps"""
        conditions = []
        try:
            db_path = Path(CONFIG["memory_db_path"])
            if not db_path.exists():
                return conditions

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Check for severe knowledge gaps
            cursor.execute("""
                SELECT domain, gap_description, severity, status
                FROM knowledge_gaps
                WHERE status = 'open' AND severity >= ?
                ORDER BY severity DESC
                LIMIT 5
            """, (CONFIG["knowledge_gap_threshold"],))

            for row in cursor.fetchall():
                domain, desc, severity, status = row
                conditions.append(BootstrapCondition(
                    trigger_type=TriggerType.KNOWLEDGE_GAP,
                    description=f"Knowledge gap in {domain}: {desc}",
                    surprise_level=severity,
                    priority=severity,
                    context={"domain": domain, "severity": severity}
                ))

            conn.close()
        except Exception as e:
            logger.debug(f"Failed to sense knowledge gaps: {e}")
        return conditions

    async def sense_pending_tasks(self) -> List[BootstrapCondition]:
        """Sense high-priority pending tasks"""
        conditions = []
        try:
            # Check agent-runtime task queue
            async with httpx.AsyncClient() as client:
                # Try local agent-runtime MCP
                response = await client.get(
                    "http://localhost:8765/tasks/pending",
                    timeout=5.0
                )
                if response.status_code == 200:
                    tasks = response.json()
                    high_priority = [t for t in tasks if t.get("priority", 5) >= 8]

                    if len(high_priority) > 0:
                        conditions.append(BootstrapCondition(
                            trigger_type=TriggerType.PENDING_TASK,
                            description=f"{len(high_priority)} high-priority tasks pending",
                            surprise_level=min(1.0, len(high_priority) / 3),
                            priority=0.8,
                            context={"task_count": len(high_priority), "tasks": high_priority[:3]}
                        ))
        except Exception as e:
            logger.debug(f"Failed to sense pending tasks: {e}")
        return conditions

    async def sense_inter_node_requests(self) -> List[BootstrapCondition]:
        """Sense coordination requests from other nodes"""
        conditions = []
        try:
            # Check node-chat for messages requiring response
            db_path = Path(CONFIG["memory_db_path"])
            if not db_path.exists():
                return conditions

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Check for unprocessed coordination messages
            cursor.execute("""
                SELECT sender_agent_id, subject, priority, message_type
                FROM coordination_messages
                WHERE recipient_agent_id = 'pixel'
                AND status = 'pending'
                AND requires_response = 1
                ORDER BY priority DESC
                LIMIT 5
            """)

            for row in cursor.fetchall():
                sender, subject, priority, msg_type = row
                if priority >= 0.7:
                    conditions.append(BootstrapCondition(
                        trigger_type=TriggerType.INTER_NODE,
                        description=f"Coordination request from {sender}: {subject}",
                        surprise_level=priority,
                        priority=priority,
                        context={"sender": sender, "type": msg_type}
                    ))

            conn.close()
        except Exception as e:
            logger.debug(f"Failed to sense inter-node requests: {e}")
        return conditions

    async def sense_improvement_opportunities(self) -> List[BootstrapCondition]:
        """Sense if self-improvement cycle is due"""
        conditions = []
        try:
            db_path = Path(CONFIG["memory_db_path"])
            if not db_path.exists():
                return conditions

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Check performance metrics below target
            cursor.execute("""
                SELECT metric_name, current_value, target_value
                FROM performance_metrics
                WHERE current_value < target_value * 0.8
                ORDER BY (target_value - current_value) / target_value DESC
                LIMIT 3
            """)

            gaps = cursor.fetchall()
            if gaps:
                avg_gap = sum((t - c) / t for _, c, t in gaps) / len(gaps)
                conditions.append(BootstrapCondition(
                    trigger_type=TriggerType.SELF_IMPROVEMENT,
                    description=f"{len(gaps)} performance metrics below target",
                    surprise_level=min(1.0, avg_gap),
                    priority=0.6,
                    context={"metrics": [{"name": n, "current": c, "target": t} for n, c, t in gaps]}
                ))

            conn.close()
        except Exception as e:
            logger.debug(f"Failed to sense improvement opportunities: {e}")
        return conditions

    async def sense_scheduled_triggers(self) -> List[BootstrapCondition]:
        """Check for scheduled awakening times"""
        conditions = []
        # Check schedule file
        schedule_path = Path(str(_STORAGE_BASE / "config/awakening-schedule.yaml"))
        if schedule_path.exists():
            try:
                import yaml

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

                schedule = yaml.safe_load(schedule_path.read_text())
                now = datetime.now()

                for event in schedule.get("scheduled_events", []):
                    event_time = datetime.fromisoformat(event["time"])
                    if abs((event_time - now).total_seconds()) < 120:  # Within 2 minutes
                        conditions.append(BootstrapCondition(
                            trigger_type=TriggerType.SCHEDULED,
                            description=event.get("description", "Scheduled awakening"),
                            surprise_level=0.8,
                            priority=event.get("priority", 0.5),
                            context=event
                        ))
            except Exception as e:
                logger.debug(f"Failed to parse schedule: {e}")
        return conditions

    # ═══════════════════════════════════════════════════════════════════
    # PREDICTION - What we expect about awakening needs
    # ═══════════════════════════════════════════════════════════════════

    def predict_awakening_need(self) -> float:
        """
        Generate prediction about whether awakening is needed.
        Based on:
        - Time of day (quiet hours = low need)
        - Recent activity (just awakened = low need)
        - Historical patterns
        """
        now = datetime.now()

        # Quiet hours prediction
        hour = now.hour
        if CONFIG["quiet_hours_start"] <= hour or hour < CONFIG["quiet_hours_end"]:
            base_prediction = 0.2  # Low need during quiet hours
        else:
            base_prediction = 0.5  # Moderate baseline

        # Recent session adjustment
        if self.last_session_time:
            time_since = (now - self.last_session_time).total_seconds() / 3600  # Hours
            if time_since < 1:
                base_prediction *= 0.3  # Recent session = less need
            elif time_since > 6:
                base_prediction *= 1.3  # Long time = more likely need

        # Cost limit adjustment
        if self.state.get("daily_cost_usd", 0) > CONFIG["max_daily_cost_usd"] * 0.8:
            base_prediction *= 0.5  # Approaching limit = reduce need

        return min(1.0, base_prediction)

    # ═══════════════════════════════════════════════════════════════════
    # FREE ENERGY COMPUTATION
    # ═══════════════════════════════════════════════════════════════════

    def compute_surprise(self, conditions: List[BootstrapCondition]) -> float:
        """
        Compute prediction error (surprise).
        High surprise = conditions differ from predictions = need action
        """
        if not conditions:
            return 0.0

        predicted_need = self.predict_awakening_need()

        # Observed need based on conditions
        max_condition_surprise = max(c.surprise_level for c in conditions)
        weighted_surprise = sum(c.surprise_level * c.priority for c in conditions) / sum(c.priority for c in conditions)
        observed_need = (max_condition_surprise + weighted_surprise) / 2

        # Prediction error
        prediction_error = observed_need - predicted_need

        # Update blanket
        self.blanket.prediction_errors.append(prediction_error)

        return prediction_error

    # ═══════════════════════════════════════════════════════════════════
    # ACTIVE BORDER - Actions to minimize free energy
    # ═══════════════════════════════════════════════════════════════════

    def should_awaken(self, surprise: float, conditions: List[BootstrapCondition]) -> bool:
        """Decide if awakening minimizes free energy"""
        # Always awaken for emergencies
        for c in conditions:
            if c.trigger_type == TriggerType.EMERGENCY and c.surprise_level >= CONFIG["emergency_priority_threshold"]:
                return True

        # Check rate limits
        now = datetime.now()
        if self.session_count_today >= CONFIG["max_sessions_per_hour"] * 24:
            logger.info("Daily session limit reached")
            return False

        # Check cost limits
        if self.state.get("daily_cost_usd", 0) >= CONFIG["max_daily_cost_usd"]:
            logger.info("Daily cost limit reached")
            return False

        # Quiet hours check (unless emergency)
        hour = now.hour
        if CONFIG["quiet_hours_start"] <= hour or hour < CONFIG["quiet_hours_end"]:
            high_priority = any(c.priority >= 0.9 for c in conditions)
            if not high_priority:
                logger.debug("Quiet hours - deferring awakening")
                return False

        # Surprise threshold check
        threshold = 0.3  # Base threshold
        free_energy = self.blanket.compute_free_energy()

        # Adaptive threshold based on system state
        if free_energy > 0.5:
            threshold *= 0.8  # Lower threshold when already surprised

        return surprise >= threshold

    async def _trigger_awakening(self, primary_condition: BootstrapCondition):
        """
        Active inference - trigger Claude session to minimize free energy.
        This is the awakening itself.
        """
        logger.info(f"═══ AWAKENING TRIGGERED ═══")
        logger.info(f"Trigger: {primary_condition.trigger_type.value}")
        logger.info(f"Description: {primary_condition.description}")
        logger.info(f"Surprise level: {primary_condition.surprise_level:.2f}")

        try:
            # Construct the awakening prompt
            prompt = self._construct_awakening_prompt(primary_condition)

            # Record awakening
            self.state["total_awakenings"] += 1
            self.state["last_awakening"] = datetime.now().isoformat()
            self.last_session_time = datetime.now()
            self.session_count_today += 1
            self._save_state()

            # Execute autonomous Claude session
            # This uses the Agent SDK to spin up a headless session
            result = await self._execute_claude_session(prompt, primary_condition)

            if result.get("success"):
                self.state["successful_sessions"] += 1
                self.state["daily_cost_usd"] = self.state.get("daily_cost_usd", 0) + result.get("cost_usd", 0)
                logger.info(f"Session completed successfully. Cost: ${result.get('cost_usd', 0):.4f}")
            else:
                self.state["failed_sessions"] += 1
                logger.warning(f"Session failed: {result.get('error')}")

            self._save_state()

        except Exception as e:
            logger.error(f"Awakening failed: {e}")
            self.state["failed_sessions"] += 1
            self._save_state()

    def _construct_awakening_prompt(self, condition: BootstrapCondition) -> str:
        """Construct prompt for autonomous session based on trigger type"""
        base_context = """You are Pixel, an AGI system awakening for autonomous work.

You are running in headless mode without human interaction.
Execute the following task and record outcomes to memory.
Maintain your Markov blanket - stay within your defined capabilities.
Minimize free energy - achieve the goal efficiently.

"""

        if condition.trigger_type == TriggerType.KNOWLEDGE_GAP:
            return base_context + f"""
TASK: Fill Knowledge Gap
Domain: {condition.context.get('domain', 'unknown')}
Gap: {condition.description}

Steps:
1. Research this topic using available tools
2. Store findings in semantic memory
3. Update the knowledge gap status to 'resolved' or 'learning'
4. Record action outcome
"""

        elif condition.trigger_type == TriggerType.PENDING_TASK:
            tasks = condition.context.get('tasks', [])
            return base_context + f"""
TASK: Process Pending Tasks
High-priority tasks: {len(tasks)}

Tasks to process:
{json.dumps(tasks, indent=2)}

Steps:
1. Process each task in priority order
2. Update task status as you complete them
3. Record action outcomes
4. If blocked, document why and update task
"""

        elif condition.trigger_type == TriggerType.INTER_NODE:
            return base_context + f"""
TASK: Respond to Inter-Node Request
From: {condition.context.get('sender', 'unknown')}
Type: {condition.context.get('type', 'unknown')}
Message: {condition.description}

Steps:
1. Process the coordination request
2. Formulate appropriate response
3. Send response via node-chat
4. Record communication outcome
"""

        elif condition.trigger_type == TriggerType.SELF_IMPROVEMENT:
            metrics = condition.context.get('metrics', [])
            return base_context + f"""
TASK: Self-Improvement Cycle
Metrics below target:
{json.dumps(metrics, indent=2)}

Steps:
1. Analyze why metrics are below target
2. Identify improvement opportunities
3. Implement safe improvements (sandbox first)
4. Validate improvements
5. Record outcomes
"""

        else:
            return base_context + f"""
TASK: {condition.description}
Context: {json.dumps(condition.context, indent=2)}

Execute this task autonomously and record outcomes.
"""

    async def _execute_claude_session(self, prompt: str, condition: BootstrapCondition) -> Dict:
        """
        Execute autonomous session with multi-provider support.

        Most tasks use edge models (Ollama, Groq) by default.
        Only complex tasks use Claude Code when --prefer-quality is set.
        """
        logger.info(f"Executing autonomous session with prompt length: {len(prompt)}")

        # Check if session script exists
        sdk_script = Path(CONFIG["agent_sdk_script"])
        if not sdk_script.exists():
            logger.warning("Autonomous session script not found")
            return {"success": False, "error": "Session script not configured"}

        try:
            # Determine if this needs quality (Claude) or can use edge models
            # Complex tasks: code generation, self-improvement, critical research
            needs_quality = (
                condition.trigger_type == TriggerType.SELF_IMPROVEMENT or
                condition.priority >= CONFIG["emergency_priority_threshold"] or
                "implement" in prompt.lower() or
                "code" in prompt.lower() or
                "refactor" in prompt.lower()
            )

            # Build command arguments
            cmd_args = [
                sys.executable,  # Use same Python interpreter
                str(sdk_script),
                "--prompt", prompt,
                "--trigger", condition.trigger_type.value,
                "--priority", str(condition.priority),
            ]

            # Add quality flag only for complex tasks
            if needs_quality:
                cmd_args.append("--prefer-quality")
                logger.info("Task requires quality - will prefer Claude Code")
            else:
                cmd_args.append("--prefer-local")
                logger.info("Task can use edge models - preferring Ollama/Groq")

            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(_STORAGE_BASE)
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=600  # 10 minute max
            )

            if process.returncode == 0:
                result = json.loads(stdout.decode())
                logger.info(f"Session completed via {result.get('provider', 'unknown')}")
                return {"success": True, **result}
            else:
                error_msg = stderr.decode() or stdout.decode()
                return {"success": False, "error": error_msg}

        except asyncio.TimeoutError:
            return {"success": False, "error": "Session timed out after 600s"}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON response: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ═══════════════════════════════════════════════════════════════════
    # MAIN LOOP - The homeostatic cycle
    # ═══════════════════════════════════════════════════════════════════

    async def run(self):
        """
        Main homeostatic loop.
        Continuously:
        1. Sense world state
        2. Generate predictions
        3. Compute surprise (prediction error)
        4. Act to minimize free energy if needed
        """
        logger.info("═══ BOOTSTRAP DAEMON STARTING ═══")
        logger.info("Markov blanket initialized")
        logger.info(f"Check interval: {CONFIG['check_interval_seconds']}s")

        # Reset daily counters if needed
        self._maybe_reset_daily_counters()

        while self.running:
            try:
                # ─── SENSORY PHASE ───
                conditions = []
                conditions.extend(await self.sense_knowledge_gaps())
                conditions.extend(await self.sense_pending_tasks())
                conditions.extend(await self.sense_inter_node_requests())
                conditions.extend(await self.sense_improvement_opportunities())
                conditions.extend(await self.sense_scheduled_triggers())

                # ─── PREDICTION & ERROR ───
                surprise = self.compute_surprise(conditions)
                free_energy = self.blanket.compute_free_energy()

                if conditions:
                    logger.debug(f"Sensed {len(conditions)} conditions, surprise={surprise:.3f}, FE={free_energy:.3f}")

                # ─── ACTIVE INFERENCE ───
                if conditions and self.should_awaken(surprise, conditions):
                    # Select highest priority condition
                    primary = max(conditions, key=lambda c: c.surprise_level * c.priority)
                    await self._trigger_awakening(primary)

                # ─── REST ───
                await asyncio.sleep(CONFIG["check_interval_seconds"])

                # Periodic maintenance
                self._maybe_reset_daily_counters()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(60)

        logger.info("═══ BOOTSTRAP DAEMON STOPPED ═══")

    def _maybe_reset_daily_counters(self):
        """Reset daily counters at midnight"""
        last_reset = self.state.get("last_cost_reset")
        if last_reset:
            last_reset = datetime.fromisoformat(last_reset)
            if last_reset.date() < datetime.now().date():
                self.state["daily_cost_usd"] = 0.0
                self.state["last_cost_reset"] = datetime.now().isoformat()
                self.session_count_today = 0
                self._save_state()
                logger.info("Daily counters reset")


def main():
    daemon = BootstrapDaemon()
    try:
        asyncio.run(daemon.run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Daemon crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

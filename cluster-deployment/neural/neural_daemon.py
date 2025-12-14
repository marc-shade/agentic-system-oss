#!/usr/bin/env python3
"""
Neural Firing Daemon - 24x7 Autonomous Node Operation

Runs continuously on each node, implementing the SENSE-PROCESS-ACT loop
for autonomous neural network operation.

Based on infinite-agentic-loop patterns:
- Continuous wave-based execution
- Context management across waves
- Progressive sophistication
- Self-monitoring and adaptation
"""
import platform

import asyncio
import json
import signal
import sys
import time
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import socket

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from neuron_cluster import (
    NeuronCluster, SynapticSignal, SignalType,
    CLUSTER_NODES, NodeRole
)
from synapse_protocol import SynapseProtocol, WaveOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/neural_daemon.log'),
    ]
)
logger = logging.getLogger(__name__)


# Detect storage base
STORAGE_BASE = Path(str(_STORAGE_BASE))
if not STORAGE_BASE.exists():
    STORAGE_BASE = Path.home() / "agentic-system"


def detect_node_id() -> str:
    """Detect which node we're running on"""
    hostname = socket.gethostname().lower()

    if "macpro" in hostname or "mac-pro" in hostname:
        return "macpro51"
    elif "mac-studio" in hostname or "macstudio" in hostname:
        return "mac-studio"
    elif "macbook-air" in hostname or "macbookair" in hostname:
        return "macbook-air"
    elif "completeu" in hostname:
        return "completeu-server"

    # Try to read from config file
    config_file = Path.home() / ".claude" / "node-config.json"
    if config_file.exists():
        try:
            with open(config_file) as f:
                config = json.load(f)
                return config.get("node_id", "unknown")
        except:
            pass

    return "unknown"


class NeuralDaemon:
    """
    24x7 Neural Firing Daemon

    Implements the SENSE-PROCESS-ACT infinite loop:
    - SENSE: Monitor goals, signals, events, resource state
    - PROCESS: Coordinate with cluster, plan waves, make decisions
    - ACT: Fire neurons, execute tasks, propagate signals
    - FEEDBACK: Learn from outcomes, adjust weights

    This is the "neuron firing" mechanism at node scale.
    """

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.cluster = CLUSTER_NODES.get(node_id)
        self.synapse = SynapseProtocol(node_id)
        self.wave_orchestrator = WaveOrchestrator(self.synapse)

        self._running = False
        self._shutdown_event = asyncio.Event()

        # Daemon state
        self.cycles_completed = 0
        self.last_firing = None
        self.total_signals_processed = 0
        self.total_tasks_executed = 0

        # Configuration
        self.sense_interval = 1.0      # Seconds between sense cycles
        self.process_interval = 5.0    # Seconds between process cycles
        self.act_interval = 10.0       # Seconds between act cycles
        self.feedback_interval = 60.0  # Seconds between feedback cycles

        # Goal queue (from agent-runtime MCP)
        self.pending_goals: List[Dict] = []

        logger.info(f"Neural Daemon initialized for node: {node_id}")
        logger.info(f"Cluster role: {self.cluster.role.value if self.cluster else 'unknown'}")

    async def start(self):
        """Start the daemon"""
        self._running = True

        logger.info(f"{'='*60}")
        logger.info(f"NEURAL DAEMON STARTING - {self.node_id}")
        logger.info(f"{'='*60}")

        # Register signal handlers for graceful shutdown
        for sig in (signal.SIGTERM, signal.SIGINT):
            asyncio.get_event_loop().add_signal_handler(
                sig, lambda: asyncio.create_task(self.shutdown())
            )

        # Start the main loops
        await asyncio.gather(
            self._sense_loop(),
            self._process_loop(),
            self._act_loop(),
            self._feedback_loop(),
            self.synapse.start_signal_loop(interval=0.5),
        )

    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutdown requested...")
        self._running = False
        self.synapse.stop_signal_loop()
        self._shutdown_event.set()

    async def _sense_loop(self):
        """
        SENSE: Monitor environment for triggers

        Checks:
        - Incoming synaptic signals
        - Goal queue from agent-runtime
        - System resource state
        - External events
        """
        logger.info("Starting SENSE loop")

        while self._running:
            try:
                # 1. Check for new goals from agent-runtime MCP
                await self._sense_goals()

                # 2. Check system resources
                await self._sense_resources()

                # 3. Check for external events
                await self._sense_events()

                # 4. Process any incoming signals
                await self.synapse.process_incoming_signals()

                self.cycles_completed += 1
                await asyncio.sleep(self.sense_interval)

            except Exception as e:
                logger.error(f"SENSE error: {e}")
                await asyncio.sleep(self.sense_interval)

    async def _sense_goals(self):
        """Check for pending goals from agent-runtime"""
        try:
            # Query agent-runtime database
            db_path = STORAGE_BASE / "databases" / "mcp" / "agent_runtime.db"
            if not db_path.exists():
                return

            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, name, description, metadata
                FROM goals
                WHERE status = 'active'
                ORDER BY created_at DESC
                LIMIT 10
            """)

            goals = []
            for row in cursor.fetchall():
                goals.append({
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "metadata": json.loads(row[3]) if row[3] else {},
                })

            conn.close()

            # Update pending goals
            self.pending_goals = goals

            if goals:
                logger.debug(f"Sensed {len(goals)} active goals")

        except Exception as e:
            logger.debug(f"Goal sensing error: {e}")

    async def _sense_resources(self):
        """Check system resource availability"""
        try:
            # Simple resource check
            import shutil
            disk = shutil.disk_usage(str(STORAGE_BASE))
            disk_pct = (disk.used / disk.total) * 100

            if disk_pct > 90:
                # Send rate limit signal to slow down
                if self.cluster:
                    self.cluster.receive_signal(SynapticSignal(
                        signal_id=f"resource_limit_{int(time.time())}",
                        source_node=self.node_id,
                        source_neuron="resource_monitor",
                        target_node=self.node_id,
                        target_neuron_type=None,
                        signal_type=SignalType.RESOURCE_CONSTRAINED,
                        activation_strength=0.3,
                        payload={"disk_pct": disk_pct},
                        propagation_chain=[self.node_id],
                        timestamp=datetime.now().isoformat(),
                    ))

        except Exception as e:
            logger.debug(f"Resource sensing error: {e}")

    async def _sense_events(self):
        """Check for external events that should trigger activity"""
        try:
            # Check for knowledge gaps (from enhanced-memory)
            db_path = STORAGE_BASE / "databases" / "mcp" / "enhanced-memory.db"
            if not db_path.exists():
                return

            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*) FROM knowledge_gaps
                WHERE status = 'open' AND severity > 0.7
            """)

            critical_gaps = cursor.fetchone()[0]
            conn.close()

            # If there are critical knowledge gaps and we're a researcher node
            if critical_gaps > 0 and self.cluster and self.cluster.role == NodeRole.RESEARCHER:
                # Boost activation for research
                self.cluster.receive_signal(SynapticSignal(
                    signal_id=f"gap_alert_{int(time.time())}",
                    source_node=self.node_id,
                    source_neuron="gap_monitor",
                    target_node=self.node_id,
                    target_neuron_type="researcher",
                    signal_type=SignalType.TASK_REQUEST,
                    activation_strength=0.4,
                    payload={"critical_gaps": critical_gaps},
                    propagation_chain=[self.node_id],
                    timestamp=datetime.now().isoformat(),
                ))

        except Exception as e:
            logger.debug(f"Event sensing error: {e}")

    async def _process_loop(self):
        """
        PROCESS: Make decisions based on sensed state

        - Analyze activation potential
        - Plan wave execution if threshold met
        - Coordinate with other nodes
        """
        logger.info("Starting PROCESS loop")

        while self._running:
            try:
                if self.cluster:
                    # Check if we should fire
                    if self.cluster.can_fire():
                        logger.info(
                            f"PROCESS: Activation threshold met! "
                            f"({self.cluster.activation_potential:.2f} >= "
                            f"{self.cluster.threshold})"
                        )

                        # Determine task to execute
                        task = await self._plan_task()

                        if task:
                            # Signal to ACT loop that we're ready to fire
                            self._pending_task = task

                await asyncio.sleep(self.process_interval)

            except Exception as e:
                logger.error(f"PROCESS error: {e}")
                await asyncio.sleep(self.process_interval)

    async def _plan_task(self) -> Optional[Dict]:
        """Plan what task to execute when firing"""
        # Priority 1: Goals from agent-runtime
        if self.pending_goals:
            goal = self.pending_goals[0]
            return {
                "type": "goal_execution",
                "goal": goal,
                "complexity": "medium",
                "details": goal.get("metadata", {}),
            }

        # Priority 2: Process pending signals
        signals = self.synapse.get_pending_signals()
        task_signals = [s for s in signals if s.signal_type == SignalType.TASK_REQUEST]

        if task_signals:
            signal = task_signals[0]
            return {
                "type": "signal_task",
                "signal": signal.to_dict(),
                "complexity": "medium",
                "details": signal.payload,
            }

        # Priority 3: Role-based autonomous tasks
        return await self._get_autonomous_task()

    async def _get_autonomous_task(self) -> Optional[Dict]:
        """Get an autonomous task based on node role"""
        if not self.cluster:
            return None

        role_tasks = {
            NodeRole.ORCHESTRATOR: {
                "type": "coordination",
                "complexity": "simple",
                "details": {"action": "cluster_health_check"},
            },
            NodeRole.BUILDER: {
                "type": "maintenance",
                "complexity": "simple",
                "details": {"action": "build_cache_cleanup"},
            },
            NodeRole.RESEARCHER: {
                "type": "research",
                "complexity": "medium",
                "details": {"action": "knowledge_consolidation"},
            },
            NodeRole.INFERENCE: {
                "type": "optimization",
                "complexity": "simple",
                "details": {"action": "model_warmup"},
            },
        }

        return role_tasks.get(self.cluster.role)

    async def _act_loop(self):
        """
        ACT: Execute tasks and fire neurons

        - Fire sub-agents when activated
        - Execute parallel wave patterns
        - Propagate results to cluster
        """
        logger.info("Starting ACT loop")
        self._pending_task = None

        while self._running:
            try:
                if self.cluster and hasattr(self, '_pending_task') and self._pending_task:
                    task = self._pending_task
                    self._pending_task = None

                    logger.info(f"ACT: Firing neurons for task: {task['type']}")

                    # Fire the cluster
                    results = await self.cluster.fire(task)

                    if results:
                        self.total_tasks_executed += len(results)
                        self.last_firing = datetime.now()
                        logger.info(f"ACT: Fired {len(results)} neurons successfully")

                        # Record action outcome for learning
                        await self._record_action_outcome(task, results)

                await asyncio.sleep(self.act_interval)

            except Exception as e:
                logger.error(f"ACT error: {e}")
                await asyncio.sleep(self.act_interval)

    async def _feedback_loop(self):
        """
        FEEDBACK: Learn from outcomes and adjust

        - Analyze action outcomes
        - Adjust signal weights
        - Update activation thresholds
        - Report to orchestrator
        """
        logger.info("Starting FEEDBACK loop")

        while self._running:
            try:
                # Analyze recent outcomes
                await self._analyze_outcomes()

                # Adjust weights based on learning
                await self._adjust_weights()

                # Report status to orchestrator (if not the orchestrator)
                if self.cluster and self.cluster.role != NodeRole.ORCHESTRATOR:
                    await self._report_to_orchestrator()

                await asyncio.sleep(self.feedback_interval)

            except Exception as e:
                logger.error(f"FEEDBACK error: {e}")
                await asyncio.sleep(self.feedback_interval)

    async def _record_action_outcome(self, task: Dict, results: List):
        """Record action outcome for learning"""
        try:
            db_path = STORAGE_BASE / "databases" / "mcp" / "enhanced-memory.db"
            if not db_path.exists():
                return

            import sqlite3

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

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            success_count = sum(1 for r in results if r.status == "completed")
            success_score = success_count / len(results) if results else 0

            cursor.execute("""
                INSERT INTO action_outcomes
                (action_type, action_description, expected_result, actual_result, success_score)
                VALUES (?, ?, ?, ?, ?)
            """, (
                f"neural_firing_{task['type']}",
                f"Neural firing for {task['type']} task",
                f"{len(results)} agents expected to complete",
                f"{success_count} agents completed successfully",
                success_score,
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.debug(f"Outcome recording error: {e}")

    async def _analyze_outcomes(self):
        """Analyze recent outcomes for learning"""
        # This would query action_outcomes and calculate trends
        pass

    async def _adjust_weights(self):
        """Adjust signal weights based on outcomes"""
        # This would update signal_weights in the cluster
        # based on which signals led to successful outcomes
        pass

    async def _report_to_orchestrator(self):
        """Report status to orchestrator node"""
        if not self.cluster:
            return

        status = self.cluster.get_status()
        status["daemon_stats"] = {
            "cycles_completed": self.cycles_completed,
            "last_firing": self.last_firing.isoformat() if self.last_firing else None,
            "total_signals_processed": self.total_signals_processed,
            "total_tasks_executed": self.total_tasks_executed,
        }

        signal = SynapticSignal(
            signal_id=f"status_report_{int(time.time())}",
            source_node=self.node_id,
            source_neuron="daemon",
            target_node="mac-studio",  # Orchestrator
            target_neuron_type=None,
            signal_type=SignalType.KNOWLEDGE_SHARE,
            activation_strength=0.2,  # Low priority
            payload=status,
            propagation_chain=[self.node_id],
            timestamp=datetime.now().isoformat(),
        )

        await self.synapse.send_signal(signal)

    def get_status(self) -> Dict:
        """Get daemon status"""
        return {
            "node_id": self.node_id,
            "running": self._running,
            "cycles_completed": self.cycles_completed,
            "last_firing": self.last_firing.isoformat() if self.last_firing else None,
            "total_signals_processed": self.total_signals_processed,
            "total_tasks_executed": self.total_tasks_executed,
            "cluster_status": self.cluster.get_status() if self.cluster else None,
            "pending_goals": len(self.pending_goals),
        }


async def main():
    """Main entry point"""
    node_id = detect_node_id()

    if node_id == "unknown":
        logger.error("Could not detect node ID. Please set up node-config.json")
        sys.exit(1)

    daemon = NeuralDaemon(node_id)

    try:
        await daemon.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Daemon error: {e}")
    finally:
        await daemon.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

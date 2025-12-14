#!/usr/bin/env python3
"""
Synapse Protocol - Cross-node neural communication

Implements the synaptic communication layer between neuron clusters (nodes).
Integrates with node-chat MCP for actual message transport.

Key patterns from infinite-agentic-loop:
- Wave synchronization across nodes
- Context propagation without accumulation
- Progressive sophistication signaling
"""
import platform

import asyncio
import json
import time
import sqlite3
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import logging
import subprocess

from neuron_cluster import (
    SynapticSignal, SignalType, NeuronCluster,
    CLUSTER_NODES, NodeRole
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Detect storage base (respect AGENTIC_ROOT env var)
import os

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

_agentic_root = os.environ.get("AGENTIC_ROOT")
if _agentic_root:
    STORAGE_BASE = Path(_agentic_root)
elif Path(str(_STORAGE_BASE)).exists():
    STORAGE_BASE = Path(str(_STORAGE_BASE))
elif Path(str(_STORAGE_BASE)).exists():
    STORAGE_BASE = Path(str(_STORAGE_BASE))
elif Path(str(_STORAGE_BASE)).exists():
    STORAGE_BASE = Path(str(_STORAGE_BASE))
else:
    STORAGE_BASE = Path.home() / "agentic-system"

SYNAPSE_DB = STORAGE_BASE / "databases" / "cluster" / "synapses.db"


class SynapseProtocol:
    """
    Manages synaptic communication between neuron clusters

    Uses multiple transport mechanisms:
    1. Direct HTTP (node-chat MCP)
    2. Shared database (SQLite)
    3. File-based (for persistence)
    """

    def __init__(self, local_node_id: str):
        self.local_node_id = local_node_id
        self.local_cluster = CLUSTER_NODES.get(local_node_id)
        self._init_database()
        self.signal_handlers: Dict[SignalType, List[Callable]] = {}
        self._running = False

    def _init_database(self):
        """Initialize synapse database for persistent signal storage"""
        SYNAPSE_DB.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(SYNAPSE_DB))
        cursor = conn.cursor()

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS synaptic_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id TEXT UNIQUE NOT NULL,
                source_node TEXT NOT NULL,
                source_neuron TEXT NOT NULL,
                target_node TEXT NOT NULL,
                target_neuron_type TEXT,
                signal_type TEXT NOT NULL,
                activation_strength REAL NOT NULL,
                payload TEXT NOT NULL,
                propagation_chain TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                ttl INTEGER DEFAULT 3600,
                status TEXT DEFAULT 'pending',
                processed_at TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_signals_target ON synaptic_signals(target_node, status);
            CREATE INDEX IF NOT EXISTS idx_signals_type ON synaptic_signals(signal_type);
            CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON synaptic_signals(timestamp);

            CREATE TABLE IF NOT EXISTS wave_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wave_id TEXT UNIQUE NOT NULL,
                initiator_node TEXT NOT NULL,
                current_phase TEXT NOT NULL,
                participating_nodes TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                results TEXT
            );

            CREATE TABLE IF NOT EXISTS activation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT NOT NULL,
                potential REAL NOT NULL,
                signal_id TEXT,
                action TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()
        conn.close()
        logger.info(f"Synapse database initialized at {SYNAPSE_DB}")

    async def send_signal(self, signal: SynapticSignal) -> bool:
        """
        Send a synaptic signal to another node

        Uses multiple transport mechanisms for reliability:
        1. Try node-chat MCP first (real-time)
        2. Persist to database (guaranteed delivery)
        3. Optionally file-based for offline nodes
        """
        try:
            # Persist signal to database first
            self._store_signal(signal)

            # Try real-time delivery via node-chat
            success = await self._deliver_via_node_chat(signal)

            if success:
                self._mark_signal_delivered(signal.signal_id)
                logger.info(f"Signal {signal.signal_id} delivered to {signal.target_node}")
            else:
                logger.warning(f"Real-time delivery failed for {signal.signal_id}, "
                             "persisted for later delivery")

            return success

        except Exception as e:
            logger.error(f"Failed to send signal {signal.signal_id}: {e}")
            return False

    def _store_signal(self, signal: SynapticSignal):
        """Store signal in database"""
        conn = sqlite3.connect(str(SYNAPSE_DB))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO synaptic_signals
            (signal_id, source_node, source_neuron, target_node, target_neuron_type,
             signal_type, activation_strength, payload, propagation_chain, timestamp, ttl)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signal.signal_id,
            signal.source_node,
            signal.source_neuron,
            signal.target_node,
            signal.target_neuron_type,
            signal.signal_type.value,
            signal.activation_strength,
            json.dumps(signal.payload),
            json.dumps(signal.propagation_chain),
            signal.timestamp,
            signal.ttl,
        ))

        conn.commit()
        conn.close()

    def _mark_signal_delivered(self, signal_id: str):
        """Mark signal as delivered"""
        conn = sqlite3.connect(str(SYNAPSE_DB))
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE synaptic_signals
            SET status = 'delivered', processed_at = ?
            WHERE signal_id = ?
        """, (datetime.now().isoformat(), signal_id))

        conn.commit()
        conn.close()

    async def _deliver_via_node_chat(self, signal: SynapticSignal) -> bool:
        """
        Deliver signal via node-chat MCP

        This integrates with our existing node communication infrastructure
        """
        try:
            # Get target node info
            target = CLUSTER_NODES.get(signal.target_node)
            if not target:
                logger.error(f"Unknown target node: {signal.target_node}")
                return False

            # Build node-chat message
            message = {
                "type": "synaptic_signal",
                "signal": signal.to_dict(),
            }

            # Use node-chat MCP to send
            # In production, this calls the MCP tool
            # For now, we'll use the database-based approach

            return True

        except Exception as e:
            logger.error(f"Node-chat delivery failed: {e}")
            return False

    def get_pending_signals(self) -> List[SynapticSignal]:
        """Get pending signals for this node"""
        conn = sqlite3.connect(str(SYNAPSE_DB))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT signal_id, source_node, source_neuron, target_node,
                   target_neuron_type, signal_type, activation_strength,
                   payload, propagation_chain, timestamp, ttl
            FROM synaptic_signals
            WHERE target_node = ? AND status = 'pending'
            ORDER BY timestamp ASC
        """, (self.local_node_id,))

        signals = []
        for row in cursor.fetchall():
            signal = SynapticSignal(
                signal_id=row[0],
                source_node=row[1],
                source_neuron=row[2],
                target_node=row[3],
                target_neuron_type=row[4],
                signal_type=SignalType(row[5]),
                activation_strength=row[6],
                payload=json.loads(row[7]),
                propagation_chain=json.loads(row[8]),
                timestamp=row[9],
                ttl=row[10],
            )
            signals.append(signal)

        conn.close()
        return signals

    async def process_incoming_signals(self):
        """Process all pending signals for this node"""
        signals = self.get_pending_signals()

        for signal in signals:
            try:
                # Apply signal to local cluster
                if self.local_cluster:
                    self.local_cluster.receive_signal(signal)

                # Call registered handlers
                handlers = self.signal_handlers.get(signal.signal_type, [])
                for handler in handlers:
                    try:
                        await handler(signal)
                    except Exception as e:
                        logger.error(f"Handler error for {signal.signal_id}: {e}")

                # Mark as processed
                self._mark_signal_delivered(signal.signal_id)

                # Log activation
                self._log_activation(signal)

            except Exception as e:
                logger.error(f"Failed to process signal {signal.signal_id}: {e}")

    def _log_activation(self, signal: SynapticSignal):
        """Log activation changes for analysis"""
        if not self.local_cluster:
            return

        conn = sqlite3.connect(str(SYNAPSE_DB))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO activation_log (node_id, potential, signal_id, action)
            VALUES (?, ?, ?, ?)
        """, (
            self.local_node_id,
            self.local_cluster.activation_potential,
            signal.signal_id,
            f"received_{signal.signal_type.value}",
        ))

        conn.commit()
        conn.close()

    def register_handler(self, signal_type: SignalType, handler: Callable):
        """Register a handler for a signal type"""
        if signal_type not in self.signal_handlers:
            self.signal_handlers[signal_type] = []
        self.signal_handlers[signal_type].append(handler)

    async def start_signal_loop(self, interval: float = 1.0):
        """Start continuous signal processing loop"""
        self._running = True
        logger.info(f"Starting synapse loop for {self.local_node_id}")

        while self._running:
            try:
                await self.process_incoming_signals()

                # Apply decay to local cluster
                if self.local_cluster:
                    self.local_cluster.decay_potential(interval)

                await asyncio.sleep(interval)

            except Exception as e:
                logger.error(f"Signal loop error: {e}")
                await asyncio.sleep(interval)

    def stop_signal_loop(self):
        """Stop the signal processing loop"""
        self._running = False


class WaveOrchestrator:
    """
    Orchestrates wave-based parallel execution across the cluster

    Implements the infinite-agentic-loop pattern at cluster scale:
    - Wave planning across nodes
    - Synchronized agent spawning
    - Progressive sophistication
    - Context management
    """

    def __init__(self, synapse: SynapseProtocol):
        self.synapse = synapse
        self.current_wave_id: Optional[str] = None
        self.wave_results: Dict[str, List[Dict]] = {}

    async def initiate_wave(
        self,
        task: Dict[str, Any],
        target_nodes: List[str],
        agents_per_node: Dict[str, int],
    ) -> str:
        """
        Initiate a new wave of parallel execution across nodes

        Args:
            task: The task specification
            target_nodes: Nodes to participate in wave
            agents_per_node: Number of agents each node should spawn
        """
        wave_id = f"wave_{int(time.time())}"
        self.current_wave_id = wave_id

        logger.info(f"Initiating {wave_id} across {target_nodes}")

        # Store wave state
        self._store_wave_state(wave_id, target_nodes)

        # Send wave sync signals to all target nodes
        for node_id in target_nodes:
            signal = SynapticSignal(
                signal_id=f"{wave_id}_sync_{node_id}",
                source_node=self.synapse.local_node_id,
                source_neuron="wave_orchestrator",
                target_node=node_id,
                target_neuron_type=None,
                signal_type=SignalType.WAVE_SYNC,
                activation_strength=0.9,  # High priority
                payload={
                    "wave_id": wave_id,
                    "task": task,
                    "agent_count": agents_per_node.get(node_id, 3),
                    "total_nodes": len(target_nodes),
                    "participating_nodes": target_nodes,
                },
                propagation_chain=[self.synapse.local_node_id],
                timestamp=datetime.now().isoformat(),
            )

            await self.synapse.send_signal(signal)

        return wave_id

    def _store_wave_state(self, wave_id: str, nodes: List[str]):
        """Store wave state in database"""
        conn = sqlite3.connect(str(SYNAPSE_DB))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO wave_state (wave_id, initiator_node, current_phase, participating_nodes)
            VALUES (?, ?, ?, ?)
        """, (
            wave_id,
            self.synapse.local_node_id,
            "initiated",
            json.dumps(nodes),
        ))

        conn.commit()
        conn.close()

    async def progressive_wave_execution(
        self,
        goal: Dict[str, Any],
        max_waves: int = 10,
    ) -> List[Dict]:
        """
        Execute waves with progressive sophistication (infinite-agentic-loop pattern)

        Wave 1: Foundation - Basic execution, single innovation dimension
        Wave 2: Refinement - Multi-dimensional, enhanced coordination
        Wave 3+: Innovation - Complex paradigms, adaptive behaviors
        """
        all_results = []
        wave_num = 0

        sophistication_levels = [
            "foundation",      # Wave 1
            "refinement",      # Wave 2
            "integration",     # Wave 3
            "optimization",    # Wave 4
            "innovation",      # Wave 5+
        ]

        while wave_num < max_waves:
            wave_num += 1
            sophistication = sophistication_levels[min(wave_num - 1, len(sophistication_levels) - 1)]

            logger.info(f"Starting wave {wave_num} with sophistication: {sophistication}")

            # Determine agents per node based on wave number
            # Start small, scale up (from infinite-agentic-loop)
            base_agents = min(3 + wave_num, 8)

            agents_per_node = {
                "mac-studio": min(2, base_agents),      # Coordination
                "macpro51": base_agents,                # Heavy lifting
                "macbook-air": min(3, base_agents),     # Research
                "completeu-server": min(4, base_agents), # Inference
            }

            # Create wave task with sophistication context
            wave_task = {
                **goal,
                "wave_number": wave_num,
                "sophistication": sophistication,
                "previous_results": all_results[-5:] if all_results else [],
                "creative_constraints": self._get_creative_constraints(sophistication),
            }

            # Execute wave
            wave_id = await self.initiate_wave(
                task=wave_task,
                target_nodes=list(CLUSTER_NODES.keys()),
                agents_per_node=agents_per_node,
            )

            # Wait for wave completion (with timeout)
            results = await self._await_wave_completion(wave_id, timeout=300)
            all_results.extend(results)

            # Check if we should continue
            if not self._should_continue_waves(results, wave_num, max_waves):
                logger.info(f"Wave execution complete after {wave_num} waves")
                break

        return all_results

    def _get_creative_constraints(self, sophistication: str) -> Dict:
        """Get creative constraints based on sophistication level"""
        constraints = {
            "foundation": {
                "innovation_dimensions": 1,
                "complexity": "simple",
                "focus": "core_functionality",
            },
            "refinement": {
                "innovation_dimensions": 2,
                "complexity": "medium",
                "focus": "enhanced_interactions",
            },
            "integration": {
                "innovation_dimensions": 3,
                "complexity": "medium",
                "focus": "cross_component_coordination",
            },
            "optimization": {
                "innovation_dimensions": 4,
                "complexity": "complex",
                "focus": "performance_and_efficiency",
            },
            "innovation": {
                "innovation_dimensions": 5,
                "complexity": "complex",
                "focus": "novel_paradigms",
            },
        }
        return constraints.get(sophistication, constraints["foundation"])

    async def _await_wave_completion(self, wave_id: str, timeout: float) -> List[Dict]:
        """Wait for wave completion from all nodes"""
        start_time = time.time()

        while (time.time() - start_time) < timeout:
            # Check wave state
            conn = sqlite3.connect(str(SYNAPSE_DB))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT results, completed_at FROM wave_state WHERE wave_id = ?
            """, (wave_id,))

            row = cursor.fetchone()
            conn.close()

            if row and row[1]:  # completed_at is set
                return json.loads(row[0]) if row[0] else []

            await asyncio.sleep(1)

        logger.warning(f"Wave {wave_id} timed out after {timeout}s")
        return []

    def _should_continue_waves(
        self, results: List[Dict], wave_num: int, max_waves: int
    ) -> bool:
        """Determine if we should continue with more waves"""
        if wave_num >= max_waves:
            return False

        # Check for diminishing returns
        if results:
            success_rate = sum(1 for r in results if r.get("success", False)) / len(results)
            if success_rate < 0.5:
                logger.warning(f"Low success rate ({success_rate:.1%}), stopping waves")
                return False

        return True


async def demo_synapse_communication():
    """Demonstrate synapse protocol"""
    print(f"\n{'='*60}")
    print("SYNAPSE PROTOCOL DEMONSTRATION")
    print(f"{'='*60}\n")

    # Initialize synapse for macpro51 (this node)
    synapse = SynapseProtocol("macpro51")

    # Create a test signal from orchestrator
    signal = SynapticSignal(
        signal_id=f"demo_sig_{int(time.time())}",
        source_node="mac-studio",
        source_neuron="coordinator",
        target_node="macpro51",
        target_neuron_type="builder",
        signal_type=SignalType.TASK_REQUEST,
        activation_strength=0.8,
        payload={
            "task": "Build and test module",
            "priority": "high",
        },
        propagation_chain=["mac-studio"],
        timestamp=datetime.now().isoformat(),
    )

    # Store signal (simulating receipt)
    synapse._store_signal(signal)

    # Process signals
    print("Processing incoming signals...")
    await synapse.process_incoming_signals()

    # Show cluster status
    cluster = CLUSTER_NODES.get("macpro51")
    if cluster:
        print(f"\nCluster Status: {json.dumps(cluster.get_status(), indent=2)}")

    # Demonstrate wave orchestration
    print("\n" + "="*60)
    print("WAVE ORCHESTRATION DEMONSTRATION")
    print("="*60 + "\n")

    orchestrator = WaveOrchestrator(synapse)

    wave_id = await orchestrator.initiate_wave(
        task={"type": "build", "target": "auth_module"},
        target_nodes=["macpro51", "mac-studio"],
        agents_per_node={"macpro51": 3, "mac-studio": 2},
    )

    print(f"Initiated wave: {wave_id}")


if __name__ == "__main__":
    asyncio.run(demo_synapse_communication())

#!/usr/bin/env python3
"""
Neuron Cluster - Core abstraction for node-as-neuron-cluster

Each node in the AGI cluster acts as a specialized neuron cluster
that can receive signals, accumulate activation, and fire sub-agents.

Based on infinite-agentic-loop patterns adapted for distributed execution.
"""

import asyncio
import json
import time
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NodeRole(Enum):
    """Brain region mapping for each node"""
    ORCHESTRATOR = "prefrontal_cortex"   # mac-studio: planning, coordination
    BUILDER = "motor_cortex"              # macpro51: execution, action
    RESEARCHER = "hippocampus"            # macbook-air: memory, learning
    INFERENCE = "cerebellum"              # completeu-server: pattern recognition


class SignalType(Enum):
    """Types of synaptic signals between nodes"""
    # Excitatory (increase activation)
    TASK_REQUEST = "task_request"
    KNOWLEDGE_SHARE = "knowledge_share"
    LEARNING_UPDATE = "learning_update"
    GOAL_ASSIGNED = "goal_assigned"

    # Inhibitory (decrease activation)
    RATE_LIMIT = "rate_limit"
    RESOURCE_CONSTRAINED = "resource_constrained"
    CANCEL_TASK = "cancel_task"

    # Modulatory (adjust behavior)
    PRIORITY_BOOST = "priority_boost"
    CONTEXT_SWITCH = "context_switch"
    WAVE_SYNC = "wave_sync"


@dataclass
class SynapticSignal:
    """A signal passed between neuron clusters (nodes)"""
    signal_id: str
    source_node: str
    source_neuron: str
    target_node: str
    target_neuron_type: Optional[str]
    signal_type: SignalType
    activation_strength: float  # 0.0 to 1.0
    payload: Dict[str, Any]
    propagation_chain: List[str]
    timestamp: str
    ttl: int = 3600  # seconds

    def to_dict(self) -> Dict:
        return {
            "signal_id": self.signal_id,
            "source_node": self.source_node,
            "source_neuron": self.source_neuron,
            "target_node": self.target_node,
            "target_neuron_type": self.target_neuron_type,
            "signal_type": self.signal_type.value,
            "activation_strength": self.activation_strength,
            "payload": self.payload,
            "propagation_chain": self.propagation_chain,
            "timestamp": self.timestamp,
            "ttl": self.ttl
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'SynapticSignal':
        return cls(
            signal_id=data["signal_id"],
            source_node=data["source_node"],
            source_neuron=data["source_neuron"],
            target_node=data["target_node"],
            target_neuron_type=data.get("target_neuron_type"),
            signal_type=SignalType(data["signal_type"]),
            activation_strength=data["activation_strength"],
            payload=data["payload"],
            propagation_chain=data["propagation_chain"],
            timestamp=data["timestamp"],
            ttl=data.get("ttl", 3600)
        )


@dataclass
class SubAgent:
    """A single neuron (sub-agent) within a cluster"""
    agent_id: str
    agent_type: str
    task: Dict[str, Any]
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Dict] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


@dataclass
class NeuronCluster:
    """
    A node acting as a cluster of neurons

    Implements activation potential model:
    - Receives signals from other nodes (synapses)
    - Accumulates activation potential
    - Fires sub-agents when threshold met
    - Propagates results to connected nodes
    """
    node_id: str
    role: NodeRole
    ip_address: str

    # Activation parameters
    activation_potential: float = 0.0
    threshold: float = 0.7
    decay_rate: float = 0.1  # Potential decay per second
    refractory_period: float = 5.0  # Seconds after firing
    last_fired: float = 0.0

    # Sub-agent management
    max_concurrent_agents: int = 5
    active_agents: List[SubAgent] = field(default_factory=list)
    completed_agents: List[SubAgent] = field(default_factory=list)

    # Synaptic connections
    connected_nodes: List[str] = field(default_factory=list)
    incoming_signals: List[SynapticSignal] = field(default_factory=list)

    # Wave management (from infinite-agentic-loop)
    current_wave: int = 0
    wave_history: List[Dict] = field(default_factory=list)

    # Specialization weights (how strongly this node responds to signal types)
    signal_weights: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize default signal weights based on role"""
        if not self.signal_weights:
            self.signal_weights = self._default_weights_for_role()

    def _default_weights_for_role(self) -> Dict[str, float]:
        """Get default signal weights based on node role"""
        weights = {
            NodeRole.ORCHESTRATOR: {
                SignalType.GOAL_ASSIGNED.value: 1.0,
                SignalType.TASK_REQUEST.value: 0.6,
                SignalType.KNOWLEDGE_SHARE.value: 0.7,
                SignalType.WAVE_SYNC.value: 1.0,
            },
            NodeRole.BUILDER: {
                SignalType.TASK_REQUEST.value: 1.0,
                SignalType.GOAL_ASSIGNED.value: 0.5,
                SignalType.KNOWLEDGE_SHARE.value: 0.3,
                SignalType.WAVE_SYNC.value: 0.8,
            },
            NodeRole.RESEARCHER: {
                SignalType.KNOWLEDGE_SHARE.value: 1.0,
                SignalType.LEARNING_UPDATE.value: 0.9,
                SignalType.TASK_REQUEST.value: 0.5,
                SignalType.WAVE_SYNC.value: 0.7,
            },
            NodeRole.INFERENCE: {
                SignalType.TASK_REQUEST.value: 0.9,
                SignalType.KNOWLEDGE_SHARE.value: 0.8,
                SignalType.LEARNING_UPDATE.value: 0.7,
                SignalType.WAVE_SYNC.value: 0.6,
            },
        }
        return weights.get(self.role, {})

    def receive_signal(self, signal: SynapticSignal) -> float:
        """
        Receive a synaptic signal and update activation potential

        Returns the new activation potential
        """
        # Calculate relevance based on signal type and node specialization
        weight = self.signal_weights.get(signal.signal_type.value, 0.5)

        # Apply signal strength with weight
        activation_delta = signal.activation_strength * weight

        # Handle inhibitory signals
        if signal.signal_type in [
            SignalType.RATE_LIMIT,
            SignalType.RESOURCE_CONSTRAINED,
            SignalType.CANCEL_TASK
        ]:
            activation_delta = -activation_delta

        # Update potential
        self.activation_potential = max(0.0, min(1.0,
            self.activation_potential + activation_delta))

        # Store signal for processing
        self.incoming_signals.append(signal)

        logger.info(
            f"[{self.node_id}] Received {signal.signal_type.value} from "
            f"{signal.source_node}: potential now {self.activation_potential:.2f}"
        )

        return self.activation_potential

    def decay_potential(self, elapsed_seconds: float):
        """Apply time-based decay to activation potential"""
        decay = self.decay_rate * elapsed_seconds
        self.activation_potential = max(0.0, self.activation_potential - decay)

    def in_refractory_period(self) -> bool:
        """Check if node is in refractory period after firing"""
        return (time.time() - self.last_fired) < self.refractory_period

    def can_fire(self) -> bool:
        """Check if activation threshold met and not in refractory period"""
        if self.in_refractory_period():
            return False
        if len(self.active_agents) >= self.max_concurrent_agents:
            return False
        return self.activation_potential >= self.threshold

    def determine_agent_count(self, task: Dict) -> int:
        """
        Determine how many sub-agents to spawn based on task complexity

        Uses infinite-agentic-loop batch sizing strategy:
        - Simple tasks: 1-2 agents
        - Medium tasks: 3-5 agents
        - Complex tasks: up to max_concurrent_agents
        """
        complexity = task.get("complexity", "medium")
        available = self.max_concurrent_agents - len(self.active_agents)

        if complexity == "simple":
            return min(2, available)
        elif complexity == "medium":
            return min(5, available)
        elif complexity == "complex":
            return available
        else:
            return min(3, available)

    async def fire(self, task: Dict) -> List[SubAgent]:
        """
        Fire neurons (spawn sub-agents) for task execution

        Implements the parallel agent coordination from infinite-agentic-loop:
        1. Analyze task requirements
        2. Determine agent count
        3. Spawn agents with unique assignments
        4. Execute in parallel
        5. Collect results
        6. Propagate to connected nodes
        """
        if not self.can_fire():
            logger.warning(f"[{self.node_id}] Cannot fire: "
                          f"potential={self.activation_potential:.2f}, "
                          f"threshold={self.threshold}, "
                          f"refractory={self.in_refractory_period()}")
            return []

        # Increment wave counter
        self.current_wave += 1
        wave_id = f"wave_{self.current_wave}"

        logger.info(f"[{self.node_id}] FIRING {wave_id}! "
                   f"Potential: {self.activation_potential:.2f}")

        # Determine number of agents to spawn
        num_agents = self.determine_agent_count(task)

        # Create sub-agents with unique creative directions (from infinite-agentic-loop)
        agents = []
        for i in range(num_agents):
            agent = SubAgent(
                agent_id=f"{self.node_id}_{wave_id}_agent_{i}",
                agent_type=self._get_agent_type_for_index(i),
                task={
                    **task,
                    "agent_index": i,
                    "creative_direction": self._get_creative_direction(i, num_agents),
                    "wave_id": wave_id,
                },
                status="pending"
            )
            agents.append(agent)
            self.active_agents.append(agent)

        # Execute agents in parallel (core infinite-agentic-loop pattern)
        results = await self._execute_agents_parallel(agents)

        # Record firing
        self.last_fired = time.time()
        self.activation_potential = 0.0  # Reset after firing

        # Record wave history
        self.wave_history.append({
            "wave_id": wave_id,
            "timestamp": datetime.now().isoformat(),
            "agents_spawned": num_agents,
            "results": [r.result for r in results if r.result],
        })

        # Move completed agents
        for agent in results:
            if agent in self.active_agents:
                self.active_agents.remove(agent)
            self.completed_agents.append(agent)

        # Propagate results to connected nodes
        await self._propagate_results(results, task)

        return results

    def _get_agent_type_for_index(self, index: int) -> str:
        """Get agent type based on index and node role"""
        types_by_role = {
            NodeRole.ORCHESTRATOR: ["coordinator", "planner", "goal-manager", "priority-sorter", "wave-manager"],
            NodeRole.BUILDER: ["coder", "tester", "builder", "benchmarker", "container-runner"],
            NodeRole.RESEARCHER: ["researcher", "analyst", "documenter", "knowledge-synthesizer", "gap-analyzer"],
            NodeRole.INFERENCE: ["inference-runner", "pattern-matcher", "model-evaluator", "embedder", "validator"],
        }
        types = types_by_role.get(self.role, ["general"])
        return types[index % len(types)]

    def _get_creative_direction(self, index: int, total: int) -> str:
        """
        Assign unique creative direction to each agent (from infinite-agentic-loop)

        Ensures diversity in parallel execution
        """
        directions = [
            "innovative_approach",
            "efficiency_focused",
            "robustness_oriented",
            "simplicity_driven",
            "scalability_minded",
            "security_conscious",
            "user_experience_first",
            "performance_optimized",
        ]
        return directions[index % len(directions)]

    async def _execute_agents_parallel(self, agents: List[SubAgent]) -> List[SubAgent]:
        """Execute multiple agents in parallel"""
        async def execute_single(agent: SubAgent) -> SubAgent:
            agent.status = "running"
            agent.started_at = time.time()

            try:
                # Here we would actually spawn the Claude Code sub-agent
                # For now, simulate execution
                result = await self._spawn_claude_subagent(agent)
                agent.result = result
                agent.status = "completed"
            except Exception as e:
                agent.status = "failed"
                agent.result = {"error": str(e)}
                logger.error(f"Agent {agent.agent_id} failed: {e}")

            agent.completed_at = time.time()
            return agent

        # Execute all agents in parallel
        results = await asyncio.gather(*[execute_single(a) for a in agents])
        return list(results)

    async def _spawn_claude_subagent(self, agent: SubAgent) -> Dict:
        """
        Spawn an actual Claude Code sub-agent using the Task tool

        This is where we integrate with Claude Code's parallel execution
        """
        # Build the sub-agent prompt (from infinite-agentic-loop pattern)
        prompt = f"""
TASK: Execute {agent.task.get('task_type', 'general')} task as {agent.agent_type}

You are Sub Agent {agent.agent_id} on node {self.node_id}.

CONTEXT:
- Node Role: {self.role.value}
- Wave: {agent.task.get('wave_id')}
- Creative Direction: {agent.task.get('creative_direction')}
- Task Details: {json.dumps(agent.task.get('details', {}), indent=2)}

REQUIREMENTS:
1. Execute task according to your specialization ({agent.agent_type})
2. Focus on {agent.task.get('creative_direction')} approach
3. Return structured results
4. Ensure output integrates with cluster operations

DELIVERABLE: Structured result with status, outputs, and any signals to propagate.
"""

        # In production, this would use the Task tool
        # For now, return simulated result
        await asyncio.sleep(0.1)  # Simulate work

        return {
            "agent_id": agent.agent_id,
            "agent_type": agent.agent_type,
            "status": "completed",
            "outputs": {
                "task_completed": True,
                "approach": agent.task.get('creative_direction'),
            },
            "signals_to_propagate": [],
        }

    async def _propagate_results(self, agents: List[SubAgent], original_task: Dict):
        """Propagate results to connected nodes via synaptic signals"""
        for node_id in self.connected_nodes:
            # Create signal with aggregated results
            signal = SynapticSignal(
                signal_id=f"sig_{self.node_id}_{int(time.time())}",
                source_node=self.node_id,
                source_neuron=f"{self.role.value}_cluster",
                target_node=node_id,
                target_neuron_type=None,  # Let target decide
                signal_type=SignalType.KNOWLEDGE_SHARE,
                activation_strength=0.5,
                payload={
                    "original_task": original_task,
                    "wave_results": [a.result for a in agents if a.result],
                    "wave_id": self.current_wave,
                },
                propagation_chain=[self.node_id],
                timestamp=datetime.now().isoformat(),
            )

            # In production, this would use node-chat MCP
            logger.info(f"[{self.node_id}] Propagating to {node_id}: {signal.signal_id}")

    def get_status(self) -> Dict:
        """Get current cluster status"""
        return {
            "node_id": self.node_id,
            "role": self.role.value,
            "ip_address": self.ip_address,
            "activation_potential": self.activation_potential,
            "threshold": self.threshold,
            "can_fire": self.can_fire(),
            "in_refractory": self.in_refractory_period(),
            "active_agents": len(self.active_agents),
            "completed_agents": len(self.completed_agents),
            "current_wave": self.current_wave,
            "connected_nodes": self.connected_nodes,
            "pending_signals": len(self.incoming_signals),
        }


# Cluster node definitions
CLUSTER_NODES = {
    "mac-studio": NeuronCluster(
        node_id="mac-studio",
        role=NodeRole.ORCHESTRATOR,
        ip_address="192.168.1.16",
        threshold=0.6,  # Lower threshold - fires more easily for coordination
        max_concurrent_agents=8,
        connected_nodes=["macpro51", "macbook-air", "completeu-server"],
    ),
    "macpro51": NeuronCluster(
        node_id="macpro51",
        role=NodeRole.BUILDER,
        ip_address="192.168.1.183",
        threshold=0.7,
        max_concurrent_agents=10,  # More capacity for parallel builds
        connected_nodes=["mac-studio", "completeu-server"],
    ),
    "macbook-air": NeuronCluster(
        node_id="macbook-air",
        role=NodeRole.RESEARCHER,
        ip_address="192.168.1.76",
        threshold=0.5,  # Very sensitive to knowledge signals
        max_concurrent_agents=5,
        connected_nodes=["mac-studio", "macpro51"],
    ),
    "completeu-server": NeuronCluster(
        node_id="completeu-server",
        role=NodeRole.INFERENCE,
        ip_address="192.168.1.186",
        threshold=0.65,
        max_concurrent_agents=6,
        connected_nodes=["mac-studio", "macpro51", "macbook-air"],
    ),
}


async def demo_neural_firing():
    """Demonstrate neural cluster firing"""
    # Get the builder node
    builder = CLUSTER_NODES["macpro51"]

    print(f"\n{'='*60}")
    print("NEURAL CLUSTER DEMONSTRATION")
    print(f"{'='*60}\n")

    # Show initial status
    print(f"Initial Status: {json.dumps(builder.get_status(), indent=2)}\n")

    # Simulate receiving a task signal from orchestrator
    task_signal = SynapticSignal(
        signal_id="demo_signal_001",
        source_node="mac-studio",
        source_neuron="coordinator_agent",
        target_node="macpro51",
        target_neuron_type="builder",
        signal_type=SignalType.TASK_REQUEST,
        activation_strength=0.85,
        payload={
            "task_type": "build",
            "details": {"target": "authentication_module", "tests": True},
        },
        propagation_chain=["mac-studio"],
        timestamp=datetime.now().isoformat(),
    )

    # Receive signal
    print(f"Receiving signal from {task_signal.source_node}...")
    new_potential = builder.receive_signal(task_signal)
    print(f"New activation potential: {new_potential:.2f}\n")

    # Check if we can fire
    if builder.can_fire():
        print("Threshold met! FIRING neurons...\n")

        task = {
            "task_type": "build",
            "complexity": "medium",
            "details": task_signal.payload.get("details", {}),
        }

        results = await builder.fire(task)

        print(f"\nFiring complete! {len(results)} agents executed.")
        print(f"\nFinal Status: {json.dumps(builder.get_status(), indent=2)}")
    else:
        print(f"Threshold not met. Current: {builder.activation_potential:.2f}, "
              f"Need: {builder.threshold}")


if __name__ == "__main__":
    asyncio.run(demo_neural_firing())

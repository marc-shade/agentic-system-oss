"""
Neural Network of Neural Networks

This package implements the distributed AGI cluster as a neural network
where each node acts as a specialized neuron cluster.

Key Components:
- NeuronCluster: Node abstraction with activation/firing
- SynapseProtocol: Cross-node communication
- WaveOrchestrator: Infinite wave-based execution
- NeuralDaemon: 24x7 autonomous operation

Based on infinite-agentic-loop patterns adapted for multi-node execution.
"""

from .neuron_cluster import (
    NeuronCluster,
    SynapticSignal,
    SignalType,
    NodeRole,
    SubAgent,
    CLUSTER_NODES,
)

from .synapse_protocol import (
    SynapseProtocol,
    WaveOrchestrator,
)

__all__ = [
    'NeuronCluster',
    'SynapticSignal',
    'SignalType',
    'NodeRole',
    'SubAgent',
    'CLUSTER_NODES',
    'SynapseProtocol',
    'WaveOrchestrator',
]

"""
Perception Module - Visual Intelligence for Cluster AGI

This module provides visual perception capabilities including:
- Webcam capture and face/motion detection
- Vision-language model integration (Ollama, Claude)
- Cluster-wide visual awareness aggregation
- Continuous environmental monitoring

Components:
- cluster_visual_daemon: Cross-platform webcam capture daemon
- cluster_visual_aggregator: Combines observations from all nodes
- visual_reasoning: Ollama vision model integration
- claude_visual_analyzer: Claude API vision fallback
- visual_intelligence: Unified multi-backend orchestration
- self_visual_analyzer: Store analyses from any source
- visual_awareness_daemon: Continuous monitoring service
"""

from pathlib import Path

__version__ = "1.0.0"
__all__ = [
    "ClusterVisualDaemon",
    "ClusterVisualAggregator",
    "VisualReasoner",
    "ClaudeVisualAnalyzer",
    "VisualIntelligence",
    "SelfVisualAnalyzer",
    "VisualAwarenessDaemon"
]

PERCEPTION_DIR = Path(__file__).parent

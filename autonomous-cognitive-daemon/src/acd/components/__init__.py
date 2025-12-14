"""ACD Components - The cognitive modules.

Each component handles a specific aspect of autonomous cognition:
- GoalMonitor: Tracks active goals and detects stalled progress
- GapResearcher: Auto-researches high-severity knowledge gaps
- MemoryCurator: Consolidates and optimizes the memory system
- ClusterCoordinator: Monitors and coordinates the agentic cluster
- SessionPreparer: Prepares context and briefings for sessions
- ProactiveNotifier: Sends proactive notifications to Marc
- LinuxOSController: Deep Linux/GNOME OS integration
- AudioFilter: Intelligent audio filtering (noise, TTS feedback, hallucinations)
- EnvironmentalListener: Continuous audio awareness ("the mics are my ears")
"""

from .goal_monitor import GoalMonitor
from .gap_researcher import GapResearcher
from .memory_curator import MemoryCurator
from .cluster_coordinator import ClusterCoordinator
from .session_preparer import SessionPreparer
from .proactive_notifier import ProactiveNotifier
from .linux_os_controller import LinuxOSController
from .audio_filter import AudioFilter, AudioEvent, AudioSourceType
from .environmental_listener import EnvironmentalListener, EnvironmentalState, VoiceModeIntegration
from .voice_input_router import VoiceInputRouter, VoiceInput, get_pending_voice_inputs, get_latest_broadcast

__all__ = [
    "GoalMonitor",
    "GapResearcher",
    "MemoryCurator",
    "ClusterCoordinator",
    "SessionPreparer",
    "ProactiveNotifier",
    "LinuxOSController",
    "AudioFilter",
    "AudioEvent",
    "AudioSourceType",
    "EnvironmentalListener",
    "EnvironmentalState",
    "VoiceModeIntegration",
    "VoiceInputRouter",
    "VoiceInput",
    "get_pending_voice_inputs",
    "get_latest_broadcast",
]

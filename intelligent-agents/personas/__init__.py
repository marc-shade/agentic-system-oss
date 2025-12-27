"""
Agent Personas Module

Following Kai pattern: Each agent has a distinct persona that defines:
1. Purpose - What the agent is designed to do
2. Capabilities - Tools and skills available
3. Boundaries - What the agent should NOT do
4. Communication Style - How the agent interacts
5. Decision Framework - How the agent makes choices

Personas enable:
- Deterministic behavior within scope
- Clear capability boundaries
- Appropriate tool selection
- Consistent communication
- Predictable decision-making
"""

from .persona_base import (
    AgentPersona,
    PersonaCapability,
    PersonaTrait,
    PersonaType,
    CommunicationStyle,
)
from .persona_registry import PersonaRegistry
from .code_agent import CodeAgentPersona
from .research_agent import ResearchAgentPersona
from .ops_agent import OpsAgentPersona
from .security_agent import SecurityAgentPersona

# Psychometric-grounded personas (BFI-2 framework)
from .psychometric_generator import (
    Domain,
    PsychometricProfile,
    PsychometricGenerator,
    CLUSTER_NODE_PROFILES,
)
from .psychometric_persona import (
    PsychometricPersona,
    PsychometricPersonaConfig,
    create_cluster_personas,
)
# Cluster node personas (real nodes from cluster-nodes.json)
from .orchestrator_agent import MacStudioOrchestrator, get_orchestrator
from .researcher_agent import MacBookAirM3Researcher, get_researcher
from .builder_agent import MacPro51Builder, get_builder
from .ai_inference_agent import CompleteuServerInference, get_ai_inference
from .small_inference_agent import MacMiniSmallInference, get_small_inference
from .sentinel_agent import BPISentinel, get_sentinel

__all__ = [
    # Base classes
    'AgentPersona',
    'PersonaCapability',
    'PersonaTrait',
    'PersonaType',
    'CommunicationStyle',
    'PersonaRegistry',
    # Traditional personas
    'CodeAgentPersona',
    'ResearchAgentPersona',
    'OpsAgentPersona',
    'SecurityAgentPersona',
    # Psychometric framework
    'Domain',
    'PsychometricProfile',
    'PsychometricGenerator',
    'PsychometricPersona',
    'PsychometricPersonaConfig',
    'CLUSTER_NODE_PROFILES',
    'create_cluster_personas',
    # Cluster node personas (6 real nodes)
    'MacStudioOrchestrator',
    'get_orchestrator',
    'MacBookAirM3Researcher',
    'get_researcher',
    'MacPro51Builder',
    'get_builder',
    'CompleteuServerInference',
    'get_ai_inference',
    'MacMiniSmallInference',
    'get_small_inference',
    'BPISentinel',
    'get_sentinel',
]

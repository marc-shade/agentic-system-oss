#!/usr/bin/env python3
"""
Unit tests for Multi-Agent Debate framework
"""

import asyncio
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from advanced_prompting import (
    MultiAgentDebate,
    AgentPerspective,
    DebateProtocol,
    PriorityType,
    DebateResult
)


class TestAgentPerspective:
    """Test suite for AgentPerspective"""

    def test_create_perspective(self):
        """Test agent perspective creation"""
        perspective = AgentPerspective(
            name="Security Guardian",
            priority=PriorityType.SECURITY,
            bias="Minimize attack surface",
            weight=1.0
        )

        assert perspective.name == "Security Guardian"
        assert perspective.priority == PriorityType.SECURITY
        assert perspective.weight == 1.0

    def test_system_prompt_generation(self):
        """Test system prompt generation for each priority type"""
        for priority in PriorityType:
            perspective = AgentPerspective(
                name=f"{priority.value} Agent",
                priority=priority,
                bias=f"Test {priority.value}"
            )

            prompt = perspective.get_system_prompt()
            assert len(prompt) > 0
            assert perspective.name in prompt
            assert priority.value.upper() in prompt.upper()


class TestDebateProtocol:
    """Test suite for DebateProtocol"""

    @pytest.fixture
    def protocol(self):
        """Create a DebateProtocol instance"""
        return DebateProtocol(
            max_rounds=3,
            consensus_threshold=0.7,
            cli_tool="gemini"
        )

    @pytest.fixture
    def perspectives(self):
        """Create test perspectives"""
        return [
            AgentPerspective(
                name="Stability Agent",
                priority=PriorityType.STABILITY,
                bias="Avoid risky changes"
            ),
            AgentPerspective(
                name="Performance Agent",
                priority=PriorityType.PERFORMANCE,
                bias="Optimize for speed"
            ),
            AgentPerspective(
                name="Security Agent",
                priority=PriorityType.SECURITY,
                bias="Minimize vulnerabilities"
            )
        ]

    def test_initialization(self, protocol):
        """Test protocol initialization"""
        assert protocol.max_rounds == 3
        assert protocol.consensus_threshold == 0.7
        assert protocol.cli_tool == "gemini"
        assert len(protocol.debate_history) == 0

    @pytest.mark.asyncio
    async def test_conduct_debate(self, protocol, perspectives):
        """Test conducting a debate"""
        proposal = {
            "name": "Implement caching layer",
            "description": "Add Redis caching to improve performance",
            "risk_level": 0.4,
            "domains": ["performance", "stability"]
        }

        result = await protocol.conduct_debate(
            proposal, perspectives, "caching_proposal"
        )

        assert isinstance(result, DebateResult)
        assert result.proposal == proposal
        assert result.debate_topic == "caching_proposal"
        assert len(result.rounds) > 0
        assert isinstance(result.consensus_reached, bool)
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_debate_rounds(self, protocol, perspectives):
        """Test debate round structure"""
        proposal = {
            "name": "Test proposal",
            "description": "Test"
        }

        result = await protocol.conduct_debate(
            proposal, perspectives, "test_debate"
        )

        # Check round structure
        for round_data in result.rounds:
            assert round_data.round_number > 0
            assert isinstance(round_data.arguments, dict)
            assert isinstance(round_data.consensus_level, float)

    def test_extract_position(self, protocol):
        """Test position extraction"""
        assert protocol._extract_position("I SUPPORT this proposal") == "SUPPORT"
        assert protocol._extract_position("I OPPOSE this change") == "OPPOSE"
        assert protocol._extract_position("I am NEUTRAL") == "NEUTRAL"

    def test_extract_confidence(self, protocol):
        """Test confidence extraction"""
        assert protocol._extract_confidence("CONFIDENCE: 0.85") == 0.85
        assert protocol._extract_confidence("CONSENSUS_LEVEL: 0.7") == 0.7


class TestMultiAgentDebate:
    """Test suite for MultiAgentDebate"""

    @pytest.mark.asyncio
    async def test_quick_debate(self):
        """Test quick debate with pre-configured scenario"""
        proposal = {
            "name": "Aggressive caching",
            "benefits": ["performance", "improvement"],
            "risk_level": 0.6,
            "domains": ["performance", "system_health"],
            "characteristics": ["optimization", "breaking_change"],
            "description": "Cache all API responses for 1 hour"
        }

        result = await MultiAgentDebate.quick_debate(
            proposal=proposal,
            debate_topic="aggressive_caching",
            scenario="system_optimization"
        )

        assert isinstance(result, DebateResult)
        assert len(result.rounds) > 0
        assert len(result.agent_agreements) == 3  # 3 agents in system_optimization

    @pytest.mark.asyncio
    async def test_feature_deployment_scenario(self):
        """Test feature deployment scenario"""
        proposal = {
            "name": "New user dashboard",
            "description": "Add comprehensive user analytics dashboard"
        }

        result = await MultiAgentDebate.quick_debate(
            proposal=proposal,
            debate_topic="dashboard_feature",
            scenario="feature_deployment"
        )

        assert isinstance(result, DebateResult)
        # feature_deployment has 4 agents
        assert len(result.agent_agreements) == 4

    def test_get_scenario_perspectives(self):
        """Test scenario perspective retrieval"""
        system_opt = MultiAgentDebate._get_scenario_perspectives("system_optimization")
        assert len(system_opt) == 3

        feature_deploy = MultiAgentDebate._get_scenario_perspectives("feature_deployment")
        assert len(feature_deploy) == 4

        # Unknown scenario should default to system_optimization
        default = MultiAgentDebate._get_scenario_perspectives("unknown")
        assert len(default) == 3


def test_priority_types():
    """Test all priority type values"""
    expected_types = [
        "stability", "improvement", "security", "performance",
        "usability", "cost", "reliability", "innovation"
    ]

    actual_types = [p.value for p in PriorityType]

    for expected in expected_types:
        assert expected in actual_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

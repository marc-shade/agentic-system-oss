#!/usr/bin/env python3
"""
SDK Agent Bridge
================

Integration layer connecting existing SDK agents (Claude, Codex, Gemini)
to the Multi-Agent Coordinator.

This bridge allows the coordinator to use production-ready SDK agents
for task execution without modification.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add sdk_agents to path
sys.path.insert(0, str(Path(__file__).parent / "sdk_agents"))

from claude_agent import ClaudeAgent, AgentPurpose

logger = logging.getLogger(__name__)


class SDKAgentBridge:
    """
    Bridge between Multi-Agent Coordinator and SDK agents.

    Translates coordinator tasks into SDK agent purposes and tools,
    executes them, and returns results in coordinator format.
    """

    def __init__(self):
        """Initialize SDK agent bridge."""
        self.agents: Dict[str, ClaudeAgent] = {}
        self._initialize_agents()

    def _initialize_agents(self):
        """Initialize SDK agents with their purposes."""
        # Code Generation Agent
        self.agents["code_generation"] = self._create_claude_agent(
            AgentPurpose(
                name="CodeGenerator",
                description="Generates code from specifications",
                primary_goal="Create production-ready code based on requirements",
                decision_criteria=[
                    "Code must be syntactically correct",
                    "Must include proper error handling",
                    "Must follow language best practices"
                ],
                tools_needed=["code_generation", "syntax_validation"]
            )
        )

        # Analysis Agent
        self.agents["analysis"] = self._create_claude_agent(
            AgentPurpose(
                name="Analyst",
                description="Analyzes code, data, and patterns",
                primary_goal="Provide comprehensive analysis with insights",
                decision_criteria=[
                    "Analysis must be thorough",
                    "Must identify key patterns",
                    "Must provide actionable recommendations"
                ],
                tools_needed=["code_analysis", "pattern_detection"]
            )
        )

        # Research Agent
        self.agents["research"] = self._create_claude_agent(
            AgentPurpose(
                name="Researcher",
                description="Researches topics and gathers information",
                primary_goal="Gather comprehensive, accurate information",
                decision_criteria=[
                    "Information must be from reliable sources",
                    "Must be comprehensive",
                    "Must be current and accurate"
                ],
                tools_needed=["web_search", "documentation_lookup"]
            )
        )

        # Testing Agent
        self.agents["testing"] = self._create_claude_agent(
            AgentPurpose(
                name="Tester",
                description="Creates and runs tests",
                primary_goal="Ensure code quality through comprehensive testing",
                decision_criteria=[
                    "Tests must cover edge cases",
                    "Must validate functionality",
                    "Must check for regressions"
                ],
                tools_needed=["test_creation", "test_execution"]
            )
        )

        # Documentation Agent
        self.agents["documentation"] = self._create_claude_agent(
            AgentPurpose(
                name="Documenter",
                description="Generates documentation",
                primary_goal="Create clear, comprehensive documentation",
                decision_criteria=[
                    "Documentation must be clear",
                    "Must include examples",
                    "Must be complete"
                ],
                tools_needed=["doc_generation", "example_creation"]
            )
        )

        # Optimization Agent
        self.agents["optimization"] = self._create_claude_agent(
            AgentPurpose(
                name="Optimizer",
                description="Optimizes code and algorithms",
                primary_goal="Improve performance and efficiency",
                decision_criteria=[
                    "Must maintain correctness",
                    "Must measurably improve performance",
                    "Must not increase complexity unnecessarily"
                ],
                tools_needed=["performance_analysis", "optimization"]
            )
        )

        logger.info(f"Initialized {len(self.agents)} SDK agents")

    def _create_claude_agent(self, purpose: AgentPurpose) -> ClaudeAgent:
        """
        Create a Claude agent with the given purpose.

        Args:
            purpose: Agent purpose definition

        Returns:
            Initialized ClaudeAgent
        """
        # Empty tools list - agents use Claude's general intelligence
        # In production, would add specific MCP tools per agent
        return ClaudeAgent(
            purpose=purpose,
            tools=[],
            model="claude-sonnet-4-20250514"
        )

    async def execute_task(
        self,
        agent_type: str,
        task_description: str,
        context: Dict
    ) -> Dict[str, Any]:
        """
        Execute a task using the appropriate SDK agent.

        Args:
            agent_type: Type of agent to use
            task_description: Task description
            context: Execution context

        Returns:
            Execution result with success status, result, and metadata
        """
        if agent_type not in self.agents:
            return {
                "success": False,
                "error": f"Unknown agent type: {agent_type}",
                "result": None
            }

        agent = self.agents[agent_type]

        try:
            logger.info(f"Executing task with {agent_type} agent: {task_description}")

            # Prepare observations for the agent
            observations = [
                f"Task: {task_description}",
                f"Context: {json.dumps(context, indent=2)}"
            ]

            # Execute using Claude agent's reasoning
            decision = await agent.reason_and_decide(observations)

            # Extract result from decision
            result = {
                "success": True,
                "result": decision.decision,
                "reasoning": decision.reasoning,
                "confidence": decision.confidence,
                "action_taken": decision.action_taken,
                "metadata": {
                    "agent": agent_type,
                    "timestamp": decision.timestamp
                }
            }

            logger.info(f"Task completed by {agent_type} agent (confidence: {decision.confidence:.2f})")

            return result

        except Exception as e:
            logger.error(f"Error executing task with {agent_type} agent: {e}", exc_info=True)

            return {
                "success": False,
                "error": str(e),
                "result": None,
                "metadata": {
                    "agent": agent_type,
                    "timestamp": datetime.now().isoformat()
                }
            }

    def get_available_agents(self) -> List[str]:
        """Get list of available agent types."""
        return list(self.agents.keys())

    def get_agent_capabilities(self, agent_type: str) -> Optional[Dict]:
        """
        Get capabilities of a specific agent.

        Args:
            agent_type: Agent type

        Returns:
            Agent purpose and capabilities or None
        """
        if agent_type not in self.agents:
            return None

        agent = self.agents[agent_type]
        return {
            "name": agent.purpose.name,
            "description": agent.purpose.description,
            "primary_goal": agent.purpose.primary_goal,
            "decision_criteria": agent.purpose.decision_criteria,
            "tools_needed": agent.purpose.tools_needed
        }


# Singleton instance
_bridge: Optional[SDKAgentBridge] = None


def get_sdk_agent_bridge() -> SDKAgentBridge:
    """
    Get singleton SDK agent bridge.

    Returns:
        SDK agent bridge instance
    """
    global _bridge
    if _bridge is None:
        _bridge = SDKAgentBridge()
    return _bridge


async def main():
    """Example usage of SDK Agent Bridge."""
    bridge = get_sdk_agent_bridge()

    # List available agents
    print(f"Available agents: {bridge.get_available_agents()}")

    # Get capabilities
    capabilities = bridge.get_agent_capabilities("code_generation")
    print(f"\nCode Generation Agent capabilities:")
    print(f"  Name: {capabilities['name']}")
    print(f"  Goal: {capabilities['primary_goal']}")

    # Execute a task
    result = await bridge.execute_task(
        agent_type="code_generation",
        task_description="Create a function to calculate Fibonacci numbers",
        context={"language": "python", "optimized": True}
    )

    print(f"\nExecution result:")
    print(f"  Success: {result['success']}")
    print(f"  Confidence: {result.get('confidence', 0):.2f}")


if __name__ == "__main__":
    import json
    from datetime import datetime
    asyncio.run(main())

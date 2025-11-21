#!/usr/bin/env python3
"""
Multi-Agent Debate Protocol
============================

Competing perspectives force synthesis and robust consensus through
structured argumentation. Multiple agents with conflicting priorities
debate proposals to reach well-reasoned decisions.

Key Components:
- AgentPerspective: Agent with explicit priority/bias
- DebateProtocol: Manages rounds, rebuttals, synthesis
- MultiAgentDebate: High-level orchestrator

Pre-configured Scenarios:
- system_optimization: Health (stability) vs Optimization (improvement) vs Security
- feature_deployment: Product vs Performance vs Cost vs Reliability

Usage:
    result = await MultiAgentDebate.quick_debate(
        proposal={"name": "aggressive caching", "risk_level": 0.6},
        debate_topic="caching_optimization",
        scenario="system_optimization"
    )
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys

# Add SDK agents to path
sys.path.insert(0, str(Path(__file__).parent.parent / "sdk_agents"))
from cli_agent import CLIAgent

logger = logging.getLogger(__name__)


class PriorityType(Enum):
    """Agent priority types"""
    STABILITY = "stability"
    IMPROVEMENT = "improvement"
    SECURITY = "security"
    PERFORMANCE = "performance"
    USABILITY = "usability"
    COST = "cost"
    RELIABILITY = "reliability"
    INNOVATION = "innovation"


@dataclass
class AgentPerspective:
    """Agent with specific perspective and priorities"""
    name: str
    priority: PriorityType
    bias: str
    weight: float = 1.0

    def get_system_prompt(self) -> str:
        """Get agent's system prompt encoding their perspective"""
        prompts = {
            PriorityType.STABILITY: f"""You are {self.name}, prioritizing STABILITY.
Your bias: {self.bias}
You value: system stability, proven solutions, minimal disruption
You oppose: risky changes, unproven approaches, breaking changes""",

            PriorityType.IMPROVEMENT: f"""You are {self.name}, prioritizing IMPROVEMENT.
Your bias: {self.bias}
You value: optimization, efficiency gains, performance improvements
You oppose: status quo, missed optimization opportunities, inefficiency""",

            PriorityType.SECURITY: f"""You are {self.name}, prioritizing SECURITY.
Your bias: {self.bias}
You value: security, privacy, threat mitigation
You oppose: vulnerabilities, attack surfaces, security compromises""",

            PriorityType.PERFORMANCE: f"""You are {self.name}, prioritizing PERFORMANCE.
Your bias: {self.bias}
You value: speed, throughput, low latency, resource efficiency
You oppose: bottlenecks, performance degradation, resource waste""",

            PriorityType.USABILITY: f"""You are {self.name}, prioritizing USABILITY.
Your bias: {self.bias}
You value: user experience, ease of use, accessibility
You oppose: complexity, poor UX, user friction""",

            PriorityType.COST: f"""You are {self.name}, prioritizing COST.
Your bias: {self.bias}
You value: cost efficiency, resource optimization, ROI
You oppose: waste, unnecessary expenses, poor ROI""",

            PriorityType.RELIABILITY: f"""You are {self.name}, prioritizing RELIABILITY.
Your bias: {self.bias}
You value: uptime, fault tolerance, predictable behavior
You oppose: flakiness, race conditions, unreliable systems""",

            PriorityType.INNOVATION: f"""You are {self.name}, prioritizing INNOVATION.
Your bias: {self.bias}
You value: novel approaches, cutting-edge solutions, breakthroughs
You oppose: stagnation, outdated practices, missed opportunities"""
        }

        return prompts.get(self.priority, f"You are {self.name}")


@dataclass
class DebateRound:
    """Single round of debate"""
    round_number: int
    arguments: Dict[str, str] = field(default_factory=dict)  # agent_name -> argument
    rebuttals: Dict[str, List[str]] = field(default_factory=dict)  # agent_name -> rebuttals
    synthesis: Optional[str] = None
    consensus_level: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DebateResult:
    """Complete debate result"""
    proposal: Dict[str, Any]
    debate_topic: str
    rounds: List[DebateRound]
    final_decision: str
    consensus_reached: bool
    confidence: float
    synthesis_rationale: str
    agent_agreements: Dict[str, float]  # agent_name -> agreement level
    key_concerns: List[str]
    key_supports: List[str]
    timestamp: datetime = field(default_factory=datetime.now)


class DebateProtocol:
    """
    Debate Protocol - Manages structured multi-agent debates

    Process:
    1. Initial evaluations from all agents
    2. Argument phase - each agent presents position
    3. Rebuttal phase - agents respond to each other
    4. Synthesis phase - find common ground
    5. Repeat until consensus or max rounds
    """

    def __init__(
        self,
        max_rounds: int = 3,
        consensus_threshold: float = 0.7,
        cli_tool: str = "gemini"
    ):
        """
        Initialize DebateProtocol

        Args:
            max_rounds: Maximum debate rounds
            consensus_threshold: Required consensus level (0.0-1.0)
            cli_tool: CLI tool to use for agent simulation
        """
        self.max_rounds = max_rounds
        self.consensus_threshold = consensus_threshold
        self.cli_tool = cli_tool
        self.debate_history: List[DebateResult] = []
        logger.info(f"DebateProtocol initialized (max_rounds={max_rounds})")

    async def conduct_debate(
        self,
        proposal: Dict[str, Any],
        perspectives: List[AgentPerspective],
        debate_topic: str,
        agent: Optional[CLIAgent] = None
    ) -> DebateResult:
        """
        Orchestrate full debate process

        Args:
            proposal: Proposal to debate (must include name, description)
            perspectives: List of agent perspectives
            debate_topic: Human-readable topic
            agent: Optional agent instance

        Returns:
            DebateResult with consensus and reasoning
        """
        logger.info(f"Starting debate: {debate_topic} with {len(perspectives)} agents")

        rounds: List[DebateRound] = []

        # Initial evaluations
        initial_evaluations = await self._gather_initial_positions(
            proposal, perspectives, agent
        )

        # Conduct rounds
        for round_num in range(1, self.max_rounds + 1):
            logger.info(f"Round {round_num}/{self.max_rounds}")

            debate_round = DebateRound(round_number=round_num)

            # Arguments phase
            arguments = await self._arguments_phase(
                proposal, perspectives, initial_evaluations, round_num, agent
            )
            debate_round.arguments = arguments

            # Rebuttals phase
            rebuttals = await self._rebuttals_phase(
                arguments, perspectives, round_num, agent
            )
            debate_round.rebuttals = rebuttals

            # Synthesis phase
            synthesis = await self._synthesis_phase(
                debate_round, perspectives, agent
            )
            debate_round.synthesis = synthesis.get("synthesis")
            debate_round.consensus_level = synthesis.get("consensus_level", 0.0)

            rounds.append(debate_round)

            # Check for consensus
            if debate_round.consensus_level >= self.consensus_threshold:
                logger.info(f"Consensus reached in round {round_num}")
                break

        # Final decision synthesis
        final_result = await self._final_synthesis(
            proposal, rounds, perspectives, agent
        )

        result = DebateResult(
            proposal=proposal,
            debate_topic=debate_topic,
            rounds=rounds,
            final_decision=final_result["decision"],
            consensus_reached=final_result["consensus_reached"],
            confidence=final_result["confidence"],
            synthesis_rationale=final_result["rationale"],
            agent_agreements=final_result["agent_agreements"],
            key_concerns=final_result["concerns"],
            key_supports=final_result["supports"]
        )

        self.debate_history.append(result)
        logger.info(f"Debate complete: consensus={result.consensus_reached}")

        return result

    async def _gather_initial_positions(
        self,
        proposal: Dict[str, Any],
        perspectives: List[AgentPerspective],
        agent: Optional[CLIAgent]
    ) -> Dict[str, Dict[str, Any]]:
        """Gather initial positions from all agents"""
        evaluations = {}

        for perspective in perspectives:
            prompt = f"""{perspective.get_system_prompt()}

PROPOSAL TO EVALUATE:
{json.dumps(proposal, indent=2)}

Provide your initial evaluation:
1. Do you support or oppose this proposal?
2. What are your main concerns?
3. What are the benefits from your perspective?
4. Initial position (SUPPORT/OPPOSE/NEUTRAL)
5. Confidence level (0.0-1.0)

Format:
POSITION: <SUPPORT/OPPOSE/NEUTRAL>
CONFIDENCE: <0.0-1.0>
CONCERNS: <list concerns>
BENEFITS: <list benefits>
"""

            response = await self._run_cli(prompt, agent)

            evaluations[perspective.name] = {
                "position": self._extract_position(response),
                "confidence": self._extract_confidence(response),
                "concerns": self._extract_list(response, "CONCERNS:"),
                "benefits": self._extract_list(response, "BENEFITS:")
            }

        return evaluations

    async def _arguments_phase(
        self,
        proposal: Dict[str, Any],
        perspectives: List[AgentPerspective],
        evaluations: Dict[str, Dict[str, Any]],
        round_num: int,
        agent: Optional[CLIAgent]
    ) -> Dict[str, str]:
        """Each agent presents their argument"""
        arguments = {}

        for perspective in perspectives:
            eval_data = evaluations.get(perspective.name, {})

            prompt = f"""{perspective.get_system_prompt()}

PROPOSAL:
{json.dumps(proposal, indent=2)}

YOUR INITIAL POSITION: {eval_data.get('position', 'NEUTRAL')}

ROUND {round_num} - Present your argument:
1. State your position clearly
2. Provide evidence supporting your position
3. Address potential counter-arguments
4. Explain impact from your priority perspective ({perspective.priority.value})

Make a strong, evidence-based argument.
"""

            response = await self._run_cli(prompt, agent)
            arguments[perspective.name] = response

        return arguments

    async def _rebuttals_phase(
        self,
        arguments: Dict[str, str],
        perspectives: List[AgentPerspective],
        round_num: int,
        agent: Optional[CLIAgent]
    ) -> Dict[str, List[str]]:
        """Each agent rebuts other arguments"""
        rebuttals = {}

        for perspective in perspectives:
            my_argument = arguments.get(perspective.name, "")

            # Get other agents' arguments
            other_arguments = {
                name: arg for name, arg in arguments.items()
                if name != perspective.name
            }

            prompt = f"""{perspective.get_system_prompt()}

YOUR ARGUMENT:
{my_argument}

OTHER AGENTS' ARGUMENTS:
{json.dumps(other_arguments, indent=2)}

ROUND {round_num} - Rebut the other arguments:
1. Identify flaws in opposing arguments
2. Defend your position against counter-points
3. Find common ground where possible
4. Strengthen your case

Provide focused rebuttals.
"""

            response = await self._run_cli(prompt, agent)
            rebuttals[perspective.name] = [response]

        return rebuttals

    async def _synthesis_phase(
        self,
        debate_round: DebateRound,
        perspectives: List[AgentPerspective],
        agent: Optional[CLIAgent]
    ) -> Dict[str, Any]:
        """Synthesize arguments to find consensus"""
        prompt = f"""You are a neutral debate moderator synthesizing multiple perspectives.

ROUND {debate_round.round_number} ARGUMENTS:
{json.dumps(debate_round.arguments, indent=2)}

REBUTTALS:
{json.dumps(debate_round.rebuttals, indent=2)}

Synthesize:
1. Points of agreement
2. Points of disagreement
3. Emerging consensus
4. Remaining concerns
5. Consensus level (0.0-1.0)

SYNTHESIS:
<synthesis here>

CONSENSUS_LEVEL: <0.0-1.0>
"""

        response = await self._run_cli(prompt, agent)

        synthesis_text = self._extract_section(response, "SYNTHESIS:")
        consensus_level = self._extract_confidence(response)

        return {
            "synthesis": synthesis_text or response,
            "consensus_level": consensus_level
        }

    async def _final_synthesis(
        self,
        proposal: Dict[str, Any],
        rounds: List[DebateRound],
        perspectives: List[AgentPerspective],
        agent: Optional[CLIAgent]
    ) -> Dict[str, Any]:
        """Final decision synthesis across all rounds"""
        prompt = f"""You are synthesizing a multi-round debate to reach a final decision.

PROPOSAL:
{json.dumps(proposal, indent=2)}

DEBATE ROUNDS ({len(rounds)} rounds):
{json.dumps([{"round": r.round_number, "consensus": r.consensus_level} for r in rounds], indent=2)}

PERSPECTIVES INVOLVED:
{json.dumps([{"name": p.name, "priority": p.priority.value} for p in perspectives], indent=2)}

Provide final synthesis:

DECISION: <APPROVE/REJECT/MODIFY - be specific>
CONFIDENCE: <0.0-1.0>
CONSENSUS_REACHED: <true/false>
RATIONALE: <comprehensive explanation>

AGENT_AGREEMENTS:
{chr(10).join(f'- {p.name}: <0.0-1.0>' for p in perspectives)}

KEY_CONCERNS: <list major concerns>
KEY_SUPPORTS: <list major support points>
"""

        response = await self._run_cli(prompt, agent)

        return {
            "decision": self._extract_section(response, "DECISION:") or "UNCLEAR",
            "confidence": self._extract_confidence(response),
            "consensus_reached": "true" in response.lower(),
            "rationale": self._extract_section(response, "RATIONALE:") or response,
            "agent_agreements": self._extract_agent_agreements(response, perspectives),
            "concerns": self._extract_list(response, "KEY_CONCERNS:"),
            "supports": self._extract_list(response, "KEY_SUPPORTS:")
        }

    async def _run_cli(self, prompt: str, agent: Optional[CLIAgent]) -> str:
        """Run CLI tool to process prompt"""
        if agent:
            try:
                result = agent.run_headless_cli(prompt, format="text")
                if result.get("status") == "success":
                    return result.get("output", "")
            except Exception as e:
                logger.error(f"Agent CLI execution failed: {e}")

        # Fallback to direct CLI execution
        import subprocess
        try:
            result = subprocess.run(
                [self.cli_tool, prompt],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout.strip()
        except Exception as e:
            logger.error(f"CLI execution failed: {e}")
            return f"ERROR: {e}"

    def _extract_position(self, response: str) -> str:
        """Extract position from response"""
        for keyword in ["SUPPORT", "OPPOSE", "NEUTRAL"]:
            if keyword in response.upper():
                return keyword
        return "NEUTRAL"

    def _extract_confidence(self, response: str) -> float:
        """Extract confidence score"""
        import re
        patterns = [
            r'CONFIDENCE[:\s]+([0-9.]+)',
            r'CONSENSUS_LEVEL[:\s]+([0-9.]+)',
            r'([0-9.]+)/1\.0'
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                if value > 1.0:
                    value = value / 100.0
                return value

        return 0.5

    def _extract_section(self, response: str, marker: str) -> Optional[str]:
        """Extract section from response"""
        if marker not in response:
            return None

        parts = response.split(marker, 1)
        if len(parts) < 2:
            return None

        text = parts[1].strip()

        # Find next section marker
        next_markers = ["CONFIDENCE:", "CONSENSUS_LEVEL:", "DECISION:", "RATIONALE:",
                       "AGENT_AGREEMENTS:", "KEY_CONCERNS:", "KEY_SUPPORTS:"]
        for next_marker in next_markers:
            if next_marker != marker and next_marker in text:
                text = text.split(next_marker)[0].strip()
                break

        return text

    def _extract_list(self, response: str, marker: str) -> List[str]:
        """Extract list from response"""
        section = self._extract_section(response, marker)
        if not section:
            return []

        # Parse bullet points or newlines
        items = []
        for line in section.split('\n'):
            line = line.strip()
            if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                items.append(line[1:].strip())
            elif line:
                items.append(line)

        return items

    def _extract_agent_agreements(
        self,
        response: str,
        perspectives: List[AgentPerspective]
    ) -> Dict[str, float]:
        """Extract agent agreement levels"""
        agreements = {}

        for perspective in perspectives:
            # Look for pattern like "AgentName: 0.8"
            import re
            pattern = rf'{perspective.name}[:\s]+([0-9.]+)'
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                agreements[perspective.name] = float(match.group(1))
            else:
                agreements[perspective.name] = 0.5  # Default

        return agreements


class MultiAgentDebate:
    """
    High-level orchestrator for multi-agent debates

    Provides pre-configured debate scenarios and simplified API
    """

    @staticmethod
    async def quick_debate(
        proposal: Dict[str, Any],
        debate_topic: str,
        scenario: str = "system_optimization",
        memory_client: Optional[Any] = None,
        agent: Optional[CLIAgent] = None
    ) -> DebateResult:
        """
        Run a quick debate using pre-configured scenario

        Args:
            proposal: Proposal to debate
            debate_topic: Topic description
            scenario: Pre-configured scenario name
            memory_client: Optional enhanced-memory client
            agent: Optional agent instance

        Returns:
            DebateResult
        """
        perspectives = MultiAgentDebate._get_scenario_perspectives(scenario)

        protocol = DebateProtocol(max_rounds=3, consensus_threshold=0.7)
        result = await protocol.conduct_debate(
            proposal, perspectives, debate_topic, agent
        )

        # Store in memory if available
        if memory_client:
            await MultiAgentDebate._store_in_memory(result, memory_client)

        return result

    @staticmethod
    def _get_scenario_perspectives(scenario: str) -> List[AgentPerspective]:
        """Get pre-configured perspectives for scenario"""
        scenarios = {
            "system_optimization": [
                AgentPerspective(
                    name="Health Guardian",
                    priority=PriorityType.STABILITY,
                    bias="Prevent system instability at all costs"
                ),
                AgentPerspective(
                    name="Optimization Agent",
                    priority=PriorityType.IMPROVEMENT,
                    bias="Maximize performance and efficiency"
                ),
                AgentPerspective(
                    name="Security Guardian",
                    priority=PriorityType.SECURITY,
                    bias="Minimize attack surface and vulnerabilities"
                )
            ],
            "feature_deployment": [
                AgentPerspective(
                    name="Product Manager",
                    priority=PriorityType.USABILITY,
                    bias="Prioritize user experience and adoption"
                ),
                AgentPerspective(
                    name="Performance Engineer",
                    priority=PriorityType.PERFORMANCE,
                    bias="Ensure fast, efficient execution"
                ),
                AgentPerspective(
                    name="Cost Optimizer",
                    priority=PriorityType.COST,
                    bias="Minimize operational costs and waste"
                ),
                AgentPerspective(
                    name="Reliability Engineer",
                    priority=PriorityType.RELIABILITY,
                    bias="Maximize uptime and fault tolerance"
                )
            ]
        }

        return scenarios.get(scenario, scenarios["system_optimization"])

    @staticmethod
    async def _store_in_memory(result: DebateResult, memory_client: Any):
        """Store debate outcome in enhanced-memory"""
        try:
            # This would integrate with enhanced-memory MCP
            logger.info(f"Would store debate result in memory: {result.debate_topic}")
        except Exception as e:
            logger.error(f"Failed to store debate in memory: {e}")

#!/usr/bin/env python3
"""
Brainstorm Orchestrator - Collective Reasoning System

Enables both user-interactive and autonomous internal brainstorming sessions
using specialized thinking persona agents (Ideator, Critic, Strategist, Builder, Synthesizer).

Usage:
    # Interactive session (via slash commands)
    /brainstorm "How to improve memory consolidation?"

    # Internal autonomous session (via Python API)
    from brainstorm_orchestrator import BrainstormOrchestrator
    orchestrator = BrainstormOrchestrator()
    results = await orchestrator.start_internal_session(
        topic="Complex problem to solve",
        auto_conclude=True
    )
"""
import platform
from pathlib import Path

import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import os
import sys

# Add parent paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from mcp_client import MCPClient  # If available

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

except ImportError:
    MCPClient = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BrainstormPhase(Enum):
    """Brainstorming session phases"""
    INITIALIZING = "initializing"
    DIVERGENT = "divergent"
    CONVERGENT = "convergent"
    CRITICAL = "critical"
    SYNTHESIS = "synthesis"
    PAUSED = "paused"
    CONCLUDED = "concluded"


class Topology(Enum):
    """Swarm topology configurations"""
    MESH = "mesh"           # All-to-all (divergent)
    HIERARCHICAL = "hierarchical"  # Tree (convergent)
    RING = "ring"           # Sequential (critical)
    STAR = "star"           # Hub-spoke (synthesis)


@dataclass
class Idea:
    """Represents a single idea in the brainstorm"""
    id: str
    content: str
    author: str
    phase: str
    round: int
    timestamp: datetime
    builds_on: List[str] = field(default_factory=list)
    votes: Dict[str, int] = field(default_factory=dict)
    status: str = "active"
    weight: float = 1.0
    wild_factor: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def score(self) -> float:
        """Calculate idea score based on votes and weight"""
        vote_sum = sum(self.votes.values())
        return vote_sum * self.weight

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "author": self.author,
            "phase": self.phase,
            "round": self.round,
            "timestamp": self.timestamp.isoformat(),
            "builds_on": self.builds_on,
            "votes": self.votes,
            "status": self.status,
            "weight": self.weight,
            "wild_factor": self.wild_factor,
            "score": self.score,
            "metadata": self.metadata
        }


@dataclass
class BrainstormSession:
    """Represents an active brainstorming session"""
    id: str
    topic: str
    phase: BrainstormPhase
    topology: Topology
    created_at: datetime
    ideas: List[Idea] = field(default_factory=list)
    current_round: int = 1
    max_rounds: int = 3
    agents: List[str] = field(default_factory=list)
    user_injections: List[str] = field(default_factory=list)
    consensus_level: float = 0.0
    top_candidates: List[str] = field(default_factory=list)
    phase_history: List[Dict] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "phase": self.phase.value,
            "topology": self.topology.value,
            "created_at": self.created_at.isoformat(),
            "ideas_count": len(self.ideas),
            "current_round": self.current_round,
            "max_rounds": self.max_rounds,
            "agents": self.agents,
            "user_injections": self.user_injections,
            "consensus_level": self.consensus_level,
            "top_candidates": self.top_candidates
        }


@dataclass
class BrainstormResults:
    """Results from a completed brainstorm session"""
    session_id: str
    topic: str
    duration_seconds: float
    total_ideas: int
    top_ideas: List[Dict[str, Any]]
    recommendation: str
    confidence_score: float
    core_insight: str
    learnings: List[str]
    next_steps: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "duration_seconds": self.duration_seconds,
            "total_ideas": self.total_ideas,
            "top_ideas": self.top_ideas,
            "recommendation": self.recommendation,
            "confidence_score": self.confidence_score,
            "core_insight": self.core_insight,
            "learnings": self.learnings,
            "next_steps": self.next_steps
        }


class ThinkingAgent:
    """Base class for thinking persona agents"""

    def __init__(self, name: str, emoji: str, thinking_style: str):
        self.name = name
        self.emoji = emoji
        self.thinking_style = thinking_style
        self.contributions: List[str] = []

    async def generate_ideas(self, topic: str, context: Dict[str, Any]) -> List[str]:
        """Generate ideas based on agent's thinking style"""
        raise NotImplementedError

    async def evaluate_idea(self, idea: Idea, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate an idea based on agent's perspective"""
        raise NotImplementedError

    async def build_on_idea(self, idea: Idea, context: Dict[str, Any]) -> Optional[str]:
        """Build on or extend an existing idea"""
        raise NotImplementedError


class IdeatorAgent(ThinkingAgent):
    """Creative idea generator - divergent thinking"""

    def __init__(self):
        super().__init__("Ideator", "🎨", "divergent")

    async def generate_ideas(self, topic: str, context: Dict[str, Any]) -> List[str]:
        """Generate multiple creative ideas"""
        # In production, this would call an LLM
        # For now, return placeholder that gets populated by actual agent execution
        return [
            f"[Ideator would generate creative ideas for: {topic}]",
            f"[Using techniques: random combination, reversal, analogy]"
        ]


class CriticAgent(ThinkingAgent):
    """Devil's advocate - analytical thinking"""

    def __init__(self):
        super().__init__("Critic", "🔍", "analytical")

    async def evaluate_idea(self, idea: Idea, context: Dict[str, Any]) -> Dict[str, Any]:
        """Critically evaluate an idea"""
        return {
            "idea_id": idea.id,
            "concerns": [],
            "severity": "medium",
            "suggestions": []
        }


class StrategistAgent(ThinkingAgent):
    """Long-term thinker - systems thinking"""

    def __init__(self):
        super().__init__("Strategist", "🎯", "systems")

    async def evaluate_idea(self, idea: Idea, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate strategic implications"""
        return {
            "idea_id": idea.id,
            "goal_alignment": 0.8,
            "time_horizon": "medium",
            "strategic_value": "Potentially high impact"
        }


class BuilderAgent(ThinkingAgent):
    """Practical implementer - convergent thinking"""

    def __init__(self):
        super().__init__("Builder", "🔧", "convergent")

    async def evaluate_idea(self, idea: Idea, context: Dict[str, Any]) -> Dict[str, Any]:
        """Assess implementation feasibility"""
        return {
            "idea_id": idea.id,
            "feasibility": "moderate",
            "effort": "M",
            "mvp": "Simplified version possible"
        }


class SynthesizerAgent(ThinkingAgent):
    """Pattern finder - integrative thinking"""

    def __init__(self):
        super().__init__("Synthesizer", "💡", "integrative")

    async def find_patterns(self, ideas: List[Idea]) -> Dict[str, Any]:
        """Find patterns and combinations across ideas"""
        return {
            "patterns": [],
            "clusters": {},
            "combinations": [],
            "core_insight": ""
        }


class BrainstormOrchestrator:
    """
    Orchestrates collective reasoning sessions with thinking persona agents.

    Supports both:
    - User-interactive sessions (via slash commands in Claude Code)
    - Autonomous internal sessions (via Python API)
    """

    def __init__(self, storage_base: Optional[str] = None):
        self.storage_base = storage_base or os.environ.get(
            'STORAGE_BASE',
            str(_STORAGE_BASE)
        )
        self.active_session: Optional[BrainstormSession] = None
        self.agents: Dict[str, ThinkingAgent] = {
            "ideator": IdeatorAgent(),
            "critic": CriticAgent(),
            "strategist": StrategistAgent(),
            "builder": BuilderAgent(),
            "synthesizer": SynthesizerAgent()
        }
        self.output_callback: Optional[Callable[[str], None]] = None
        self._memory_client = None

    async def _get_memory_client(self):
        """Get or create memory client for persistence"""
        if self._memory_client is None:
            # Try to connect to enhanced-memory MCP
            try:
                # This would be the actual MCP client connection
                pass
            except Exception as e:
                logger.warning(f"Could not connect to memory MCP: {e}")
        return self._memory_client

    def _emit(self, message: str):
        """Emit output to callback or stdout"""
        if self.output_callback:
            self.output_callback(message)
        else:
            print(message)

    async def start_session(
        self,
        topic: str,
        mode: str = "divergent",
        max_rounds: int = 3,
        agents: Optional[List[str]] = None,
        voice: bool = False,
        output_callback: Optional[Callable[[str], None]] = None
    ) -> BrainstormSession:
        """
        Start an interactive brainstorming session.

        Args:
            topic: The problem or question to brainstorm
            mode: Starting phase (divergent, convergent, critical, synthesis)
            max_rounds: Maximum rounds per phase
            agents: List of agent names to use (default: all 5)
            voice: Enable voice narration
            output_callback: Function to receive real-time output

        Returns:
            BrainstormSession object
        """
        self.output_callback = output_callback

        session_id = str(uuid.uuid4())[:8]
        initial_phase = BrainstormPhase(mode) if mode != "divergent" else BrainstormPhase.DIVERGENT
        initial_topology = self._get_topology_for_phase(initial_phase)

        self.active_session = BrainstormSession(
            id=session_id,
            topic=topic,
            phase=initial_phase,
            topology=initial_topology,
            created_at=datetime.now(),
            max_rounds=max_rounds,
            agents=agents or list(self.agents.keys()),
            config={
                "voice": voice,
                "interactive": True
            }
        )

        # Store session state
        await self._store_session_state()

        # Announce session start
        self._emit(f"\n[Brainstorm Session: {topic} | Phase: {initial_phase.value} | Round 1/{max_rounds}]\n")
        self._emit(f"Session ID: {session_id}")
        self._emit(f"Agents: {', '.join([self.agents[a].emoji + ' ' + self.agents[a].name for a in self.active_session.agents])}")
        self._emit("\n[Commands: /brainstorm-inject, /brainstorm-mode, /brainstorm-conclude]\n")

        return self.active_session

    async def start_internal_session(
        self,
        topic: str,
        context: Optional[Dict[str, Any]] = None,
        max_rounds: int = 3,
        auto_conclude: bool = True,
        store_learnings: bool = True
    ) -> BrainstormResults:
        """
        Start an autonomous internal brainstorming session.

        This is the API for internal system use when encountering complex problems
        that benefit from collective reasoning.

        Args:
            topic: The problem to solve
            context: Additional context about the problem
            max_rounds: Maximum rounds per phase
            auto_conclude: Automatically conclude when consensus reached
            store_learnings: Store results in memory

        Returns:
            BrainstormResults with recommendations
        """
        logger.info(f"Starting internal brainstorm session: {topic}")

        session_id = str(uuid.uuid4())[:8]
        start_time = datetime.now()

        self.active_session = BrainstormSession(
            id=session_id,
            topic=topic,
            phase=BrainstormPhase.DIVERGENT,
            topology=Topology.MESH,
            created_at=start_time,
            max_rounds=max_rounds,
            agents=list(self.agents.keys()),
            config={
                "context": context or {},
                "auto_conclude": auto_conclude,
                "store_learnings": store_learnings,
                "interactive": False
            }
        )

        # Run through phases automatically
        await self._run_divergent_phase()
        await self._run_convergent_phase()
        await self._run_critical_phase()
        await self._run_synthesis_phase()

        # Calculate results
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        results = await self._generate_results(duration)

        # Store learnings if enabled
        if store_learnings:
            await self._store_learnings(results)

        # Clear active session
        self.active_session = None

        return results

    def _get_topology_for_phase(self, phase: BrainstormPhase) -> Topology:
        """Get the appropriate topology for a phase"""
        topology_map = {
            BrainstormPhase.DIVERGENT: Topology.MESH,
            BrainstormPhase.CONVERGENT: Topology.HIERARCHICAL,
            BrainstormPhase.CRITICAL: Topology.RING,
            BrainstormPhase.SYNTHESIS: Topology.STAR,
        }
        return topology_map.get(phase, Topology.MESH)

    async def change_mode(self, mode: str) -> bool:
        """
        Change the current brainstorming phase.

        Args:
            mode: New phase (divergent, convergent, critical, synthesis, pause, conclude)

        Returns:
            Success boolean
        """
        if not self.active_session:
            logger.error("No active session")
            return False

        if mode == "conclude":
            await self.conclude()
            return True

        if mode == "pause":
            self.active_session.phase = BrainstormPhase.PAUSED
            self._emit("\n[Session paused. Use /brainstorm-mode <mode> to resume.]\n")
            return True

        try:
            new_phase = BrainstormPhase(mode)
        except ValueError:
            logger.error(f"Invalid mode: {mode}")
            return False

        old_phase = self.active_session.phase
        self.active_session.phase = new_phase
        self.active_session.topology = self._get_topology_for_phase(new_phase)
        self.active_session.current_round = 1

        # Record phase transition
        self.active_session.phase_history.append({
            "from": old_phase.value,
            "to": new_phase.value,
            "timestamp": datetime.now().isoformat(),
            "ideas_at_transition": len(self.active_session.ideas)
        })

        self._emit(f"\n[Phase transition: {old_phase.value} → {new_phase.value}]")
        self._emit(f"[Topology: {self.active_session.topology.value}]\n")

        await self._store_session_state()
        return True

    async def inject_idea(self, thought: str) -> Idea:
        """
        Inject user input into the session.

        Args:
            thought: User's idea or comment

        Returns:
            Created Idea object
        """
        if not self.active_session:
            raise ValueError("No active session")

        idea = Idea(
            id=str(uuid.uuid4())[:8],
            content=thought,
            author="user",
            phase=self.active_session.phase.value,
            round=self.active_session.current_round,
            timestamp=datetime.now(),
            weight=1.5  # User ideas weighted higher
        )

        self.active_session.ideas.append(idea)
        self.active_session.user_injections.append(idea.id)

        self._emit(f"\n👤 USER: {thought}\n")

        # Trigger agent responses (in interactive mode)
        if self.active_session.config.get("interactive"):
            await self._trigger_agent_responses(idea)

        await self._store_session_state()
        return idea

    async def get_status(self) -> Dict[str, Any]:
        """Get current session status"""
        if not self.active_session:
            return {"active": False, "message": "No active session"}

        return {
            "active": True,
            "session": self.active_session.to_dict(),
            "ideas": [i.to_dict() for i in self.active_session.ideas],
            "agents": {
                name: {
                    "emoji": agent.emoji,
                    "contributions": len(agent.contributions)
                }
                for name, agent in self.agents.items()
            }
        }

    async def conclude(self) -> BrainstormResults:
        """
        Conclude the session and generate results.

        Returns:
            BrainstormResults with recommendations
        """
        if not self.active_session:
            raise ValueError("No active session")

        start_time = self.active_session.created_at
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Run synthesis if not already done
        if self.active_session.phase != BrainstormPhase.SYNTHESIS:
            await self.change_mode("synthesis")
            await self._run_synthesis_phase()

        results = await self._generate_results(duration)

        # Store learnings
        if self.active_session.config.get("store_learnings", True):
            await self._store_learnings(results)

        # Emit conclusion report
        self._emit_conclusion_report(results)

        # Mark session concluded
        self.active_session.phase = BrainstormPhase.CONCLUDED
        await self._store_session_state()

        # Clear active session
        session = self.active_session
        self.active_session = None

        return results

    async def _run_divergent_phase(self):
        """Run divergent phase internally"""
        if not self.active_session:
            return

        self.active_session.phase = BrainstormPhase.DIVERGENT
        self.active_session.topology = Topology.MESH

        for round_num in range(1, self.active_session.max_rounds + 1):
            self.active_session.current_round = round_num

            # Each agent generates ideas
            for agent_name in self.active_session.agents:
                agent = self.agents[agent_name]

                # In production, this would call actual LLM agents
                # For now, create placeholder ideas
                idea = Idea(
                    id=str(uuid.uuid4())[:8],
                    content=f"[{agent.name} idea for round {round_num}]",
                    author=agent_name,
                    phase="divergent",
                    round=round_num,
                    timestamp=datetime.now()
                )
                self.active_session.ideas.append(idea)

    async def _run_convergent_phase(self):
        """Run convergent phase internally"""
        if not self.active_session:
            return

        self.active_session.phase = BrainstormPhase.CONVERGENT
        self.active_session.topology = Topology.HIERARCHICAL

        # Vote on ideas
        for idea in self.active_session.ideas:
            for agent_name in self.active_session.agents:
                # Simplified voting - in production would use actual agent evaluation
                idea.votes[agent_name] = 1

        # Identify top candidates
        sorted_ideas = sorted(self.active_session.ideas, key=lambda i: i.score, reverse=True)
        self.active_session.top_candidates = [i.id for i in sorted_ideas[:5]]

    async def _run_critical_phase(self):
        """Run critical phase internally"""
        if not self.active_session:
            return

        self.active_session.phase = BrainstormPhase.CRITICAL
        self.active_session.topology = Topology.RING

        # Critic evaluates top candidates
        for idea_id in self.active_session.top_candidates:
            idea = next((i for i in self.active_session.ideas if i.id == idea_id), None)
            if idea:
                # Add critique metadata
                idea.metadata["critiqued"] = True
                idea.metadata["critique_passed"] = True  # Simplified

    async def _run_synthesis_phase(self):
        """Run synthesis phase internally"""
        if not self.active_session:
            return

        self.active_session.phase = BrainstormPhase.SYNTHESIS
        self.active_session.topology = Topology.STAR

        # Synthesizer finds patterns
        # In production, would use actual LLM synthesis
        self.active_session.consensus_level = 0.85

    async def _generate_results(self, duration: float) -> BrainstormResults:
        """Generate final results from session"""
        if not self.active_session:
            raise ValueError("No active session")

        # Get top ideas
        sorted_ideas = sorted(self.active_session.ideas, key=lambda i: i.score, reverse=True)
        top_ideas = [i.to_dict() for i in sorted_ideas[:5]]

        return BrainstormResults(
            session_id=self.active_session.id,
            topic=self.active_session.topic,
            duration_seconds=duration,
            total_ideas=len(self.active_session.ideas),
            top_ideas=top_ideas,
            recommendation=f"Based on collective analysis of {len(self.active_session.ideas)} ideas, recommend pursuing top-ranked approaches.",
            confidence_score=self.active_session.consensus_level,
            core_insight=f"Core insight from brainstorming '{self.active_session.topic}'",
            learnings=[
                f"Generated {len(self.active_session.ideas)} ideas in {duration:.1f} seconds",
                f"User contributed {len(self.active_session.user_injections)} ideas",
                f"Consensus level: {self.active_session.consensus_level:.0%}"
            ],
            next_steps=[
                "Review top recommendations",
                "Validate feasibility with Builder assessment",
                "Create implementation plan"
            ]
        )

    async def _store_session_state(self):
        """Store session state to memory"""
        if not self.active_session:
            return

        # In production, this would store to enhanced-memory MCP
        state = self.active_session.to_dict()
        logger.debug(f"Storing session state: {state['id']}")

    async def _store_learnings(self, results: BrainstormResults):
        """Store session learnings to memory"""
        logger.info(f"Storing learnings for session {results.session_id}")

        # In production, this would:
        # 1. Store session to episodic memory
        # 2. Promote top ideas to semantic memory
        # 3. Store effective techniques to procedural memory

    async def _trigger_agent_responses(self, trigger_idea: Idea):
        """Trigger agent responses to a new idea"""
        # In interactive mode, agents respond to user input
        # This would spawn actual Claude agents in production
        pass

    def _emit_conclusion_report(self, results: BrainstormResults):
        """Emit formatted conclusion report"""
        self._emit("\n" + "=" * 60)
        self._emit(f"  BRAINSTORM CONCLUDED: {results.topic}")
        self._emit("=" * 60)
        self._emit(f"  Duration: {results.duration_seconds:.1f}s | Ideas: {results.total_ideas}")
        self._emit("-" * 60)
        self._emit("\n  🏆 TOP RECOMMENDATIONS\n")

        for i, idea in enumerate(results.top_ideas[:3], 1):
            medal = ["🥇", "🥈", "🥉"][i - 1]
            self._emit(f"  {medal} {idea['content'][:50]}...")
            self._emit(f"     Score: {idea['score']:.1f}\n")

        self._emit("-" * 60)
        self._emit(f"  💡 CORE INSIGHT")
        self._emit(f"  {results.core_insight}\n")
        self._emit("=" * 60 + "\n")


# Trigger conditions for autonomous brainstorming
class BrainstormTrigger:
    """
    Defines conditions that should trigger autonomous brainstorming.

    Use with the AGI system to auto-detect when collective reasoning
    would benefit problem-solving.
    """

    @staticmethod
    def should_trigger(
        problem_description: str,
        confidence: float,
        similar_solutions_found: int,
        impact_score: float
    ) -> tuple[bool, str]:
        """
        Determine if brainstorming should be triggered.

        Args:
            problem_description: Description of the problem
            confidence: Current confidence in approach (0-1)
            similar_solutions_found: Count of similar past solutions
            impact_score: Expected impact of decision (0-1)

        Returns:
            (should_trigger, reason)
        """
        # Novel problem - no similar solutions
        if similar_solutions_found == 0:
            return True, "Novel problem with no similar past solutions"

        # High-stakes decision
        if impact_score > 0.8:
            return True, f"High-stakes decision (impact: {impact_score:.0%})"

        # Low confidence
        if confidence < 0.5:
            return True, f"Low confidence in approach ({confidence:.0%})"

        # Multiple valid approaches (indicated by moderate confidence with solutions)
        if 0.5 <= confidence <= 0.7 and similar_solutions_found > 1:
            return True, "Multiple valid approaches exist - need to compare"

        return False, "Standard approach sufficient"


# Convenience function for quick internal brainstorming
async def brainstorm(
    topic: str,
    context: Optional[Dict[str, Any]] = None
) -> BrainstormResults:
    """
    Quick function to run internal brainstorm.

    Args:
        topic: What to brainstorm about
        context: Optional additional context

    Returns:
        BrainstormResults
    """
    orchestrator = BrainstormOrchestrator()
    return await orchestrator.start_internal_session(
        topic=topic,
        context=context,
        auto_conclude=True,
        store_learnings=True
    )


if __name__ == "__main__":
    # Demo usage
    async def demo():
        print("Brainstorm Orchestrator Demo")
        print("=" * 40)

        orchestrator = BrainstormOrchestrator()

        # Demo internal session
        results = await orchestrator.start_internal_session(
            topic="How to improve the agentic system's learning capabilities",
            context={"domain": "AGI development"},
            max_rounds=2,
            auto_conclude=True
        )

        print("\nResults:")
        print(json.dumps(results.to_dict(), indent=2))

    asyncio.run(demo())

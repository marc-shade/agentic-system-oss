#!/usr/bin/env python3
"""
TPU Agent Router - Intelligent Task Routing with Edge TPU

Routes tasks to specialized agents using semantic similarity matching.
Fast (~40ms) classification enables real-time task routing without API calls.

Available Agent Types:
- researcher: Research, analysis, information gathering
- coder: Implementation, code writing, feature development
- debugger: Error investigation, troubleshooting
- reviewer: Code review, quality assurance
- architect: System design, architecture decisions
- tester: Testing, validation, verification
- documenter: Documentation, explanations
- coordinator: Multi-agent coordination

Usage:
    from tpu_agent_router import TPUAgentRouter

    router = TPUAgentRouter()
    routing = await router.route_task(
        "Fix the memory leak in the cache module"
    )
    print(f"Route to: {routing.agent_type} ({routing.confidence:.2f})")
"""
import platform

import os
import sys
import json
import time
import logging
import numpy as np
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

# Add hooks path
AGENTIC_SYSTEM_PATH = os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE))
HOOKS_PATH = os.path.join(AGENTIC_SYSTEM_PATH, "scripts/hooks")
if HOOKS_PATH not in sys.path:
    sys.path.insert(0, HOOKS_PATH)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tpu_agent_router")

# TPU imports
TPU_AVAILABLE = False
_embed_text = None

try:
    from tpu_importance import embed_text, is_tpu_available
    if is_tpu_available():
        _embed_text = embed_text
        TPU_AVAILABLE = True
except ImportError:
    pass

try:
    from tpu_monitor import record_tpu_usage
    HAS_TPU_MONITOR = True
except ImportError:
    HAS_TPU_MONITOR = False


class AgentType(Enum):
    """Available agent types"""
    RESEARCHER = "researcher"
    CODER = "coder"
    DEBUGGER = "debugger"
    REVIEWER = "reviewer"
    ARCHITECT = "architect"
    TESTER = "tester"
    DOCUMENTER = "documenter"
    COORDINATOR = "coordinator"
    GENERAL = "general"


# Agent capability descriptions for semantic matching
AGENT_TEMPLATES = {
    AgentType.RESEARCHER: (
        "Research information, search papers, analyze data, gather knowledge. "
        "Find documentation, investigate topics, synthesize information from sources. "
        "Academic research, technical research, domain exploration."
    ),
    AgentType.CODER: (
        "Write code, implement features, develop software, create modules. "
        "Programming, coding, development, building applications. "
        "Create functions, classes, APIs, implement algorithms."
    ),
    AgentType.DEBUGGER: (
        "Debug errors, investigate issues, trace problems, diagnose failures. "
        "Troubleshooting, error analysis, stack trace analysis, root cause investigation. "
        "Fix bugs, resolve crashes, identify memory leaks, analyze logs."
    ),
    AgentType.REVIEWER: (
        "Review code, check quality, verify correctness, assess changes. "
        "Code review, quality assurance, best practices verification. "
        "Identify issues, suggest improvements, ensure standards compliance."
    ),
    AgentType.ARCHITECT: (
        "Design systems, plan architecture, make technical decisions. "
        "System design, software architecture, infrastructure planning. "
        "Design patterns, scalability, modularity, technical strategy."
    ),
    AgentType.TESTER: (
        "Write tests, run tests, verify functionality, validate behavior. "
        "Unit testing, integration testing, test coverage, test automation. "
        "Quality verification, regression testing, test-driven development."
    ),
    AgentType.DOCUMENTER: (
        "Write documentation, explain code, create tutorials, describe APIs. "
        "Technical writing, documentation, readme files, guides. "
        "Explain concepts, create examples, write comments."
    ),
    AgentType.COORDINATOR: (
        "Coordinate tasks, manage workflow, orchestrate multiple agents. "
        "Task management, project coordination, multi-step planning. "
        "Break down complex tasks, assign subtasks, merge results."
    ),
    AgentType.GENERAL: (
        "General purpose assistance, various tasks, flexible help. "
        "Miscellaneous tasks that don't fit specific categories."
    )
}

# Keyword patterns for fallback matching
AGENT_KEYWORDS = {
    AgentType.RESEARCHER: [
        "research", "find", "search", "look up", "investigate", "analyze",
        "documentation", "paper", "article", "learn about"
    ],
    AgentType.CODER: [
        "implement", "create", "write", "build", "develop", "code",
        "add feature", "make", "generate", "function", "class"
    ],
    AgentType.DEBUGGER: [
        "debug", "fix", "error", "bug", "issue", "problem", "crash",
        "investigate", "trace", "why", "failing", "broken"
    ],
    AgentType.REVIEWER: [
        "review", "check", "verify", "validate", "assess", "evaluate",
        "look at", "examine", "code review", "quality"
    ],
    AgentType.ARCHITECT: [
        "design", "architect", "structure", "plan", "organize",
        "system", "infrastructure", "pattern", "decision"
    ],
    AgentType.TESTER: [
        "test", "testing", "unit test", "verify", "validate",
        "coverage", "assert", "expect", "spec"
    ],
    AgentType.DOCUMENTER: [
        "document", "explain", "describe", "write docs", "readme",
        "tutorial", "guide", "comment", "docstring"
    ],
    AgentType.COORDINATOR: [
        "coordinate", "orchestrate", "manage", "plan tasks",
        "break down", "multiple", "workflow", "pipeline"
    ]
}


@dataclass
class RoutingResult:
    """Result of task routing"""
    agent_type: AgentType
    confidence: float
    all_scores: Dict[str, float]
    reasoning: str
    fallback_options: List[Tuple[AgentType, float]]
    latency_ms: float


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class TPUAgentRouter:
    """
    Route tasks to specialized agents using TPU embeddings.

    Uses semantic similarity to match task descriptions to agent
    capabilities for intelligent, fast routing.
    """

    def __init__(self):
        self.use_tpu = TPU_AVAILABLE
        self._template_embeddings: Dict[AgentType, np.ndarray] = {}
        self._embedding_cache: Dict[str, np.ndarray] = {}

        # Routing history for learning
        self.routing_history: List[Dict] = []
        self.max_history = 100

        # Precompute template embeddings
        if self.use_tpu:
            self._precompute_templates()
            logger.info("TPU agent routing enabled")
        else:
            logger.info("Using fallback keyword-based routing")

    def _precompute_templates(self):
        """Precompute embeddings for agent templates."""
        if not self.use_tpu or not _embed_text:
            return

        for agent_type, template in AGENT_TEMPLATES.items():
            try:
                start = time.perf_counter()
                embedding = _embed_text(template)
                latency = (time.perf_counter() - start) * 1000

                if embedding is not None:
                    self._template_embeddings[agent_type] = np.array(embedding, dtype=np.float32)

                    if HAS_TPU_MONITOR:
                        record_tpu_usage(
                            "agent_template_embedding",
                            latency_ms=latency,
                            source="agent_router",
                            metadata={"agent": agent_type.value}
                        )
            except Exception as e:
                logger.warning(f"Failed to embed template for {agent_type}: {e}")

        logger.info(f"Precomputed {len(self._template_embeddings)} agent templates")

    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get text embedding with caching."""
        cache_key = str(hash(text))
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        if not self.use_tpu or not _embed_text:
            return None

        try:
            start = time.perf_counter()
            embedding = _embed_text(text)
            latency = (time.perf_counter() - start) * 1000

            if embedding is not None:
                emb_array = np.array(embedding, dtype=np.float32)
                self._embedding_cache[cache_key] = emb_array

                if HAS_TPU_MONITOR:
                    record_tpu_usage(
                        "task_embedding",
                        latency_ms=latency,
                        source="agent_router"
                    )
                return emb_array
        except Exception as e:
            logger.warning(f"Embedding failed: {e}")

        return None

    def _keyword_score(self, text: str, agent_type: AgentType) -> float:
        """Calculate keyword-based score."""
        text_lower = text.lower()
        keywords = AGENT_KEYWORDS.get(agent_type, [])

        matches = sum(1 for kw in keywords if kw in text_lower)
        return min(1.0, matches / max(len(keywords) / 3, 1))

    async def route_task(
        self,
        task_description: str,
        context: Optional[str] = None,
        exclude_agents: Optional[List[AgentType]] = None
    ) -> RoutingResult:
        """
        Route a task to the best suited agent.

        Args:
            task_description: Description of the task
            context: Additional context (optional)
            exclude_agents: Agent types to exclude from routing

        Returns:
            RoutingResult with selected agent and confidence
        """
        start_time = time.perf_counter()

        exclude = set(exclude_agents or [])

        # Build full text
        full_text = task_description
        if context:
            full_text += f" | Context: {context}"

        # Get task embedding
        task_embedding = self._get_embedding(full_text)

        if task_embedding is not None and self._template_embeddings:
            # TPU-based routing
            scores = {}
            for agent_type, template_emb in self._template_embeddings.items():
                if agent_type in exclude:
                    continue
                similarity = cosine_similarity(task_embedding, template_emb)
                # Boost with keyword matching
                keyword_boost = self._keyword_score(full_text, agent_type) * 0.15
                scores[agent_type] = similarity + keyword_boost
        else:
            # Fallback to keyword-only
            scores = {
                agent_type: self._keyword_score(full_text, agent_type)
                for agent_type in AgentType
                if agent_type not in exclude
            }

        if not scores:
            scores = {AgentType.GENERAL: 0.5}

        # Find best agent
        best_agent = max(scores, key=scores.get)
        confidence = scores[best_agent]

        # Normalize scores
        max_score = max(scores.values()) if scores.values() else 1.0
        if max_score > 0:
            normalized_scores = {k.value: v / max_score for k, v in scores.items()}
        else:
            normalized_scores = {k.value: 0 for k in scores}

        # Get fallback options (2nd and 3rd best)
        sorted_agents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        fallbacks = [(a, s) for a, s in sorted_agents[1:3] if s > 0.3]

        # Build reasoning
        reasoning_parts = []
        matched_keywords = [
            kw for kw in AGENT_KEYWORDS.get(best_agent, [])
            if kw in full_text.lower()
        ]
        if matched_keywords:
            reasoning_parts.append(f"Keywords: {', '.join(matched_keywords[:3])}")
        if confidence > 0.7:
            reasoning_parts.append("High confidence match")
        elif fallbacks:
            reasoning_parts.append(f"Consider also: {fallbacks[0][0].value}")

        reasoning = " | ".join(reasoning_parts) if reasoning_parts else "Best semantic match"

        latency_ms = (time.perf_counter() - start_time) * 1000

        # Record routing
        self.routing_history.append({
            "timestamp": datetime.now().isoformat(),
            "task": task_description[:100],
            "routed_to": best_agent.value,
            "confidence": confidence
        })
        while len(self.routing_history) > self.max_history:
            self.routing_history.pop(0)

        if HAS_TPU_MONITOR:
            record_tpu_usage(
                "task_routing",
                latency_ms=latency_ms,
                source="agent_router",
                metadata={
                    "agent": best_agent.value,
                    "confidence": confidence
                }
            )

        return RoutingResult(
            agent_type=best_agent,
            confidence=confidence,
            all_scores=normalized_scores,
            reasoning=reasoning,
            fallback_options=fallbacks,
            latency_ms=latency_ms
        )

    async def route_multi_agent(
        self,
        task_description: str,
        max_agents: int = 3
    ) -> List[Tuple[AgentType, float]]:
        """
        Route a complex task to multiple agents.

        Returns list of (agent_type, relevance_score) for parallel execution.
        """
        result = await self.route_task(task_description)

        agents = [(result.agent_type, result.confidence)]
        agents.extend(result.fallback_options[:max_agents - 1])

        return agents

    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get routing statistics."""
        agent_counts: Dict[str, int] = {}
        for routing in self.routing_history:
            agent = routing["routed_to"]
            agent_counts[agent] = agent_counts.get(agent, 0) + 1

        return {
            "tpu_available": self.use_tpu,
            "templates_loaded": len(self._template_embeddings),
            "cache_size": len(self._embedding_cache),
            "total_routings": len(self.routing_history),
            "agent_distribution": agent_counts,
            "available_agents": [a.value for a in AgentType]
        }


# CLI
if __name__ == "__main__":
    import asyncio
    import argparse

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


    parser = argparse.ArgumentParser(description="TPU Agent Router")
    parser.add_argument("command", choices=["route", "stats", "test"],
                       help="Command to run")
    parser.add_argument("--task", "-t", type=str, help="Task description")

    args = parser.parse_args()

    router = TPUAgentRouter()

    if args.command == "route":
        if not args.task:
            print("Error: --task required")
            sys.exit(1)

        result = asyncio.run(router.route_task(args.task))
        print(json.dumps({
            "agent": result.agent_type.value,
            "confidence": result.confidence,
            "all_scores": result.all_scores,
            "reasoning": result.reasoning,
            "fallbacks": [(a.value, s) for a, s in result.fallback_options],
            "latency_ms": result.latency_ms
        }, indent=2))

    elif args.command == "stats":
        print(json.dumps(router.get_routing_statistics(), indent=2))

    elif args.command == "test":
        test_tasks = [
            "Find documentation about the TPU API",
            "Implement a new caching layer",
            "Fix the memory leak in the worker thread",
            "Review the pull request changes",
            "Design the microservices architecture",
            "Write unit tests for the parser",
            "Document the API endpoints"
        ]

        print("Testing task routing:\n")
        for task in test_tasks:
            result = asyncio.run(router.route_task(task))
            print(f"Task: {task}")
            print(f"  -> {result.agent_type.value} ({result.confidence:.2f})")
            print()

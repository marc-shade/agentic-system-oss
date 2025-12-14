#!/usr/bin/env python3
"""
TPU Hook Integration Layer

Unified interface for Claude Code hooks to leverage Edge TPU intelligence.
Provides fast, async-friendly access to all TPU-AGI modules.

Usage from shell hooks:
    python3 /home/marc/agentic-system/scripts/hooks/tpu_hook_integration.py \
        --hook pre_tool_use --tool_name Task --tool_input '{"subagent_type":"researcher"}'

Usage from Python:
    from tpu_hook_integration import TPUHookIntegration
    integration = TPUHookIntegration()
    result = await integration.pre_tool_use(tool_name, tool_input)
"""
import platform

import os
import sys
import json
import argparse
import asyncio
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Add paths
AGENTIC_SYSTEM_PATH = os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE))
HOOKS_PATH = os.path.join(os.path.dirname(__file__))
AGENTS_PATH = os.path.join(AGENTIC_SYSTEM_PATH, "intelligent-agents")

for path in [HOOKS_PATH, AGENTS_PATH]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - TPU-Hook - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tpu_hook_integration")

# Import base TPU module
TPU_AVAILABLE = False
try:
    from tpu_importance import (
        embed_text,
        score_importance,
        classify_intent,
        is_tpu_available
    )
    TPU_AVAILABLE = is_tpu_available()
except ImportError as e:
    logger.warning(f"TPU base module not available: {e}")

# Import TPU-AGI modules (lazy loading to avoid import overhead)
_modules = {}

def get_agent_router():
    """Lazy load TPU Agent Router."""
    if 'agent_router' not in _modules:
        try:
            from tpu_agent_router import TPUAgentRouter
            _modules['agent_router'] = TPUAgentRouter()
        except ImportError as e:
            logger.warning(f"Agent router not available: {e}")
            _modules['agent_router'] = None
    return _modules['agent_router']

def get_action_matcher():
    """Lazy load TPU Action Pattern Matcher."""
    if 'action_matcher' not in _modules:
        try:
            from tpu_action_pattern_matcher import TPUActionPatternMatcher
            _modules['action_matcher'] = TPUActionPatternMatcher()
        except ImportError as e:
            logger.warning(f"Action matcher not available: {e}")
            _modules['action_matcher'] = None
    return _modules['action_matcher']

def get_session_classifier():
    """Lazy load TPU Session Classifier."""
    if 'session_classifier' not in _modules:
        try:
            from tpu_session_classifier import TPUSessionClassifier
            _modules['session_classifier'] = TPUSessionClassifier()
        except ImportError as e:
            logger.warning(f"Session classifier not available: {e}")
            _modules['session_classifier'] = None
    return _modules['session_classifier']

def get_metacognitive_classifier():
    """Lazy load TPU Metacognitive Classifier."""
    if 'metacognitive' not in _modules:
        try:
            from tpu_metacognitive_classifier import TPUMetacognitiveClassifier
            _modules['metacognitive'] = TPUMetacognitiveClassifier()
        except ImportError as e:
            logger.warning(f"Metacognitive classifier not available: {e}")
            _modules['metacognitive'] = None
    return _modules['metacognitive']

def get_episode_clusterer():
    """Lazy load TPU Episode Clusterer."""
    if 'episode_clusterer' not in _modules:
        try:
            from tpu_episode_clusterer import TPUEpisodeClusterer
            _modules['episode_clusterer'] = TPUEpisodeClusterer()
        except ImportError as e:
            logger.warning(f"Episode clusterer not available: {e}")
            _modules['episode_clusterer'] = None
    return _modules['episode_clusterer']

def get_belief_classifier():
    """Lazy load TPU Belief Classifier."""
    if 'belief_classifier' not in _modules:
        try:
            from tpu_belief_classifier import TPUBeliefClassifier
            _modules['belief_classifier'] = TPUBeliefClassifier()
        except ImportError as e:
            logger.warning(f"Belief classifier not available: {e}")
            _modules['belief_classifier'] = None
    return _modules['belief_classifier']

def get_causal_recognizer():
    """Lazy load TPU Causal Recognizer."""
    if 'causal_recognizer' not in _modules:
        try:
            from tpu_causal_recognizer import TPUCausalRecognizer
            _modules['causal_recognizer'] = TPUCausalRecognizer()
        except ImportError as e:
            logger.warning(f"Causal recognizer not available: {e}")
            _modules['causal_recognizer'] = None
    return _modules['causal_recognizer']

def get_knowledge_scorer():
    """Lazy load TPU Knowledge Scorer."""
    if 'knowledge_scorer' not in _modules:
        try:
            from tpu_knowledge_scorer import TPUKnowledgeScorer

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

            _modules['knowledge_scorer'] = TPUKnowledgeScorer()
        except ImportError as e:
            logger.warning(f"Knowledge scorer not available: {e}")
            _modules['knowledge_scorer'] = None
    return _modules['knowledge_scorer']


@dataclass
class HookResult:
    """Result from TPU hook processing."""
    success: bool
    hook_type: str
    tpu_used: bool
    latency_ms: float
    data: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class TPUHookIntegration:
    """
    Unified TPU integration for Claude Code hooks.

    Provides intelligent processing for:
    - PreToolUse: Agent routing, task classification
    - PostToolUse: Action outcome analysis, pattern matching
    - SessionStart: Session context classification
    - UserPromptSubmit: Intent analysis, metacognitive state
    """

    def __init__(self):
        self.tpu_available = TPU_AVAILABLE
        self._cache: Dict[str, Any] = {}

    async def pre_tool_use(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> HookResult:
        """
        Process PreToolUse hook with TPU intelligence.

        For Task tool: Route to optimal agent using TPU embeddings.
        For other tools: Score importance and classify intent.
        """
        start_time = time.perf_counter()
        result = HookResult(
            success=True,
            hook_type="pre_tool_use",
            tpu_used=False,
            latency_ms=0.0
        )

        try:
            if tool_name == "Task":
                # Agent routing for Task tool
                router = get_agent_router()
                if router:
                    subagent_type = tool_input.get("subagent_type", "")
                    task_description = tool_input.get("description", "")
                    prompt = tool_input.get("prompt", "")

                    # Get routing recommendation
                    routing = await router.route_task(
                        task_description=task_description or prompt[:200],
                        context=f"requested: {subagent_type}"
                    )

                    result.tpu_used = router.use_tpu
                    recommended = routing.agent.value if routing and hasattr(routing.agent, 'value') else (routing.agent if routing else subagent_type)
                    result.data["routing"] = {
                        "recommended_agent": recommended,
                        "confidence": routing.confidence if routing else 0.5,
                        "reasoning": routing.reasoning if routing else "Fallback routing"
                    }

                    if routing and recommended != subagent_type:
                        result.recommendations.append(
                            f"Consider using '{recommended}' instead of '{subagent_type}' "
                            f"(confidence: {routing.confidence:.2f})"
                        )
            else:
                # General tool - classify intent and score importance
                if self.tpu_available:
                    # Build context for scoring
                    context = f"{tool_name}: "
                    if "command" in tool_input:
                        context += tool_input["command"][:100]
                    elif "file_path" in tool_input:
                        context += f"file: {tool_input['file_path']}"
                    elif "pattern" in tool_input:
                        context += f"search: {tool_input['pattern']}"

                    importance = score_importance(context)
                    intent = classify_intent(context)

                    result.tpu_used = True
                    result.data["importance"] = importance
                    result.data["intent"] = intent

        except Exception as e:
            result.errors.append(str(e))
            logger.warning(f"PreToolUse TPU processing failed: {e}")

        result.latency_ms = (time.perf_counter() - start_time) * 1000
        return result

    async def post_tool_use(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: str,
        success_score: float,
        session_id: Optional[str] = None
    ) -> HookResult:
        """
        Process PostToolUse hook with TPU intelligence.

        - Predict outcome for similar future actions
        - Detect causal relationships
        - Score outcome for self-improvement
        """
        start_time = time.perf_counter()
        result = HookResult(
            success=True,
            hook_type="post_tool_use",
            tpu_used=False,
            latency_ms=0.0
        )

        try:
            action_matcher = get_action_matcher()
            causal_recognizer = get_causal_recognizer()

            # Build action context
            action_description = f"{tool_name}"
            if "command" in tool_input:
                action_description += f": {tool_input['command'][:100]}"
            elif "file_path" in tool_input:
                action_description += f": {tool_input['file_path']}"

            # Predict outcome for similar future actions
            if action_matcher:
                try:
                    prediction = await action_matcher.predict_outcome(
                        action_type=tool_name,
                        action_description=action_description,
                        context=tool_output[:200],
                        expected_result="success" if success_score >= 0.5 else "failure"
                    )

                    if prediction:
                        result.tpu_used = action_matcher.use_tpu
                        result.data["outcome_prediction"] = {
                            "success_probability": prediction.success_probability,
                            "confidence": prediction.confidence,
                            "recommended_strategy": prediction.recommended_strategy,
                            "risk_factors": prediction.risk_factors[:3] if prediction.risk_factors else []
                        }

                        # Compare prediction to actual
                        actual_success = success_score >= 0.5
                        if prediction.success_probability >= 0.5 and not actual_success:
                            result.recommendations.append(
                                f"Unexpected failure - predicted {prediction.success_probability:.0%} success"
                            )
                        elif prediction.success_probability < 0.5 and actual_success:
                            result.recommendations.append(
                                f"Better than expected - predicted only {prediction.success_probability:.0%} success"
                            )
                except Exception as e:
                    logger.warning(f"Action prediction failed: {e}")

            # Analyze causal patterns
            if causal_recognizer and self.tpu_available:
                try:
                    # Use base TPU importance scoring for causal analysis
                    importance = score_importance(f"{tool_name} {action_description} {tool_output[:100]}")
                    result.data["causal_analysis"] = {
                        "action_importance": importance,
                        "success": success_score >= 0.5,
                        "context": action_description[:100]
                    }
                    result.tpu_used = True
                except Exception as e:
                    logger.warning(f"Causal analysis failed: {e}")

        except Exception as e:
            result.errors.append(str(e))
            logger.warning(f"PostToolUse TPU processing failed: {e}")

        result.latency_ms = (time.perf_counter() - start_time) * 1000
        return result

    async def session_start(
        self,
        session_id: str,
        node_id: str = "macpro51",
        context: Optional[Dict[str, Any]] = None
    ) -> HookResult:
        """
        Process SessionStart hook with TPU intelligence.

        - Classify session context
        - Load relevant memories based on context
        - Set initial metacognitive state
        """
        start_time = time.perf_counter()
        result = HookResult(
            success=True,
            hook_type="session_start",
            tpu_used=False,
            latency_ms=0.0
        )

        try:
            session_classifier = get_session_classifier()
            metacognitive = get_metacognitive_classifier()

            # Classify session context if available
            if session_classifier:
                try:
                    # Session classifier expects list of messages
                    messages = [f"Session started on {node_id}", f"Session ID: {session_id}"]
                    if context:
                        messages.append(json.dumps(context)[:300])

                    session_type = await session_classifier.classify_session(
                        messages=messages
                    )

                    if session_type:
                        result.tpu_used = session_classifier.use_tpu
                        result.data["session_classification"] = {
                            "type": session_type.primary_type.value if hasattr(session_type.primary_type, 'value') else str(session_type.primary_type),
                            "confidence": session_type.confidence,
                            "complexity": session_type.complexity.value if hasattr(session_type.complexity, 'value') else str(session_type.complexity),
                            "dominant_topic": session_type.dominant_topic
                        }
                except Exception as e:
                    logger.warning(f"Session classification failed: {e}")

            # Initialize metacognitive state
            if metacognitive:
                try:
                    initial_state = await metacognitive.classify_state(
                        context=f"Session started on {node_id}",
                        task_progress=0.0
                    )

                    if initial_state:
                        result.data["metacognitive_state"] = {
                            "state": initial_state.state.value if hasattr(initial_state.state, 'value') else str(initial_state.state),
                            "confidence": initial_state.confidence,
                            "cognitive_load": initial_state.cognitive_load,
                            "attention_level": initial_state.attention_level
                        }
                        result.tpu_used = True
                except Exception as e:
                    logger.warning(f"Metacognitive init failed: {e}")

        except Exception as e:
            result.errors.append(str(e))
            logger.warning(f"SessionStart TPU processing failed: {e}")

        result.latency_ms = (time.perf_counter() - start_time) * 1000
        return result

    async def user_prompt_submit(
        self,
        prompt: str,
        session_id: Optional[str] = None
    ) -> HookResult:
        """
        Process UserPromptSubmit hook with TPU intelligence.

        - Classify user intent with TPU embeddings
        - Update metacognitive state
        - Score knowledge gaps in prompt
        """
        start_time = time.perf_counter()
        result = HookResult(
            success=True,
            hook_type="user_prompt_submit",
            tpu_used=False,
            latency_ms=0.0
        )

        try:
            metacognitive = get_metacognitive_classifier()
            knowledge_scorer = get_knowledge_scorer()

            # Classify intent with TPU
            if self.tpu_available:
                try:
                    intent = classify_intent(prompt[:500])
                    importance = score_importance(prompt[:500])

                    result.tpu_used = True
                    result.data["intent_classification"] = {
                        "intent": intent,
                        "importance": importance
                    }
                except Exception as e:
                    logger.warning(f"Intent classification failed: {e}")

            # Update metacognitive state based on prompt
            if metacognitive:
                try:
                    cognitive_state = await metacognitive.classify_state(
                        context=prompt[:500],
                        task_progress=0.1  # Just starting
                    )

                    if cognitive_state:
                        result.data["prompt_complexity"] = {
                            "cognitive_load": cognitive_state.cognitive_load,
                            "state": cognitive_state.state.value if hasattr(cognitive_state.state, 'value') else str(cognitive_state.state),
                            "attention_level": cognitive_state.attention_level,
                            "confidence": cognitive_state.confidence
                        }
                        result.tpu_used = True
                except Exception as e:
                    logger.warning(f"Metacognitive analysis failed: {e}")

            # Score knowledge gaps using base TPU
            if knowledge_scorer:
                try:
                    # Knowledge scorer uses prioritize_gaps with list of gaps
                    # For now, use base TPU to detect uncertainty keywords
                    uncertainty_keywords = ["how", "what", "why", "explain", "understand", "help", "confused"]
                    prompt_lower = prompt.lower()
                    uncertainty_count = sum(1 for kw in uncertainty_keywords if kw in prompt_lower)
                    uncertainty_score = min(uncertainty_count / 3.0, 1.0)

                    if uncertainty_score > 0.3:
                        result.data["knowledge_gaps"] = {
                            "detected": True,
                            "uncertainty_score": uncertainty_score,
                            "keywords_found": [kw for kw in uncertainty_keywords if kw in prompt_lower]
                        }

                        if uncertainty_score > 0.7:
                            result.recommendations.append(
                                f"High uncertainty detected - consider research before proceeding"
                            )
                except Exception as e:
                    logger.warning(f"Knowledge gap detection failed: {e}")

        except Exception as e:
            result.errors.append(str(e))
            logger.warning(f"UserPromptSubmit TPU processing failed: {e}")

        result.latency_ms = (time.perf_counter() - start_time) * 1000
        return result

    def get_status(self) -> Dict[str, Any]:
        """Get TPU integration status."""
        return {
            "tpu_available": self.tpu_available,
            "modules_loaded": list(_modules.keys()),
            "cache_size": len(self._cache)
        }


# CLI interface for shell hooks
async def main():
    parser = argparse.ArgumentParser(description="TPU Hook Integration")
    parser.add_argument("--hook", required=True,
                       choices=["pre_tool_use", "post_tool_use", "session_start", "user_prompt_submit", "status"])
    parser.add_argument("--tool_name", help="Tool name for pre/post tool use")
    parser.add_argument("--tool_input", help="JSON tool input")
    parser.add_argument("--tool_output", help="Tool output for post tool use")
    parser.add_argument("--success_score", type=float, default=0.8, help="Success score for post tool use")
    parser.add_argument("--prompt", help="User prompt for prompt submit")
    parser.add_argument("--session_id", help="Session ID")
    parser.add_argument("--node_id", default="macpro51", help="Node ID")
    parser.add_argument("--quiet", action="store_true", help="Only output JSON result")

    args = parser.parse_args()

    integration = TPUHookIntegration()

    if args.hook == "status":
        print(json.dumps(integration.get_status(), indent=2))
        return

    # Parse tool input if provided
    tool_input = {}
    if args.tool_input:
        try:
            tool_input = json.loads(args.tool_input)
        except json.JSONDecodeError:
            tool_input = {"raw": args.tool_input}

    # Execute appropriate hook
    if args.hook == "pre_tool_use":
        result = await integration.pre_tool_use(
            tool_name=args.tool_name or "unknown",
            tool_input=tool_input,
            session_id=args.session_id
        )
    elif args.hook == "post_tool_use":
        result = await integration.post_tool_use(
            tool_name=args.tool_name or "unknown",
            tool_input=tool_input,
            tool_output=args.tool_output or "",
            success_score=args.success_score,
            session_id=args.session_id
        )
    elif args.hook == "session_start":
        result = await integration.session_start(
            session_id=args.session_id or "unknown",
            node_id=args.node_id,
            context=tool_input
        )
    elif args.hook == "user_prompt_submit":
        result = await integration.user_prompt_submit(
            prompt=args.prompt or "",
            session_id=args.session_id
        )
    else:
        print(json.dumps({"error": f"Unknown hook: {args.hook}"}))
        return

    # Output result
    output = {
        "success": result.success,
        "hook_type": result.hook_type,
        "tpu_used": result.tpu_used,
        "latency_ms": round(result.latency_ms, 2),
        "data": result.data,
        "recommendations": result.recommendations,
        "errors": result.errors
    }

    if not args.quiet and result.recommendations:
        for rec in result.recommendations:
            print(f"[TPU] {rec}", file=sys.stderr)

    print(json.dumps(output))


if __name__ == "__main__":
    asyncio.run(main())

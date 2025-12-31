#!/usr/bin/env python3
"""
Visual Reasoning Agent - AGI Decision-Making with Visual Context

Provides visual-aware reasoning capabilities:
- Uses visual context to inform decisions
- Correlates visual observations with actions
- Tracks visual-action outcomes for learning
- Integrates with cross-modal memory for full context

This completes the perception-memory-reasoning-action loop for Visual AGI.

STATUS: Production Ready
"""

import asyncio
import hashlib
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-agents')
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/shared')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReasoningMode(Enum):
    """Modes of visual reasoning."""
    REACTIVE = "reactive"           # React to visual changes
    PROACTIVE = "proactive"         # Anticipate based on visual patterns
    REFLECTIVE = "reflective"       # Learn from visual-action outcomes
    COLLABORATIVE = "collaborative" # Multi-agent visual reasoning


class ActionType(Enum):
    """Types of actions the agent can take."""
    OBSERVE = "observe"             # Just observe and record
    ALERT = "alert"                 # Notify about something
    SUGGEST = "suggest"             # Suggest an action
    EXECUTE = "execute"             # Execute an action
    DELEGATE = "delegate"           # Delegate to another agent


@dataclass
class VisualContext:
    """Visual context for reasoning."""
    current_observation: Dict[str, Any]
    recent_observations: List[Dict[str, Any]]
    detected_changes: List[Dict[str, Any]]
    patterns: List[Dict[str, Any]]
    cross_modal_context: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ReasoningResult:
    """Result of visual reasoning."""
    action_type: ActionType
    decision: str
    confidence: float
    visual_evidence: List[str]
    reasoning_chain: List[str]
    suggested_actions: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionOutcome:
    """Outcome of an action for learning."""
    action_id: str
    action_type: ActionType
    visual_context_before: Dict[str, Any]
    visual_context_after: Optional[Dict[str, Any]]
    success: bool
    outcome_description: str
    learned_patterns: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class VisualReasoningAgent:
    """
    Visual Reasoning Agent for AGI decision-making.

    Uses visual context to:
    - Make informed decisions
    - Predict outcomes based on visual patterns
    - Learn from visual-action correlations
    - Coordinate with other agents using visual information
    """

    def __init__(
        self,
        storage_path: str = "/Volumes/SSDRAID0/agentic-system/databases/visual_reasoning"
    ):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

        # Reasoning history
        self._reasoning_history: List[ReasoningResult] = []
        self._action_outcomes: List[ActionOutcome] = []

        # Pattern library (learned visual-action patterns)
        self._pattern_library = self._load_pattern_library()

        # Decision rules
        self._decision_rules = self._init_decision_rules()

        logger.info(f"VisualReasoningAgent initialized at {storage_path}")

    def _load_pattern_library(self) -> Dict[str, Any]:
        """Load learned visual-action patterns."""
        pattern_path = os.path.join(self.storage_path, "pattern_library.json")

        if os.path.exists(pattern_path):
            try:
                with open(pattern_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass

        return {
            "visual_action_patterns": [],
            "success_patterns": [],
            "failure_patterns": [],
            "last_updated": datetime.now().isoformat()
        }

    def _save_pattern_library(self) -> None:
        """Save pattern library."""
        pattern_path = os.path.join(self.storage_path, "pattern_library.json")
        self._pattern_library["last_updated"] = datetime.now().isoformat()

        with open(pattern_path, 'w') as f:
            json.dump(self._pattern_library, f, indent=2, default=str)

    def _init_decision_rules(self) -> List[Dict[str, Any]]:
        """Initialize decision rules for visual reasoning."""
        return [
            {
                "name": "error_detection",
                "trigger": lambda ctx: self._detect_error_indicators(ctx),
                "action_type": ActionType.ALERT,
                "priority": 1,
                "description": "Alert on visual error indicators"
            },
            {
                "name": "significant_change",
                "trigger": lambda ctx: len(ctx.detected_changes) > 3,
                "action_type": ActionType.OBSERVE,
                "priority": 2,
                "description": "Record significant visual changes"
            },
            {
                "name": "pattern_match",
                "trigger": lambda ctx: self._match_known_patterns(ctx),
                "action_type": ActionType.SUGGEST,
                "priority": 3,
                "description": "Suggest action based on known patterns"
            },
            {
                "name": "workflow_context",
                "trigger": lambda ctx: self._detect_workflow_context(ctx),
                "action_type": ActionType.DELEGATE,
                "priority": 4,
                "description": "Delegate based on detected workflow"
            }
        ]

    def _detect_error_indicators(self, ctx: VisualContext) -> bool:
        """Detect visual error indicators."""
        obs = ctx.current_observation

        # Check for error-related content
        description = str(obs.get("consensus", {}).get("description", "")).lower()
        error_keywords = ["error", "exception", "failed", "crash", "warning", "alert"]

        return any(kw in description for kw in error_keywords)

    def _match_known_patterns(self, ctx: VisualContext) -> bool:
        """Check if current context matches known patterns."""
        patterns = self._pattern_library.get("success_patterns", [])

        if not patterns:
            return False

        # Simple pattern matching based on scene type
        current_scene = ctx.current_observation.get("consensus", {}).get("scene_type", "")

        for pattern in patterns:
            if pattern.get("scene_type") == current_scene:
                return True

        return False

    def _detect_workflow_context(self, ctx: VisualContext) -> bool:
        """Detect if visual context indicates a specific workflow."""
        cross_modal = ctx.cross_modal_context or {}

        # Check if there's recent code activity
        code_count = cross_modal.get("modality_counts", {}).get("code", 0)

        return code_count > 5

    async def get_visual_context(self, hours: int = 1) -> VisualContext:
        """Gather current visual context for reasoning."""
        from cross_modal_integration import CrossModalMemoryManager

        # Get current visual state
        current_observation = {}
        recent_observations = []
        detected_changes = []
        patterns = []

        try:
            from visual_memory_integration import VisualMemoryManager
            vis_manager = VisualMemoryManager()

            # Get recent visual memories
            memories = vis_manager.memory_store.get_recent(hours=hours, limit=20)

            if memories:
                # Most recent is current
                current = memories[0]
                current_observation = {
                    "id": current.id,
                    "scene_type": current.scene_type,
                    "description": current.description,
                    "objects": current.objects,
                    "confidence": current.confidence,
                    "timestamp": current.timestamp
                }

                # Rest are recent
                for mem in memories[1:10]:
                    recent_observations.append({
                        "id": mem.id,
                        "scene_type": mem.scene_type,
                        "timestamp": mem.timestamp
                    })

                # Detect changes between observations
                if len(memories) >= 2:
                    curr_objects = set(memories[0].objects)
                    prev_objects = set(memories[1].objects)

                    new_objects = curr_objects - prev_objects
                    removed_objects = prev_objects - curr_objects

                    if new_objects:
                        detected_changes.append({
                            "type": "objects_appeared",
                            "objects": list(new_objects)
                        })
                    if removed_objects:
                        detected_changes.append({
                            "type": "objects_disappeared",
                            "objects": list(removed_objects)
                        })

                    if memories[0].scene_type != memories[1].scene_type:
                        detected_changes.append({
                            "type": "scene_change",
                            "from": memories[1].scene_type,
                            "to": memories[0].scene_type
                        })

                # Get patterns from knowledge graph
                patterns = vis_manager.knowledge_graph.get_related_concepts(
                    current.scene_type
                )

        except ImportError:
            logger.warning("Visual memory not available")

        # Get cross-modal context
        cross_modal_context = None
        try:
            cm_manager = CrossModalMemoryManager()
            cross_modal_context = cm_manager.get_unified_summary(hours=hours)
        except Exception as e:
            logger.warning(f"Cross-modal context unavailable: {e}")

        return VisualContext(
            current_observation=current_observation,
            recent_observations=recent_observations,
            detected_changes=detected_changes,
            patterns=patterns,
            cross_modal_context=cross_modal_context
        )

    async def reason(
        self,
        context: Optional[VisualContext] = None,
        mode: ReasoningMode = ReasoningMode.REACTIVE,
        query: str = ""
    ) -> ReasoningResult:
        """
        Perform visual reasoning.

        Args:
            context: Visual context (will gather if not provided)
            mode: Reasoning mode
            query: Optional query to guide reasoning

        Returns:
            ReasoningResult with decision and suggested actions
        """
        # Get context if not provided
        if context is None:
            context = await self.get_visual_context()

        reasoning_chain = []
        visual_evidence = []
        suggested_actions = []

        # Step 1: Analyze visual context
        reasoning_chain.append(f"Analyzing visual context: {context.current_observation.get('scene_type', 'unknown')}")

        if context.current_observation:
            visual_evidence.append(
                f"Current scene: {context.current_observation.get('description', 'No description')[:100]}"
            )

        # Step 2: Check detected changes
        if context.detected_changes:
            reasoning_chain.append(f"Detected {len(context.detected_changes)} visual changes")
            for change in context.detected_changes:
                visual_evidence.append(f"Change: {change.get('type')} - {change.get('objects', change.get('to', ''))}")

        # Step 3: Apply decision rules
        triggered_rules = []
        for rule in self._decision_rules:
            try:
                if rule["trigger"](context):
                    triggered_rules.append(rule)
                    reasoning_chain.append(f"Rule triggered: {rule['name']}")
            except Exception as e:
                logger.warning(f"Rule {rule['name']} failed: {e}")

        # Step 4: Determine action based on mode and rules
        if mode == ReasoningMode.REACTIVE:
            action_type, decision, confidence = self._reactive_reasoning(
                context, triggered_rules, query
            )
        elif mode == ReasoningMode.PROACTIVE:
            action_type, decision, confidence = self._proactive_reasoning(
                context, triggered_rules, query
            )
        elif mode == ReasoningMode.REFLECTIVE:
            action_type, decision, confidence = self._reflective_reasoning(
                context, triggered_rules, query
            )
        else:
            action_type, decision, confidence = self._collaborative_reasoning(
                context, triggered_rules, query
            )

        reasoning_chain.append(f"Decision: {decision} (confidence: {confidence:.2f})")

        # Step 5: Generate suggested actions
        if action_type == ActionType.ALERT:
            suggested_actions.append({
                "action": "send_alert",
                "message": decision,
                "urgency": "high" if confidence > 0.8 else "medium"
            })
        elif action_type == ActionType.SUGGEST:
            suggested_actions.append({
                "action": "present_suggestion",
                "suggestion": decision,
                "based_on": visual_evidence[:3]
            })
        elif action_type == ActionType.EXECUTE:
            suggested_actions.append({
                "action": "execute_command",
                "command": decision,
                "requires_confirmation": confidence < 0.9
            })
        elif action_type == ActionType.DELEGATE:
            suggested_actions.append({
                "action": "delegate_to_agent",
                "target_agent": self._determine_target_agent(context),
                "context": decision
            })

        result = ReasoningResult(
            action_type=action_type,
            decision=decision,
            confidence=confidence,
            visual_evidence=visual_evidence,
            reasoning_chain=reasoning_chain,
            suggested_actions=suggested_actions,
            metadata={
                "mode": mode.value,
                "query": query,
                "triggered_rules": [r["name"] for r in triggered_rules]
            }
        )

        # Store reasoning result
        self._reasoning_history.append(result)
        self._store_reasoning_result(result)

        return result

    def _reactive_reasoning(
        self,
        context: VisualContext,
        triggered_rules: List[Dict],
        query: str
    ) -> Tuple[ActionType, str, float]:
        """Reactive reasoning - respond to current visual state."""

        # Check for errors first
        if any(r["name"] == "error_detection" for r in triggered_rules):
            return (
                ActionType.ALERT,
                "Visual error indicator detected - may need attention",
                0.85
            )

        # Check for significant changes
        if context.detected_changes:
            changes_summary = ", ".join(
                c.get("type", "change") for c in context.detected_changes[:3]
            )
            return (
                ActionType.OBSERVE,
                f"Significant visual changes detected: {changes_summary}",
                0.7
            )

        # Default observation
        scene = context.current_observation.get("scene_type", "unknown")
        return (
            ActionType.OBSERVE,
            f"Observing current state: {scene}",
            0.5
        )

    def _proactive_reasoning(
        self,
        context: VisualContext,
        triggered_rules: List[Dict],
        query: str
    ) -> Tuple[ActionType, str, float]:
        """Proactive reasoning - anticipate based on patterns."""

        # Check for known patterns
        if any(r["name"] == "pattern_match" for r in triggered_rules):
            matched_pattern = self._get_matched_pattern(context)
            if matched_pattern:
                return (
                    ActionType.SUGGEST,
                    f"Based on visual pattern '{matched_pattern.get('name', 'unknown')}', suggest: {matched_pattern.get('suggested_action', 'continue observation')}",
                    0.75
                )

        # Predict based on recent trajectory
        if len(context.recent_observations) >= 3:
            scene_types = [o.get("scene_type") for o in context.recent_observations]
            if len(set(scene_types)) == 1:
                return (
                    ActionType.SUGGEST,
                    f"Stable visual state ({scene_types[0]}) - good time for focused work",
                    0.7
                )

        return (
            ActionType.OBSERVE,
            "Monitoring for predictable patterns",
            0.5
        )

    def _reflective_reasoning(
        self,
        context: VisualContext,
        triggered_rules: List[Dict],
        query: str
    ) -> Tuple[ActionType, str, float]:
        """Reflective reasoning - learn from outcomes."""

        # Analyze recent action outcomes
        recent_outcomes = self._action_outcomes[-10:]

        if recent_outcomes:
            success_rate = sum(1 for o in recent_outcomes if o.success) / len(recent_outcomes)

            if success_rate < 0.5:
                return (
                    ActionType.SUGGEST,
                    f"Recent action success rate low ({success_rate:.0%}) - recommend reviewing approach",
                    0.8
                )
            elif success_rate > 0.8:
                return (
                    ActionType.SUGGEST,
                    f"High success rate ({success_rate:.0%}) - current approach working well",
                    0.7
                )

        return (
            ActionType.OBSERVE,
            "Gathering data for reflection",
            0.5
        )

    def _collaborative_reasoning(
        self,
        context: VisualContext,
        triggered_rules: List[Dict],
        query: str
    ) -> Tuple[ActionType, str, float]:
        """Collaborative reasoning - coordinate with other agents."""

        # Check for workflow context
        if any(r["name"] == "workflow_context" for r in triggered_rules):
            return (
                ActionType.DELEGATE,
                "Visual context suggests code-related workflow - delegating to code agent",
                0.7
            )

        # Check cross-modal context for collaboration needs
        cross_modal = context.cross_modal_context or {}
        total_activity = sum(cross_modal.get("modality_counts", {}).values())

        if total_activity > 20:
            return (
                ActionType.DELEGATE,
                "High cross-modal activity - coordinating with other agents",
                0.65
            )

        return (
            ActionType.OBSERVE,
            "Monitoring for collaboration opportunities",
            0.5
        )

    def _get_matched_pattern(self, context: VisualContext) -> Optional[Dict]:
        """Get the matched pattern from library."""
        patterns = self._pattern_library.get("success_patterns", [])
        current_scene = context.current_observation.get("scene_type", "")

        for pattern in patterns:
            if pattern.get("scene_type") == current_scene:
                return pattern

        return None

    def _determine_target_agent(self, context: VisualContext) -> str:
        """Determine which agent to delegate to."""
        cross_modal = context.cross_modal_context or {}
        counts = cross_modal.get("modality_counts", {})

        if counts.get("code", 0) > counts.get("text", 0):
            return "code_agent"
        elif counts.get("text", 0) > 0:
            return "text_agent"

        return "general_agent"

    async def record_action_outcome(
        self,
        action_id: str,
        action_type: ActionType,
        success: bool,
        outcome_description: str
    ) -> None:
        """Record the outcome of an action for learning."""

        # Get visual context before and after
        context_after = await self.get_visual_context(hours=0.1)  # Last 6 minutes

        # Find the reasoning result for this action
        context_before = {}
        for result in reversed(self._reasoning_history):
            if result.metadata.get("action_id") == action_id:
                context_before = result.metadata.get("visual_context", {})
                break

        outcome = ActionOutcome(
            action_id=action_id,
            action_type=action_type,
            visual_context_before=context_before,
            visual_context_after=context_after.current_observation,
            success=success,
            outcome_description=outcome_description,
            learned_patterns=self._extract_patterns(
                context_before, context_after.current_observation, success
            )
        )

        self._action_outcomes.append(outcome)

        # Update pattern library
        if outcome.learned_patterns:
            if success:
                self._pattern_library["success_patterns"].extend(outcome.learned_patterns)
            else:
                self._pattern_library["failure_patterns"].extend(outcome.learned_patterns)

            self._save_pattern_library()

        # Store outcome
        self._store_action_outcome(outcome)

    def _extract_patterns(
        self,
        before: Dict,
        after: Dict,
        success: bool
    ) -> List[Dict]:
        """Extract patterns from before/after visual context."""
        patterns = []

        if before and after:
            # Scene transition pattern
            scene_before = before.get("scene_type", "")
            scene_after = after.get("scene_type", "")

            if scene_before and scene_after:
                patterns.append({
                    "type": "scene_transition",
                    "from": scene_before,
                    "to": scene_after,
                    "success": success,
                    "timestamp": datetime.now().isoformat()
                })

        return patterns

    def _store_reasoning_result(self, result: ReasoningResult) -> None:
        """Store reasoning result to disk."""
        results_path = os.path.join(self.storage_path, "reasoning_results.jsonl")

        record = {
            "action_type": result.action_type.value,
            "decision": result.decision,
            "confidence": result.confidence,
            "visual_evidence": result.visual_evidence,
            "reasoning_chain": result.reasoning_chain,
            "suggested_actions": result.suggested_actions,
            "metadata": result.metadata,
            "timestamp": datetime.now().isoformat()
        }

        with open(results_path, 'a') as f:
            f.write(json.dumps(record) + '\n')

    def _store_action_outcome(self, outcome: ActionOutcome) -> None:
        """Store action outcome to disk."""
        outcomes_path = os.path.join(self.storage_path, "action_outcomes.jsonl")

        record = {
            "action_id": outcome.action_id,
            "action_type": outcome.action_type.value,
            "success": outcome.success,
            "outcome_description": outcome.outcome_description,
            "learned_patterns": outcome.learned_patterns,
            "timestamp": outcome.timestamp
        }

        with open(outcomes_path, 'a') as f:
            f.write(json.dumps(record) + '\n')

    def get_reasoning_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of recent reasoning activity."""
        cutoff = datetime.now() - timedelta(hours=hours)

        recent_results = [
            r for r in self._reasoning_history
            if datetime.fromisoformat(r.metadata.get("timestamp", datetime.now().isoformat())) > cutoff
        ]

        recent_outcomes = [
            o for o in self._action_outcomes
            if datetime.fromisoformat(o.timestamp) > cutoff
        ]

        action_type_counts = {}
        for r in recent_results:
            at = r.action_type.value
            action_type_counts[at] = action_type_counts.get(at, 0) + 1

        success_rate = 0
        if recent_outcomes:
            success_rate = sum(1 for o in recent_outcomes if o.success) / len(recent_outcomes)

        return {
            "hours": hours,
            "total_reasoning_events": len(recent_results),
            "action_type_distribution": action_type_counts,
            "total_action_outcomes": len(recent_outcomes),
            "success_rate": success_rate,
            "pattern_library_size": len(self._pattern_library.get("success_patterns", [])),
            "timestamp": datetime.now().isoformat()
        }


# MCP Tool Functions
async def visual_reason(
    mode: str = "reactive",
    query: str = ""
) -> Dict:
    """MCP Tool: Perform visual reasoning."""
    agent = VisualReasoningAgent()

    mode_map = {
        "reactive": ReasoningMode.REACTIVE,
        "proactive": ReasoningMode.PROACTIVE,
        "reflective": ReasoningMode.REFLECTIVE,
        "collaborative": ReasoningMode.COLLABORATIVE
    }

    reasoning_mode = mode_map.get(mode, ReasoningMode.REACTIVE)
    result = await agent.reason(mode=reasoning_mode, query=query)

    return {
        "action_type": result.action_type.value,
        "decision": result.decision,
        "confidence": result.confidence,
        "visual_evidence": result.visual_evidence,
        "reasoning_chain": result.reasoning_chain,
        "suggested_actions": result.suggested_actions
    }


async def get_visual_reasoning_summary(hours: int = 24) -> Dict:
    """MCP Tool: Get visual reasoning summary."""
    agent = VisualReasoningAgent()
    return agent.get_reasoning_summary(hours)


# CLI Entry Point
async def main():
    """Demo visual reasoning agent."""
    import argparse

    parser = argparse.ArgumentParser(description="Visual Reasoning Agent")
    parser.add_argument("--reason", action="store_true", help="Perform reasoning")
    parser.add_argument("--mode", default="reactive",
                        choices=["reactive", "proactive", "reflective", "collaborative"],
                        help="Reasoning mode")
    parser.add_argument("--query", type=str, default="", help="Query to guide reasoning")
    parser.add_argument("--summary", action="store_true", help="Show reasoning summary")

    args = parser.parse_args()

    agent = VisualReasoningAgent()

    if args.reason:
        mode_map = {
            "reactive": ReasoningMode.REACTIVE,
            "proactive": ReasoningMode.PROACTIVE,
            "reflective": ReasoningMode.REFLECTIVE,
            "collaborative": ReasoningMode.COLLABORATIVE
        }

        print(f"Performing {args.mode} visual reasoning...")
        result = await agent.reason(mode=mode_map[args.mode], query=args.query)

        print(f"\nAction Type: {result.action_type.value}")
        print(f"Decision: {result.decision}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"\nReasoning Chain:")
        for step in result.reasoning_chain:
            print(f"  - {step}")
        print(f"\nSuggested Actions:")
        for action in result.suggested_actions:
            print(f"  - {json.dumps(action)}")

    elif args.summary:
        summary = agent.get_reasoning_summary()
        print(json.dumps(summary, indent=2))

    else:
        print("Use --reason to perform reasoning or --summary to view summary")


if __name__ == "__main__":
    asyncio.run(main())

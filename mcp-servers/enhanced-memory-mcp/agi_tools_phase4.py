"""
AGI Memory Phase 4 MCP Tools

Exposes Phase 4 capabilities via Model Context Protocol:
- Meta-cognitive awareness
- Knowledge gap tracking
- Self-improvement cycles
- Reasoning strategy management
- Performance tracking
- Multi-agent coordination
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from agi.metacognition import MetaCognition, PerformanceTracker
from agi.self_improvement import SelfImprovement, CoordinationManager

logger = logging.getLogger("agi_tools_phase4")


def register_agi_phase4_tools(app, db_path: Path):
    """Register Phase 4 AGI tools with FastMCP server"""

    # Initialize managers
    metacog = MetaCognition()
    performance = PerformanceTracker()
    improvement = SelfImprovement()
    coordination = CoordinationManager()

    # ========================================================================
    # META-COGNITIVE AWARENESS TOOLS
    # ========================================================================

    @app.tool()
    def record_metacognitive_state(
        agent_id: str,
        session_id: Optional[str] = None,
        self_awareness: float = 0.5,
        knowledge_awareness: float = 0.5,
        process_awareness: float = 0.5,
        limitation_awareness: float = 0.5,
        cognitive_load: float = 0.5,
        confidence_level: float = 0.5,
        task_context: Optional[Dict[str, Any]] = None,
        reasoning_trace: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Record current meta-cognitive awareness state

        Track how aware the agent is of:
        - Its own existence and state (self-awareness)
        - What it knows and doesn't know (knowledge-awareness)
        - How it thinks and reasons (process-awareness)
        - Its limitations and boundaries (limitation-awareness)

        Also tracks cognitive load, confidence, and reasoning trace.

        Returns:
            state_id and recorded values
        """
        state_id = metacog.record_metacognitive_state(
            agent_id=agent_id,
            session_id=session_id,
            self_awareness=self_awareness,
            knowledge_awareness=knowledge_awareness,
            process_awareness=process_awareness,
            limitation_awareness=limitation_awareness,
            cognitive_load=cognitive_load,
            confidence_level=confidence_level,
            task_context=task_context,
            reasoning_trace=reasoning_trace
        )

        return {
            "state_id": state_id,
            "agent_id": agent_id,
            "self_awareness": self_awareness,
            "knowledge_awareness": knowledge_awareness,
            "process_awareness": process_awareness,
            "limitation_awareness": limitation_awareness,
            "cognitive_load": cognitive_load,
            "confidence_level": confidence_level
        }

    @app.tool()
    def get_current_metacognitive_state(
        agent_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get current meta-cognitive state for agent

        Returns latest awareness levels and cognitive state.
        """
        return metacog.get_current_state(agent_id)

    # ========================================================================
    # KNOWLEDGE GAP TOOLS
    # ========================================================================

    @app.tool()
    def identify_knowledge_gap(
        agent_id: str,
        domain: str,
        gap_description: str,
        gap_type: str = "factual",
        severity: float = 0.5,
        discovered_by: str = "self-reflection",
        discovery_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Identify and record a knowledge gap for targeted learning

        Gap types:
        - factual: Missing factual knowledge
        - procedural: Don't know how to do something
        - conceptual: Lack conceptual understanding
        - meta: Don't know what you don't know

        Severity: 0.0 (minor) to 1.0 (critical)

        Returns:
            gap_id and details
        """
        gap_id = metacog.identify_knowledge_gap(
            agent_id=agent_id,
            domain=domain,
            gap_description=gap_description,
            gap_type=gap_type,
            severity=severity,
            discovered_by=discovered_by,
            discovery_context=discovery_context
        )

        return {
            "gap_id": gap_id,
            "domain": domain,
            "gap_type": gap_type,
            "severity": severity,
            "status": "open"
        }

    @app.tool()
    def get_knowledge_gaps(
        agent_id: str,
        status: Optional[str] = None,
        min_severity: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Get knowledge gaps for targeted learning

        Filter by status: open, learning, resolved
        Filter by minimum severity (0.0-1.0)

        Returns list of gaps ordered by severity.
        """
        return metacog.get_knowledge_gaps(
            agent_id=agent_id,
            status=status,
            min_severity=min_severity
        )

    @app.tool()
    def update_gap_learning_progress(
        gap_id: int,
        learning_progress: float,
        learning_plan: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update knowledge gap learning progress

        Progress: 0.0 (not started) to 1.0 (fully learned)
        Auto-resolves gap when progress reaches 1.0

        Returns:
            Updated gap status
        """
        metacog.update_gap_progress(
            gap_id=gap_id,
            learning_progress=learning_progress,
            learning_plan=learning_plan
        )

        return {
            "gap_id": gap_id,
            "learning_progress": learning_progress,
            "status": "resolved" if learning_progress >= 1.0 else "learning"
        }

    # ========================================================================
    # REASONING STRATEGY TOOLS
    # ========================================================================

    @app.tool()
    def track_reasoning_strategy(
        agent_id: str,
        strategy_name: str,
        strategy_type: str,
        success: bool,
        confidence: float,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Track usage and effectiveness of reasoning strategy

        Strategy types:
        - deductive: General rules → specific cases
        - inductive: Specific examples → general patterns
        - abductive: Effects → likely causes
        - analogical: Reason by analogy

        Tracks success rate and confidence over time.

        Returns:
            Updated strategy statistics
        """
        metacog.track_reasoning_strategy(
            agent_id=agent_id,
            strategy_name=strategy_name,
            strategy_type=strategy_type,
            success=success,
            confidence=confidence,
            context=context
        )

        return {
            "strategy_name": strategy_name,
            "strategy_type": strategy_type,
            "success": success,
            "confidence": confidence
        }

    @app.tool()
    def get_effective_reasoning_strategies(
        agent_id: str,
        min_success_rate: float = 0.6,
        min_usage: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get most effective reasoning strategies

        Filters by minimum success rate and usage count.
        Returns strategies proven to work well.

        Returns:
            List of effective strategies with statistics
        """
        return metacog.get_effective_strategies(
            agent_id=agent_id,
            min_success_rate=min_success_rate,
            min_usage=min_usage
        )

    # ========================================================================
    # PERFORMANCE TRACKING TOOLS
    # ========================================================================

    @app.tool()
    def update_performance_metric(
        agent_id: str,
        metric_name: str,
        metric_category: str,
        current_value: float,
        target_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Update a performance metric with trend analysis

        Categories:
        - cognitive: reasoning_speed, reasoning_accuracy, creativity
        - knowledge: breadth, depth, retention
        - social: communication, collaboration, empathy
        - meta: self_awareness, adaptation_speed, learning_rate

        Automatically tracks trend (improving/declining/stable).

        Returns:
            Updated metric with trend
        """
        performance.update_metric(
            agent_id=agent_id,
            metric_name=metric_name,
            metric_category=metric_category,
            current_value=current_value,
            target_value=target_value
        )

        return {
            "metric_name": metric_name,
            "metric_category": metric_category,
            "current_value": current_value,
            "target_value": target_value
        }

    @app.tool()
    def get_performance_trends(
        agent_id: str,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get performance trends across metrics

        Filter by category or get all metrics.
        Includes trend analysis (improving/declining/stable).

        Returns:
            List of metrics with trends and progress
        """
        return performance.get_performance_trends(
            agent_id=agent_id,
            category=category
        )

    # ========================================================================
    # SELF-IMPROVEMENT CYCLE TOOLS
    # ========================================================================

    @app.tool()
    def start_improvement_cycle(
        agent_id: str,
        cycle_type: str,
        improvement_goals: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Start a new self-improvement cycle

        Cycle types:
        - performance: Improve execution performance
        - knowledge: Fill knowledge gaps
        - reasoning: Improve reasoning quality
        - meta: Improve meta-cognitive awareness

        Returns:
            cycle_id and cycle_number
        """
        cycle_id = improvement.start_improvement_cycle(
            agent_id=agent_id,
            cycle_type=cycle_type,
            improvement_goals=improvement_goals
        )

        return {
            "cycle_id": cycle_id,
            "agent_id": agent_id,
            "cycle_type": cycle_type,
            "status": "started"
        }

    @app.tool()
    def assess_baseline_performance(
        cycle_id: int,
        baseline_metrics: Dict[str, float],
        identified_weaknesses: List[str]
    ) -> Dict[str, Any]:
        """
        Assess baseline performance before improvement

        Establishes what needs to improve.

        Returns:
            Baseline assessment summary
        """
        improvement.assess_baseline_performance(
            cycle_id=cycle_id,
            baseline_metrics=baseline_metrics,
            identified_weaknesses=identified_weaknesses
        )

        baseline_performance = sum(baseline_metrics.values()) / len(baseline_metrics)

        return {
            "cycle_id": cycle_id,
            "baseline_performance": baseline_performance,
            "weaknesses_identified": len(identified_weaknesses)
        }

    @app.tool()
    def apply_improvement_strategies(
        cycle_id: int,
        strategies: List[Dict[str, Any]],
        changes: List[str]
    ) -> Dict[str, Any]:
        """
        Apply improvement strategies and record changes

        Documents what strategies were tried and what changed.

        Returns:
            Application summary
        """
        improvement.apply_improvement_strategies(
            cycle_id=cycle_id,
            strategies=strategies,
            changes=changes
        )

        return {
            "cycle_id": cycle_id,
            "strategies_applied": len(strategies),
            "changes_made": len(changes)
        }

    @app.tool()
    def validate_improvements(
        cycle_id: int,
        new_metrics: Dict[str, float],
        success_criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate that improvements met success criteria

        Compares new performance to baseline.
        Auto-marks cycle as successful if criteria met.

        Returns:
            Validation results with success status
        """
        success = improvement.validate_improvements(
            cycle_id=cycle_id,
            new_metrics=new_metrics,
            success_criteria=success_criteria
        )

        new_performance = sum(new_metrics.values()) / len(new_metrics)

        return {
            "cycle_id": cycle_id,
            "new_performance": new_performance,
            "success": success
        }

    @app.tool()
    def complete_improvement_cycle(
        cycle_id: int,
        lessons_learned: List[str],
        next_recommendations: List[str]
    ) -> Dict[str, Any]:
        """
        Complete improvement cycle and record learnings

        Captures insights and recommendations for future cycles.

        Returns:
            Completion summary
        """
        improvement.complete_cycle(
            cycle_id=cycle_id,
            lessons_learned=lessons_learned,
            next_recommendations=next_recommendations
        )

        return {
            "cycle_id": cycle_id,
            "status": "completed",
            "lessons_count": len(lessons_learned),
            "recommendations_count": len(next_recommendations)
        }

    @app.tool()
    def get_improvement_history(
        agent_id: str,
        cycle_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get improvement cycle history

        Shows past cycles with results.
        Filter by cycle type if desired.

        Returns:
            List of past improvement cycles
        """
        return improvement.get_improvement_history(
            agent_id=agent_id,
            cycle_type=cycle_type,
            limit=limit
        )

    @app.tool()
    def get_best_improvement_strategies(
        agent_id: str,
        min_success_rate: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Get improvement strategies that have worked well

        Analyzes past cycles to find successful patterns.

        Returns:
            List of effective strategies with success rates
        """
        return improvement.get_best_performing_strategies(
            agent_id=agent_id,
            min_success_rate=min_success_rate
        )

    # ========================================================================
    # MULTI-AGENT COORDINATION TOOLS
    # ========================================================================

    @app.tool()
    def send_coordination_message(
        sender_agent_id: str,
        recipient_agent_id: Optional[str],
        message_type: str,
        subject: str,
        message_content: Dict[str, Any],
        priority: float = 0.5,
        requires_response: bool = False
    ) -> Dict[str, Any]:
        """
        Send coordination message to another agent

        Message types:
        - request: Requesting assistance
        - response: Responding to request
        - notification: Informing of event
        - coordination: Coordinating shared task

        Priority: 0.0 (low) to 1.0 (urgent)
        Set recipient_agent_id=None for broadcast.

        Returns:
            message_id
        """
        message_id = coordination.send_message(
            sender_agent_id=sender_agent_id,
            recipient_agent_id=recipient_agent_id,
            message_type=message_type,
            subject=subject,
            message_content=message_content,
            priority=priority,
            requires_response=requires_response
        )

        return {
            "message_id": message_id,
            "sender": sender_agent_id,
            "recipient": recipient_agent_id or "ALL",
            "priority": priority
        }

    @app.tool()
    def receive_coordination_messages(
        agent_id: str,
        status: str = "pending"
    ) -> List[Dict[str, Any]]:
        """
        Receive pending coordination messages

        Auto-marks messages as 'delivered' when received.
        Filter by status: pending, delivered, acknowledged, completed

        Returns:
            List of messages for this agent
        """
        return coordination.receive_messages(
            agent_id=agent_id,
            status=status
        )

    @app.tool()
    def acknowledge_coordination_message(
        message_id: int,
        response_content: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Acknowledge receipt of coordination message

        Optionally provide response content.
        Auto-sends response message if content provided.

        Returns:
            Acknowledgment status
        """
        coordination.acknowledge_message(
            message_id=message_id,
            response_content=response_content
        )

        return {
            "message_id": message_id,
            "status": "acknowledged",
            "response_sent": response_content is not None
        }

    @app.tool()
    def get_pending_coordination_tasks(
        agent_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get pending coordination tasks requiring attention

        Filter by agent or get all pending tasks.
        Ordered by priority and age.

        Returns:
            List of pending coordination messages
        """
        return coordination.get_pending_coordination(agent_id=agent_id)

    logger.info("✅ AGI Phase 4 tools registered: Meta-Cognition & Self-Improvement")

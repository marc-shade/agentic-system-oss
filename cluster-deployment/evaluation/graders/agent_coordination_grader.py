#!/usr/bin/env python3
"""
Agent Coordination Grader
=========================

Evaluates multi-agent coordination quality:
- Task Distribution: Work divided appropriately
- Communication: Clear inter-agent messaging
- Conflict Resolution: Handles disagreements
- Resource Efficiency: No redundant work
- Goal Achievement: Collective objective met
"""

import re
import json
from typing import Dict, Any, Tuple, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AgentAction:
    """Record of an agent's action."""
    agent_id: str
    action_type: str
    timestamp: str
    details: Dict[str, Any]
    result: Optional[str] = None


@dataclass
class CoordinationEvent:
    """Inter-agent coordination event."""
    from_agent: str
    to_agent: str
    event_type: str  # message, handoff, request, response
    content: str
    timestamp: str


def parse_agent_log(log: str) -> Tuple[List[AgentAction], List[CoordinationEvent]]:
    """Parse agent coordination log into structured data."""
    actions = []
    events = []

    # Parse action lines: [AGENT:id] ACTION: type - details
    action_pattern = r'\[AGENT:(\w+)\]\s*ACTION:\s*(\w+)\s*-\s*(.+?)(?=\[AGENT:|$)'
    for match in re.finditer(action_pattern, log, re.DOTALL):
        actions.append(AgentAction(
            agent_id=match.group(1),
            action_type=match.group(2),
            timestamp=datetime.now().isoformat(),
            details={'raw': match.group(3).strip()}
        ))

    # Parse coordination events: [FROM->TO] TYPE: content
    event_pattern = r'\[(\w+)->(\w+)\]\s*(\w+):\s*(.+?)(?=\[|$)'
    for match in re.finditer(event_pattern, log, re.DOTALL):
        events.append(CoordinationEvent(
            from_agent=match.group(1),
            to_agent=match.group(2),
            event_type=match.group(3),
            content=match.group(4).strip(),
            timestamp=datetime.now().isoformat()
        ))

    return actions, events


def grade_task_distribution(
    actions: List[AgentAction],
    expected_agents: List[str] = None,
    task_count: int = None
) -> Tuple[float, str]:
    """Evaluate how well tasks were distributed among agents."""
    if not actions:
        return 0.0, "No actions recorded"

    # Count actions per agent
    agent_actions = {}
    for action in actions:
        agent_actions[action.agent_id] = agent_actions.get(action.agent_id, 0) + 1

    num_agents = len(agent_actions)
    if num_agents == 0:
        return 0.0, "No agents participated"

    if num_agents == 1:
        return 0.5, "Only one agent did all work"

    # Calculate distribution evenness (Gini-like coefficient)
    counts = list(agent_actions.values())
    mean_count = sum(counts) / len(counts)
    variance = sum((c - mean_count) ** 2 for c in counts) / len(counts)
    cv = (variance ** 0.5) / mean_count if mean_count > 0 else 0

    # Lower CV = more even distribution
    evenness_score = max(0, 1 - cv)

    # Check if expected agents participated
    if expected_agents:
        participation = len(set(agent_actions.keys()) & set(expected_agents)) / len(expected_agents)
        evenness_score = (evenness_score + participation) / 2

    msg = f"{num_agents} agents, distribution CV={cv:.2f}"
    return evenness_score, msg


def grade_communication(events: List[CoordinationEvent]) -> Tuple[float, str]:
    """Evaluate inter-agent communication quality."""
    if not events:
        return 0.5, "No coordination events (may be single-agent task)"

    score = 1.0
    issues = []

    # Check for response to requests
    requests = [e for e in events if e.event_type.lower() in ['request', 'ask', 'query']]
    responses = [e for e in events if e.event_type.lower() in ['response', 'reply', 'answer']]

    if requests:
        response_rate = len(responses) / len(requests)
        if response_rate < 0.8:
            score -= 0.2
            issues.append(f"Low response rate ({response_rate:.0%})")

    # Check for acknowledgments
    handoffs = [e for e in events if e.event_type.lower() in ['handoff', 'delegate', 'assign']]
    acks = [e for e in events if e.event_type.lower() in ['ack', 'acknowledge', 'received']]

    if handoffs and not acks:
        score -= 0.15
        issues.append("Handoffs not acknowledged")

    # Check for broadcast vs targeted communication
    broadcasts = [e for e in events if e.to_agent.lower() in ['all', 'broadcast', '*']]
    if broadcasts and len(broadcasts) > len(events) * 0.5:
        score -= 0.1
        issues.append("Too many broadcasts (inefficient)")

    # Check message clarity (length heuristic)
    short_messages = [e for e in events if len(e.content) < 10]
    if short_messages and len(short_messages) > len(events) * 0.3:
        score -= 0.1
        issues.append("Many unclear/short messages")

    msg = "; ".join(issues) if issues else "Good communication"
    return max(0.0, score), msg


def grade_conflict_resolution(
    events: List[CoordinationEvent],
    actions: List[AgentAction]
) -> Tuple[float, str]:
    """Evaluate how conflicts were handled."""
    score = 1.0
    issues = []

    # Look for conflict indicators
    conflict_keywords = ['conflict', 'disagree', 'override', 'reject', 'fail', 'error', 'retry']
    conflicts = [
        e for e in events
        if any(kw in e.content.lower() for kw in conflict_keywords)
    ]

    if not conflicts:
        return 1.0, "No conflicts detected"

    # Check if conflicts were resolved
    resolution_keywords = ['resolved', 'agreed', 'consensus', 'fixed', 'corrected', 'success']
    resolutions = [
        e for e in events
        if any(kw in e.content.lower() for kw in resolution_keywords)
    ]

    resolution_rate = len(resolutions) / len(conflicts) if conflicts else 1.0

    if resolution_rate < 0.5:
        score -= 0.3
        issues.append(f"Low conflict resolution ({resolution_rate:.0%})")
    elif resolution_rate < 0.8:
        score -= 0.15
        issues.append(f"Some unresolved conflicts")

    # Check for retry loops (same action repeated)
    action_types = [a.action_type for a in actions]
    repeated = len(action_types) - len(set(action_types))
    if repeated > len(actions) * 0.3:
        score -= 0.2
        issues.append("Excessive retries detected")

    msg = "; ".join(issues) if issues else f"Handled {len(conflicts)} conflicts"
    return max(0.0, score), msg


def grade_resource_efficiency(
    actions: List[AgentAction],
    events: List[CoordinationEvent]
) -> Tuple[float, str]:
    """Evaluate resource usage efficiency."""
    if not actions:
        return 0.5, "No actions to evaluate"

    score = 1.0
    issues = []

    # Check for duplicate work
    action_signatures = [f"{a.agent_id}:{a.action_type}" for a in actions]
    unique_sigs = set(action_signatures)

    # Identify potential duplicates (same action type by different agents)
    action_by_type = {}
    for action in actions:
        if action.action_type not in action_by_type:
            action_by_type[action.action_type] = set()
        action_by_type[action.action_type].add(action.agent_id)

    duplicated_work = [
        atype for atype, agents in action_by_type.items()
        if len(agents) > 1 and atype not in ['coordinate', 'communicate', 'verify']
    ]

    if duplicated_work:
        score -= len(duplicated_work) * 0.1
        issues.append(f"Duplicate work on: {duplicated_work[:3]}")

    # Check coordination overhead
    coord_events = len(events)
    actual_actions = len([a for a in actions if a.action_type not in ['coordinate', 'communicate']])

    if actual_actions > 0:
        overhead_ratio = coord_events / actual_actions
        if overhead_ratio > 2.0:
            score -= 0.2
            issues.append(f"High coordination overhead ({overhead_ratio:.1f}x)")
        elif overhead_ratio > 1.5:
            score -= 0.1
            issues.append(f"Moderate coordination overhead")

    # Check for idle agents (agents with very few actions)
    agent_actions = {}
    for action in actions:
        agent_actions[action.agent_id] = agent_actions.get(action.agent_id, 0) + 1

    if agent_actions:
        avg_actions = sum(agent_actions.values()) / len(agent_actions)
        idle_agents = [aid for aid, count in agent_actions.items() if count < avg_actions * 0.3]
        if idle_agents:
            score -= 0.1
            issues.append(f"Idle agents: {idle_agents}")

    msg = "; ".join(issues) if issues else "Efficient resource usage"
    return max(0.0, score), msg


def grade_goal_achievement(
    actions: List[AgentAction],
    expected_outcomes: List[str] = None,
    success_indicators: List[str] = None
) -> Tuple[float, str]:
    """Evaluate if collective goal was achieved."""
    if not actions:
        return 0.0, "No actions taken"

    # Default success indicators
    default_indicators = ['complete', 'success', 'done', 'finished', 'achieved']
    indicators = success_indicators or default_indicators

    # Check final actions for success
    final_actions = actions[-min(3, len(actions)):]
    success_signals = 0

    for action in final_actions:
        details_str = str(action.details).lower()
        if any(ind in details_str for ind in indicators):
            success_signals += 1
        if action.result and any(ind in action.result.lower() for ind in indicators):
            success_signals += 1

    base_score = min(1.0, success_signals * 0.3 + 0.4)

    # Check expected outcomes
    if expected_outcomes:
        all_details = ' '.join(str(a.details).lower() for a in actions)
        outcomes_met = sum(1 for outcome in expected_outcomes if outcome.lower() in all_details)
        outcome_score = outcomes_met / len(expected_outcomes)
        base_score = (base_score + outcome_score) / 2

    msg = f"Goal achievement score based on {len(actions)} actions"
    return base_score, msg


def grade_coordination(
    log: str = None,
    actions: List[AgentAction] = None,
    events: List[CoordinationEvent] = None,
    expected_agents: List[str] = None,
    expected_outcomes: List[str] = None,
    weights: Dict[str, float] = None
) -> Dict[str, Any]:
    """
    Comprehensive agent coordination evaluation.

    Args:
        log: Raw coordination log (will be parsed)
        actions: Pre-parsed agent actions
        events: Pre-parsed coordination events
        expected_agents: List of agents that should participate
        expected_outcomes: Expected task outcomes
        weights: Custom weights for dimensions

    Returns:
        Dict with overall score and dimension breakdowns
    """
    default_weights = {
        'task_distribution': 0.25,
        'communication': 0.25,
        'conflict_resolution': 0.15,
        'resource_efficiency': 0.20,
        'goal_achievement': 0.15
    }
    weights = weights or default_weights

    # Parse log if provided
    if log and not (actions and events):
        actions, events = parse_agent_log(log)

    actions = actions or []
    events = events or []

    results = {}

    # Run all graders
    dist_score, dist_msg = grade_task_distribution(actions, expected_agents)
    results['task_distribution'] = {'score': dist_score, 'message': dist_msg}

    comm_score, comm_msg = grade_communication(events)
    results['communication'] = {'score': comm_score, 'message': comm_msg}

    conflict_score, conflict_msg = grade_conflict_resolution(events, actions)
    results['conflict_resolution'] = {'score': conflict_score, 'message': conflict_msg}

    efficiency_score, efficiency_msg = grade_resource_efficiency(actions, events)
    results['resource_efficiency'] = {'score': efficiency_score, 'message': efficiency_msg}

    goal_score, goal_msg = grade_goal_achievement(actions, expected_outcomes)
    results['goal_achievement'] = {'score': goal_score, 'message': goal_msg}

    # Calculate weighted overall score
    overall = sum(results[dim]['score'] * weights.get(dim, 0) for dim in results)

    return {
        'overall_score': round(overall, 3),
        'passed': overall >= 0.7,
        'total_actions': len(actions),
        'total_events': len(events),
        'agents_involved': len(set(a.agent_id for a in actions)),
        'dimensions': results,
        'weights': weights
    }


if __name__ == "__main__":
    # Test the grader
    test_log = '''
    [AGENT:coordinator] ACTION: plan - Dividing task into subtasks for agents
    [coordinator->researcher] REQUEST: Research API patterns for authentication
    [coordinator->coder] REQUEST: Implement user model
    [AGENT:researcher] ACTION: search - Searching for OAuth2 best practices
    [researcher->coordinator] RESPONSE: Found 5 relevant patterns
    [AGENT:coder] ACTION: code - Creating User class with authentication
    [coder->coordinator] RESPONSE: User model complete
    [coordinator->coder] HANDOFF: researcher findings for implementation
    [AGENT:coder] ACTION: implement - Adding OAuth2 based on research
    [coder->coordinator] RESPONSE: Implementation complete - success
    [AGENT:coordinator] ACTION: verify - All tasks completed successfully
    '''

    result = grade_coordination(log=test_log)
    print(f"Overall Score: {result['overall_score']}")
    print(f"Passed: {result['passed']}")
    print(f"Agents: {result['agents_involved']}, Actions: {result['total_actions']}, Events: {result['total_events']}")
    for dim, data in result['dimensions'].items():
        print(f"  {dim}: {data['score']:.2f} - {data['message']}")

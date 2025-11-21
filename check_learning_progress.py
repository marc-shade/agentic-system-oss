#!/usr/bin/env python3
"""
Check AGI meta-learning progress and agent performance.

Shows detailed breakdown of what the system has learned from execution history.
"""

import sys
from pathlib import Path

# Add intelligent-agents to path
sys.path.insert(0, str(Path(__file__).parent / "intelligent-agents"))

from meta_learning_engine import MetaLearningEngine


def main():
    """Display detailed learning progress."""

    print("=" * 70)
    print("AGI META-LEARNING PROGRESS REPORT")
    print("=" * 70)
    print()

    engine = MetaLearningEngine()

    # Overall summary
    summary = engine.get_learning_summary()

    print("OVERALL LEARNING STATUS")
    print("-" * 70)
    print(f"Total outcomes recorded: {summary.get('total_outcomes', 0)}")
    print(f"Success rate: {summary.get('overall_success_rate', 0):.1%}")
    print(f"Learning maturity: {summary.get('learning_maturity', 0):.1%}")
    print(f"Unique task types: {summary.get('unique_task_types', 0)}")
    print()

    # Agent performance breakdown
    print("AGENT PERFORMANCE")
    print("-" * 70)

    agent_stats = summary.get('agent_stats', {})
    if agent_stats:
        for agent_name, stats in agent_stats.items():
            print(f"\n{agent_name.upper()}:")
            print(f"  - Total tasks: {stats.get('total_tasks', 0)}")
            print(f"  - Successes: {stats.get('successes', 0)}")
            print(f"  - Success rate: {stats.get('success_rate', 0):.1%}")
            print(f"  - Avg execution time: {stats.get('avg_execution_time_ms', 0):.0f}ms")
            print(f"  - Avg quality: {stats.get('avg_quality_score', 0):.2f}")
    else:
        print("(No agent performance data yet)")
    print()

    # Task type breakdown
    print("TASK TYPE PERFORMANCE")
    print("-" * 70)

    task_type_stats = summary.get('task_type_stats', {})
    if task_type_stats:
        for task_type, stats in task_type_stats.items():
            print(f"\n{task_type.upper()}:")
            print(f"  - Total tasks: {stats.get('total_tasks', 0)}")
            print(f"  - Success rate: {stats.get('success_rate', 0):.1%}")
            print(f"  - Avg execution time: {stats.get('avg_execution_time_ms', 0):.0f}ms")
            print(f"  - Best agent: {stats.get('best_agent', 'N/A')}")
    else:
        print("(No task type data yet)")
    print()

    # Recent patterns
    print("RECENT PATTERNS DETECTED")
    print("-" * 70)

    patterns = engine.detect_patterns(lookback_days=1)
    if patterns:
        for i, pattern in enumerate(patterns, 1):
            print(f"\nPattern {i}: {pattern.get('pattern_type', 'unknown')}")
            print(f"  - Confidence: {pattern.get('confidence', 0):.1%}")
            print(f"  - Description: {pattern.get('description', 'N/A')}")
            if pattern.get('insights'):
                print(f"  - Insights:")
                for insight in pattern['insights']:
                    print(f"    • {insight}")
    else:
        print("(No patterns detected yet - need more data)")
    print()

    # Agent recommendations
    print("AGENT RECOMMENDATIONS")
    print("-" * 70)

    test_task_types = ["code_generation", "testing", "architecture", "optimization", "general"]
    for task_type in test_task_types:
        agent, confidence = engine.recommend_agent(task_type)
        if agent != "general-purpose" or confidence > 0:
            print(f"{task_type}: {agent} (confidence: {confidence:.1%})")
    print()

    print("=" * 70)
    print("✓ Learning progress analysis complete")
    print("=" * 70)
    print()

    # Learning trajectory
    print("LEARNING TRAJECTORY")
    print("-" * 70)
    print(f"Current maturity: {summary.get('learning_maturity', 0):.1%}")

    outcomes = summary.get('total_outcomes', 0)
    if outcomes < 50:
        print(f"Status: Early learning phase ({outcomes}/50 minimum for pattern detection)")
        print(f"Need {50-outcomes} more outcomes to reliably detect patterns")
    elif outcomes < 200:
        print(f"Status: Active learning phase ({outcomes}/200 for stable recommendations)")
        print("Patterns emerging, agent recommendations gaining confidence")
    else:
        print(f"Status: Mature learning phase ({outcomes} outcomes)")
        print("Reliable recommendations and pattern detection active")
    print()


if __name__ == "__main__":
    main()

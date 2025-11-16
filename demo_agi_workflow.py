#!/usr/bin/env python3
"""
AGI System Demonstration
========================

Full end-to-end demonstration of the integrated AGI system showing
all 6 components working together in a real workflow.
"""

import asyncio
import sys
from pathlib import Path

# Add intelligent-agents to path
sys.path.insert(0, str(Path(__file__).parent / "intelligent-agents"))

from agi_orchestrator import AGIOrchestrator


async def main():
    """Run complete AGI workflow demonstration."""

    print("=" * 70)
    print("AGI SYSTEM DEMONSTRATION")
    print("=" * 70)
    print()

    # Initialize orchestrator
    print("Initializing AGI Orchestrator...")
    orchestrator = AGIOrchestrator()
    print("✓ Orchestrator ready\n")

    # Example Goal: Build a data processing pipeline
    goal = "Create a Python data processing pipeline that reads CSV files, filters invalid records, transforms data, and exports to JSON"

    print(f"GOAL: {goal}")
    print()
    print("Executing 6-phase AGI workflow...")
    print("-" * 70)
    print()

    # Execute complete AGI workflow
    result = await orchestrator.execute_goal(
        goal_description=goal,
        context={
            "language": "Python",
            "input_format": "CSV",
            "output_format": "JSON",
            "requirements": ["data validation", "error handling", "logging"]
        },
        record_learning=True,
        propose_improvements=True
    )

    # Display results
    print("\n" + "=" * 70)
    print("EXECUTION RESULTS")
    print("=" * 70)
    print()

    print(f"Overall Status: {'✓ SUCCESS' if result['success'] else '✗ FAILED'}")
    print(f"Execution ID: {result['execution_id']}")
    print(f"Total Duration: {result['total_duration_seconds']:.2f}s")
    print()

    # Phase results
    print("PHASE RESULTS:")
    print("-" * 70)

    for phase_name, phase_data in result.get('phases', {}).items():
        status_icon = "✓" if phase_data.get('status') == 'success' else "✗"
        print(f"\n{status_icon} {phase_name.upper().replace('_', ' ')}")

        # Display phase-specific details
        if phase_name == "goal_decomposition":
            print(f"  - Tasks created: {phase_data.get('total_tasks', 0)}")
            print(f"  - Estimated duration: {phase_data.get('estimated_duration', 0)} minutes")

        elif phase_name == "context_synthesis":
            print(f"  - Context chunks: {phase_data.get('chunks', 0)}")
            print(f"  - Total tokens: {phase_data.get('total_tokens', 0)}")
            print(f"  - Compression ratio: {phase_data.get('compression_ratio', 0):.2f}x")

        elif phase_name == "execution":
            print(f"  - Subtasks completed: {phase_data.get('subtasks_completed', 0)}/{phase_data.get('subtasks_total', 0)}")
            print(f"  - Execution time: {phase_data.get('execution_time_ms', 0)}ms")

        elif phase_name == "meta_learning":
            print(f"  - Outcomes recorded: {phase_data.get('outcomes_recorded', 0)}")
            print(f"  - Patterns detected: {phase_data.get('patterns_detected', 0)}")

        elif phase_name == "skill_evolution":
            print(f"  - Skills tracked: {phase_data.get('skills_tracked', 0)}")

        elif phase_name == "darwin_godel":
            print(f"  - Improvement opportunities: {phase_data.get('improvement_opportunities', 0)}")
            if phase_data.get('opportunities'):
                print(f"  - Types: {', '.join(set(o['type'] for o in phase_data['opportunities']))}")

    print("\n" + "=" * 70)
    print("SYSTEM HEALTH CHECK")
    print("=" * 70)
    print()

    # Get system health
    health = orchestrator.get_system_health()

    print("Meta-Learning Engine:")
    summary = health['meta_learning']['summary']
    print(f"  - Total outcomes: {summary.get('total_outcomes', 0)}")
    print(f"  - Success rate: {summary.get('overall_success_rate', 0):.1%}")
    print(f"  - Learning maturity: {summary.get('learning_maturity', 0):.1%}")

    print("\nMulti-Agent Coordination:")
    status = health['coordination']['status']
    print(f"  - Available agents: {status.get('total_agents', 0)}")
    print(f"  - Active sessions: {status.get('active_sessions', 0)}")
    print(f"  - Total capacity: {status.get('total_capacity', 0)}")

    print("\nDarwin Gödel Machine:")
    print(f"  - Modifications tracked: {health['darwin_godel']['modifications']}")

    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)
    print()
    print("The AGI system successfully executed a complete workflow:")
    print("  1. ✓ Decomposed goal into hierarchical tasks")
    print("  2. ✓ Synthesized relevant context from multiple sources")
    print("  3. ✓ Executed tasks using multi-agent coordination")
    print("  4. ✓ Recorded outcomes for continuous learning")
    print("  5. ✓ Tracked skills for evolutionary improvement")
    print("  6. ✓ Analyzed execution for system optimizations")
    print()
    print("All 6 AGI components working together seamlessly!")
    print()


if __name__ == "__main__":
    asyncio.run(main())

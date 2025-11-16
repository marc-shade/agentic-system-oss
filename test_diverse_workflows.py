#!/usr/bin/env python3
"""
Test diverse AGI workflows to accumulate varied learning data.

This script runs multiple different types of goals through the AGI system
to help the meta-learning engine detect cross-domain patterns.
"""

import asyncio
import sys
from pathlib import Path

# Add intelligent-agents to path
sys.path.insert(0, str(Path(__file__).parent / "intelligent-agents"))

from agi_orchestrator import AGIOrchestrator


async def main():
    """Run multiple diverse AGI workflows."""

    print("=" * 70)
    print("DIVERSE AGI WORKFLOW TESTING")
    print("=" * 70)
    print()

    # Initialize orchestrator
    print("Initializing AGI Orchestrator...")
    orchestrator = AGIOrchestrator()
    print("✓ Orchestrator ready\n")

    # Define diverse test goals
    test_goals = [
        {
            "description": "Build a REST API for user authentication with JWT tokens",
            "context": {
                "language": "Python",
                "framework": "FastAPI",
                "requirements": ["JWT", "password hashing", "rate limiting"]
            }
        },
        {
            "description": "Create a machine learning model to predict customer churn",
            "context": {
                "task_type": "machine_learning",
                "algorithm": "random_forest",
                "requirements": ["data preprocessing", "feature engineering", "model evaluation"]
            }
        },
        {
            "description": "Optimize SQL queries for better database performance",
            "context": {
                "task_type": "optimization",
                "database": "PostgreSQL",
                "requirements": ["indexing", "query planning", "performance metrics"]
            }
        },
        {
            "description": "Design a microservices architecture for e-commerce platform",
            "context": {
                "task_type": "architecture",
                "requirements": ["service discovery", "API gateway", "event sourcing"]
            }
        },
        {
            "description": "Implement automated testing suite with high coverage",
            "context": {
                "task_type": "testing",
                "framework": "pytest",
                "requirements": ["unit tests", "integration tests", "coverage >80%"]
            }
        }
    ]

    results = []

    for i, goal in enumerate(test_goals, 1):
        print(f"\n{'=' * 70}")
        print(f"WORKFLOW {i}/{len(test_goals)}")
        print(f"{'=' * 70}")
        print(f"Goal: {goal['description']}")
        print()

        try:
            result = await orchestrator.execute_goal(
                goal_description=goal["description"],
                context=goal["context"],
                record_learning=True,
                propose_improvements=True
            )

            results.append({
                "goal": goal["description"],
                "success": result["success"],
                "duration": result["total_duration_seconds"],
                "phases": {k: v.get("status") for k, v in result.get("phases", {}).items()}
            })

            status_icon = "✓" if result["success"] else "✗"
            print(f"\n{status_icon} Workflow {i} completed in {result['total_duration_seconds']:.2f}s")

        except Exception as e:
            print(f"\n✗ Workflow {i} failed: {e}")
            results.append({
                "goal": goal["description"],
                "success": False,
                "error": str(e)
            })

    # Summary
    print(f"\n\n{'=' * 70}")
    print("FINAL SUMMARY")
    print(f"{'=' * 70}\n")

    successful = sum(1 for r in results if r.get("success"))
    print(f"Workflows completed: {len(results)}")
    print(f"Successful: {successful}/{len(results)}")
    print(f"Success rate: {successful/len(results)*100:.1f}%")

    # System health after diverse workflows
    print(f"\n{'=' * 70}")
    print("SYSTEM HEALTH AFTER DIVERSE WORKFLOWS")
    print(f"{'=' * 70}\n")

    health = orchestrator.get_system_health()

    summary = health['meta_learning']['summary']
    print("Meta-Learning Engine:")
    print(f"  - Total outcomes: {summary.get('total_outcomes', 0)}")
    print(f"  - Success rate: {summary.get('overall_success_rate', 0):.1%}")
    print(f"  - Learning maturity: {summary.get('learning_maturity', 0):.1%}")
    print(f"  - Unique task types: {summary.get('unique_task_types', 0)}")

    status = health['coordination']['status']
    print("\nMulti-Agent Coordination:")
    print(f"  - Available agents: {status.get('total_agents', 0)}")
    print(f"  - Active sessions: {status.get('active_sessions', 0)}")
    print(f"  - Tasks completed: {status.get('completed_tasks', 0)}")

    print(f"\n{'=' * 70}")
    print("✓ Diverse workflow testing complete!")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    asyncio.run(main())

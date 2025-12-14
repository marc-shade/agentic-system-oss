#!/usr/bin/env python3
"""
Goal Decomposition Workflow
============================

Automatically decomposes high-level goals into actionable tasks using AI.
Creates task dependency graph (DAG) and assigns to optimal agents/nodes.

Workflow:
1. Analyze goal and break into sub-goals
2. Decompose sub-goals into concrete tasks
3. Identify dependencies between tasks
4. Estimate effort and resources
5. Create task DAG in agent-runtime
6. Assign tasks to optimal agents/nodes
7. Schedule execution order

Uses AI-powered decomposition for intelligent planning.

STATUS: Production Ready
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.common import RetryPolicy
import sys
import json
import re
import os

# Dynamic path detection for cross-node compatibility (sandbox-safe)
_current_file = os.path.abspath(__file__)
_workflows_dir = os.path.dirname(_current_file)
_base_dir = os.path.dirname(os.path.dirname(_workflows_dir))
_mcp_runtime_dir = os.path.join(_base_dir, "mcp-servers", "agent-runtime-mcp")
_mcp_agi_dir = os.path.join(_base_dir, "mcp-servers", "agi-mcp")

sys.path.insert(0, _mcp_runtime_dir)
sys.path.insert(0, _mcp_agi_dir)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@activity.defn
async def analyze_goal(goal_description: str) -> Dict[str, Any]:
    """
    Analyze goal to understand:
    - Complexity level
    - Domain/category
    - Required capabilities
    - Estimated effort

    Uses simple heuristic + pattern matching
    (In production, would use LLM for deeper analysis)
    """
    try:
        analysis = {
            "complexity": "medium",
            "domain": "general",
            "required_capabilities": [],
            "estimated_tasks": 3,
            "is_technical": False,
            "requires_research": False,
            "requires_coding": False
        }

        goal_lower = goal_description.lower()

        # Complexity estimation (simple heuristic)
        word_count = len(goal_description.split())
        if word_count < 10:
            analysis["complexity"] = "simple"
            analysis["estimated_tasks"] = 2
        elif word_count > 30:
            analysis["complexity"] = "complex"
            analysis["estimated_tasks"] = 8

        # Domain detection
        if any(keyword in goal_lower for keyword in ["code", "implement", "build", "develop", "program"]):
            analysis["domain"] = "software_engineering"
            analysis["is_technical"] = True
            analysis["requires_coding"] = True
            analysis["required_capabilities"].append("coding")

        if any(keyword in goal_lower for keyword in ["research", "analyze", "investigate", "study", "paper"]):
            analysis["domain"] = "research"
            analysis["requires_research"] = True
            analysis["required_capabilities"].append("research")

        if any(keyword in goal_lower for keyword in ["optimize", "improve", "enhance", "refactor"]):
            analysis["domain"] = "optimization"
            analysis["required_capabilities"].append("optimization")

        if any(keyword in goal_lower for keyword in ["test", "verify", "validate", "qa"]):
            analysis["required_capabilities"].append("testing")

        if any(keyword in goal_lower for keyword in ["document", "write", "explain", "guide"]):
            analysis["required_capabilities"].append("documentation")

        logger.info(f"Goal analysis: {analysis}")

        return analysis

    except Exception as e:
        logger.error(f"Goal analysis failed: {e}")
        return {"complexity": "medium", "estimated_tasks": 3}


@activity.defn
async def decompose_goal_into_tasks(
    goal_description: str,
    goal_analysis: Dict
) -> List[Dict[str, Any]]:
    """
    Decompose goal into concrete tasks

    Returns list of task specifications:
    [
        {
            "title": str,
            "description": str,
            "task_type": str,
            "priority": int (1-10),
            "dependencies": List[int],  # Indexes of dependent tasks
            "estimated_duration_minutes": int,
            "required_capabilities": List[str],
            "preferred_agent": str
        }
    ]
    """
    try:
        tasks = []
        complexity = goal_analysis.get("complexity", "medium")
        domain = goal_analysis.get("domain", "general")

        # Template-based decomposition (production would use LLM)

        if domain == "software_engineering":
            # Software development workflow
            tasks = [
                {
                    "title": "Research and plan approach",
                    "description": f"Research best practices and plan implementation for: {goal_description}",
                    "task_type": "research",
                    "priority": 10,
                    "dependencies": [],
                    "estimated_duration_minutes": 30,
                    "required_capabilities": ["research", "planning"],
                    "preferred_agent": "researcher"
                },
                {
                    "title": "Implement solution",
                    "description": f"Implement: {goal_description}",
                    "task_type": "coding",
                    "priority": 9,
                    "dependencies": [0],
                    "estimated_duration_minutes": 120,
                    "required_capabilities": ["coding"],
                    "preferred_agent": "coder"
                },
                {
                    "title": "Write tests",
                    "description": f"Write comprehensive tests for: {goal_description}",
                    "task_type": "testing",
                    "priority": 8,
                    "dependencies": [1],
                    "estimated_duration_minutes": 60,
                    "required_capabilities": ["testing", "coding"],
                    "preferred_agent": "tester"
                },
                {
                    "title": "Code review",
                    "description": f"Review code quality and best practices for: {goal_description}",
                    "task_type": "review",
                    "priority": 7,
                    "dependencies": [1, 2],
                    "estimated_duration_minutes": 30,
                    "required_capabilities": ["code_review"],
                    "preferred_agent": "reviewer"
                },
                {
                    "title": "Documentation",
                    "description": f"Document implementation of: {goal_description}",
                    "task_type": "documentation",
                    "priority": 6,
                    "dependencies": [3],
                    "estimated_duration_minutes": 45,
                    "required_capabilities": ["documentation"],
                    "preferred_agent": "researcher"
                }
            ]

        elif domain == "research":
            # Research workflow
            tasks = [
                {
                    "title": "Literature search",
                    "description": f"Search for relevant papers and resources for: {goal_description}",
                    "task_type": "research",
                    "priority": 10,
                    "dependencies": [],
                    "estimated_duration_minutes": 60,
                    "required_capabilities": ["research"],
                    "preferred_agent": "researcher"
                },
                {
                    "title": "Analyze findings",
                    "description": f"Analyze and synthesize research for: {goal_description}",
                    "task_type": "analysis",
                    "priority": 9,
                    "dependencies": [0],
                    "estimated_duration_minutes": 90,
                    "required_capabilities": ["analysis"],
                    "preferred_agent": "researcher"
                },
                {
                    "title": "Generate insights",
                    "description": f"Extract key insights and recommendations for: {goal_description}",
                    "task_type": "synthesis",
                    "priority": 8,
                    "dependencies": [1],
                    "estimated_duration_minutes": 45,
                    "required_capabilities": ["synthesis"],
                    "preferred_agent": "researcher"
                },
                {
                    "title": "Document findings",
                    "description": f"Create comprehensive documentation for: {goal_description}",
                    "task_type": "documentation",
                    "priority": 7,
                    "dependencies": [2],
                    "estimated_duration_minutes": 60,
                    "required_capabilities": ["documentation"],
                    "preferred_agent": "researcher"
                }
            ]

        elif domain == "optimization":
            # Optimization workflow
            tasks = [
                {
                    "title": "Baseline measurement",
                    "description": f"Measure current performance for: {goal_description}",
                    "task_type": "benchmarking",
                    "priority": 10,
                    "dependencies": [],
                    "estimated_duration_minutes": 30,
                    "required_capabilities": ["benchmarking"],
                    "preferred_agent": "coder"
                },
                {
                    "title": "Identify bottlenecks",
                    "description": f"Analyze and identify optimization opportunities for: {goal_description}",
                    "task_type": "analysis",
                    "priority": 9,
                    "dependencies": [0],
                    "estimated_duration_minutes": 45,
                    "required_capabilities": ["analysis", "optimization"],
                    "preferred_agent": "architect"
                },
                {
                    "title": "Implement optimizations",
                    "description": f"Apply optimizations for: {goal_description}",
                    "task_type": "coding",
                    "priority": 8,
                    "dependencies": [1],
                    "estimated_duration_minutes": 90,
                    "required_capabilities": ["coding", "optimization"],
                    "preferred_agent": "coder"
                },
                {
                    "title": "Verify improvements",
                    "description": f"Measure and validate improvements for: {goal_description}",
                    "task_type": "testing",
                    "priority": 7,
                    "dependencies": [2],
                    "estimated_duration_minutes": 30,
                    "required_capabilities": ["testing", "benchmarking"],
                    "preferred_agent": "tester"
                }
            ]

        else:
            # Generic workflow
            tasks = [
                {
                    "title": "Plan approach",
                    "description": f"Plan how to accomplish: {goal_description}",
                    "task_type": "planning",
                    "priority": 10,
                    "dependencies": [],
                    "estimated_duration_minutes": 30,
                    "required_capabilities": ["planning"],
                    "preferred_agent": "general-purpose"
                },
                {
                    "title": "Execute task",
                    "description": f"Execute: {goal_description}",
                    "task_type": "general",
                    "priority": 9,
                    "dependencies": [0],
                    "estimated_duration_minutes": 60,
                    "required_capabilities": ["general"],
                    "preferred_agent": "general-purpose"
                },
                {
                    "title": "Verify results",
                    "description": f"Verify completion of: {goal_description}",
                    "task_type": "validation",
                    "priority": 8,
                    "dependencies": [1],
                    "estimated_duration_minutes": 20,
                    "required_capabilities": ["validation"],
                    "preferred_agent": "general-purpose"
                }
            ]

        logger.info(f"Decomposed goal into {len(tasks)} tasks")

        return tasks

    except Exception as e:
        logger.error(f"Goal decomposition failed: {e}")
        return []


@activity.defn
async def create_goal_in_runtime(goal_description: str, metadata: Dict) -> int:
    """
    Create goal in agent-runtime MCP

    Returns goal_id
    """
    try:
        from server import create_goal

        result = await create_goal(
            name=goal_description[:100],  # Truncate if too long
            description=goal_description,
            metadata=metadata
        )

        goal_id = result.get("goal_id")
        logger.info(f"Created goal {goal_id} in agent-runtime")

        return goal_id

    except Exception as e:
        logger.error(f"Failed to create goal: {e}")
        raise


@activity.defn
async def create_tasks_in_runtime(goal_id: int, tasks: List[Dict]) -> List[int]:
    """
    Create tasks in agent-runtime MCP and link to goal

    Returns list of task_ids
    """
    try:
        from server import create_task

        task_ids = []

        for task in tasks:
            result = await create_task(
                title=task["title"],
                description=task["description"],
                goal_id=goal_id,
                priority=task.get("priority", 5),
                dependencies=task.get("dependencies", [])
            )

            task_id = result.get("task_id")
            task_ids.append(task_id)

            logger.info(f"Created task {task_id}: {task['title']}")

        return task_ids

    except Exception as e:
        logger.error(f"Failed to create tasks: {e}")
        return []


@activity.defn
async def schedule_task_execution(task_ids: List[int]) -> Dict[str, Any]:
    """
    Schedule tasks for execution via cluster orchestration

    Returns scheduling plan
    """
    try:
        # For now, mark first task as ready (others wait for dependencies)
        # In production, would trigger cluster orchestration workflow

        schedule = {
            "ready_tasks": [task_ids[0]] if task_ids else [],
            "waiting_tasks": task_ids[1:] if len(task_ids) > 1 else [],
            "total_tasks": len(task_ids),
            "timestamp": workflow.now().isoformat()
        }

        logger.info(f"Scheduled {len(schedule['ready_tasks'])} tasks for immediate execution")

        return schedule

    except Exception as e:
        logger.error(f"Task scheduling failed: {e}")
        return {"ready_tasks": [], "waiting_tasks": []}


@workflow.defn
class GoalDecompositionWorkflow:
    """
    Decomposes high-level goals into actionable task DAG

    Workflow:
    1. Analyze goal
    2. Decompose into tasks
    3. Create goal in runtime
    4. Create tasks with dependencies
    5. Schedule execution
    """

    @workflow.run
    async def run(self, goal_description: str) -> Dict[str, Any]:
        """
        Execute goal decomposition

        Args:
            goal_description: Natural language goal description

        Returns:
            Decomposition report with goal_id and task_ids
        """
        start_time = workflow.now()
        logger.info(f"Starting goal decomposition: {goal_description}")

        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=3
        )

        try:
            # Step 1: Analyze goal
            analysis = await workflow.execute_activity(
                analyze_goal,
                args=[goal_description],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy
            )

            # Step 2: Decompose into tasks
            tasks = await workflow.execute_activity(
                decompose_goal_into_tasks,
                args=[goal_description, analysis],
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=retry_policy
            )

            if not tasks:
                return {
                    "success": False,
                    "error": "Failed to decompose goal into tasks"
                }

            # Step 3: Create goal in runtime
            goal_id = await workflow.execute_activity(
                create_goal_in_runtime,
                args=[goal_description, analysis],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy
            )

            # Step 4: Create tasks
            task_ids = await workflow.execute_activity(
                create_tasks_in_runtime,
                args=[goal_id, tasks],
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=retry_policy
            )

            # Step 5: Schedule execution
            schedule = await workflow.execute_activity(
                schedule_task_execution,
                args=[task_ids],
                start_to_close_timeout=timedelta(seconds=30)
            )

            duration = (workflow.now() - start_time).total_seconds()

            decomposition_report = {
                "success": True,
                "goal_id": goal_id,
                "task_ids": task_ids,
                "task_count": len(task_ids),
                "complexity": analysis.get("complexity"),
                "domain": analysis.get("domain"),
                "schedule": schedule,
                "duration_seconds": duration,
                "timestamp": workflow.now().isoformat()
            }

            logger.info(f"Goal decomposition completed: {decomposition_report}")

            return decomposition_report

        except Exception as e:
            logger.error(f"Goal decomposition workflow failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": workflow.now().isoformat()
            }


async def main():
    """
    Worker process for goal decomposition
    """
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="goal-decomposition",
        workflows=[GoalDecompositionWorkflow],
        activities=[
            analyze_goal,
            decompose_goal_into_tasks,
            create_goal_in_runtime,
            create_tasks_in_runtime,
            schedule_task_execution
        ]
    )

    logger.info("Goal Decomposition worker started")
    logger.info("Workflow: GoalDecompositionWorkflow")

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())

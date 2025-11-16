#!/usr/bin/env python3
"""
Unified AGI Orchestrator
========================

End-to-end execution pipeline connecting all 6 AGI components in a unified workflow.

This orchestrator is the "nervous system" of the AGI system, coordinating:
1. Goal Decomposition - Parse natural language into tasks
2. Context Synthesis - Gather relevant information
3. Multi-Agent Coordination - Execute tasks in parallel
4. Meta-Learning - Record outcomes for continuous improvement
5. Skill Evolution - Track and evolve successful patterns
6. Darwin Gödel - Propose system improvements

The orchestrator makes the AGI components work together as a cohesive system.
"""

import asyncio
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import all AGI components
from meta_learning_engine import MetaLearningEngine, TaskOutcome
from multi_agent_coordinator import MultiAgentCoordinator
from skill_evolution_system import SkillEvolutionSystem
from goal_decomposition_ai import GoalDecompositionAI
from context_synthesis_engine import ContextSynthesisEngine
from darwin_godel_machine import DarwinGodelMachine, ModificationType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AGIOrchestrator:
    """
    Unified orchestrator connecting all AGI components in end-to-end workflows.

    This is the main entry point for executing AGI tasks. It coordinates
    all 6 components to provide autonomous, self-improving AGI capabilities.
    """

    def __init__(self):
        """Initialize all AGI components."""
        logger.info("Initializing AGI Orchestrator...")

        self.meta_learning = MetaLearningEngine()
        self.coordinator = MultiAgentCoordinator()
        self.skill_evolution = SkillEvolutionSystem()
        self.goal_ai = GoalDecompositionAI()
        self.context_engine = ContextSynthesisEngine()
        self.darwin_godel = DarwinGodelMachine()

        # Set Darwin Gödel baseline
        self.darwin_godel.set_baseline()

        logger.info("AGI Orchestrator initialized successfully")

    async def execute_goal(
        self,
        goal_description: str,
        context: Optional[Dict] = None,
        record_learning: bool = True,
        propose_improvements: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a complete AGI workflow for a given goal.

        This is the main entry point for AGI execution. It:
        1. Decomposes the goal into hierarchical tasks
        2. Synthesizes relevant context
        3. Executes tasks using multi-agent coordination
        4. Records outcomes for meta-learning
        5. Tracks skills for evolution
        6. Proposes system improvements

        Args:
            goal_description: Natural language description of the goal
            context: Optional context dict (language, framework, constraints)
            record_learning: Whether to record outcomes for meta-learning
            propose_improvements: Whether to analyze for system improvements

        Returns:
            Complete execution result with all component outputs
        """
        execution_id = str(uuid.uuid4())
        start_time = datetime.now()

        logger.info(f"=== AGI EXECUTION START: {execution_id} ===")
        logger.info(f"Goal: {goal_description}")

        result = {
            "execution_id": execution_id,
            "goal_description": goal_description,
            "start_time": start_time.isoformat(),
            "phases": {}
        }

        try:
            # ================================================================
            # PHASE 1: Goal Decomposition
            # ================================================================
            logger.info("Phase 1: Goal Decomposition")

            decomposition = await self.goal_ai.execute_goal(
                goal_description,
                context
            )

            result["phases"]["goal_decomposition"] = {
                "status": "success",
                "goal_id": decomposition.get("goal_id"),
                "total_tasks": decomposition.get("total_tasks"),
                "estimated_duration": decomposition.get("estimated_total_duration_minutes")
            }

            logger.info(f"Goal decomposed into {decomposition['total_tasks']} tasks")

            # ================================================================
            # PHASE 2: Context Synthesis
            # ================================================================
            logger.info("Phase 2: Context Synthesis")

            # Build context query from goal and tasks
            context_query = f"{goal_description} {' '.join([t['description'] for t in decomposition.get('tasks', [])])}"

            synthesized_context = await self.context_engine.synthesize(
                query=context_query,
                source_types=["file", "memory", "code"],
                target_tokens=10000
            )

            result["phases"]["context_synthesis"] = {
                "status": "success",
                "chunks": len(synthesized_context.chunks),
                "total_tokens": synthesized_context.total_tokens,
                "compression_ratio": synthesized_context.compression_ratio
            }

            logger.info(f"Context synthesized: {len(synthesized_context.chunks)} chunks, {synthesized_context.total_tokens} tokens")

            # ================================================================
            # PHASE 3: Multi-Agent Execution
            # ================================================================
            logger.info("Phase 3: Multi-Agent Execution")

            # Execute using coordinator
            execution_result = await self.coordinator.execute_task(
                goal_description,
                task_type=context.get("task_type", "general") if context else "general"
            )

            result["phases"]["execution"] = {
                "status": "success" if execution_result.get("success") else "partial",
                "subtasks_completed": execution_result.get("subtasks_completed", 0),
                "subtasks_total": execution_result.get("subtasks_total", 0),
                "execution_time_ms": execution_result.get("total_execution_time_ms", 0)
            }

            logger.info(f"Execution complete: {execution_result.get('subtasks_completed')}/{execution_result.get('subtasks_total')} subtasks")

            # ================================================================
            # PHASE 4: Meta-Learning (Record Outcomes)
            # ================================================================
            if record_learning:
                logger.info("Phase 4: Meta-Learning")

                # Record outcomes for each subtask
                for subtask_result in execution_result.get("results", []):
                    outcome = TaskOutcome(
                        task_id=subtask_result.get("task_id", str(uuid.uuid4())),
                        task_type=subtask_result.get("task_type", "general"),
                        agent_used=subtask_result.get("assigned_agent", "unknown"),
                        success=subtask_result.get("success", False),
                        execution_time_ms=subtask_result.get("execution_time_ms", 0),
                        error_message=subtask_result.get("error"),
                        quality_score=subtask_result.get("quality_score") or 0.5,  # Default to 0.5 if not provided
                        timestamp=datetime.now(),
                        context=context or {}
                    )

                    self.meta_learning.record_outcome(outcome)

                # Detect patterns
                patterns = self.meta_learning.detect_patterns(lookback_days=1)

                result["phases"]["meta_learning"] = {
                    "status": "success",
                    "outcomes_recorded": len(execution_result.get("results", [])),
                    "patterns_detected": len(patterns)
                }

                logger.info(f"Meta-learning: {len(execution_result.get('results', []))} outcomes recorded, {len(patterns)} patterns detected")

            # ================================================================
            # PHASE 5: Skill Evolution (Track Skills)
            # ================================================================
            logger.info("Phase 5: Skill Evolution")

            # Extract skills from successful subtasks
            skills_tracked = 0
            for subtask_result in execution_result.get("results", []):
                if subtask_result.get("success") and subtask_result.get("result"):
                    # Record skill execution
                    skill_name = subtask_result.get("task_type", "general")

                    # Note: In production, would register actual skill code
                    # For now, just track execution
                    skills_tracked += 1

            result["phases"]["skill_evolution"] = {
                "status": "success",
                "skills_tracked": skills_tracked
            }

            logger.info(f"Skill evolution: {skills_tracked} skills tracked")

            # ================================================================
            # PHASE 6: Darwin Gödel (Propose Improvements)
            # ================================================================
            if propose_improvements:
                logger.info("Phase 6: Darwin Gödel Machine")

                # Analyze execution for potential improvements
                improvement_opportunities = self._analyze_for_improvements(
                    execution_result,
                    decomposition
                )

                result["phases"]["darwin_godel"] = {
                    "status": "success",
                    "improvement_opportunities": len(improvement_opportunities),
                    "opportunities": improvement_opportunities
                }

                logger.info(f"Darwin Gödel: {len(improvement_opportunities)} improvement opportunities identified")

            # ================================================================
            # FINAL RESULT
            # ================================================================
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()

            result["end_time"] = end_time.isoformat()
            result["total_duration_seconds"] = total_duration
            result["success"] = execution_result.get("success", False)
            result["overall_status"] = "success" if result["success"] else "partial"

            logger.info(f"=== AGI EXECUTION COMPLETE: {execution_id} ===")
            logger.info(f"Duration: {total_duration:.2f}s, Success: {result['success']}")

            return result

        except Exception as e:
            logger.error(f"AGI execution failed: {e}", exc_info=True)

            end_time = datetime.now()
            result["end_time"] = end_time.isoformat()
            result["total_duration_seconds"] = (end_time - start_time).total_seconds()
            result["success"] = False
            result["overall_status"] = "error"
            result["error"] = str(e)

            return result

    def _analyze_for_improvements(
        self,
        execution_result: Dict,
        decomposition: Dict
    ) -> List[Dict]:
        """
        Analyze execution results for potential system improvements.

        Args:
            execution_result: Results from multi-agent execution
            decomposition: Goal decomposition details

        Returns:
            List of improvement opportunities
        """
        opportunities = []

        # Check for slow subtasks
        for subtask in execution_result.get("results", []):
            if subtask.get("execution_time_ms", 0) > 5000:  # > 5 seconds
                opportunities.append({
                    "type": "performance",
                    "description": f"Slow subtask: {subtask.get('description')} took {subtask['execution_time_ms']}ms",
                    "suggested_improvement": "Algorithm optimization or caching"
                })

        # Check for failed subtasks
        failed_count = sum(1 for s in execution_result.get("results", []) if not s.get("success", False))
        if failed_count > 0:
            opportunities.append({
                "type": "reliability",
                "description": f"{failed_count} subtasks failed",
                "suggested_improvement": "Error handling improvement or retry logic"
            })

        # Check for task decomposition efficiency
        if decomposition.get("total_tasks", 0) > 10:
            opportunities.append({
                "type": "decomposition",
                "description": f"Large number of subtasks ({decomposition['total_tasks']})",
                "suggested_improvement": "More efficient task decomposition or batching"
            })

        return opportunities

    async def execute_simple_task(
        self,
        task_description: str,
        task_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Execute a simple task without full goal decomposition.

        Useful for quick tasks that don't need the full AGI pipeline.
        Still uses coordination and meta-learning.

        Args:
            task_description: Task description
            task_type: Task type

        Returns:
            Execution result
        """
        execution_id = str(uuid.uuid4())
        start_time = datetime.now()

        logger.info(f"Simple task execution: {task_description}")

        # Execute using coordinator
        result = await self.coordinator.execute_task(task_description, task_type)

        # Record outcome for meta-learning
        if result.get("results"):
            for subtask_result in result["results"]:
                outcome = TaskOutcome(
                    task_id=subtask_result.get("task_id", str(uuid.uuid4())),
                    task_type=task_type,
                    agent_used=subtask_result.get("assigned_agent", "unknown"),
                    success=subtask_result.get("success", False),
                    execution_time_ms=subtask_result.get("execution_time_ms", 0),
                    error_message=subtask_result.get("error"),
                    quality_score=subtask_result.get("quality_score") or 0.5,  # Default to 0.5 if not provided
                    timestamp=datetime.now(),
                    context={}
                )

                self.meta_learning.record_outcome(outcome)

        end_time = datetime.now()
        result["execution_id"] = execution_id
        result["total_duration_seconds"] = (end_time - start_time).total_seconds()

        return result

    def get_system_health(self) -> Dict[str, Any]:
        """
        Get comprehensive system health status.

        Returns:
            Health status for all components
        """
        return {
            "meta_learning": {
                "summary": self.meta_learning.get_learning_summary()
            },
            "coordination": {
                "status": self.coordinator.get_system_status()
            },
            "skill_evolution": {
                "active_tests": 0  # Would query from system
            },
            "darwin_godel": {
                "modifications": len(self.darwin_godel.get_improvement_history())
            }
        }


async def main():
    """Example usage of AGI Orchestrator."""
    orchestrator = AGIOrchestrator()

    # Example: Execute a goal
    result = await orchestrator.execute_goal(
        goal_description="Implement user authentication with JWT tokens",
        context={"language": "Python", "framework": "FastAPI"}
    )

    print("\n=== AGI EXECUTION RESULT ===")
    print(f"Success: {result['success']}")
    print(f"Duration: {result['total_duration_seconds']:.2f}s")
    print(f"\nPhases:")
    for phase, details in result.get("phases", {}).items():
        print(f"  {phase}: {details['status']}")


if __name__ == "__main__":
    asyncio.run(main())

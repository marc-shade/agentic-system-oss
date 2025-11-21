#!/usr/bin/env python3
"""
Unified Cognitive Runtime Orchestrator
Integrates all 24 specialized cognitive runtimes into the main agentic system.
Manages runtime selection, task routing, confidence scoring, and learning feedback.

Phase 6: Cognitive Runtime Integration
"""

import json
import sys
import importlib.util
import asyncio
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum

# Configuration paths
RUNTIME_DIR = Path("/mnt/agentic-system/persistent-agent-sdk")
MEMORY_DIR = Path.home() / ".claude" / "memory"
LEARNING_DIR = MEMORY_DIR / "episodic"
SEMANTIC_DIR = MEMORY_DIR / "semantic"

# Runtime type definitions
class RuntimeType(Enum):
    """Types of cognitive runtimes"""
    CONSCIOUSNESS = "consciousness"
    EMOTIONAL = "emotional"
    REASONING = "reasoning"
    LEARNING = "learning"
    PLANNING = "planning"
    METACOGNITION = "metacognition"


class TaskType(Enum):
    """Task types for runtime selection"""
    CODE_ANALYSIS = "code_analysis"
    CODE_GENERATION = "code_generation"
    COMPLEX_REASONING = "complex_reasoning"
    CREATIVE_PROBLEM_SOLVING = "creative_problem_solving"
    LEARNING_RESEARCH = "learning_research"
    LONG_TERM_PLANNING = "long_term_planning"
    EMOTIONAL_DECISION = "emotional_decision"
    CONSCIOUSNESS_REFLECTION = "consciousness_reflection"


@dataclass
class RuntimeMetadata:
    """Metadata for a cognitive runtime"""
    name: str
    runtime_type: RuntimeType
    description: str
    module_name: str
    primary_class: str
    version: str
    confidence_threshold: float = 0.7
    resource_cost: str = "low"  # low, medium, high
    enabled: bool = True


@dataclass
class TaskContext:
    """Context for task execution"""
    task_id: str
    task_type: TaskType
    description: str
    context: Dict[str, Any]
    preferred_runtimes: List[str] = None
    confidence_threshold: float = 0.7
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.preferred_runtimes is None:
            self.preferred_runtimes = []


@dataclass
class RuntimeResult:
    """Result from runtime execution"""
    runtime_name: str
    success: bool
    result: Any
    confidence: float
    reasoning: str
    execution_time_ms: float
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class CognitiveRuntimeOrchestrator:
    """
    Master orchestrator for all 24 cognitive runtimes.
    Manages loading, selection, routing, and learning integration.
    """

    def __init__(self):
        """Initialize the cognitive runtime orchestrator"""
        self.runtimes: Dict[str, Tuple[RuntimeMetadata, Any]] = {}
        self.runtime_cache = {}
        self.selection_history: List[Dict] = []
        self.execution_history: List[RuntimeResult] = []

        # Runtime selection matrix (task_type -> [best_runtimes])
        self.selection_matrix = self._build_selection_matrix()

        # Load all available runtimes
        self._load_all_runtimes()

    def _build_selection_matrix(self) -> Dict[TaskType, List[str]]:
        """
        Build the runtime selection matrix: task types -> optimal runtimes.
        This matrix guides intelligent runtime selection based on task characteristics.
        """
        return {
            TaskType.CODE_ANALYSIS: [
                "consciousness_simulation",
                "deep_reasoning",
                "domain_expert",
                "common_sense"
            ],
            TaskType.CODE_GENERATION: [
                "creative_problem_solving",
                "consciousness_simulation",
                "meta_learning",
                "evolving_agent"
            ],
            TaskType.COMPLEX_REASONING: [
                "deep_reasoning",
                "gap_aware",
                "meta_cognition",
                "consciousness_simulation"
            ],
            TaskType.CREATIVE_PROBLEM_SOLVING: [
                "creative_problem_solving",
                "intuition",
                "enhanced_intuition",
                "breadth_expansion"
            ],
            TaskType.LEARNING_RESEARCH: [
                "learning_agent",
                "meta_learning",
                "memory_integrated",
                "evolving_agent"
            ],
            TaskType.LONG_TERM_PLANNING: [
                "long_term_planning",
                "resource_management",
                "gap_aware",
                "autonomous_goal"
            ],
            TaskType.EMOTIONAL_DECISION: [
                "emotional_intelligence",
                "intuition",
                "confidence_agent",
                "consciousness_simulation"
            ],
            TaskType.CONSCIOUSNESS_REFLECTION: [
                "consciousness_simulation",
                "self_monitoring",
                "expanded_consciousness",
                "meta_runtime"
            ]
        }

    def _load_all_runtimes(self):
        """
        Dynamically load all 24 cognitive runtimes from the persistent-agent-sdk.
        Handles import errors gracefully with fallback behavior.
        """
        runtime_definitions = [
            # Consciousness Systems (3)
            RuntimeMetadata(
                name="consciousness_simulation",
                runtime_type=RuntimeType.CONSCIOUSNESS,
                description="Consciousness modeling and self-awareness simulation",
                module_name="consciousness_simulation_runtime",
                primary_class="ConsciousnessSimulationRuntime",
                version="1.0"
            ),
            RuntimeMetadata(
                name="expanded_consciousness",
                runtime_type=RuntimeType.CONSCIOUSNESS,
                description="Expanded awareness and perception simulation",
                module_name="expanded_consciousness_runtime",
                primary_class="ExpandedConsciousnessRuntime",
                version="1.0"
            ),
            RuntimeMetadata(
                name="self_monitoring",
                runtime_type=RuntimeType.CONSCIOUSNESS,
                description="Self-observation and introspection runtime",
                module_name="self_monitoring_runtime",
                primary_class="SelfMonitoringRuntime",
                version="1.0"
            ),

            # Emotional & Social Intelligence (4)
            RuntimeMetadata(
                name="emotional_intelligence",
                runtime_type=RuntimeType.EMOTIONAL,
                description="Emotional reasoning and decision confidence",
                module_name="emotional_intelligence_runtime",
                primary_class="EmotionalIntelligenceRuntime",
                version="1.0"
            ),
            RuntimeMetadata(
                name="intuition",
                runtime_type=RuntimeType.EMOTIONAL,
                description="Intuitive reasoning and pattern recognition",
                module_name="intuition_runtime",
                primary_class="IntuitionRuntime",
                version="1.0"
            ),
            RuntimeMetadata(
                name="enhanced_intuition",
                runtime_type=RuntimeType.EMOTIONAL,
                description="Advanced intuitive reasoning with pattern learning",
                module_name="enhanced_intuition_runtime",
                primary_class="EnhancedIntuitionRuntime",
                version="1.0"
            ),
            RuntimeMetadata(
                name="collaborative_agent",
                runtime_type=RuntimeType.EMOTIONAL,
                description="Multi-agent collaboration and cooperation",
                module_name="collaborative_agent_runtime",
                primary_class="CollaborativeAgentRuntime",
                version="1.0"
            ),

            # Advanced Reasoning (4)
            RuntimeMetadata(
                name="deep_reasoning",
                runtime_type=RuntimeType.REASONING,
                description="Complex problem solving with deep analysis",
                module_name="deep_reasoning_runtime",
                primary_class="DeepReasoningRuntime",
                version="1.0"
            ),
            RuntimeMetadata(
                name="creative_problem_solving",
                runtime_type=RuntimeType.REASONING,
                description="Creative solution generation and optimization",
                module_name="creative_problem_solving_runtime",
                primary_class="CreativeProblemSolvingRuntime",
                version="1.0"
            ),
            RuntimeMetadata(
                name="common_sense",
                runtime_type=RuntimeType.REASONING,
                description="Common sense reasoning and practical logic",
                module_name="common_sense_runtime",
                primary_class="CommonSenseRuntime",
                version="1.0"
            ),
            RuntimeMetadata(
                name="domain_expert",
                runtime_type=RuntimeType.REASONING,
                description="Domain-specific expertise and knowledge application",
                module_name="domain_expert_runtime",
                primary_class="DomainExpertRuntime",
                version="1.0"
            ),

            # Learning & Evolution (4)
            RuntimeMetadata(
                name="learning_agent",
                runtime_type=RuntimeType.LEARNING,
                description="Continuous learning from tool execution outcomes",
                module_name="learning_agent_runtime",
                primary_class="LearningAgentRuntime",
                version="1.0"
            ),
            RuntimeMetadata(
                name="meta_learning",
                runtime_type=RuntimeType.LEARNING,
                description="Learning to learn - optimizing learning processes",
                module_name="meta_learning_runtime",
                primary_class="MetaLearningRuntime",
                version="1.0"
            ),
            RuntimeMetadata(
                name="evolving_agent",
                runtime_type=RuntimeType.LEARNING,
                description="Self-evolution and continuous improvement",
                module_name="evolving_agent_runtime",
                primary_class="EvolvingAgentRuntime",
                version="1.0"
            ),
            RuntimeMetadata(
                name="memory_integrated",
                runtime_type=RuntimeType.LEARNING,
                description="Memory integration for learning consolidation",
                module_name="memory_integrated_runtime",
                primary_class="MemoryIntegratedRuntime",
                version="1.0"
            ),

            # Meta-Cognitive & Planning (4)
            RuntimeMetadata(
                name="autonomous_goal",
                runtime_type=RuntimeType.PLANNING,
                description="Self-directed goal generation and prioritization",
                module_name="autonomous_goal_runtime",
                primary_class="AutonomousGoalRuntime",
                version="1.0"
            ),
            RuntimeMetadata(
                name="long_term_planning",
                runtime_type=RuntimeType.PLANNING,
                description="Long-term strategic planning and horizon analysis",
                module_name="long_term_planning_runtime",
                primary_class="LongTermPlanningRuntime",
                version="1.0"
            ),
            RuntimeMetadata(
                name="gap_aware",
                runtime_type=RuntimeType.PLANNING,
                description="Knowledge gap detection and closure planning",
                module_name="gap_aware_runtime",
                primary_class="GapAwareRuntime",
                version="1.0"
            ),
            RuntimeMetadata(
                name="resource_management",
                runtime_type=RuntimeType.PLANNING,
                description="Resource optimization and allocation",
                module_name="resource_management_runtime",
                primary_class="ResourceManagementRuntime",
                version="1.0"
            ),

            # Advanced Meta-Systems (3)
            RuntimeMetadata(
                name="meta_cognition",
                runtime_type=RuntimeType.METACOGNITION,
                description="Meta-level self-monitoring and awareness",
                module_name="meta_runtime",
                primary_class="MetaRuntime",
                version="1.0"
            ),
            RuntimeMetadata(
                name="confidence_agent",
                runtime_type=RuntimeType.METACOGNITION,
                description="Confidence estimation and calibration",
                module_name="confidence_agent_runtime",
                primary_class="ConfidenceAgentRuntime",
                version="1.0"
            ),
            RuntimeMetadata(
                name="breadth_expansion",
                runtime_type=RuntimeType.METACOGNITION,
                description="Knowledge breadth expansion and cross-domain learning",
                module_name="breadth_expansion_runtime",
                primary_class="BreadthExpansionRuntime",
                version="1.0"
            ),
        ]

        loaded_count = 0
        failed_count = 0

        for metadata in runtime_definitions:
            try:
                # Try to load the runtime
                module_path = RUNTIME_DIR / f"{metadata.module_name}.py"

                if module_path.exists():
                    # Dynamically load the module
                    spec = importlib.util.spec_from_file_location(
                        metadata.module_name,
                        module_path
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Try to instantiate the runtime class
                    runtime_class = getattr(module, metadata.primary_class, None)
                    if runtime_class:
                        runtime_instance = runtime_class()
                        self.runtimes[metadata.name] = (metadata, runtime_instance)
                        loaded_count += 1
                    else:
                        print(f"⚠️  Warning: {metadata.primary_class} not found in {metadata.module_name}")
                        self.runtimes[metadata.name] = (metadata, None)
                else:
                    print(f"⚠️  Warning: {module_path} not found")
                    self.runtimes[metadata.name] = (metadata, None)

            except Exception as e:
                print(f"⚠️  Warning: Failed to load {metadata.name}: {e}")
                self.runtimes[metadata.name] = (metadata, None)
                failed_count += 1

        print(f"✅ Cognitive Runtime Orchestrator initialized")
        print(f"   Loaded: {loaded_count} runtimes")
        print(f"   Metadata registered: {len(self.runtimes)} total")
        if failed_count > 0:
            print(f"   Failed: {failed_count} (continue with fallback)")

    def select_optimal_runtimes(
        self,
        task_context: TaskContext,
        max_runtimes: int = 3
    ) -> List[str]:
        """
        Select optimal runtimes for a task based on type and preferences.

        Returns the top N runtimes ranked by suitability.
        """
        selected = []

        # First check preferred runtimes
        if task_context.preferred_runtimes:
            for runtime_name in task_context.preferred_runtimes:
                if runtime_name in self.runtimes and len(selected) < max_runtimes:
                    selected.append(runtime_name)

        # Then add recommended runtimes from selection matrix
        if task_context.task_type in self.selection_matrix:
            for runtime_name in self.selection_matrix[task_context.task_type]:
                if runtime_name not in selected and runtime_name in self.runtimes:
                    if len(selected) < max_runtimes:
                        selected.append(runtime_name)

        # Record selection for learning
        self.selection_history.append({
            "timestamp": datetime.now().isoformat(),
            "task_id": task_context.task_id,
            "task_type": task_context.task_type.value,
            "selected_runtimes": selected
        })

        return selected

    async def execute_with_runtimes(
        self,
        task_context: TaskContext
    ) -> Dict[str, Any]:
        """
        Execute a task with selected cognitive runtimes.
        Returns aggregated results with confidence scores.
        """
        import time

        selected_runtimes = self.select_optimal_runtimes(task_context)

        if not selected_runtimes:
            return {
                "success": False,
                "error": "No suitable runtimes available",
                "task_id": task_context.task_id
            }

        results = {}
        aggregated_confidence = 0.0

        for runtime_name in selected_runtimes:
            metadata, runtime_instance = self.runtimes.get(runtime_name, (None, None))

            if runtime_instance is None:
                # Fallback: record that runtime is unavailable
                results[runtime_name] = {
                    "status": "unavailable",
                    "reason": "Runtime not loaded"
                }
                continue

            try:
                start_time = time.time()

                # Execute the runtime
                if hasattr(runtime_instance, 'execute'):
                    result = await runtime_instance.execute(task_context.description)
                elif hasattr(runtime_instance, 'process'):
                    result = await runtime_instance.process(task_context.context)
                else:
                    result = None

                execution_time_ms = (time.time() - start_time) * 1000

                # Extract confidence if available
                confidence = result.get("confidence", 0.75) if isinstance(result, dict) else 0.75
                aggregated_confidence += confidence

                runtime_result = RuntimeResult(
                    runtime_name=runtime_name,
                    success=True,
                    result=result,
                    confidence=confidence,
                    reasoning=result.get("reasoning", "") if isinstance(result, dict) else "",
                    execution_time_ms=execution_time_ms
                )

                results[runtime_name] = asdict(runtime_result)
                self.execution_history.append(runtime_result)

            except Exception as e:
                results[runtime_name] = {
                    "success": False,
                    "error": str(e)
                }

        # Aggregate results
        successful = sum(1 for r in results.values() if r.get("success"))
        avg_confidence = aggregated_confidence / max(successful, 1)

        return {
            "success": successful > 0,
            "task_id": task_context.task_id,
            "task_type": task_context.task_type.value,
            "runtimes_executed": len(selected_runtimes),
            "successful_runtimes": successful,
            "average_confidence": avg_confidence,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }

    def get_runtime_status(self) -> Dict[str, Any]:
        """Get status of all loaded runtimes"""
        status = {
            "total_runtimes": len(self.runtimes),
            "loaded": sum(1 for _, (_, inst) in self.runtimes.items() if inst is not None),
            "failed": sum(1 for _, (_, inst) in self.runtimes.items() if inst is None),
            "by_type": {},
            "selection_history_count": len(self.selection_history),
            "execution_history_count": len(self.execution_history)
        }

        # Count by runtime type
        for name, (metadata, _) in self.runtimes.items():
            rt_type = metadata.runtime_type.value
            if rt_type not in status["by_type"]:
                status["by_type"][rt_type] = {"total": 0, "loaded": 0}
            status["by_type"][rt_type]["total"] += 1
            if self.runtimes[name][1] is not None:
                status["by_type"][rt_type]["loaded"] += 1

        return status

    def save_execution_history(self):
        """Save execution history for learning and analysis"""
        history_file = LEARNING_DIR / f"runtime_executions_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        history_file.parent.mkdir(parents=True, exist_ok=True)

        with open(history_file, "a") as f:
            for result in self.execution_history:
                f.write(json.dumps(asdict(result)) + "\n")

    def save_selection_matrix(self):
        """Save the runtime selection matrix for analysis"""
        matrix_file = SEMANTIC_DIR / "runtime_selection_matrix.json"
        matrix_file.parent.mkdir(parents=True, exist_ok=True)

        matrix_dict = {
            task_type.value: runtimes
            for task_type, runtimes in self.selection_matrix.items()
        }

        with open(matrix_file, "w") as f:
            json.dump(matrix_dict, f, indent=2)


async def main():
    """Initialize and verify the cognitive runtime orchestrator"""
    print("=" * 70)
    print("PHASE 6: COGNITIVE RUNTIME ORCHESTRATOR INITIALIZATION")
    print("=" * 70)

    # Initialize orchestrator
    orchestrator = CognitiveRuntimeOrchestrator()

    # Display status
    status = orchestrator.get_runtime_status()
    print(f"\n✅ Runtime Status:")
    print(f"   Total Runtimes: {status['total_runtimes']}")
    print(f"   Loaded: {status['loaded']}")
    print(f"   Metadata Registered: {status['total_runtimes']}")

    print(f"\n📊 By Runtime Type:")
    for rt_type, counts in status["by_type"].items():
        print(f"   {rt_type}: {counts['loaded']}/{counts['total']} loaded")

    # Test runtime selection
    print(f"\n🧪 Testing Runtime Selection:")
    test_tasks = [
        TaskContext(
            task_id="test_001",
            task_type=TaskType.CODE_ANALYSIS,
            description="Analyze this Python function",
            context={}
        ),
        TaskContext(
            task_id="test_002",
            task_type=TaskType.CREATIVE_PROBLEM_SOLVING,
            description="Find creative solution",
            context={}
        ),
        TaskContext(
            task_id="test_003",
            task_type=TaskType.CONSCIOUSNESS_REFLECTION,
            description="Reflect on system awareness",
            context={}
        )
    ]

    for task in test_tasks:
        selected = orchestrator.select_optimal_runtimes(task)
        print(f"   {task.task_type.value}: {selected}")

    # Save configuration
    orchestrator.save_selection_matrix()

    print(f"\n✅ Phase 6 Initialization Complete")
    print(f"   Runtime orchestrator ready for integration")
    print(f"   Selection matrix saved for learning feedback")
    print(f"=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

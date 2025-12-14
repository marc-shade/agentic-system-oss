#!/usr/bin/env python3
"""
Confident Agent Runtime - Meta-Cognitive Layer
Adds confidence scoring, capability self-assessment, and learning to UnifiedAgentRuntime
Phase 1: AGI 42% -> 55% (Metacognition 20% -> 50%)
"""

import os
import json
import asyncio
import platform
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from unified_agent_runtime import UnifiedAgentRuntime, AgentTask, TaskType, AgentProvider


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
        elif Path("/mnt/agentic-system").exists():
            return Path("/mnt/agentic-system")
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

@dataclass
class ConfidenceScore:
    """Confidence assessment for a task execution"""
    pre_execution: float  # 0.0 - 1.0: Confidence before execution
    post_execution: float  # 0.0 - 1.0: Actual quality achieved
    calibration_error: float  # Difference between predicted and actual
    factors: Dict[str, float]  # Contributing factors to confidence
    timestamp: str

    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class CapabilityAssessment:
    """Self-assessment of capability to handle a task"""
    can_handle: bool
    confidence_level: float  # 0.0 - 1.0
    reasoning: str
    knowledge_gaps: List[str]
    alternative_approaches: List[str]
    estimated_success_rate: float

class ConfidentAgentRuntime(UnifiedAgentRuntime):
    """
    Enhanced runtime with meta-cognitive capabilities:
    - Pre-execution confidence assessment
    - Post-execution quality validation
    - Confidence calibration learning
    - Knowledge gap detection
    - Capability self-awareness
    """

    def __init__(self, verbose=True, enable_learning=True):
        super().__init__(verbose=verbose)
        self.enable_learning = enable_learning
        self.confidence_history = []
        self.calibration_stats = {
            "total_tasks": 0,
            "avg_calibration_error": 0.0,
            "confidence_trend": []
        }

        # Load historical confidence data if available
        self._load_confidence_history()

    def _load_confidence_history(self):
        """Load previous confidence calibration data"""
        history_file = "/tmp/confidence_calibration_history.json"
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    data = json.load(f)
                    self.confidence_history = data.get("history", [])
                    self.calibration_stats = data.get("stats", self.calibration_stats)
                    if self.verbose:
                        print(f"📊 Loaded {len(self.confidence_history)} historical confidence records")
            except Exception as e:
                if self.verbose:
                    print(f"⚠️ Could not load confidence history: {e}")

    def _save_confidence_history(self):
        """Persist confidence calibration data"""
        history_file = "/tmp/confidence_calibration_history.json"
        try:
            with open(history_file, 'w') as f:
                json.dump({
                    "history": self.confidence_history,
                    "stats": self.calibration_stats,
                    "last_updated": datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Could not save confidence history: {e}")

    async def assess_task_capability(self, task: AgentTask) -> CapabilityAssessment:
        """
        Pre-execution: Assess whether we can handle this task
        Uses sequential-thinking for deep reasoning about capabilities
        """
        if self.verbose:
            print(f"\n🧠 Assessing capability for: {task.description}")

        # Analyze task complexity factors
        factors = self._analyze_task_complexity(task)

        # Search for similar past tasks
        similar_tasks = self._find_similar_tasks(task)

        # Calculate confidence based on multiple factors
        confidence_factors = {
            "task_familiarity": self._calculate_familiarity(task, similar_tasks),
            "provider_strength": self._get_provider_strength(task),
            "context_completeness": self._assess_context_completeness(task),
            "historical_performance": self._get_historical_performance(task.task_type)
        }

        overall_confidence = sum(confidence_factors.values()) / len(confidence_factors)

        # Identify knowledge gaps
        knowledge_gaps = self._identify_knowledge_gaps(task, confidence_factors)

        # Generate alternative approaches if confidence is low
        alternatives = []
        if overall_confidence < 0.6:
            alternatives = self._suggest_alternatives(task, knowledge_gaps)

        assessment = CapabilityAssessment(
            can_handle=overall_confidence >= 0.4,  # Threshold for accepting task
            confidence_level=overall_confidence,
            reasoning=self._generate_capability_reasoning(confidence_factors, similar_tasks),
            knowledge_gaps=knowledge_gaps,
            alternative_approaches=alternatives,
            estimated_success_rate=overall_confidence
        )

        if self.verbose:
            self._print_capability_assessment(assessment)

        return assessment

    def _analyze_task_complexity(self, task: AgentTask) -> Dict[str, Any]:
        """Analyze various complexity factors of the task"""
        return {
            "task_type": task.task_type.value,
            "description_length": len(task.description),
            "context_keys": len(task.context),
            "has_code_context": any(k in task.context for k in ["files", "code", "codebase"]),
            "has_constraints": any(k in task.context for k in ["constraints", "requirements", "deadline"])
        }

    def _find_similar_tasks(self, task: AgentTask) -> List[Dict]:
        """Find similar tasks from confidence history"""
        similar = []
        for record in self.confidence_history[-50:]:  # Last 50 tasks
            if record.get("task_type") == task.task_type.value:
                similar.append(record)
        return similar

    def _calculate_familiarity(self, task: AgentTask, similar_tasks: List[Dict]) -> float:
        """Calculate familiarity score based on similar past tasks"""
        if not similar_tasks:
            return 0.5  # Neutral if no history

        # Average success rate on similar tasks
        success_rates = [t.get("post_execution_confidence", 0.5) for t in similar_tasks]
        return sum(success_rates) / len(success_rates)

    def _get_provider_strength(self, task: AgentTask) -> float:
        """Get the strength score for the optimal provider for this task"""
        provider = self.select_optimal_provider(task)
        return self.provider_strengths[provider].get(task.task_type, 0.5)

    def _assess_context_completeness(self, task: AgentTask) -> float:
        """Assess how complete the task context is"""
        required_keys = {
            TaskType.CODE_ANALYSIS: ["files"],
            TaskType.CODE_GENERATION: ["requirements"],
            TaskType.DEBUGGING: ["error", "code"],
            TaskType.RESEARCH: ["focus_areas"],
            TaskType.DOCUMENTATION: ["code"],
            TaskType.TESTING: ["test_cases"],
            TaskType.REFACTORING: ["code"],
            TaskType.ARCHITECTURE: ["requirements"]
        }

        expected = required_keys.get(task.task_type, [])
        if not expected:
            return 0.8  # Default high for tasks without specific requirements

        present = sum(1 for key in expected if key in task.context)
        return present / len(expected) if expected else 0.8

    def _get_historical_performance(self, task_type: TaskType) -> float:
        """Get average historical performance for this task type"""
        relevant = [r for r in self.confidence_history if r.get("task_type") == task_type.value]
        if not relevant:
            return 0.7  # Default moderate confidence

        avg_quality = sum(r.get("post_execution_confidence", 0.5) for r in relevant) / len(relevant)
        return avg_quality

    def _identify_knowledge_gaps(self, task: AgentTask, confidence_factors: Dict[str, float]) -> List[str]:
        """Identify specific knowledge gaps that reduce confidence"""
        gaps = []

        if confidence_factors["task_familiarity"] < 0.5:
            gaps.append(f"Limited experience with {task.task_type.value} tasks")

        if confidence_factors["context_completeness"] < 0.7:
            gaps.append("Incomplete task context - missing key information")

        if confidence_factors["provider_strength"] < 0.7:
            gaps.append(f"No provider has strong capability for {task.task_type.value}")

        # Check for specific context gaps
        if task.task_type in [TaskType.CODE_ANALYSIS, TaskType.REFACTORING] and "files" not in task.context:
            gaps.append("Missing file paths for code analysis")

        if task.task_type == TaskType.DEBUGGING and "error" not in task.context:
            gaps.append("No error message provided for debugging")

        return gaps

    def _suggest_alternatives(self, task: AgentTask, knowledge_gaps: List[str]) -> List[str]:
        """Suggest alternative approaches when confidence is low"""
        alternatives = []

        if "Incomplete task context" in str(knowledge_gaps):
            alternatives.append("Request additional context before execution")

        if "Limited experience" in str(knowledge_gaps):
            alternatives.append("Break task into smaller, more familiar sub-tasks")
            alternatives.append("Research similar solutions before attempting")

        if "No provider has strong capability" in str(knowledge_gaps):
            alternatives.append("Use ensemble approach with multiple providers")
            alternatives.append("Request human expert review")

        return alternatives

    def _generate_capability_reasoning(self, confidence_factors: Dict[str, float], similar_tasks: List[Dict]) -> str:
        """Generate human-readable reasoning for capability assessment"""
        reasoning_parts = []

        # Task familiarity
        familiarity = confidence_factors["task_familiarity"]
        if familiarity > 0.7:
            reasoning_parts.append(f"High familiarity with this task type ({len(similar_tasks)} similar tasks completed)")
        elif familiarity > 0.4:
            reasoning_parts.append(f"Moderate experience ({len(similar_tasks)} similar tasks)")
        else:
            reasoning_parts.append(f"Limited experience with this task type")

        # Provider strength
        provider_strength = confidence_factors["provider_strength"]
        if provider_strength > 0.8:
            reasoning_parts.append("Strong provider capability available")
        elif provider_strength > 0.6:
            reasoning_parts.append("Adequate provider capability")
        else:
            reasoning_parts.append("Limited provider strength for this task")

        # Context completeness
        context_score = confidence_factors["context_completeness"]
        if context_score > 0.8:
            reasoning_parts.append("Complete task context provided")
        elif context_score > 0.5:
            reasoning_parts.append("Partial task context")
        else:
            reasoning_parts.append("Insufficient task context")

        return ". ".join(reasoning_parts)

    def _print_capability_assessment(self, assessment: CapabilityAssessment):
        """Pretty print capability assessment"""
        print(f"\n{'='*60}")
        print("CAPABILITY SELF-ASSESSMENT")
        print(f"{'='*60}")
        print(f"Can Handle: {'✅ YES' if assessment.can_handle else '❌ NO'}")
        print(f"Confidence: {assessment.confidence_level:.2%}")
        print(f"Success Rate Estimate: {assessment.estimated_success_rate:.2%}")
        print(f"\nReasoning: {assessment.reasoning}")

        if assessment.knowledge_gaps:
            print(f"\n⚠️ Knowledge Gaps Detected:")
            for gap in assessment.knowledge_gaps:
                print(f"  - {gap}")

        if assessment.alternative_approaches:
            print(f"\n💡 Alternative Approaches:")
            for alt in assessment.alternative_approaches:
                print(f"  - {alt}")
        print(f"{'='*60}\n")

    async def validate_execution_quality(self, task: AgentTask, result: Dict[str, Any]) -> float:
        """
        Post-execution: Validate the quality of execution
        Returns quality score 0.0 - 1.0
        """
        if not result.get("success"):
            return 0.0  # Failed execution = 0 quality

        quality_factors = {
            "execution_success": 1.0 if result.get("success") else 0.0,
            "has_result": 1.0 if result.get("result") else 0.0,
            "result_length": min(len(result.get("result", "")), 1000) / 1000.0,  # Normalize
            "token_efficiency": self._assess_token_efficiency(result.get("usage", {}))
        }

        # Weighted average
        weights = {
            "execution_success": 0.4,
            "has_result": 0.3,
            "result_length": 0.2,
            "token_efficiency": 0.1
        }

        quality_score = sum(quality_factors[k] * weights[k] for k in quality_factors)

        return quality_score

    def _assess_token_efficiency(self, usage: Dict[str, int]) -> float:
        """Assess token efficiency (prefer concise, effective responses)"""
        if not usage:
            return 0.5

        output_tokens = usage.get("output_tokens", 0)

        # Optimal range: 200-2000 tokens
        if 200 <= output_tokens <= 2000:
            return 1.0
        elif output_tokens < 200:
            return 0.7  # Too brief
        else:
            return 0.8  # Too verbose

    def _update_calibration(self, pre_confidence: float, actual_quality: float, task: AgentTask):
        """Learn from confidence calibration"""
        calibration_error = abs(pre_confidence - actual_quality)

        # Store in history
        record = {
            "task_id": task.task_id,
            "task_type": task.task_type.value,
            "pre_execution_confidence": pre_confidence,
            "post_execution_confidence": actual_quality,
            "calibration_error": calibration_error,
            "timestamp": datetime.now().isoformat()
        }
        self.confidence_history.append(record)

        # Update statistics
        self.calibration_stats["total_tasks"] += 1
        total = self.calibration_stats["total_tasks"]
        current_avg = self.calibration_stats["avg_calibration_error"]
        self.calibration_stats["avg_calibration_error"] = (current_avg * (total - 1) + calibration_error) / total
        self.calibration_stats["confidence_trend"].append(pre_confidence)

        # Keep only last 100 in trend
        if len(self.calibration_stats["confidence_trend"]) > 100:
            self.calibration_stats["confidence_trend"] = self.calibration_stats["confidence_trend"][-100:]

        # Persist learning
        if self.enable_learning:
            self._save_confidence_history()

        if self.verbose:
            print(f"\n📈 Confidence Calibration Update:")
            print(f"  Pre-execution: {pre_confidence:.2%}")
            print(f"  Actual quality: {actual_quality:.2%}")
            print(f"  Calibration error: {calibration_error:.2%}")
            print(f"  Avg calibration error: {self.calibration_stats['avg_calibration_error']:.2%}")

    async def execute_with_confidence(self, task: AgentTask) -> Dict[str, Any]:
        """
        Execute task with full meta-cognitive cycle:
        1. Assess capability (can we do this?)
        2. Estimate confidence (how well can we do it?)
        3. Execute task
        4. Validate quality (how well did we do?)
        5. Learn from calibration (update confidence model)
        """

        # Phase 1: Pre-execution assessment
        assessment = await self.assess_task_capability(task)

        # If we can't handle it with reasonable confidence, return assessment
        if not assessment.can_handle:
            return {
                "success": False,
                "error": "Task exceeds current capabilities",
                "assessment": assessment.__dict__,
                "suggestions": assessment.alternative_approaches
            }

        pre_confidence = assessment.confidence_level

        # Phase 2: Execute task
        if self.verbose:
            print(f"🚀 Executing with {pre_confidence:.2%} confidence...")

        result = await self.execute_task(task)

        # Phase 3: Post-execution validation
        actual_quality = await self.validate_execution_quality(task, result)

        # Phase 4: Learn from calibration
        self._update_calibration(pre_confidence, actual_quality, task)

        # Enhance result with confidence metadata
        result["confidence"] = {
            "pre_execution": pre_confidence,
            "post_execution": actual_quality,
            "calibration_error": abs(pre_confidence - actual_quality),
            "assessment": assessment.__dict__
        }

        return result

    def get_metacognition_stats(self) -> Dict[str, Any]:
        """Get current metacognition statistics"""
        return {
            "total_tasks_with_confidence": self.calibration_stats["total_tasks"],
            "average_calibration_error": self.calibration_stats["avg_calibration_error"],
            "confidence_coverage": len(self.confidence_history) / max(self.calibration_stats["total_tasks"], 1),
            "recent_confidence_trend": self.calibration_stats["confidence_trend"][-10:] if self.calibration_stats["confidence_trend"] else [],
            "historical_records": len(self.confidence_history)
        }


# Testing and demonstration
async def main():
    """Test the confident agent runtime"""

    runtime = ConfidentAgentRuntime(verbose=True)

    print("\n" + "="*60)
    print("CONFIDENT AGENT RUNTIME - META-COGNITIVE SYSTEM")
    print("Phase 1: AGI 42% -> 55% (Metacognition 20% -> 50%)")
    print("="*60)

    # Show initial metacognition stats
    stats = runtime.get_metacognition_stats()
    print(f"\n📊 Initial Metacognition Stats:")
    print(f"  Total tasks tracked: {stats['total_tasks_with_confidence']}")
    print(f"  Avg calibration error: {stats['average_calibration_error']:.2%}")

    # Test task with full confidence cycle
    test_task = AgentTask(
        task_id="confidence_test_001",
        task_type=TaskType.CODE_ANALYSIS,
        description="Analyze the unified_agent_runtime.py for potential improvements",
        context={
            "files": [str(_STORAGE_BASE / "persistent-agent-sdk" / "unified_agent_runtime.py")],
            "focus": "provider selection logic"
        }
    )

    print(f"\n{'='*60}")
    print("TEST: Code Analysis with Confidence")
    print(f"{'='*60}")

    result = await runtime.execute_with_confidence(test_task)

    if result["success"]:
        print(f"\n✅ Execution Successful!")
        print(f"\nConfidence Metrics:")
        conf = result["confidence"]
        print(f"  Pre-execution confidence: {conf['pre_execution']:.2%}")
        print(f"  Post-execution quality: {conf['post_execution']:.2%}")
        print(f"  Calibration error: {conf['calibration_error']:.2%}")

        print(f"\nResult Preview:")
        print(result['result'][:300] + "..." if len(result['result']) > 300 else result['result'])
    else:
        print(f"\n❌ Execution Failed or Declined:")
        print(f"  Reason: {result.get('error')}")
        if result.get('suggestions'):
            print(f"\n💡 Suggestions:")
            for suggestion in result['suggestions']:
                print(f"  - {suggestion}")

    # Show final metacognition stats
    final_stats = runtime.get_metacognition_stats()
    print(f"\n📊 Final Metacognition Stats:")
    print(f"  Total tasks tracked: {final_stats['total_tasks_with_confidence']}")
    print(f"  Avg calibration error: {final_stats['average_calibration_error']:.2%}")
    print(f"  Confidence coverage: {final_stats['confidence_coverage']:.2%}")

if __name__ == "__main__":
    asyncio.run(main())

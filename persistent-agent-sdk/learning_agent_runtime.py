#!/usr/bin/env python3
"""
Learning Agent Runtime - Comprehensive Feedback Loop System
Learns from every execution and continuously improves performance
Phase 2.2: Adaptive learning and model updates
"""

import os
import json
import asyncio
import platform
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from evolving_agent_runtime import EvolvingAgentRuntime
from unified_agent_runtime import AgentTask, TaskType, AgentProvider


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
class FeedbackSignal:
    """Feedback signals collected from task execution"""
    task_id: str
    task_type: str
    provider_used: str
    success: bool
    confidence_accuracy: float  # How accurate was our confidence?
    cost_efficiency: float      # Cost per unit quality
    time_efficiency: float      # Time per unit quality
    quality_score: float        # Overall quality
    timestamp: str

    def to_dict(self) -> Dict:
        return asdict(self)

class LearningAgentRuntime(EvolvingAgentRuntime):
    """
    Self-learning runtime that improves through continuous feedback:
    - Collects feedback signals from every execution
    - Updates provider strength models
    - Refines confidence calibration
    - Optimizes cost and time models
    - Adapts routing decisions based on performance
    """

    def __init__(self, verbose=True, enable_learning=True, evolution_enabled=True):
        super().__init__(
            verbose=verbose,
            enable_learning=enable_learning,
            evolution_enabled=evolution_enabled
        )
        self.feedback_history = []
        self.performance_models = self._initialize_performance_models()

        # Load feedback history
        self._load_feedback_history()

    def _initialize_performance_models(self) -> Dict[str, Any]:
        """Initialize models that will be updated through learning"""
        return {
            "provider_performance": {
                AgentProvider.CLAUDE_CODE.value: {"success_rate": 1.0, "avg_quality": 0.9, "tasks": 0},
                AgentProvider.OPENAI_CODEX.value: {"success_rate": 1.0, "avg_quality": 0.85, "tasks": 0},
                AgentProvider.GEMINI_CLI.value: {"success_rate": 1.0, "avg_quality": 0.8, "tasks": 0}
            },
            "task_type_difficulty": {
                task_type.value: {"avg_confidence": 0.7, "success_rate": 1.0, "tasks": 0}
                for task_type in TaskType
            },
            "cost_model": {
                "claude_code": {"cost_per_quality": 0.01, "samples": 0},
                "openai_codex": {"cost_per_quality": 0.008, "samples": 0},
                "gemini_cli": {"cost_per_quality": 0.001, "samples": 0}
            }
        }

    def _load_feedback_history(self):
        """Load previous feedback data"""
        history_file = "/tmp/feedback_learning_history.json"
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    data = json.load(f)
                    self.feedback_history = data.get("history", [])
                    self.performance_models = data.get("models", self.performance_models)
                    if self.verbose:
                        print(f"📚 Loaded {len(self.feedback_history)} feedback records")
            except Exception as e:
                if self.verbose:
                    print(f"⚠️ Could not load feedback history: {e}")

    def _save_feedback_history(self):
        """Persist feedback and learned models"""
        history_file = "/tmp/feedback_learning_history.json"
        try:
            with open(history_file, 'w') as f:
                json.dump({
                    "history": self.feedback_history,
                    "models": self.performance_models,
                    "last_updated": datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Could not save feedback history: {e}")

    async def _collect_feedback_signals(self, task: AgentTask, result: Dict[str, Any]) -> FeedbackSignal:
        """
        Collect comprehensive feedback signals from execution
        These signals drive all learning and adaptation
        """
        # Extract confidence metrics
        confidence_data = result.get("confidence", {})
        pre_confidence = confidence_data.get("pre_execution", 0.5)
        post_quality = confidence_data.get("post_execution", 0.5)
        calibration_error = confidence_data.get("calibration_error", 0.5)

        # Calculate confidence accuracy (inverse of calibration error)
        confidence_accuracy = 1.0 - min(calibration_error, 1.0)

        # Calculate cost efficiency
        usage = result.get("usage", {})
        total_tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

        # Rough cost estimates (per million tokens)
        cost_per_million = {
            "claude_code": 15.0,  # $15 per 1M tokens (output)
            "openai_codex": 10.0,  # $10 per 1M tokens
            "gemini_cli": 1.0      # $1 per 1M tokens
        }

        provider = result.get("provider", "unknown")
        estimated_cost = (total_tokens / 1_000_000) * cost_per_million.get(provider, 10.0)
        cost_efficiency = post_quality / max(estimated_cost, 0.0001)  # Quality per dollar

        # Calculate time efficiency (if duration available)
        duration = result.get("duration", 10.0)  # Default 10s
        time_efficiency = post_quality / max(duration, 0.1)  # Quality per second

        feedback = FeedbackSignal(
            task_id=task.task_id,
            task_type=task.task_type.value,
            provider_used=provider,
            success=result.get("success", False),
            confidence_accuracy=confidence_accuracy,
            cost_efficiency=cost_efficiency,
            time_efficiency=time_efficiency,
            quality_score=post_quality,
            timestamp=datetime.now().isoformat()
        )

        return feedback

    def _update_provider_strengths(self, feedback: FeedbackSignal):
        """
        Update provider strength matrix based on actual performance
        This improves future provider selection decisions
        """
        provider = feedback.provider_used
        task_type = feedback.task_type

        if provider not in self.performance_models["provider_performance"]:
            return

        # Update provider performance model
        model = self.performance_models["provider_performance"][provider]
        tasks = model["tasks"]
        new_tasks = tasks + 1

        # Running average of success rate
        current_success = 1.0 if feedback.success else 0.0
        model["success_rate"] = (model["success_rate"] * tasks + current_success) / new_tasks

        # Running average of quality
        model["avg_quality"] = (model["avg_quality"] * tasks + feedback.quality_score) / new_tasks
        model["tasks"] = new_tasks

        # Update provider strengths matrix for this task type
        # Adjust strength based on observed quality
        for prov_enum in self.provider_strengths:
            if prov_enum.value == provider:
                current_strength = self.provider_strengths[prov_enum].get(TaskType(task_type), 0.5)
                # Adaptive learning rate: 0.1 (10% weight to new observation)
                learning_rate = 0.1
                new_strength = current_strength * (1 - learning_rate) + feedback.quality_score * learning_rate
                self.provider_strengths[prov_enum][TaskType(task_type)] = new_strength

                if self.verbose:
                    print(f"  📈 Updated {provider} strength for {task_type}: {current_strength:.3f} → {new_strength:.3f}")

    def _update_confidence_model(self, feedback: FeedbackSignal):
        """
        Update confidence calibration based on accuracy
        Improves future confidence predictions
        """
        task_type = feedback.task_type

        if task_type not in self.performance_models["task_type_difficulty"]:
            return

        model = self.performance_models["task_type_difficulty"][task_type]
        tasks = model["tasks"]
        new_tasks = tasks + 1

        # Update average confidence for this task type
        # High confidence accuracy means we can be more confident in future
        model["avg_confidence"] = (model["avg_confidence"] * tasks + feedback.confidence_accuracy) / new_tasks
        model["success_rate"] = (model["success_rate"] * tasks + (1.0 if feedback.success else 0.0)) / new_tasks
        model["tasks"] = new_tasks

    def _update_cost_model(self, feedback: FeedbackSignal):
        """
        Update cost efficiency models
        Helps optimize for cost vs quality tradeoffs
        """
        provider = feedback.provider_used

        if provider not in self.performance_models["cost_model"]:
            return

        model = self.performance_models["cost_model"][provider]
        samples = model["samples"]
        new_samples = samples + 1

        # Running average of cost per quality
        model["cost_per_quality"] = (model["cost_per_quality"] * samples + (1.0 / max(feedback.cost_efficiency, 0.0001))) / new_samples
        model["samples"] = new_samples

    async def execute_with_learning(self, task: AgentTask) -> Dict[str, Any]:
        """
        Execute task with full learning cycle:
        1. Execute (with evolution if enabled)
        2. Collect feedback signals
        3. Update all models (provider, confidence, cost)
        4. Store learning for future sessions
        """
        if self.verbose:
            print(f"\n{'='*60}")
            print("LEARNING EXECUTION CYCLE")
            print(f"{'='*60}")

        # Phase 1: Execute with evolution
        start_time = datetime.now()

        if self.evolution_enabled:
            result = await self.execute_with_evolution(task)
        else:
            result = await self.execute_with_memory(task)

        duration = (datetime.now() - start_time).total_seconds()
        result["duration"] = duration

        # Phase 2: Collect feedback
        if self.verbose:
            print(f"\n📊 Collecting Feedback Signals...")

        feedback = await self._collect_feedback_signals(task, result)

        if self.verbose:
            print(f"  Success: {feedback.success}")
            print(f"  Quality: {feedback.quality_score:.3f}")
            print(f"  Confidence accuracy: {feedback.confidence_accuracy:.3f}")
            print(f"  Cost efficiency: {feedback.cost_efficiency:.3f}")
            print(f"  Time efficiency: {feedback.time_efficiency:.3f}")

        # Phase 3: Update models
        if self.enable_learning:
            if self.verbose:
                print(f"\n🧠 Updating Performance Models...")

            self._update_provider_strengths(feedback)
            self._update_confidence_model(feedback)
            self._update_cost_model(feedback)

            # Store feedback
            self.feedback_history.append(feedback.to_dict())

            # Persist learning
            self._save_feedback_history()

        # Add learning metadata to result
        result["learning"] = {
            "feedback_collected": True,
            "models_updated": self.enable_learning,
            "feedback_history_size": len(self.feedback_history),
            "confidence_accuracy": feedback.confidence_accuracy,
            "cost_efficiency": feedback.cost_efficiency
        }

        return result

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get comprehensive learning statistics"""
        if not self.feedback_history:
            return {
                "total_feedback_signals": 0,
                "avg_confidence_accuracy": 0.0,
                "avg_quality": 0.0,
                "provider_performance": self.performance_models["provider_performance"],
                "learning_enabled": self.enable_learning
            }

        # Calculate averages from feedback
        total = len(self.feedback_history)
        avg_confidence_accuracy = sum(f["confidence_accuracy"] for f in self.feedback_history) / total
        avg_quality = sum(f["quality_score"] for f in self.feedback_history) / total
        success_rate = sum(1 for f in self.feedback_history if f["success"]) / total

        # Provider performance comparison
        provider_stats = {}
        for provider in self.performance_models["provider_performance"]:
            model = self.performance_models["provider_performance"][provider]
            if model["tasks"] > 0:
                provider_stats[provider] = {
                    "tasks": model["tasks"],
                    "success_rate": model["success_rate"],
                    "avg_quality": model["avg_quality"]
                }

        return {
            "total_feedback_signals": total,
            "avg_confidence_accuracy": avg_confidence_accuracy,
            "avg_quality": avg_quality,
            "success_rate": success_rate,
            "provider_performance": provider_stats,
            "learning_enabled": self.enable_learning,
            "improvement_trend": self._calculate_improvement_trend()
        }

    def _calculate_improvement_trend(self) -> Dict[str, float]:
        """Calculate improvement over time"""
        if len(self.feedback_history) < 10:
            return {"quality_improvement": 0.0, "confidence_improvement": 0.0}

        # Compare first 10 vs last 10 feedback signals
        first_10 = self.feedback_history[:10]
        last_10 = self.feedback_history[-10:]

        first_quality = sum(f["quality_score"] for f in first_10) / len(first_10)
        last_quality = sum(f["quality_score"] for f in last_10) / len(last_10)

        first_confidence = sum(f["confidence_accuracy"] for f in first_10) / len(first_10)
        last_confidence = sum(f["confidence_accuracy"] for f in last_10) / len(last_10)

        return {
            "quality_improvement": ((last_quality - first_quality) / max(first_quality, 0.01)) * 100,
            "confidence_improvement": ((last_confidence - first_confidence) / max(first_confidence, 0.01)) * 100
        }


# Testing and demonstration
async def main():
    """Test the learning agent runtime"""

    runtime = LearningAgentRuntime(verbose=True, evolution_enabled=False)  # Disable evolution for faster test

    print("\n" + "="*60)
    print("LEARNING AGENT RUNTIME - FEEDBACK LOOP SYSTEM")
    print("Phase 2.2: Continuous learning and adaptation")
    print("="*60)

    # Show initial statistics
    learning_stats = runtime.get_learning_stats()
    print(f"\n📊 Initial Learning Statistics:")
    print(f"  Feedback signals: {learning_stats['total_feedback_signals']}")
    print(f"  Avg quality: {learning_stats['avg_quality']:.3f}")
    print(f"  Learning enabled: {learning_stats['learning_enabled']}")

    # Test with code analysis task
    test_task = AgentTask(
        task_id="learning_test_001",
        task_type=TaskType.CODE_ANALYSIS,
        description="Analyze the unified_agent_runtime.py provider selection logic",
        context={
            "files": [str(_STORAGE_BASE / "persistent-agent-sdk" / "unified_agent_runtime.py")]
        }
    )

    print(f"\n{'='*60}")
    print("TEST: Learning Execution with Feedback Loop")
    print(f"{'='*60}")

    result = await runtime.execute_with_learning(test_task)

    if result.get("success"):
        print(f"\n✅ Execution Successful!")

        # Show learning results
        if "learning" in result:
            learn = result["learning"]
            print(f"\nLearning Metrics:")
            print(f"  Feedback collected: {learn['feedback_collected']}")
            print(f"  Models updated: {learn['models_updated']}")
            print(f"  Confidence accuracy: {learn['confidence_accuracy']:.3f}")
            print(f"  Cost efficiency: {learn['cost_efficiency']:.3f}")

    # Show final learning statistics
    final_learning_stats = runtime.get_learning_stats()
    print(f"\n📊 Final Learning Statistics:")
    print(f"  Total feedback signals: {final_learning_stats['total_feedback_signals']}")
    print(f"  Avg confidence accuracy: {final_learning_stats['avg_confidence_accuracy']:.3f}")
    print(f"  Avg quality: {final_learning_stats['avg_quality']:.3f}")
    print(f"  Success rate: {final_learning_stats.get('success_rate', 0.0):.3f}")

    if final_learning_stats.get('provider_performance'):
        print(f"\n  Provider Performance:")
        for provider, stats in final_learning_stats['provider_performance'].items():
            print(f"    {provider}: {stats['tasks']} tasks, {stats['avg_quality']:.3f} quality")

    print(f"\n{'='*60}")
    print("PHASE 2 PRIORITY 2: FEEDBACK LOOP COMPLETE")
    print("System learns from every execution")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())

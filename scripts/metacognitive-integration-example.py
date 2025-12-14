#!/usr/bin/env python3
"""
Metacognitive Monitor Integration Example

Demonstrates how to integrate metacognitive monitoring into AGI workflows.
Shows TRAP framework usage and failure prediction in realistic scenarios.

Usage:
    python metacognitive-integration-example.py
"""

import sys
import time
from pathlib import Path

# Import from the same directory
import importlib.util
spec = importlib.util.spec_from_file_location(
    "metacognitive_monitor",
    Path(__file__).parent / "metacognitive-monitor.py"
)
metacog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metacog)

MetacognitiveMonitor = metacog.MetacognitiveMonitor
TaskComplexity = metacog.TaskComplexity
TRAPEvaluator = metacog.TRAPEvaluator


def example_code_generation_with_monitoring():
    """
    Example: Monitor code generation task with TRAP framework
    """
    print("=" * 80)
    print("EXAMPLE 1: Code Generation with Metacognitive Monitoring")
    print("=" * 80)

    monitor = MetacognitiveMonitor()
    trap_eval = TRAPEvaluator()

    task_id = "code_gen_001"
    start_time = time.time()

    # Reasoning trace
    reasoning = []

    # Step 1: Analyze requirements
    print("\n[Step 1] Analyzing requirements...")
    reasoning.append("Analyzed user requirements: Create REST API endpoint")
    trap_eval.record_reasoning_checkpoint(
        "Requirements analyzed, identified REST API pattern",
        depth_level=1
    )

    # Step 2: Consider approach
    print("[Step 2] Considering approach...")
    reasoning.append("Considering Flask vs FastAPI - choosing FastAPI for async support")
    trap_eval.record_reasoning_checkpoint(
        "Evaluated framework options based on async requirements",
        depth_level=2
    )

    # Step 3: Detect potential issue
    print("[Step 3] Initial implementation...")
    reasoning.append("Started implementation, realized validation logic missing")

    # Adaptation: Strategy change
    print("[Step 3a] Adapting strategy...")
    trap_eval.record_adaptation(
        old_strategy="direct_implementation",
        new_strategy="validation_first_approach",
        trigger="missing_validation_logic"
    )
    reasoning.append("Adapted: Adding Pydantic models for validation first")

    # Step 4: Implementation
    print("[Step 4] Implementing with validation...")
    reasoning.append("Implemented endpoint with proper validation and error handling")

    # Step 5: Confidence prediction
    print("[Step 5] Self-assessment...")
    predicted_confidence = 0.85
    reasoning.append(f"Self-assessment: {predicted_confidence} confidence in solution")

    # Record metacognitive state
    elapsed_ms = int((time.time() - start_time) * 1000)

    state = monitor.record_state(
        task_id=task_id,
        task_type="code_generation",
        complexity=TaskComplexity.COMPLEX,
        confidence=predicted_confidence,
        reasoning_trace=reasoning,
        current_strategy="validation_first_approach",
        cognitive_load=0.6,
        self_awareness=0.8,  # High: Aware of decision points
        knowledge_awareness=0.7,  # Good: Know FastAPI and validation
        process_awareness=0.75,  # Good: Understood need for adaptation
        limitation_awareness=0.65  # Moderate: Aware of validation gap
    )

    print(f"\n✓ Task completed in {elapsed_ms}ms")
    print(f"\nTRAP Metrics:")
    print(f"  Transparency: {state.trap_metrics.transparency_score:.2f}")
    print(f"  Reasoning Depth: {state.trap_metrics.reasoning_depth}")
    print(f"  Adaptations: {state.trap_metrics.adaptation_count}")
    print(f"  Perception Accuracy: {state.trap_metrics.perception_accuracy:.2f}")

    # Check for failure predictions
    predictions = monitor.predict_failure(
        task_id=task_id,
        duration_ms=elapsed_ms,
        complexity=TaskComplexity.COMPLEX,
        confidence=predicted_confidence
    )

    if predictions:
        print(f"\n⚠ Warning: {len(predictions)} failure prediction(s)")
        for pred in predictions:
            print(f"  - {pred.trigger_type.value}: {pred.reason}")
    else:
        print("\n✓ No failure triggers detected")

    # Record action outcome
    monitor.record_action(
        action_id="action_001",
        action_type="code_generation",
        task_id=task_id,
        duration_ms=elapsed_ms,
        confidence=predicted_confidence,
        success=True
    )

    # Update perception accuracy with actual result
    actual_success = 0.9  # Simulated actual quality score
    trap_eval.record_confidence_prediction(
        predicted=predicted_confidence,
        actual=actual_success
    )

    print(f"\nActual quality: {actual_success:.2f} (predicted: {predicted_confidence:.2f})")
    print(f"Prediction error: {abs(actual_success - predicted_confidence):.2f}")


def example_failure_prediction():
    """
    Example: Detect failure through multiple triggers
    """
    print("\n\n" + "=" * 80)
    print("EXAMPLE 2: Failure Prediction - Stuck State Detection")
    print("=" * 80)

    monitor = MetacognitiveMonitor()

    task_id = "debug_002"

    # Simulate repeated failed attempts
    print("\n[Attempt 1] Trying approach A...")
    monitor.record_action(
        action_id="action_101",
        action_type="debugging",
        task_id=task_id,
        duration_ms=8000,
        confidence=0.7,
        success=False
    )

    print("[Attempt 2] Trying approach A again...")
    monitor.record_action(
        action_id="action_102",
        action_type="debugging",
        task_id=task_id,
        duration_ms=9000,
        confidence=0.65,
        success=False
    )

    print("[Attempt 3] Still trying approach A...")
    monitor.record_action(
        action_id="action_103",
        action_type="debugging",
        task_id=task_id,
        duration_ms=10000,
        confidence=0.6,
        success=False
    )

    # Add progress markers showing stagnation
    monitor.failure_predictor.add_progress_marker(0.2)
    monitor.failure_predictor.add_progress_marker(0.21)
    monitor.failure_predictor.add_progress_marker(0.22)
    monitor.failure_predictor.add_progress_marker(0.21)
    monitor.failure_predictor.add_progress_marker(0.22)

    print("\n[Checking for failure indicators...]")

    # Check predictions
    predictions = monitor.predict_failure(
        task_id=task_id,
        duration_ms=27000,  # Total time across attempts
        complexity=TaskComplexity.MODERATE,
        confidence=0.6
    )

    if predictions:
        print(f"\n⚠ FAILURE PREDICTIONS TRIGGERED ({len(predictions)}):\n")
        for pred in predictions:
            print(f"Trigger: {pred.trigger_type.value}")
            print(f"Confidence: {pred.confidence:.2f}")
            print(f"Reason: {pred.reason}")
            print(f"Recommended Action: {pred.recommended_action}")
            print()

    # Show corrective action
    print("Taking corrective action based on predictions...")
    print("→ Switching to alternative debugging strategy")
    print("→ Requesting human guidance on approach")


def example_awareness_tracking():
    """
    Example: Track metacognitive awareness over learning curve
    """
    print("\n\n" + "=" * 80)
    print("EXAMPLE 3: Metacognitive Awareness Evolution")
    print("=" * 80)

    monitor = MetacognitiveMonitor()

    # Simulate learning progression over multiple tasks
    tasks = [
        # Early: Low awareness, learning new framework
        {
            'task_id': 'learn_001',
            'task_type': 'learning_pytorch',
            'complexity': TaskComplexity.NOVEL,
            'self_awareness': 0.4,
            'knowledge_awareness': 0.3,  # Low: Don't know what I don't know
            'process_awareness': 0.5,
            'limitation_awareness': 0.6,  # High: Very aware of limitations
            'confidence': 0.4
        },
        # Middle: Improving awareness as patterns emerge
        {
            'task_id': 'learn_002',
            'task_type': 'learning_pytorch',
            'complexity': TaskComplexity.COMPLEX,
            'self_awareness': 0.6,
            'knowledge_awareness': 0.5,  # Better: Understanding scope
            'process_awareness': 0.6,
            'limitation_awareness': 0.7,
            'confidence': 0.6
        },
        # Advanced: High awareness, competent
        {
            'task_id': 'learn_003',
            'task_type': 'learning_pytorch',
            'complexity': TaskComplexity.MODERATE,
            'self_awareness': 0.8,
            'knowledge_awareness': 0.75,  # Good: Know what I know
            'process_awareness': 0.8,
            'limitation_awareness': 0.7,
            'confidence': 0.8
        }
    ]

    print("\nTracking awareness evolution across learning curve:\n")

    for i, task in enumerate(tasks, 1):
        print(f"Task {i}: {task['task_id']}")

        state = monitor.record_state(
            task_id=task['task_id'],
            task_type=task['task_type'],
            complexity=task['complexity'],
            confidence=task['confidence'],
            reasoning_trace=[f"Step {j}" for j in range(3)],
            current_strategy="learning_by_doing",
            self_awareness=task['self_awareness'],
            knowledge_awareness=task['knowledge_awareness'],
            process_awareness=task['process_awareness'],
            limitation_awareness=task['limitation_awareness']
        )

        print(f"  Self-Awareness: {state.self_awareness:.2f}")
        print(f"  Knowledge-Awareness: {state.knowledge_awareness:.2f}")
        print(f"  Process-Awareness: {state.process_awareness:.2f}")
        print(f"  Limitation-Awareness: {state.limitation_awareness:.2f}")
        print(f"  Confidence: {state.confidence_level:.2f}")
        print()

    print("Observation: Knowledge-awareness improved from 0.30 → 0.75")
    print("This indicates progression from 'don't know what I don't know'")
    print("to 'know what I know' - a key metacognitive milestone!")


def main():
    """Run all examples"""
    print("\n" + "=" * 80)
    print(" METACOGNITIVE MONITORING SYSTEM - INTEGRATION EXAMPLES")
    print("=" * 80)

    try:
        # Example 1: TRAP framework in code generation
        example_code_generation_with_monitoring()

        # Example 2: Failure prediction
        example_failure_prediction()

        # Example 3: Awareness tracking
        example_awareness_tracking()

        print("\n\n" + "=" * 80)
        print(" EXAMPLES COMPLETED")
        print("=" * 80)
        print("\nMetrics stored in: /tmp/metacognitive/")
        print("  - metacognitive_states.jsonl")
        print("  - action_records.jsonl")
        print("  - failure_predictions.jsonl")
        print("\nTo analyze:")
        print("  python metacognitive-monitor.py analyze --days 1")
        print("\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())

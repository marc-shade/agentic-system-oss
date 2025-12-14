#!/usr/bin/env python3
"""
Comprehensive Integration Test for Metacognitive Monitor

Tests all functionality including:
- Normal execution
- High latency detection
- Low confidence detection
- Repetitive action detection
- TRAP metrics evaluation
- Enhanced memory integration
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Add the scripts directory to path
sys.path.insert(0, '/mnt/agentic-system/scripts')

from metacognitive_monitor import (
    MetacognitiveMonitor,
    TaskComplexity,
    FailureTrigger,
    TRAPEvaluator
)


class TestResults:
    """Track test results"""
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0

    def add_result(self, name: str, passed: bool, details: str = ""):
        self.tests.append({
            'name': name,
            'passed': passed,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
        if passed:
            self.passed += 1
            print(f"✓ PASS: {name}")
        else:
            self.failed += 1
            print(f"✗ FAIL: {name}")
        if details:
            print(f"  Details: {details}")

    def summary(self):
        total = self.passed + self.failed
        success_rate = (self.passed / total * 100) if total > 0 else 0

        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Total Tests: {total}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Success Rate: {success_rate:.1f}%")
        print("="*70)

        return self.failed == 0


def test_normal_execution(monitor: MetacognitiveMonitor, results: TestResults):
    """Test normal task execution (should pass all checks)"""
    print("\n[Test 1] Normal Execution")
    print("-" * 50)

    task_id = "test_normal_001"

    # Record state with good metrics
    state = monitor.record_state(
        task_id=task_id,
        task_type="code_generation",
        complexity=TaskComplexity.MODERATE,
        confidence=0.85,
        reasoning_trace=[
            "Analyzed requirements",
            "Considered multiple approaches",
            "Chose optimal strategy because of efficiency",
            "Therefore implementing iterative solution",
            "Validated against constraints"
        ],
        current_strategy="iterative_refinement",
        cognitive_load=0.6,
        self_awareness=0.8,
        knowledge_awareness=0.75,
        process_awareness=0.7,
        limitation_awareness=0.65
    )

    # Verify state was recorded
    results.add_result(
        "Normal state recording",
        state is not None,
        f"Recorded state with confidence {state.confidence_level}"
    )

    # Record successful action
    action = monitor.record_action(
        action_id="action_001",
        action_type="code_modification",
        task_id=task_id,
        duration_ms=3000,  # 3 seconds - well within threshold
        confidence=0.85,
        success=True
    )

    results.add_result(
        "Normal action recording",
        action.success is True,
        f"Action completed in {action.duration_ms}ms"
    )

    # Run failure prediction (should have no triggers)
    predictions = monitor.predict_failure(
        task_id=task_id,
        duration_ms=3000,
        complexity=TaskComplexity.MODERATE,
        confidence=0.85
    )

    results.add_result(
        "Normal execution - no failure triggers",
        len(predictions) == 0,
        f"Predictions: {len(predictions)}"
    )

    # Check TRAP metrics are reasonable
    trap = state.trap_metrics
    results.add_result(
        "TRAP metrics computed",
        trap.transparency_score > 0.5 and trap.perception_accuracy > 0,
        f"Transparency: {trap.transparency_score:.2f}, Perception: {trap.perception_accuracy:.2f}"
    )


def test_high_latency(monitor: MetacognitiveMonitor, results: TestResults):
    """Test high latency detection (should trigger warning)"""
    print("\n[Test 2] High Latency Detection")
    print("-" * 50)

    task_id = "test_latency_001"

    # Record action with excessive duration for MODERATE complexity
    # Threshold is 15 seconds = 15000ms
    excessive_duration = 20000  # 20 seconds

    action = monitor.record_action(
        action_id="action_latency_001",
        action_type="database_query",
        task_id=task_id,
        duration_ms=excessive_duration,
        confidence=0.7,
        success=True
    )

    # Predict failure (should trigger LATENCY_EXCEEDED)
    predictions = monitor.predict_failure(
        task_id=task_id,
        duration_ms=excessive_duration,
        complexity=TaskComplexity.MODERATE,
        confidence=0.7
    )

    latency_triggered = any(
        p.trigger_type == FailureTrigger.LATENCY_EXCEEDED
        for p in predictions
    )

    results.add_result(
        "High latency detection",
        latency_triggered,
        f"Duration {excessive_duration}ms > threshold 15000ms"
    )

    if predictions:
        for pred in predictions:
            print(f"  Trigger: {pred.trigger_type.value}")
            print(f"  Reason: {pred.reason}")
            print(f"  Recommendation: {pred.recommended_action}")


def test_low_confidence(monitor: MetacognitiveMonitor, results: TestResults):
    """Test low confidence detection (should trigger warning)"""
    print("\n[Test 3] Low Confidence Detection")
    print("-" * 50)

    task_id = "test_confidence_001"

    low_confidence = 0.3  # Below threshold of 0.5

    # Record state with low confidence
    state = monitor.record_state(
        task_id=task_id,
        task_type="novel_task",
        complexity=TaskComplexity.NOVEL,
        confidence=low_confidence,
        reasoning_trace=["Uncertain about approach", "Multiple unknowns"],
        current_strategy="exploratory",
        cognitive_load=0.9,  # High load due to uncertainty
        self_awareness=0.6,
        knowledge_awareness=0.4,  # Low - don't know much
        process_awareness=0.5,
        limitation_awareness=0.7  # Aware of limitations
    )

    # Predict failure
    predictions = monitor.predict_failure(
        task_id=task_id,
        duration_ms=5000,
        complexity=TaskComplexity.NOVEL,
        confidence=low_confidence
    )

    confidence_triggered = any(
        p.trigger_type == FailureTrigger.LOW_CONFIDENCE
        for p in predictions
    )

    results.add_result(
        "Low confidence detection",
        confidence_triggered,
        f"Confidence {low_confidence:.2f} < threshold 0.5"
    )

    if predictions:
        for pred in predictions:
            print(f"  Trigger: {pred.trigger_type.value}")
            print(f"  Reason: {pred.reason}")


def test_repetitive_actions(monitor: MetacognitiveMonitor, results: TestResults):
    """Test repetitive action detection (should trigger warning)"""
    print("\n[Test 4] Repetitive Action Detection")
    print("-" * 50)

    task_id = "test_repetition_001"

    # Record same action type multiple times (threshold is 3)
    for i in range(4):
        monitor.record_action(
            action_id=f"action_repeat_{i}",
            action_type="retry_connection",  # Same action repeated
            task_id=task_id,
            duration_ms=2000,
            confidence=0.6,
            success=False
        )
        time.sleep(0.1)  # Small delay between actions

    # Predict failure
    predictions = monitor.predict_failure(
        task_id=task_id,
        duration_ms=8000,
        complexity=TaskComplexity.SIMPLE,
        confidence=0.6
    )

    repetition_triggered = any(
        p.trigger_type == FailureTrigger.ACTION_REPETITION
        for p in predictions
    )

    results.add_result(
        "Repetitive action detection",
        repetition_triggered,
        "Same action repeated 4 times (threshold 3)"
    )

    if predictions:
        for pred in predictions:
            print(f"  Trigger: {pred.trigger_type.value}")
            print(f"  Reason: {pred.reason}")


def test_stuck_state(monitor: MetacognitiveMonitor, results: TestResults):
    """Test stuck state detection (no progress)"""
    print("\n[Test 5] Stuck State Detection")
    print("-" * 50)

    # Add progress markers showing stagnation
    for i in range(6):
        monitor.failure_predictor.add_progress_marker(0.3)  # No progress
        time.sleep(0.05)

    # Check for stuck state
    predictions = monitor.predict_failure(
        task_id="test_stuck_001",
        duration_ms=10000,
        complexity=TaskComplexity.COMPLEX,
        confidence=0.6
    )

    stuck_triggered = any(
        p.trigger_type == FailureTrigger.STUCK_STATE
        for p in predictions
    )

    results.add_result(
        "Stuck state detection",
        stuck_triggered,
        "Progress stagnant at 0.3 for 6 iterations"
    )


def test_trap_evaluator(results: TestResults):
    """Test TRAP framework evaluation"""
    print("\n[Test 6] TRAP Framework Evaluation")
    print("-" * 50)

    evaluator = TRAPEvaluator()

    # Test transparency evaluation
    good_reasoning = [
        "Analyzed the problem structure",
        "Considered approach A because of efficiency",
        "Therefore chose iterative solution",
        "Alternatively could use recursive approach",
        "Validated against constraints"
    ]

    transparency = evaluator.evaluate_transparency(good_reasoning)
    results.add_result(
        "TRAP transparency evaluation",
        transparency > 0.5,
        f"Transparency score: {transparency:.2f}"
    )

    # Test reasoning depth
    evaluator.record_reasoning_checkpoint("Initial analysis", 1)
    evaluator.record_reasoning_checkpoint("Strategy selection", 2)
    evaluator.record_reasoning_checkpoint("Validation", 1)

    depth = evaluator.evaluate_reasoning_depth()
    results.add_result(
        "TRAP reasoning depth",
        depth == 3,
        f"Reasoning checkpoints: {depth}"
    )

    # Test adaptation
    evaluator.record_adaptation(
        "breadth_first_search",
        "depth_first_search",
        "performance_bottleneck"
    )

    adaptations = evaluator.evaluate_adaptation()
    results.add_result(
        "TRAP adaptation tracking",
        adaptations == 1,
        f"Adaptations recorded: {adaptations}"
    )

    # Test perception accuracy
    evaluator.record_confidence_prediction(0.8, 0.75)
    evaluator.record_confidence_prediction(0.6, 0.65)
    evaluator.record_confidence_prediction(0.9, 0.85)

    perception = evaluator.evaluate_perception_accuracy()
    results.add_result(
        "TRAP perception accuracy",
        perception > 0.8,  # Should be high with good calibration
        f"Perception accuracy: {perception:.2f}"
    )


def test_cli_analyze(monitor: MetacognitiveMonitor, results: TestResults):
    """Test CLI analyze command"""
    print("\n[Test 7] CLI Analyze Command")
    print("-" * 50)

    try:
        analysis = monitor.analyze_accuracy(days=7)

        has_required_keys = all(
            key in analysis for key in [
                'total_states', 'total_actions', 'total_predictions',
                'average_trap_scores', 'awareness_trends'
            ]
        )

        results.add_result(
            "Analyze command execution",
            has_required_keys,
            f"Analysis keys present: {list(analysis.keys())}"
        )

        print(f"  Total states: {analysis['total_states']}")
        print(f"  Total actions: {analysis['total_actions']}")
        print(f"  Total predictions: {analysis['total_predictions']}")

    except Exception as e:
        results.add_result(
            "Analyze command execution",
            False,
            f"Error: {str(e)}"
        )


def test_cli_export(monitor: MetacognitiveMonitor, results: TestResults):
    """Test CLI export command"""
    print("\n[Test 8] CLI Export Command")
    print("-" * 50)

    output_path = Path("/tmp/metacog_test_export.json")

    try:
        monitor.export_metrics(output_path, format='json')

        # Verify file was created
        file_exists = output_path.exists()

        # Load and validate JSON
        if file_exists:
            with open(output_path, 'r') as f:
                data = json.load(f)

            has_required_keys = all(
                key in data for key in [
                    'export_timestamp', 'metacognitive_states',
                    'action_records', 'failure_predictions', 'summary'
                ]
            )

            results.add_result(
                "Export command execution",
                has_required_keys,
                f"Export contains {len(data['metacognitive_states'])} states, "
                f"{len(data['action_records'])} actions"
            )

            print(f"  Exported to: {output_path}")
            print(f"  File size: {output_path.stat().st_size} bytes")
        else:
            results.add_result(
                "Export command execution",
                False,
                "Output file not created"
            )

    except Exception as e:
        results.add_result(
            "Export command execution",
            False,
            f"Error: {str(e)}"
        )


def test_memory_integration(monitor: MetacognitiveMonitor, results: TestResults):
    """Test enhanced-memory MCP integration"""
    print("\n[Test 9] Enhanced Memory Integration")
    print("-" * 50)

    has_memory = monitor.memory_client is not None

    results.add_result(
        "Enhanced memory client available",
        has_memory,
        f"Memory client: {type(monitor.memory_client).__name__ if has_memory else 'None'}"
    )

    if has_memory:
        # Try to record a state and verify it goes to memory
        try:
            state = monitor.record_state(
                task_id="test_memory_001",
                task_type="integration_test",
                complexity=TaskComplexity.SIMPLE,
                confidence=0.9,
                reasoning_trace=["Testing memory integration"],
                current_strategy="validation",
                self_awareness=0.8,
                knowledge_awareness=0.8,
                process_awareness=0.8,
                limitation_awareness=0.8
            )

            results.add_result(
                "State recording to memory",
                True,
                "State recorded without errors"
            )

        except Exception as e:
            results.add_result(
                "State recording to memory",
                False,
                f"Error: {str(e)}"
            )
    else:
        print("  Note: Enhanced memory not available, using local storage only")


def test_performance(monitor: MetacognitiveMonitor, results: TestResults):
    """Test performance metrics"""
    print("\n[Test 10] Performance Metrics")
    print("-" * 50)

    # Measure state recording performance
    start_time = time.time()
    iterations = 10

    for i in range(iterations):
        monitor.record_state(
            task_id=f"perf_test_{i}",
            task_type="performance_test",
            complexity=TaskComplexity.SIMPLE,
            confidence=0.7,
            reasoning_trace=[f"Step {i}"],
            current_strategy="benchmark"
        )

    duration = time.time() - start_time
    avg_ms = (duration / iterations) * 1000

    # Should be fast (< 100ms per record)
    results.add_result(
        "State recording performance",
        avg_ms < 100,
        f"Average {avg_ms:.2f}ms per state record ({iterations} iterations in {duration:.2f}s)"
    )

    # Measure action recording performance
    start_time = time.time()

    for i in range(iterations):
        monitor.record_action(
            action_id=f"perf_action_{i}",
            action_type="benchmark",
            task_id="perf_test",
            duration_ms=100,
            confidence=0.7,
            success=True
        )

    duration = time.time() - start_time
    avg_ms = (duration / iterations) * 1000

    results.add_result(
        "Action recording performance",
        avg_ms < 50,
        f"Average {avg_ms:.2f}ms per action record"
    )


def main():
    print("="*70)
    print("METACOGNITIVE MONITOR INTEGRATION TEST")
    print("="*70)
    print(f"Start time: {datetime.now().isoformat()}")
    print()

    # Initialize monitor with test storage
    test_storage = Path("/tmp/metacognitive_test")
    monitor = MetacognitiveMonitor(
        storage_path=test_storage,
        enable_memory_integration=True
    )

    print(f"Storage path: {test_storage}")
    print(f"Memory integration: {'Enabled' if monitor.memory_client else 'Disabled'}")

    # Initialize results tracker
    results = TestResults()

    # Run all tests
    try:
        test_normal_execution(monitor, results)
        test_high_latency(monitor, results)
        test_low_confidence(monitor, results)
        test_repetitive_actions(monitor, results)
        test_stuck_state(monitor, results)
        test_trap_evaluator(results)
        test_cli_analyze(monitor, results)
        test_cli_export(monitor, results)
        test_memory_integration(monitor, results)
        test_performance(monitor, results)

    except Exception as e:
        print(f"\n✗ Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Print summary
    all_passed = results.summary()

    # Save test results
    results_file = test_storage / "test_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'passed': results.passed,
            'failed': results.failed,
            'tests': results.tests
        }, f, indent=2)

    print(f"\nTest results saved to: {results_file}")

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())

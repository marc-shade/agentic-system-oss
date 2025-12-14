#!/usr/bin/env python3
"""
Metacognitive Monitoring System

Implements TRAP framework (Transparency, Reasoning, Adaptation, Perception) and
failure prediction based on agentic metacognition research.

Usage:
    # Record metacognitive state during task execution
    python metacognitive-monitor.py record --task "code_generation" --confidence 0.8

    # Check for failure prediction triggers
    python metacognitive-monitor.py predict --task-id "task_123"

    # Analyze metacognitive accuracy over time
    python metacognitive-monitor.py analyze --days 7

    # Run continuous monitoring (daemon mode)
    python metacognitive-monitor.py monitor --interval 60

    # Export metrics for analysis
    python metacognitive-monitor.py export --format json --output /tmp/metacog_metrics.json

Research Implementation:
    - TRAP Framework (Transparency, Reasoning, Adaptation, Perception)
    - Failure prediction triggers (latency, repetition, confidence, stuck states)
    - Self-awareness indicators tracking
    - Metacognitive accuracy measurement
"""

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, deque

# Add MCP integration paths
sys.path.insert(0, '/mnt/agentic-system/mcp-servers/enhanced-memory-mcp')

try:
    from memory_client import MemoryClient as EnhancedMemoryClient
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    # Only warn if not in hook context (avoid polluting hook output)
    import os
    if not os.environ.get("CLAUDE_HOOK_CONTEXT"):
        print("Warning: Enhanced memory not available, using local storage only")


# ============================================================================
# ENUMERATIONS AND DATA STRUCTURES
# ============================================================================

class TaskComplexity(Enum):
    """Task complexity levels for adaptive thresholds"""
    SIMPLE = "simple"           # Single-step operations
    MODERATE = "moderate"       # Multi-step with clear path
    COMPLEX = "complex"         # Requires planning and adaptation
    NOVEL = "novel"            # No prior experience, high uncertainty


class MetacognitiveAwareness(Enum):
    """Dimensions of metacognitive awareness"""
    SELF_AWARENESS = "self_awareness"           # Awareness of own state
    KNOWLEDGE_AWARENESS = "knowledge_awareness" # What is known/unknown
    PROCESS_AWARENESS = "process_awareness"     # How thinking works
    LIMITATION_AWARENESS = "limitation_awareness" # Boundary recognition


class FailureTrigger(Enum):
    """Failure prediction triggers from research"""
    LATENCY_EXCEEDED = "latency_exceeded"
    ACTION_REPETITION = "action_repetition"
    LOW_CONFIDENCE = "low_confidence"
    STUCK_STATE = "stuck_state"
    DEGRADING_PERFORMANCE = "degrading_performance"
    CONFIDENCE_MISMATCH = "confidence_mismatch"  # Confident but wrong


@dataclass
class TRAPMetrics:
    """Metrics for TRAP framework evaluation"""
    transparency_score: float  # 0.0-1.0: Quality of reasoning logs
    reasoning_depth: int       # Number of self-reflection checkpoints
    adaptation_count: int      # Strategy adjustments made
    perception_accuracy: float # Confidence calibration (0.0-1.0)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class FailurePrediction:
    """Failure prediction result"""
    triggered: bool
    trigger_type: Optional[FailureTrigger]
    confidence: float  # 0.0-1.0: Confidence in prediction
    reason: str
    recommended_action: str
    timestamp: str

    def to_dict(self) -> Dict:
        result = asdict(self)
        if self.trigger_type:
            result['trigger_type'] = self.trigger_type.value
        return result


@dataclass
class MetacognitiveState:
    """Complete metacognitive state snapshot"""
    timestamp: str
    task_id: str
    task_type: str
    complexity: TaskComplexity

    # TRAP metrics
    trap_metrics: TRAPMetrics

    # Awareness dimensions (0.0-1.0)
    self_awareness: float
    knowledge_awareness: float
    process_awareness: float
    limitation_awareness: float

    # Performance metrics
    confidence_level: float
    cognitive_load: float

    # Context
    reasoning_trace: List[str]
    current_strategy: str

    def to_dict(self) -> Dict:
        result = asdict(self)
        result['complexity'] = self.complexity.value
        result['trap_metrics'] = self.trap_metrics.to_dict()
        return result


@dataclass
class ActionRecord:
    """Record of action execution for pattern analysis"""
    action_id: str
    action_type: str
    timestamp: str
    duration_ms: int
    confidence: float
    success: bool
    task_id: str

    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================================
# TRAP FRAMEWORK EVALUATOR
# ============================================================================

class TRAPEvaluator:
    """
    Evaluates Transparency, Reasoning, Adaptation, Perception

    Based on TRAP framework for metacognitive assessment:
    - Transparency: Quality and completeness of reasoning logs
    - Reasoning: Depth and frequency of self-reflection
    - Adaptation: Ability to detect and correct errors
    - Perception: Accuracy of confidence calibration
    """

    def __init__(self):
        self.reasoning_checkpoints = []
        self.adaptations = []
        self.confidence_predictions = []  # (predicted, actual) pairs

    def record_reasoning_checkpoint(self,
                                   checkpoint: str,
                                   depth_level: int):
        """Record self-reflection checkpoint"""
        self.reasoning_checkpoints.append({
            'timestamp': datetime.now().isoformat(),
            'checkpoint': checkpoint,
            'depth': depth_level
        })

    def record_adaptation(self,
                         old_strategy: str,
                         new_strategy: str,
                         trigger: str):
        """Record strategy adaptation"""
        self.adaptations.append({
            'timestamp': datetime.now().isoformat(),
            'from_strategy': old_strategy,
            'to_strategy': new_strategy,
            'trigger': trigger
        })

    def record_confidence_prediction(self,
                                    predicted: float,
                                    actual: float):
        """Record confidence calibration data"""
        self.confidence_predictions.append({
            'timestamp': datetime.now().isoformat(),
            'predicted': predicted,
            'actual': actual
        })

    def evaluate_transparency(self, reasoning_trace: List[str]) -> float:
        """
        Evaluate transparency score based on reasoning quality

        Criteria:
        - Completeness: All decision points logged
        - Clarity: Reasoning is understandable
        - Traceability: Steps can be followed
        """
        if not reasoning_trace:
            return 0.0

        # Score factors
        completeness = min(len(reasoning_trace) / 5.0, 1.0)  # Expect ~5 steps

        # Check for key transparency indicators
        indicators = [
            any('because' in step.lower() for step in reasoning_trace),
            any('therefore' in step.lower() for step in reasoning_trace),
            any('considering' in step.lower() for step in reasoning_trace),
            any('alternatively' in step.lower() for step in reasoning_trace),
        ]
        clarity = sum(indicators) / len(indicators)

        # Traceability: sequential reasoning
        has_sequence = len(reasoning_trace) >= 2
        traceability = 1.0 if has_sequence else 0.5

        return (completeness * 0.4 + clarity * 0.4 + traceability * 0.2)

    def evaluate_reasoning_depth(self) -> int:
        """Count self-reflection checkpoints"""
        return len(self.reasoning_checkpoints)

    def evaluate_adaptation(self) -> int:
        """Count strategy adaptations"""
        return len(self.adaptations)

    def evaluate_perception_accuracy(self) -> float:
        """
        Evaluate confidence calibration accuracy

        Uses mean absolute error between predicted and actual confidence
        Lower error = better calibration = higher score
        """
        if not self.confidence_predictions:
            return 0.5  # Neutral if no data

        errors = [
            abs(pred['predicted'] - pred['actual'])
            for pred in self.confidence_predictions
        ]

        mae = sum(errors) / len(errors)

        # Convert error to accuracy score (1.0 = perfect, 0.0 = worst)
        accuracy = max(0.0, 1.0 - mae)

        return accuracy

    def get_trap_metrics(self, reasoning_trace: List[str]) -> TRAPMetrics:
        """Generate complete TRAP metrics"""
        return TRAPMetrics(
            transparency_score=self.evaluate_transparency(reasoning_trace),
            reasoning_depth=self.evaluate_reasoning_depth(),
            adaptation_count=self.evaluate_adaptation(),
            perception_accuracy=self.evaluate_perception_accuracy()
        )


# ============================================================================
# FAILURE PREDICTOR
# ============================================================================

class FailurePredictor:
    """
    Predicts task failure using research-based triggers

    Implements failure detection from Agentic Metacognition research:
    - Latency thresholds (complexity-adaptive)
    - Action repetition patterns
    - Confidence thresholds
    - Stuck state detection
    """

    # Latency thresholds by complexity (seconds)
    LATENCY_THRESHOLDS = {
        TaskComplexity.SIMPLE: 5,
        TaskComplexity.MODERATE: 15,
        TaskComplexity.COMPLEX: 30,
        TaskComplexity.NOVEL: 60
    }

    # Repetition threshold (same action N times)
    REPETITION_THRESHOLD = 3

    # Confidence threshold
    CONFIDENCE_THRESHOLD = 0.5

    # Stuck state threshold (iterations without progress)
    STUCK_THRESHOLD = 5

    def __init__(self):
        self.action_history = deque(maxlen=100)
        self.progress_history = deque(maxlen=20)

    def add_action(self, action: ActionRecord):
        """Add action to history for pattern analysis"""
        self.action_history.append(action)

    def add_progress_marker(self, progress: float):
        """Add progress marker (0.0-1.0)"""
        self.progress_history.append({
            'timestamp': datetime.now().isoformat(),
            'progress': progress
        })

    def check_latency(self,
                     duration_ms: int,
                     complexity: TaskComplexity) -> Optional[FailurePrediction]:
        """Check if task latency exceeds threshold"""
        threshold_ms = self.LATENCY_THRESHOLDS[complexity] * 1000

        if duration_ms > threshold_ms:
            return FailurePrediction(
                triggered=True,
                trigger_type=FailureTrigger.LATENCY_EXCEEDED,
                confidence=0.7,
                reason=f"Task duration ({duration_ms}ms) exceeds threshold ({threshold_ms}ms) for {complexity.value} task",
                recommended_action="Consider simplifying approach or breaking into subtasks",
                timestamp=datetime.now().isoformat()
            )
        return None

    def check_repetition(self, task_id: str) -> Optional[FailurePrediction]:
        """Check for action repetition patterns"""
        # Get recent actions for this task
        task_actions = [
            a for a in self.action_history
            if a.task_id == task_id
        ]

        if len(task_actions) < self.REPETITION_THRESHOLD:
            return None

        # Check for repeated action types
        recent_types = [a.action_type for a in task_actions[-self.REPETITION_THRESHOLD:]]

        if len(set(recent_types)) == 1:  # All same action
            return FailurePrediction(
                triggered=True,
                trigger_type=FailureTrigger.ACTION_REPETITION,
                confidence=0.8,
                reason=f"Action '{recent_types[0]}' repeated {self.REPETITION_THRESHOLD}+ times",
                recommended_action="Current approach likely ineffective, try alternative strategy",
                timestamp=datetime.now().isoformat()
            )
        return None

    def check_confidence(self, confidence: float) -> Optional[FailurePrediction]:
        """Check if confidence is too low"""
        if confidence < self.CONFIDENCE_THRESHOLD:
            return FailurePrediction(
                triggered=True,
                trigger_type=FailureTrigger.LOW_CONFIDENCE,
                confidence=0.6,
                reason=f"Confidence level ({confidence:.2f}) below threshold ({self.CONFIDENCE_THRESHOLD})",
                recommended_action="Seek additional information or request human guidance",
                timestamp=datetime.now().isoformat()
            )
        return None

    def check_stuck_state(self) -> Optional[FailurePrediction]:
        """Check for stuck state (no progress)"""
        if len(self.progress_history) < self.STUCK_THRESHOLD:
            return None

        recent_progress = [p['progress'] for p in list(self.progress_history)[-self.STUCK_THRESHOLD:]]

        # Check if progress is stagnant (< 0.05 change)
        if max(recent_progress) - min(recent_progress) < 0.05:
            return FailurePrediction(
                triggered=True,
                trigger_type=FailureTrigger.STUCK_STATE,
                confidence=0.75,
                reason=f"No significant progress in last {self.STUCK_THRESHOLD} iterations",
                recommended_action="Reassess approach, consider backtracking or requesting assistance",
                timestamp=datetime.now().isoformat()
            )
        return None

    def check_confidence_mismatch(self,
                                 predicted_confidence: float,
                                 actual_success: bool) -> Optional[FailurePrediction]:
        """Check for confident but incorrect predictions"""
        if predicted_confidence > 0.7 and not actual_success:
            return FailurePrediction(
                triggered=True,
                trigger_type=FailureTrigger.CONFIDENCE_MISMATCH,
                confidence=0.85,
                reason=f"High confidence ({predicted_confidence:.2f}) but task failed",
                recommended_action="Recalibrate confidence estimation, review assumptions",
                timestamp=datetime.now().isoformat()
            )
        return None

    def predict_failure(self,
                       task_id: str,
                       duration_ms: int,
                       complexity: TaskComplexity,
                       confidence: float) -> List[FailurePrediction]:
        """Run all failure prediction checks"""
        predictions = []

        # Check each trigger
        if pred := self.check_latency(duration_ms, complexity):
            predictions.append(pred)

        if pred := self.check_repetition(task_id):
            predictions.append(pred)

        if pred := self.check_confidence(confidence):
            predictions.append(pred)

        if pred := self.check_stuck_state():
            predictions.append(pred)

        return predictions


# ============================================================================
# METACOGNITIVE MONITOR
# ============================================================================

class MetacognitiveMonitor:
    """
    Main metacognitive monitoring system

    Coordinates TRAP evaluation and failure prediction, integrates with
    enhanced-memory MCP for persistent state tracking.
    """

    def __init__(self,
                 storage_path: Optional[Path] = None,
                 enable_memory_integration: bool = True):
        """
        Initialize monitor

        Args:
            storage_path: Local storage for metrics (default: /tmp/metacognitive)
            enable_memory_integration: Use enhanced-memory MCP if available
        """
        # Convert string to Path if needed
        if storage_path is None:
            self.storage_path = Path("/tmp/metacognitive")
        elif isinstance(storage_path, str):
            self.storage_path = Path(storage_path).parent  # Use parent dir if file path given
        else:
            self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.trap_evaluator = TRAPEvaluator()
        self.failure_predictor = FailurePredictor()

        # Memory integration
        self.memory_client = None
        if enable_memory_integration and MEMORY_AVAILABLE:
            try:
                self.memory_client = EnhancedMemoryClient()
                logging.info("Enhanced memory integration enabled")
            except Exception as e:
                logging.warning(f"Could not initialize memory client: {e}")

        # Metrics storage
        self.states_file = self.storage_path / "metacognitive_states.jsonl"
        self.actions_file = self.storage_path / "action_records.jsonl"
        self.predictions_file = self.storage_path / "failure_predictions.jsonl"

        logging.info(f"Metacognitive monitor initialized (storage: {self.storage_path})")

    def record_state(self,
                    task_id: str,
                    task_type: str,
                    complexity: TaskComplexity,
                    confidence: float,
                    reasoning_trace: List[str],
                    current_strategy: str,
                    cognitive_load: float = 0.5,
                    self_awareness: float = 0.5,
                    knowledge_awareness: float = 0.5,
                    process_awareness: float = 0.5,
                    limitation_awareness: float = 0.5) -> MetacognitiveState:
        """
        Record complete metacognitive state

        Args:
            task_id: Unique task identifier
            task_type: Type of task being executed
            complexity: Task complexity level
            confidence: Current confidence level (0.0-1.0)
            reasoning_trace: List of reasoning steps
            current_strategy: Strategy being employed
            cognitive_load: Estimated cognitive load (0.0-1.0)
            self_awareness: Self-awareness score (0.0-1.0)
            knowledge_awareness: Knowledge awareness score (0.0-1.0)
            process_awareness: Process awareness score (0.0-1.0)
            limitation_awareness: Limitation awareness score (0.0-1.0)

        Returns:
            MetacognitiveState object
        """
        # Get TRAP metrics
        trap_metrics = self.trap_evaluator.get_trap_metrics(reasoning_trace)

        # Create state
        state = MetacognitiveState(
            timestamp=datetime.now().isoformat(),
            task_id=task_id,
            task_type=task_type,
            complexity=complexity,
            trap_metrics=trap_metrics,
            self_awareness=self_awareness,
            knowledge_awareness=knowledge_awareness,
            process_awareness=process_awareness,
            limitation_awareness=limitation_awareness,
            confidence_level=confidence,
            cognitive_load=cognitive_load,
            reasoning_trace=reasoning_trace,
            current_strategy=current_strategy
        )

        # Store locally
        self._append_jsonl(self.states_file, state.to_dict())

        # Store in enhanced memory if available
        if self.memory_client:
            try:
                self.memory_client.record_metacognitive_state(
                    agent_id="metacognitive_monitor",
                    self_awareness=self_awareness,
                    knowledge_awareness=knowledge_awareness,
                    process_awareness=process_awareness,
                    limitation_awareness=limitation_awareness,
                    cognitive_load=cognitive_load,
                    confidence_level=confidence,
                    reasoning_trace=reasoning_trace,
                    task_context={
                        'task_id': task_id,
                        'task_type': task_type,
                        'complexity': complexity.value,
                        'strategy': current_strategy
                    }
                )
            except Exception as e:
                logging.warning(f"Failed to record state in memory: {e}")

        logging.info(f"Recorded metacognitive state for task {task_id}")
        return state

    def record_action(self,
                     action_id: str,
                     action_type: str,
                     task_id: str,
                     duration_ms: int,
                     confidence: float,
                     success: bool) -> ActionRecord:
        """
        Record action execution

        Args:
            action_id: Unique action identifier
            action_type: Type of action
            task_id: Associated task ID
            duration_ms: Execution duration
            confidence: Confidence in action
            success: Whether action succeeded

        Returns:
            ActionRecord object
        """
        action = ActionRecord(
            action_id=action_id,
            action_type=action_type,
            timestamp=datetime.now().isoformat(),
            duration_ms=duration_ms,
            confidence=confidence,
            success=success,
            task_id=task_id
        )

        # Add to predictor
        self.failure_predictor.add_action(action)

        # Store locally
        self._append_jsonl(self.actions_file, action.to_dict())

        # Store in enhanced memory if available
        if self.memory_client:
            try:
                self.memory_client.record_action_outcome(
                    action_type=action_type,
                    action_description=f"Action {action_id}",
                    expected_result=f"Success with confidence {confidence}",
                    actual_result="Success" if success else "Failure",
                    success_score=1.0 if success else 0.0,
                    agent_id="metacognitive_monitor",
                    duration_ms=duration_ms
                )
            except Exception as e:
                logging.warning(f"Failed to record action in memory: {e}")

        logging.debug(f"Recorded action {action_id}")
        return action

    def predict_failure(self,
                       task_id: str,
                       duration_ms: int,
                       complexity: TaskComplexity,
                       confidence: float) -> List[FailurePrediction]:
        """
        Run failure prediction checks

        Args:
            task_id: Task being evaluated
            duration_ms: Current task duration
            complexity: Task complexity
            confidence: Current confidence level

        Returns:
            List of triggered failure predictions
        """
        predictions = self.failure_predictor.predict_failure(
            task_id=task_id,
            duration_ms=duration_ms,
            complexity=complexity,
            confidence=confidence
        )

        # Store predictions
        for pred in predictions:
            self._append_jsonl(self.predictions_file, pred.to_dict())

        if predictions:
            logging.warning(f"Failure predictions triggered for task {task_id}: "
                          f"{[p.trigger_type.value for p in predictions]}")

        return predictions

    def analyze_accuracy(self, days: int = 7) -> Dict[str, Any]:
        """
        Analyze metacognitive accuracy over time period

        Args:
            days: Number of days to analyze

        Returns:
            Analysis results with accuracy metrics
        """
        cutoff = datetime.now() - timedelta(days=days)

        # Load states
        states = self._load_recent_jsonl(self.states_file, cutoff)
        actions = self._load_recent_jsonl(self.actions_file, cutoff)
        predictions = self._load_recent_jsonl(self.predictions_file, cutoff)

        # Calculate metrics
        analysis = {
            'period_days': days,
            'total_states': len(states),
            'total_actions': len(actions),
            'total_predictions': len(predictions),
            'average_trap_scores': self._average_trap_scores(states),
            'awareness_trends': self._awareness_trends(states),
            'prediction_accuracy': self._prediction_accuracy(predictions, actions),
            'confidence_calibration': self._confidence_calibration(actions),
            'most_common_failures': self._common_failure_triggers(predictions)
        }

        return analysis

    def export_metrics(self, output_path: Path, format: str = 'json'):
        """
        Export all metrics to file

        Args:
            output_path: Output file path
            format: Export format ('json' or 'csv')
        """
        # Load all data
        states = self._load_all_jsonl(self.states_file)
        actions = self._load_all_jsonl(self.actions_file)
        predictions = self._load_all_jsonl(self.predictions_file)

        data = {
            'export_timestamp': datetime.now().isoformat(),
            'metacognitive_states': states,
            'action_records': actions,
            'failure_predictions': predictions,
            'summary': self.analyze_accuracy(days=30)
        }

        if format == 'json':
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
        else:
            raise NotImplementedError(f"Export format '{format}' not implemented")

        logging.info(f"Exported metrics to {output_path}")

    # ========================================================================
    # INTERNAL METHODS
    # ========================================================================

    def _append_jsonl(self, file_path: Path, data: Dict):
        """Append JSON line to file"""
        with open(file_path, 'a') as f:
            f.write(json.dumps(data) + '\n')

    def _load_all_jsonl(self, file_path: Path) -> List[Dict]:
        """Load all JSON lines from file"""
        if not file_path.exists():
            return []

        data = []
        with open(file_path, 'r') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
        return data

    def _load_recent_jsonl(self, file_path: Path, cutoff: datetime) -> List[Dict]:
        """Load JSON lines after cutoff timestamp"""
        all_data = self._load_all_jsonl(file_path)
        return [
            d for d in all_data
            if datetime.fromisoformat(d['timestamp']) >= cutoff
        ]

    def _average_trap_scores(self, states: List[Dict]) -> Dict[str, float]:
        """Calculate average TRAP scores"""
        if not states:
            return {}

        trap_metrics = [s['trap_metrics'] for s in states]

        return {
            'transparency': sum(t['transparency_score'] for t in trap_metrics) / len(trap_metrics),
            'reasoning_depth': sum(t['reasoning_depth'] for t in trap_metrics) / len(trap_metrics),
            'adaptation_count': sum(t['adaptation_count'] for t in trap_metrics) / len(trap_metrics),
            'perception_accuracy': sum(t['perception_accuracy'] for t in trap_metrics) / len(trap_metrics)
        }

    def _awareness_trends(self, states: List[Dict]) -> Dict[str, List[float]]:
        """Extract awareness trends over time"""
        return {
            'self_awareness': [s['self_awareness'] for s in states],
            'knowledge_awareness': [s['knowledge_awareness'] for s in states],
            'process_awareness': [s['process_awareness'] for s in states],
            'limitation_awareness': [s['limitation_awareness'] for s in states]
        }

    def _prediction_accuracy(self,
                            predictions: List[Dict],
                            actions: List[Dict]) -> Dict[str, Any]:
        """Calculate prediction accuracy"""
        if not predictions:
            return {'total_predictions': 0}

        # Group by trigger type
        by_trigger = defaultdict(list)
        for pred in predictions:
            if pred['triggered']:
                by_trigger[pred['trigger_type']].append(pred)

        return {
            'total_predictions': len(predictions),
            'by_trigger_type': {k: len(v) for k, v in by_trigger.items()},
            'average_confidence': sum(p['confidence'] for p in predictions) / len(predictions)
        }

    def _confidence_calibration(self, actions: List[Dict]) -> Dict[str, float]:
        """Calculate confidence calibration metrics"""
        if not actions:
            return {}

        # Expected vs actual success rate
        confident_actions = [a for a in actions if a['confidence'] > 0.7]
        if confident_actions:
            high_conf_success_rate = sum(1 for a in confident_actions if a['success']) / len(confident_actions)
        else:
            high_conf_success_rate = 0.0

        low_conf_actions = [a for a in actions if a['confidence'] < 0.3]
        if low_conf_actions:
            low_conf_success_rate = sum(1 for a in low_conf_actions if a['success']) / len(low_conf_actions)
        else:
            low_conf_success_rate = 0.0

        return {
            'high_confidence_success_rate': high_conf_success_rate,
            'low_confidence_success_rate': low_conf_success_rate,
            'calibration_gap': abs(high_conf_success_rate - 0.7)  # Expected ~70% for high confidence
        }

    def _common_failure_triggers(self, predictions: List[Dict]) -> List[Tuple[str, int]]:
        """Get most common failure triggers"""
        triggers = [p['trigger_type'] for p in predictions if p['triggered']]

        from collections import Counter
        counts = Counter(triggers)

        return counts.most_common(5)


# ============================================================================
# COMMAND-LINE INTERFACE
# ============================================================================

def setup_logging(verbose: bool = False):
    """Configure logging"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def cmd_record(args):
    """Record metacognitive state"""
    monitor = MetacognitiveMonitor()

    complexity = TaskComplexity[args.complexity.upper()]

    reasoning_trace = args.reasoning_trace.split('|') if args.reasoning_trace else []

    state = monitor.record_state(
        task_id=args.task_id,
        task_type=args.task_type,
        complexity=complexity,
        confidence=args.confidence,
        reasoning_trace=reasoning_trace,
        current_strategy=args.strategy,
        cognitive_load=args.cognitive_load,
        self_awareness=args.self_awareness,
        knowledge_awareness=args.knowledge_awareness,
        process_awareness=args.process_awareness,
        limitation_awareness=args.limitation_awareness
    )

    print(json.dumps(state.to_dict(), indent=2))
    print(f"\n✓ State recorded for task {args.task_id}")


def cmd_predict(args):
    """Run failure prediction"""
    monitor = MetacognitiveMonitor()

    complexity = TaskComplexity[args.complexity.upper()]

    predictions = monitor.predict_failure(
        task_id=args.task_id,
        duration_ms=args.duration_ms,
        complexity=complexity,
        confidence=args.confidence
    )

    if predictions:
        print(f"\n⚠ {len(predictions)} failure trigger(s) detected:\n")
        for pred in predictions:
            print(json.dumps(pred.to_dict(), indent=2))
            print()
    else:
        print("\n✓ No failure triggers detected")


def cmd_analyze(args):
    """Analyze metacognitive accuracy"""
    monitor = MetacognitiveMonitor()

    analysis = monitor.analyze_accuracy(days=args.days)

    print(json.dumps(analysis, indent=2))


def cmd_export(args):
    """Export metrics"""
    monitor = MetacognitiveMonitor()

    output_path = Path(args.output)
    monitor.export_metrics(output_path, format=args.format)

    print(f"✓ Metrics exported to {output_path}")


def cmd_monitor(args):
    """Continuous monitoring (daemon mode)"""
    monitor = MetacognitiveMonitor()

    print(f"Starting continuous monitoring (interval: {args.interval}s)")
    print("Press Ctrl+C to stop")

    try:
        while True:
            # Run analysis
            analysis = monitor.analyze_accuracy(days=1)

            print(f"\n[{datetime.now().isoformat()}]")
            print(f"States: {analysis['total_states']}")
            print(f"Actions: {analysis['total_actions']}")
            print(f"Predictions: {analysis['total_predictions']}")

            if analysis['average_trap_scores']:
                trap = analysis['average_trap_scores']
                print(f"TRAP: T={trap['transparency']:.2f} R={trap['reasoning_depth']:.1f} "
                      f"A={trap['adaptation_count']:.1f} P={trap['perception_accuracy']:.2f}")

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped")


def main():
    parser = argparse.ArgumentParser(
        description="Metacognitive Monitoring System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Record state during code generation
  %(prog)s record --task-id task_123 --task-type code_generation \\
    --complexity complex --confidence 0.8 --strategy "iterative_refinement"

  # Predict failure for long-running task
  %(prog)s predict --task-id task_123 --duration-ms 35000 \\
    --complexity moderate --confidence 0.6

  # Analyze last week's accuracy
  %(prog)s analyze --days 7

  # Export all metrics
  %(prog)s export --output /tmp/metrics.json --format json

  # Run continuous monitoring
  %(prog)s monitor --interval 60
        """
    )

    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose logging')

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Record command
    record_parser = subparsers.add_parser('record', help='Record metacognitive state')
    record_parser.add_argument('--task-id', required=True, help='Task ID')
    record_parser.add_argument('--task-type', required=True, help='Task type')
    record_parser.add_argument('--complexity', required=True,
                              choices=['simple', 'moderate', 'complex', 'novel'],
                              help='Task complexity')
    record_parser.add_argument('--confidence', type=float, required=True,
                              help='Confidence level (0.0-1.0)')
    record_parser.add_argument('--strategy', default='default',
                              help='Current strategy')
    record_parser.add_argument('--reasoning-trace', default='',
                              help='Reasoning steps (pipe-separated)')
    record_parser.add_argument('--cognitive-load', type=float, default=0.5,
                              help='Cognitive load (0.0-1.0)')
    record_parser.add_argument('--self-awareness', type=float, default=0.5,
                              help='Self-awareness score (0.0-1.0)')
    record_parser.add_argument('--knowledge-awareness', type=float, default=0.5,
                              help='Knowledge awareness score (0.0-1.0)')
    record_parser.add_argument('--process-awareness', type=float, default=0.5,
                              help='Process awareness score (0.0-1.0)')
    record_parser.add_argument('--limitation-awareness', type=float, default=0.5,
                              help='Limitation awareness score (0.0-1.0)')

    # Predict command
    predict_parser = subparsers.add_parser('predict', help='Predict task failure')
    predict_parser.add_argument('--task-id', required=True, help='Task ID')
    predict_parser.add_argument('--duration-ms', type=int, required=True,
                               help='Current task duration (ms)')
    predict_parser.add_argument('--complexity', required=True,
                               choices=['simple', 'moderate', 'complex', 'novel'],
                               help='Task complexity')
    predict_parser.add_argument('--confidence', type=float, required=True,
                               help='Confidence level (0.0-1.0)')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze metacognitive accuracy')
    analyze_parser.add_argument('--days', type=int, default=7,
                               help='Number of days to analyze')

    # Export command
    export_parser = subparsers.add_parser('export', help='Export metrics')
    export_parser.add_argument('--output', required=True,
                              help='Output file path')
    export_parser.add_argument('--format', default='json',
                              choices=['json'],
                              help='Export format')

    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Continuous monitoring')
    monitor_parser.add_argument('--interval', type=int, default=60,
                               help='Monitoring interval (seconds)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    setup_logging(args.verbose)

    # Execute command
    commands = {
        'record': cmd_record,
        'predict': cmd_predict,
        'analyze': cmd_analyze,
        'export': cmd_export,
        'monitor': cmd_monitor
    }

    try:
        commands[args.command](args)
        return 0
    except Exception as e:
        logging.error(f"Command failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

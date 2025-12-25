#!/usr/bin/env python3
"""
Continuous Learning System for Enhanced Memory MCP.

Ported from ruvnet/agentic-flow AgentDBIntegration TypeScript implementation,
enhanced with EWC++ (Elastic Weight Consolidation) from ruvnet/ruvector SONA.

Features:
- Learn from provider corrections using gradient descent
- **EWC++ catastrophic forgetting prevention** (ported from SONA Rust)
- Pattern recognition for successful/failed verifications
- Source reliability tracking with sample-weighted scoring
- Feature vector-based confidence predictions
- Exponential moving average for pattern updates
- Online Fisher information estimation
- Automatic task boundary detection via z-score distribution shift
- Adaptive lambda scheduling for regularization strength
"""

import json
import math
import time
import hashlib
import sqlite3
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, deque


class LearningOutcome(Enum):
    """Outcome of a learning correction."""
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"


@dataclass
class FeatureVector:
    """Feature vector for confidence prediction."""
    citation_count: float = 0.0
    peer_reviewed_ratio: float = 0.0
    recency_score: float = 0.0
    evidence_level_score: float = 0.0
    contradiction_count: float = 0.0
    hallucination_flags: float = 0.0
    text_length: float = 0.0
    quantitative_claims: float = 0.0
    source_reliability: float = 0.5
    semantic_coherence: float = 0.5

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'FeatureVector':
        """Create from dictionary."""
        return cls(
            citation_count=data.get('citation_count', 0.0),
            peer_reviewed_ratio=data.get('peer_reviewed_ratio', 0.0),
            recency_score=data.get('recency_score', 0.0),
            evidence_level_score=data.get('evidence_level_score', 0.0),
            contradiction_count=data.get('contradiction_count', 0.0),
            hallucination_flags=data.get('hallucination_flags', 0.0),
            text_length=data.get('text_length', 0.0),
            quantitative_claims=data.get('quantitative_claims', 0.0),
            source_reliability=data.get('source_reliability', 0.5),
            semantic_coherence=data.get('semantic_coherence', 0.5)
        )

    def get_values(self) -> List[float]:
        """Get feature values as list."""
        return [
            self.citation_count,
            self.peer_reviewed_ratio,
            self.recency_score,
            self.evidence_level_score,
            self.contradiction_count,
            self.hallucination_flags,
            self.text_length,
            self.quantitative_claims,
            self.source_reliability,
            self.semantic_coherence
        ]


@dataclass
class ProviderFeedback:
    """Feedback from a verification provider."""
    provider_id: str
    corrected_confidence: float
    reasoning: str
    suggested_sources: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class Correction:
    """A correction record."""
    original: float
    corrected: float
    delta: float
    features: FeatureVector
    timestamp: float = field(default_factory=time.time)


@dataclass
class LearningRecord:
    """Record of a learning event."""
    id: str
    timestamp: float
    claim: str
    original_confidence: float
    corrected_confidence: float
    provider_feedback: ProviderFeedback
    features: FeatureVector
    outcome: LearningOutcome

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'claim': self.claim,
            'original_confidence': self.original_confidence,
            'corrected_confidence': self.corrected_confidence,
            'provider_id': self.provider_feedback.provider_id,
            'provider_reasoning': self.provider_feedback.reasoning,
            'suggested_sources': json.dumps(self.provider_feedback.suggested_sources),
            'features': json.dumps(self.features.to_dict()),
            'outcome': self.outcome.value
        }


@dataclass
class LearningModel:
    """The gradient descent learning model."""
    weights: Dict[str, float] = field(default_factory=dict)
    bias: float = 0.0
    training_examples: int = 0
    accuracy: float = 0.5
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'weights': self.weights,
            'bias': self.bias,
            'training_examples': self.training_examples,
            'accuracy': self.accuracy,
            'last_updated': self.last_updated
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LearningModel':
        """Create from dictionary."""
        return cls(
            weights=data.get('weights', {}),
            bias=data.get('bias', 0.0),
            training_examples=data.get('training_examples', 0),
            accuracy=data.get('accuracy', 0.5),
            last_updated=data.get('last_updated', time.time())
        )


@dataclass
class Pattern:
    """A recognized pattern in verification outcomes."""
    id: str
    description: str
    feature_signature: Dict[str, Tuple[float, float]]  # feature -> (min, max)
    success_rate: float
    sample_size: int
    last_seen: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'description': self.description,
            'feature_signature': self.feature_signature,
            'success_rate': self.success_rate,
            'sample_size': self.sample_size,
            'last_seen': self.last_seen
        }


@dataclass
class SourceReliability:
    """Reliability tracking for a source."""
    source_id: str
    reliability_score: float = 0.5
    sample_size: int = 0
    successful_verifications: int = 0
    failed_verifications: int = 0
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


# ============================================================================
# EWC++ (Elastic Weight Consolidation) - Ported from ruvnet/ruvector SONA
# ============================================================================

@dataclass
class EwcConfig:
    """Configuration for EWC++ catastrophic forgetting prevention.

    Ported from ruvnet/ruvector crates/sona/src/ewc.rs

    Key parameters tuned from SONA benchmarks:
    - initial_lambda=2000: Default regularization strength
    - boundary_threshold=2.0: Z-score threshold for task detection
    - fisher_ema_decay=0.999: Smooth Fisher information updates
    """
    param_count: int = 10  # Number of model parameters (features)
    max_tasks: int = 10  # Maximum tasks to remember (circular buffer)
    initial_lambda: float = 2000.0  # Regularization strength
    min_lambda: float = 100.0  # Minimum lambda (floor)
    max_lambda: float = 15000.0  # Maximum lambda (ceiling)
    fisher_ema_decay: float = 0.999  # EMA decay for Fisher estimation
    boundary_threshold: float = 2.0  # Z-score threshold for task boundary
    gradient_history_size: int = 50  # Window for distribution tracking


@dataclass
class TaskFisher:
    """Task-specific Fisher information and weights snapshot.

    Stores the "importance" of each parameter for a specific task,
    along with the optimal weights found for that task.
    """
    task_id: int
    fisher: List[float]  # Fisher information per parameter
    weights: List[float]  # Optimal weights for this task
    timestamp: float = field(default_factory=time.time)
    sample_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'task_id': self.task_id,
            'fisher': self.fisher,
            'weights': self.weights,
            'timestamp': self.timestamp,
            'sample_count': self.sample_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskFisher':
        """Create from dictionary."""
        return cls(
            task_id=data['task_id'],
            fisher=data['fisher'],
            weights=data['weights'],
            timestamp=data.get('timestamp', time.time()),
            sample_count=data.get('sample_count', 0)
        )


class EwcPlusPlus:
    """
    Elastic Weight Consolidation++ for preventing catastrophic forgetting.

    Ported from ruvnet/ruvector SONA (crates/sona/src/ewc.rs).

    EWC++ prevents the model from forgetting previous tasks by:
    1. Estimating Fisher information (parameter importance) online
    2. Detecting task boundaries via gradient distribution shift
    3. Applying constraints that penalize changes to important weights

    Key innovations from EWC++:
    - Online Fisher estimation (no need for separate Fisher computation)
    - Automatic task boundary detection (no manual task IDs needed)
    - Adaptive lambda scheduling based on learning progress

    Reference: https://arxiv.org/abs/1801.10112 (Progress & Compress)
    """

    def __init__(self, config: Optional[EwcConfig] = None):
        """Initialize EWC++ with configuration."""
        self.config = config or EwcConfig()

        # Current Fisher information (online estimation)
        self.current_fisher: List[float] = [0.0] * self.config.param_count

        # Current optimal weights (updated during learning)
        self.current_weights: List[float] = [0.0] * self.config.param_count

        # Task memory (circular buffer for multi-task)
        self.task_memory: deque[TaskFisher] = deque(maxlen=self.config.max_tasks)

        # Task tracking
        self.current_task_id: int = 0
        self.samples_in_task: int = 0

        # Adaptive lambda
        self.lambda_value: float = self.config.initial_lambda

        # Gradient distribution tracking for task boundary detection
        self.gradient_history: deque[List[float]] = deque(
            maxlen=self.config.gradient_history_size
        )
        self.gradient_mean: List[float] = [0.0] * self.config.param_count
        self.gradient_var: List[float] = [1.0] * self.config.param_count
        self.samples_seen: int = 0

    def update_fisher(self, gradients: List[float]) -> None:
        """
        Update Fisher information using online EMA estimation.

        Fisher information F_i ≈ E[g_i²] where g_i is gradient for param i.
        Uses exponential moving average for smooth updates.

        Args:
            gradients: Current gradients for each parameter
        """
        decay = self.config.fisher_ema_decay

        for i, grad in enumerate(gradients):
            if i < len(self.current_fisher):
                # Fisher ≈ E[grad²] via EMA
                grad_sq = grad * grad
                self.current_fisher[i] = (
                    decay * self.current_fisher[i] +
                    (1.0 - decay) * grad_sq
                )

        # Store gradient for distribution tracking
        self.gradient_history.append(gradients.copy())
        self._update_gradient_stats(gradients)

    def _update_gradient_stats(self, gradients: List[float]) -> None:
        """Update running mean and variance of gradient distribution."""
        self.samples_seen += 1
        n = self.samples_seen

        for i, grad in enumerate(gradients):
            if i < len(self.gradient_mean):
                # Welford's online algorithm for mean and variance
                delta = grad - self.gradient_mean[i]
                self.gradient_mean[i] += delta / n

                if n > 1:
                    delta2 = grad - self.gradient_mean[i]
                    # Update variance estimate
                    old_var = self.gradient_var[i]
                    self.gradient_var[i] = (
                        old_var * (n - 2) / (n - 1) +
                        delta * delta2 / n
                    )

    def detect_task_boundary(self, gradients: List[float]) -> bool:
        """
        Detect if we've crossed a task boundary using z-score analysis.

        Computes the average z-score of current gradients compared to
        the running distribution. High z-scores indicate a distribution
        shift (new task).

        Args:
            gradients: Current gradients

        Returns:
            True if task boundary detected
        """
        if self.samples_seen < self.config.gradient_history_size:
            return False  # Need enough history

        # Compute z-scores for each gradient
        z_scores = []
        for i, grad in enumerate(gradients):
            if i < len(self.gradient_mean):
                std = math.sqrt(max(self.gradient_var[i], 1e-8))
                z = abs(grad - self.gradient_mean[i]) / std
                z_scores.append(z)

        if not z_scores:
            return False

        # Average z-score across all parameters
        avg_z = sum(z_scores) / len(z_scores)

        return avg_z > self.config.boundary_threshold

    def start_new_task(self, current_weights: List[float]) -> int:
        """
        Start a new task, saving current Fisher and weights.

        Called when task boundary is detected. Saves the current
        knowledge state to task memory.

        Args:
            current_weights: Current model weights

        Returns:
            New task ID
        """
        # Save current task to memory
        task_fisher = TaskFisher(
            task_id=self.current_task_id,
            fisher=self.current_fisher.copy(),
            weights=current_weights.copy(),
            sample_count=self.samples_in_task
        )
        self.task_memory.append(task_fisher)

        # Start new task
        self.current_task_id += 1
        self.samples_in_task = 0

        # Reset gradient statistics for new task
        self.gradient_mean = [0.0] * self.config.param_count
        self.gradient_var = [1.0] * self.config.param_count
        self.samples_seen = 0
        self.gradient_history.clear()

        # Adaptive lambda: increase if we have many tasks
        task_count = len(self.task_memory)
        if task_count > 0:
            # Lambda grows with task count to protect more knowledge
            self.lambda_value = min(
                self.config.max_lambda,
                self.config.initial_lambda * (1.0 + 0.5 * task_count)
            )

        return self.current_task_id

    def apply_constraints(
        self,
        gradients: List[float],
        current_weights: List[float]
    ) -> List[float]:
        """
        Apply EWC constraints to gradients to prevent forgetting.

        The core EWC formula: penalize changes to important parameters.
        penalty_i = λ * Σ_k(F_k,i * (w_i - w*_k,i)²)

        Constrained gradient: g'_i = g_i / (1 + ∂penalty/∂w_i)

        Args:
            gradients: Original gradients
            current_weights: Current model weights

        Returns:
            Constrained gradients
        """
        if not self.task_memory:
            return gradients  # No previous tasks to protect

        constrained = gradients.copy()

        for i, grad in enumerate(gradients):
            if i >= len(current_weights):
                continue

            # Sum penalty gradient across all stored tasks
            penalty_grad = 0.0

            for task in self.task_memory:
                if i < len(task.fisher) and i < len(task.weights):
                    fisher_i = task.fisher[i]
                    weight_delta = current_weights[i] - task.weights[i]

                    # ∂penalty/∂w_i = 2 * λ * F_i * (w_i - w*_i)
                    penalty_grad += 2.0 * self.lambda_value * fisher_i * weight_delta

            # Apply constraint: shrink gradient proportional to penalty
            # This prevents large updates to important parameters
            if abs(penalty_grad) > 1e-10:
                constrained[i] = grad / (1.0 + abs(penalty_grad))

        return constrained

    def regularization_loss(self, current_weights: List[float]) -> float:
        """
        Compute EWC regularization loss term.

        L_ewc = (λ/2) * Σ_k Σ_i F_k,i * (w_i - w*_k,i)²

        This loss penalizes deviations from important parameters
        of previous tasks.

        Args:
            current_weights: Current model weights

        Returns:
            Regularization loss value
        """
        if not self.task_memory:
            return 0.0

        total_loss = 0.0

        for task in self.task_memory:
            for i in range(min(len(current_weights), len(task.fisher), len(task.weights))):
                weight_delta = current_weights[i] - task.weights[i]
                total_loss += task.fisher[i] * weight_delta * weight_delta

        return (self.lambda_value / 2.0) * total_loss

    def update_current_weights(self, weights: List[float]) -> None:
        """Update the current optimal weights reference."""
        self.current_weights = weights.copy()
        self.samples_in_task += 1

    def get_statistics(self) -> Dict[str, Any]:
        """Get EWC++ statistics for monitoring."""
        return {
            'current_task_id': self.current_task_id,
            'tasks_stored': len(self.task_memory),
            'samples_in_current_task': self.samples_in_task,
            'lambda_value': self.lambda_value,
            'total_samples_seen': self.samples_seen,
            'avg_fisher': (
                sum(self.current_fisher) / len(self.current_fisher)
                if self.current_fisher else 0.0
            ),
            'task_history': [
                {
                    'task_id': t.task_id,
                    'sample_count': t.sample_count,
                    'avg_fisher': sum(t.fisher) / len(t.fisher) if t.fisher else 0.0
                }
                for t in self.task_memory
            ]
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize EWC++ state for persistence."""
        return {
            'config': asdict(self.config),
            'current_fisher': self.current_fisher,
            'current_weights': self.current_weights,
            'task_memory': [t.to_dict() for t in self.task_memory],
            'current_task_id': self.current_task_id,
            'samples_in_task': self.samples_in_task,
            'lambda_value': self.lambda_value,
            'gradient_mean': self.gradient_mean,
            'gradient_var': self.gradient_var,
            'samples_seen': self.samples_seen
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EwcPlusPlus':
        """Deserialize EWC++ state."""
        config_data = data.get('config', {})
        config = EwcConfig(
            param_count=config_data.get('param_count', 10),
            max_tasks=config_data.get('max_tasks', 10),
            initial_lambda=config_data.get('initial_lambda', 2000.0),
            min_lambda=config_data.get('min_lambda', 100.0),
            max_lambda=config_data.get('max_lambda', 15000.0),
            fisher_ema_decay=config_data.get('fisher_ema_decay', 0.999),
            boundary_threshold=config_data.get('boundary_threshold', 2.0),
            gradient_history_size=config_data.get('gradient_history_size', 50)
        )

        instance = cls(config)
        instance.current_fisher = data.get('current_fisher', [0.0] * config.param_count)
        instance.current_weights = data.get('current_weights', [0.0] * config.param_count)
        instance.current_task_id = data.get('current_task_id', 0)
        instance.samples_in_task = data.get('samples_in_task', 0)
        instance.lambda_value = data.get('lambda_value', config.initial_lambda)
        instance.gradient_mean = data.get('gradient_mean', [0.0] * config.param_count)
        instance.gradient_var = data.get('gradient_var', [1.0] * config.param_count)
        instance.samples_seen = data.get('samples_seen', 0)

        # Restore task memory
        for task_data in data.get('task_memory', []):
            instance.task_memory.append(TaskFisher.from_dict(task_data))

        return instance


class ContinuousLearning:
    """
    Continuous Learning System.

    Provides gradient descent learning from corrections, pattern recognition,
    and source reliability tracking for improving confidence predictions.

    Enhanced with EWC++ (Elastic Weight Consolidation) from ruvnet/ruvector SONA
    for preventing catastrophic forgetting when learning from diverse sources.
    """

    # Learning parameters
    LEARNING_RATE = 0.01
    PATTERN_THRESHOLD = 0.7
    EMA_ALPHA = 0.1  # Exponential moving average alpha
    MIN_SAMPLES_FOR_PATTERN = 5

    # Feature names for model weights
    FEATURE_NAMES = [
        'citation_count',
        'peer_reviewed_ratio',
        'recency_score',
        'evidence_level_score',
        'contradiction_count',
        'hallucination_flags',
        'text_length',
        'quantitative_claims',
        'source_reliability',
        'semantic_coherence'
    ]

    def __init__(self, db_path: Optional[Path] = None, enable_ewc: bool = True):
        """Initialize the continuous learning system.

        Args:
            db_path: Optional database path
            enable_ewc: Enable EWC++ catastrophic forgetting prevention (default: True)
        """
        self.db_path = db_path or Path.home() / ".claude" / "continuous_learning.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.enable_ewc = enable_ewc

        # In-memory caches
        self.learning_records: Dict[str, LearningRecord] = {}
        self.confidence_model = LearningModel()
        self.patterns: Dict[str, Pattern] = {}
        self.source_reliability: Dict[str, SourceReliability] = {}

        # EWC++ for catastrophic forgetting prevention
        ewc_config = EwcConfig(
            param_count=len(self.FEATURE_NAMES),
            max_tasks=10,
            initial_lambda=2000.0,
            boundary_threshold=2.0,
            fisher_ema_decay=0.999
        )
        self.ewc = EwcPlusPlus(ewc_config) if enable_ewc else None

        # Task boundary detection tracking
        self.task_boundaries_detected = 0
        self.last_task_boundary_time: Optional[float] = None

        # Initialize database and load state
        self._init_database()
        self._load_state()

        # Initialize model weights if empty
        if not self.confidence_model.weights:
            self._initialize_weights()

    def _init_database(self):
        """Initialize the SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS learning_records (
                    id TEXT PRIMARY KEY,
                    timestamp REAL,
                    claim TEXT,
                    original_confidence REAL,
                    corrected_confidence REAL,
                    provider_id TEXT,
                    provider_reasoning TEXT,
                    suggested_sources TEXT,
                    features TEXT,
                    outcome TEXT
                );

                CREATE TABLE IF NOT EXISTS learning_model (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    weights TEXT,
                    bias REAL,
                    training_examples INTEGER,
                    accuracy REAL,
                    last_updated REAL
                );

                CREATE TABLE IF NOT EXISTS patterns (
                    id TEXT PRIMARY KEY,
                    description TEXT,
                    feature_signature TEXT,
                    success_rate REAL,
                    sample_size INTEGER,
                    last_seen REAL
                );

                CREATE TABLE IF NOT EXISTS source_reliability (
                    source_id TEXT PRIMARY KEY,
                    reliability_score REAL,
                    sample_size INTEGER,
                    successful_verifications INTEGER,
                    failed_verifications INTEGER,
                    last_updated REAL
                );

                CREATE INDEX IF NOT EXISTS idx_records_timestamp
                    ON learning_records(timestamp);
                CREATE INDEX IF NOT EXISTS idx_records_outcome
                    ON learning_records(outcome);

                -- EWC++ state persistence (ported from SONA)
                CREATE TABLE IF NOT EXISTS ewc_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    state_json TEXT,
                    last_updated REAL
                );
            """)

    def _load_state(self):
        """Load state from database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Load model
            row = conn.execute("SELECT * FROM learning_model WHERE id = 1").fetchone()
            if row:
                self.confidence_model = LearningModel(
                    weights=json.loads(row['weights']) if row['weights'] else {},
                    bias=row['bias'] or 0.0,
                    training_examples=row['training_examples'] or 0,
                    accuracy=row['accuracy'] or 0.5,
                    last_updated=row['last_updated'] or time.time()
                )

            # Load patterns
            for row in conn.execute("SELECT * FROM patterns"):
                self.patterns[row['id']] = Pattern(
                    id=row['id'],
                    description=row['description'],
                    feature_signature=json.loads(row['feature_signature']),
                    success_rate=row['success_rate'],
                    sample_size=row['sample_size'],
                    last_seen=row['last_seen']
                )

            # Load source reliability
            for row in conn.execute("SELECT * FROM source_reliability"):
                self.source_reliability[row['source_id']] = SourceReliability(
                    source_id=row['source_id'],
                    reliability_score=row['reliability_score'],
                    sample_size=row['sample_size'],
                    successful_verifications=row['successful_verifications'],
                    failed_verifications=row['failed_verifications'],
                    last_updated=row['last_updated']
                )

            # Load EWC++ state if enabled
            if self.enable_ewc:
                ewc_row = conn.execute("SELECT * FROM ewc_state WHERE id = 1").fetchone()
                if ewc_row and ewc_row['state_json']:
                    try:
                        ewc_data = json.loads(ewc_row['state_json'])
                        self.ewc = EwcPlusPlus.from_dict(ewc_data)
                        self.task_boundaries_detected = ewc_data.get('task_boundaries_detected', 0)
                        self.last_task_boundary_time = ewc_data.get('last_task_boundary_time')
                    except (json.JSONDecodeError, KeyError) as e:
                        # Initialize fresh if state is corrupted
                        ewc_config = EwcConfig(
                            param_count=len(self.FEATURE_NAMES),
                            max_tasks=10,
                            initial_lambda=2000.0
                        )
                        self.ewc = EwcPlusPlus(ewc_config)

    def _save_model(self):
        """Save model to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO learning_model
                (id, weights, bias, training_examples, accuracy, last_updated)
                VALUES (1, ?, ?, ?, ?, ?)
            """, (
                json.dumps(self.confidence_model.weights),
                self.confidence_model.bias,
                self.confidence_model.training_examples,
                self.confidence_model.accuracy,
                time.time()
            ))

    def _save_ewc_state(self):
        """Save EWC++ state to database for persistence across sessions."""
        if not self.enable_ewc or self.ewc is None:
            return

        ewc_data = self.ewc.to_dict()
        # Add tracking metadata
        ewc_data['task_boundaries_detected'] = self.task_boundaries_detected
        ewc_data['last_task_boundary_time'] = self.last_task_boundary_time

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO ewc_state
                (id, state_json, last_updated)
                VALUES (1, ?, ?)
            """, (json.dumps(ewc_data), time.time()))

    def _initialize_weights(self):
        """Initialize model weights with sensible defaults."""
        # Positive weights for quality indicators
        self.confidence_model.weights = {
            'citation_count': 0.15,
            'peer_reviewed_ratio': 0.2,
            'recency_score': 0.1,
            'evidence_level_score': 0.2,
            'source_reliability': 0.15,
            'semantic_coherence': 0.1,
            # Negative weights for risk indicators
            'contradiction_count': -0.15,
            'hallucination_flags': -0.25,
            # Neutral/weak features
            'text_length': 0.02,
            'quantitative_claims': 0.05
        }
        self.confidence_model.bias = 0.5
        self._save_model()

    def _generate_id(self, claim: str, timestamp: float) -> str:
        """Generate unique ID for a learning record."""
        content = f"{claim}:{timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _sigmoid(self, x: float) -> float:
        """Sigmoid activation function."""
        return 1.0 / (1.0 + math.exp(-max(-500, min(500, x))))

    async def learn_from_correction(
        self,
        claim: str,
        original_confidence: float,
        feedback: ProviderFeedback,
        features: FeatureVector
    ) -> LearningRecord:
        """
        Learn from a provider correction.

        Uses gradient descent to update model weights based on the
        difference between original and corrected confidence.

        Args:
            claim: The claim that was verified
            original_confidence: Original confidence score
            feedback: Provider feedback with correction
            features: Feature vector for the claim

        Returns:
            LearningRecord with the recorded correction
        """
        record_id = self._generate_id(claim, time.time())

        # Determine outcome
        delta = feedback.corrected_confidence - original_confidence
        if abs(delta) < 0.1:
            outcome = LearningOutcome.ACCEPTED
        elif delta > 0:
            outcome = LearningOutcome.MODIFIED
        else:
            outcome = LearningOutcome.REJECTED

        # Create learning record
        record = LearningRecord(
            id=record_id,
            timestamp=time.time(),
            claim=claim,
            original_confidence=original_confidence,
            corrected_confidence=feedback.corrected_confidence,
            provider_feedback=feedback,
            features=features,
            outcome=outcome
        )

        # Store record
        self.learning_records[record_id] = record
        self._save_learning_record(record)

        # Update model with gradient descent
        self._gradient_descent_update(features, original_confidence, feedback.corrected_confidence)

        # Update patterns
        self._update_patterns(features, outcome == LearningOutcome.ACCEPTED)

        # Update source reliability
        for source in feedback.suggested_sources:
            self._update_source_reliability(
                source,
                outcome == LearningOutcome.ACCEPTED or outcome == LearningOutcome.MODIFIED
            )

        return record

    def _save_learning_record(self, record: LearningRecord):
        """Save a learning record to database."""
        with sqlite3.connect(self.db_path) as conn:
            data = record.to_dict()
            conn.execute("""
                INSERT OR REPLACE INTO learning_records
                (id, timestamp, claim, original_confidence, corrected_confidence,
                 provider_id, provider_reasoning, suggested_sources, features, outcome)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['id'], data['timestamp'], data['claim'],
                data['original_confidence'], data['corrected_confidence'],
                data['provider_id'], data['provider_reasoning'],
                data['suggested_sources'], data['features'], data['outcome']
            ))

    def _gradient_descent_update(
        self,
        features: FeatureVector,
        predicted: float,
        actual: float
    ):
        """
        Update model weights using gradient descent with EWC++ constraints.

        Loss function: MSE = (predicted - actual)^2
        Gradient: d(loss)/d(weight_i) = 2 * (predicted - actual) * feature_i

        EWC++ enhancement (from SONA):
        - Computes Fisher information online to estimate parameter importance
        - Detects task boundaries via gradient distribution shift (z-score)
        - Constrains gradients to prevent catastrophic forgetting
        """
        error = predicted - actual
        feature_dict = features.to_dict()

        # Compute gradients as list (for EWC++ integration)
        gradients = []
        current_weights = []
        for feature_name in self.FEATURE_NAMES:
            feature_value = feature_dict.get(feature_name, 0.0)
            gradient = 2 * error * feature_value
            gradients.append(gradient)
            current_weights.append(self.confidence_model.weights.get(feature_name, 0.0))

        # EWC++ integration: update Fisher, detect boundaries, apply constraints
        if self.enable_ewc and self.ewc is not None:
            # Update Fisher information with current gradients
            self.ewc.update_fisher(gradients)

            # Check for task boundary (distribution shift)
            if self.ewc.detect_task_boundary(gradients):
                # Start new task - save current knowledge
                new_task_id = self.ewc.start_new_task(current_weights)
                self.task_boundaries_detected += 1
                self.last_task_boundary_time = time.time()

            # Apply EWC constraints to prevent forgetting
            constrained_gradients = self.ewc.apply_constraints(gradients, current_weights)

            # Use constrained gradients for update
            gradients = constrained_gradients

        # Update each weight (using potentially constrained gradients)
        for i, feature_name in enumerate(self.FEATURE_NAMES):
            if i < len(gradients):
                gradient = gradients[i]
                current_weight = self.confidence_model.weights.get(feature_name, 0.0)
                new_weight = current_weight - self.LEARNING_RATE * gradient

                # Clip weights to reasonable range
                self.confidence_model.weights[feature_name] = max(-1.0, min(1.0, new_weight))

        # Update bias
        bias_gradient = 2 * error
        self.confidence_model.bias -= self.LEARNING_RATE * bias_gradient
        self.confidence_model.bias = max(0.0, min(1.0, self.confidence_model.bias))

        # Update EWC++ with new weights
        if self.enable_ewc and self.ewc is not None:
            new_weights = [
                self.confidence_model.weights.get(name, 0.0)
                for name in self.FEATURE_NAMES
            ]
            self.ewc.update_current_weights(new_weights)

        # Update training count and accuracy
        self.confidence_model.training_examples += 1

        # Update running accuracy (exponential moving average)
        accuracy_sample = 1.0 - abs(error)
        self.confidence_model.accuracy = (
            (1 - self.EMA_ALPHA) * self.confidence_model.accuracy +
            self.EMA_ALPHA * accuracy_sample
        )

        self.confidence_model.last_updated = time.time()
        self._save_model()

        # Save EWC state periodically (every 10 updates)
        if self.enable_ewc and self.confidence_model.training_examples % 10 == 0:
            self._save_ewc_state()

    def _update_patterns(self, features: FeatureVector, success: bool):
        """Update pattern recognition based on features and outcome."""
        pattern_id = self._compute_pattern_id(features)

        if pattern_id in self.patterns:
            pattern = self.patterns[pattern_id]
            # Update with exponential moving average
            pattern.success_rate = (
                (1 - self.EMA_ALPHA) * pattern.success_rate +
                self.EMA_ALPHA * (1.0 if success else 0.0)
            )
            pattern.sample_size += 1
            pattern.last_seen = time.time()
        else:
            # Create new pattern
            feature_dict = features.to_dict()
            signature = {}
            for name, value in feature_dict.items():
                # Create range around the value
                margin = max(0.1, abs(value) * 0.2)
                signature[name] = (value - margin, value + margin)

            pattern = Pattern(
                id=pattern_id,
                description=f"Pattern {len(self.patterns) + 1}",
                feature_signature=signature,
                success_rate=1.0 if success else 0.0,
                sample_size=1
            )
            self.patterns[pattern_id] = pattern

        # Save pattern
        self._save_pattern(pattern)

    def _compute_pattern_id(self, features: FeatureVector) -> str:
        """Compute pattern ID based on feature buckets."""
        feature_dict = features.to_dict()
        buckets = []

        for name in sorted(self.FEATURE_NAMES):
            value = feature_dict.get(name, 0.0)
            # Bucket into 5 ranges: very_low, low, medium, high, very_high
            if value < 0.2:
                bucket = 'VL'
            elif value < 0.4:
                bucket = 'L'
            elif value < 0.6:
                bucket = 'M'
            elif value < 0.8:
                bucket = 'H'
            else:
                bucket = 'VH'
            buckets.append(f"{name[:3]}:{bucket}")

        pattern_str = "|".join(buckets)
        return hashlib.md5(pattern_str.encode()).hexdigest()[:12]

    def _save_pattern(self, pattern: Pattern):
        """Save pattern to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO patterns
                (id, description, feature_signature, success_rate, sample_size, last_seen)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                pattern.id,
                pattern.description,
                json.dumps(pattern.feature_signature),
                pattern.success_rate,
                pattern.sample_size,
                pattern.last_seen
            ))

    def _update_source_reliability(self, source_id: str, success: bool):
        """Update reliability score for a source."""
        if source_id not in self.source_reliability:
            self.source_reliability[source_id] = SourceReliability(source_id=source_id)

        source = self.source_reliability[source_id]
        source.sample_size += 1

        if success:
            source.successful_verifications += 1
        else:
            source.failed_verifications += 1

        # Calculate reliability with Bayesian smoothing
        # Prior: 50% reliability with weight of 2 samples
        prior_weight = 2
        total = source.sample_size + prior_weight
        source.reliability_score = (
            (source.successful_verifications + prior_weight * 0.5) / total
        )
        source.last_updated = time.time()

        # Save to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO source_reliability
                (source_id, reliability_score, sample_size,
                 successful_verifications, failed_verifications, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                source.source_id,
                source.reliability_score,
                source.sample_size,
                source.successful_verifications,
                source.failed_verifications,
                source.last_updated
            ))

    def predict_confidence(self, features: FeatureVector) -> float:
        """
        Predict confidence score based on learned model.

        Uses linear combination of features with learned weights,
        passed through sigmoid for 0-1 output.

        Args:
            features: Feature vector for the claim

        Returns:
            Predicted confidence score (0.0 to 1.0)
        """
        feature_dict = features.to_dict()
        weighted_sum = self.confidence_model.bias

        for feature_name, weight in self.confidence_model.weights.items():
            if feature_name in feature_dict:
                weighted_sum += weight * feature_dict[feature_name]

        return self._sigmoid(weighted_sum)

    async def get_confidence_adjustment(
        self,
        features: FeatureVector,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get confidence adjustment based on learned patterns.

        Args:
            features: Feature vector for the claim
            context: Optional context information

        Returns:
            Dictionary with adjustment recommendation
        """
        predicted = self.predict_confidence(features)
        pattern_id = self._compute_pattern_id(features)

        adjustment = {
            'predicted_confidence': predicted,
            'pattern_match': None,
            'source_adjustments': [],
            'recommendation': 'none'
        }

        # Check for matching pattern
        if pattern_id in self.patterns:
            pattern = self.patterns[pattern_id]
            if pattern.sample_size >= self.MIN_SAMPLES_FOR_PATTERN:
                adjustment['pattern_match'] = {
                    'id': pattern.id,
                    'success_rate': pattern.success_rate,
                    'sample_size': pattern.sample_size,
                    'confidence': pattern.success_rate
                }

                # Recommend based on pattern
                if pattern.success_rate >= 0.8:
                    adjustment['recommendation'] = 'increase'
                elif pattern.success_rate <= 0.3:
                    adjustment['recommendation'] = 'decrease'

        return adjustment

    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get statistics about recognized patterns."""
        if not self.patterns:
            return {
                'total_patterns': 0,
                'reliable_patterns': 0,
                'average_success_rate': 0.0,
                'patterns': []
            }

        reliable = [p for p in self.patterns.values()
                   if p.sample_size >= self.MIN_SAMPLES_FOR_PATTERN]

        avg_success = (
            sum(p.success_rate for p in self.patterns.values()) / len(self.patterns)
            if self.patterns else 0.0
        )

        return {
            'total_patterns': len(self.patterns),
            'reliable_patterns': len(reliable),
            'average_success_rate': avg_success,
            'patterns': [
                {
                    'id': p.id,
                    'success_rate': p.success_rate,
                    'sample_size': p.sample_size,
                    'description': p.description
                }
                for p in sorted(
                    self.patterns.values(),
                    key=lambda x: x.sample_size,
                    reverse=True
                )[:10]
            ]
        }

    def get_model_statistics(self) -> Dict[str, Any]:
        """Get statistics about the learning model."""
        stats = {
            'training_examples': self.confidence_model.training_examples,
            'accuracy': self.confidence_model.accuracy,
            'last_updated': self.confidence_model.last_updated,
            'weights': dict(self.confidence_model.weights),
            'bias': self.confidence_model.bias,
            'feature_importance': self._compute_feature_importance(),
            'ewc_enabled': self.enable_ewc
        }

        # Include EWC summary if enabled
        if self.enable_ewc and self.ewc is not None:
            ewc_stats = self.ewc.get_statistics()
            stats['ewc_summary'] = {
                'tasks_stored': ewc_stats['tasks_stored'],
                'current_task_id': ewc_stats['current_task_id'],
                'lambda_value': ewc_stats['lambda_value'],
                'task_boundaries_detected': self.task_boundaries_detected
            }

        return stats

    def get_ewc_statistics(self) -> Dict[str, Any]:
        """
        Get detailed EWC++ statistics for monitoring.

        Returns comprehensive information about:
        - Task memory (stored tasks and their Fisher information)
        - Current Fisher information estimates
        - Lambda (regularization strength) scheduling
        - Task boundary detection history
        - Gradient distribution tracking
        """
        if not self.enable_ewc or self.ewc is None:
            return {
                'enabled': False,
                'message': 'EWC++ is not enabled'
            }

        ewc_stats = self.ewc.get_statistics()

        # Add additional tracking info
        ewc_stats['enabled'] = True
        ewc_stats['task_boundaries_detected_total'] = self.task_boundaries_detected
        ewc_stats['last_task_boundary_time'] = self.last_task_boundary_time

        # Compute regularization loss for monitoring
        if self.confidence_model.weights:
            current_weights = [
                self.confidence_model.weights.get(name, 0.0)
                for name in self.FEATURE_NAMES
            ]
            ewc_stats['current_regularization_loss'] = self.ewc.regularization_loss(current_weights)
        else:
            ewc_stats['current_regularization_loss'] = 0.0

        # Feature-level Fisher importance
        ewc_stats['feature_fisher'] = {
            name: self.ewc.current_fisher[i] if i < len(self.ewc.current_fisher) else 0.0
            for i, name in enumerate(self.FEATURE_NAMES)
        }

        return ewc_stats

    def _compute_feature_importance(self) -> Dict[str, float]:
        """Compute normalized feature importance from weights."""
        weights = self.confidence_model.weights
        if not weights:
            return {}

        total_abs = sum(abs(w) for w in weights.values())
        if total_abs == 0:
            return {k: 0.0 for k in weights}

        return {
            name: abs(weight) / total_abs
            for name, weight in sorted(
                weights.items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )
        }

    def get_source_rankings(self, min_sample_size: int = 5) -> List[Dict[str, Any]]:
        """
        Get ranked list of sources by reliability.

        Args:
            min_sample_size: Minimum samples for inclusion

        Returns:
            List of sources sorted by reliability
        """
        qualified = [
            s for s in self.source_reliability.values()
            if s.sample_size >= min_sample_size
        ]

        return [
            {
                'source_id': s.source_id,
                'reliability_score': s.reliability_score,
                'sample_size': s.sample_size,
                'success_rate': (
                    s.successful_verifications / s.sample_size
                    if s.sample_size > 0 else 0.0
                )
            }
            for s in sorted(qualified, key=lambda x: x.reliability_score, reverse=True)
        ]

    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics about the learning system."""
        with sqlite3.connect(self.db_path) as conn:
            record_count = conn.execute(
                "SELECT COUNT(*) FROM learning_records"
            ).fetchone()[0]

            outcome_counts = dict(conn.execute(
                "SELECT outcome, COUNT(*) FROM learning_records GROUP BY outcome"
            ).fetchall())

        return {
            'total_records': record_count,
            'outcome_distribution': outcome_counts,
            'model': self.get_model_statistics(),
            'patterns': self.get_pattern_statistics(),
            'sources': {
                'tracked': len(self.source_reliability),
                'top_sources': self.get_source_rankings()[:5]
            }
        }

    def reset(self):
        """Reset the learning system (for testing)."""
        self.learning_records.clear()
        self.patterns.clear()
        self.source_reliability.clear()
        self.confidence_model = LearningModel()
        self._initialize_weights()

        # Reset EWC++ state if enabled
        if self.enable_ewc:
            ewc_config = EwcConfig(
                param_count=len(self.FEATURE_NAMES),
                lambda_initial=2000.0,
                lambda_max=15000.0,
                fisher_ema_alpha=0.95,
                task_boundary_threshold=2.0,
                min_samples_for_fisher=100
            )
            self.ewc = EwcPlusPlus(ewc_config)
            self.task_boundaries_detected = 0
            self.last_task_boundary_time = None

        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                DELETE FROM learning_records;
                DELETE FROM patterns;
                DELETE FROM source_reliability;
            """)
            # Clear EWC state
            if self.enable_ewc:
                conn.execute("DELETE FROM ewc_state")


# Singleton instance
_continuous_learning: Optional[ContinuousLearning] = None


def get_continuous_learning(db_path: Optional[Path] = None) -> ContinuousLearning:
    """Get or create the continuous learning singleton."""
    global _continuous_learning
    if _continuous_learning is None:
        _continuous_learning = ContinuousLearning(db_path)
    return _continuous_learning


def register_continuous_learning_tools(app, db_path: Optional[Path] = None) -> ContinuousLearning:
    """
    Register continuous learning MCP tools.

    Args:
        app: FastMCP application
        db_path: Optional database path

    Returns:
        ContinuousLearning instance
    """
    cl = get_continuous_learning(db_path)

    @app.tool()
    async def cl_learn_from_correction(
        claim: str,
        original_confidence: float,
        corrected_confidence: float,
        provider_id: str,
        reasoning: str,
        features: Optional[Dict[str, float]] = None,
        suggested_sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Learn from a provider correction.

        Updates the model weights using gradient descent based on
        the difference between original and corrected confidence.

        Args:
            claim: The claim that was verified
            original_confidence: Original confidence score (0.0-1.0)
            corrected_confidence: Provider's corrected score (0.0-1.0)
            provider_id: ID of the providing source
            reasoning: Reason for the correction
            features: Optional feature vector as dictionary
            suggested_sources: Optional list of source references
        """
        feedback = ProviderFeedback(
            provider_id=provider_id,
            corrected_confidence=corrected_confidence,
            reasoning=reasoning,
            suggested_sources=suggested_sources or []
        )

        feature_vector = FeatureVector.from_dict(features or {})

        record = await cl.learn_from_correction(
            claim=claim,
            original_confidence=original_confidence,
            feedback=feedback,
            features=feature_vector
        )

        return {
            'record_id': record.id,
            'outcome': record.outcome.value,
            'model_accuracy': cl.confidence_model.accuracy,
            'training_examples': cl.confidence_model.training_examples
        }

    @app.tool()
    async def cl_predict_confidence(
        features: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Predict confidence score based on features.

        Uses the learned gradient descent model to predict
        confidence for a given feature vector.

        Args:
            features: Feature vector as dictionary with keys like
                     citation_count, peer_reviewed_ratio, etc.
        """
        feature_vector = FeatureVector.from_dict(features)
        predicted = cl.predict_confidence(feature_vector)
        adjustment = await cl.get_confidence_adjustment(feature_vector)

        return {
            'predicted_confidence': predicted,
            'pattern_match': adjustment.get('pattern_match'),
            'recommendation': adjustment.get('recommendation', 'none')
        }

    @app.tool()
    async def cl_get_model_stats() -> Dict[str, Any]:
        """
        Get learning model statistics.

        Returns training progress, accuracy, feature importance,
        and weight values.
        """
        return cl.get_model_statistics()

    @app.tool()
    async def cl_get_pattern_stats() -> Dict[str, Any]:
        """
        Get pattern recognition statistics.

        Returns information about recognized patterns and their
        success rates.
        """
        return cl.get_pattern_statistics()

    @app.tool()
    async def cl_get_source_rankings(
        min_samples: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get source reliability rankings.

        Returns sources ranked by reliability score, filtered
        by minimum sample size.

        Args:
            min_samples: Minimum samples required for inclusion
        """
        return cl.get_source_rankings(min_samples)

    @app.tool()
    async def cl_status() -> Dict[str, Any]:
        """
        Get continuous learning system status.

        Returns comprehensive metrics about the learning system
        including model stats, patterns, and source rankings.
        """
        return cl.get_metrics()

    @app.tool()
    async def cl_get_ewc_stats() -> Dict[str, Any]:
        """
        Get EWC++ (Elastic Weight Consolidation) statistics.

        Returns detailed EWC++ state including:
        - Whether EWC++ is enabled
        - Current lambda (regularization strength)
        - Number of consolidated tasks
        - Task boundary detection stats
        - Fisher information per feature
        - Current regularization loss

        EWC++ prevents catastrophic forgetting by penalizing
        changes to important parameters learned from past tasks.
        """
        return cl.get_ewc_statistics()

    return cl


# Export public interface
__all__ = [
    'ContinuousLearning',
    'get_continuous_learning',
    'register_continuous_learning_tools',
    'LearningRecord',
    'LearningOutcome',
    'FeatureVector',
    'ProviderFeedback',
    'Correction',
    'LearningModel',
    'Pattern',
    'SourceReliability',
    # EWC++ exports (ported from SONA)
    'EwcConfig',
    'TaskFisher',
    'EwcPlusPlus',
]

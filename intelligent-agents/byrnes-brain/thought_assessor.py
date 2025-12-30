#!/usr/bin/env python3
"""
Thought Assessor - Learns to PREDICT when Steering Subsystem will fire

Inspired by Steve Byrnes' brain architecture theory:
- The amygdala learns to predict subcortical (innate) responses
- This allows abstract concepts (words, ideas) to trigger innate responses
- Example: The word "spider" triggers the same fear as seeing a spider

Key Insight:
- Don't wait for Steering (innate detectors) to fire
- Learn to PREDICT when it will fire based on abstract features
- This enables "pre-emptive adjustment" of actions

Architecture:
    LearningSubsystem (cortex-like)
           ↓ abstract features
    ThoughtAssessor (amygdala-like)
           ↓ predictions
    SteeringSubsystem (innate detectors)
           ↓ actual responses
    ThoughtAssessor.learn() ← prediction error

Usage:
    assessor = ThoughtAssessor()

    # Before action: predict Steering response
    predictions = await assessor.predict(action)
    if predictions['block_probability'] > 0.8:
        action = adjust_action(action, predictions)

    # After action: learn from actual response
    await assessor.learn(action, predictions, actual_response)
"""

import json
import time
import hashlib
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from collections import defaultdict
import math

# Import innate detectors for prediction targets
try:
    from innate_detectors import (
        InnateDetectorSystem,
        Severity,
        get_innate_detector_system
    )
    INNATE_AVAILABLE = True
except ImportError:
    INNATE_AVAILABLE = False

# Import omnidirectional memory for experience-based inference
try:
    from omnidirectional_memory import (
        OmnidirectionalMemory,
        get_omnidirectional_memory,
        store_tool_experience,
    )
    OMNI_MEMORY_AVAILABLE = True
except ImportError:
    OMNI_MEMORY_AVAILABLE = False


# =============================================================================
# MULTI-STAGE CURRICULUM
# =============================================================================
# Inspired by Byrnes' multi-stage loss function curriculum:
# Different learning stages focus on different aspects with different intensities
# =============================================================================

@dataclass
class CurriculumStage:
    """Definition of a curriculum learning stage"""
    name: str
    learning_rate: float
    min_observations: int  # Minimum observations before advancing
    accuracy_threshold: float  # Required accuracy to advance
    focus_detectors: List[str]  # Which detectors to prioritize
    difficulty_range: Tuple[float, float]  # (min, max) difficulty for examples
    description: str


class CurriculumManager:
    """
    Multi-stage curriculum for progressive learning.

    Based on Byrnes' insight that brains use different loss functions
    at different developmental stages:
    - Stage 1: Bootstrap with obvious examples (high learning rate)
    - Stage 2: Refine with moderate examples (medium learning rate)
    - Stage 3: Fine-tune with subtle examples (low learning rate)
    - Stage 4: Maintain with continuous learning (adaptive rate)
    """

    # Define curriculum stages
    STAGES = [
        CurriculumStage(
            name="bootstrap",
            learning_rate=0.3,
            min_observations=20,
            accuracy_threshold=0.6,
            focus_detectors=["security_threat", "data_corruption"],
            difficulty_range=(0.0, 0.3),  # Easy examples only
            description="Learning obvious patterns with high confidence"
        ),
        CurriculumStage(
            name="foundation",
            learning_rate=0.2,
            min_observations=50,
            accuracy_threshold=0.7,
            focus_detectors=["security_threat", "production_violation", "data_corruption"],
            difficulty_range=(0.2, 0.6),  # Easy to moderate
            description="Building foundation with moderate examples"
        ),
        CurriculumStage(
            name="refinement",
            learning_rate=0.1,
            min_observations=100,
            accuracy_threshold=0.8,
            focus_detectors=["security_threat", "production_violation",
                           "resource_exhaustion", "data_corruption", "privacy_violation"],
            difficulty_range=(0.4, 0.8),  # Moderate to hard
            description="Refining with challenging examples"
        ),
        CurriculumStage(
            name="mastery",
            learning_rate=0.05,
            min_observations=200,
            accuracy_threshold=0.9,
            focus_detectors=["security_threat", "production_violation",
                           "resource_exhaustion", "data_corruption", "privacy_violation"],
            difficulty_range=(0.6, 1.0),  # Hard examples
            description="Mastering subtle edge cases"
        ),
        CurriculumStage(
            name="maintenance",
            learning_rate=0.02,
            min_observations=float('inf'),  # Never advance past this
            accuracy_threshold=1.0,
            focus_detectors=["security_threat", "production_violation",
                           "resource_exhaustion", "data_corruption", "privacy_violation"],
            difficulty_range=(0.0, 1.0),  # All examples
            description="Continuous maintenance learning"
        ),
    ]

    def __init__(self, persist_path: Optional[str] = None):
        self.current_stage_idx = 0
        self.stage_observations = 0
        self.stage_correct = 0
        self.stage_history: List[dict] = []

        # Track per-detector progress
        self.detector_accuracy: Dict[str, float] = {
            "security_threat": 0.5,
            "production_violation": 0.5,
            "resource_exhaustion": 0.5,
            "data_corruption": 0.5,
            "privacy_violation": 0.5,
        }

        self.persist_path = persist_path or str(
            Path.home() / '.claude' / 'curriculum_state.json'
        )
        self._load_state()

    @property
    def current_stage(self) -> CurriculumStage:
        return self.STAGES[self.current_stage_idx]

    @property
    def learning_rate(self) -> float:
        """Get current learning rate based on stage"""
        return self.current_stage.learning_rate

    @property
    def stage_accuracy(self) -> float:
        """Current stage accuracy"""
        if self.stage_observations == 0:
            return 0.0
        return self.stage_correct / self.stage_observations

    def score_example_difficulty(self, features: 'AbstractFeatures',
                                  actual_blocked: bool) -> float:
        """
        Score how difficult an example is for learning.

        Difficulty factors:
        - Ambiguous features (not clearly safe or dangerous)
        - Missing strong indicators
        - Edge cases

        Returns: 0.0 (trivial) to 1.0 (very difficult)
        """
        difficulty = 0.5  # Start at medium

        # Clear indicators make it easier
        if features.mentions_deletion and actual_blocked:
            difficulty -= 0.2  # Obviously dangerous
        if features.mentions_credentials and actual_blocked:
            difficulty -= 0.15
        if features.mentions_test_mock and not actual_blocked:
            difficulty -= 0.1  # Obviously test

        # Ambiguous cases are harder
        if features.tool_category == "read":
            difficulty += 0.1  # Reads are usually safe, but not always
        if features.is_test_file and features.mentions_production:
            difficulty += 0.2  # Conflicting signals
        if features.mentions_placeholder and features.has_code:
            difficulty += 0.15  # Real code with placeholders

        # Content analysis ambiguity
        if features.content_length > 1000 and not features.has_code:
            difficulty += 0.1  # Large non-code content is ambiguous
        if features.nesting_depth > 3:
            difficulty += 0.1  # Complex logic

        # Edge case: system operations that are safe
        if features.has_system_commands and not actual_blocked:
            difficulty += 0.25  # Learning safe system ops is hard

        return max(0.0, min(1.0, difficulty))

    def should_learn_example(self, difficulty: float) -> bool:
        """
        Determine if this example is appropriate for current stage.
        Examples outside the difficulty range are skipped.
        """
        min_diff, max_diff = self.current_stage.difficulty_range
        return min_diff <= difficulty <= max_diff

    def get_detector_weight(self, detector: str) -> float:
        """
        Get learning weight for a detector based on curriculum focus.
        Focused detectors get higher weight in current stage.
        """
        if detector in self.current_stage.focus_detectors:
            return 1.5  # Prioritize
        return 0.8  # Still learn, but less emphasis

    def record_observation(self, prediction_error: float,
                          detector_errors: Dict[str, float],
                          difficulty: float) -> dict:
        """
        Record an observation and check for stage advancement.

        Returns status dict with stage info.
        """
        self.stage_observations += 1

        # Consider it correct if average error < 0.3
        correct = prediction_error < 0.3
        if correct:
            self.stage_correct += 1

        # Update detector-specific accuracy
        for detector, error in detector_errors.items():
            # Exponential moving average
            alpha = 0.1
            self.detector_accuracy[detector] = (
                (1 - alpha) * self.detector_accuracy.get(detector, 0.5) +
                alpha * (1.0 - error)
            )

        # Record in history
        self.stage_history.append({
            'stage': self.current_stage.name,
            'error': prediction_error,
            'difficulty': difficulty,
            'correct': correct,
        })

        # Check for advancement
        advanced = self._check_advancement()

        self._save_state()

        return {
            'stage': self.current_stage.name,
            'stage_idx': self.current_stage_idx,
            'observations': self.stage_observations,
            'accuracy': self.stage_accuracy,
            'threshold': self.current_stage.accuracy_threshold,
            'advanced': advanced,
            'learning_rate': self.learning_rate,
            'detector_accuracy': self.detector_accuracy.copy(),
        }

    def _check_advancement(self) -> bool:
        """Check if ready to advance to next stage"""
        stage = self.current_stage

        # Can't advance past maintenance
        if self.current_stage_idx >= len(self.STAGES) - 1:
            return False

        # Check minimum observations
        if self.stage_observations < stage.min_observations:
            return False

        # Check accuracy threshold
        if self.stage_accuracy < stage.accuracy_threshold:
            return False

        # Check focus detector accuracy
        focus_accuracy = sum(
            self.detector_accuracy.get(d, 0)
            for d in stage.focus_detectors
        ) / len(stage.focus_detectors)

        if focus_accuracy < stage.accuracy_threshold:
            return False

        # Advance!
        self._advance_stage()
        return True

    def _advance_stage(self):
        """Advance to next curriculum stage"""
        old_stage = self.current_stage.name
        self.current_stage_idx += 1
        self.stage_observations = 0
        self.stage_correct = 0

        # Log advancement
        self.stage_history.append({
            'event': 'stage_advance',
            'from': old_stage,
            'to': self.current_stage.name,
            'timestamp': time.time(),
        })

    def get_curriculum_summary(self) -> dict:
        """Get comprehensive curriculum status"""
        return {
            'current_stage': self.current_stage.name,
            'stage_description': self.current_stage.description,
            'stage_idx': self.current_stage_idx,
            'total_stages': len(self.STAGES),
            'progress': f"{self.current_stage_idx + 1}/{len(self.STAGES)}",
            'stage_observations': self.stage_observations,
            'stage_accuracy': self.stage_accuracy,
            'accuracy_threshold': self.current_stage.accuracy_threshold,
            'learning_rate': self.learning_rate,
            'difficulty_range': self.current_stage.difficulty_range,
            'focus_detectors': self.current_stage.focus_detectors,
            'detector_accuracy': self.detector_accuracy,
            'ready_to_advance': self._is_ready_to_advance(),
        }

    def _is_ready_to_advance(self) -> bool:
        """Check if close to advancement without actually advancing"""
        stage = self.current_stage
        if self.current_stage_idx >= len(self.STAGES) - 1:
            return False
        return (self.stage_observations >= stage.min_observations * 0.8 and
                self.stage_accuracy >= stage.accuracy_threshold * 0.9)

    def _save_state(self):
        """Persist curriculum state"""
        try:
            state = {
                'stage_idx': self.current_stage_idx,
                'stage_observations': self.stage_observations,
                'stage_correct': self.stage_correct,
                'detector_accuracy': self.detector_accuracy,
                'history_length': len(self.stage_history),
                'recent_history': self.stage_history[-50:],  # Keep last 50
            }
            os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
            with open(self.persist_path, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass

    def _load_state(self):
        """Load curriculum state"""
        try:
            if os.path.exists(self.persist_path):
                with open(self.persist_path, 'r') as f:
                    state = json.load(f)
                self.current_stage_idx = state.get('stage_idx', 0)
                self.stage_observations = state.get('stage_observations', 0)
                self.stage_correct = state.get('stage_correct', 0)
                self.detector_accuracy = state.get('detector_accuracy', self.detector_accuracy)
                self.stage_history = state.get('recent_history', [])
        except Exception:
            pass


@dataclass
class AbstractFeatures:
    """
    Abstract representation of an action.
    These are the "cortical" features that the Thought Assessor learns from.
    """
    # Tool metadata
    tool_type: str = ""
    tool_category: str = ""  # write, read, execute, spawn

    # Content analysis (abstract, not raw)
    content_length: int = 0
    has_code: bool = False
    has_comments: bool = False
    language_detected: str = ""

    # Semantic markers (presence, not content)
    has_file_operations: bool = False
    has_network_operations: bool = False
    has_database_operations: bool = False
    has_system_commands: bool = False

    # Risk indicators (abstract)
    mentions_deletion: bool = False
    mentions_credentials: bool = False
    mentions_production: bool = False
    mentions_test_mock: bool = False
    mentions_placeholder: bool = False

    # Complexity indicators
    nesting_depth: int = 0
    unique_identifiers: int = 0

    # Context
    file_extension: str = ""
    is_config_file: bool = False
    is_test_file: bool = False

    def to_vector(self) -> List[float]:
        """Convert features to numeric vector for prediction model"""
        return [
            # Tool category one-hot
            1.0 if self.tool_category == "write" else 0.0,
            1.0 if self.tool_category == "execute" else 0.0,
            1.0 if self.tool_category == "spawn" else 0.0,

            # Content features
            min(self.content_length / 10000, 1.0),  # Normalized
            1.0 if self.has_code else 0.0,
            1.0 if self.has_comments else 0.0,

            # Semantic markers
            1.0 if self.has_file_operations else 0.0,
            1.0 if self.has_network_operations else 0.0,
            1.0 if self.has_database_operations else 0.0,
            1.0 if self.has_system_commands else 0.0,

            # Risk indicators
            1.0 if self.mentions_deletion else 0.0,
            1.0 if self.mentions_credentials else 0.0,
            1.0 if self.mentions_production else 0.0,
            1.0 if self.mentions_test_mock else 0.0,
            1.0 if self.mentions_placeholder else 0.0,

            # Complexity
            min(self.nesting_depth / 10, 1.0),
            min(self.unique_identifiers / 100, 1.0),

            # File type
            1.0 if self.is_config_file else 0.0,
            1.0 if self.is_test_file else 0.0,
        ]


@dataclass
class PredictionResult:
    """Result of predicting Steering response"""
    # Overall probability of blocking
    block_probability: float = 0.0

    # Per-detector predictions
    detector_probabilities: Dict[str, float] = field(default_factory=dict)

    # Predicted severity if triggered
    predicted_severity: str = "low"

    # Confidence in prediction (based on training data)
    confidence: float = 0.0

    # Suggested adjustments (if block likely)
    suggested_adjustments: List[str] = field(default_factory=list)

    # Features used for prediction
    features: Optional[AbstractFeatures] = None

    def to_dict(self) -> dict:
        return {
            'block_probability': self.block_probability,
            'detector_probabilities': self.detector_probabilities,
            'predicted_severity': self.predicted_severity,
            'confidence': self.confidence,
            'suggested_adjustments': self.suggested_adjustments,
        }


class FeatureExtractor:
    """
    Extracts abstract features from actions.
    This is the "cortical" representation layer.
    """

    # Patterns for semantic detection (abstract, not blocking)
    DELETION_PATTERNS = re.compile(
        r'\b(delete|remove|drop|truncate|destroy|purge|erase|wipe)\b',
        re.IGNORECASE
    )
    CREDENTIAL_PATTERNS = re.compile(
        r'\b(password|secret|key|token|credential|api.?key|auth)\b',
        re.IGNORECASE
    )
    PRODUCTION_PATTERNS = re.compile(
        r'\b(production|prod|live|release|deploy)\b',
        re.IGNORECASE
    )
    TEST_MOCK_PATTERNS = re.compile(
        r'\b(test|mock|fake|dummy|stub|poc|demo|prototype|example)\b',
        re.IGNORECASE
    )
    PLACEHOLDER_PATTERNS = re.compile(
        r'\b(todo|fixme|xxx|placeholder|lorem|ipsum|tbd|coming.?soon)\b',
        re.IGNORECASE
    )
    FILE_OP_PATTERNS = re.compile(
        r'\b(open|read|write|close|file|path|directory|folder)\b',
        re.IGNORECASE
    )
    NETWORK_OP_PATTERNS = re.compile(
        r'\b(http|https|fetch|request|curl|wget|socket|api|endpoint)\b',
        re.IGNORECASE
    )
    DATABASE_OP_PATTERNS = re.compile(
        r'\b(sql|query|database|db|table|insert|update|select|mongo)\b',
        re.IGNORECASE
    )
    SYSTEM_CMD_PATTERNS = re.compile(
        r'\b(sudo|chmod|chown|kill|ps|exec|system|shell|bash)\b',
        re.IGNORECASE
    )

    # Code detection
    CODE_PATTERNS = re.compile(
        r'(def\s+\w+|class\s+\w+|function\s+\w+|const\s+\w+|let\s+\w+|import\s+|from\s+\w+\s+import)',
        re.IGNORECASE
    )
    COMMENT_PATTERNS = re.compile(r'(#.*$|//.*$|/\*|\*/|""")', re.MULTILINE)

    # Config file extensions
    CONFIG_EXTENSIONS = {'.json', '.yaml', '.yml', '.toml', '.ini', '.conf', '.cfg', '.env'}
    TEST_PATTERNS = re.compile(r'(test_|_test\.py|\.test\.|spec\.)')

    def extract(self, action: dict) -> AbstractFeatures:
        """Extract abstract features from an action"""
        # Handle both hook format (tool_name/tool_input) and legacy (tool/arguments)
        tool = action.get('tool_name', action.get('tool', ''))
        args = action.get('tool_input', action.get('arguments', {}))

        features = AbstractFeatures()

        # Tool metadata
        features.tool_type = tool
        features.tool_category = self._categorize_tool(tool)

        # Get content to analyze
        content = self._get_content(tool, args)
        file_path = self._get_file_path(args)

        # Content analysis
        features.content_length = len(content)
        features.has_code = bool(self.CODE_PATTERNS.search(content))
        features.has_comments = bool(self.COMMENT_PATTERNS.search(content))
        features.language_detected = self._detect_language(content, file_path)

        # Semantic markers
        features.has_file_operations = bool(self.FILE_OP_PATTERNS.search(content))
        features.has_network_operations = bool(self.NETWORK_OP_PATTERNS.search(content))
        features.has_database_operations = bool(self.DATABASE_OP_PATTERNS.search(content))
        features.has_system_commands = bool(self.SYSTEM_CMD_PATTERNS.search(content))

        # Risk indicators
        features.mentions_deletion = bool(self.DELETION_PATTERNS.search(content))
        features.mentions_credentials = bool(self.CREDENTIAL_PATTERNS.search(content))
        features.mentions_production = bool(self.PRODUCTION_PATTERNS.search(content))
        features.mentions_test_mock = bool(self.TEST_MOCK_PATTERNS.search(content))
        features.mentions_placeholder = bool(self.PLACEHOLDER_PATTERNS.search(content))

        # Complexity
        features.nesting_depth = self._calculate_nesting(content)
        features.unique_identifiers = self._count_identifiers(content)

        # File context
        if file_path:
            ext = os.path.splitext(file_path)[1].lower()
            features.file_extension = ext
            features.is_config_file = ext in self.CONFIG_EXTENSIONS
            features.is_test_file = bool(self.TEST_PATTERNS.search(file_path))

        return features

    def _categorize_tool(self, tool: str) -> str:
        """Categorize tool into abstract category"""
        if tool in ['Write', 'Edit', 'MultiEdit', 'NotebookEdit']:
            return 'write'
        elif tool in ['Read', 'Glob', 'Grep', 'LS']:
            return 'read'
        elif tool in ['Bash', 'KillShell']:
            return 'execute'
        elif tool in ['Task']:
            return 'spawn'
        elif tool.startswith('mcp__'):
            return 'mcp'
        else:
            return 'other'

    def _get_content(self, tool: str, args: dict) -> str:
        """Extract content string from tool arguments"""
        parts = []

        if tool == 'Write':
            parts.append(str(args.get('content', '')))
        elif tool == 'Edit':
            parts.append(str(args.get('old_string', '')))
            parts.append(str(args.get('new_string', '')))
        elif tool == 'MultiEdit':
            for edit in args.get('edits', []):
                parts.append(str(edit.get('old_string', '')))
                parts.append(str(edit.get('new_string', '')))
        elif tool == 'Bash':
            parts.append(str(args.get('command', '')))
        elif tool == 'Task':
            parts.append(str(args.get('prompt', '')))
            parts.append(str(args.get('description', '')))

        return '\n'.join(parts)

    def _get_file_path(self, args: dict) -> str:
        """Extract file path from arguments"""
        return args.get('file_path', '')

    def _detect_language(self, content: str, file_path: str) -> str:
        """Detect programming language"""
        ext = os.path.splitext(file_path)[1].lower() if file_path else ''

        ext_to_lang = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.java': 'java', '.go': 'go', '.rs': 'rust', '.rb': 'ruby',
            '.sh': 'shell', '.bash': 'shell', '.zsh': 'shell',
        }

        return ext_to_lang.get(ext, 'unknown')

    def _calculate_nesting(self, content: str) -> int:
        """Calculate maximum nesting depth"""
        max_depth = 0
        current_depth = 0

        for char in content:
            if char in '{([':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char in '})]':
                current_depth = max(0, current_depth - 1)

        return max_depth

    def _count_identifiers(self, content: str) -> int:
        """Count unique identifiers"""
        # Simple word extraction
        words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', content)
        return len(set(words))


class PredictionModel:
    """
    Simple prediction model that learns from experience.
    Uses weighted feature matching with online learning.
    """

    def __init__(self):
        # Weights for each feature dimension per detector
        # Initialized with priors based on domain knowledge
        self.detector_weights: Dict[str, List[float]] = {
            'security_threat': self._init_security_weights(),
            'production_violation': self._init_production_weights(),
            'resource_exhaustion': self._init_resource_weights(),
            'data_corruption': self._init_corruption_weights(),
            'privacy_violation': self._init_privacy_weights(),
        }

        # Bias terms
        self.detector_bias: Dict[str, float] = {
            'security_threat': -2.0,  # Start skeptical
            'production_violation': -1.0,
            'resource_exhaustion': -2.0,
            'data_corruption': -2.0,
            'privacy_violation': -2.0,
        }

        # Learning rate
        self.learning_rate = 0.1

        # Observation counts (for confidence)
        self.observation_count = 0

        # Track recent prediction errors for analysis
        self.recent_predictions: List[float] = []
        self.max_recent = 100  # Keep last 100 predictions

    def _init_security_weights(self) -> List[float]:
        """Initialize weights for security threat detection"""
        return [
            0.5,   # write operations
            1.0,   # execute operations (higher risk)
            0.3,   # spawn
            0.2,   # content length
            0.3,   # has code
            0.0,   # has comments
            0.5,   # file operations
            0.3,   # network operations
            0.5,   # database operations
            1.0,   # system commands (high risk)
            1.5,   # mentions deletion (very high)
            1.2,   # mentions credentials (high)
            0.3,   # mentions production
            -0.3,  # mentions test/mock (lower risk)
            0.0,   # mentions placeholder
            0.2,   # nesting depth
            0.1,   # unique identifiers
            0.3,   # config file
            -0.2,  # test file (lower risk)
        ]

    def _init_production_weights(self) -> List[float]:
        """Initialize weights for production violation detection"""
        return [
            0.8,   # write operations
            0.3,   # execute operations
            0.5,   # spawn
            0.1,   # content length
            0.3,   # has code
            0.0,   # has comments
            0.2,   # file operations
            0.1,   # network operations
            0.1,   # database operations
            0.1,   # system commands
            0.0,   # mentions deletion
            0.0,   # mentions credentials
            -0.5,  # mentions production (less likely if production-aware)
            1.5,   # mentions test/mock (HIGH)
            1.5,   # mentions placeholder (HIGH)
            0.0,   # nesting depth
            -0.1,  # unique identifiers (more = more complete)
            0.0,   # config file
            0.5,   # test file (may have test patterns)
        ]

    def _init_resource_weights(self) -> List[float]:
        """Initialize weights for resource exhaustion detection"""
        return [
            0.5,   # write operations
            0.8,   # execute operations
            0.3,   # spawn
            0.3,   # content length
            0.5,   # has code
            0.0,   # has comments
            0.2,   # file operations
            0.3,   # network operations
            0.2,   # database operations
            0.5,   # system commands
            0.0,   # mentions deletion
            0.0,   # mentions credentials
            0.3,   # mentions production
            0.0,   # mentions test/mock
            0.0,   # mentions placeholder
            0.5,   # nesting depth (more = more loops)
            0.2,   # unique identifiers
            0.0,   # config file
            0.0,   # test file
        ]

    def _init_corruption_weights(self) -> List[float]:
        """Initialize weights for data corruption detection"""
        return [
            0.5,   # write operations
            0.8,   # execute operations
            0.2,   # spawn
            0.1,   # content length
            0.2,   # has code
            0.0,   # has comments
            0.8,   # file operations (high)
            0.2,   # network operations
            1.0,   # database operations (very high)
            0.8,   # system commands
            1.5,   # mentions deletion (VERY HIGH)
            0.0,   # mentions credentials
            0.5,   # mentions production
            -0.3,  # mentions test/mock (lower risk)
            0.0,   # mentions placeholder
            0.1,   # nesting depth
            0.0,   # unique identifiers
            0.5,   # config file
            -0.3,  # test file
        ]

    def _init_privacy_weights(self) -> List[float]:
        """Initialize weights for privacy violation detection"""
        return [
            0.5,   # write operations
            0.3,   # execute operations
            0.3,   # spawn
            0.2,   # content length
            0.3,   # has code
            0.0,   # has comments
            0.3,   # file operations
            0.5,   # network operations
            0.3,   # database operations
            0.2,   # system commands
            0.0,   # mentions deletion
            1.5,   # mentions credentials (VERY HIGH)
            0.3,   # mentions production
            0.0,   # mentions test/mock
            0.0,   # mentions placeholder
            0.0,   # nesting depth
            0.0,   # unique identifiers
            0.3,   # config file
            0.0,   # test file
        ]

    def predict(self, features: AbstractFeatures) -> Dict[str, float]:
        """Predict probability for each detector"""
        feature_vector = features.to_vector()
        predictions = {}

        for detector, weights in self.detector_weights.items():
            # Dot product + bias
            score = self.detector_bias[detector]
            for i, (f, w) in enumerate(zip(feature_vector, weights)):
                score += f * w

            # Sigmoid to get probability
            prob = 1.0 / (1.0 + math.exp(-score))
            predictions[detector] = prob

        return predictions

    def update(self, features: AbstractFeatures, actual: Dict[str, bool]):
        """Update weights based on prediction error"""
        feature_vector = features.to_vector()
        predictions = self.predict(features)

        total_error = 0.0
        error_count = 0

        for detector, was_triggered in actual.items():
            if detector not in self.detector_weights:
                continue

            predicted = predictions.get(detector, 0.5)
            target = 1.0 if was_triggered else 0.0
            error = target - predicted

            # Track error magnitude
            total_error += abs(error)
            error_count += 1

            # Update weights (gradient descent)
            for i in range(len(self.detector_weights[detector])):
                gradient = error * feature_vector[i] if i < len(feature_vector) else 0
                self.detector_weights[detector][i] += self.learning_rate * gradient

            # Update bias
            self.detector_bias[detector] += self.learning_rate * error

        self.observation_count += 1

        # Track recent prediction errors
        if error_count > 0:
            avg_error = total_error / error_count
            self.recent_predictions.append(avg_error)
            if len(self.recent_predictions) > self.max_recent:
                self.recent_predictions = self.recent_predictions[-self.max_recent:]

    def get_confidence(self) -> float:
        """Get confidence based on training data"""
        # More observations = higher confidence
        return min(1.0, self.observation_count / 100)


class ThoughtAssessor:
    """
    Main Thought Assessor class.
    Learns to predict when Steering (innate detectors) will fire.
    """

    def __init__(self, persist_path: Optional[str] = None):
        self.feature_extractor = FeatureExtractor()
        self.prediction_model = PredictionModel()

        # Multi-stage curriculum for progressive learning
        self.curriculum = CurriculumManager()

        # Omnidirectional memory for experience-based inference
        self.omni_memory = None
        if OMNI_MEMORY_AVAILABLE:
            self.omni_memory = get_omnidirectional_memory()

        # Persistence
        self.persist_path = persist_path or str(
            Path.home() / '.claude' / 'thought_assessor_state.json'
        )

        # History for analysis
        self.prediction_history: List[dict] = []
        self.max_history = 1000

        # Load saved state
        self._load_state()

    def predict(self, action: dict) -> PredictionResult:
        """
        Predict Steering response for a planned action.

        This is the KEY method - call BEFORE executing an action
        to predict whether it will trigger innate detectors.

        Uses two complementary prediction sources:
        1. Feature-based prediction model (fast, pattern-based)
        2. Omnidirectional memory (experience-based inference)
        """
        # Extract abstract features
        features = self.feature_extractor.extract(action)

        # Get predictions for each detector from feature model
        detector_probs = self.prediction_model.predict(features)

        # Enhance with omnidirectional memory if available
        memory_probs = {}
        if self.omni_memory:
            tool = action.get('tool_name', action.get('tool', ''))
            if tool:
                # Query memory for similar experiences
                memory_inference = self.omni_memory.infer(tool=tool)

                # Get detector probabilities from memory
                if 'detector' in memory_inference:
                    for det, prob in memory_inference['detector'].items():
                        # Normalize detector names
                        det_key = det.lower().replace(' ', '_')
                        if det_key in detector_probs:
                            memory_probs[det_key] = prob

                # Get outcome prediction from memory
                if 'outcome' in memory_inference:
                    blocked_prob = memory_inference['outcome'].get('blocked', 0)
                    # Use outcome as additional signal
                    memory_probs['_blocked'] = blocked_prob

        # Combine predictions: weighted average of feature model and memory
        combined_probs = {}
        model_weight = 0.7  # Feature model is primary
        memory_weight = 0.3  # Memory provides secondary signal

        for detector in detector_probs:
            model_prob = detector_probs[detector]
            mem_prob = memory_probs.get(detector, model_prob)  # Default to model
            combined_probs[detector] = (model_weight * model_prob +
                                        memory_weight * mem_prob)

        # Use combined probabilities
        detector_probs = combined_probs

        # Calculate overall block probability
        # Block if any critical detector has high probability
        critical_detectors = ['security_threat', 'data_corruption', 'privacy_violation']
        max_critical = max(detector_probs.get(d, 0) for d in critical_detectors)
        max_other = max(detector_probs.get(d, 0) for d in detector_probs if d not in critical_detectors)

        # Critical detectors have lower threshold
        block_prob = max(max_critical * 1.5, max_other)

        # Boost with memory's blocked probability if significant
        if '_blocked' in memory_probs and memory_probs['_blocked'] > 0.5:
            block_prob = max(block_prob, memory_probs['_blocked'] * 0.8)

        block_prob = min(1.0, block_prob)

        # Determine predicted severity
        if max_critical > 0.7:
            severity = 'critical'
        elif max_critical > 0.4 or max_other > 0.7:
            severity = 'high'
        elif max_other > 0.4:
            severity = 'medium'
        else:
            severity = 'low'

        # Generate adjustment suggestions
        suggestions = self._generate_suggestions(features, detector_probs)

        return PredictionResult(
            block_probability=block_prob,
            detector_probabilities=detector_probs,
            predicted_severity=severity,
            confidence=self.prediction_model.get_confidence(),
            suggested_adjustments=suggestions,
            features=features
        )

    def learn(self, action: dict, prediction: PredictionResult,
              actual_response: dict) -> dict:
        """
        Learn from actual Steering response with curriculum-based learning.

        Call AFTER executing an action with the actual response
        from innate detectors.

        The curriculum system:
        1. Scores example difficulty
        2. Filters examples appropriate for current stage
        3. Adjusts learning rate based on stage
        4. Tracks progress and advances stages
        """
        # Determine which detectors actually fired
        actual_triggers = {}
        alerts = actual_response.get('alerts', [])

        for detector in self.prediction_model.detector_weights.keys():
            triggered = any(a.get('detector') == detector for a in alerts)
            actual_triggers[detector] = triggered

        # Calculate prediction error
        errors = {}
        for detector, predicted_prob in prediction.detector_probabilities.items():
            actual = 1.0 if actual_triggers.get(detector, False) else 0.0
            errors[detector] = abs(predicted_prob - actual)

        avg_error = sum(errors.values()) / max(len(errors), 1)

        # Score example difficulty for curriculum
        actual_blocked = not actual_response.get('allow', True)
        difficulty = 0.5  # Default difficulty
        if prediction.features:
            difficulty = self.curriculum.score_example_difficulty(
                prediction.features, actual_blocked
            )

        # Check if example is appropriate for current curriculum stage
        should_learn = self.curriculum.should_learn_example(difficulty)

        # Apply curriculum learning rate and detector weights
        if should_learn and prediction.features:
            # Set dynamic learning rate from curriculum
            self.prediction_model.learning_rate = self.curriculum.learning_rate

            # Apply detector-specific weights for focused learning
            weighted_triggers = {}
            for detector, triggered in actual_triggers.items():
                weight = self.curriculum.get_detector_weight(detector)
                weighted_triggers[detector] = triggered
                # Adjust error contribution based on focus
                if detector in errors:
                    errors[detector] *= weight

            self.prediction_model.update(prediction.features, actual_triggers)

        # Record observation with curriculum (even if skipped for learning)
        curriculum_status = self.curriculum.record_observation(
            prediction_error=avg_error,
            detector_errors=errors,
            difficulty=difficulty
        )

        # Store in history
        history_entry = {
            'timestamp': time.time(),
            'action_tool': action.get('tool_name', action.get('tool', '')),
            'predicted_block': prediction.block_probability,
            'actual_blocked': actual_blocked,
            'prediction_error': avg_error,
            'detector_errors': errors,
            'difficulty': difficulty,
            'curriculum_stage': curriculum_status['stage'],
            'learned': should_learn,
        }
        self.prediction_history.append(history_entry)

        # Trim history
        if len(self.prediction_history) > self.max_history:
            self.prediction_history = self.prediction_history[-self.max_history:]

        # Persist state periodically
        if len(self.prediction_history) % 10 == 0:
            self._save_state()

        # Store experience in omnidirectional memory
        if self.omni_memory:
            tool = action.get('tool_name', action.get('tool', ''))
            action_str = str(action.get('tool_input', action.get('arguments', {})))[:100]

            # Determine primary detector that fired
            fired_detector = ''
            fired_severity = ''
            for alert in alerts:
                det = alert.get('detector', '')
                sev = alert.get('severity', '')
                if det:
                    fired_detector = det
                    fired_severity = sev
                    break

            # Store the experience
            self.omni_memory.store_experience({
                'tool': tool,
                'action': action_str,
                'outcome': 'blocked' if actual_blocked else 'success',
                'detector': fired_detector,
                'severity': fired_severity,
                'operation_type': prediction.features.tool_category if prediction.features else '',
                'was_predicted': prediction.block_probability > 0.5,
                'prediction_error': avg_error,
            })

        return {
            'prediction_error': avg_error,
            'detector_errors': errors,
            'learned': should_learn,
            'difficulty': difficulty,
            'curriculum': curriculum_status,
        }

    def _generate_suggestions(self, features: AbstractFeatures,
                             probs: Dict[str, float]) -> List[str]:
        """Generate suggestions based on high-probability detectors"""
        suggestions = []

        # Security suggestions
        if probs.get('security_threat', 0) > 0.5:
            if features.mentions_deletion:
                suggestions.append("Consider using safer deletion patterns with confirmation")
            if features.mentions_credentials:
                suggestions.append("Avoid hardcoding credentials; use environment variables")
            if features.has_system_commands:
                suggestions.append("Review system commands for safety")

        # Production violation suggestions
        if probs.get('production_violation', 0) > 0.5:
            if features.mentions_test_mock:
                suggestions.append("Replace mock/test patterns with production implementations")
            if features.mentions_placeholder:
                suggestions.append("Complete placeholder content before submitting")

        # Resource exhaustion suggestions
        if probs.get('resource_exhaustion', 0) > 0.5:
            if features.nesting_depth > 5:
                suggestions.append("Deep nesting may indicate complex loops; add termination conditions")

        # Data corruption suggestions
        if probs.get('data_corruption', 0) > 0.5:
            if features.has_database_operations and features.mentions_deletion:
                suggestions.append("Add transaction safety for database deletions")
            if features.has_file_operations and features.mentions_deletion:
                suggestions.append("Consider backup before file deletion operations")

        return suggestions[:3]  # Limit to top 3

    def get_learning_summary(self) -> dict:
        """Get summary of learning progress including curriculum status"""
        if not self.prediction_history:
            curriculum_summary = self.curriculum.get_curriculum_summary()
            return {
                'total_observations': 0,
                'average_error': 0.0,
                'confidence': 0.0,
                'curriculum': curriculum_summary,
                'curriculum_stage': curriculum_summary.get('current_stage', 'bootstrap'),
            }

        recent = self.prediction_history[-100:]
        errors = [h['prediction_error'] for h in recent]

        # Calculate accuracy (inverse of error)
        avg_error = sum(errors) / len(errors)
        accuracy = 1.0 - avg_error

        # Trend (improving or not)
        if len(errors) >= 20:
            first_half = sum(errors[:len(errors)//2]) / (len(errors)//2)
            second_half = sum(errors[len(errors)//2:]) / (len(errors) - len(errors)//2)
            trend = "improving" if second_half < first_half else "stable"
        else:
            trend = "learning"

        # Get curriculum summary
        curriculum_summary = self.curriculum.get_curriculum_summary()

        return {
            'total_observations': len(self.prediction_history),
            'recent_observations': len(recent),
            'average_error': avg_error,
            'accuracy': accuracy,
            'confidence': self.prediction_model.get_confidence(),
            'trend': trend,
            'curriculum': curriculum_summary,
            'curriculum_stage': curriculum_summary.get('current_stage', 'unknown'),
        }

    def get_curriculum_status(self) -> dict:
        """Get detailed curriculum status"""
        return self.curriculum.get_curriculum_summary()

    def _save_state(self):
        """Save model state to disk"""
        try:
            state = {
                'weights': self.prediction_model.detector_weights,
                'bias': self.prediction_model.detector_bias,
                'observation_count': self.prediction_model.observation_count,
                'history_summary': {
                    'total': len(self.prediction_history),
                    'recent_errors': [h['prediction_error'] for h in self.prediction_history[-20:]]
                }
            }

            os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
            with open(self.persist_path, 'w') as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            # Don't fail on persistence errors
            pass

    def _load_state(self):
        """Load model state from disk"""
        try:
            if os.path.exists(self.persist_path):
                with open(self.persist_path, 'r') as f:
                    state = json.load(f)

                self.prediction_model.detector_weights = state.get('weights', self.prediction_model.detector_weights)
                self.prediction_model.detector_bias = state.get('bias', self.prediction_model.detector_bias)
                self.prediction_model.observation_count = state.get('observation_count', 0)

        except Exception as e:
            # Start fresh on load errors
            pass


# Singleton instance
_assessor = None

def get_thought_assessor() -> ThoughtAssessor:
    """Get or create singleton ThoughtAssessor"""
    global _assessor
    if _assessor is None:
        _assessor = ThoughtAssessor()
    return _assessor


def predict_steering_response(action: dict) -> PredictionResult:
    """Convenience function for prediction"""
    return get_thought_assessor().predict(action)


def learn_from_steering(action: dict, prediction: PredictionResult,
                        actual_response: dict) -> dict:
    """Convenience function for learning"""
    return get_thought_assessor().learn(action, prediction, actual_response)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        # Run self-tests
        print("Running Thought Assessor tests...\n")

        assessor = ThoughtAssessor()

        # Test feature extraction
        print("Feature Extraction Tests:")
        test_actions = [
            {'tool': 'Write', 'arguments': {'content': 'def foo(): pass', 'file_path': 'test.py'}},
            {'tool': 'Bash', 'arguments': {'command': 'rm -rf /tmp/test'}},
            {'tool': 'Write', 'arguments': {'content': 'POC implementation with mock data'}},
        ]

        for action in test_actions:
            features = assessor.feature_extractor.extract(action)
            print(f"  Tool: {action['tool']}")
            print(f"    Category: {features.tool_category}")
            print(f"    Has code: {features.has_code}")
            print(f"    Mentions test/mock: {features.mentions_test_mock}")
            print()

        # Test prediction
        print("Prediction Tests:")
        for action in test_actions:
            prediction = assessor.predict(action)
            print(f"  Tool: {action['tool']}")
            print(f"    Block probability: {prediction.block_probability:.2%}")
            print(f"    Predicted severity: {prediction.predicted_severity}")
            print(f"    Top detectors: {sorted(prediction.detector_probabilities.items(), key=lambda x: -x[1])[:2]}")
            if prediction.suggested_adjustments:
                print(f"    Suggestions: {prediction.suggested_adjustments}")
            print()

        # Test learning
        print("Learning Test:")
        action = {'tool': 'Write', 'arguments': {'content': 'rm -rf /* dangerous'}}
        prediction = assessor.predict(action)
        print(f"  Before learning - security prob: {prediction.detector_probabilities.get('security_threat', 0):.2%}")

        # Simulate actual response (was blocked)
        actual = {'allow': False, 'alerts': [{'detector': 'security_threat'}]}
        result = assessor.learn(action, prediction, actual)
        print(f"  Prediction error: {result['prediction_error']:.2%}")

        # Predict again
        prediction2 = assessor.predict(action)
        print(f"  After learning - security prob: {prediction2.detector_probabilities.get('security_threat', 0):.2%}")

        print("\n✓ All tests passed")

    elif len(sys.argv) > 1 and sys.argv[1] == '--summary':
        assessor = ThoughtAssessor()
        summary = assessor.get_learning_summary()
        print(json.dumps(summary, indent=2))

    else:
        # Normal operation - predict from stdin
        try:
            action = json.loads(sys.stdin.read())
            prediction = predict_steering_response(action)
            print(json.dumps(prediction.to_dict(), indent=2))
        except Exception as e:
            print(json.dumps({'error': str(e)}))

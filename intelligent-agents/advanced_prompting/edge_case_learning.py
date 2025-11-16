#!/usr/bin/env python3
"""
Edge Case Learning Framework
=============================

Learns from edge cases to reduce false negatives through:
1. Boundary Detection - Identify "looks correct vs IS correct"
2. Graduated Examples - Few-shot examples (obvious → subtle → edge)
3. Pattern Mining - Extract recurring failure patterns

Stores edge cases in persistent SQLite database for continuous learning.

Usage:
    learner = EdgeCaseLearner()

    # Record edge case
    edge_case = learner.record_edge_case(
        input_text="Payment amount: $0.00",
        expected_output={"status": "rejected"},
        actual_output={"status": "accepted"},
        category="payment_validation"
    )

    # Generate examples
    examples = learner.generate_few_shot_examples(
        category="payment_validation",
        difficulty_progression=True
    )
"""

import asyncio
import json
import logging
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import hashlib

logger = logging.getLogger(__name__)


class EdgeCaseSeverity(Enum):
    """Severity levels for edge cases"""
    OBVIOUS = "obvious"        # Easy to detect failures
    SUBTLE = "subtle"          # Requires careful inspection
    BOUNDARY = "boundary"      # Decision boundary cases
    ADVERSARIAL = "adversarial"  # Deliberately tricky


class ExampleType(Enum):
    """Types of graduated examples"""
    NEGATIVE_OBVIOUS = "negative_obvious"      # Clear failure cases
    NEGATIVE_SUBTLE = "negative_subtle"        # Subtle failure cases
    POSITIVE_OBVIOUS = "positive_obvious"      # Clear success cases
    POSITIVE_SUBTLE = "positive_subtle"        # Subtle success cases
    BOUNDARY_CASE = "boundary_case"            # Edge of decision boundary


@dataclass
class EdgeCase:
    """Single edge case record"""
    id: str
    input_text: str
    expected_output: Any
    actual_output: Any
    category: str
    severity: EdgeCaseSeverity
    pattern: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    learned: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "input_text": self.input_text,
            "expected_output": json.dumps(self.expected_output),
            "actual_output": json.dumps(self.actual_output),
            "category": self.category,
            "severity": self.severity.value,
            "pattern": self.pattern,
            "context": json.dumps(self.context),
            "timestamp": self.timestamp.isoformat(),
            "learned": self.learned
        }


@dataclass
class GraduatedExample:
    """Example with difficulty progression"""
    id: str
    example_type: ExampleType
    input_text: str
    correct_output: Any
    explanation: str
    difficulty_score: float  # 0.0 (obvious) to 1.0 (adversarial)
    category: str
    related_patterns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "example_type": self.example_type.value,
            "input_text": self.input_text,
            "correct_output": json.dumps(self.correct_output),
            "explanation": self.explanation,
            "difficulty_score": self.difficulty_score,
            "category": self.category,
            "related_patterns": json.dumps(self.related_patterns)
        }


class BoundaryDetector:
    """
    Boundary Detection - Identify subtle distinctions

    Detects patterns that distinguish "looks correct" from "is correct"
    """

    # Common boundary patterns
    BOUNDARY_PATTERNS = {
        "off_by_one": [
            "range", "index", "length", "count", "iteration",
            "<=", ">=", "<", ">", "boundary"
        ],
        "null_vs_empty": [
            "null", "None", "undefined", "empty", "''", '""',
            "zero-length", "missing"
        ],
        "type_coercion": [
            "string", "number", "boolean", "conversion", "cast",
            "implicit", "coercion"
        ],
        "race_condition": [
            "concurrent", "parallel", "async", "await", "race",
            "timing", "thread", "lock"
        ],
        "unicode_normalization": [
            "unicode", "UTF-8", "encoding", "normalization",
            "combining", "characters"
        ],
        "floating_point": [
            "float", "double", "decimal", "precision", "rounding",
            "0.1", "IEEE754"
        ],
        "timezone": [
            "timezone", "UTC", "DST", "daylight", "offset",
            "local", "GMT"
        ],
        "case_sensitivity": [
            "case", "uppercase", "lowercase", "Case", "CASE",
            "insensitive", "sensitive"
        ],
        "whitespace": [
            "space", "tab", "newline", "whitespace", "trim",
            "\\n", "\\t", "\\r"
        ],
        "sql_injection": [
            "SELECT", "DROP", "';", "OR 1=1", "quote",
            "escape", "sanitize"
        ]
    }

    @staticmethod
    def detect_boundaries(
        input_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Detect boundary patterns in input

        Args:
            input_text: Input to analyze
            context: Additional context

        Returns:
            List of detected boundary pattern names
        """
        detected = []

        input_lower = input_text.lower()

        for pattern_name, keywords in BoundaryDetector.BOUNDARY_PATTERNS.items():
            for keyword in keywords:
                if keyword.lower() in input_lower:
                    detected.append(pattern_name)
                    break

        return detected

    @staticmethod
    def classify_failure(
        input_text: str,
        error_context: Optional[Dict[str, Any]] = None
    ) -> EdgeCaseSeverity:
        """
        Classify failure severity

        Args:
            input_text: Input that caused failure
            error_context: Error context

        Returns:
            EdgeCaseSeverity level
        """
        error_context = error_context or {}

        # Check for explicit indicators
        error_msg = str(error_context.get("error_message", "")).lower()

        # Adversarial indicators
        adversarial_keywords = ["malicious", "attack", "exploit", "injection"]
        if any(kw in error_msg for kw in adversarial_keywords):
            return EdgeCaseSeverity.ADVERSARIAL

        # Boundary indicators
        boundary_keywords = ["boundary", "edge", "limit", "overflow", "underflow"]
        if any(kw in error_msg for kw in boundary_keywords):
            return EdgeCaseSeverity.BOUNDARY

        # Subtle indicators
        subtle_keywords = ["race", "timing", "intermittent", "occasional"]
        if any(kw in error_msg for kw in subtle_keywords):
            return EdgeCaseSeverity.SUBTLE

        # Default to obvious
        return EdgeCaseSeverity.OBVIOUS

    @staticmethod
    def assess_correctness_gap(
        actual: Any,
        expected: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, float, str]:
        """
        Assess the correctness gap

        Args:
            actual: Actual output
            expected: Expected output
            context: Additional context

        Returns:
            (has_gap, confidence, explanation)
        """
        # Convert to strings for comparison
        actual_str = str(actual)
        expected_str = str(expected)

        if actual_str == expected_str:
            return False, 1.0, "Outputs match exactly"

        # Check for subtle differences
        if actual_str.lower() == expected_str.lower():
            return True, 0.9, "Case mismatch (looks correct, is wrong)"

        if actual_str.strip() == expected_str.strip():
            return True, 0.9, "Whitespace mismatch (looks correct, is wrong)"

        if actual_str.replace(" ", "") == expected_str.replace(" ", ""):
            return True, 0.8, "Spacing difference (looks similar, is wrong)"

        # Substantial difference
        return True, 0.5, "Significant difference"


class EdgeCaseLearner:
    """
    Edge Case Learner - Learn from failures

    Records edge cases, detects patterns, and generates
    graduated examples for few-shot learning.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize EdgeCaseLearner

        Args:
            db_path: Path to SQLite database (default: /mnt/agentic-system/databases/edge_cases.db)
        """
        if db_path is None:
            db_path = Path("/mnt/agentic-system/databases/edge_cases.db")

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.detector = BoundaryDetector()
        self.edge_cases: Dict[str, EdgeCase] = {}
        self.pattern_index: Dict[str, List[str]] = {}  # pattern -> edge_case_ids

        # Initialize database
        self._init_database()
        self._load_edge_cases()

        logger.info(f"EdgeCaseLearner initialized with {len(self.edge_cases)} cases")

    def _init_database(self):
        """Initialize SQLite database schema"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS edge_cases (
                    id TEXT PRIMARY KEY,
                    input_text TEXT NOT NULL,
                    expected_output TEXT NOT NULL,
                    actual_output TEXT NOT NULL,
                    category TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    pattern TEXT,
                    context TEXT,
                    timestamp TEXT NOT NULL,
                    learned INTEGER DEFAULT 0
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS graduated_examples (
                    id TEXT PRIMARY KEY,
                    example_type TEXT NOT NULL,
                    input_text TEXT NOT NULL,
                    correct_output TEXT NOT NULL,
                    explanation TEXT NOT NULL,
                    difficulty_score REAL NOT NULL,
                    category TEXT NOT NULL,
                    related_patterns TEXT
                )
            """)

            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON edge_cases(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_severity ON edge_cases(severity)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pattern ON edge_cases(pattern)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_example_type ON graduated_examples(example_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_difficulty ON graduated_examples(difficulty_score)")

            conn.commit()

    def _load_edge_cases(self):
        """Load edge cases from database"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("SELECT * FROM edge_cases")
            for row in cursor:
                edge_case = EdgeCase(
                    id=row[0],
                    input_text=row[1],
                    expected_output=json.loads(row[2]),
                    actual_output=json.loads(row[3]),
                    category=row[4],
                    severity=EdgeCaseSeverity(row[5]),
                    pattern=row[6],
                    context=json.loads(row[7]) if row[7] else {},
                    timestamp=datetime.fromisoformat(row[8]),
                    learned=bool(row[9])
                )
                self.edge_cases[edge_case.id] = edge_case

                # Build pattern index
                if edge_case.pattern:
                    if edge_case.pattern not in self.pattern_index:
                        self.pattern_index[edge_case.pattern] = []
                    self.pattern_index[edge_case.pattern].append(edge_case.id)

    def record_edge_case(
        self,
        input_text: str,
        expected_output: Any,
        actual_output: Any,
        category: str,
        context: Optional[Dict[str, Any]] = None
    ) -> EdgeCase:
        """
        Record a new edge case

        Args:
            input_text: Input that caused the edge case
            expected_output: Expected output
            actual_output: Actual output
            category: Category (e.g., "validation", "parsing")
            context: Additional context

        Returns:
            Created EdgeCase
        """
        context = context or {}

        # Generate ID
        case_id = hashlib.sha256(
            f"{input_text}{expected_output}{actual_output}{category}".encode()
        ).hexdigest()[:16]

        # Detect boundaries
        boundaries = self.detector.detect_boundaries(input_text, context)
        pattern = boundaries[0] if boundaries else None

        # Classify severity
        severity = self.detector.classify_failure(input_text, context)

        # Create edge case
        edge_case = EdgeCase(
            id=case_id,
            input_text=input_text,
            expected_output=expected_output,
            actual_output=actual_output,
            category=category,
            severity=severity,
            pattern=pattern,
            context=context
        )

        # Store in database
        with sqlite3.connect(str(self.db_path)) as conn:
            data = edge_case.to_dict()
            conn.execute("""
                INSERT OR REPLACE INTO edge_cases
                (id, input_text, expected_output, actual_output, category,
                 severity, pattern, context, timestamp, learned)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["id"], data["input_text"], data["expected_output"],
                data["actual_output"], data["category"], data["severity"],
                data["pattern"], data["context"], data["timestamp"],
                int(data["learned"])
            ))
            conn.commit()

        # Store in memory
        self.edge_cases[case_id] = edge_case

        # Update pattern index
        if pattern:
            if pattern not in self.pattern_index:
                self.pattern_index[pattern] = []
            self.pattern_index[pattern].append(case_id)

        logger.info(f"Recorded edge case: {case_id} ({severity.value}, pattern: {pattern})")

        return edge_case

    def generate_few_shot_examples(
        self,
        category: str,
        difficulty_progression: bool = True,
        max_examples: int = 5
    ) -> List[GraduatedExample]:
        """
        Generate graduated few-shot examples

        Args:
            category: Category to generate examples for
            difficulty_progression: Whether to progress from obvious to subtle
            max_examples: Maximum examples to generate

        Returns:
            List of GraduatedExamples
        """
        # Filter edge cases by category
        category_cases = [
            case for case in self.edge_cases.values()
            if case.category == category
        ]

        if not category_cases:
            logger.warning(f"No edge cases found for category: {category}")
            return []

        # Sort by severity if progression requested
        if difficulty_progression:
            severity_order = {
                EdgeCaseSeverity.OBVIOUS: 0,
                EdgeCaseSeverity.SUBTLE: 1,
                EdgeCaseSeverity.BOUNDARY: 2,
                EdgeCaseSeverity.ADVERSARIAL: 3
            }
            category_cases.sort(key=lambda c: severity_order.get(c.severity, 0))

        # Generate examples
        examples = []
        for i, case in enumerate(category_cases[:max_examples]):
            example_type = self._determine_example_type(case)
            difficulty = self._calculate_difficulty(case)

            example = GraduatedExample(
                id=f"ex_{case.id}",
                example_type=example_type,
                input_text=case.input_text,
                correct_output=case.expected_output,
                explanation=f"{case.severity.value} case: {case.pattern or 'general'}",
                difficulty_score=difficulty,
                category=category,
                related_patterns=[case.pattern] if case.pattern else []
            )

            examples.append(example)

        logger.info(f"Generated {len(examples)} examples for {category}")

        return examples

    def create_graduated_example(
        self,
        example_type: ExampleType,
        input_text: str,
        correct_output: Any,
        explanation: str,
        difficulty_score: float,
        category: str,
        related_patterns: Optional[List[str]] = None
    ) -> GraduatedExample:
        """
        Manually create a graduated example

        Args:
            example_type: Type of example
            input_text: Input text
            correct_output: Correct output
            explanation: Explanation
            difficulty_score: Difficulty (0.0-1.0)
            category: Category
            related_patterns: Related patterns

        Returns:
            Created GraduatedExample
        """
        example_id = hashlib.sha256(
            f"{input_text}{correct_output}{category}".encode()
        ).hexdigest()[:16]

        example = GraduatedExample(
            id=example_id,
            example_type=example_type,
            input_text=input_text,
            correct_output=correct_output,
            explanation=explanation,
            difficulty_score=difficulty_score,
            category=category,
            related_patterns=related_patterns or []
        )

        # Store in database
        with sqlite3.connect(str(self.db_path)) as conn:
            data = example.to_dict()
            conn.execute("""
                INSERT OR REPLACE INTO graduated_examples
                (id, example_type, input_text, correct_output, explanation,
                 difficulty_score, category, related_patterns)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["id"], data["example_type"], data["input_text"],
                data["correct_output"], data["explanation"],
                data["difficulty_score"], data["category"],
                data["related_patterns"]
            ))
            conn.commit()

        return example

    def search_similar_cases(
        self,
        input_text: str,
        category: Optional[str] = None,
        limit: int = 5
    ) -> List[EdgeCase]:
        """
        Search for similar edge cases

        Args:
            input_text: Input to find similar cases for
            category: Optional category filter
            limit: Maximum results

        Returns:
            List of similar EdgeCases
        """
        # Simple similarity based on shared words
        input_words = set(input_text.lower().split())

        cases = list(self.edge_cases.values())

        # Filter by category if specified
        if category:
            cases = [c for c in cases if c.category == category]

        # Score by word overlap
        scored = []
        for case in cases:
            case_words = set(case.input_text.lower().split())
            overlap = len(input_words & case_words)
            if overlap > 0:
                scored.append((overlap, case))

        # Sort by overlap and return top k
        scored.sort(reverse=True, key=lambda x: x[0])

        return [case for _, case in scored[:limit]]

    def get_quality_metrics(self) -> Dict[str, Any]:
        """
        Get edge case learning quality metrics

        Returns:
            Dictionary of metrics
        """
        total = len(self.edge_cases)

        if total == 0:
            return {
                "total_edge_cases": 0,
                "false_negative_rate": 0.0,
                "false_positive_rate": 0.0,
                "boundary_detection_coverage": 0.0,
                "patterns_detected": []
            }

        # Count by severity
        severity_counts = {}
        for case in self.edge_cases.values():
            severity_counts[case.severity.value] = severity_counts.get(case.severity.value, 0) + 1

        # Pattern coverage
        patterns_detected = list(self.pattern_index.keys())

        return {
            "total_edge_cases": total,
            "severity_distribution": severity_counts,
            "false_negative_rate": severity_counts.get("subtle", 0) / total,
            "false_positive_rate": 0.0,  # Would need ground truth
            "boundary_detection_coverage": len(patterns_detected) / len(BoundaryDetector.BOUNDARY_PATTERNS),
            "patterns_detected": patterns_detected
        }

    def _determine_example_type(self, case: EdgeCase) -> ExampleType:
        """Determine example type from edge case"""
        if case.severity == EdgeCaseSeverity.OBVIOUS:
            return ExampleType.NEGATIVE_OBVIOUS
        elif case.severity == EdgeCaseSeverity.SUBTLE:
            return ExampleType.NEGATIVE_SUBTLE
        elif case.severity == EdgeCaseSeverity.BOUNDARY:
            return ExampleType.BOUNDARY_CASE
        else:
            return ExampleType.NEGATIVE_SUBTLE

    def _calculate_difficulty(self, case: EdgeCase) -> float:
        """Calculate difficulty score from edge case"""
        severity_scores = {
            EdgeCaseSeverity.OBVIOUS: 0.2,
            EdgeCaseSeverity.SUBTLE: 0.5,
            EdgeCaseSeverity.BOUNDARY: 0.7,
            EdgeCaseSeverity.ADVERSARIAL: 0.9
        }
        return severity_scores.get(case.severity, 0.5)

    async def learn_from_failure_async(
        self,
        input_text: str,
        expected_output: Any,
        actual_output: Any,
        category: str,
        context: Optional[Dict[str, Any]] = None
    ) -> EdgeCase:
        """
        Async version of record_edge_case

        Useful for integration with async workflows
        """
        return self.record_edge_case(
            input_text, expected_output, actual_output, category, context
        )

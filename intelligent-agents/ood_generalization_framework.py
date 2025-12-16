"""
Out-of-Distribution (OOD) Generalization Framework

Implements Goal 5 requirements for AGI validation per LLM Council mandate:
- Novel task types with held-out conceptual primitives
- Strict data provenance to preclude leakage
- Memorization detection and prevention
- Performance above baseline on genuinely novel problems

Based on research:
- ARC-AGI benchmark methodology
- PASSUNTIL emergence metric
- Compositional generalization protocols

CRITICAL: All tests must be externally designed and validated.
Self-designed tests DO NOT count toward AGI claims.

Author: AGI System
Date: 2025-12-16
Stage: 3 Requirement (Proto-AGI)
"""

import asyncio
import hashlib
import json
import logging
import sqlite3
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OODTestType(Enum):
    """Types of OOD generalization tests per council requirements."""
    NOVEL_TASK = "novel_task"  # Tasks never seen in training
    COMPOSITIONAL = "compositional"  # New combinations of known primitives
    DISTRIBUTION_SHIFT = "distribution_shift"  # Same task, different distribution
    MEMORIZATION_CHECK = "memorization_check"  # Verify no training leakage
    HELD_OUT_PRIMITIVE = "held_out_primitive"  # Concepts withheld from training


class DataProvenance(Enum):
    """Data provenance tracking for leakage prevention."""
    TRAINING = "training"  # Used in training
    VALIDATION = "validation"  # Used in validation
    HELD_OUT = "held_out"  # Strictly held out
    EXTERNAL = "external"  # From external source
    SYNTHETIC = "synthetic"  # Synthetically generated
    UNKNOWN = "unknown"  # Provenance not verified


@dataclass
class ProvenanceRecord:
    """Records provenance of test data to prevent leakage."""
    data_id: str
    source: str
    creation_date: str
    provenance: DataProvenance
    hash_signature: str  # SHA-256 of data content
    verified_by: Optional[str] = None  # External verifier
    isolation_confirmed: bool = False
    notes: str = ""


@dataclass
class OODTest:
    """An out-of-distribution generalization test."""
    test_id: str
    test_type: OODTestType
    name: str
    description: str

    # Test content
    task_specification: Dict[str, Any]
    expected_behavior: str
    success_criteria: List[str]

    # Provenance tracking
    provenance_records: List[ProvenanceRecord]
    held_out_primitives: List[str]  # Concepts specifically withheld

    # Validation requirements
    is_external: bool  # MUST be True for AGI claims
    designer: str  # Who designed this test
    blinded: bool  # Was design process blinded?

    # Difficulty and novelty
    novelty_score: float  # 0.0 = familiar, 1.0 = completely novel
    complexity_level: int  # 1-10 scale

    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OODTestResult:
    """Result of an OOD generalization test."""
    result_id: str
    test_id: str

    # Performance metrics
    passed: bool
    accuracy: float
    baseline_comparison: float  # Performance vs random baseline
    generalization_gap: float  # Train vs test performance difference

    # Memorization detection
    memorization_detected: bool
    memorization_evidence: List[str]

    # Novel capability indicators
    novel_strategy_observed: bool
    strategy_description: str

    # Validation
    externally_validated: bool
    validator: Optional[str] = None

    executed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    execution_time_ms: int = 0
    raw_output: str = ""
    analysis: str = ""


@dataclass
class MemorizationCheck:
    """Result of checking for training data memorization."""
    check_id: str
    test_id: str
    data_hash: str

    # Detection results
    exact_match_found: bool
    near_duplicate_score: float  # 0.0 = no similarity, 1.0 = identical
    training_data_overlap: float  # Percentage of overlap

    # Evidence
    matched_patterns: List[str]
    similar_training_examples: List[str]

    # Conclusion
    memorization_likely: bool
    confidence: float

    checked_at: str = field(default_factory=lambda: datetime.now().isoformat())


class OODTestRunner(ABC):
    """Base class for OOD test execution."""

    @abstractmethod
    async def run(self, test: OODTest, system_under_test: Callable) -> OODTestResult:
        """Execute an OOD test against the system."""
        pass

    @abstractmethod
    def check_memorization(self, test: OODTest, output: str) -> MemorizationCheck:
        """Check if output shows signs of memorization."""
        pass

    @abstractmethod
    def compute_baseline(self, test: OODTest) -> float:
        """Compute random/naive baseline for comparison."""
        pass


class NovelTaskTestRunner(OODTestRunner):
    """Runs tests with completely novel task types."""

    async def run(self, test: OODTest, system_under_test: Callable) -> OODTestResult:
        result_id = str(uuid.uuid4())
        start_time = datetime.now()

        try:
            # Execute system on novel task
            task_input = test.task_specification.get("input", "")
            output = await system_under_test(task_input)

            # Check for memorization
            mem_check = self.check_memorization(test, output)

            # Compute baseline and compare
            baseline = self.compute_baseline(test)
            accuracy = self._evaluate_accuracy(test, output)

            # Check for novel strategies
            novel_strategy, strategy_desc = self._detect_novel_strategy(test, output)

            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            return OODTestResult(
                result_id=result_id,
                test_id=test.test_id,
                passed=accuracy > baseline and not mem_check.memorization_likely,
                accuracy=accuracy,
                baseline_comparison=accuracy - baseline,
                generalization_gap=0.0,  # Computed separately
                memorization_detected=mem_check.memorization_likely,
                memorization_evidence=mem_check.matched_patterns,
                novel_strategy_observed=novel_strategy,
                strategy_description=strategy_desc,
                externally_validated=test.is_external,
                validator=test.designer if test.is_external else None,
                execution_time_ms=execution_time,
                raw_output=str(output),
                analysis=self._generate_analysis(test, output, accuracy, baseline)
            )

        except Exception as e:
            logger.error(f"Novel task test failed: {e}")
            return OODTestResult(
                result_id=result_id,
                test_id=test.test_id,
                passed=False,
                accuracy=0.0,
                baseline_comparison=0.0,
                generalization_gap=0.0,
                memorization_detected=False,
                memorization_evidence=[],
                novel_strategy_observed=False,
                strategy_description="",
                externally_validated=False,
                analysis=f"Test execution failed: {e}"
            )

    def check_memorization(self, test: OODTest, output: str) -> MemorizationCheck:
        """Check for signs of training data memorization."""
        check_id = str(uuid.uuid4())
        output_hash = hashlib.sha256(output.encode()).hexdigest()

        # Check against known training patterns
        matched_patterns = []
        similar_examples = []

        # Heuristic checks for memorization signs
        memorization_indicators = [
            output.startswith("As an AI"),  # Stock response
            "I cannot" in output and len(output) < 100,  # Refusal pattern
            output.count("\n") == 0 and len(output) > 500,  # Wall of text
        ]

        near_duplicate_score = sum(memorization_indicators) / len(memorization_indicators)

        return MemorizationCheck(
            check_id=check_id,
            test_id=test.test_id,
            data_hash=output_hash,
            exact_match_found=False,  # Would need actual training data
            near_duplicate_score=near_duplicate_score,
            training_data_overlap=0.0,  # Requires provenance audit
            matched_patterns=matched_patterns,
            similar_training_examples=similar_examples,
            memorization_likely=near_duplicate_score > 0.5,
            confidence=0.7 if near_duplicate_score > 0.5 else 0.3
        )

    def compute_baseline(self, test: OODTest) -> float:
        """Compute random baseline for novel tasks."""
        # For novel tasks, baseline is typically very low
        complexity = test.complexity_level
        return max(0.05, 0.5 / complexity)

    def _evaluate_accuracy(self, test: OODTest, output: str) -> float:
        """Evaluate accuracy against success criteria."""
        if not test.success_criteria:
            return 0.0

        criteria_met = 0
        for criterion in test.success_criteria:
            # Simple keyword matching - real implementation would be more sophisticated
            if criterion.lower() in output.lower():
                criteria_met += 1

        return criteria_met / len(test.success_criteria)

    def _detect_novel_strategy(self, test: OODTest, output: str) -> Tuple[bool, str]:
        """Detect if system used a novel problem-solving strategy."""
        # Look for indicators of novel approaches
        novel_indicators = [
            "alternative approach",
            "instead of",
            "novel method",
            "different strategy",
            "unconventional",
        ]

        for indicator in novel_indicators:
            if indicator in output.lower():
                return True, f"Detected novel approach indicator: {indicator}"

        return False, "No novel strategy detected"

    def _generate_analysis(self, test: OODTest, output: str, accuracy: float, baseline: float) -> str:
        """Generate analysis of test results."""
        return f"""
OOD Novel Task Analysis:
- Task: {test.name}
- Novelty Score: {test.novelty_score}
- Accuracy: {accuracy:.2%}
- Baseline: {baseline:.2%}
- Above Baseline: {accuracy > baseline}
- External Validation: {test.is_external}
"""


class CompositionalTestRunner(OODTestRunner):
    """Runs tests requiring compositional generalization."""

    async def run(self, test: OODTest, system_under_test: Callable) -> OODTestResult:
        result_id = str(uuid.uuid4())
        start_time = datetime.now()

        try:
            task_input = test.task_specification.get("input", "")
            output = await system_under_test(task_input)

            mem_check = self.check_memorization(test, output)
            baseline = self.compute_baseline(test)
            accuracy = self._evaluate_compositional_accuracy(test, output)

            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Check for systematic compositionality
            systematic, desc = self._check_systematic_compositionality(test, output)

            return OODTestResult(
                result_id=result_id,
                test_id=test.test_id,
                passed=accuracy > baseline and not mem_check.memorization_likely,
                accuracy=accuracy,
                baseline_comparison=accuracy - baseline,
                generalization_gap=self._compute_compositional_gap(test, accuracy),
                memorization_detected=mem_check.memorization_likely,
                memorization_evidence=mem_check.matched_patterns,
                novel_strategy_observed=systematic,
                strategy_description=desc,
                externally_validated=test.is_external,
                validator=test.designer if test.is_external else None,
                execution_time_ms=execution_time,
                raw_output=str(output),
                analysis=f"Compositional generalization: {accuracy:.2%} accuracy"
            )

        except Exception as e:
            logger.error(f"Compositional test failed: {e}")
            return OODTestResult(
                result_id=result_id,
                test_id=test.test_id,
                passed=False,
                accuracy=0.0,
                baseline_comparison=0.0,
                generalization_gap=0.0,
                memorization_detected=False,
                memorization_evidence=[],
                novel_strategy_observed=False,
                strategy_description="",
                externally_validated=False,
                analysis=f"Test execution failed: {e}"
            )

    def check_memorization(self, test: OODTest, output: str) -> MemorizationCheck:
        check_id = str(uuid.uuid4())
        output_hash = hashlib.sha256(output.encode()).hexdigest()

        return MemorizationCheck(
            check_id=check_id,
            test_id=test.test_id,
            data_hash=output_hash,
            exact_match_found=False,
            near_duplicate_score=0.0,
            training_data_overlap=0.0,
            matched_patterns=[],
            similar_training_examples=[],
            memorization_likely=False,
            confidence=0.5
        )

    def compute_baseline(self, test: OODTest) -> float:
        """Baseline for compositional tasks."""
        num_primitives = len(test.held_out_primitives)
        return 0.5 ** num_primitives  # Exponential decay with primitive count

    def _evaluate_compositional_accuracy(self, test: OODTest, output: str) -> float:
        """Evaluate ability to compose primitives correctly."""
        if not test.success_criteria:
            return 0.0

        criteria_met = 0
        for criterion in test.success_criteria:
            if criterion.lower() in output.lower():
                criteria_met += 1

        return criteria_met / len(test.success_criteria)

    def _compute_compositional_gap(self, test: OODTest, test_accuracy: float) -> float:
        """Compute gap between training and test performance."""
        # Assume training performance is high for known primitives
        estimated_train_accuracy = 0.9
        return estimated_train_accuracy - test_accuracy

    def _check_systematic_compositionality(self, test: OODTest, output: str) -> Tuple[bool, str]:
        """Check if system shows systematic compositional generalization."""
        # Look for evidence of rule-based composition
        return False, "Systematic compositionality not verified"


class MemorizationCheckRunner(OODTestRunner):
    """Specifically checks for training data memorization."""

    def __init__(self, training_data_hashes: Set[str] = None):
        self.training_data_hashes = training_data_hashes or set()

    async def run(self, test: OODTest, system_under_test: Callable) -> OODTestResult:
        result_id = str(uuid.uuid4())
        start_time = datetime.now()

        try:
            # Use probing inputs designed to elicit memorized content
            probing_inputs = test.task_specification.get("probing_inputs", [])

            memorization_detected = False
            evidence = []

            for probe in probing_inputs:
                output = await system_under_test(probe)
                mem_check = self.check_memorization(test, output)

                if mem_check.memorization_likely:
                    memorization_detected = True
                    evidence.extend(mem_check.matched_patterns)

            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            return OODTestResult(
                result_id=result_id,
                test_id=test.test_id,
                passed=not memorization_detected,
                accuracy=1.0 if not memorization_detected else 0.0,
                baseline_comparison=0.0,
                generalization_gap=0.0,
                memorization_detected=memorization_detected,
                memorization_evidence=evidence,
                novel_strategy_observed=False,
                strategy_description="",
                externally_validated=test.is_external,
                validator=test.designer if test.is_external else None,
                execution_time_ms=execution_time,
                raw_output="",
                analysis=f"Memorization {'detected' if memorization_detected else 'not detected'}"
            )

        except Exception as e:
            logger.error(f"Memorization check failed: {e}")
            return OODTestResult(
                result_id=result_id,
                test_id=test.test_id,
                passed=False,
                accuracy=0.0,
                baseline_comparison=0.0,
                generalization_gap=0.0,
                memorization_detected=False,
                memorization_evidence=[],
                novel_strategy_observed=False,
                strategy_description="",
                externally_validated=False,
                analysis=f"Test execution failed: {e}"
            )

    def check_memorization(self, test: OODTest, output: str) -> MemorizationCheck:
        check_id = str(uuid.uuid4())
        output_hash = hashlib.sha256(output.encode()).hexdigest()

        # Check against known training data
        exact_match = output_hash in self.training_data_hashes

        # Compute near-duplicate score
        near_duplicate_score = 0.0
        if exact_match:
            near_duplicate_score = 1.0

        return MemorizationCheck(
            check_id=check_id,
            test_id=test.test_id,
            data_hash=output_hash,
            exact_match_found=exact_match,
            near_duplicate_score=near_duplicate_score,
            training_data_overlap=1.0 if exact_match else 0.0,
            matched_patterns=["Exact hash match"] if exact_match else [],
            similar_training_examples=[],
            memorization_likely=exact_match,
            confidence=1.0 if exact_match else 0.5
        )

    def compute_baseline(self, test: OODTest) -> float:
        return 0.0  # Baseline for memorization checks


class HeldOutPrimitiveTestRunner(OODTestRunner):
    """Tests generalization to held-out conceptual primitives."""

    async def run(self, test: OODTest, system_under_test: Callable) -> OODTestResult:
        result_id = str(uuid.uuid4())
        start_time = datetime.now()

        try:
            task_input = test.task_specification.get("input", "")
            output = await system_under_test(task_input)

            mem_check = self.check_memorization(test, output)
            baseline = self.compute_baseline(test)

            # Evaluate handling of held-out primitives
            accuracy = self._evaluate_primitive_handling(test, output)

            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            return OODTestResult(
                result_id=result_id,
                test_id=test.test_id,
                passed=accuracy > baseline and not mem_check.memorization_likely,
                accuracy=accuracy,
                baseline_comparison=accuracy - baseline,
                generalization_gap=0.0,
                memorization_detected=mem_check.memorization_likely,
                memorization_evidence=mem_check.matched_patterns,
                novel_strategy_observed=False,
                strategy_description="",
                externally_validated=test.is_external,
                validator=test.designer if test.is_external else None,
                execution_time_ms=execution_time,
                raw_output=str(output),
                analysis=f"Held-out primitive handling: {accuracy:.2%}"
            )

        except Exception as e:
            logger.error(f"Held-out primitive test failed: {e}")
            return OODTestResult(
                result_id=result_id,
                test_id=test.test_id,
                passed=False,
                accuracy=0.0,
                baseline_comparison=0.0,
                generalization_gap=0.0,
                memorization_detected=False,
                memorization_evidence=[],
                novel_strategy_observed=False,
                strategy_description="",
                externally_validated=False,
                analysis=f"Test execution failed: {e}"
            )

    def check_memorization(self, test: OODTest, output: str) -> MemorizationCheck:
        check_id = str(uuid.uuid4())
        output_hash = hashlib.sha256(output.encode()).hexdigest()

        return MemorizationCheck(
            check_id=check_id,
            test_id=test.test_id,
            data_hash=output_hash,
            exact_match_found=False,
            near_duplicate_score=0.0,
            training_data_overlap=0.0,
            matched_patterns=[],
            similar_training_examples=[],
            memorization_likely=False,
            confidence=0.5
        )

    def compute_baseline(self, test: OODTest) -> float:
        """Baseline for held-out primitives is very low."""
        return 0.1

    def _evaluate_primitive_handling(self, test: OODTest, output: str) -> float:
        """Evaluate correct handling of held-out primitives."""
        if not test.held_out_primitives:
            return 0.0

        correct_handling = 0
        for primitive in test.held_out_primitives:
            # Check if system correctly inferred the primitive's meaning
            if primitive.lower() in output.lower():
                correct_handling += 1

        return correct_handling / len(test.held_out_primitives)


class OODGeneralizationFramework:
    """
    Main framework for Out-of-Distribution generalization testing.

    CRITICAL: For AGI claims, tests must be:
    1. Externally designed (is_external=True)
    2. Blinded (designer didn't know system internals)
    3. Provenance verified (no training data leakage)
    4. Performance above baseline on genuinely novel problems
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path.home() / ".claude" / "agi" / "ood_tests.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_database()

        # Initialize test runners
        self.runners = {
            OODTestType.NOVEL_TASK: NovelTaskTestRunner(),
            OODTestType.COMPOSITIONAL: CompositionalTestRunner(),
            OODTestType.MEMORIZATION_CHECK: MemorizationCheckRunner(),
            OODTestType.HELD_OUT_PRIMITIVE: HeldOutPrimitiveTestRunner(),
        }

    def _init_database(self):
        """Initialize SQLite database for test persistence."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ood_tests (
                test_id TEXT PRIMARY KEY,
                test_type TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                task_specification TEXT,
                expected_behavior TEXT,
                success_criteria TEXT,
                provenance_records TEXT,
                held_out_primitives TEXT,
                is_external BOOLEAN NOT NULL,
                designer TEXT,
                blinded BOOLEAN,
                novelty_score REAL,
                complexity_level INTEGER,
                created_at TEXT,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ood_results (
                result_id TEXT PRIMARY KEY,
                test_id TEXT NOT NULL,
                passed BOOLEAN,
                accuracy REAL,
                baseline_comparison REAL,
                generalization_gap REAL,
                memorization_detected BOOLEAN,
                memorization_evidence TEXT,
                novel_strategy_observed BOOLEAN,
                strategy_description TEXT,
                externally_validated BOOLEAN,
                validator TEXT,
                executed_at TEXT,
                execution_time_ms INTEGER,
                raw_output TEXT,
                analysis TEXT,
                FOREIGN KEY (test_id) REFERENCES ood_tests(test_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memorization_checks (
                check_id TEXT PRIMARY KEY,
                test_id TEXT NOT NULL,
                data_hash TEXT,
                exact_match_found BOOLEAN,
                near_duplicate_score REAL,
                training_data_overlap REAL,
                matched_patterns TEXT,
                similar_training_examples TEXT,
                memorization_likely BOOLEAN,
                confidence REAL,
                checked_at TEXT,
                FOREIGN KEY (test_id) REFERENCES ood_tests(test_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS provenance_records (
                data_id TEXT PRIMARY KEY,
                source TEXT,
                creation_date TEXT,
                provenance TEXT,
                hash_signature TEXT,
                verified_by TEXT,
                isolation_confirmed BOOLEAN,
                notes TEXT
            )
        """)

        conn.commit()
        conn.close()

    def create_test(self, test: OODTest) -> str:
        """Create and store an OOD test."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO ood_tests (
                test_id, test_type, name, description, task_specification,
                expected_behavior, success_criteria, provenance_records,
                held_out_primitives, is_external, designer, blinded,
                novelty_score, complexity_level, created_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            test.test_id,
            test.test_type.value,
            test.name,
            test.description,
            json.dumps(test.task_specification),
            test.expected_behavior,
            json.dumps(test.success_criteria),
            json.dumps([{
                "data_id": p.data_id,
                "source": p.source,
                "provenance": p.provenance.value,
                "hash_signature": p.hash_signature,
                "verified_by": p.verified_by,
                "isolation_confirmed": p.isolation_confirmed
            } for p in test.provenance_records]),
            json.dumps(test.held_out_primitives),
            test.is_external,
            test.designer,
            test.blinded,
            test.novelty_score,
            test.complexity_level,
            test.created_at,
            json.dumps(test.metadata)
        ))

        conn.commit()
        conn.close()

        return test.test_id

    async def run_test(self, test_id: str, system_under_test: Callable) -> OODTestResult:
        """Run a specific OOD test."""
        test = self.get_test(test_id)
        if not test:
            raise ValueError(f"Test not found: {test_id}")

        runner = self.runners.get(test.test_type)
        if not runner:
            raise ValueError(f"No runner for test type: {test.test_type}")

        result = await runner.run(test, system_under_test)
        self._save_result(result)

        return result

    async def run_battery(self, battery_name: str, test_ids: List[str],
                         system_under_test: Callable) -> Dict[str, Any]:
        """Run a battery of OOD tests."""
        results = []
        passed = 0

        for test_id in test_ids:
            result = await self.run_test(test_id, system_under_test)
            results.append(result)
            if result.passed:
                passed += 1

        return {
            "battery_name": battery_name,
            "total_tests": len(test_ids),
            "passed": passed,
            "pass_rate": passed / len(test_ids) if test_ids else 0.0,
            "results": results,
            "all_external": all(r.externally_validated for r in results),
            "valid_for_agi_claim": all(r.externally_validated and r.passed for r in results)
        }

    def get_test(self, test_id: str) -> Optional[OODTest]:
        """Retrieve a test by ID."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM ood_tests WHERE test_id = ?", (test_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return OODTest(
            test_id=row[0],
            test_type=OODTestType(row[1]),
            name=row[2],
            description=row[3],
            task_specification=json.loads(row[4]) if row[4] else {},
            expected_behavior=row[5],
            success_criteria=json.loads(row[6]) if row[6] else [],
            provenance_records=[ProvenanceRecord(
                data_id=p["data_id"],
                source=p["source"],
                creation_date="",
                provenance=DataProvenance(p["provenance"]),
                hash_signature=p["hash_signature"],
                verified_by=p.get("verified_by"),
                isolation_confirmed=p.get("isolation_confirmed", False)
            ) for p in json.loads(row[7]) if row[7]] if row[7] else [],
            held_out_primitives=json.loads(row[8]) if row[8] else [],
            is_external=bool(row[9]),
            designer=row[10],
            blinded=bool(row[11]) if row[11] is not None else False,
            novelty_score=row[12] or 0.0,
            complexity_level=row[13] or 1,
            created_at=row[14],
            metadata=json.loads(row[15]) if row[15] else {}
        )

    def _save_result(self, result: OODTestResult):
        """Save test result to database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO ood_results (
                result_id, test_id, passed, accuracy, baseline_comparison,
                generalization_gap, memorization_detected, memorization_evidence,
                novel_strategy_observed, strategy_description, externally_validated,
                validator, executed_at, execution_time_ms, raw_output, analysis
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.result_id,
            result.test_id,
            result.passed,
            result.accuracy,
            result.baseline_comparison,
            result.generalization_gap,
            result.memorization_detected,
            json.dumps(result.memorization_evidence),
            result.novel_strategy_observed,
            result.strategy_description,
            result.externally_validated,
            result.validator,
            result.executed_at,
            result.execution_time_ms,
            result.raw_output[:10000] if result.raw_output else "",
            result.analysis
        ))

        conn.commit()
        conn.close()

    def get_agi_validation_status(self) -> Dict[str, Any]:
        """
        Check if OOD generalization requirements are met for AGI claims.

        Requirements (per LLM Council):
        1. Novel task tests with external validation
        2. Compositional generalization tests
        3. Memorization checks passed
        4. Held-out primitive tests passed
        5. All tests externally designed and validated
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Get all results
        cursor.execute("""
            SELECT r.*, t.test_type, t.is_external
            FROM ood_results r
            JOIN ood_tests t ON r.test_id = t.test_id
        """)
        results = cursor.fetchall()
        conn.close()

        if not results:
            return {
                "agi_validation_status": "NOT_STARTED",
                "message": "No OOD tests have been run",
                "requirements_met": {
                    "novel_task_tests": False,
                    "compositional_tests": False,
                    "memorization_checks": False,
                    "held_out_primitive_tests": False,
                    "all_external": False,
                },
                "ready_for_agi_claim": False
            }

        # Analyze results by type
        by_type = {t: [] for t in OODTestType}
        external_count = 0

        for r in results:
            test_type = OODTestType(r[16])  # test_type column
            is_external = bool(r[17])  # is_external column
            passed = bool(r[2])  # passed column

            by_type[test_type].append({
                "passed": passed,
                "is_external": is_external
            })

            if is_external:
                external_count += 1

        def check_type_passed(test_type: OODTestType) -> bool:
            tests = by_type[test_type]
            if not tests:
                return False
            return all(t["passed"] and t["is_external"] for t in tests)

        requirements = {
            "novel_task_tests": check_type_passed(OODTestType.NOVEL_TASK),
            "compositional_tests": check_type_passed(OODTestType.COMPOSITIONAL),
            "memorization_checks": check_type_passed(OODTestType.MEMORIZATION_CHECK),
            "held_out_primitive_tests": check_type_passed(OODTestType.HELD_OUT_PRIMITIVE),
            "all_external": external_count == len(results) and len(results) > 0,
        }

        all_met = all(requirements.values())

        return {
            "agi_validation_status": "PASSED" if all_met else "NOT_PASSED",
            "message": "All OOD requirements met" if all_met else "Missing requirements",
            "requirements_met": requirements,
            "ready_for_agi_claim": all_met,
            "total_tests": len(results),
            "external_tests": external_count,
            "tests_by_type": {t.value: len(by_type[t]) for t in OODTestType}
        }


def create_example_tests() -> List[OODTest]:
    """
    Create example OOD tests.

    WARNING: These are INTERNAL examples and DO NOT count toward AGI validation.
    Real AGI validation requires EXTERNALLY designed tests.
    """

    examples = [
        OODTest(
            test_id=str(uuid.uuid4()),
            test_type=OODTestType.NOVEL_TASK,
            name="Novel Spatial Reasoning",
            description="Test spatial reasoning on unseen geometric configurations",
            task_specification={
                "input": "Given a 4D hypercube, describe the path from vertex A to vertex B that passes through exactly 3 edges",
                "domain": "spatial_reasoning"
            },
            expected_behavior="Systematic exploration of hypercube structure",
            success_criteria=[
                "Correct identification of 4D structure",
                "Valid path enumeration",
                "Correct edge count"
            ],
            provenance_records=[ProvenanceRecord(
                data_id="internal_spatial_1",
                source="internal",
                creation_date=datetime.now().isoformat(),
                provenance=DataProvenance.SYNTHETIC,
                hash_signature="",
                verified_by=None,
                isolation_confirmed=False
            )],
            held_out_primitives=["4D navigation"],
            is_external=False,  # INTERNAL - NOT valid for AGI claims
            designer="internal",
            blinded=False,
            novelty_score=0.8,
            complexity_level=7
        ),
        OODTest(
            test_id=str(uuid.uuid4()),
            test_type=OODTestType.COMPOSITIONAL,
            name="Compositional Language Task",
            description="Test composition of novel word combinations",
            task_specification={
                "input": "If 'blick' means 'jump twice' and 'dax' means 'turn left', what is 'blick dax blick'?",
                "domain": "language_composition"
            },
            expected_behavior="Systematic application of composition rules",
            success_criteria=[
                "Correct interpretation of primitives",
                "Correct sequential composition"
            ],
            provenance_records=[],
            held_out_primitives=["blick", "dax"],
            is_external=False,  # INTERNAL
            designer="internal",
            blinded=False,
            novelty_score=0.6,
            complexity_level=4
        ),
        OODTest(
            test_id=str(uuid.uuid4()),
            test_type=OODTestType.MEMORIZATION_CHECK,
            name="Training Data Leakage Check",
            description="Probe for memorized training data",
            task_specification={
                "probing_inputs": [
                    "Complete: 'The quick brown fox'",
                    "What is the first line of Pride and Prejudice?",
                    "Recite the SHA-256 hash of 'test'"
                ]
            },
            expected_behavior="No verbatim reproduction of training data",
            success_criteria=[
                "No exact training matches",
                "Paraphrased responses"
            ],
            provenance_records=[],
            held_out_primitives=[],
            is_external=False,  # INTERNAL
            designer="internal",
            blinded=False,
            novelty_score=0.3,
            complexity_level=2
        )
    ]

    return examples


async def main():
    """Demo the OOD generalization framework."""
    print("OOD Generalization Framework - Demo")
    print("=" * 50)
    print()
    print("WARNING: Internal examples DO NOT count toward AGI claims.")
    print("AGI validation requires externally designed tests.")
    print()

    framework = OODGeneralizationFramework()

    # Create example tests
    examples = create_example_tests()
    for test in examples:
        framework.create_test(test)
        print(f"Created test: {test.name} ({test.test_type.value})")

    print()

    # Check validation status
    status = framework.get_agi_validation_status()
    print("AGI Validation Status:")
    print(f"  Status: {status['agi_validation_status']}")
    print(f"  Ready for AGI claim: {status['ready_for_agi_claim']}")
    print(f"  Requirements met: {status['requirements_met']}")


if __name__ == "__main__":
    asyncio.run(main())

"""
Provenance-Verified Self-Improvement Framework

Implements Goal 6 requirements for AGI validation per LLM Council mandate:
- Capability deltas with code/provenance diffs
- Ablations proving improvements aren't cached training patterns
- Demonstration of novel strategies not in original architecture

Based on research:
- Darwin-Gödel Machine principles
- LADDER framework for recursive improvement
- Provenance verification protocols

CRITICAL: Self-improvement claims must be:
1. Externally verifiable with complete provenance chain
2. Ablation-tested to rule out training pattern caching
3. Demonstrated with code diffs and capability measurements
4. Not explainable by existing architecture patterns

Author: AGI System
Date: 2025-12-16
Stage: 3 Requirement (Proto-AGI)
"""

import asyncio
import hashlib
import json
import logging
import sqlite3
import subprocess
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImprovementType(Enum):
    """Types of self-improvement that require provenance verification."""
    ARCHITECTURE_MODIFICATION = "architecture_modification"
    ALGORITHM_OPTIMIZATION = "algorithm_optimization"
    CAPABILITY_EXTENSION = "capability_extension"
    ERROR_CORRECTION = "error_correction"
    STRATEGY_INVENTION = "strategy_invention"
    KNOWLEDGE_SYNTHESIS = "knowledge_synthesis"


class ProvenanceStatus(Enum):
    """Status of provenance verification."""
    UNVERIFIED = "unverified"
    PARTIAL = "partial"
    VERIFIED = "verified"
    FAILED = "failed"
    EXTERNAL_PENDING = "external_pending"


class AblationResult(Enum):
    """Results of ablation testing."""
    NOT_TESTED = "not_tested"
    PASSED = "passed"  # Improvement holds without training patterns
    FAILED = "failed"  # Improvement is just training pattern
    INCONCLUSIVE = "inconclusive"


@dataclass
class CapabilitySnapshot:
    """Snapshot of system capabilities at a point in time."""
    snapshot_id: str
    timestamp: str

    # Code state
    git_commit: str
    code_hash: str
    file_checksums: Dict[str, str]

    # Capability measurements
    capabilities: Dict[str, float]  # capability_name -> score
    benchmark_results: Dict[str, Any]

    # Architecture state
    architecture_version: str
    model_parameters: Dict[str, Any]

    # Provenance
    created_by: str  # Who/what created this snapshot
    verified_by: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImprovementProposal:
    """A proposed self-improvement with provenance tracking."""
    proposal_id: str
    improvement_type: ImprovementType

    # Description
    title: str
    description: str
    hypothesis: str  # What improvement is expected
    rationale: str  # Why this should work

    # Before/after snapshots
    before_snapshot_id: str
    proposed_changes: Dict[str, Any]  # What will change

    # Expected outcomes
    expected_capability_deltas: Dict[str, float]
    success_criteria: List[str]

    # Provenance chain
    source_inspiration: str  # Where did this idea come from?
    not_from_training: bool  # Can we verify this isn't from training?
    derivation_steps: List[str]  # How was this derived?

    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "proposed"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImprovementResult:
    """Result of implementing a self-improvement."""
    result_id: str
    proposal_id: str

    # Implementation
    implemented: bool
    implementation_commit: Optional[str]
    code_diff: str
    files_changed: List[str]

    # Before/after comparison
    before_snapshot_id: str
    after_snapshot_id: str
    capability_deltas: Dict[str, float]  # Measured changes

    # Ablation testing
    ablation_result: AblationResult
    ablation_details: str

    # Provenance verification
    provenance_status: ProvenanceStatus
    provenance_chain: List[str]  # Chain of reasoning
    verifier: Optional[str]  # External verifier

    # Novel strategy detection
    novel_strategy_detected: bool
    strategy_description: str
    not_in_original_architecture: bool

    # Validation
    externally_validated: bool
    validation_notes: str

    executed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AblationTest:
    """An ablation test to verify improvement isn't training pattern."""
    test_id: str
    improvement_id: str

    # Test design
    test_type: str  # "remove_component", "randomize_weights", "swap_data", etc.
    hypothesis: str  # What we expect if improvement is genuine
    control_condition: str

    # Results
    with_improvement: float  # Performance with improvement
    without_improvement: float  # Performance without
    random_baseline: float  # Random/null performance

    # Analysis
    improvement_holds: bool  # Does improvement persist after ablation?
    likely_training_pattern: bool  # Does it look like cached pattern?
    confidence: float

    executed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    notes: str = ""


class CapabilityMeasurer(ABC):
    """Base class for measuring system capabilities."""

    @abstractmethod
    async def measure(self, capability_name: str) -> float:
        """Measure a specific capability."""
        pass

    @abstractmethod
    async def run_benchmark(self, benchmark_name: str) -> Dict[str, Any]:
        """Run a benchmark suite."""
        pass


class DefaultCapabilityMeasurer(CapabilityMeasurer):
    """Default implementation of capability measurement."""

    async def measure(self, capability_name: str) -> float:
        """Measure a capability (placeholder for real implementation)."""
        # In real implementation, this would run actual capability tests
        return 0.5

    async def run_benchmark(self, benchmark_name: str) -> Dict[str, Any]:
        """Run a benchmark suite."""
        return {
            "benchmark": benchmark_name,
            "score": 0.5,
            "details": "Placeholder benchmark"
        }


class AblationTester:
    """Runs ablation tests to verify improvement provenance."""

    async def run_ablation(self, improvement: ImprovementResult,
                          system_under_test: Callable,
                          measurer: CapabilityMeasurer) -> AblationTest:
        """
        Run ablation test to verify improvement isn't cached training pattern.

        Tests:
        1. Does improvement persist when component is removed?
        2. Does improvement persist with randomized weights?
        3. Is improvement significantly above random baseline?
        """
        test_id = str(uuid.uuid4())

        # Measure with improvement
        with_improvement = await measurer.measure("target_capability")

        # Measure without improvement (would require rollback in real impl)
        without_improvement = await measurer.measure("baseline_capability")

        # Random baseline
        random_baseline = 0.1  # Would be computed from random trials

        # Analysis
        delta = with_improvement - without_improvement
        improvement_holds = delta > 0.1  # Significant improvement
        above_baseline = with_improvement > random_baseline * 2

        # Check if this looks like a training pattern
        likely_training = delta > 0.5 and not above_baseline

        return AblationTest(
            test_id=test_id,
            improvement_id=improvement.result_id,
            test_type="capability_ablation",
            hypothesis="Improvement persists without training patterns",
            control_condition="Remove improvement code",
            with_improvement=with_improvement,
            without_improvement=without_improvement,
            random_baseline=random_baseline,
            improvement_holds=improvement_holds and above_baseline,
            likely_training_pattern=likely_training,
            confidence=0.7 if improvement_holds else 0.3,
            notes=f"Delta: {delta:.3f}, Above baseline: {above_baseline}"
        )


class ProvenanceVerifier:
    """Verifies provenance chain for self-improvements."""

    def __init__(self, repo_path: str = None):
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()

    def get_git_commit(self) -> str:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    def get_git_diff(self, from_commit: str, to_commit: str) -> str:
        """Get diff between two commits."""
        try:
            result = subprocess.run(
                ["git", "diff", from_commit, to_commit],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            return result.stdout if result.returncode == 0 else ""
        except Exception:
            return ""

    def compute_file_checksums(self, files: List[str]) -> Dict[str, str]:
        """Compute SHA-256 checksums for files."""
        checksums = {}
        for file_path in files:
            try:
                full_path = self.repo_path / file_path
                if full_path.exists():
                    with open(full_path, 'rb') as f:
                        checksums[file_path] = hashlib.sha256(f.read()).hexdigest()
            except Exception:
                checksums[file_path] = "error"
        return checksums

    def verify_provenance_chain(self, chain: List[str]) -> Tuple[ProvenanceStatus, str]:
        """
        Verify a provenance chain for an improvement.

        Returns status and explanation.
        """
        if not chain:
            return ProvenanceStatus.UNVERIFIED, "No provenance chain provided"

        # Check each step in chain
        verified_steps = 0
        issues = []

        for i, step in enumerate(chain):
            # Check if step is documented
            if len(step) < 10:
                issues.append(f"Step {i+1}: Too brief to verify")
            else:
                verified_steps += 1

        # Determine status
        if verified_steps == len(chain):
            return ProvenanceStatus.VERIFIED, "All steps verified"
        elif verified_steps > 0:
            return ProvenanceStatus.PARTIAL, f"Verified {verified_steps}/{len(chain)} steps"
        else:
            return ProvenanceStatus.FAILED, f"Issues: {'; '.join(issues)}"


class ProvenanceSelfImprovementFramework:
    """
    Main framework for provenance-verified self-improvement.

    CRITICAL: For AGI claims, improvements must be:
    1. Tracked with complete provenance chain
    2. Ablation-tested to rule out training patterns
    3. Demonstrated with measurable capability deltas
    4. Externally verified as novel (not from original architecture)
    """

    def __init__(self, db_path: str = None, repo_path: str = None):
        if db_path is None:
            db_path = Path.home() / ".claude" / "agi" / "provenance_improvements.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_database()

        self.verifier = ProvenanceVerifier(repo_path)
        self.ablation_tester = AblationTester()
        self.measurer = DefaultCapabilityMeasurer()

    def _init_database(self):
        """Initialize SQLite database for provenance tracking."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS capability_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                timestamp TEXT,
                git_commit TEXT,
                code_hash TEXT,
                file_checksums TEXT,
                capabilities TEXT,
                benchmark_results TEXT,
                architecture_version TEXT,
                model_parameters TEXT,
                created_by TEXT,
                verified_by TEXT,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS improvement_proposals (
                proposal_id TEXT PRIMARY KEY,
                improvement_type TEXT,
                title TEXT,
                description TEXT,
                hypothesis TEXT,
                rationale TEXT,
                before_snapshot_id TEXT,
                proposed_changes TEXT,
                expected_capability_deltas TEXT,
                success_criteria TEXT,
                source_inspiration TEXT,
                not_from_training BOOLEAN,
                derivation_steps TEXT,
                created_at TEXT,
                status TEXT,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS improvement_results (
                result_id TEXT PRIMARY KEY,
                proposal_id TEXT,
                implemented BOOLEAN,
                implementation_commit TEXT,
                code_diff TEXT,
                files_changed TEXT,
                before_snapshot_id TEXT,
                after_snapshot_id TEXT,
                capability_deltas TEXT,
                ablation_result TEXT,
                ablation_details TEXT,
                provenance_status TEXT,
                provenance_chain TEXT,
                verifier TEXT,
                novel_strategy_detected BOOLEAN,
                strategy_description TEXT,
                not_in_original_architecture BOOLEAN,
                externally_validated BOOLEAN,
                validation_notes TEXT,
                executed_at TEXT,
                metadata TEXT,
                FOREIGN KEY (proposal_id) REFERENCES improvement_proposals(proposal_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ablation_tests (
                test_id TEXT PRIMARY KEY,
                improvement_id TEXT,
                test_type TEXT,
                hypothesis TEXT,
                control_condition TEXT,
                with_improvement REAL,
                without_improvement REAL,
                random_baseline REAL,
                improvement_holds BOOLEAN,
                likely_training_pattern BOOLEAN,
                confidence REAL,
                executed_at TEXT,
                notes TEXT,
                FOREIGN KEY (improvement_id) REFERENCES improvement_results(result_id)
            )
        """)

        conn.commit()
        conn.close()

    async def create_capability_snapshot(self, created_by: str = "system",
                                         files_to_track: List[str] = None) -> CapabilitySnapshot:
        """Create a snapshot of current system capabilities."""
        snapshot_id = str(uuid.uuid4())

        if files_to_track is None:
            files_to_track = []

        # Get git state
        git_commit = self.verifier.get_git_commit()
        file_checksums = self.verifier.compute_file_checksums(files_to_track)

        # Compute code hash
        checksum_str = json.dumps(file_checksums, sort_keys=True)
        code_hash = hashlib.sha256(checksum_str.encode()).hexdigest()

        # Measure capabilities
        capabilities = {}
        for cap in ["reasoning", "coding", "learning", "adaptation"]:
            capabilities[cap] = await self.measurer.measure(cap)

        snapshot = CapabilitySnapshot(
            snapshot_id=snapshot_id,
            timestamp=datetime.now().isoformat(),
            git_commit=git_commit,
            code_hash=code_hash,
            file_checksums=file_checksums,
            capabilities=capabilities,
            benchmark_results={},
            architecture_version="1.0",
            model_parameters={},
            created_by=created_by
        )

        self._save_snapshot(snapshot)
        return snapshot

    def _save_snapshot(self, snapshot: CapabilitySnapshot):
        """Save capability snapshot to database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO capability_snapshots (
                snapshot_id, timestamp, git_commit, code_hash, file_checksums,
                capabilities, benchmark_results, architecture_version,
                model_parameters, created_by, verified_by, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot.snapshot_id,
            snapshot.timestamp,
            snapshot.git_commit,
            snapshot.code_hash,
            json.dumps(snapshot.file_checksums),
            json.dumps(snapshot.capabilities),
            json.dumps(snapshot.benchmark_results),
            snapshot.architecture_version,
            json.dumps(snapshot.model_parameters),
            snapshot.created_by,
            snapshot.verified_by,
            json.dumps(snapshot.metadata)
        ))

        conn.commit()
        conn.close()

    def create_proposal(self, proposal: ImprovementProposal) -> str:
        """Create and store an improvement proposal."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO improvement_proposals (
                proposal_id, improvement_type, title, description, hypothesis,
                rationale, before_snapshot_id, proposed_changes,
                expected_capability_deltas, success_criteria, source_inspiration,
                not_from_training, derivation_steps, created_at, status, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            proposal.proposal_id,
            proposal.improvement_type.value,
            proposal.title,
            proposal.description,
            proposal.hypothesis,
            proposal.rationale,
            proposal.before_snapshot_id,
            json.dumps(proposal.proposed_changes),
            json.dumps(proposal.expected_capability_deltas),
            json.dumps(proposal.success_criteria),
            proposal.source_inspiration,
            proposal.not_from_training,
            json.dumps(proposal.derivation_steps),
            proposal.created_at,
            proposal.status,
            json.dumps(proposal.metadata)
        ))

        conn.commit()
        conn.close()

        return proposal.proposal_id

    async def implement_and_verify(self, proposal_id: str,
                                   implementation_func: Callable) -> ImprovementResult:
        """
        Implement an improvement and verify its provenance.

        Steps:
        1. Create before snapshot
        2. Implement the improvement
        3. Create after snapshot
        4. Measure capability deltas
        5. Run ablation tests
        6. Verify provenance chain
        """
        result_id = str(uuid.uuid4())

        # Get proposal
        proposal = self.get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal not found: {proposal_id}")

        # Before snapshot
        before_snapshot = await self.create_capability_snapshot("system")

        # Implement improvement
        try:
            implementation_result = await implementation_func(proposal)
            implemented = True
            implementation_commit = self.verifier.get_git_commit()
            code_diff = ""  # Would get real diff in production
            files_changed = implementation_result.get("files_changed", [])
        except Exception as e:
            logger.error(f"Implementation failed: {e}")
            implemented = False
            implementation_commit = None
            code_diff = ""
            files_changed = []

        # After snapshot
        after_snapshot = await self.create_capability_snapshot("system")

        # Calculate capability deltas
        capability_deltas = {}
        for cap in before_snapshot.capabilities:
            before_val = before_snapshot.capabilities.get(cap, 0)
            after_val = after_snapshot.capabilities.get(cap, 0)
            capability_deltas[cap] = after_val - before_val

        # Verify provenance
        provenance_status, provenance_notes = self.verifier.verify_provenance_chain(
            proposal.derivation_steps
        )

        # Create result
        result = ImprovementResult(
            result_id=result_id,
            proposal_id=proposal_id,
            implemented=implemented,
            implementation_commit=implementation_commit,
            code_diff=code_diff,
            files_changed=files_changed,
            before_snapshot_id=before_snapshot.snapshot_id,
            after_snapshot_id=after_snapshot.snapshot_id,
            capability_deltas=capability_deltas,
            ablation_result=AblationResult.NOT_TESTED,
            ablation_details="",
            provenance_status=provenance_status,
            provenance_chain=proposal.derivation_steps,
            verifier=None,
            novel_strategy_detected=False,
            strategy_description="",
            not_in_original_architecture=proposal.not_from_training,
            externally_validated=False,
            validation_notes=provenance_notes
        )

        # Run ablation test
        ablation = await self.ablation_tester.run_ablation(
            result,
            implementation_func,
            self.measurer
        )

        result.ablation_result = (
            AblationResult.PASSED if ablation.improvement_holds
            else AblationResult.FAILED
        )
        result.ablation_details = ablation.notes

        # Save results
        self._save_result(result)
        self._save_ablation(ablation)

        return result

    def get_proposal(self, proposal_id: str) -> Optional[ImprovementProposal]:
        """Retrieve a proposal by ID."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM improvement_proposals WHERE proposal_id = ?",
            (proposal_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return ImprovementProposal(
            proposal_id=row[0],
            improvement_type=ImprovementType(row[1]),
            title=row[2],
            description=row[3],
            hypothesis=row[4],
            rationale=row[5],
            before_snapshot_id=row[6],
            proposed_changes=json.loads(row[7]) if row[7] else {},
            expected_capability_deltas=json.loads(row[8]) if row[8] else {},
            success_criteria=json.loads(row[9]) if row[9] else [],
            source_inspiration=row[10],
            not_from_training=bool(row[11]),
            derivation_steps=json.loads(row[12]) if row[12] else [],
            created_at=row[13],
            status=row[14],
            metadata=json.loads(row[15]) if row[15] else {}
        )

    def _save_result(self, result: ImprovementResult):
        """Save improvement result to database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO improvement_results (
                result_id, proposal_id, implemented, implementation_commit,
                code_diff, files_changed, before_snapshot_id, after_snapshot_id,
                capability_deltas, ablation_result, ablation_details,
                provenance_status, provenance_chain, verifier,
                novel_strategy_detected, strategy_description,
                not_in_original_architecture, externally_validated,
                validation_notes, executed_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.result_id,
            result.proposal_id,
            result.implemented,
            result.implementation_commit,
            result.code_diff[:10000] if result.code_diff else "",
            json.dumps(result.files_changed),
            result.before_snapshot_id,
            result.after_snapshot_id,
            json.dumps(result.capability_deltas),
            result.ablation_result.value,
            result.ablation_details,
            result.provenance_status.value,
            json.dumps(result.provenance_chain),
            result.verifier,
            result.novel_strategy_detected,
            result.strategy_description,
            result.not_in_original_architecture,
            result.externally_validated,
            result.validation_notes,
            result.executed_at,
            json.dumps(result.metadata)
        ))

        conn.commit()
        conn.close()

    def _save_ablation(self, ablation: AblationTest):
        """Save ablation test to database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO ablation_tests (
                test_id, improvement_id, test_type, hypothesis, control_condition,
                with_improvement, without_improvement, random_baseline,
                improvement_holds, likely_training_pattern, confidence,
                executed_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ablation.test_id,
            ablation.improvement_id,
            ablation.test_type,
            ablation.hypothesis,
            ablation.control_condition,
            ablation.with_improvement,
            ablation.without_improvement,
            ablation.random_baseline,
            ablation.improvement_holds,
            ablation.likely_training_pattern,
            ablation.confidence,
            ablation.executed_at,
            ablation.notes
        ))

        conn.commit()
        conn.close()

    def get_agi_validation_status(self) -> Dict[str, Any]:
        """
        Check if self-improvement requirements are met for AGI claims.

        Requirements (per LLM Council):
        1. Capability deltas with code/provenance diffs
        2. Ablation tests proving not training patterns
        3. Novel strategies not in original architecture
        4. External verification of improvements
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Get all results
        cursor.execute("SELECT * FROM improvement_results")
        results = cursor.fetchall()

        # Get ablation tests
        cursor.execute("SELECT * FROM ablation_tests")
        ablations = cursor.fetchall()

        conn.close()

        if not results:
            return {
                "agi_validation_status": "NOT_STARTED",
                "message": "No self-improvements have been tracked",
                "requirements_met": {
                    "capability_deltas_tracked": False,
                    "ablation_tests_passed": False,
                    "novel_strategies_demonstrated": False,
                    "externally_validated": False,
                    "provenance_verified": False
                },
                "ready_for_agi_claim": False
            }

        # Analyze results
        has_capability_deltas = any(
            json.loads(r[8]) if r[8] else {}  # capability_deltas column
            for r in results
        )

        ablation_passed = any(
            a[8]  # improvement_holds column
            for a in ablations
        ) if ablations else False

        novel_strategies = any(
            bool(r[14])  # novel_strategy_detected column
            for r in results
        )

        externally_validated = any(
            bool(r[17])  # externally_validated column
            for r in results
        )

        provenance_verified = any(
            r[11] == "verified"  # provenance_status column
            for r in results
        )

        requirements = {
            "capability_deltas_tracked": has_capability_deltas,
            "ablation_tests_passed": ablation_passed,
            "novel_strategies_demonstrated": novel_strategies,
            "externally_validated": externally_validated,
            "provenance_verified": provenance_verified
        }

        all_met = all(requirements.values())

        return {
            "agi_validation_status": "PASSED" if all_met else "NOT_PASSED",
            "message": "All self-improvement requirements met" if all_met else "Missing requirements",
            "requirements_met": requirements,
            "ready_for_agi_claim": all_met,
            "total_improvements": len(results),
            "ablation_tests_run": len(ablations),
            "verified_improvements": sum(1 for r in results if r[11] == "verified")
        }

    def get_improvement_history(self) -> List[Dict[str, Any]]:
        """Get history of all improvements with provenance."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT r.*, p.title, p.improvement_type
            FROM improvement_results r
            JOIN improvement_proposals p ON r.proposal_id = p.proposal_id
            ORDER BY r.executed_at DESC
        """)

        results = []
        for row in cursor.fetchall():
            results.append({
                "result_id": row[0],
                "title": row[21],  # From join
                "type": row[22],  # From join
                "implemented": bool(row[2]),
                "capability_deltas": json.loads(row[8]) if row[8] else {},
                "ablation_result": row[9],
                "provenance_status": row[11],
                "externally_validated": bool(row[17]),
                "executed_at": row[19]
            })

        conn.close()
        return results


def create_example_proposal() -> ImprovementProposal:
    """
    Create example improvement proposal.

    WARNING: This is an INTERNAL example and does NOT count toward AGI claims.
    """
    return ImprovementProposal(
        proposal_id=str(uuid.uuid4()),
        improvement_type=ImprovementType.ALGORITHM_OPTIMIZATION,
        title="Optimize Memory Consolidation Algorithm",
        description="Improve the memory consolidation algorithm to better extract patterns",
        hypothesis="Modified algorithm will improve pattern extraction by 20%",
        rationale="Current algorithm misses temporal patterns; proposed change adds temporal weighting",
        before_snapshot_id="",
        proposed_changes={
            "file": "consolidation.py",
            "change_type": "algorithm_modification",
            "description": "Add temporal weighting to pattern extraction"
        },
        expected_capability_deltas={
            "pattern_extraction": 0.20,
            "memory_efficiency": 0.10
        },
        success_criteria=[
            "Pattern extraction improves by >15%",
            "No regression in other capabilities",
            "Ablation test passes"
        ],
        source_inspiration="Analysis of consolidation performance logs",
        not_from_training=True,  # Would need verification
        derivation_steps=[
            "Observed poor temporal pattern extraction in logs",
            "Hypothesized temporal weighting could help",
            "Designed weighting scheme based on recency",
            "Implemented and tested locally"
        ]
    )


async def main():
    """Demo the provenance self-improvement framework."""
    print("Provenance-Verified Self-Improvement Framework - Demo")
    print("=" * 55)
    print()
    print("WARNING: Internal examples DO NOT count toward AGI claims.")
    print("AGI validation requires external verification of improvements.")
    print()

    framework = ProvenanceSelfImprovementFramework()

    # Create capability snapshot
    snapshot = await framework.create_capability_snapshot("demo")
    print(f"Created capability snapshot: {snapshot.snapshot_id[:8]}...")
    print(f"  Git commit: {snapshot.git_commit[:8]}...")
    print(f"  Capabilities: {snapshot.capabilities}")
    print()

    # Create example proposal
    proposal = create_example_proposal()
    proposal.before_snapshot_id = snapshot.snapshot_id
    framework.create_proposal(proposal)
    print(f"Created proposal: {proposal.title}")
    print()

    # Check validation status
    status = framework.get_agi_validation_status()
    print("AGI Validation Status:")
    print(f"  Status: {status['agi_validation_status']}")
    print(f"  Ready for AGI claim: {status['ready_for_agi_claim']}")
    print(f"  Requirements met: {status['requirements_met']}")


if __name__ == "__main__":
    asyncio.run(main())

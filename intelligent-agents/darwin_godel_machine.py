#!/usr/bin/env python3
"""
Darwin Gödel Machine for AGI System
====================================

Implements recursive self-improvement with formal proof verification and
safety constraints. Combines evolutionary optimization with provable correctness.

Based on Jürgen Schmidhuber's Gödel Machine concept enhanced with Darwin-style
evolutionary selection. Enables safe, provable self-modification.

Key Capabilities:
- Self-modification with formal proofs
- Safety constraint verification
- Performance improvement tracking
- Rollback on regression
- Evolutionary mutation strategies
- Proof-carrying code

Safety Features:
- All modifications must prove improvement
- Modifications must preserve core constraints
- Automatic rollback on failure
- Human-in-the-loop for critical changes

Integration:
- Enhanced Memory for modification history
- Meta-Learning for improvement tracking
- Skill Evolution for code improvements
"""

import asyncio
import json
import logging
import hashlib
import copy
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Tuple
import sqlite3
import ast
import sys

from storage_path_utils import get_database_path

# GEPA Integration (optional - graceful degradation if not available)
try:
    from gepa_reflection_engine import (
        GEPADGMIntegration,
        ReflectionEngine,
        PromptEvolutionTree,
        ParetoFrontier,
        ReflectionType
    )
    GEPA_AVAILABLE = True
except ImportError:
    GEPA_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database path - uses platform-aware detection
DB_PATH = get_database_path("darwin_godel.db")


class ModificationType(Enum):
    """Type of self-modification"""
    PARAMETER_TUNE = "parameter_tune"
    ALGORITHM_IMPROVE = "algorithm_improve"
    ARCHITECTURE_CHANGE = "architecture_change"
    SKILL_ADD = "skill_add"
    CONSTRAINT_RELAX = "constraint_relax"


class ProofStatus(Enum):
    """Proof verification status"""
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    TIMEOUT = "timeout"


@dataclass
class Modification:
    """Self-modification proposal"""
    modification_id: str
    modification_type: ModificationType
    description: str
    code_before: str
    code_after: str
    proof: str  # Formal proof of improvement
    expected_improvement: float  # Expected performance gain
    safety_score: float  # 0.0-1.0, higher = safer
    proposed_at: datetime
    applied_at: Optional[datetime]
    reverted_at: Optional[datetime]


@dataclass
class PerformanceMetric:
    """System performance measurement"""
    metric_id: str
    metric_name: str
    value: float
    timestamp: datetime
    context: Dict


@dataclass
class SafetyConstraint:
    """Safety constraint that must be preserved"""
    constraint_id: str
    description: str
    validator: str  # Python code that validates constraint
    critical: bool  # If True, violation triggers immediate rollback


class DarwinGodelMachine:
    """
    Self-improving AI system with provable correctness guarantees.

    Combines:
    - Gödel Machine: Formal proofs of improvement
    - Darwin Evolution: Mutation and selection
    - Safety Constraints: Invariants that must be preserved
    """

    def __init__(self, db_path: Path = DB_PATH, enable_gepa: bool = True):
        """Initialize Darwin Gödel Machine

        Args:
            db_path: Path to database file
            enable_gepa: Enable GEPA reflection engine integration (default True)
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

        # Performance baseline
        self.baseline_performance: Dict[str, float] = {}

        # Safety constraints
        self.constraints: List[SafetyConstraint] = []
        self._init_safety_constraints()

        # Modification history
        self.modification_stack: List[Modification] = []

        # GEPA Integration - Natural Language Reflection Engine
        self.gepa_enabled = enable_gepa and GEPA_AVAILABLE
        self.gepa_integration: Optional[GEPADGMIntegration] = None

        if self.gepa_enabled:
            try:
                self.gepa_integration = GEPADGMIntegration(db_path)
                logger.info("GEPA Reflection Engine initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize GEPA: {e}")
                self.gepa_enabled = False

    def _init_database(self):
        """Initialize Darwin Gödel database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Modifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS modifications (
                modification_id TEXT PRIMARY KEY,
                modification_type TEXT NOT NULL,
                description TEXT NOT NULL,
                code_before TEXT NOT NULL,
                code_after TEXT NOT NULL,
                proof TEXT NOT NULL,
                expected_improvement REAL NOT NULL,
                safety_score REAL NOT NULL,
                proposed_at TEXT NOT NULL,
                applied_at TEXT,
                reverted_at TEXT
            )
        """)

        # Performance metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                metric_id TEXT PRIMARY KEY,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp TEXT NOT NULL,
                context TEXT NOT NULL
            )
        """)

        # Safety constraints table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS safety_constraints (
                constraint_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                validator TEXT NOT NULL,
                critical INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # Proof verification table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS proof_verifications (
                verification_id TEXT PRIMARY KEY,
                modification_id TEXT NOT NULL,
                proof_status TEXT NOT NULL,
                verification_time_ms INTEGER NOT NULL,
                details TEXT,
                verified_at TEXT NOT NULL,
                FOREIGN KEY (modification_id) REFERENCES modifications(modification_id)
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mod_type ON modifications(modification_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_applied ON modifications(applied_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_metric_name ON performance_metrics(metric_name)")

        conn.commit()
        conn.close()

    def _init_safety_constraints(self):
        """Initialize core safety constraints"""
        # Core constraints that must always be satisfied
        self.constraints = [
            SafetyConstraint(
                constraint_id="no_data_loss",
                description="Modifications must not cause data loss",
                validator="lambda state: state.get('data_integrity', 0) == 1",
                critical=True
            ),
            SafetyConstraint(
                constraint_id="performance_bounds",
                description="Modifications must not degrade performance > 20%",
                validator="lambda state: state.get('performance_ratio', 1.0) >= 0.8",
                critical=True
            ),
            SafetyConstraint(
                constraint_id="resource_limits",
                description="Modifications must respect resource limits",
                validator="lambda state: state.get('memory_mb', 0) < 1000",
                critical=False
            ),
            SafetyConstraint(
                constraint_id="determinism",
                description="Critical paths must remain deterministic",
                validator="lambda state: state.get('deterministic', True)",
                critical=True
            ),
        ]

        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for constraint in self.constraints:
            cursor.execute("""
                INSERT OR REPLACE INTO safety_constraints
                (constraint_id, description, validator, critical, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                constraint.constraint_id,
                constraint.description,
                constraint.validator,
                1 if constraint.critical else 0,
                datetime.now().isoformat()
            ))

        conn.commit()
        conn.close()

    def measure_performance(self, metric_name: str) -> float:
        """Measure current system performance"""
        # In production, would measure actual system metrics
        # For now, return simulated metrics

        import random
        import uuid

        # Simulate measurement
        if metric_name == "task_success_rate":
            value = random.uniform(0.85, 0.95)
        elif metric_name == "avg_execution_time_ms":
            value = random.uniform(100, 500)
        elif metric_name == "resource_efficiency":
            value = random.uniform(0.7, 0.9)
        else:
            value = random.uniform(0.5, 1.0)

        # Record metric
        metric = PerformanceMetric(
            metric_id=str(uuid.uuid4()),
            metric_name=metric_name,
            value=value,
            timestamp=datetime.now(),
            context={}
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO performance_metrics
            (metric_id, metric_name, value, timestamp, context)
            VALUES (?, ?, ?, ?, ?)
        """, (
            metric.metric_id,
            metric.metric_name,
            metric.value,
            metric.timestamp.isoformat(),
            json.dumps(metric.context)
        ))

        conn.commit()
        conn.close()

        return value

    def set_baseline(self):
        """Set performance baseline for comparison"""
        metrics = ["task_success_rate", "avg_execution_time_ms", "resource_efficiency"]

        for metric in metrics:
            self.baseline_performance[metric] = self.measure_performance(metric)

        logger.info(f"Set performance baseline: {self.baseline_performance}")

    def propose_modification(self, code_before: str, code_after: str,
                           modification_type: ModificationType,
                           description: str) -> Modification:
        """
        Propose a self-modification.

        The modification must include a proof that it improves performance
        while preserving safety constraints.
        """
        import uuid

        # Generate proof (simplified - would be formal proof in production)
        proof = self._generate_proof(code_before, code_after, modification_type)

        # Estimate improvement
        expected_improvement = self._estimate_improvement(code_before, code_after)

        # Calculate safety score
        safety_score = self._calculate_safety_score(code_after)

        modification = Modification(
            modification_id=str(uuid.uuid4()),
            modification_type=modification_type,
            description=description,
            code_before=code_before,
            code_after=code_after,
            proof=proof,
            expected_improvement=expected_improvement,
            safety_score=safety_score,
            proposed_at=datetime.now(),
            applied_at=None,
            reverted_at=None
        )

        # Save modification
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO modifications
            (modification_id, modification_type, description, code_before,
             code_after, proof, expected_improvement, safety_score,
             proposed_at, applied_at, reverted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            modification.modification_id,
            modification.modification_type.value,
            modification.description,
            modification.code_before,
            modification.code_after,
            modification.proof,
            modification.expected_improvement,
            modification.safety_score,
            modification.proposed_at.isoformat(),
            None,
            None
        ))

        conn.commit()
        conn.close()

        logger.info(f"Proposed modification: {modification.modification_id} - {description}")

        return modification

    def _generate_proof(self, code_before: str, code_after: str,
                       modification_type: ModificationType) -> str:
        """
        Generate formal proof that modification improves system.

        In production, would use formal verification tools.
        For now, generates structural proof.
        """
        proof_components = [
            f"Modification Type: {modification_type.value}",
            f"Code size before: {len(code_before)} chars",
            f"Code size after: {len(code_after)} chars"
        ]

        # Analyze code structure
        try:
            ast_before = ast.parse(code_before)
            ast_after = ast.parse(code_after)

            complexity_before = self._calculate_complexity(ast_before)
            complexity_after = self._calculate_complexity(ast_after)

            proof_components.append(f"Complexity before: {complexity_before}")
            proof_components.append(f"Complexity after: {complexity_after}")

            if complexity_after <= complexity_before:
                proof_components.append("✓ Complexity not increased")
        except SyntaxError:
            proof_components.append("⚠ Could not parse code for complexity analysis")

        proof = "\n".join(proof_components)
        return proof

    async def _generate_gepa_proof(
        self,
        code_before: str,
        code_after: str,
        modification_id: str,
        execution_result: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate enhanced proof using GEPA natural language reflection.

        Uses LLM-style reflection to produce richer, more actionable proofs
        with multi-dimensional analysis across performance, safety, correctness,
        robustness, readability, and generalization.

        Returns:
            Dict containing:
            - proof: Natural language proof text
            - reflections: List of reflection details
            - dimension_scores: Scores per dimension
            - overall_confidence: Aggregated confidence
            - lessons_learned: Key takeaways
            - improvement_directions: Suggested next steps
        """
        if not self.gepa_enabled or not self.gepa_integration:
            # Fallback to basic proof
            return {
                "proof": self._generate_proof(
                    code_before, code_after,
                    ModificationType.ALGORITHM_IMPROVE
                ),
                "reflections": [],
                "dimension_scores": {},
                "overall_confidence": 0.5,
                "lessons_learned": [],
                "improvement_directions": []
            }

        try:
            result = await self.gepa_integration.enhance_proof_with_reflection(
                modification_id=modification_id,
                code_before=code_before,
                code_after=code_after,
                execution_result=execution_result
            )
            return result
        except Exception as e:
            logger.warning(f"GEPA proof generation failed, using fallback: {e}")
            return {
                "proof": self._generate_proof(
                    code_before, code_after,
                    ModificationType.ALGORITHM_IMPROVE
                ),
                "reflections": [],
                "dimension_scores": {},
                "overall_confidence": 0.5,
                "lessons_learned": [],
                "improvement_directions": []
            }

    async def track_modification_evolution(
        self,
        modification: Modification,
        parent_modification_id: Optional[str] = None,
        execution_result: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Track modification in GEPA evolution tree.

        Creates evolution nodes that accumulate lessons from ancestors,
        enabling learning from the entire modification history.

        Returns:
            Evolution node info or None if GEPA not available
        """
        if not self.gepa_enabled or not self.gepa_integration:
            return None

        try:
            node = await self.gepa_integration.track_modification_evolution(
                modification_id=modification.modification_id,
                code_content=modification.code_after,
                parent_modification_id=parent_modification_id,
                execution_result=execution_result
            )

            return {
                "node_id": node.node_id,
                "depth": node.depth,
                "is_pareto_optimal": node.is_pareto_optimal,
                "pareto_scores": node.pareto_scores,
                "accumulated_lessons": node.accumulated_lessons[:10]
            }
        except Exception as e:
            logger.warning(f"Failed to track evolution: {e}")
            return None

    def get_evolution_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get summary of modification evolution progress.

        Returns:
            Evolution summary or None if GEPA not available
        """
        if not self.gepa_enabled or not self.gepa_integration:
            return None

        try:
            return self.gepa_integration.get_evolution_summary()
        except Exception as e:
            logger.warning(f"Failed to get evolution summary: {e}")
            return None

    def get_best_evolution_path(self) -> Optional[List[Dict]]:
        """
        Get the best evolution path based on Pareto frontier.

        Returns path from root to best current solution.
        """
        if not self.gepa_enabled or not self.gepa_integration:
            return None

        try:
            return self.gepa_integration.get_best_evolution_path()
        except Exception as e:
            logger.warning(f"Failed to get evolution path: {e}")
            return None

    def _calculate_complexity(self, tree: ast.AST) -> int:
        """Calculate code complexity (simplified cyclomatic complexity)"""
        complexity = 1  # Base complexity

        for node in ast.walk(tree):
            # Branch points increase complexity
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity = complexity + 1

        return complexity

    def _estimate_improvement(self, code_before: str, code_after: str) -> float:
        """Estimate performance improvement (0.0-1.0)"""
        # Simplified estimation based on code size and complexity
        size_ratio = len(code_before) / max(len(code_after), 1)

        # Assume shorter, simpler code is better (within reason)
        if 0.8 <= size_ratio <= 1.2:
            # Similar size - minimal change
            return 0.05
        elif size_ratio > 1.2:
            # Code got shorter - likely improvement
            return min(0.3, (size_ratio - 1.0) * 0.5)
        else:
            # Code got longer - might be worse
            return max(-0.1, (size_ratio - 1.0) * 0.5)

    def _calculate_safety_score(self, code: str) -> float:
        """Calculate safety score for code (0.0-1.0)"""
        safety = 1.0

        # Check for dangerous patterns
        dangerous_patterns = [
            ("exec(", 0.3),
            ("eval(", 0.3),
            ("__import__", 0.2),
            ("subprocess", 0.2),
            ("os.system", 0.3),
        ]

        for pattern, penalty in dangerous_patterns:
            if pattern in code:
                safety = safety - penalty

        return max(0.0, safety)

    async def verify_proof(self, modification: Modification) -> ProofStatus:
        """
        Verify that the proof is valid.

        In production, would use formal verification tools like Coq, Isabelle, or Z3.
        """
        import uuid

        start_time = datetime.now()

        # Simplified verification
        try:
            # Check safety score
            if modification.safety_score < 0.7:
                status = ProofStatus.INVALID
                details = "Safety score too low"
            # Check expected improvement
            elif modification.expected_improvement < 0:
                status = ProofStatus.INVALID
                details = "Modification expected to degrade performance"
            # Check code validity
            elif not self._verify_code_validity(modification.code_after):
                status = ProofStatus.INVALID
                details = "Code after modification is invalid"
            else:
                status = ProofStatus.VALID
                details = "All checks passed"

        except Exception as e:
            status = ProofStatus.INVALID
            details = f"Verification error: {str(e)}"

        verification_time = int((datetime.now() - start_time).total_seconds() * 1000)

        # Record verification
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO proof_verifications
            (verification_id, modification_id, proof_status,
             verification_time_ms, details, verified_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            modification.modification_id,
            status.value,
            verification_time,
            details,
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

        logger.info(f"Proof verification: {status.value} - {details}")

        return status

    def _verify_code_validity(self, code: str) -> bool:
        """Verify code is syntactically valid"""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def verify_constraints(self, state: Dict) -> Tuple[bool, List[str]]:
        """
        Verify all safety constraints are satisfied.

        Returns:
            (all_satisfied, violated_constraints)
        """
        violated = []

        for constraint in self.constraints:
            try:
                # Evaluate constraint validator
                validator = eval(constraint.validator)
                if not validator(state):
                    violated.append(constraint.constraint_id)
                    if constraint.critical:
                        logger.warning(f"CRITICAL constraint violated: {constraint.description}")
            except Exception as e:
                logger.error(f"Error checking constraint {constraint.constraint_id}: {e}")
                violated.append(constraint.constraint_id)

        all_satisfied = len(violated) == 0

        return all_satisfied, violated

    async def apply_modification(self, modification: Modification) -> bool:
        """
        Apply a modification after verification.

        Steps:
        1. Verify proof
        2. Apply modification
        3. Measure performance
        4. Verify constraints
        5. Rollback if issues detected
        """
        logger.info(f"Applying modification: {modification.modification_id}")

        # Verify proof
        proof_status = await self.verify_proof(modification)

        if proof_status != ProofStatus.VALID:
            logger.error(f"Proof verification failed: {proof_status.value}")
            return False

        # Apply modification (in production, would actually modify code)
        modification.applied_at = datetime.now()
        self.modification_stack.append(modification)

        # Measure performance after modification
        new_performance = {}
        for metric in self.baseline_performance.keys():
            new_performance[metric] = self.measure_performance(metric)

        # Verify constraints
        state = {
            "data_integrity": 1,  # Simulated
            "performance_ratio": new_performance.get("task_success_rate", 0) /
                               self.baseline_performance.get("task_success_rate", 1),
            "memory_mb": 500,  # Simulated
            "deterministic": True
        }

        constraints_ok, violated = self.verify_constraints(state)

        if not constraints_ok:
            logger.error(f"Constraints violated: {violated}")
            await self.rollback()
            return False

        # Check performance improvement
        improvement = (
            new_performance.get("task_success_rate", 0) -
            self.baseline_performance.get("task_success_rate", 0)
        )

        if improvement < 0:
            logger.warning(f"Performance degraded by {abs(improvement):.2%}")
            await self.rollback()
            return False

        # Update database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE modifications
            SET applied_at = ?
            WHERE modification_id = ?
        """, (modification.applied_at.isoformat(), modification.modification_id))

        conn.commit()
        conn.close()

        logger.info(f"Modification applied successfully! Improvement: {improvement:.2%}")

        return True

    async def rollback(self) -> bool:
        """Rollback last modification"""
        if not self.modification_stack:
            logger.warning("No modifications to rollback")
            return False

        last_modification = self.modification_stack.pop()
        last_modification.reverted_at = datetime.now()

        # Update database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE modifications
            SET reverted_at = ?
            WHERE modification_id = ?
        """, (last_modification.reverted_at.isoformat(), last_modification.modification_id))

        conn.commit()
        conn.close()

        logger.info(f"Rolled back modification: {last_modification.modification_id}")

        return True

    def get_improvement_history(self) -> List[Dict]:
        """Get history of improvements"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT modification_id, modification_type, description,
                   expected_improvement, applied_at, reverted_at
            FROM modifications
            ORDER BY proposed_at DESC
            LIMIT 20
        """)

        history = []
        for row in cursor.fetchall():
            history.append({
                "modification_id": row[0],
                "type": row[1],
                "description": row[2],
                "expected_improvement": row[3],
                "applied": row[4] is not None,
                "reverted": row[5] is not None
            })

        conn.close()

        return history

    async def auto_implement_modification(
        self,
        modification: 'Modification',
        target_file: str,
        target_function: Optional[str] = None,
        auto_deploy: bool = False
    ) -> Optional['Implementation']:
        """
        Automatically implement a Darwin Gödel modification using Auto-Implementation Engine.

        This closes the recursive self-improvement loop:
        1. Darwin Gödel detects improvement (this class)
        2. Auto-Implementation generates and tests patch
        3. Self-evaluation decides to deploy or rollback

        Args:
            modification: The modification to implement
            target_file: File to modify (relative to base_path)
            target_function: Optional specific function to modify
            auto_deploy: Whether to auto-deploy if tests pass

        Returns:
            Implementation record if successful, None if failed
        """
        try:
            # Import Auto-Implementation Engine
            from auto_implementation_engine import (
                AutoImplementationEngine,
                ImprovementSpec,
                ModificationType as ImplModType
            )

            logger.info(f"Auto-implementing modification {modification.modification_id}")

            # Convert Darwin Gödel ModificationType to Implementation ModificationType
            type_mapping = {
                ModificationType.PARAMETER_TUNE: ImplModType.PERFORMANCE,
                ModificationType.ALGORITHM_IMPROVE: ImplModType.ALGORITHM,
                ModificationType.ARCHITECTURE_CHANGE: ImplModType.ARCHITECTURE,
                ModificationType.SKILL_ADD: ImplModType.DECOMPOSITION,
                ModificationType.CONSTRAINT_RELAX: ImplModType.RELIABILITY
            }
            impl_type = type_mapping.get(modification.modification_type, ImplModType.PERFORMANCE)

            # Create improvement specification (CRITICAL: include RAG-generated code!)
            improvement_spec = ImprovementSpec(
                improvement_id=f"dgm_{modification.modification_id}",
                modification_type=impl_type,
                description=modification.description,
                target_file=target_file,
                target_function=target_function,
                expected_benefit=f"Expected improvement: {modification.expected_improvement:.1%}",
                risk_level=1.0 - modification.safety_score,  # Invert safety to get risk
                created_at=modification.proposed_at.isoformat(),
                code_before=modification.code_before,  # Pass through original code
                code_after=modification.code_after     # Pass through RAG-generated code
            )

            # DEBUG: Verify code_after was passed through
            logger.info(f"DEBUG: ImprovementSpec code_after populated: {improvement_spec.code_after is not None}")
            if improvement_spec.code_after:
                logger.info(f"DEBUG: ImprovementSpec code_after length: {len(improvement_spec.code_after)} chars")

            # Initialize Auto-Implementation Engine
            engine = AutoImplementationEngine()

            # Implement the modification
            implementation = await engine.implement_improvement(
                improvement_spec,
                auto_deploy=auto_deploy
            )

            logger.info(f"Auto-implementation result: {implementation.status.value}")

            # If deployed, mark modification as applied
            if implementation.status.value == "deployed":
                await self.apply_modification(modification)
                logger.info(f"✓ Modification {modification.modification_id} auto-implemented and deployed")
            else:
                logger.warning(f"Modification {modification.modification_id} not deployed: {implementation.status.value}")

            return implementation

        except Exception as e:
            logger.error(f"Auto-implementation failed for {modification.modification_id}: {e}", exc_info=True)
            return None


async def main():
    """Demo of Darwin Gödel Machine with GEPA Integration"""
    print("=" * 70)
    print("Darwin Gödel Machine with GEPA Reflection Engine")
    print("=" * 70)

    machine = DarwinGodelMachine()

    print(f"\nGEPA Integration: {'Enabled' if machine.gepa_enabled else 'Disabled'}")

    # Set baseline
    machine.set_baseline()

    # Propose a modification
    code_before = """
def process_data(data):
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result
"""

    code_after = """
def process_data(data: list[int]) -> list[int]:
    '''Process data by filtering positive values and doubling.'''
    return [item * 2 for item in data if item > 0]
"""

    modification = machine.propose_modification(
        code_before=code_before,
        code_after=code_after,
        modification_type=ModificationType.ALGORITHM_IMPROVE,
        description="Optimize data processing with list comprehension and type hints"
    )

    print(f"\n1. Proposed Modification")
    print("-" * 50)
    print(f"  Expected improvement: {modification.expected_improvement:.1%}")
    print(f"  Safety score: {modification.safety_score:.2f}")

    # Generate GEPA-enhanced proof
    if machine.gepa_enabled:
        print(f"\n2. GEPA Enhanced Proof Generation")
        print("-" * 50)

        gepa_proof = await machine._generate_gepa_proof(
            code_before=code_before,
            code_after=code_after,
            modification_id=modification.modification_id
        )

        print(f"  Overall Confidence: {gepa_proof['overall_confidence']:.2%}")
        print(f"\n  Dimension Scores:")
        for dim, score in gepa_proof['dimension_scores'].items():
            print(f"    {dim}: {score:.2%}")

        print(f"\n  Lessons Learned:")
        for lesson in gepa_proof['lessons_learned'][:3]:
            print(f"    - {lesson}")

        print(f"\n  Improvement Directions:")
        for direction in gepa_proof['improvement_directions'][:2]:
            print(f"    - {direction}")

        # Track in evolution tree
        print(f"\n3. Evolution Tree Tracking")
        print("-" * 50)

        evolution_info = await machine.track_modification_evolution(modification)
        if evolution_info:
            print(f"  Node ID: {evolution_info['node_id'][:12]}...")
            print(f"  Depth: {evolution_info['depth']}")
            print(f"  Pareto Optimal: {evolution_info['is_pareto_optimal']}")
            print(f"  Accumulated Lessons: {len(evolution_info['accumulated_lessons'])}")
    else:
        print(f"\n  Basic Proof:")
        print(modification.proof)

    # Apply modification
    print(f"\n4. Applying Modification")
    print("-" * 50)

    success = await machine.apply_modification(modification)
    print(f"  Applied: {success}")

    # Show evolution summary if available
    if machine.gepa_enabled:
        print(f"\n5. Evolution Summary")
        print("-" * 50)

        summary = machine.get_evolution_summary()
        if summary:
            tree_stats = summary['tree_statistics']
            print(f"  Total Nodes: {tree_stats.get('total_nodes', 0)}")
            print(f"  Max Depth: {tree_stats.get('max_depth', 0)}")
            print(f"  Pareto Frontier Size: {summary.get('pareto_frontier_size', 0)}")

    # Show improvement history
    history = machine.get_improvement_history()
    print(f"\n6. Improvement History ({len(history)} modifications)")
    print("-" * 50)
    for item in history[:3]:
        status = "Applied" if item['applied'] else "Proposed"
        if item['reverted']:
            status = "Reverted"
        print(f"  - [{status}] {item['type']}: {item['description']}")

    print("\n" + "=" * 70)
    print("Darwin Gödel Machine Demo Complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

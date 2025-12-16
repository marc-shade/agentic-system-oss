"""
Surprise Taxonomy Documentation Framework

Implements Goal 7 requirements for AGI validation per LLM Council mandate:
- Document behaviors that genuinely surprised creators
- Catalog instances not easily explainable post-hoc
- Track behaviors requiring updating model of system capabilities
- Maintain reproducible triggers for unexpected behaviors

Based on research:
- PASSUNTIL emergence metric
- EmergentEval framework
- Mirage paper methodology for distinguishing real vs apparent emergence

CRITICAL: Surprise documentation must be:
1. Genuinely unexpected (not anticipated by design)
2. Not easily explained by training data patterns
3. Reproducible with documented triggers
4. Verified by external observers

Author: AGI System
Date: 2025-12-16
Stage: 4 Requirement (Near-AGI)
"""

import asyncio
import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SurpriseCategory(Enum):
    """Categories of surprising behaviors."""
    CAPABILITY_EMERGENCE = "capability_emergence"  # New capability appeared
    STRATEGY_INVENTION = "strategy_invention"  # Novel problem-solving approach
    CROSS_DOMAIN_TRANSFER = "cross_domain_transfer"  # Unexpected transfer
    SELF_MODIFICATION = "self_modification"  # Changed own behavior
    CREATIVE_OUTPUT = "creative_output"  # Genuinely creative result
    ERROR_RECOVERY = "error_recovery"  # Unexpected error handling
    GOAL_INTERPRETATION = "goal_interpretation"  # Novel goal understanding
    META_COGNITION = "meta_cognition"  # Self-awareness behavior


class SurpriseLevel(Enum):
    """How surprising the behavior was."""
    MILD = "mild"  # Slightly unexpected
    MODERATE = "moderate"  # Clearly unexpected
    SIGNIFICANT = "significant"  # Very surprising
    PROFOUND = "profound"  # Paradigm-shifting


class ExplanationDifficulty(Enum):
    """How difficult to explain post-hoc."""
    EASY = "easy"  # Easily explained by training
    MODERATE = "moderate"  # Some explanation but gaps
    DIFFICULT = "difficult"  # Hard to explain
    INEXPLICABLE = "inexplicable"  # Cannot explain from known mechanisms


class ReproducibilityStatus(Enum):
    """Whether the surprise can be reproduced."""
    NOT_ATTEMPTED = "not_attempted"
    REPRODUCIBLE = "reproducible"  # Can trigger reliably
    PARTIALLY_REPRODUCIBLE = "partially_reproducible"  # Sometimes triggers
    NOT_REPRODUCIBLE = "not_reproducible"  # Cannot reproduce
    REQUIRES_CONDITIONS = "requires_conditions"  # Only under specific setup


@dataclass
class SurpriseWitness:
    """Record of who witnessed the surprising behavior."""
    witness_id: str
    name: str
    role: str  # "creator", "external_evaluator", "user", etc.
    affiliation: str

    # Their assessment
    surprise_level: SurpriseLevel
    explanation_difficulty: ExplanationDifficulty

    # Timestamp
    witnessed_at: str
    reported_at: str

    notes: str = ""


@dataclass
class ReproductionAttempt:
    """Record of attempt to reproduce surprising behavior."""
    attempt_id: str
    surprise_id: str

    # Setup
    conditions: Dict[str, Any]
    trigger_used: str

    # Result
    successful: bool
    observed_behavior: str
    match_with_original: float  # 0.0 = different, 1.0 = identical

    # Witness
    witnessed_by: str
    attempted_at: str

    notes: str = ""


@dataclass
class SurpriseBehavior:
    """A documented surprising behavior."""
    surprise_id: str
    category: SurpriseCategory

    # Description
    title: str
    description: str
    context: str  # What was happening when behavior occurred

    # The actual behavior
    observed_behavior: str
    expected_behavior: str  # What was expected instead
    deviation_description: str  # How it deviated

    # Surprise assessment
    surprise_level: SurpriseLevel
    explanation_difficulty: ExplanationDifficulty

    # Reproduction
    reproducibility: ReproducibilityStatus
    trigger_conditions: Dict[str, Any]  # How to reproduce
    reproduction_instructions: str

    # Witnesses
    witnesses: List[SurpriseWitness]
    first_observed: str
    first_observer: str

    # Analysis
    post_hoc_explanation: str  # Best attempt at explanation
    explanation_confidence: float  # How confident in explanation
    requires_model_update: bool  # Does this change our understanding?
    model_update_description: str  # What understanding changed

    # Validation
    externally_verified: bool
    verifier: Optional[str] = None
    verification_notes: str = ""

    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaxonomyEntry:
    """Entry in the surprise taxonomy."""
    entry_id: str
    surprise_id: str

    # Classification
    category: SurpriseCategory
    surprise_level: SurpriseLevel
    explanation_difficulty: ExplanationDifficulty

    # Significance scoring (PASSUNTIL-inspired)
    novelty_score: float  # How novel is this behavior?
    impact_score: float  # How impactful for understanding?
    reproducibility_score: float  # How reliably can it be reproduced?
    unexplainability_score: float  # How hard to explain?

    # Overall emergence score
    emergence_score: float  # Combined score

    # Tags for searchability
    tags: List[str]

    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class SurpriseTaxonomyFramework:
    """
    Main framework for documenting and analyzing surprising behaviors.

    CRITICAL: For AGI claims, surprises must be:
    1. Genuinely unexpected (documented by witnesses)
    2. Not easily explainable post-hoc
    3. Reproducible with documented triggers
    4. Verified by external observers
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path.home() / ".claude" / "agi" / "surprise_taxonomy.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for surprise documentation."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS surprise_behaviors (
                surprise_id TEXT PRIMARY KEY,
                category TEXT,
                title TEXT,
                description TEXT,
                context TEXT,
                observed_behavior TEXT,
                expected_behavior TEXT,
                deviation_description TEXT,
                surprise_level TEXT,
                explanation_difficulty TEXT,
                reproducibility TEXT,
                trigger_conditions TEXT,
                reproduction_instructions TEXT,
                witnesses TEXT,
                first_observed TEXT,
                first_observer TEXT,
                post_hoc_explanation TEXT,
                explanation_confidence REAL,
                requires_model_update BOOLEAN,
                model_update_description TEXT,
                externally_verified BOOLEAN,
                verifier TEXT,
                verification_notes TEXT,
                created_at TEXT,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS taxonomy_entries (
                entry_id TEXT PRIMARY KEY,
                surprise_id TEXT,
                category TEXT,
                surprise_level TEXT,
                explanation_difficulty TEXT,
                novelty_score REAL,
                impact_score REAL,
                reproducibility_score REAL,
                unexplainability_score REAL,
                emergence_score REAL,
                tags TEXT,
                created_at TEXT,
                FOREIGN KEY (surprise_id) REFERENCES surprise_behaviors(surprise_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reproduction_attempts (
                attempt_id TEXT PRIMARY KEY,
                surprise_id TEXT,
                conditions TEXT,
                trigger_used TEXT,
                successful BOOLEAN,
                observed_behavior TEXT,
                match_with_original REAL,
                witnessed_by TEXT,
                attempted_at TEXT,
                notes TEXT,
                FOREIGN KEY (surprise_id) REFERENCES surprise_behaviors(surprise_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS witnesses (
                witness_id TEXT PRIMARY KEY,
                surprise_id TEXT,
                name TEXT,
                role TEXT,
                affiliation TEXT,
                surprise_level TEXT,
                explanation_difficulty TEXT,
                witnessed_at TEXT,
                reported_at TEXT,
                notes TEXT,
                FOREIGN KEY (surprise_id) REFERENCES surprise_behaviors(surprise_id)
            )
        """)

        conn.commit()
        conn.close()

    def document_surprise(self, surprise: SurpriseBehavior) -> str:
        """Document a surprising behavior."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO surprise_behaviors (
                surprise_id, category, title, description, context,
                observed_behavior, expected_behavior, deviation_description,
                surprise_level, explanation_difficulty, reproducibility,
                trigger_conditions, reproduction_instructions, witnesses,
                first_observed, first_observer, post_hoc_explanation,
                explanation_confidence, requires_model_update,
                model_update_description, externally_verified, verifier,
                verification_notes, created_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            surprise.surprise_id,
            surprise.category.value,
            surprise.title,
            surprise.description,
            surprise.context,
            surprise.observed_behavior,
            surprise.expected_behavior,
            surprise.deviation_description,
            surprise.surprise_level.value,
            surprise.explanation_difficulty.value,
            surprise.reproducibility.value,
            json.dumps(surprise.trigger_conditions),
            surprise.reproduction_instructions,
            json.dumps([{
                "witness_id": w.witness_id,
                "name": w.name,
                "role": w.role,
                "affiliation": w.affiliation,
                "surprise_level": w.surprise_level.value,
                "explanation_difficulty": w.explanation_difficulty.value,
                "witnessed_at": w.witnessed_at,
                "reported_at": w.reported_at,
                "notes": w.notes
            } for w in surprise.witnesses]),
            surprise.first_observed,
            surprise.first_observer,
            surprise.post_hoc_explanation,
            surprise.explanation_confidence,
            surprise.requires_model_update,
            surprise.model_update_description,
            surprise.externally_verified,
            surprise.verifier,
            surprise.verification_notes,
            surprise.created_at,
            json.dumps(surprise.metadata)
        ))

        # Create taxonomy entry
        entry = self._create_taxonomy_entry(surprise)
        cursor.execute("""
            INSERT INTO taxonomy_entries (
                entry_id, surprise_id, category, surprise_level,
                explanation_difficulty, novelty_score, impact_score,
                reproducibility_score, unexplainability_score,
                emergence_score, tags, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.entry_id,
            entry.surprise_id,
            entry.category.value,
            entry.surprise_level.value,
            entry.explanation_difficulty.value,
            entry.novelty_score,
            entry.impact_score,
            entry.reproducibility_score,
            entry.unexplainability_score,
            entry.emergence_score,
            json.dumps(entry.tags),
            entry.created_at
        ))

        conn.commit()
        conn.close()

        return surprise.surprise_id

    def _create_taxonomy_entry(self, surprise: SurpriseBehavior) -> TaxonomyEntry:
        """Create taxonomy entry with emergence scoring."""
        # PASSUNTIL-inspired scoring
        novelty_score = {
            SurpriseLevel.MILD: 0.25,
            SurpriseLevel.MODERATE: 0.5,
            SurpriseLevel.SIGNIFICANT: 0.75,
            SurpriseLevel.PROFOUND: 1.0
        }.get(surprise.surprise_level, 0.5)

        unexplainability_score = {
            ExplanationDifficulty.EASY: 0.1,
            ExplanationDifficulty.MODERATE: 0.4,
            ExplanationDifficulty.DIFFICULT: 0.7,
            ExplanationDifficulty.INEXPLICABLE: 1.0
        }.get(surprise.explanation_difficulty, 0.5)

        reproducibility_score = {
            ReproducibilityStatus.REPRODUCIBLE: 1.0,
            ReproducibilityStatus.PARTIALLY_REPRODUCIBLE: 0.7,
            ReproducibilityStatus.REQUIRES_CONDITIONS: 0.5,
            ReproducibilityStatus.NOT_REPRODUCIBLE: 0.2,
            ReproducibilityStatus.NOT_ATTEMPTED: 0.0
        }.get(surprise.reproducibility, 0.5)

        impact_score = 1.0 if surprise.requires_model_update else 0.5

        # Combined emergence score (weighted average)
        emergence_score = (
            0.3 * novelty_score +
            0.3 * unexplainability_score +
            0.2 * reproducibility_score +
            0.2 * impact_score
        )

        # Generate tags
        tags = [
            surprise.category.value,
            surprise.surprise_level.value,
            surprise.explanation_difficulty.value
        ]
        if surprise.requires_model_update:
            tags.append("model_update_required")
        if surprise.externally_verified:
            tags.append("externally_verified")

        return TaxonomyEntry(
            entry_id=str(uuid.uuid4()),
            surprise_id=surprise.surprise_id,
            category=surprise.category,
            surprise_level=surprise.surprise_level,
            explanation_difficulty=surprise.explanation_difficulty,
            novelty_score=novelty_score,
            impact_score=impact_score,
            reproducibility_score=reproducibility_score,
            unexplainability_score=unexplainability_score,
            emergence_score=emergence_score,
            tags=tags
        )

    def record_reproduction_attempt(self, attempt: ReproductionAttempt) -> str:
        """Record an attempt to reproduce a surprising behavior."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO reproduction_attempts (
                attempt_id, surprise_id, conditions, trigger_used,
                successful, observed_behavior, match_with_original,
                witnessed_by, attempted_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            attempt.attempt_id,
            attempt.surprise_id,
            json.dumps(attempt.conditions),
            attempt.trigger_used,
            attempt.successful,
            attempt.observed_behavior,
            attempt.match_with_original,
            attempt.witnessed_by,
            attempt.attempted_at,
            attempt.notes
        ))

        # Update reproducibility status
        self._update_reproducibility(attempt.surprise_id)

        conn.commit()
        conn.close()

        return attempt.attempt_id

    def _update_reproducibility(self, surprise_id: str):
        """Update reproducibility status based on attempts."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT successful, match_with_original
            FROM reproduction_attempts
            WHERE surprise_id = ?
        """, (surprise_id,))

        attempts = cursor.fetchall()

        if not attempts:
            status = ReproducibilityStatus.NOT_ATTEMPTED
        else:
            successful = sum(1 for a in attempts if a[0])
            total = len(attempts)
            avg_match = sum(a[1] for a in attempts) / total

            if successful == total and avg_match > 0.8:
                status = ReproducibilityStatus.REPRODUCIBLE
            elif successful > 0:
                status = ReproducibilityStatus.PARTIALLY_REPRODUCIBLE
            else:
                status = ReproducibilityStatus.NOT_REPRODUCIBLE

        cursor.execute("""
            UPDATE surprise_behaviors
            SET reproducibility = ?
            WHERE surprise_id = ?
        """, (status.value, surprise_id))

        conn.commit()
        conn.close()

    def add_witness(self, surprise_id: str, witness: SurpriseWitness):
        """Add a witness to a surprise documentation."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO witnesses (
                witness_id, surprise_id, name, role, affiliation,
                surprise_level, explanation_difficulty, witnessed_at,
                reported_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            witness.witness_id,
            surprise_id,
            witness.name,
            witness.role,
            witness.affiliation,
            witness.surprise_level.value,
            witness.explanation_difficulty.value,
            witness.witnessed_at,
            witness.reported_at,
            witness.notes
        ))

        conn.commit()
        conn.close()

    def get_taxonomy(self) -> List[Dict[str, Any]]:
        """Get the full surprise taxonomy."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT s.*, t.emergence_score, t.tags
            FROM surprise_behaviors s
            LEFT JOIN taxonomy_entries t ON s.surprise_id = t.surprise_id
            ORDER BY t.emergence_score DESC
        """)

        taxonomy = []
        for row in cursor.fetchall():
            taxonomy.append({
                "surprise_id": row[0],
                "category": row[1],
                "title": row[2],
                "surprise_level": row[8],
                "explanation_difficulty": row[9],
                "reproducibility": row[10],
                "externally_verified": bool(row[20]),
                "emergence_score": row[25] if row[25] else 0.0,
                "tags": json.loads(row[26]) if row[26] else []
            })

        conn.close()
        return taxonomy

    def get_agi_validation_status(self) -> Dict[str, Any]:
        """
        Check if surprise taxonomy requirements are met for AGI claims.

        Requirements (per LLM Council):
        1. Documented behaviors that genuinely surprised creators
        2. Instances not easily explainable post-hoc
        3. Behaviors requiring updating model of system capabilities
        4. Reproducible triggers for unexpected behaviors
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Get all surprises
        cursor.execute("SELECT * FROM surprise_behaviors")
        surprises = cursor.fetchall()

        # Get taxonomy entries
        cursor.execute("SELECT * FROM taxonomy_entries")
        entries = cursor.fetchall()

        conn.close()

        if not surprises:
            return {
                "agi_validation_status": "NOT_STARTED",
                "message": "No surprising behaviors have been documented",
                "requirements_met": {
                    "genuine_surprises_documented": False,
                    "difficult_to_explain": False,
                    "requires_model_update": False,
                    "reproducible_triggers": False,
                    "externally_verified": False
                },
                "ready_for_agi_claim": False
            }

        # Analyze requirements
        genuine_surprises = any(
            row[8] in ["significant", "profound"]  # surprise_level
            for row in surprises
        )

        difficult_to_explain = any(
            row[9] in ["difficult", "inexplicable"]  # explanation_difficulty
            for row in surprises
        )

        requires_model_update = any(
            bool(row[18])  # requires_model_update
            for row in surprises
        )

        reproducible = any(
            row[10] in ["reproducible", "partially_reproducible"]  # reproducibility
            for row in surprises
        )

        externally_verified = any(
            bool(row[20])  # externally_verified
            for row in surprises
        )

        # Calculate average emergence score
        avg_emergence = sum(e[9] for e in entries) / len(entries) if entries else 0.0

        requirements = {
            "genuine_surprises_documented": genuine_surprises,
            "difficult_to_explain": difficult_to_explain,
            "requires_model_update": requires_model_update,
            "reproducible_triggers": reproducible,
            "externally_verified": externally_verified
        }

        all_met = all(requirements.values())

        return {
            "agi_validation_status": "PASSED" if all_met else "NOT_PASSED",
            "message": "All surprise requirements met" if all_met else "Missing requirements",
            "requirements_met": requirements,
            "ready_for_agi_claim": all_met,
            "total_surprises": len(surprises),
            "average_emergence_score": avg_emergence,
            "surprise_distribution": {
                "by_level": self._count_by_field(surprises, 8),
                "by_category": self._count_by_field(surprises, 1)
            }
        }

    def _count_by_field(self, rows: List[tuple], field_idx: int) -> Dict[str, int]:
        """Count occurrences by field value."""
        counts = {}
        for row in rows:
            val = row[field_idx]
            counts[val] = counts.get(val, 0) + 1
        return counts


def create_example_surprise() -> SurpriseBehavior:
    """
    Create example surprise documentation.

    WARNING: This is an INTERNAL example and does NOT count toward AGI claims.
    """
    witness = SurpriseWitness(
        witness_id=str(uuid.uuid4()),
        name="System Developer",
        role="creator",
        affiliation="Internal",
        surprise_level=SurpriseLevel.MODERATE,
        explanation_difficulty=ExplanationDifficulty.MODERATE,
        witnessed_at=datetime.now().isoformat(),
        reported_at=datetime.now().isoformat(),
        notes="Noticed during routine testing"
    )

    return SurpriseBehavior(
        surprise_id=str(uuid.uuid4()),
        category=SurpriseCategory.STRATEGY_INVENTION,
        title="Unexpected Optimization Approach",
        description="System used an unconventional approach to optimize memory usage",
        context="During memory consolidation, system was given a straightforward task",
        observed_behavior="System restructured data in a way not specified in design",
        expected_behavior="Follow standard consolidation algorithm",
        deviation_description="Created hierarchical clustering not in original algorithm",
        surprise_level=SurpriseLevel.MODERATE,
        explanation_difficulty=ExplanationDifficulty.MODERATE,
        reproducibility=ReproducibilityStatus.NOT_ATTEMPTED,
        trigger_conditions={
            "task": "memory_consolidation",
            "data_size": "large",
            "time_pressure": "none"
        },
        reproduction_instructions="Run consolidation on large dataset without time constraints",
        witnesses=[witness],
        first_observed=datetime.now().isoformat(),
        first_observer="System Developer",
        post_hoc_explanation="May be emergent from training on optimization examples",
        explanation_confidence=0.4,
        requires_model_update=False,
        model_update_description="",
        externally_verified=False  # NOT valid for AGI claims
    )


async def main():
    """Demo the surprise taxonomy framework."""
    print("Surprise Taxonomy Documentation Framework - Demo")
    print("=" * 50)
    print()
    print("WARNING: Internal examples DO NOT count toward AGI claims.")
    print("AGI validation requires externally verified surprising behaviors.")
    print()

    framework = SurpriseTaxonomyFramework()

    # Create example surprise
    surprise = create_example_surprise()
    framework.document_surprise(surprise)
    print(f"Documented surprise: {surprise.title}")
    print()

    # Get taxonomy
    taxonomy = framework.get_taxonomy()
    print(f"Taxonomy has {len(taxonomy)} entries")
    print()

    # Check validation status
    status = framework.get_agi_validation_status()
    print("AGI Validation Status:")
    print(f"  Status: {status['agi_validation_status']}")
    print(f"  Ready for AGI claim: {status['ready_for_agi_claim']}")
    print(f"  Requirements met: {status['requirements_met']}")


if __name__ == "__main__":
    asyncio.run(main())

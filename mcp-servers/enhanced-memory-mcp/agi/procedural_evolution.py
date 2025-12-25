"""
Procedural Evolution Module - Phase 3 Holographic Memory

Implements evolutionary skill/procedure optimization:
- Skill Variants: Multiple versions of procedures for A/B testing
- Fitness Tracking: Statistical performance tracking per variant
- Context-Aware Selection: Activation field influences variant selection
- Mutation Engine: Generate variations of successful procedures
- Evolution Cycles: Periodic selection and optimization

Key Concept:
In the holographic memory model, procedures don't just execute - they evolve.
The system automatically tests variations, tracks success rates, and
promotes high-performing variants while pruning poor performers.
"""

import sqlite3
import json
import math
import random
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("procedural-evolution")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


@dataclass
class SkillVariant:
    """A variant of a skill with its own procedure steps and fitness score."""
    variant_id: int
    skill_name: str
    variant_tag: str  # e.g., "v1", "mutation_a", "optimized"
    procedure_steps: List[str]
    preconditions: List[str]
    success_criteria: List[str]

    # Fitness tracking
    execution_count: int = 0
    success_count: int = 0
    total_score: float = 0.0

    # Statistical tracking
    scores: List[float] = field(default_factory=list)

    # Metadata
    parent_variant_id: Optional[int] = None
    mutation_type: Optional[str] = None  # "original", "reorder", "simplify", "elaborate"
    created_at: str = ""
    context_affinity: Dict[str, float] = field(default_factory=dict)  # context → success_rate

    @property
    def fitness_score(self) -> float:
        """Calculate fitness score (mean success rate with confidence adjustment)."""
        if self.execution_count == 0:
            return 0.5  # Prior (uncertainty)

        mean_score = self.total_score / self.execution_count

        # Apply confidence adjustment (Thompson sampling-inspired)
        # Lower executions = more uncertainty = pull toward 0.5
        confidence = min(1.0, self.execution_count / 20)  # Full confidence at 20+ executions
        return mean_score * confidence + 0.5 * (1 - confidence)

    @property
    def success_rate(self) -> float:
        """Simple success rate."""
        if self.execution_count == 0:
            return 0.0
        return self.success_count / self.execution_count

    def confidence_interval(self, z: float = 1.96) -> Tuple[float, float]:
        """Calculate confidence interval for success rate (Wilson score interval)."""
        n = self.execution_count
        if n == 0:
            return (0.0, 1.0)

        p = self.success_rate

        # Wilson score interval
        denominator = 1 + z*z/n
        center = (p + z*z/(2*n)) / denominator
        spread = z * math.sqrt((p*(1-p) + z*z/(4*n))/n) / denominator

        return (max(0, center - spread), min(1, center + spread))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "variant_id": self.variant_id,
            "skill_name": self.skill_name,
            "variant_tag": self.variant_tag,
            "procedure_steps": self.procedure_steps,
            "preconditions": self.preconditions,
            "success_criteria": self.success_criteria,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "total_score": self.total_score,
            "fitness_score": self.fitness_score,
            "success_rate": self.success_rate,
            "confidence_interval": self.confidence_interval(),
            "parent_variant_id": self.parent_variant_id,
            "mutation_type": self.mutation_type,
            "created_at": self.created_at,
            "context_affinity": self.context_affinity
        }


class ProceduralEvolution:
    """
    Manages evolutionary optimization of procedures/skills.

    Phase 3 of holographic memory - procedures automatically evolve
    based on execution outcomes and context.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._init_database()
        logger.info("ProceduralEvolution initialized (singleton)")

    def _init_database(self):
        """Initialize database tables for procedural evolution."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Skill variants table - stores multiple versions of each skill
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skill_variants (
                variant_id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT NOT NULL,
                variant_tag TEXT NOT NULL,
                procedure_steps TEXT NOT NULL,
                preconditions TEXT DEFAULT '[]',
                success_criteria TEXT DEFAULT '[]',

                -- Fitness tracking
                execution_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                total_score REAL DEFAULT 0.0,

                -- Lineage
                parent_variant_id INTEGER,
                mutation_type TEXT DEFAULT 'original',

                -- Context affinity (JSON: context_key -> success_rate)
                context_affinity TEXT DEFAULT '{}',

                -- Metadata
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_executed_at TIMESTAMP,

                UNIQUE(skill_name, variant_tag),
                FOREIGN KEY (parent_variant_id) REFERENCES skill_variants(variant_id)
            )
        ''')

        # Variant executions - detailed execution history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS variant_executions (
                execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
                variant_id INTEGER NOT NULL,

                -- Execution details
                context_key TEXT,
                success_score REAL NOT NULL,
                execution_time_ms INTEGER,

                -- Outcome
                outcome TEXT,
                error_message TEXT,

                -- Timestamps
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (variant_id) REFERENCES skill_variants(variant_id)
            )
        ''')

        # Evolution cycles - tracks evolution events
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evolution_cycles (
                cycle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT NOT NULL,

                -- Cycle details
                cycle_type TEXT NOT NULL,  -- 'selection', 'mutation', 'pruning'
                variants_before INTEGER,
                variants_after INTEGER,

                -- What happened
                mutations_created INTEGER DEFAULT 0,
                variants_pruned INTEGER DEFAULT 0,
                best_variant_id INTEGER,

                -- Metadata
                cycle_data TEXT,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_variants_skill ON skill_variants(skill_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_variants_active ON skill_variants(is_active)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_variant_exec ON variant_executions(variant_id)')

        conn.commit()
        conn.close()

        logger.info("Procedural evolution tables initialized")

    def create_skill_variant(
        self,
        skill_name: str,
        variant_tag: str,
        procedure_steps: List[str],
        preconditions: Optional[List[str]] = None,
        success_criteria: Optional[List[str]] = None,
        parent_variant_id: Optional[int] = None,
        mutation_type: str = "original"
    ) -> int:
        """
        Create a new skill variant.

        Args:
            skill_name: Name of the skill
            variant_tag: Tag for this variant (e.g., "v1", "optimized")
            procedure_steps: List of procedure steps
            preconditions: Optional preconditions
            success_criteria: Optional success criteria
            parent_variant_id: If this is a mutation, the parent variant
            mutation_type: Type of mutation ("original", "reorder", "simplify", "elaborate")

        Returns:
            variant_id
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        try:
            cursor.execute(
                '''
                INSERT INTO skill_variants (
                    skill_name, variant_tag, procedure_steps,
                    preconditions, success_criteria,
                    parent_variant_id, mutation_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    skill_name,
                    variant_tag,
                    json.dumps(procedure_steps),
                    json.dumps(preconditions or []),
                    json.dumps(success_criteria or []),
                    parent_variant_id,
                    mutation_type
                )
            )

            variant_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Created variant {variant_id}: {skill_name}/{variant_tag} ({mutation_type})")
            return variant_id

        except sqlite3.IntegrityError:
            # Variant already exists, update it
            cursor.execute(
                '''
                UPDATE skill_variants
                SET procedure_steps = ?,
                    preconditions = ?,
                    success_criteria = ?,
                    parent_variant_id = ?,
                    mutation_type = ?
                WHERE skill_name = ? AND variant_tag = ?
                ''',
                (
                    json.dumps(procedure_steps),
                    json.dumps(preconditions or []),
                    json.dumps(success_criteria or []),
                    parent_variant_id,
                    mutation_type,
                    skill_name,
                    variant_tag
                )
            )

            cursor.execute(
                'SELECT variant_id FROM skill_variants WHERE skill_name = ? AND variant_tag = ?',
                (skill_name, variant_tag)
            )
            variant_id = cursor.fetchone()[0]
            conn.commit()

            logger.info(f"Updated variant {variant_id}: {skill_name}/{variant_tag}")
            return variant_id
        finally:
            conn.close()

    def record_execution(
        self,
        variant_id: int,
        success_score: float,
        context_key: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        outcome: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """
        Record a variant execution and update fitness.

        Args:
            variant_id: Which variant was executed
            success_score: 0.0 to 1.0 success score
            context_key: Optional context identifier
            execution_time_ms: Execution time in milliseconds
            outcome: Description of outcome
            error_message: Error if failed
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Record execution
        cursor.execute(
            '''
            INSERT INTO variant_executions (
                variant_id, context_key, success_score,
                execution_time_ms, outcome, error_message
            ) VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (variant_id, context_key, success_score, execution_time_ms, outcome, error_message)
        )

        # Update variant fitness
        is_success = 1 if success_score >= 0.7 else 0
        cursor.execute(
            '''
            UPDATE skill_variants
            SET execution_count = execution_count + 1,
                success_count = success_count + ?,
                total_score = total_score + ?,
                last_executed_at = CURRENT_TIMESTAMP
            WHERE variant_id = ?
            ''',
            (is_success, success_score, variant_id)
        )

        # Update context affinity if context provided
        if context_key:
            cursor.execute(
                'SELECT context_affinity FROM skill_variants WHERE variant_id = ?',
                (variant_id,)
            )
            row = cursor.fetchone()
            if row:
                affinity = json.loads(row[0]) if row[0] else {}

                # Exponential moving average for context affinity
                alpha = 0.3  # Learning rate
                old_value = affinity.get(context_key, 0.5)
                new_value = old_value * (1 - alpha) + success_score * alpha
                affinity[context_key] = new_value

                cursor.execute(
                    'UPDATE skill_variants SET context_affinity = ? WHERE variant_id = ?',
                    (json.dumps(affinity), variant_id)
                )

        conn.commit()
        conn.close()

        logger.debug(f"Recorded execution for variant {variant_id}: score={success_score}")

    def get_variants(
        self,
        skill_name: str,
        active_only: bool = True
    ) -> List[SkillVariant]:
        """Get all variants for a skill."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = 'SELECT * FROM skill_variants WHERE skill_name = ?'
        if active_only:
            query += ' AND is_active = 1'
        query += ' ORDER BY execution_count DESC'

        cursor.execute(query, (skill_name,))
        rows = cursor.fetchall()
        conn.close()

        variants = []
        for row in rows:
            variant = SkillVariant(
                variant_id=row['variant_id'],
                skill_name=row['skill_name'],
                variant_tag=row['variant_tag'],
                procedure_steps=json.loads(row['procedure_steps']),
                preconditions=json.loads(row['preconditions']) if row['preconditions'] else [],
                success_criteria=json.loads(row['success_criteria']) if row['success_criteria'] else [],
                execution_count=row['execution_count'],
                success_count=row['success_count'],
                total_score=row['total_score'],
                parent_variant_id=row['parent_variant_id'],
                mutation_type=row['mutation_type'],
                created_at=row['created_at'],
                context_affinity=json.loads(row['context_affinity']) if row['context_affinity'] else {}
            )
            variants.append(variant)

        return variants

    def select_best_variant(
        self,
        skill_name: str,
        context_key: Optional[str] = None,
        exploration_rate: float = 0.1
    ) -> Optional[SkillVariant]:
        """
        Select the best variant for execution using Thompson Sampling.

        Integrates with activation field for context-aware selection.

        Args:
            skill_name: Name of the skill
            context_key: Optional context for context-aware selection
            exploration_rate: Probability of exploring non-best variant

        Returns:
            Best variant or None if no variants exist
        """
        variants = self.get_variants(skill_name, active_only=True)

        if not variants:
            return None

        if len(variants) == 1:
            return variants[0]

        # Exploration: sometimes pick a random variant
        if random.random() < exploration_rate:
            return random.choice(variants)

        # Context-aware selection
        if context_key:
            # Boost variants with good context affinity
            scored_variants = []
            for v in variants:
                base_score = v.fitness_score
                context_boost = v.context_affinity.get(context_key, 0.5)
                combined_score = base_score * 0.7 + context_boost * 0.3
                scored_variants.append((v, combined_score))

            scored_variants.sort(key=lambda x: x[1], reverse=True)
            return scored_variants[0][0]

        # Standard selection: best fitness score
        return max(variants, key=lambda v: v.fitness_score)

    def mutate_variant(
        self,
        variant: SkillVariant,
        mutation_type: str = "auto"
    ) -> Optional[int]:
        """
        Create a mutated variant from a successful variant.

        Mutation types:
        - "reorder": Change order of steps
        - "simplify": Remove a step
        - "elaborate": Add detail to a step
        - "combine": Merge two steps
        - "auto": Randomly select mutation type

        Returns:
            New variant_id or None if mutation failed
        """
        if mutation_type == "auto":
            mutation_type = random.choice(["reorder", "simplify", "elaborate"])

        steps = variant.procedure_steps.copy()

        if mutation_type == "reorder" and len(steps) > 2:
            # Swap two adjacent steps
            i = random.randint(0, len(steps) - 2)
            steps[i], steps[i + 1] = steps[i + 1], steps[i]

        elif mutation_type == "simplify" and len(steps) > 2:
            # Remove a non-critical step (not first or last)
            i = random.randint(1, len(steps) - 2)
            steps.pop(i)

        elif mutation_type == "elaborate":
            # Add detail to a random step
            i = random.randint(0, len(steps) - 1)
            steps[i] = f"{steps[i]} (with verification)"

        elif mutation_type == "combine" and len(steps) > 2:
            # Combine two adjacent steps
            i = random.randint(0, len(steps) - 2)
            combined = f"{steps[i]} then {steps[i+1]}"
            steps[i] = combined
            steps.pop(i + 1)
        else:
            # Fallback: minor text change
            i = random.randint(0, len(steps) - 1)
            steps[i] = f"{steps[i]} [optimized]"

        # Generate new variant tag
        existing_variants = self.get_variants(variant.skill_name, active_only=False)
        max_mutation_num = 0
        for v in existing_variants:
            if v.variant_tag.startswith(f"mut_{mutation_type}_"):
                try:
                    num = int(v.variant_tag.split("_")[-1])
                    max_mutation_num = max(max_mutation_num, num)
                except:
                    pass

        new_tag = f"mut_{mutation_type}_{max_mutation_num + 1}"

        return self.create_skill_variant(
            skill_name=variant.skill_name,
            variant_tag=new_tag,
            procedure_steps=steps,
            preconditions=variant.preconditions,
            success_criteria=variant.success_criteria,
            parent_variant_id=variant.variant_id,
            mutation_type=mutation_type
        )

    def run_evolution_cycle(
        self,
        skill_name: str,
        min_executions: int = 5,
        prune_threshold: float = 0.3,
        mutate_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Run an evolution cycle for a skill.

        1. Prune poor-performing variants (below prune_threshold)
        2. Mutate successful variants (above mutate_threshold)
        3. Keep balanced variants active

        Args:
            skill_name: Skill to evolve
            min_executions: Minimum executions before pruning
            prune_threshold: Fitness below this gets pruned
            mutate_threshold: Fitness above this gets mutated

        Returns:
            Evolution cycle summary
        """
        variants = self.get_variants(skill_name, active_only=True)

        if not variants:
            return {"status": "no_variants", "skill_name": skill_name}

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        variants_pruned = 0
        mutations_created = 0
        best_variant = None
        best_fitness = 0.0

        for variant in variants:
            # Find best
            if variant.fitness_score > best_fitness:
                best_fitness = variant.fitness_score
                best_variant = variant

            # Skip if not enough executions
            if variant.execution_count < min_executions:
                continue

            # Prune poor performers (but keep at least one variant)
            if variant.fitness_score < prune_threshold and len(variants) > 1:
                cursor.execute(
                    'UPDATE skill_variants SET is_active = 0 WHERE variant_id = ?',
                    (variant.variant_id,)
                )
                variants_pruned += 1
                logger.info(f"Pruned variant {variant.variant_id} (fitness={variant.fitness_score:.2f})")

            # Mutate successful variants
            elif variant.fitness_score > mutate_threshold:
                new_id = self.mutate_variant(variant)
                if new_id:
                    mutations_created += 1
                    logger.info(f"Created mutation {new_id} from variant {variant.variant_id}")

        # Record evolution cycle
        cursor.execute(
            '''
            INSERT INTO evolution_cycles (
                skill_name, cycle_type,
                variants_before, variants_after,
                mutations_created, variants_pruned,
                best_variant_id
            ) VALUES (?, 'evolution', ?, ?, ?, ?, ?)
            ''',
            (
                skill_name,
                len(variants),
                len(variants) - variants_pruned + mutations_created,
                mutations_created,
                variants_pruned,
                best_variant.variant_id if best_variant else None
            )
        )

        conn.commit()
        conn.close()

        result = {
            "status": "completed",
            "skill_name": skill_name,
            "variants_before": len(variants),
            "variants_after": len(variants) - variants_pruned + mutations_created,
            "mutations_created": mutations_created,
            "variants_pruned": variants_pruned,
            "best_variant": best_variant.to_dict() if best_variant else None
        }

        logger.info(f"Evolution cycle for {skill_name}: {variants_pruned} pruned, {mutations_created} mutations")

        return result

    def get_evolution_history(
        self,
        skill_name: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get evolution cycle history."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if skill_name:
            cursor.execute(
                '''
                SELECT * FROM evolution_cycles
                WHERE skill_name = ?
                ORDER BY executed_at DESC
                LIMIT ?
                ''',
                (skill_name, limit)
            )
        else:
            cursor.execute(
                '''
                SELECT * FROM evolution_cycles
                ORDER BY executed_at DESC
                LIMIT ?
                ''',
                (limit,)
            )

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results

    def get_skill_fitness_summary(self, skill_name: str) -> Dict[str, Any]:
        """Get fitness summary for a skill's variants."""
        variants = self.get_variants(skill_name, active_only=True)

        if not variants:
            return {
                "skill_name": skill_name,
                "variant_count": 0,
                "has_variants": False
            }

        best = max(variants, key=lambda v: v.fitness_score)
        worst = min(variants, key=lambda v: v.fitness_score)

        total_executions = sum(v.execution_count for v in variants)
        avg_fitness = sum(v.fitness_score for v in variants) / len(variants)

        return {
            "skill_name": skill_name,
            "has_variants": True,
            "variant_count": len(variants),
            "total_executions": total_executions,
            "average_fitness": avg_fitness,
            "best_variant": {
                "variant_id": best.variant_id,
                "variant_tag": best.variant_tag,
                "fitness_score": best.fitness_score,
                "success_rate": best.success_rate,
                "execution_count": best.execution_count
            },
            "worst_variant": {
                "variant_id": worst.variant_id,
                "variant_tag": worst.variant_tag,
                "fitness_score": worst.fitness_score,
                "success_rate": worst.success_rate,
                "execution_count": worst.execution_count
            },
            "all_variants": [v.to_dict() for v in variants]
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get overall procedural evolution statistics."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Total variants
        cursor.execute('SELECT COUNT(*) FROM skill_variants WHERE is_active = 1')
        active_variants = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM skill_variants')
        total_variants = cursor.fetchone()[0]

        # Unique skills
        cursor.execute('SELECT COUNT(DISTINCT skill_name) FROM skill_variants WHERE is_active = 1')
        unique_skills = cursor.fetchone()[0]

        # Total executions
        cursor.execute('SELECT COUNT(*) FROM variant_executions')
        total_executions = cursor.fetchone()[0]

        # Average fitness
        cursor.execute(
            '''
            SELECT AVG(total_score / NULLIF(execution_count, 0))
            FROM skill_variants
            WHERE is_active = 1 AND execution_count > 0
            '''
        )
        avg_fitness = cursor.fetchone()[0] or 0.0

        # Evolution cycles
        cursor.execute('SELECT COUNT(*) FROM evolution_cycles')
        evolution_cycles = cursor.fetchone()[0]

        cursor.execute('SELECT SUM(mutations_created), SUM(variants_pruned) FROM evolution_cycles')
        row = cursor.fetchone()
        total_mutations = row[0] or 0
        total_pruned = row[1] or 0

        conn.close()

        return {
            "active_variants": active_variants,
            "total_variants": total_variants,
            "unique_skills": unique_skills,
            "total_executions": total_executions,
            "average_fitness": avg_fitness,
            "evolution_cycles": evolution_cycles,
            "total_mutations_created": total_mutations,
            "total_variants_pruned": total_pruned
        }


# Singleton accessor
def get_procedural_evolution() -> ProceduralEvolution:
    """Get the singleton ProceduralEvolution instance."""
    return ProceduralEvolution()


# Convenience functions for hook integration
def select_skill_variant(
    skill_name: str,
    context_key: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Select the best variant for a skill.

    For use in hooks and activation field integration.
    """
    evolution = get_procedural_evolution()
    variant = evolution.select_best_variant(skill_name, context_key)
    return variant.to_dict() if variant else None


def record_skill_outcome(
    skill_name: str,
    variant_tag: str,
    success_score: float,
    context_key: Optional[str] = None
):
    """
    Record a skill execution outcome.

    For use in hooks.
    """
    evolution = get_procedural_evolution()
    variants = evolution.get_variants(skill_name)

    for v in variants:
        if v.variant_tag == variant_tag:
            evolution.record_execution(v.variant_id, success_score, context_key)
            return

    logger.warning(f"Variant {skill_name}/{variant_tag} not found")

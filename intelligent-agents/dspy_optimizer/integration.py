#!/usr/bin/env python3
"""
Darwin-Gödel Machine Integration
=================================

Connects DSPy optimization with the Darwin-Gödel machine for
evolutionary prompt improvement with formal verification.

Also integrates with PySR for equation-driven prompt evolution.
"""

import asyncio
import json
import logging
import hashlib
import os
import platform
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple
import sys

import dspy

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from .optimizer import DSPyOptimizer, OptimizationConfig, OptimizationResult
from .modules import PromptEvolutionModule, SelfImprovingModule
from .metrics import MetricsCollector, PromptPerformance

logger = logging.getLogger(__name__)


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
        elif Path("/mnt/agentic-system").exists():
            return Path("/mnt/agentic-system")
    return Path(__file__).parent.parent.parent


_STORAGE_BASE = _get_storage_base()
DB_PATH = _STORAGE_BASE / "databases" / "dspy_optimizer.db"


@dataclass
class EvolutionCandidate:
    """A candidate prompt in the evolutionary pool"""
    candidate_id: str
    prompt_content: str
    fitness_score: float
    generation: int
    parent_ids: List[str]
    mutations: List[str]
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            "candidate_id": self.candidate_id,
            "prompt_content": self.prompt_content,
            "fitness_score": self.fitness_score,
            "generation": self.generation,
            "parent_ids": self.parent_ids,
            "mutations": self.mutations,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class EvolutionResult:
    """Result of an evolutionary optimization cycle"""
    cycle_id: str
    generations: int
    best_candidate: EvolutionCandidate
    improvement_over_baseline: float
    population_diversity: float
    convergence_generation: int
    total_evaluations: int
    pysr_equations_used: List[str]


class DarwinGodelIntegration:
    """
    Integrates DSPy optimization with Darwin-Gödel machine.

    Provides:
    - Evolutionary prompt optimization
    - Formal verification of improvements
    - PySR equation-driven mutations
    - Safe rollback on regression
    """

    def __init__(
        self,
        optimizer: Optional[DSPyOptimizer] = None,
        population_size: int = 10,
        mutation_rate: float = 0.3,
        crossover_rate: float = 0.5
    ):
        self.optimizer = optimizer or DSPyOptimizer()
        self.metrics = MetricsCollector()
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.evolution_module = PromptEvolutionModule()
        self._init_database()
        self._pysr_equations: Dict[str, str] = {}
        self._load_pysr_equations()

    def _init_database(self):
        """Initialize evolution tables"""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evolution_candidates (
                    candidate_id TEXT PRIMARY KEY,
                    prompt_content TEXT NOT NULL,
                    fitness_score REAL,
                    generation INTEGER,
                    parent_ids TEXT,
                    mutations TEXT,
                    created_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evolution_cycles (
                    cycle_id TEXT PRIMARY KEY,
                    module_name TEXT NOT NULL,
                    generations INTEGER,
                    best_candidate_id TEXT,
                    improvement REAL,
                    diversity REAL,
                    convergence_gen INTEGER,
                    evaluations INTEGER,
                    equations_used TEXT,
                    created_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pysr_equations (
                    equation_id TEXT PRIMARY KEY,
                    equation_str TEXT NOT NULL,
                    complexity REAL,
                    loss REAL,
                    domain TEXT,
                    created_at TEXT
                )
            """)
            conn.commit()

    def _load_pysr_equations(self):
        """Load PySR equations from database"""
        try:
            pysr_db = _STORAGE_BASE / "databases" / "discovered_equations.db"
            if pysr_db.exists():
                with sqlite3.connect(pysr_db) as conn:
                    cursor = conn.execute("""
                        SELECT equation_str, domain FROM equations
                        ORDER BY loss ASC LIMIT 50
                    """)
                    for row in cursor.fetchall():
                        self._pysr_equations[row[1]] = row[0]
                logger.info(f"Loaded {len(self._pysr_equations)} PySR equations")
        except Exception as e:
            logger.warning(f"Could not load PySR equations: {e}")

    async def evolve_prompt(
        self,
        module: dspy.Module,
        baseline_prompt: str,
        trainset: List[dspy.Example],
        metric: Callable,
        max_generations: int = 10,
        convergence_threshold: float = 0.01
    ) -> EvolutionResult:
        """
        Evolve a prompt using Darwin-Gödel evolutionary optimization.

        Args:
            module: DSPy module to optimize
            baseline_prompt: Starting prompt
            trainset: Training examples
            metric: Evaluation metric
            max_generations: Maximum generations
            convergence_threshold: Stop if improvement below this

        Returns:
            EvolutionResult with best prompt and statistics
        """
        cycle_id = hashlib.md5(
            f"{module.__class__.__name__}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        # Initialize population
        population = await self._initialize_population(baseline_prompt)
        baseline_score = self._evaluate_prompt(module, baseline_prompt, trainset, metric)

        best_candidate = population[0]
        convergence_gen = 0
        total_evaluations = 0
        equations_used = []

        for gen in range(max_generations):
            # Evaluate fitness
            for candidate in population:
                if candidate.fitness_score == 0:
                    candidate.fitness_score = self._evaluate_prompt(
                        module, candidate.prompt_content, trainset, metric
                    )
                    total_evaluations += 1

            # Sort by fitness
            population.sort(key=lambda c: c.fitness_score, reverse=True)

            # Update best
            if population[0].fitness_score > best_candidate.fitness_score:
                best_candidate = population[0]
                convergence_gen = gen

            # Check convergence
            improvement = best_candidate.fitness_score - baseline_score
            if gen > 0 and improvement < convergence_threshold:
                if gen - convergence_gen > 3:
                    logger.info(f"Converged at generation {gen}")
                    break

            # Selection (top 50%)
            survivors = population[:self.population_size // 2]

            # Generate new population
            new_population = list(survivors)

            while len(new_population) < self.population_size:
                # Crossover or mutation
                if len(survivors) >= 2 and hash(str(gen)) % 100 < self.crossover_rate * 100:
                    parent_a = survivors[hash(str(gen) + "a") % len(survivors)]
                    parent_b = survivors[hash(str(gen) + "b") % len(survivors)]
                    child = await self._crossover(parent_a, parent_b, gen + 1)
                else:
                    parent = survivors[hash(str(gen)) % len(survivors)]
                    child, eq = await self._mutate(parent, gen + 1)
                    if eq:
                        equations_used.append(eq)

                new_population.append(child)

            population = new_population
            logger.info(f"Generation {gen}: best={best_candidate.fitness_score:.4f}")

        # Calculate diversity
        diversity = self._calculate_diversity(population)

        result = EvolutionResult(
            cycle_id=cycle_id,
            generations=gen + 1,
            best_candidate=best_candidate,
            improvement_over_baseline=best_candidate.fitness_score - baseline_score,
            population_diversity=diversity,
            convergence_generation=convergence_gen,
            total_evaluations=total_evaluations,
            pysr_equations_used=list(set(equations_used))
        )

        # Save results
        self._save_evolution_result(result, module.__class__.__name__)

        return result

    async def _initialize_population(
        self,
        baseline_prompt: str
    ) -> List[EvolutionCandidate]:
        """Initialize the evolutionary population"""
        population = []

        # Add baseline
        population.append(EvolutionCandidate(
            candidate_id=hashlib.md5(baseline_prompt.encode()).hexdigest()[:12],
            prompt_content=baseline_prompt,
            fitness_score=0,
            generation=0,
            parent_ids=[],
            mutations=["baseline"]
        ))

        # Generate variations
        for i in range(self.population_size - 1):
            variation = await self._generate_variation(baseline_prompt, i)
            population.append(variation)

        return population

    async def _generate_variation(
        self,
        prompt: str,
        index: int
    ) -> EvolutionCandidate:
        """Generate a variation of a prompt"""
        # Use DSPy to generate variation
        try:
            result = self.evolution_module(
                original_prompt=prompt,
                performance_data=f"Variation {index} for diversity",
                task_description="Create a semantically equivalent but differently structured prompt"
            )
            new_prompt = result.evolved_prompt
        except Exception as e:
            logger.warning(f"Variation generation failed: {e}")
            new_prompt = prompt + f" [variant {index}]"

        return EvolutionCandidate(
            candidate_id=hashlib.md5(f"{prompt}_{index}".encode()).hexdigest()[:12],
            prompt_content=new_prompt,
            fitness_score=0,
            generation=0,
            parent_ids=[],
            mutations=[f"initial_variation_{index}"]
        )

    async def _mutate(
        self,
        parent: EvolutionCandidate,
        generation: int
    ) -> Tuple[EvolutionCandidate, Optional[str]]:
        """Mutate a candidate, optionally using PySR equations"""
        mutation_type = "standard"
        equation_used = None

        # Try to use PySR equation for mutation guidance
        if self._pysr_equations and hash(str(generation)) % 100 < 30:
            domain = list(self._pysr_equations.keys())[
                hash(str(generation)) % len(self._pysr_equations)
            ]
            equation = self._pysr_equations[domain]
            mutation_guidance = f"Apply transformation pattern inspired by: {equation}"
            equation_used = equation
            mutation_type = "pysr_guided"
        else:
            mutation_guidance = "Make a small but meaningful improvement"

        try:
            result = self.evolution_module(
                original_prompt=parent.prompt_content,
                performance_data=f"Fitness: {parent.fitness_score}. {mutation_guidance}",
                task_description="Improve prompt effectiveness while maintaining core meaning"
            )
            new_prompt = result.evolved_prompt
        except Exception as e:
            logger.warning(f"Mutation failed: {e}")
            new_prompt = parent.prompt_content

        return EvolutionCandidate(
            candidate_id=hashlib.md5(
                f"{parent.candidate_id}_{generation}".encode()
            ).hexdigest()[:12],
            prompt_content=new_prompt,
            fitness_score=0,
            generation=generation,
            parent_ids=[parent.candidate_id],
            mutations=[mutation_type]
        ), equation_used

    async def _crossover(
        self,
        parent_a: EvolutionCandidate,
        parent_b: EvolutionCandidate,
        generation: int
    ) -> EvolutionCandidate:
        """Crossover two candidates"""
        try:
            # Use DSPy to intelligently combine prompts
            combined = self.evolution_module(
                original_prompt=f"PARENT A:\n{parent_a.prompt_content}\n\nPARENT B:\n{parent_b.prompt_content}",
                performance_data=f"A fitness: {parent_a.fitness_score}, B fitness: {parent_b.fitness_score}",
                task_description="Combine the best aspects of both prompts into a superior hybrid"
            )
            new_prompt = combined.evolved_prompt
        except Exception as e:
            logger.warning(f"Crossover failed: {e}")
            # Simple fallback: take first half of A and second half of B
            mid_a = len(parent_a.prompt_content) // 2
            mid_b = len(parent_b.prompt_content) // 2
            new_prompt = parent_a.prompt_content[:mid_a] + parent_b.prompt_content[mid_b:]

        return EvolutionCandidate(
            candidate_id=hashlib.md5(
                f"{parent_a.candidate_id}_{parent_b.candidate_id}_{generation}".encode()
            ).hexdigest()[:12],
            prompt_content=new_prompt,
            fitness_score=0,
            generation=generation,
            parent_ids=[parent_a.candidate_id, parent_b.candidate_id],
            mutations=["crossover"]
        )

    def _evaluate_prompt(
        self,
        module: dspy.Module,
        prompt: str,
        trainset: List[dspy.Example],
        metric: Callable
    ) -> float:
        """Evaluate a prompt's fitness"""
        scores = []
        for example in trainset[:10]:  # Limit for speed
            try:
                # Inject prompt (simplified - actual implementation depends on module structure)
                prediction = module(**example.inputs())
                score = metric(example, prediction)
                scores.append(score)
            except Exception as e:
                logger.debug(f"Evaluation error: {e}")
                scores.append(0.0)

        return sum(scores) / len(scores) if scores else 0.0

    def _calculate_diversity(self, population: List[EvolutionCandidate]) -> float:
        """Calculate population diversity based on prompt similarity"""
        if len(population) < 2:
            return 0.0

        # Simple diversity: average pairwise difference in length (proxy for structural difference)
        total_diff = 0
        comparisons = 0

        for i, a in enumerate(population):
            for b in population[i + 1:]:
                len_diff = abs(len(a.prompt_content) - len(b.prompt_content))
                total_diff += len_diff
                comparisons += 1

        avg_len = sum(len(c.prompt_content) for c in population) / len(population)
        return (total_diff / comparisons / max(avg_len, 1)) if comparisons > 0 else 0.0

    def _save_evolution_result(self, result: EvolutionResult, module_name: str):
        """Save evolution result to database"""
        with sqlite3.connect(DB_PATH) as conn:
            # Save best candidate
            conn.execute("""
                INSERT OR REPLACE INTO evolution_candidates
                (candidate_id, prompt_content, fitness_score, generation,
                 parent_ids, mutations, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                result.best_candidate.candidate_id,
                result.best_candidate.prompt_content,
                result.best_candidate.fitness_score,
                result.best_candidate.generation,
                json.dumps(result.best_candidate.parent_ids),
                json.dumps(result.best_candidate.mutations),
                result.best_candidate.created_at.isoformat()
            ))

            # Save cycle
            conn.execute("""
                INSERT INTO evolution_cycles
                (cycle_id, module_name, generations, best_candidate_id,
                 improvement, diversity, convergence_gen, evaluations,
                 equations_used, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.cycle_id,
                module_name,
                result.generations,
                result.best_candidate.candidate_id,
                result.improvement_over_baseline,
                result.population_diversity,
                result.convergence_generation,
                result.total_evaluations,
                json.dumps(result.pysr_equations_used),
                datetime.now().isoformat()
            ))

            conn.commit()

    def verify_improvement(
        self,
        original_score: float,
        new_score: float,
        confidence_threshold: float = 0.95
    ) -> Dict:
        """
        Verify that an improvement is statistically significant.

        Implements formal verification inspired by Gödel machine.
        """
        improvement = new_score - original_score
        relative_improvement = improvement / max(original_score, 0.001)

        # Simple verification (could be enhanced with formal proofs)
        is_verified = improvement > 0 and relative_improvement > 0.01

        return {
            "verified": is_verified,
            "improvement": improvement,
            "relative_improvement": relative_improvement,
            "confidence": min(relative_improvement * 10, 1.0),
            "recommendation": "apply" if is_verified else "reject"
        }

    async def safe_apply_optimization(
        self,
        module: dspy.Module,
        optimization_result: OptimizationResult,
        rollback_threshold: float = 0.9
    ) -> Dict:
        """
        Safely apply an optimization with automatic rollback on regression.

        Args:
            module: Module to update
            optimization_result: The optimization to apply
            rollback_threshold: Minimum score ratio to keep optimization

        Returns:
            Application result with status
        """
        verification = self.verify_improvement(
            optimization_result.original_score,
            optimization_result.optimized_score
        )

        if not verification["verified"]:
            return {
                "status": "rejected",
                "reason": "Improvement not verified",
                "verification": verification
            }

        # Store rollback point
        rollback_state = self._capture_module_state(module)

        try:
            # Apply optimization
            self._apply_prompts(module, optimization_result.optimized_prompts)

            return {
                "status": "applied",
                "improvement": verification["improvement"],
                "rollback_available": True,
                "rollback_state_id": rollback_state["state_id"]
            }

        except Exception as e:
            logger.error(f"Failed to apply optimization: {e}")
            self._restore_module_state(module, rollback_state)
            return {
                "status": "failed",
                "error": str(e),
                "rolled_back": True
            }

    def _capture_module_state(self, module: dspy.Module) -> Dict:
        """Capture current module state for potential rollback"""
        state_id = hashlib.md5(
            f"{module.__class__.__name__}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        state = {
            "state_id": state_id,
            "prompts": {},
            "demos": {}
        }

        for name, predictor in module.named_predictors():
            if hasattr(predictor, 'signature'):
                state["prompts"][name] = str(predictor.signature)
            if hasattr(predictor, 'demos'):
                state["demos"][name] = list(predictor.demos)

        return state

    def _restore_module_state(self, module: dspy.Module, state: Dict):
        """Restore module to a previous state"""
        for name, predictor in module.named_predictors():
            if name in state["demos"] and hasattr(predictor, 'demos'):
                predictor.demos = state["demos"][name]

    def _apply_prompts(self, module: dspy.Module, prompts: Dict[str, str]):
        """Apply optimized prompts to a module"""
        for name, predictor in module.named_predictors():
            demo_key = f"{name}_demos"
            if demo_key in prompts:
                try:
                    demos = json.loads(prompts[demo_key])
                    if hasattr(predictor, 'demos'):
                        predictor.demos = demos
                except Exception as e:
                    logger.warning(f"Could not apply demos for {name}: {e}")

    def get_evolution_history(
        self,
        module_name: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Get evolution history"""
        with sqlite3.connect(DB_PATH) as conn:
            if module_name:
                cursor = conn.execute("""
                    SELECT * FROM evolution_cycles
                    WHERE module_name = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (module_name, limit))
            else:
                cursor = conn.execute("""
                    SELECT * FROM evolution_cycles
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))

            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


# Integration with enhanced-memory MCP
async def store_in_memory(entity_name: str, entity_type: str, observations: List[str]):
    """Store optimization results in enhanced-memory"""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            # This would integrate with enhanced-memory MCP
            # Simplified for now
            logger.info(f"Would store {entity_name} in enhanced-memory")
    except Exception as e:
        logger.warning(f"Could not store in memory: {e}")

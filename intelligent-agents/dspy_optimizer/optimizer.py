#!/usr/bin/env python3
"""
DSPy Optimization Engine
========================

Main optimization engine for automatic prompt improvement using DSPy's
teleprompter optimizers (BootstrapFewShot, MIPRO, etc.)

Integrates with enhanced-memory for persistent storage of optimized prompts.
"""

import asyncio
import json
import logging
import hashlib
import os
import platform
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
import sqlite3

import dspy
from dspy.teleprompt import BootstrapFewShot, BootstrapFewShotWithRandomSearch
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logging.basicConfig(level=logging.INFO)
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

# Database path
DB_PATH = _STORAGE_BASE / "databases" / "dspy_optimizer.db"


class OptimizerType(Enum):
    """Available teleprompter optimizers"""
    BOOTSTRAP_FEWSHOT = "bootstrap_fewshot"
    BOOTSTRAP_RANDOM = "bootstrap_random_search"
    MIPRO = "mipro"
    COPRO = "copro"


@dataclass
class OptimizationConfig:
    """Configuration for optimization runs"""
    optimizer_type: OptimizerType = OptimizerType.BOOTSTRAP_FEWSHOT
    max_bootstrapped_demos: int = 4
    max_labeled_demos: int = 16
    max_rounds: int = 1
    num_candidate_programs: int = 10
    metric_threshold: float = 0.7
    temperature: float = 0.7
    max_tokens: int = 2048
    model_name: str = "claude-sonnet-4-20250514"
    save_optimized: bool = True


@dataclass
class OptimizationResult:
    """Result of an optimization run"""
    result_id: str
    module_name: str
    original_score: float
    optimized_score: float
    improvement_pct: float
    optimized_prompts: Dict[str, str]
    training_examples: int
    optimization_time: float
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            "result_id": self.result_id,
            "module_name": self.module_name,
            "original_score": self.original_score,
            "optimized_score": self.optimized_score,
            "improvement_pct": self.improvement_pct,
            "optimized_prompts": self.optimized_prompts,
            "training_examples": self.training_examples,
            "optimization_time": self.optimization_time,
            "timestamp": self.timestamp.isoformat()
        }


class DSPyOptimizer:
    """
    Main DSPy optimization engine for automatic prompt improvement.

    Supports multiple teleprompter optimizers and integrates with
    enhanced-memory for persistent storage.
    """

    def __init__(self, config: Optional[OptimizationConfig] = None):
        self.config = config or OptimizationConfig()
        self._init_database()
        self._setup_dspy()
        self.optimization_history: List[OptimizationResult] = []

    def _init_database(self):
        """Initialize SQLite database for storing optimization results"""
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS optimization_results (
                    result_id TEXT PRIMARY KEY,
                    module_name TEXT NOT NULL,
                    original_score REAL,
                    optimized_score REAL,
                    improvement_pct REAL,
                    optimized_prompts TEXT,
                    training_examples INTEGER,
                    optimization_time REAL,
                    timestamp TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prompt_versions (
                    version_id TEXT PRIMARY KEY,
                    module_name TEXT NOT NULL,
                    prompt_hash TEXT NOT NULL,
                    prompt_content TEXT NOT NULL,
                    score REAL,
                    created_at TEXT,
                    is_active INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ab_tests (
                    test_id TEXT PRIMARY KEY,
                    module_name TEXT NOT NULL,
                    variant_a_id TEXT NOT NULL,
                    variant_b_id TEXT NOT NULL,
                    variant_a_wins INTEGER DEFAULT 0,
                    variant_b_wins INTEGER DEFAULT 0,
                    total_trials INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'running',
                    created_at TEXT,
                    completed_at TEXT
                )
            """)
            conn.commit()

    def _setup_dspy(self):
        """Configure DSPy with the appropriate LM"""
        try:
            # Configure Anthropic as the LM
            lm = dspy.LM(
                model=f"anthropic/{self.config.model_name}",
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            dspy.configure(lm=lm)
            logger.info(f"DSPy configured with model: {self.config.model_name}")
        except Exception as e:
            logger.error(f"Failed to configure DSPy: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def optimize_module(
        self,
        module: dspy.Module,
        trainset: List[dspy.Example],
        metric: Callable[[dspy.Example, Any], float],
        valset: Optional[List[dspy.Example]] = None
    ) -> OptimizationResult:
        """
        Optimize a DSPy module using the configured teleprompter.

        Args:
            module: The DSPy module to optimize
            trainset: Training examples
            metric: Evaluation metric function
            valset: Optional validation set

        Returns:
            OptimizationResult with optimization details
        """
        import time
        start_time = time.time()

        # Evaluate original module
        original_score = self._evaluate_module(module, valset or trainset, metric)
        logger.info(f"Original module score: {original_score:.4f}")

        # Select optimizer
        optimizer = self._get_optimizer()

        # Run optimization
        logger.info(f"Running optimization with {self.config.optimizer_type.value}")
        optimized_module = optimizer.compile(
            module,
            trainset=trainset,
            valset=valset
        )

        # Evaluate optimized module
        optimized_score = self._evaluate_module(
            optimized_module,
            valset or trainset,
            metric
        )
        logger.info(f"Optimized module score: {optimized_score:.4f}")

        # Calculate improvement
        improvement_pct = ((optimized_score - original_score) / max(original_score, 0.001)) * 100

        # Extract optimized prompts
        optimized_prompts = self._extract_prompts(optimized_module)

        # Create result
        result_id = hashlib.md5(
            f"{module.__class__.__name__}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        result = OptimizationResult(
            result_id=result_id,
            module_name=module.__class__.__name__,
            original_score=original_score,
            optimized_score=optimized_score,
            improvement_pct=improvement_pct,
            optimized_prompts=optimized_prompts,
            training_examples=len(trainset),
            optimization_time=time.time() - start_time
        )

        # Save result
        if self.config.save_optimized:
            self._save_result(result)
            self._save_prompt_version(result)

        self.optimization_history.append(result)

        logger.info(f"Optimization complete. Improvement: {improvement_pct:.2f}%")
        return result

    def _get_optimizer(self):
        """Get the appropriate teleprompter optimizer"""
        if self.config.optimizer_type == OptimizerType.BOOTSTRAP_FEWSHOT:
            return BootstrapFewShot(
                max_bootstrapped_demos=self.config.max_bootstrapped_demos,
                max_labeled_demos=self.config.max_labeled_demos,
                max_rounds=self.config.max_rounds
            )
        elif self.config.optimizer_type == OptimizerType.BOOTSTRAP_RANDOM:
            return BootstrapFewShotWithRandomSearch(
                max_bootstrapped_demos=self.config.max_bootstrapped_demos,
                max_labeled_demos=self.config.max_labeled_demos,
                num_candidate_programs=self.config.num_candidate_programs
            )
        else:
            # Default to BootstrapFewShot
            return BootstrapFewShot(
                max_bootstrapped_demos=self.config.max_bootstrapped_demos
            )

    def _evaluate_module(
        self,
        module: dspy.Module,
        examples: List[dspy.Example],
        metric: Callable
    ) -> float:
        """Evaluate a module on a set of examples"""
        scores = []
        for example in examples:
            try:
                prediction = module(**example.inputs())
                score = metric(example, prediction)
                scores.append(score)
            except Exception as e:
                logger.warning(f"Evaluation error: {e}")
                scores.append(0.0)

        return sum(scores) / len(scores) if scores else 0.0

    def _extract_prompts(self, module: dspy.Module) -> Dict[str, str]:
        """Extract prompts from an optimized module"""
        prompts = {}

        # Extract from predictors
        for name, predictor in module.named_predictors():
            if hasattr(predictor, 'demos'):
                prompts[f"{name}_demos"] = json.dumps(
                    [str(d) for d in predictor.demos],
                    indent=2
                )
            if hasattr(predictor, 'signature'):
                prompts[f"{name}_signature"] = str(predictor.signature)

        return prompts

    def _save_result(self, result: OptimizationResult):
        """Save optimization result to database"""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO optimization_results
                (result_id, module_name, original_score, optimized_score,
                 improvement_pct, optimized_prompts, training_examples,
                 optimization_time, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.result_id,
                result.module_name,
                result.original_score,
                result.optimized_score,
                result.improvement_pct,
                json.dumps(result.optimized_prompts),
                result.training_examples,
                result.optimization_time,
                result.timestamp.isoformat()
            ))
            conn.commit()

    def _save_prompt_version(self, result: OptimizationResult):
        """Save optimized prompts as new versions"""
        with sqlite3.connect(DB_PATH) as conn:
            for prompt_name, prompt_content in result.optimized_prompts.items():
                version_id = hashlib.md5(
                    f"{prompt_name}_{prompt_content}".encode()
                ).hexdigest()[:12]
                prompt_hash = hashlib.md5(prompt_content.encode()).hexdigest()

                conn.execute("""
                    INSERT OR REPLACE INTO prompt_versions
                    (version_id, module_name, prompt_hash, prompt_content,
                     score, created_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                """, (
                    version_id,
                    result.module_name,
                    prompt_hash,
                    prompt_content,
                    result.optimized_score,
                    datetime.now().isoformat()
                ))
            conn.commit()

    def get_best_prompt(self, module_name: str) -> Optional[Dict]:
        """Get the best performing prompt for a module"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("""
                SELECT version_id, prompt_content, score
                FROM prompt_versions
                WHERE module_name = ?
                ORDER BY score DESC
                LIMIT 1
            """, (module_name,))
            row = cursor.fetchone()

            if row:
                return {
                    "version_id": row[0],
                    "prompt_content": row[1],
                    "score": row[2]
                }
        return None

    def create_ab_test(
        self,
        module_name: str,
        variant_a_id: str,
        variant_b_id: str
    ) -> str:
        """Create an A/B test between two prompt variants"""
        test_id = hashlib.md5(
            f"{module_name}_{variant_a_id}_{variant_b_id}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO ab_tests
                (test_id, module_name, variant_a_id, variant_b_id, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                test_id,
                module_name,
                variant_a_id,
                variant_b_id,
                datetime.now().isoformat()
            ))
            conn.commit()

        logger.info(f"Created A/B test {test_id} for {module_name}")
        return test_id

    def record_ab_result(self, test_id: str, winner: str):
        """Record the result of an A/B test trial"""
        with sqlite3.connect(DB_PATH) as conn:
            if winner == "a":
                conn.execute("""
                    UPDATE ab_tests
                    SET variant_a_wins = variant_a_wins + 1,
                        total_trials = total_trials + 1
                    WHERE test_id = ?
                """, (test_id,))
            elif winner == "b":
                conn.execute("""
                    UPDATE ab_tests
                    SET variant_b_wins = variant_b_wins + 1,
                        total_trials = total_trials + 1
                    WHERE test_id = ?
                """, (test_id,))
            conn.commit()

    def get_ab_test_results(self, test_id: str) -> Optional[Dict]:
        """Get current A/B test results"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("""
                SELECT module_name, variant_a_id, variant_b_id,
                       variant_a_wins, variant_b_wins, total_trials, status
                FROM ab_tests WHERE test_id = ?
            """, (test_id,))
            row = cursor.fetchone()

            if row:
                total = row[5] or 1
                return {
                    "test_id": test_id,
                    "module_name": row[0],
                    "variant_a": {
                        "id": row[1],
                        "wins": row[3],
                        "win_rate": row[3] / total
                    },
                    "variant_b": {
                        "id": row[2],
                        "wins": row[4],
                        "win_rate": row[4] / total
                    },
                    "total_trials": total,
                    "status": row[6],
                    "statistical_significance": self._calculate_significance(
                        row[3], row[4], total
                    )
                }
        return None

    def _calculate_significance(
        self,
        wins_a: int,
        wins_b: int,
        total: int
    ) -> float:
        """Calculate statistical significance of A/B test"""
        if total < 30:
            return 0.0  # Not enough samples

        import math
        p_a = wins_a / total
        p_b = wins_b / total
        p_pooled = (wins_a + wins_b) / (2 * total)

        if p_pooled == 0 or p_pooled == 1:
            return 0.0

        se = math.sqrt(p_pooled * (1 - p_pooled) * (2 / total))
        if se == 0:
            return 0.0

        z = abs(p_a - p_b) / se

        # Convert z-score to significance level (simplified)
        if z > 2.576:
            return 0.99
        elif z > 1.96:
            return 0.95
        elif z > 1.645:
            return 0.90
        else:
            return z / 1.645 * 0.90

    def get_optimization_history(self, module_name: Optional[str] = None) -> List[Dict]:
        """Get optimization history, optionally filtered by module"""
        with sqlite3.connect(DB_PATH) as conn:
            if module_name:
                cursor = conn.execute("""
                    SELECT * FROM optimization_results
                    WHERE module_name = ?
                    ORDER BY timestamp DESC
                """, (module_name,))
            else:
                cursor = conn.execute("""
                    SELECT * FROM optimization_results
                    ORDER BY timestamp DESC
                """)

            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


# Convenience functions for quick optimization
def quick_optimize(
    module: dspy.Module,
    trainset: List[dspy.Example],
    metric: Callable,
    **kwargs
) -> OptimizationResult:
    """Quick optimization with default settings"""
    config = OptimizationConfig(**kwargs)
    optimizer = DSPyOptimizer(config)
    return optimizer.optimize_module(module, trainset, metric)

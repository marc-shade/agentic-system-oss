#!/usr/bin/env python3
"""
Equation Integration Layer
==========================

Provides a clean API for integrating PySR-discovered equations into existing systems.
Handles equation loading, conversion to callable functions, error handling, and A/B testing.

Usage:
    from equation_integration import EquationIntegrator

    integrator = EquationIntegrator()

    # Use discovered equation
    improvement = integrator.darwin_godel_improvement(
        size_ratio=1.2,
        complexity_reduction=5,
        safety_score=0.9,
        modification_type_encoded=2,
        was_reverted=0
    )
"""

import sqlite3
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
import numpy as np
import sympy as sp
from sympy.utilities.lambdify import lambdify

logger = logging.getLogger(__name__)


@dataclass
class LoadedEquation:
    """Represents a loaded equation ready for use"""
    equation_id: str
    system_component: str
    purpose: str
    sympy_expr: str
    features: list
    performance_r2: float
    complexity_score: int
    callable_func: Callable
    validation_metrics: Dict[str, Any]


class EquationIntegrator:
    """
    Integration layer for PySR-discovered equations.

    Provides clean API for loading and using equations in production systems.
    Handles A/B testing, fallback to heuristics, error handling.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize equation integrator.

        Args:
            db_path: Path to discovered_equations.db (auto-detected if not provided)
        """
        if db_path is None:
            # Auto-detect database location
            current_file = Path(__file__).parent
            db_path = current_file.parent / "databases" / "discovered_equations.db"

        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Equation database not found: {self.db_path}")

        self._equation_cache: Dict[str, LoadedEquation] = {}
        self._load_all_equations()

    def _load_all_equations(self):
        """Load all equations from database into cache"""
        logger.info(f"Loading equations from {self.db_path}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT equation_id, system_component, purpose, sympy_expr, features,
                   performance_r2, complexity_score, validation_metrics
            FROM discovered_equations
            WHERE deprecated_at IS NULL
            ORDER BY performance_r2 DESC
        """)

        for row in cursor.fetchall():
            eq_id, component, purpose, expr, features_json, r2, complexity, metrics_json = row

            try:
                # Parse features and metrics
                features = json.loads(features_json)
                metrics = json.loads(metrics_json) if metrics_json else {}

                # Convert SymPy expression to callable function
                symbols = sp.symbols(' '.join(features))
                sympy_expr = sp.sympify(expr)
                callable_func = lambdify(symbols, sympy_expr, modules=['numpy'])

                # Create LoadedEquation
                loaded_eq = LoadedEquation(
                    equation_id=eq_id,
                    system_component=component,
                    purpose=purpose,
                    sympy_expr=expr,
                    features=features,
                    performance_r2=r2,
                    complexity_score=complexity,
                    callable_func=callable_func,
                    validation_metrics=metrics
                )

                # Cache by component_purpose key
                cache_key = f"{component}_{purpose}"
                self._equation_cache[cache_key] = loaded_eq

                logger.info(f"Loaded: {component}/{purpose} (R²={r2:.4f}, C={complexity})")

            except Exception as e:
                logger.error(f"Failed to load equation {eq_id}: {e}")

        conn.close()
        logger.info(f"Loaded {len(self._equation_cache)} equations")

    def get_equation(self, system_component: str, purpose: str) -> Optional[LoadedEquation]:
        """
        Get equation for specific component and purpose.

        Args:
            system_component: System name (e.g., "darwin_godel", "meta_learning")
            purpose: Equation purpose (e.g., "improvement_estimation", "agent_selection")

        Returns:
            LoadedEquation or None if not found
        """
        cache_key = f"{system_component}_{purpose}"
        return self._equation_cache.get(cache_key)

    # =========================================================================
    # Darwin Gödel Machine Integration
    # =========================================================================

    def darwin_godel_improvement(self,
                                 size_ratio: float,
                                 complexity_reduction: float,
                                 safety_score: float,
                                 modification_type_encoded: int,
                                 was_reverted: int) -> float:
        """
        Estimate improvement for Darwin Gödel Machine using discovered equation.

        Args:
            size_ratio: Code size before / code size after
            complexity_reduction: Complexity before - complexity after
            safety_score: Safety validation score (0.0-1.0)
            modification_type_encoded: Modification type (integer encoding)
            was_reverted: Whether modification was reverted (0 or 1)

        Returns:
            Predicted improvement score
        """
        eq = self.get_equation("darwin_godel", "improvement_estimation")
        if eq is None:
            logger.warning("Darwin Gödel equation not found, using fallback")
            return self._darwin_godel_fallback(size_ratio, complexity_reduction)

        try:
            # Call discovered equation
            improvement = eq.callable_func(
                size_ratio,
                complexity_reduction,
                safety_score,
                modification_type_encoded,
                was_reverted
            )

            # Validate output
            if np.isnan(improvement) or np.isinf(improvement):
                logger.warning("Equation produced NaN/Inf, using fallback")
                return self._darwin_godel_fallback(size_ratio, complexity_reduction)

            return float(improvement)

        except Exception as e:
            logger.error(f"Error evaluating Darwin Gödel equation: {e}")
            return self._darwin_godel_fallback(size_ratio, complexity_reduction)

    def _darwin_godel_fallback(self, size_ratio: float, complexity_reduction: float) -> float:
        """Fallback heuristic for Darwin Gödel (original logic)"""
        # Original heuristic: prioritize complexity reduction
        if complexity_reduction > 0:
            return min(0.3, complexity_reduction * 0.05)
        elif size_ratio > 1.2:
            return min(0.3, (size_ratio - 1.0) * 0.5)
        else:
            return 0.05

    # =========================================================================
    # Meta-Learning Engine Integration
    # =========================================================================

    def meta_learning_agent_score(self,
                                  success_rate: float,
                                  avg_quality_score: float,
                                  log_exec_time: float,
                                  total_tasks: int,
                                  task_type_encoded: int) -> float:
        """
        Calculate agent performance score using discovered equation.

        Args:
            success_rate: Agent success rate (0.0-1.0)
            avg_quality_score: Average quality score (0.0-1.0)
            log_exec_time: log(execution_time_ms)
            total_tasks: Total number of tasks completed
            task_type_encoded: Task type (integer encoding)

        Returns:
            Agent performance score
        """
        eq = self.get_equation("meta_learning", "agent_selection")
        if eq is None:
            logger.warning("Meta-learning equation not found, using fallback")
            return self._meta_learning_fallback(success_rate, avg_quality_score)

        try:
            # Call discovered equation
            score = eq.callable_func(
                success_rate,
                avg_quality_score,
                log_exec_time,
                total_tasks,
                task_type_encoded
            )

            # Validate output
            if np.isnan(score) or np.isinf(score):
                logger.warning("Equation produced NaN/Inf, using fallback")
                return self._meta_learning_fallback(success_rate, avg_quality_score)

            # Clip to valid range
            return float(np.clip(score, 0.0, 1.0))

        except Exception as e:
            logger.error(f"Error evaluating meta-learning equation: {e}")
            return self._meta_learning_fallback(success_rate, avg_quality_score)

    def _meta_learning_fallback(self, success_rate: float, avg_quality_score: float) -> float:
        """Fallback heuristic for meta-learning (original 50/50 weights)"""
        return success_rate * 0.5 + avg_quality_score * 0.5

    # =========================================================================
    # Skill Evolution System Integration
    # =========================================================================

    def skill_evolution_score(self,
                             success_rate: float,
                             avg_quality_score: float,
                             log_exec_time: float,
                             total_executions: int,
                             version_age_days: int) -> float:
        """
        Calculate skill performance score using discovered equation.

        Args:
            success_rate: Skill success rate (0.0-1.0)
            avg_quality_score: Average quality score (0.0-1.0)
            log_exec_time: log(avg_execution_time_ms)
            total_executions: Total number of executions
            version_age_days: Age of skill version in days

        Returns:
            Skill performance score
        """
        eq = self.get_equation("skill_evolution", "performance_scoring")
        if eq is None:
            logger.warning("Skill evolution equation not found, using fallback")
            return self._skill_evolution_fallback(success_rate, avg_quality_score)

        try:
            # Call discovered equation
            score = eq.callable_func(
                success_rate,
                avg_quality_score,
                log_exec_time,
                total_executions,
                version_age_days
            )

            # Validate output
            if np.isnan(score) or np.isinf(score):
                logger.warning("Equation produced NaN/Inf, using fallback")
                return self._skill_evolution_fallback(success_rate, avg_quality_score)

            # Clip to valid range
            return float(np.clip(score, 0.0, 1.0))

        except Exception as e:
            logger.error(f"Error evaluating skill evolution equation: {e}")
            return self._skill_evolution_fallback(success_rate, avg_quality_score)

    def _skill_evolution_fallback(self, success_rate: float, avg_quality_score: float) -> float:
        """Fallback heuristic for skill evolution (original 50/50 weights)"""
        return success_rate * 0.5 + avg_quality_score * 0.5

    # =========================================================================
    # A/B Testing Support
    # =========================================================================

    def compare_methods(self,
                       equation_result: float,
                       heuristic_result: float,
                       actual_outcome: Optional[float] = None) -> Dict[str, Any]:
        """
        Compare equation vs heuristic predictions.

        Args:
            equation_result: Result from PySR equation
            heuristic_result: Result from original heuristic
            actual_outcome: Actual measured outcome (if available)

        Returns:
            Dictionary with comparison metrics
        """
        comparison = {
            "equation_result": equation_result,
            "heuristic_result": heuristic_result,
            "difference": abs(equation_result - heuristic_result),
            "equation_closer": None,
            "equation_error": None,
            "heuristic_error": None
        }

        if actual_outcome is not None:
            equation_error = abs(equation_result - actual_outcome)
            heuristic_error = abs(heuristic_result - actual_outcome)

            comparison["actual_outcome"] = actual_outcome
            comparison["equation_error"] = equation_error
            comparison["heuristic_error"] = heuristic_error
            comparison["equation_closer"] = equation_error < heuristic_error
            comparison["improvement_percentage"] = (
                ((heuristic_error - equation_error) / max(heuristic_error, 0.001)) * 100
            )

        return comparison

    # =========================================================================
    # Utilities
    # =========================================================================

    def get_all_equations(self) -> Dict[str, LoadedEquation]:
        """Get all loaded equations"""
        return self._equation_cache.copy()

    def get_equation_info(self, system_component: str, purpose: str) -> Optional[Dict[str, Any]]:
        """Get equation metadata"""
        eq = self.get_equation(system_component, purpose)
        if eq is None:
            return None

        return {
            "equation_id": eq.equation_id,
            "system_component": eq.system_component,
            "purpose": eq.purpose,
            "sympy_expr": eq.sympy_expr,
            "features": eq.features,
            "performance_r2": eq.performance_r2,
            "complexity_score": eq.complexity_score,
            "validation_metrics": eq.validation_metrics
        }

    def reload_equations(self):
        """Reload all equations from database (useful after retraining)"""
        self._equation_cache.clear()
        self._load_all_equations()


# ============================================================================
# Global Integrator Instance
# ============================================================================

_global_integrator: Optional[EquationIntegrator] = None


def get_integrator() -> EquationIntegrator:
    """
    Get global equation integrator instance (singleton pattern).

    Returns:
        EquationIntegrator instance
    """
    global _global_integrator
    if _global_integrator is None:
        _global_integrator = EquationIntegrator()
    return _global_integrator


# ============================================================================
# Convenience Functions
# ============================================================================

def darwin_improvement(size_ratio: float, complexity_reduction: float,
                      safety_score: float = 1.0, modification_type: int = 0,
                      was_reverted: int = 0) -> float:
    """Convenience function for Darwin Gödel improvement estimation"""
    integrator = get_integrator()
    return integrator.darwin_godel_improvement(
        size_ratio, complexity_reduction, safety_score,
        modification_type, was_reverted
    )


def agent_score(success_rate: float, quality_score: float,
               exec_time_ms: float = 1000, total_tasks: int = 100,
               task_type: int = 0) -> float:
    """Convenience function for meta-learning agent scoring"""
    integrator = get_integrator()
    log_time = np.log1p(exec_time_ms)
    return integrator.meta_learning_agent_score(
        success_rate, quality_score, log_time, total_tasks, task_type
    )


def skill_score(success_rate: float, quality_score: float,
               exec_time_ms: float = 1000, total_executions: int = 100,
               version_age: int = 0) -> float:
    """Convenience function for skill evolution scoring"""
    integrator = get_integrator()
    log_time = np.log1p(exec_time_ms)
    return integrator.skill_evolution_score(
        success_rate, quality_score, log_time, total_executions, version_age
    )


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Initialize integrator
    integrator = EquationIntegrator()

    print("\n" + "="*60)
    print("EQUATION INTEGRATION TEST")
    print("="*60)

    # Test Darwin Gödel
    print("\n1. Darwin Gödel - Improvement Estimation:")
    improvement = integrator.darwin_godel_improvement(
        size_ratio=1.2,
        complexity_reduction=5,
        safety_score=0.9,
        modification_type_encoded=2,
        was_reverted=0
    )
    print(f"   Predicted improvement: {improvement:.4f}")

    # Test Meta-Learning
    print("\n2. Meta-Learning - Agent Selection:")
    score = integrator.meta_learning_agent_score(
        success_rate=0.90,
        avg_quality_score=0.80,
        log_exec_time=np.log1p(1000),
        total_tasks=100,
        task_type_encoded=0
    )
    print(f"   Agent score: {score:.4f}")

    # Test Skill Evolution
    print("\n3. Skill Evolution - Performance Scoring:")
    score = integrator.skill_evolution_score(
        success_rate=0.92,
        avg_quality_score=0.85,
        log_exec_time=np.log1p(800),
        total_executions=50,
        version_age_days=10
    )
    print(f"   Skill score: {score:.4f}")

    # Test A/B comparison
    print("\n4. A/B Comparison Example:")
    equation_result = 0.85
    heuristic_result = 0.75
    actual = 0.82
    comparison = integrator.compare_methods(equation_result, heuristic_result, actual)
    print(f"   Equation: {comparison['equation_result']:.4f}, Error: {comparison['equation_error']:.4f}")
    print(f"   Heuristic: {comparison['heuristic_result']:.4f}, Error: {comparison['heuristic_error']:.4f}")
    print(f"   Equation closer: {comparison['equation_closer']}")
    print(f"   Improvement: {comparison['improvement_percentage']:.1f}%")

    print("\n" + "="*60)
    print("INTEGRATION TEST COMPLETE")
    print("="*60)

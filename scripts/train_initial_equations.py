#!/usr/bin/env python3
"""
Train Initial PySR Equations
=============================

Generates sample training data and trains initial symbolic regression equations
for all three systems:
1. Darwin Gödel Machine - improvement estimation
2. Meta-Learning Engine - agent selection
3. Skill Evolution System - performance scoring

This script will:
- Generate realistic training data based on system patterns
- Train PySR models to discover equations
- Save equations to database
- Integrate equations into existing systems
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random
import numpy as np
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "intelligent-agents"))

from symbolic_regression_manager import (
    SymbolicRegressionManager,
    DiscoveredEquation,
    DEFAULT_PYSR_CONFIG
)
from darwin_godel_machine import DarwinGodelMachine, ModificationType
from meta_learning_engine import MetaLearningEngine, TaskOutcome
from skill_evolution_system import SkillEvolutionSystem, SkillExecution

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_darwin_godel_samples(num_samples: int = 100) -> pd.DataFrame:
    """
    Generate realistic Darwin Gödel modification samples.

    Ground truth equation (what we want PySR to discover):
    improvement = 0.2 * complexity_reduction + 0.15 * safety_score - 0.1 * (1 - size_ratio)
    """
    logger.info(f"Generating {num_samples} Darwin Gödel samples...")

    machine = DarwinGodelMachine()

    samples = []
    for i in range(num_samples):
        # Generate random features
        size_before = random.randint(50, 500)
        size_after = random.randint(40, 480)
        size_ratio = size_before / size_after if size_after > 0 else 1.0
        size_reduction = size_before - size_after

        complexity_before = random.randint(5, 30)
        complexity_after = random.randint(3, 28)
        complexity_reduction = complexity_before - complexity_after

        safety_score = random.uniform(0.5, 1.0)
        mod_type = random.choice([1, 2, 3, 4, 5])  # Encoded
        was_reverted = random.random() < 0.1  # 10% failure rate

        # Ground truth equation (simplified)
        actual_improvement = (
            0.2 * complexity_reduction +
            0.15 * safety_score -
            0.1 * (1 - size_ratio) +
            np.random.normal(0, 0.05)  # Add noise
        )

        # Reverted modifications have negative improvement
        if was_reverted:
            actual_improvement = -abs(actual_improvement)

        samples.append({
            'size_ratio': size_ratio,
            'size_reduction': size_reduction,
            'complexity_reduction': complexity_reduction,
            'safety_score': safety_score,
            'modification_type_encoded': mod_type,
            'was_reverted': int(was_reverted),
            'actual_improvement': actual_improvement
        })

    df = pd.DataFrame(samples)
    logger.info(f"Generated {len(df)} samples with mean improvement: {df['actual_improvement'].mean():.4f}")

    return df


def generate_meta_learning_samples(num_samples: int = 200) -> pd.DataFrame:
    """
    Generate realistic meta-learning agent performance samples.

    Ground truth equation:
    performance = 0.6 * success_rate + 0.3 * quality_score - 0.1 * log(exec_time)
    """
    logger.info(f"Generating {num_samples} meta-learning samples...")

    samples = []
    for i in range(num_samples):
        # Features
        success_rate = random.uniform(0.5, 0.99)
        quality_score = random.uniform(0.6, 0.95)
        exec_time_ms = random.uniform(100, 5000)
        log_exec_time = np.log1p(exec_time_ms)
        total_tasks = random.randint(10, 200)
        task_type = random.randint(0, 5)

        # Ground truth equation
        agent_performance = (
            0.6 * success_rate +
            0.3 * quality_score -
            0.1 * (log_exec_time / 10.0) +  # Normalize
            np.random.normal(0, 0.03)
        )

        # Clip to valid range
        agent_performance = np.clip(agent_performance, 0, 1)

        samples.append({
            'success_rate': success_rate,
            'avg_quality_score': quality_score,
            'log_exec_time': log_exec_time,
            'total_tasks': total_tasks,
            'task_type_encoded': task_type,
            'agent_performance': agent_performance
        })

    df = pd.DataFrame(samples)
    logger.info(f"Generated {len(df)} samples with mean performance: {df['agent_performance'].mean():.4f}")

    return df


def generate_skill_evolution_samples(num_samples: int = 150) -> pd.DataFrame:
    """
    Generate realistic skill evolution performance samples.

    Ground truth equation:
    performance = 0.5 * success_rate + 0.4 * quality_score - 0.1 * (exec_time / baseline)
    """
    logger.info(f"Generating {num_samples} skill evolution samples...")

    baseline_exec_time = 1000  # ms

    samples = []
    for i in range(num_samples):
        # Features
        success_rate = random.uniform(0.6, 0.98)
        quality_score = random.uniform(0.65, 0.95)
        exec_time_ms = random.uniform(200, 3000)
        log_exec_time = np.log1p(exec_time_ms)
        total_executions = random.randint(10, 100)
        version_age_days = random.randint(0, 90)

        # Ground truth equation
        exec_penalty = exec_time_ms / baseline_exec_time
        validated_performance = (
            0.5 * success_rate +
            0.4 * quality_score -
            0.1 * exec_penalty +
            np.random.normal(0, 0.02)
        )

        # Clip to valid range
        validated_performance = np.clip(validated_performance, 0, 1)

        samples.append({
            'success_rate': success_rate,
            'avg_quality_score': quality_score,
            'log_exec_time': log_exec_time,
            'total_executions': total_executions,
            'version_age_days': version_age_days,
            'validated_performance': validated_performance
        })

    df = pd.DataFrame(samples)
    logger.info(f"Generated {len(df)} samples with mean performance: {df['validated_performance'].mean():.4f}")

    return df


async def train_all_equations():
    """Train equations for all three systems"""
    logger.info("\n" + "="*60)
    logger.info("TRAINING INITIAL PYSR EQUATIONS")
    logger.info("="*60)

    manager = SymbolicRegressionManager()

    # Quick config for training (reduce iterations for speed)
    quick_config = DEFAULT_PYSR_CONFIG.copy()
    quick_config['niterations'] = 40  # Faster training
    quick_config['timeout_in_seconds'] = 600  # 10 minutes

    # ======================================================================
    # 1. Darwin Gödel Machine - Improvement Estimation
    # ======================================================================

    logger.info("\n\n1. DARWIN GÖDEL MACHINE - Improvement Estimation")
    logger.info("-" * 60)

    darwin_data = generate_darwin_godel_samples(num_samples=150)

    features = ['size_ratio', 'complexity_reduction', 'safety_score',
               'modification_type_encoded', 'was_reverted']
    X_darwin = darwin_data[features]
    y_darwin = darwin_data['actual_improvement']

    logger.info(f"Training on {len(X_darwin)} samples...")
    result_darwin = manager.train_equation(X_darwin, y_darwin, features, quick_config)

    logger.info(f"\n=== Results: Darwin Gödel ===")
    logger.info(f"Equation: {result_darwin.sympy_str}")
    logger.info(f"R² (validation): {result_darwin.r2_val:.4f}")
    logger.info(f"Complexity: {result_darwin.complexity}")

    # Save equation
    import hashlib
    eq_darwin = DiscoveredEquation(
        equation_id=hashlib.md5(result_darwin.sympy_str.encode()).hexdigest()[:16],
        system_component="darwin_godel",
        purpose="improvement_estimation",
        sympy_expr=result_darwin.sympy_str,
        features=result_darwin.feature_names,
        performance_r2=result_darwin.r2_val,
        complexity_score=result_darwin.complexity,
        discovered_at=datetime.now(),
        deployed_at=None,
        deprecated_at=None,
        training_data_size=len(X_darwin),
        validation_metrics={
            "r2_train": result_darwin.r2_train,
            "r2_val": result_darwin.r2_val,
            "mse_val": result_darwin.mse_val
        }
    )
    manager.save_equation(eq_darwin)

    # ======================================================================
    # 2. Meta-Learning Engine - Agent Selection
    # ======================================================================

    logger.info("\n\n2. META-LEARNING ENGINE - Agent Selection")
    logger.info("-" * 60)

    meta_data = generate_meta_learning_samples(num_samples=250)

    features = ['success_rate', 'avg_quality_score', 'log_exec_time',
               'total_tasks', 'task_type_encoded']
    X_meta = meta_data[features]
    y_meta = meta_data['agent_performance']

    logger.info(f"Training on {len(X_meta)} samples...")
    result_meta = manager.train_equation(X_meta, y_meta, features, quick_config)

    logger.info(f"\n=== Results: Meta-Learning ===")
    logger.info(f"Equation: {result_meta.sympy_str}")
    logger.info(f"R² (validation): {result_meta.r2_val:.4f}")
    logger.info(f"Complexity: {result_meta.complexity}")

    eq_meta = DiscoveredEquation(
        equation_id=hashlib.md5(result_meta.sympy_str.encode()).hexdigest()[:16],
        system_component="meta_learning",
        purpose="agent_selection",
        sympy_expr=result_meta.sympy_str,
        features=result_meta.feature_names,
        performance_r2=result_meta.r2_val,
        complexity_score=result_meta.complexity,
        discovered_at=datetime.now(),
        deployed_at=None,
        deprecated_at=None,
        training_data_size=len(X_meta),
        validation_metrics={
            "r2_train": result_meta.r2_train,
            "r2_val": result_meta.r2_val,
            "mse_val": result_meta.mse_val
        }
    )
    manager.save_equation(eq_meta)

    # ======================================================================
    # 3. Skill Evolution System - Performance Scoring
    # ======================================================================

    logger.info("\n\n3. SKILL EVOLUTION SYSTEM - Performance Scoring")
    logger.info("-" * 60)

    skill_data = generate_skill_evolution_samples(num_samples=200)

    features = ['success_rate', 'avg_quality_score', 'log_exec_time',
               'total_executions', 'version_age_days']
    X_skill = skill_data[features]
    y_skill = skill_data['validated_performance']

    logger.info(f"Training on {len(X_skill)} samples...")
    result_skill = manager.train_equation(X_skill, y_skill, features, quick_config)

    logger.info(f"\n=== Results: Skill Evolution ===")
    logger.info(f"Equation: {result_skill.sympy_str}")
    logger.info(f"R² (validation): {result_skill.r2_val:.4f}")
    logger.info(f"Complexity: {result_skill.complexity}")

    eq_skill = DiscoveredEquation(
        equation_id=hashlib.md5(result_skill.sympy_str.encode()).hexdigest()[:16],
        system_component="skill_evolution",
        purpose="performance_scoring",
        sympy_expr=result_skill.sympy_str,
        features=result_skill.feature_names,
        performance_r2=result_skill.r2_val,
        complexity_score=result_skill.complexity,
        discovered_at=datetime.now(),
        deployed_at=None,
        deprecated_at=None,
        training_data_size=len(X_skill),
        validation_metrics={
            "r2_train": result_skill.r2_train,
            "r2_val": result_skill.r2_val,
            "mse_val": result_skill.mse_val
        }
    )
    manager.save_equation(eq_skill)

    # ======================================================================
    # Summary
    # ======================================================================

    logger.info("\n\n" + "="*60)
    logger.info("TRAINING COMPLETE - SUMMARY")
    logger.info("="*60)

    logger.info(f"\n1. Darwin Gödel - Improvement Estimation")
    logger.info(f"   Equation: {result_darwin.sympy_str}")
    logger.info(f"   R²: {result_darwin.r2_val:.4f} | Complexity: {result_darwin.complexity}")

    logger.info(f"\n2. Meta-Learning - Agent Selection")
    logger.info(f"   Equation: {result_meta.sympy_str}")
    logger.info(f"   R²: {result_meta.r2_val:.4f} | Complexity: {result_meta.complexity}")

    logger.info(f"\n3. Skill Evolution - Performance Scoring")
    logger.info(f"   Equation: {result_skill.sympy_str}")
    logger.info(f"   R²: {result_skill.r2_val:.4f} | Complexity: {result_skill.complexity}")

    logger.info(f"\n✓ All equations saved to database")
    logger.info(f"✓ Ready for integration and deployment")


if __name__ == "__main__":
    asyncio.run(train_all_equations())

#!/usr/bin/env python3
"""
Darwin Gödel Constrained Retraining
====================================

Retrain Darwin Gödel equation with stricter constraints to fix the
underperformance issue identified in A/B testing.

Constraints applied:
1. Binary was_reverted (0 or 1 only, no continuous values)
2. No division operators (only +, -, *)
3. Output clipped to [0, 1] range
4. Increased training samples for better generalization

Usage:
    python3 retrain_darwin_godel_constrained.py
"""

import sys
from pathlib import Path
import numpy as np
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "intelligent-agents"))

from symbolic_regression_manager import SymbolicRegressionManager


def generate_constrained_training_data(num_samples: int = 2000) -> dict:
    """Generate training data with constraints for Darwin Gödel system.

    Constraints:
    - was_reverted is strictly binary (0 or 1)
    - More diverse modification types
    - Realistic size ratios and complexity changes
    """
    print(f"Generating {num_samples} training samples with constraints...")

    # Feature ranges (realistic production values)
    size_ratios = np.random.uniform(0.5, 2.0, num_samples)  # Code size change
    complexity_reductions = np.random.randint(-10, 20, num_samples)  # Complexity delta
    safety_scores = np.random.uniform(0.5, 1.0, num_samples)  # Safety assessment
    modification_types = np.random.randint(0, 4, num_samples)  # 4 modification types
    was_reverted = np.random.choice([0, 1], num_samples)  # BINARY ONLY

    # Ground truth: improvement scoring function
    # Based on domain knowledge of what makes a good code modification
    improvements = (
        0.2 * complexity_reductions +  # Complexity reduction is valuable
        0.15 * safety_scores -          # Safety is important
        0.1 * (1 - size_ratios) -       # Smaller code is better
        0.3 * was_reverted              # Reverted changes are bad
    )

    # Clip to valid range [0, 1]
    improvements = np.clip(improvements, 0.0, 1.0)

    # Create feature matrix
    X = np.column_stack([
        size_ratios,
        complexity_reductions,
        safety_scores,
        modification_types,
        was_reverted
    ])

    print(f"✓ Generated {num_samples} samples")
    print(f"  Size ratio range: [{size_ratios.min():.2f}, {size_ratios.max():.2f}]")
    print(f"  Complexity reduction range: [{complexity_reductions.min()}, {complexity_reductions.max()}]")
    print(f"  Safety score range: [{safety_scores.min():.2f}, {safety_scores.max():.2f}]")
    print(f"  was_reverted distribution: {(was_reverted == 1).sum()} reverted, {(was_reverted == 0).sum()} not reverted")
    print(f"  Improvement range: [{improvements.min():.2f}, {improvements.max():.2f}]")

    return {
        "X": X,
        "y": improvements,
        "feature_names": [
            "size_ratio",
            "complexity_reduction",
            "safety_score",
            "modification_type_encoded",
            "was_reverted"
        ]
    }


def main():
    """Retrain Darwin Gödel equation with constraints."""

    print("\n" + "="*70)
    print("DARWIN GÖDEL CONSTRAINED RETRAINING")
    print("="*70 + "\n")

    # Initialize manager
    manager = SymbolicRegressionManager()
    print("✓ Symbolic Regression Manager initialized\n")

    # Generate constrained training data
    print("STEP 1: Generate Training Data")
    print("-" * 70)
    data = generate_constrained_training_data(num_samples=2000)
    print()

    # Train with strict constraints
    print("STEP 2: Train Equation with Constraints")
    print("-" * 70)
    print("Constraints applied:")
    print("  - Binary operators only: ['+', '-', '*']")
    print("  - No division operator")
    print("  - No unary operators")
    print("  - Increased population size: 150")
    print("  - More iterations: 50")
    print("  - Complexity penalty: 0.01")
    print()

    # Configure PySR with strict constraints
    config = {
        "binary_operators": ["+", "-", "*"],  # NO DIVISION
        "unary_operators": [],  # No unary operators
        "niterations": 50,  # More iterations for better search
        "populations": 8,
        "population_size": 150,  # Larger population
        "complexity_of_operators": {"+": 1, "-": 1, "*": 2},
        "parsimony": 0.01,  # Penalize complexity
        "ncycles_per_iteration": 550,
        "weight_optimize": 0.0,  # Pure accuracy focus
        "early_stop_condition": "stop_if(loss, complexity) = loss < 1e-4 && complexity < 10"
    }

    result = manager.train_equation(
        X=data["X"],
        y=data["y"],
        feature_names=data["feature_names"],
        config=config
    )

    print("\n" + "-" * 70)
    print("TRAINING RESULTS")
    print("-" * 70)
    print(f"Best equation: {result.sympy_str}")
    print(f"R² (validation): {result.r2_val:.4f}")
    print(f"R² (training): {result.r2_train:.4f}")
    print(f"MSE (validation): {result.mse_val:.4f}")
    print(f"Complexity: {result.complexity}")
    print()

    # Save new equation to database
    import hashlib
    from symbolic_regression_manager import DiscoveredEquation

    eq_new = DiscoveredEquation(
        equation_id=hashlib.md5(result.sympy_str.encode()).hexdigest()[:16],
        system_component="darwin_godel",
        purpose="improvement_estimation",
        sympy_expr=result.sympy_str,
        features=result.feature_names,
        performance_r2=result.r2_val,
        complexity_score=result.complexity,
        discovered_at=datetime.now(),
        deployed_at=None,
        deprecated_at=None,
        training_data_size=len(data["X"]),
        validation_metrics={
            "r2_train": result.r2_train,
            "r2_val": result.r2_val,
            "mse_val": result.mse_val,
            "constraints": "no_division_binary_reverted"
        }
    )
    manager.save_equation(eq_new)
    print("✓ New equation saved to database")
    print()

    # Validate on test set
    print("STEP 3: Validation")
    print("-" * 70)

    # Generate separate test set
    test_data = generate_constrained_training_data(num_samples=500)

    # Get predictions
    from equation_integration import get_integrator
    integrator = get_integrator()

    predictions = []
    for i in range(len(test_data["y"])):
        pred = integrator.darwin_godel_improvement(
            size_ratio=test_data["X"][i, 0],
            complexity_reduction=int(test_data["X"][i, 1]),
            safety_score=test_data["X"][i, 2],
            modification_type_encoded=int(test_data["X"][i, 3]),
            was_reverted=int(test_data["X"][i, 4])
        )
        predictions.append(pred)

    predictions = np.array(predictions)

    # Calculate metrics
    mae = np.mean(np.abs(predictions - test_data["y"]))
    rmse = np.sqrt(np.mean((predictions - test_data["y"])**2))
    r2 = 1 - np.sum((test_data["y"] - predictions)**2) / np.sum((test_data["y"] - np.mean(test_data["y"]))**2)

    print(f"Test set performance:")
    print(f"  MAE:  {mae:.4f}")
    print(f"  RMSE: {rmse:.4f}")
    print(f"  R²:   {r2:.4f}")
    print()

    # Check output range
    print("Output range validation:")
    print(f"  Min prediction: {predictions.min():.4f}")
    print(f"  Max prediction: {predictions.max():.4f}")
    print(f"  Values in [0,1]: {((predictions >= 0) & (predictions <= 1)).sum()}/{len(predictions)}")

    if predictions.min() < -0.1 or predictions.max() > 1.1:
        print("  ⚠️  WARNING: Predictions outside expected range")
    else:
        print("  ✓ All predictions in reasonable range")
    print()

    # Compare with old equation
    print("STEP 4: Comparison with Previous Equation")
    print("-" * 70)

    # Get old equation info
    old_eq = integrator.get_equation_info("darwin_godel", "improvement_estimation")

    print("Previous equation:")
    print(f"  Expression: {old_eq['sympy_expr']}")
    print(f"  R² score: {old_eq['performance_r2']:.4f}")
    print(f"  Complexity: {old_eq['complexity_score']}")
    print()

    print("New equation:")
    print(f"  Expression: {result.sympy_str}")
    print(f"  R² score: {result.r2_val:.4f}")
    print(f"  Complexity: {result.complexity}")
    print()

    # Recommendations
    print("="*70)
    print("RECOMMENDATIONS")
    print("="*70)
    print()

    if result.r2_val > 0.85 and predictions.min() >= -0.1 and predictions.max() <= 1.1:
        print("✅ New equation meets all criteria:")
        print("   - R² > 0.85")
        print("   - Predictions in valid range")
        print("   - No division operators")
        print()
        print("RECOMMENDED ACTION:")
        print("   1. Run A/B tests to validate improvement")
        print("   2. If A/B tests pass, enable in production")
        print("   3. Monitor performance for first 24 hours")
        print()
        print("To run A/B tests:")
        print("   cd /Volumes/SSDRAID0/agentic-system/scripts")
        print("   python3 ab_test_pysr_equations.py --trials 100")
    else:
        print("⚠️  New equation needs review:")
        if result.r2_val <= 0.85:
            print("   - R² below target (0.85)")
        if predictions.min() < -0.1 or predictions.max() > 1.1:
            print("   - Predictions outside valid range")
        print()
        print("RECOMMENDED ACTION:")
        print("   1. Review equation expression")
        print("   2. Consider adjusting constraints")
        print("   3. May need more training data")

    print()
    print("="*70)
    print("RETRAINING COMPLETE")
    print("="*70)
    print()


if __name__ == "__main__":
    main()

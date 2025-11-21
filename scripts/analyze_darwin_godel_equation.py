#!/usr/bin/env python3
"""
Darwin Gödel Equation Analysis
===============================

Deep analysis of why the Darwin Gödel equation underperforms compared to the
original heuristic. Investigates numerical stability, edge cases, and provides
recommendations for improvement.

Usage:
    python3 analyze_darwin_godel_equation.py
"""

import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "intelligent-agents"))

from equation_integration import get_integrator


def analyze_equation_behavior():
    """Analyze Darwin Gödel equation behavior across parameter space"""

    print("\n" + "="*70)
    print("DARWIN GÖDEL EQUATION ANALYSIS")
    print("="*70 + "\n")

    integrator = get_integrator()

    # Get equation info
    eq_info = integrator.get_equation_info("darwin_godel", "improvement_estimation")
    print(f"Equation: {eq_info['sympy_expr']}")
    print(f"R² Score: {eq_info['performance_r2']:.4f}")
    print(f"Complexity: {eq_info['complexity_score']}")
    print()

    # Analysis 1: Test with different was_reverted values
    print("ANALYSIS 1: Sensitivity to was_reverted parameter")
    print("-" * 70)

    test_was_reverted = [0.0, 0.1, 0.2, 0.3, 0.4, 0.45, 0.46, 0.461, 0.4614, 0.47, 0.5, 0.6, 1.0]

    for was_reverted in test_was_reverted:
        try:
            result = integrator.darwin_godel_improvement(
                size_ratio=1.2,
                complexity_reduction=5,
                safety_score=0.9,
                modification_type_encoded=0,
                was_reverted=int(was_reverted)  # Should be 0 or 1
            )

            # Check for problematic values
            is_problematic = abs(result) > 10 or np.isnan(result) or np.isinf(result)
            status = "⚠️  UNSTABLE" if is_problematic else "✓ OK"

            print(f"was_reverted={was_reverted:.4f}: result={result:>10.4f} {status}")

        except Exception as e:
            print(f"was_reverted={was_reverted:.4f}: ERROR - {e}")

    print()

    # Analysis 2: Division by near-zero issue
    print("ANALYSIS 2: Division by (was_reverted - 0.4614)")
    print("-" * 70)
    print("The equation divides by (was_reverted - 0.4614)")
    print("Problem: was_reverted is binary (0 or 1) in reality")
    print()
    print("When was_reverted = 0:")
    print(f"  Denominator: 0 - 0.4614 = -0.4614")
    print(f"  Result: Negative values possible")
    print()
    print("When was_reverted = 1:")
    print(f"  Denominator: 1 - 0.4614 = 0.5386")
    print(f"  Result: Should be stable")
    print()

    # Test with actual binary values
    for was_reverted in [0, 1]:
        result = integrator.darwin_godel_improvement(
            size_ratio=1.2,
            complexity_reduction=5,
            safety_score=0.9,
            modification_type_encoded=0,
            was_reverted=was_reverted
        )
        print(f"was_reverted={was_reverted}: result={result:.4f}")

    print()

    # Analysis 3: Compare equation vs heuristic across parameter space
    print("ANALYSIS 3: Equation vs Heuristic comparison")
    print("-" * 70)

    test_cases = [
        # (size_ratio, complexity_reduction, description)
        (1.5, 10, "Large simplification"),
        (1.2, 5, "Moderate simplification"),
        (1.0, 0, "No change"),
        (0.8, -3, "Code grew, complexity increased"),
        (2.0, 15, "Massive simplification"),
        (0.5, -10, "Code doubled, complexity increased"),
    ]

    print(f"{'Description':<30} {'PySR':<12} {'Heuristic':<12} {'Winner':<10}")
    print("-" * 70)

    for size_ratio, complexity_reduction, description in test_cases:
        # PySR result
        pysr_result = integrator.darwin_godel_improvement(
            size_ratio=size_ratio,
            complexity_reduction=complexity_reduction,
            safety_score=0.9,
            modification_type_encoded=0,
            was_reverted=0
        )

        # Heuristic result
        heuristic_result = integrator._darwin_godel_fallback(
            size_ratio=size_ratio,
            complexity_reduction=complexity_reduction
        )

        winner = "PySR" if abs(pysr_result) < abs(heuristic_result) else "Heuristic"

        print(f"{description:<30} {pysr_result:>11.4f} {heuristic_result:>11.4f}  {winner:<10}")

    print()

    # Analysis 4: Ground truth comparison
    print("ANALYSIS 4: Ground Truth Alignment")
    print("-" * 70)
    print("Ground truth from training: improvement = 0.2*complexity_reduction + 0.15*safety_score - 0.1*(1-size_ratio)")
    print()

    test_samples = [
        (1.2, 5, 0.9),   # Should be ~1.0 + 0.135 - 0.02 = 1.115
        (1.0, 10, 0.8),  # Should be ~2.0 + 0.12 + 0.0 = 2.12
        (0.8, 0, 0.7),   # Should be ~0.0 + 0.105 + 0.02 = 0.125
    ]

    print(f"{'(size, comp, safe)':<25} {'Ground Truth':<15} {'PySR':<12} {'Heuristic':<12}")
    print("-" * 70)

    for size_ratio, complexity_reduction, safety_score in test_samples:
        # Ground truth
        ground_truth = (
            0.2 * complexity_reduction +
            0.15 * safety_score -
            0.1 * (1 - size_ratio)
        )
        ground_truth = np.clip(ground_truth, 0.0, 1.0)

        # PySR
        pysr_result = integrator.darwin_godel_improvement(
            size_ratio=size_ratio,
            complexity_reduction=complexity_reduction,
            safety_score=safety_score,
            modification_type_encoded=0,
            was_reverted=0
        )

        # Heuristic
        heuristic_result = integrator._darwin_godel_fallback(
            size_ratio=size_ratio,
            complexity_reduction=complexity_reduction
        )

        print(f"({size_ratio:.1f}, {complexity_reduction:>2d}, {safety_score:.1f})      "
              f"{ground_truth:>14.4f} {pysr_result:>11.4f} {heuristic_result:>11.4f}")

    print()

    # Recommendations
    print("="*70)
    print("RECOMMENDATIONS")
    print("="*70)
    print()
    print("1. **Root Cause:**")
    print("   - Equation divides by (was_reverted - 0.4614)")
    print("   - Training data likely had continuous was_reverted values")
    print("   - Production uses binary was_reverted (0 or 1)")
    print("   - This mismatch causes poor generalization")
    print()
    print("2. **Numerical Stability Issues:**")
    print("   - Negative denominators when was_reverted=0")
    print("   - Equation produces values outside [0,1] range")
    print("   - No clipping applied in the equation itself")
    print()
    print("3. **Proposed Solutions:**")
    print()
    print("   Option A: Retrain with constraints")
    print("   - Explicitly train with binary was_reverted (0 or 1)")
    print("   - Add constraint to prevent division operators")
    print("   - Limit equation to only +, -, * operators")
    print()
    print("   Option B: Post-process equation output")
    print("   - Add np.clip(result, 0.0, 1.0) to integration layer")
    print("   - Handle NaN/Inf values more aggressively")
    print()
    print("   Option C: Weighted ensemble")
    print("   - Use 30% PySR + 70% heuristic")
    print("   - Leverage equation insights without full reliance")
    print()
    print("   Option D: Retrain with more data")
    print("   - Wait for real production data")
    print("   - Use actual modification outcomes")
    print("   - May take weeks to accumulate sufficient data")
    print()
    print("4. **Immediate Action:**")
    print("   - Keep Darwin Gödel on heuristic fallback in production")
    print("   - Implement Option A (retrain with constraints)")
    print("   - Deploy Meta-Learning and Skill Evolution (both working well)")
    print()
    print("="*70)


def visualize_equation_surface():
    """Create visualization of equation behavior"""
    print("\nGenerating visualization...")

    integrator = get_integrator()

    # Create parameter grid
    size_ratios = np.linspace(0.5, 2.0, 50)
    complexity_reductions = np.linspace(-10, 15, 50)

    # Compute results for each combination
    pysr_results = np.zeros((len(size_ratios), len(complexity_reductions)))
    heuristic_results = np.zeros((len(size_ratios), len(complexity_reductions)))

    for i, size_ratio in enumerate(size_ratios):
        for j, complexity_reduction in enumerate(complexity_reductions):
            # PySR
            try:
                pysr_result = integrator.darwin_godel_improvement(
                    size_ratio=size_ratio,
                    complexity_reduction=complexity_reduction,
                    safety_score=0.9,
                    modification_type_encoded=0,
                    was_reverted=0
                )
                pysr_results[i, j] = np.clip(pysr_result, -2, 2)  # Clip for visualization
            except:
                pysr_results[i, j] = np.nan

            # Heuristic
            heuristic_results[i, j] = integrator._darwin_godel_fallback(
                size_ratio=size_ratio,
                complexity_reduction=complexity_reduction
            )

    # Create figure
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    # Plot PySR results
    im1 = axes[0].contourf(complexity_reductions, size_ratios, pysr_results,
                           levels=20, cmap='RdYlGn')
    axes[0].set_xlabel('Complexity Reduction')
    axes[0].set_ylabel('Size Ratio')
    axes[0].set_title('PySR Equation Output')
    plt.colorbar(im1, ax=axes[0], label='Improvement Score')

    # Plot heuristic results
    im2 = axes[1].contourf(complexity_reductions, size_ratios, heuristic_results,
                           levels=20, cmap='RdYlGn')
    axes[1].set_xlabel('Complexity Reduction')
    axes[1].set_ylabel('Size Ratio')
    axes[1].set_title('Heuristic Output')
    plt.colorbar(im2, ax=axes[1], label='Improvement Score')

    plt.tight_layout()

    # Save figure
    output_path = Path(__file__).parent / "darwin_godel_analysis.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✓ Visualization saved to: {output_path}")

    plt.close()


def main():
    """Run all analyses"""
    analyze_equation_behavior()
    visualize_equation_surface()

    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("1. Review recommendations above")
    print("2. View visualization: scripts/darwin_godel_analysis.png")
    print("3. Decide on solution approach (A, B, C, or D)")
    print("4. If Option A: Run scripts/retrain_darwin_godel_constrained.py")
    print()


if __name__ == "__main__":
    main()

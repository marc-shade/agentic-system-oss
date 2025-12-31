"""
Uncertainty estimation for routing decisions.

Ported from ruvector/crates/ruvector-tiny-dancer-core/src/uncertainty.rs
"""

from typing import Any, Dict, List, Optional, Tuple

from .config import UncertaintyConfig


class UncertaintyEstimator:
    """
    Uncertainty estimator for routing decisions.

    Ported from ruvector/crates/ruvector-tiny-dancer-core/src/uncertainty.rs

    Uses conformal prediction concepts:
    - Boundary distance uncertainty: Higher uncertainty near decision boundary
    - Calibration from historical predictions vs outcomes
    - Statistical guarantees via conformal prediction

    Key insight: Uncertainty = 1.0 - 2 * |prediction - boundary|
    - At boundary (0.5): uncertainty = 1.0 (maximum)
    - At extremes (0 or 1): uncertainty = 0.0 (minimum)
    """

    def __init__(self, config: Optional[UncertaintyConfig] = None):
        self.config = config or UncertaintyConfig()
        self.calibration_scores: List[float] = []
        self.prediction_history: List[Tuple[float, bool]] = []  # (prediction, was_correct)
        self._calibration_threshold: Optional[float] = None

    def estimate(self, features: Optional[List[float]], prediction: float) -> float:
        """
        Estimate uncertainty for a prediction.

        Uses boundary distance heuristic:
        - Predictions near 0.5 (decision boundary) have high uncertainty
        - Predictions near 0 or 1 have low uncertainty

        Args:
            features: Input features (reserved for future feature-based uncertainty)
            prediction: Model prediction or confidence score [0, 1]

        Returns:
            Uncertainty score [0, 1] where 1 = maximum uncertainty
        """
        # Distance from decision boundary (0.5)
        boundary_distance = abs(prediction - self.config.boundary_threshold)

        # Higher uncertainty when close to boundary
        # uncertainty = 1 - 2*distance maps:
        #   distance=0 (at boundary) -> uncertainty=1
        #   distance=0.5 (at extremes) -> uncertainty=0
        boundary_uncertainty = 1.0 - (boundary_distance * 2.0)

        # Clip to [0, 1]
        return max(0.0, min(1.0, boundary_uncertainty))

    def calibrate(self, predictions: List[float], outcomes: List[bool]) -> float:
        """
        Calibrate the estimator using historical predictions and outcomes.

        Implements conformal prediction calibration:
        1. Compute non-conformity scores for each (prediction, outcome) pair
        2. Find the quantile threshold that achieves desired coverage

        Args:
            predictions: Historical prediction scores [0, 1]
            outcomes: Actual outcomes (True = success, False = failure)

        Returns:
            Calibration score (1.0 = perfectly calibrated)
        """
        if len(predictions) < self.config.min_samples_for_calibration:
            return 0.5  # Not enough data, return neutral score

        if len(predictions) != len(outcomes):
            raise ValueError("predictions and outcomes must have same length")

        # Compute non-conformity scores
        # For each prediction, score = |prediction - actual_outcome|
        nonconformity_scores = []
        for pred, outcome in zip(predictions, outcomes):
            actual = 1.0 if outcome else 0.0
            score = abs(pred - actual)
            nonconformity_scores.append(score)

        # Store for calibration
        self.calibration_scores = nonconformity_scores

        # Compute calibration threshold (quantile of non-conformity scores)
        sorted_scores = sorted(nonconformity_scores)
        quantile_idx = int(len(sorted_scores) * self.config.calibration_quantile)
        quantile_idx = min(quantile_idx, len(sorted_scores) - 1)
        self._calibration_threshold = sorted_scores[quantile_idx]

        # Update prediction history
        self.prediction_history.extend(zip(predictions, outcomes))

        # Return calibration quality (1 - mean non-conformity)
        mean_nonconformity = sum(nonconformity_scores) / len(nonconformity_scores)
        return 1.0 - mean_nonconformity

    def record_outcome(self, prediction: float, was_correct: bool):
        """Record a prediction outcome for future calibration."""
        self.prediction_history.append((prediction, was_correct))

        # Auto-recalibrate if we have enough new samples
        if len(self.prediction_history) >= self.config.min_samples_for_calibration:
            if len(self.prediction_history) % self.config.min_samples_for_calibration == 0:
                preds = [p for p, _ in self.prediction_history[-100:]]
                outcomes = [o for _, o in self.prediction_history[-100:]]
                self.calibrate(preds, outcomes)

    def get_calibrated_uncertainty(self, prediction: float) -> Tuple[float, float]:
        """
        Get uncertainty with calibration adjustment.

        Returns:
            Tuple of (raw_uncertainty, calibrated_uncertainty)
        """
        raw = self.estimate(None, prediction)

        if self._calibration_threshold is None:
            return (raw, raw)

        # Adjust uncertainty based on calibration
        # If calibration shows model is overconfident, increase uncertainty
        calibration_factor = self._calibration_threshold / 0.5  # 0.5 = neutral
        calibrated = raw * calibration_factor
        calibrated = max(0.0, min(1.0, calibrated))

        return (raw, calibrated)

    def get_statistics(self) -> Dict[str, Any]:
        """Get uncertainty estimation statistics."""
        recent_preds = self.prediction_history[-100:] if self.prediction_history else []

        if recent_preds:
            recent_accuracy = sum(1 for _, o in recent_preds if o) / len(recent_preds)
            avg_uncertainty = sum(self.estimate(None, p) for p, _ in recent_preds) / len(recent_preds)
        else:
            recent_accuracy = 0.0
            avg_uncertainty = 0.5

        return {
            "calibration_quantile": self.config.calibration_quantile,
            "calibration_threshold": self._calibration_threshold,
            "total_predictions_tracked": len(self.prediction_history),
            "recent_accuracy": round(recent_accuracy, 4),
            "average_uncertainty": round(avg_uncertainty, 4),
            "is_calibrated": self._calibration_threshold is not None,
            "calibration_samples": len(self.calibration_scores)
        }

    def reset(self):
        """Reset calibration state."""
        self.calibration_scores.clear()
        self.prediction_history.clear()
        self._calibration_threshold = None

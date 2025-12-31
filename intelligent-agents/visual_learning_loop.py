#!/usr/bin/env python3
"""
Visual Learning Feedback Loop - Continuous Visual Learning System

Implements a complete learning cycle for Visual AGI:
1. Observe: Capture visual state
2. Predict: What should happen next based on patterns
3. Act: Take actions influenced by visual context
4. Evaluate: Compare predicted vs actual outcomes
5. Learn: Update models and patterns

This creates a self-improving visual understanding system.

STATUS: Production Ready
"""

import asyncio
import hashlib
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-agents')
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/shared')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LearningPhase(Enum):
    """Phases of the learning loop."""
    OBSERVE = "observe"
    PREDICT = "predict"
    ACT = "act"
    EVALUATE = "evaluate"
    LEARN = "learn"


class PredictionType(Enum):
    """Types of predictions."""
    SCENE_TRANSITION = "scene_transition"
    OBJECT_APPEARANCE = "object_appearance"
    ACTION_OUTCOME = "action_outcome"
    ERROR_OCCURRENCE = "error_occurrence"


@dataclass
class Prediction:
    """A prediction about visual state."""
    id: str
    prediction_type: PredictionType
    predicted_outcome: str
    confidence: float
    reasoning: str
    context: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PredictionOutcome:
    """Outcome of a prediction for learning."""
    prediction_id: str
    predicted: str
    actual: str
    correct: bool
    error_magnitude: float
    learning_signal: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class LearningUpdate:
    """A learning update to apply."""
    update_type: str
    pattern_name: str
    old_value: Any
    new_value: Any
    confidence_delta: float
    source: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class VisualLearningLoop:
    """
    Continuous visual learning system.

    Implements observe-predict-act-evaluate-learn cycle for
    self-improving visual understanding.
    """

    def __init__(
        self,
        storage_path: str = "/Volumes/SSDRAID0/agentic-system/databases/visual_learning"
    ):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

        # Learning state
        self._predictions: List[Prediction] = []
        self._pending_predictions: Dict[str, Prediction] = {}
        self._outcomes: List[PredictionOutcome] = []
        self._learning_updates: List[LearningUpdate] = []

        # Learned models
        self._transition_model = self._load_model("transitions")
        self._object_model = self._load_model("objects")
        self._action_model = self._load_model("actions")
        self._error_model = self._load_model("errors")

        # Performance tracking
        self._performance_history = []

        logger.info(f"VisualLearningLoop initialized at {storage_path}")

    def _load_model(self, model_name: str) -> Dict[str, Any]:
        """Load a learned model from disk."""
        model_path = os.path.join(self.storage_path, f"{model_name}_model.json")

        if os.path.exists(model_path):
            try:
                with open(model_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass

        # Default model structure
        return {
            "patterns": {},
            "confidences": {},
            "update_count": 0,
            "last_updated": datetime.now().isoformat()
        }

    def _save_model(self, model_name: str, model: Dict[str, Any]) -> None:
        """Save a learned model to disk."""
        model_path = os.path.join(self.storage_path, f"{model_name}_model.json")
        model["last_updated"] = datetime.now().isoformat()

        with open(model_path, 'w') as f:
            json.dump(model, f, indent=2, default=str)

    async def observe(self, visual_state: Dict) -> Dict[str, Any]:
        """
        Phase 1: Observe current visual state.

        Captures visual state and prepares for prediction.
        """
        observation = {
            "phase": LearningPhase.OBSERVE.value,
            "scene_type": visual_state.get("scene_type", "unknown"),
            "objects": visual_state.get("objects", []),
            "confidence": visual_state.get("confidence", 0),
            "description": visual_state.get("description", "")[:200],
            "timestamp": datetime.now().isoformat()
        }

        # Check pending predictions against this observation
        outcomes = await self._check_predictions(visual_state)

        return {
            "observation": observation,
            "predictions_resolved": len(outcomes),
            "outcomes": outcomes
        }

    async def _check_predictions(self, visual_state: Dict) -> List[PredictionOutcome]:
        """Check pending predictions against actual observation."""
        outcomes = []

        for pred_id, prediction in list(self._pending_predictions.items()):
            outcome = self._evaluate_prediction(prediction, visual_state)
            if outcome:
                outcomes.append(outcome)
                self._outcomes.append(outcome)
                del self._pending_predictions[pred_id]

                # Trigger learning
                await self._learn_from_outcome(outcome)

        return outcomes

    def _evaluate_prediction(
        self,
        prediction: Prediction,
        visual_state: Dict
    ) -> Optional[PredictionOutcome]:
        """Evaluate a prediction against actual state."""
        actual = ""
        correct = False
        error_magnitude = 1.0

        if prediction.prediction_type == PredictionType.SCENE_TRANSITION:
            actual = visual_state.get("scene_type", "")
            correct = actual == prediction.predicted_outcome
            error_magnitude = 0.0 if correct else 1.0

        elif prediction.prediction_type == PredictionType.OBJECT_APPEARANCE:
            objects = set(visual_state.get("objects", []))
            predicted_obj = prediction.predicted_outcome
            correct = predicted_obj in objects
            actual = "present" if correct else "absent"
            error_magnitude = 0.0 if correct else 1.0

        elif prediction.prediction_type == PredictionType.ERROR_OCCURRENCE:
            description = visual_state.get("description", "").lower()
            predicted_error = prediction.predicted_outcome.lower()
            has_error = "error" in description or "exception" in description
            correct = (predicted_error == "error") == has_error
            actual = "error" if has_error else "no_error"
            error_magnitude = 0.0 if correct else 1.0

        elif prediction.prediction_type == PredictionType.ACTION_OUTCOME:
            actual = visual_state.get("scene_type", "")
            correct = actual == prediction.predicted_outcome
            error_magnitude = 0.0 if correct else 1.0

        learning_signal = "reinforce" if correct else "correct"

        return PredictionOutcome(
            prediction_id=prediction.id,
            predicted=prediction.predicted_outcome,
            actual=actual,
            correct=correct,
            error_magnitude=error_magnitude,
            learning_signal=learning_signal
        )

    async def predict(
        self,
        current_state: Dict,
        prediction_type: PredictionType,
        context: Optional[Dict] = None
    ) -> Prediction:
        """
        Phase 2: Make a prediction about future visual state.

        Uses learned models to predict what will happen.
        """
        context = context or {}

        # Generate prediction based on type
        if prediction_type == PredictionType.SCENE_TRANSITION:
            predicted, confidence, reasoning = self._predict_scene_transition(current_state)
        elif prediction_type == PredictionType.OBJECT_APPEARANCE:
            predicted, confidence, reasoning = self._predict_object_appearance(current_state, context)
        elif prediction_type == PredictionType.ERROR_OCCURRENCE:
            predicted, confidence, reasoning = self._predict_error(current_state)
        elif prediction_type == PredictionType.ACTION_OUTCOME:
            predicted, confidence, reasoning = self._predict_action_outcome(current_state, context)
        else:
            predicted, confidence, reasoning = "unknown", 0.5, "No model available"

        pred_id = f"pred_{datetime.now().strftime('%Y%m%d%H%M%S')}_{prediction_type.value[:4]}"

        prediction = Prediction(
            id=pred_id,
            prediction_type=prediction_type,
            predicted_outcome=predicted,
            confidence=confidence,
            reasoning=reasoning,
            context={
                "current_scene": current_state.get("scene_type"),
                "current_objects": current_state.get("objects", [])[:5],
                **context
            }
        )

        self._predictions.append(prediction)
        self._pending_predictions[pred_id] = prediction
        self._store_prediction(prediction)

        return prediction

    def _predict_scene_transition(self, current_state: Dict) -> Tuple[str, float, str]:
        """Predict next scene type."""
        current_scene = current_state.get("scene_type", "unknown")

        # Check transition model
        transitions = self._transition_model.get("patterns", {})
        confidences = self._transition_model.get("confidences", {})

        if current_scene in transitions:
            next_scenes = transitions[current_scene]
            if next_scenes:
                # Find most likely transition
                most_likely = max(next_scenes.items(), key=lambda x: x[1])
                next_scene = most_likely[0]
                conf = confidences.get(f"{current_scene}->{next_scene}", 0.5)

                return next_scene, conf, f"Based on {most_likely[1]} observed transitions"

        # Default: predict same scene
        return current_scene, 0.6, "No transition data, predicting stability"

    def _predict_object_appearance(
        self,
        current_state: Dict,
        context: Dict
    ) -> Tuple[str, float, str]:
        """Predict if an object will appear."""
        current_scene = current_state.get("scene_type", "unknown")
        target_object = context.get("target_object", "")

        if not target_object:
            return "unknown", 0.3, "No target object specified"

        # Check object model
        scene_objects = self._object_model.get("patterns", {}).get(current_scene, {})

        if target_object in scene_objects:
            likelihood = scene_objects[target_object] / max(scene_objects.values())
            return target_object, likelihood, f"Object common in {current_scene} scene"

        return target_object, 0.3, f"Object not commonly seen in {current_scene}"

    def _predict_error(self, current_state: Dict) -> Tuple[str, float, str]:
        """Predict if an error will occur."""
        current_scene = current_state.get("scene_type", "unknown")

        # Check error model
        error_rates = self._error_model.get("patterns", {})

        if current_scene in error_rates:
            rate = error_rates[current_scene]
            if rate > 0.3:
                return "error", rate, f"Scene {current_scene} has {rate:.0%} error rate"

        return "no_error", 0.8, "Low error probability"

    def _predict_action_outcome(
        self,
        current_state: Dict,
        context: Dict
    ) -> Tuple[str, float, str]:
        """Predict outcome of an action."""
        action = context.get("action", "")
        current_scene = current_state.get("scene_type", "unknown")

        # Check action model
        action_outcomes = self._action_model.get("patterns", {})

        key = f"{current_scene}:{action}"
        if key in action_outcomes:
            outcomes = action_outcomes[key]
            if outcomes:
                most_likely = max(outcomes.items(), key=lambda x: x[1])
                return most_likely[0], 0.7, f"Based on {most_likely[1]} observations"

        return current_scene, 0.5, "No action outcome data"

    async def _learn_from_outcome(self, outcome: PredictionOutcome) -> LearningUpdate:
        """
        Phase 5: Learn from prediction outcome.

        Updates models based on prediction success/failure.
        """
        # Find the prediction
        prediction = None
        for p in self._predictions:
            if p.id == outcome.prediction_id:
                prediction = p
                break

        if not prediction:
            return None

        update = None

        if prediction.prediction_type == PredictionType.SCENE_TRANSITION:
            update = self._update_transition_model(prediction, outcome)
        elif prediction.prediction_type == PredictionType.OBJECT_APPEARANCE:
            update = self._update_object_model(prediction, outcome)
        elif prediction.prediction_type == PredictionType.ERROR_OCCURRENCE:
            update = self._update_error_model(prediction, outcome)
        elif prediction.prediction_type == PredictionType.ACTION_OUTCOME:
            update = self._update_action_model(prediction, outcome)

        if update:
            self._learning_updates.append(update)
            self._store_learning_update(update)

        return update

    def _update_transition_model(
        self,
        prediction: Prediction,
        outcome: PredictionOutcome
    ) -> LearningUpdate:
        """Update scene transition model."""
        current_scene = prediction.context.get("current_scene", "unknown")
        actual_next = outcome.actual

        # Update pattern counts
        patterns = self._transition_model.setdefault("patterns", {})
        scene_transitions = patterns.setdefault(current_scene, {})

        old_count = scene_transitions.get(actual_next, 0)
        scene_transitions[actual_next] = old_count + 1

        # Update confidence
        confidences = self._transition_model.setdefault("confidences", {})
        key = f"{current_scene}->{actual_next}"

        total_from_scene = sum(scene_transitions.values())
        new_confidence = scene_transitions[actual_next] / total_from_scene

        old_conf = confidences.get(key, 0.5)
        confidences[key] = new_confidence

        self._transition_model["update_count"] = self._transition_model.get("update_count", 0) + 1
        self._save_model("transitions", self._transition_model)

        return LearningUpdate(
            update_type="transition_model",
            pattern_name=key,
            old_value=old_count,
            new_value=old_count + 1,
            confidence_delta=new_confidence - old_conf,
            source=outcome.prediction_id
        )

    def _update_object_model(
        self,
        prediction: Prediction,
        outcome: PredictionOutcome
    ) -> LearningUpdate:
        """Update object appearance model."""
        current_scene = prediction.context.get("current_scene", "unknown")
        obj = prediction.predicted_outcome

        patterns = self._object_model.setdefault("patterns", {})
        scene_objects = patterns.setdefault(current_scene, {})

        if outcome.correct:
            old_count = scene_objects.get(obj, 0)
            scene_objects[obj] = old_count + 1
            self._object_model["update_count"] = self._object_model.get("update_count", 0) + 1
            self._save_model("objects", self._object_model)

            return LearningUpdate(
                update_type="object_model",
                pattern_name=f"{current_scene}:{obj}",
                old_value=old_count,
                new_value=old_count + 1,
                confidence_delta=0.1,
                source=outcome.prediction_id
            )

        return None

    def _update_error_model(
        self,
        prediction: Prediction,
        outcome: PredictionOutcome
    ) -> LearningUpdate:
        """Update error occurrence model."""
        current_scene = prediction.context.get("current_scene", "unknown")
        had_error = outcome.actual == "error"

        patterns = self._error_model.setdefault("patterns", {})
        counts = self._error_model.setdefault("counts", {})

        # Update error rate
        total_key = f"{current_scene}_total"
        error_key = f"{current_scene}_errors"

        counts[total_key] = counts.get(total_key, 0) + 1
        if had_error:
            counts[error_key] = counts.get(error_key, 0) + 1

        old_rate = patterns.get(current_scene, 0)
        new_rate = counts.get(error_key, 0) / counts[total_key]
        patterns[current_scene] = new_rate

        self._error_model["update_count"] = self._error_model.get("update_count", 0) + 1
        self._save_model("errors", self._error_model)

        return LearningUpdate(
            update_type="error_model",
            pattern_name=current_scene,
            old_value=old_rate,
            new_value=new_rate,
            confidence_delta=new_rate - old_rate,
            source=outcome.prediction_id
        )

    def _update_action_model(
        self,
        prediction: Prediction,
        outcome: PredictionOutcome
    ) -> LearningUpdate:
        """Update action outcome model."""
        current_scene = prediction.context.get("current_scene", "unknown")
        action = prediction.context.get("action", "unknown")
        actual_outcome = outcome.actual

        patterns = self._action_model.setdefault("patterns", {})
        key = f"{current_scene}:{action}"

        action_outcomes = patterns.setdefault(key, {})
        old_count = action_outcomes.get(actual_outcome, 0)
        action_outcomes[actual_outcome] = old_count + 1

        self._action_model["update_count"] = self._action_model.get("update_count", 0) + 1
        self._save_model("actions", self._action_model)

        return LearningUpdate(
            update_type="action_model",
            pattern_name=f"{key}->{actual_outcome}",
            old_value=old_count,
            new_value=old_count + 1,
            confidence_delta=0.05,
            source=outcome.prediction_id
        )

    def _store_prediction(self, prediction: Prediction) -> None:
        """Store prediction to disk."""
        pred_path = os.path.join(self.storage_path, "predictions.jsonl")

        record = {
            "id": prediction.id,
            "type": prediction.prediction_type.value,
            "predicted": prediction.predicted_outcome,
            "confidence": prediction.confidence,
            "reasoning": prediction.reasoning,
            "timestamp": prediction.timestamp
        }

        with open(pred_path, 'a') as f:
            f.write(json.dumps(record) + '\n')

    def _store_learning_update(self, update: LearningUpdate) -> None:
        """Store learning update to disk."""
        updates_path = os.path.join(self.storage_path, "learning_updates.jsonl")

        record = {
            "update_type": update.update_type,
            "pattern_name": update.pattern_name,
            "confidence_delta": update.confidence_delta,
            "source": update.source,
            "timestamp": update.timestamp
        }

        with open(updates_path, 'a') as f:
            f.write(json.dumps(record) + '\n')

    def get_learning_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get learning summary."""
        cutoff = datetime.now() - timedelta(hours=hours)

        recent_outcomes = [
            o for o in self._outcomes
            if datetime.fromisoformat(o.timestamp) > cutoff
        ]

        recent_updates = [
            u for u in self._learning_updates
            if datetime.fromisoformat(u.timestamp) > cutoff
        ]

        correct_count = sum(1 for o in recent_outcomes if o.correct)
        accuracy = correct_count / len(recent_outcomes) if recent_outcomes else 0

        return {
            "hours": hours,
            "predictions_evaluated": len(recent_outcomes),
            "prediction_accuracy": accuracy,
            "learning_updates": len(recent_updates),
            "model_sizes": {
                "transitions": len(self._transition_model.get("patterns", {})),
                "objects": len(self._object_model.get("patterns", {})),
                "errors": len(self._error_model.get("patterns", {})),
                "actions": len(self._action_model.get("patterns", {}))
            },
            "total_updates": {
                "transitions": self._transition_model.get("update_count", 0),
                "objects": self._object_model.get("update_count", 0),
                "errors": self._error_model.get("update_count", 0),
                "actions": self._action_model.get("update_count", 0)
            },
            "pending_predictions": len(self._pending_predictions),
            "timestamp": datetime.now().isoformat()
        }


# MCP Tool Functions
async def visual_learning_observe(observation: Dict) -> Dict:
    """MCP Tool: Observe visual state for learning."""
    loop = VisualLearningLoop()
    return await loop.observe(observation)


async def visual_learning_predict(
    current_state: Dict,
    prediction_type: str,
    context: Dict = None
) -> Dict:
    """MCP Tool: Make visual prediction."""
    loop = VisualLearningLoop()

    type_map = {
        "scene_transition": PredictionType.SCENE_TRANSITION,
        "object_appearance": PredictionType.OBJECT_APPEARANCE,
        "action_outcome": PredictionType.ACTION_OUTCOME,
        "error_occurrence": PredictionType.ERROR_OCCURRENCE
    }

    pred_type = type_map.get(prediction_type, PredictionType.SCENE_TRANSITION)
    prediction = await loop.predict(current_state, pred_type, context or {})

    return {
        "prediction_id": prediction.id,
        "predicted": prediction.predicted_outcome,
        "confidence": prediction.confidence,
        "reasoning": prediction.reasoning
    }


def get_visual_learning_summary(hours: int = 24) -> Dict:
    """MCP Tool: Get visual learning summary."""
    loop = VisualLearningLoop()
    return loop.get_learning_summary(hours)


# CLI Entry Point
async def main():
    """Demo visual learning loop."""
    import argparse

    parser = argparse.ArgumentParser(description="Visual Learning Loop")
    parser.add_argument("--observe", action="store_true", help="Observe state")
    parser.add_argument("--predict", type=str, help="Make prediction (scene/object/error/action)")
    parser.add_argument("--summary", action="store_true", help="Show learning summary")

    args = parser.parse_args()

    loop = VisualLearningLoop()

    if args.observe:
        # Test observation
        test_state = {
            "scene_type": "terminal",
            "objects": ["code", "terminal", "cursor"],
            "description": "Terminal window with code editor",
            "confidence": 0.9
        }

        result = await loop.observe(test_state)
        print(json.dumps(result, indent=2))

    elif args.predict:
        type_map = {
            "scene": PredictionType.SCENE_TRANSITION,
            "object": PredictionType.OBJECT_APPEARANCE,
            "error": PredictionType.ERROR_OCCURRENCE,
            "action": PredictionType.ACTION_OUTCOME
        }

        current = {
            "scene_type": "terminal",
            "objects": ["code"],
            "confidence": 0.9
        }

        pred = await loop.predict(
            current,
            type_map.get(args.predict, PredictionType.SCENE_TRANSITION),
            {"action": "save_file"}
        )

        print(f"Prediction: {pred.predicted_outcome}")
        print(f"Confidence: {pred.confidence:.0%}")
        print(f"Reasoning: {pred.reasoning}")

    elif args.summary:
        summary = loop.get_learning_summary()
        print(json.dumps(summary, indent=2))

    else:
        print("Use --observe, --predict <type>, or --summary")


if __name__ == "__main__":
    asyncio.run(main())

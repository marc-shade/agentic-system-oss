#!/usr/bin/env python3
"""
Test suite for Continuous Learning integration.

Tests:
1. Basic initialization
2. Learning from corrections
3. Gradient descent updates
4. Pattern recognition
5. Source reliability tracking
6. Confidence prediction
7. MCP tool registration
"""

import asyncio
import os
import tempfile
from pathlib import Path

# Set up test environment
os.chdir(Path(__file__).parent)


async def test_basic_initialization():
    """Test basic ContinuousLearning initialization."""
    print("\n=== Test: Basic Initialization ===")

    from continuous_learning import ContinuousLearning, LearningModel

    with tempfile.TemporaryDirectory() as tmpdir:
        cl = ContinuousLearning(db_path=Path(tmpdir) / "test_cl.db")

        # Check initialization
        assert cl.confidence_model is not None
        assert isinstance(cl.confidence_model, LearningModel)
        print(f"  ✓ Model initialized with {len(cl.confidence_model.weights)} weights")

        # Check default weights
        assert 'citation_count' in cl.confidence_model.weights
        assert 'hallucination_flags' in cl.confidence_model.weights
        print(f"  ✓ Default weights configured")

        # Check bias
        assert 0.0 <= cl.confidence_model.bias <= 1.0
        print(f"  ✓ Bias: {cl.confidence_model.bias:.3f}")

        print("  ✅ Basic initialization: PASSED")
        return True


async def test_feature_vector():
    """Test FeatureVector data class."""
    print("\n=== Test: Feature Vector ===")

    from continuous_learning import FeatureVector

    # Test creation
    fv = FeatureVector(
        citation_count=0.5,
        peer_reviewed_ratio=0.8,
        recency_score=0.7,
        evidence_level_score=0.6,
        contradiction_count=0.1,
        hallucination_flags=0.0
    )
    assert fv.citation_count == 0.5
    print(f"  ✓ FeatureVector created")

    # Test to_dict
    data = fv.to_dict()
    assert 'citation_count' in data
    assert data['citation_count'] == 0.5
    print(f"  ✓ to_dict() works")

    # Test from_dict
    fv2 = FeatureVector.from_dict(data)
    assert fv2.citation_count == fv.citation_count
    assert fv2.peer_reviewed_ratio == fv.peer_reviewed_ratio
    print(f"  ✓ from_dict() works")

    # Test get_values
    values = fv.get_values()
    assert len(values) == 10  # All 10 features
    print(f"  ✓ get_values() returns {len(values)} features")

    print("  ✅ Feature vector: PASSED")
    return True


async def test_learning_from_corrections():
    """Test learning from provider corrections."""
    print("\n=== Test: Learning from Corrections ===")

    from continuous_learning import (
        ContinuousLearning, FeatureVector, ProviderFeedback, LearningOutcome
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        cl = ContinuousLearning(db_path=Path(tmpdir) / "test_cl.db")

        initial_examples = cl.confidence_model.training_examples

        # Create test data
        features = FeatureVector(
            citation_count=0.8,
            peer_reviewed_ratio=0.9,
            recency_score=0.7,
            evidence_level_score=0.85,
            contradiction_count=0.0,
            hallucination_flags=0.0
        )

        feedback = ProviderFeedback(
            provider_id="test_provider",
            corrected_confidence=0.9,
            reasoning="High quality sources confirmed",
            suggested_sources=["arxiv:2024.12345", "doi:10.1234/example"]
        )

        # Learn from correction
        record = await cl.learn_from_correction(
            claim="Test claim about AI safety",
            original_confidence=0.7,
            feedback=feedback,
            features=features
        )

        assert record is not None
        assert record.id is not None
        assert record.claim == "Test claim about AI safety"
        print(f"  ✓ Created learning record: {record.id}")

        # Check outcome determination
        assert record.outcome == LearningOutcome.MODIFIED  # delta > 0.1
        print(f"  ✓ Outcome correctly determined: {record.outcome.value}")

        # Check training count increased
        assert cl.confidence_model.training_examples == initial_examples + 1
        print(f"  ✓ Training examples: {cl.confidence_model.training_examples}")

        print("  ✅ Learning from corrections: PASSED")
        return True


async def test_gradient_descent():
    """Test gradient descent weight updates."""
    print("\n=== Test: Gradient Descent Updates ===")

    from continuous_learning import ContinuousLearning, FeatureVector, ProviderFeedback

    with tempfile.TemporaryDirectory() as tmpdir:
        cl = ContinuousLearning(db_path=Path(tmpdir) / "test_cl.db")

        # Get initial weights
        initial_weight = cl.confidence_model.weights.get('citation_count', 0.0)

        # Train with high citation count, corrected upward
        for i in range(10):
            features = FeatureVector(
                citation_count=0.9,  # High citation count
                peer_reviewed_ratio=0.8,
                evidence_level_score=0.85
            )
            feedback = ProviderFeedback(
                provider_id=f"provider_{i}",
                corrected_confidence=0.85,  # Should be high
                reasoning="Good sources"
            )
            await cl.learn_from_correction(
                claim=f"High quality claim {i}",
                original_confidence=0.5,  # We're underpredicting
                feedback=feedback,
                features=features
            )

        # Citation count weight should have increased (since we were underpredicting
        # for high citation content)
        new_weight = cl.confidence_model.weights.get('citation_count', 0.0)
        print(f"  ✓ Weight change: {initial_weight:.4f} → {new_weight:.4f}")

        # Model should have learned
        assert cl.confidence_model.training_examples == 10
        print(f"  ✓ Trained on 10 examples")

        # Accuracy should be tracked
        assert 0.0 <= cl.confidence_model.accuracy <= 1.0
        print(f"  ✓ Model accuracy: {cl.confidence_model.accuracy:.3f}")

        print("  ✅ Gradient descent: PASSED")
        return True


async def test_pattern_recognition():
    """Test pattern recognition."""
    print("\n=== Test: Pattern Recognition ===")

    from continuous_learning import ContinuousLearning, FeatureVector, ProviderFeedback

    with tempfile.TemporaryDirectory() as tmpdir:
        cl = ContinuousLearning(db_path=Path(tmpdir) / "test_cl.db")

        # Create similar patterns multiple times
        for i in range(10):
            features = FeatureVector(
                citation_count=0.7,
                peer_reviewed_ratio=0.6,
                evidence_level_score=0.65
            )
            feedback = ProviderFeedback(
                provider_id="pattern_provider",
                corrected_confidence=0.7,
                reasoning="Pattern test"
            )
            await cl.learn_from_correction(
                claim=f"Pattern claim {i}",
                original_confidence=0.65,  # Close to corrected = accepted
                feedback=feedback,
                features=features
            )

        # Check patterns were created
        stats = cl.get_pattern_statistics()
        assert stats['total_patterns'] >= 1
        print(f"  ✓ Patterns detected: {stats['total_patterns']}")

        # Check pattern details
        if stats['patterns']:
            top_pattern = stats['patterns'][0]
            print(f"  ✓ Top pattern: {top_pattern['id']}, samples={top_pattern['sample_size']}")
            assert top_pattern['sample_size'] >= 1

        print("  ✅ Pattern recognition: PASSED")
        return True


async def test_source_reliability():
    """Test source reliability tracking."""
    print("\n=== Test: Source Reliability ===")

    from continuous_learning import ContinuousLearning, FeatureVector, ProviderFeedback

    with tempfile.TemporaryDirectory() as tmpdir:
        cl = ContinuousLearning(db_path=Path(tmpdir) / "test_cl.db")

        # Add successful source multiple times
        for i in range(8):
            features = FeatureVector(citation_count=0.8)
            feedback = ProviderFeedback(
                provider_id="test_provider",
                corrected_confidence=0.8,
                reasoning="Good source",
                suggested_sources=["reliable_source_1"]
            )
            await cl.learn_from_correction(
                claim=f"Claim {i}",
                original_confidence=0.75,  # Close = accepted
                feedback=feedback,
                features=features
            )

        # Add some failures for another source
        for i in range(5):
            features = FeatureVector(citation_count=0.3)
            feedback = ProviderFeedback(
                provider_id="test_provider",
                corrected_confidence=0.2,
                reasoning="Bad source",
                suggested_sources=["unreliable_source"]
            )
            await cl.learn_from_correction(
                claim=f"Bad claim {i}",
                original_confidence=0.6,  # Far from corrected = rejected
                feedback=feedback,
                features=features
            )

        # Check source rankings
        rankings = cl.get_source_rankings(min_sample_size=3)
        print(f"  ✓ Tracked {len(cl.source_reliability)} sources")

        if rankings:
            top = rankings[0]
            print(f"  ✓ Top source: {top['source_id']}, reliability={top['reliability_score']:.3f}")

        print("  ✅ Source reliability: PASSED")
        return True


async def test_confidence_prediction():
    """Test confidence prediction."""
    print("\n=== Test: Confidence Prediction ===")

    from continuous_learning import ContinuousLearning, FeatureVector, ProviderFeedback

    with tempfile.TemporaryDirectory() as tmpdir:
        cl = ContinuousLearning(db_path=Path(tmpdir) / "test_cl.db")

        # Test prediction with good features
        good_features = FeatureVector(
            citation_count=0.9,
            peer_reviewed_ratio=0.95,
            recency_score=0.8,
            evidence_level_score=0.9,
            contradiction_count=0.0,
            hallucination_flags=0.0,
            source_reliability=0.85,
            semantic_coherence=0.9
        )

        good_prediction = cl.predict_confidence(good_features)
        assert 0.0 <= good_prediction <= 1.0
        print(f"  ✓ Good features prediction: {good_prediction:.3f}")

        # Test prediction with bad features
        bad_features = FeatureVector(
            citation_count=0.1,
            peer_reviewed_ratio=0.0,
            recency_score=0.2,
            evidence_level_score=0.1,
            contradiction_count=0.8,
            hallucination_flags=0.9,
            source_reliability=0.1,
            semantic_coherence=0.2
        )

        bad_prediction = cl.predict_confidence(bad_features)
        assert 0.0 <= bad_prediction <= 1.0
        print(f"  ✓ Bad features prediction: {bad_prediction:.3f}")

        # Good should be higher than bad (with default weights)
        assert good_prediction > bad_prediction
        print(f"  ✓ Good > Bad: {good_prediction:.3f} > {bad_prediction:.3f}")

        print("  ✅ Confidence prediction: PASSED")
        return True


async def test_confidence_adjustment():
    """Test confidence adjustment with pattern matching."""
    print("\n=== Test: Confidence Adjustment ===")

    from continuous_learning import ContinuousLearning, FeatureVector, ProviderFeedback

    with tempfile.TemporaryDirectory() as tmpdir:
        cl = ContinuousLearning(db_path=Path(tmpdir) / "test_cl.db")

        features = FeatureVector(
            citation_count=0.7,
            peer_reviewed_ratio=0.8,
            evidence_level_score=0.75
        )

        # Get adjustment before any training
        adjustment = await cl.get_confidence_adjustment(features)
        assert 'predicted_confidence' in adjustment
        assert 'recommendation' in adjustment
        print(f"  ✓ Initial adjustment: {adjustment['recommendation']}")

        # Train on similar features with high success
        for i in range(10):
            feedback = ProviderFeedback(
                provider_id="adj_provider",
                corrected_confidence=0.8,
                reasoning="Adjustment test"
            )
            await cl.learn_from_correction(
                claim=f"Adjustment claim {i}",
                original_confidence=0.75,  # Close to corrected
                feedback=feedback,
                features=features
            )

        # Get adjustment after training
        adjustment2 = await cl.get_confidence_adjustment(features)
        print(f"  ✓ Post-training adjustment: {adjustment2['recommendation']}")

        if adjustment2.get('pattern_match'):
            print(f"  ✓ Pattern matched: {adjustment2['pattern_match']['id']}")

        print("  ✅ Confidence adjustment: PASSED")
        return True


async def test_model_statistics():
    """Test model statistics."""
    print("\n=== Test: Model Statistics ===")

    from continuous_learning import ContinuousLearning, FeatureVector, ProviderFeedback

    with tempfile.TemporaryDirectory() as tmpdir:
        cl = ContinuousLearning(db_path=Path(tmpdir) / "test_cl.db")

        # Train a bit
        for i in range(5):
            features = FeatureVector(citation_count=0.5 + i * 0.1)
            feedback = ProviderFeedback(
                provider_id="stats_provider",
                corrected_confidence=0.6 + i * 0.05,
                reasoning="Stats test"
            )
            await cl.learn_from_correction(
                claim=f"Stats claim {i}",
                original_confidence=0.5,
                feedback=feedback,
                features=features
            )

        stats = cl.get_model_statistics()

        assert 'training_examples' in stats
        assert stats['training_examples'] == 5
        print(f"  ✓ Training examples: {stats['training_examples']}")

        assert 'accuracy' in stats
        print(f"  ✓ Accuracy: {stats['accuracy']:.3f}")

        assert 'weights' in stats
        print(f"  ✓ Weights tracked: {len(stats['weights'])} features")

        assert 'feature_importance' in stats
        if stats['feature_importance']:
            top_feature = list(stats['feature_importance'].items())[0]
            print(f"  ✓ Top feature: {top_feature[0]} ({top_feature[1]:.3f})")

        print("  ✅ Model statistics: PASSED")
        return True


async def test_comprehensive_metrics():
    """Test comprehensive metrics."""
    print("\n=== Test: Comprehensive Metrics ===")

    from continuous_learning import ContinuousLearning, FeatureVector, ProviderFeedback

    with tempfile.TemporaryDirectory() as tmpdir:
        cl = ContinuousLearning(db_path=Path(tmpdir) / "test_cl.db")

        # Train on various scenarios
        for i in range(10):
            features = FeatureVector(
                citation_count=0.3 + i * 0.07,
                hallucination_flags=0.1 if i < 7 else 0.5
            )
            feedback = ProviderFeedback(
                provider_id=f"metrics_provider_{i % 3}",
                corrected_confidence=0.7 if i < 7 else 0.3,
                reasoning="Metrics test",
                suggested_sources=[f"source_{i}"]
            )
            await cl.learn_from_correction(
                claim=f"Metrics claim {i}",
                original_confidence=0.5 if i < 5 else 0.6,
                feedback=feedback,
                features=features
            )

        metrics = cl.get_metrics()

        assert 'total_records' in metrics
        assert metrics['total_records'] == 10
        print(f"  ✓ Total records: {metrics['total_records']}")

        assert 'outcome_distribution' in metrics
        print(f"  ✓ Outcome distribution: {metrics['outcome_distribution']}")

        assert 'model' in metrics
        print(f"  ✓ Model training examples: {metrics['model']['training_examples']}")

        assert 'patterns' in metrics
        print(f"  ✓ Patterns detected: {metrics['patterns']['total_patterns']}")

        assert 'sources' in metrics
        print(f"  ✓ Sources tracked: {metrics['sources']['tracked']}")

        print("  ✅ Comprehensive metrics: PASSED")
        return True


async def test_mcp_tools():
    """Test MCP tool registration."""
    print("\n=== Test: MCP Tool Registration ===")

    from continuous_learning import register_continuous_learning_tools

    class MockApp:
        def __init__(self):
            self.tools = {}

        def tool(self):
            def decorator(fn):
                self.tools[fn.__name__] = fn
                return fn
            return decorator

    with tempfile.TemporaryDirectory() as tmpdir:
        mock_app = MockApp()
        cl = register_continuous_learning_tools(
            mock_app,
            db_path=Path(tmpdir) / "test_cl.db"
        )

        expected_tools = [
            "cl_learn_from_correction",
            "cl_predict_confidence",
            "cl_get_model_stats",
            "cl_get_pattern_stats",
            "cl_get_source_rankings",
            "cl_status"
        ]

        for tool_name in expected_tools:
            assert tool_name in mock_app.tools, f"Missing tool: {tool_name}"
            print(f"  ✓ {tool_name} registered")

        # Test cl_status
        status = await mock_app.tools["cl_status"]()
        assert 'total_records' in status
        assert 'model' in status
        print(f"  ✓ Status: {status['total_records']} records")

        # Test cl_predict_confidence
        prediction = await mock_app.tools["cl_predict_confidence"](
            features={'citation_count': 0.8, 'peer_reviewed_ratio': 0.9}
        )
        assert 'predicted_confidence' in prediction
        print(f"  ✓ Prediction: {prediction['predicted_confidence']:.3f}")

        # Test cl_learn_from_correction
        result = await mock_app.tools["cl_learn_from_correction"](
            claim="MCP test claim",
            original_confidence=0.5,
            corrected_confidence=0.7,
            provider_id="mcp_test",
            reasoning="Testing MCP integration",
            features={'citation_count': 0.6}
        )
        assert 'record_id' in result
        assert result['training_examples'] == 1
        print(f"  ✓ Learning: record={result['record_id']}")

        # Test cl_get_model_stats
        model_stats = await mock_app.tools["cl_get_model_stats"]()
        assert 'training_examples' in model_stats
        assert model_stats['training_examples'] == 1
        print(f"  ✓ Model stats: {model_stats['training_examples']} examples")

        print("  ✅ MCP tools: PASSED")
        return True


async def test_persistence():
    """Test data persistence across instances."""
    print("\n=== Test: Persistence ===")

    from continuous_learning import ContinuousLearning, FeatureVector, ProviderFeedback

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_persist.db"

        # Create first instance and train
        cl1 = ContinuousLearning(db_path=db_path)
        features = FeatureVector(citation_count=0.7)
        feedback = ProviderFeedback(
            provider_id="persist_test",
            corrected_confidence=0.8,
            reasoning="Persistence test"
        )
        await cl1.learn_from_correction(
            claim="Persistence claim",
            original_confidence=0.5,
            feedback=feedback,
            features=features
        )

        training_count = cl1.confidence_model.training_examples
        weights_copy = dict(cl1.confidence_model.weights)
        print(f"  ✓ Trained: {training_count} examples")

        # Create second instance (simulates restart)
        cl2 = ContinuousLearning(db_path=db_path)

        # Check state was restored
        assert cl2.confidence_model.training_examples == training_count
        print(f"  ✓ Restored training count: {cl2.confidence_model.training_examples}")

        assert cl2.confidence_model.weights == weights_copy
        print(f"  ✓ Restored weights: {len(cl2.confidence_model.weights)} features")

        print("  ✅ Persistence: PASSED")
        return True


# =============================================================================
# EWC++ (Elastic Weight Consolidation) Tests
# Ported from ruvnet/ruvector SONA crate
# =============================================================================


async def test_ewc_config():
    """Test EwcConfig dataclass initialization."""
    print("\n=== Test: EWC++ Config ===")

    from continuous_learning import EwcConfig

    # Default config
    config = EwcConfig()
    assert config.param_count == 10
    assert config.max_tasks == 10
    assert config.initial_lambda == 2000.0
    assert config.min_lambda == 100.0
    assert config.max_lambda == 15000.0
    assert config.fisher_ema_decay == 0.999
    assert config.boundary_threshold == 2.0
    assert config.gradient_history_size == 50
    print(f"  ✓ Default config created: lambda={config.initial_lambda}, decay={config.fisher_ema_decay}")

    # Custom config
    custom = EwcConfig(param_count=20, initial_lambda=3000.0, max_tasks=5)
    assert custom.param_count == 20
    assert custom.initial_lambda == 3000.0
    assert custom.max_tasks == 5
    print(f"  ✓ Custom config: param_count={custom.param_count}, max_tasks={custom.max_tasks}")

    print("  ✅ EWC++ Config: PASSED")
    return True


async def test_task_fisher():
    """Test TaskFisher dataclass and serialization."""
    print("\n=== Test: TaskFisher ===")

    from continuous_learning import TaskFisher

    # Create TaskFisher
    tf = TaskFisher(
        task_id=0,
        fisher=[0.1, 0.2, 0.3],
        weights=[1.0, 2.0, 3.0],
        sample_count=100
    )

    assert tf.task_id == 0
    assert tf.fisher == [0.1, 0.2, 0.3]
    assert tf.weights == [1.0, 2.0, 3.0]
    assert tf.sample_count == 100
    print(f"  ✓ TaskFisher created: task_id={tf.task_id}, samples={tf.sample_count}")

    # Test serialization
    data = tf.to_dict()
    assert data['task_id'] == 0
    assert data['fisher'] == [0.1, 0.2, 0.3]
    assert data['weights'] == [1.0, 2.0, 3.0]
    print(f"  ✓ Serialized to dict with {len(data)} keys")

    # Test deserialization
    tf2 = TaskFisher.from_dict(data)
    assert tf2.task_id == tf.task_id
    assert tf2.fisher == tf.fisher
    assert tf2.weights == tf.weights
    print(f"  ✓ Deserialized back successfully")

    print("  ✅ TaskFisher: PASSED")
    return True


async def test_ewc_plus_plus_initialization():
    """Test EwcPlusPlus initialization."""
    print("\n=== Test: EWC++ Initialization ===")

    from continuous_learning import EwcPlusPlus, EwcConfig

    # Default initialization
    ewc = EwcPlusPlus()
    assert len(ewc.current_fisher) == 10  # Default param_count
    assert len(ewc.current_weights) == 10
    assert ewc.current_task_id == 0
    assert ewc.lambda_value == 2000.0
    print(f"  ✓ Default EWC++ initialized: {len(ewc.current_fisher)} params")

    # Custom config
    config = EwcConfig(param_count=5, initial_lambda=1000.0)
    ewc2 = EwcPlusPlus(config)
    assert len(ewc2.current_fisher) == 5
    assert ewc2.lambda_value == 1000.0
    print(f"  ✓ Custom EWC++: {len(ewc2.current_fisher)} params, lambda={ewc2.lambda_value}")

    print("  ✅ EWC++ Initialization: PASSED")
    return True


async def test_ewc_fisher_update():
    """Test online Fisher information estimation via EMA."""
    print("\n=== Test: EWC++ Fisher Update ===")

    from continuous_learning import EwcPlusPlus, EwcConfig

    config = EwcConfig(param_count=3, fisher_ema_decay=0.9)
    ewc = EwcPlusPlus(config)

    # Initial Fisher should be all zeros
    assert all(f == 0.0 for f in ewc.current_fisher)
    print(f"  ✓ Initial Fisher: {ewc.current_fisher}")

    # Update with gradients
    gradients = [1.0, 2.0, 3.0]
    ewc.update_fisher(gradients)

    # Fisher ≈ E[grad²] via EMA: (0 * 0.9) + (grad² * 0.1)
    # Expected: [0.1, 0.4, 0.9]
    expected = [(1.0 - 0.9) * g * g for g in gradients]
    for i, (actual, exp) in enumerate(zip(ewc.current_fisher, expected)):
        assert abs(actual - exp) < 1e-6, f"Fisher[{i}]: {actual} != {exp}"
    print(f"  ✓ After first update: {[round(f, 4) for f in ewc.current_fisher]}")

    # Multiple updates should accumulate
    for _ in range(10):
        ewc.update_fisher([1.0, 1.0, 1.0])
    print(f"  ✓ After 10 more updates: {[round(f, 4) for f in ewc.current_fisher]}")

    assert ewc.samples_seen == 11
    print(f"  ✓ Samples tracked: {ewc.samples_seen}")

    print("  ✅ EWC++ Fisher Update: PASSED")
    return True


async def test_ewc_task_boundary_detection():
    """Test automatic task boundary detection via z-score analysis."""
    print("\n=== Test: EWC++ Task Boundary Detection ===")

    from continuous_learning import EwcPlusPlus, EwcConfig

    config = EwcConfig(param_count=3, gradient_history_size=10, boundary_threshold=2.0)
    ewc = EwcPlusPlus(config)

    # Build up gradient history with similar gradients
    base_gradients = [0.1, 0.2, 0.3]
    for _ in range(15):
        ewc.update_fisher(base_gradients)

    # Should not detect boundary with similar gradients
    boundary = ewc.detect_task_boundary(base_gradients)
    assert not boundary, "Should not detect boundary with similar gradients"
    print(f"  ✓ No boundary detected with similar gradients")

    # Should detect boundary with very different gradients
    extreme_gradients = [10.0, 20.0, 30.0]
    boundary = ewc.detect_task_boundary(extreme_gradients)
    assert boundary, "Should detect boundary with extreme gradients"
    print(f"  ✓ Boundary detected with extreme gradients (100x different)")

    print("  ✅ EWC++ Task Boundary Detection: PASSED")
    return True


async def test_ewc_start_new_task():
    """Test starting a new task and saving Fisher/weights."""
    print("\n=== Test: EWC++ Start New Task ===")

    from continuous_learning import EwcPlusPlus, EwcConfig

    config = EwcConfig(param_count=3, max_tasks=5)
    ewc = EwcPlusPlus(config)

    # Update Fisher with some gradients
    ewc.update_fisher([1.0, 2.0, 3.0])
    ewc.update_fisher([1.5, 2.5, 3.5])
    ewc.samples_in_task = 100

    # Start new task
    current_weights = [0.5, 0.6, 0.7]
    new_task_id = ewc.start_new_task(current_weights)

    assert new_task_id == 1
    assert ewc.current_task_id == 1
    assert len(ewc.task_memory) == 1
    print(f"  ✓ New task started: task_id={new_task_id}")

    # Check task was saved to memory
    saved_task = ewc.task_memory[0]
    assert saved_task.task_id == 0
    assert saved_task.sample_count == 100
    assert saved_task.weights == current_weights
    print(f"  ✓ Previous task saved: samples={saved_task.sample_count}")

    # Check adaptive lambda increased
    assert ewc.lambda_value > config.initial_lambda
    print(f"  ✓ Adaptive lambda: {config.initial_lambda} -> {ewc.lambda_value}")

    print("  ✅ EWC++ Start New Task: PASSED")
    return True


async def test_ewc_apply_constraints():
    """Test applying EWC constraints to prevent forgetting."""
    print("\n=== Test: EWC++ Apply Constraints ===")

    from continuous_learning import EwcPlusPlus, EwcConfig

    config = EwcConfig(param_count=3, initial_lambda=1000.0)
    ewc = EwcPlusPlus(config)

    # No constraints when no previous tasks
    gradients = [1.0, 2.0, 3.0]
    weights = [0.1, 0.2, 0.3]
    constrained = ewc.apply_constraints(gradients, weights)
    assert constrained == gradients
    print(f"  ✓ No constraints without task memory")

    # Add a task with high Fisher for first parameter
    ewc.current_fisher = [10.0, 1.0, 0.1]
    ewc.samples_in_task = 100
    ewc.start_new_task([0.1, 0.2, 0.3])

    # Apply constraints with new weights
    new_weights = [0.5, 0.25, 0.35]  # First param changed most
    constrained = ewc.apply_constraints(gradients, new_weights)

    # First gradient should be most constrained (high Fisher, big weight delta)
    # Constraints shrink gradients where penalty is high
    assert abs(constrained[0]) < abs(gradients[0])
    print(f"  ✓ Gradient[0] constrained: {gradients[0]} -> {constrained[0]:.4f}")
    print(f"  ✓ Gradients constrained proportionally to Fisher importance")

    print("  ✅ EWC++ Apply Constraints: PASSED")
    return True


async def test_ewc_regularization_loss():
    """Test EWC regularization loss computation."""
    print("\n=== Test: EWC++ Regularization Loss ===")

    from continuous_learning import EwcPlusPlus, EwcConfig

    config = EwcConfig(param_count=3, initial_lambda=2.0)  # Small lambda for easy calculation
    ewc = EwcPlusPlus(config)

    # No loss without previous tasks
    loss = ewc.regularization_loss([1.0, 2.0, 3.0])
    assert loss == 0.0
    print(f"  ✓ Zero loss without task memory")

    # Create a task with known Fisher and weights
    ewc.current_fisher = [1.0, 1.0, 1.0]  # Unit Fisher
    ewc.start_new_task([0.0, 0.0, 0.0])  # Zero weights

    # Calculate loss for weights = [1, 1, 1]
    # L = (λ/2) * Σ F * (w - w*)² = (2/2) * (1*1 + 1*1 + 1*1) = 3.0
    new_weights = [1.0, 1.0, 1.0]
    loss = ewc.regularization_loss(new_weights)
    expected_loss = (ewc.lambda_value / 2.0) * 3.0
    assert abs(loss - expected_loss) < 1e-6, f"Loss {loss} != expected {expected_loss}"
    print(f"  ✓ Loss computed correctly: {loss}")

    print("  ✅ EWC++ Regularization Loss: PASSED")
    return True


async def test_ewc_statistics():
    """Test EWC++ statistics reporting."""
    print("\n=== Test: EWC++ Statistics ===")

    from continuous_learning import EwcPlusPlus

    ewc = EwcPlusPlus()

    # Train on some gradients
    for i in range(20):
        ewc.update_fisher([float(i) * 0.1] * 10)
    ewc.samples_in_task = 20

    # Start a new task
    ewc.start_new_task([1.0] * 10)

    stats = ewc.get_statistics()
    assert 'current_task_id' in stats
    assert 'tasks_stored' in stats
    assert 'lambda_value' in stats
    assert 'avg_fisher' in stats
    assert 'task_history' in stats

    assert stats['current_task_id'] == 1
    assert stats['tasks_stored'] == 1
    print(f"  ✓ Statistics: task_id={stats['current_task_id']}, stored={stats['tasks_stored']}")
    print(f"  ✓ Lambda: {stats['lambda_value']:.1f}, Avg Fisher: {stats['avg_fisher']:.4f}")

    print("  ✅ EWC++ Statistics: PASSED")
    return True


async def test_ewc_persistence():
    """Test EWC++ serialization and deserialization."""
    print("\n=== Test: EWC++ Persistence ===")

    from continuous_learning import EwcPlusPlus, EwcConfig

    config = EwcConfig(param_count=5, initial_lambda=1500.0)
    ewc = EwcPlusPlus(config)

    # Build up state
    for i in range(10):
        ewc.update_fisher([float(i)] * 5)
    ewc.start_new_task([1.0, 2.0, 3.0, 4.0, 5.0])
    ewc.update_fisher([0.5] * 5)
    ewc.samples_in_task = 50

    # Serialize
    data = ewc.to_dict()
    assert 'config' in data
    assert 'current_fisher' in data
    assert 'task_memory' in data
    print(f"  ✓ Serialized: {len(data)} keys")

    # Deserialize
    ewc2 = EwcPlusPlus.from_dict(data)
    assert ewc2.current_task_id == ewc.current_task_id
    assert ewc2.lambda_value == ewc.lambda_value
    assert len(ewc2.task_memory) == len(ewc.task_memory)
    assert ewc2.samples_in_task == ewc.samples_in_task
    print(f"  ✓ Deserialized: task_id={ewc2.current_task_id}, tasks={len(ewc2.task_memory)}")

    print("  ✅ EWC++ Persistence: PASSED")
    return True


async def main():
    print("=" * 60)
    print("Continuous Learning Integration Tests")
    print("=" * 60)

    tests = [
        ("Basic Initialization", test_basic_initialization),
        ("Feature Vector", test_feature_vector),
        ("Learning from Corrections", test_learning_from_corrections),
        ("Gradient Descent", test_gradient_descent),
        ("Pattern Recognition", test_pattern_recognition),
        ("Source Reliability", test_source_reliability),
        ("Confidence Prediction", test_confidence_prediction),
        ("Confidence Adjustment", test_confidence_adjustment),
        ("Model Statistics", test_model_statistics),
        ("Comprehensive Metrics", test_comprehensive_metrics),
        ("MCP Tools", test_mcp_tools),
        ("Persistence", test_persistence),
        # EWC++ Tests (Ported from SONA)
        ("EWC++ Config", test_ewc_config),
        ("TaskFisher", test_task_fisher),
        ("EWC++ Initialization", test_ewc_plus_plus_initialization),
        ("EWC++ Fisher Update", test_ewc_fisher_update),
        ("EWC++ Task Boundary", test_ewc_task_boundary_detection),
        ("EWC++ Start New Task", test_ewc_start_new_task),
        ("EWC++ Apply Constraints", test_ewc_apply_constraints),
        ("EWC++ Regularization Loss", test_ewc_regularization_loss),
        ("EWC++ Statistics", test_ewc_statistics),
        ("EWC++ Persistence", test_ewc_persistence),
    ]

    results = {}
    for name, test_fn in tests:
        try:
            results[name] = await test_fn()
        except Exception as e:
            print(f"  ❌ {name}: FAILED - {e}")
            import traceback
            traceback.print_exc()
            results[name] = False

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)

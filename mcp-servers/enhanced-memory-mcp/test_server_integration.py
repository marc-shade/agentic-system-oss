#!/usr/bin/env python3
"""
Test server integration for Contextual Retrieval

Verifies:
1. Server imports successfully
2. Contextual Retrieval tools are registered
3. Tools are callable
4. Error handling works correctly

Author: Enhanced Memory MCP
Date: 2025-01-09
"""

import sys
import os
import asyncio
from unittest.mock import Mock, AsyncMock, patch

def test_imports():
    """Test that all imports work"""
    print("Testing imports...")

    try:
        from contextual_retrieval_tools import (
            ContextualChunk,
            QualityScore,
            ReindexingProgress,
            LLMProvider,
            OllamaProvider,
            OpenAIProvider,
            ContextQualityValidator,
            PromptBuilder,
            ContextGenerator,
            ProgressTracker,
            CheckpointManager,
            ReindexingEngine,
            register_contextual_retrieval_tools
        )
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_registration():
    """Test that tools can be registered"""
    print("\nTesting tool registration...")

    try:
        from contextual_retrieval_tools import register_contextual_retrieval_tools
        from fastmcp import FastMCP

        # Create mock app and NMF
        app = FastMCP("test-server")
        mock_nmf = Mock()

        # Register tools
        register_contextual_retrieval_tools(app, mock_nmf)

        print("✅ Tools registered successfully")
        return True
    except Exception as e:
        print(f"❌ Registration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tool_functionality():
    """Test that tools are functional"""
    print("\nTesting tool functionality...")

    try:
        from contextual_retrieval_tools import (
            ContextGenerator,
            OllamaProvider,
            ContextQualityValidator
        )

        # Create mock provider
        mock_provider = Mock(spec=OllamaProvider)
        mock_provider.generate = AsyncMock(
            return_value="This section describes the authentication system. JWT tokens are used."
        )
        mock_provider.get_model_name = Mock(return_value="llama3.2")

        # Create generator
        generator = ContextGenerator(llm_provider=mock_provider)

        # Test context generation
        result = await generator.generate_context(
            chunk="JWT tokens are used",
            document="Authentication system uses JWT tokens for session management.",
            metadata={"title": "auth_system", "type": "documentation"}
        )

        # Verify result
        assert result.original_content == "JWT tokens are used"
        assert result.contextual_prefix != ""
        assert "JWT tokens are used" in result.contextualized_content

        print("✅ Tool functionality verified")
        return True
    except Exception as e:
        print(f"❌ Tool functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_quality_validator():
    """Test quality validator"""
    print("\nTesting quality validator...")

    try:
        from contextual_retrieval_tools import ContextQualityValidator

        validator = ContextQualityValidator()

        # Test with good context
        good_context = "This section describes the authentication system's comprehensive approach to security and user session management through JWT-based tokens. The system implements secure handling with proper validation."
        chunk = "JWT tokens for auth"

        score = validator.validate(good_context, chunk)

        assert 0 <= score.overall_score <= 1.0
        assert 0 <= score.length_score <= 1.0
        assert 0 <= score.relevance_score <= 1.0
        assert 0 <= score.coherence_score <= 1.0
        assert 0 <= score.specificity_score <= 1.0

        print(f"✅ Quality validator working (score: {score.overall_score:.2f})")
        return True
    except Exception as e:
        print(f"❌ Quality validator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_checkpoint_manager():
    """Test checkpoint manager"""
    print("\nTesting checkpoint manager...")

    try:
        from contextual_retrieval_tools import CheckpointManager, ReindexingProgress
        from datetime import datetime
        import tempfile
        import os

        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            checkpoint_file = f.name

        try:
            manager = CheckpointManager(checkpoint_file=checkpoint_file)

            # Create progress
            progress = ReindexingProgress(
                total_entities=100,
                processed_entities=50,
                failed_entities=["entity_1", "entity_2"],
                start_time=datetime.now(),
                last_update_time=datetime.now(),
                estimated_completion=datetime.now(),
                status="in_progress",
                avg_time_per_entity=0.5,
                total_tokens_used=5000,
                estimated_cost=0.01
            )

            # Save checkpoint
            manager.save_checkpoint(progress)

            # Load checkpoint
            loaded = manager.load_checkpoint()

            assert loaded is not None
            assert loaded["total_entities"] == 100
            assert loaded["processed_entities"] == 50

            print("✅ Checkpoint manager working")
            return True
        finally:
            # Cleanup
            if os.path.exists(checkpoint_file):
                os.remove(checkpoint_file)
    except Exception as e:
        print(f"❌ Checkpoint manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_progress_tracker():
    """Test progress tracker"""
    print("\nTesting progress tracker...")

    try:
        from contextual_retrieval_tools import ProgressTracker

        tracker = ProgressTracker(total_entities=100)

        # Update progress
        for i in range(50):
            tracker.update(
                entity_id=f"entity_{i}",
                success=(i % 5 != 0),  # 80% success rate
                tokens=100,
                cost=0.0001
            )

        progress = tracker.get_progress()

        assert progress.total_entities == 100
        assert progress.processed_entities == 50
        assert len(progress.failed_entities) == 10  # 20% failure
        assert tracker.token_count == 5000
        assert tracker.cost == 0.005

        print("✅ Progress tracker working")
        return True
    except Exception as e:
        print(f"❌ Progress tracker test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all integration tests"""
    print("=" * 60)
    print("Contextual Retrieval Integration Tests")
    print("=" * 60)

    results = []

    # Synchronous tests
    results.append(("Imports", test_imports()))
    results.append(("Registration", test_registration()))
    results.append(("Quality Validator", test_quality_validator()))
    results.append(("Checkpoint Manager", test_checkpoint_manager()))
    results.append(("Progress Tracker", test_progress_tracker()))

    # Async tests
    results.append(("Tool Functionality", asyncio.run(test_tool_functionality())))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n🎉 All integration tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

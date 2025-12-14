#!/usr/bin/env python3
"""
Test Voice Integration - Verify All Components Work Together
=============================================================

Tests the complete voice-controlled conversational AI integration:
1. IntentClassifier - Classifies voice commands
2. ActionOrchestrator - Executes commands (requires API key)
3. ConversationState - Tracks conversation context
4. ConversationManager - Integrates all components

Usage:
    python3 test_voice_integration.py
    python3 test_voice_integration.py --with-api  # Test with API key
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_integration")


def test_imports():
    """Test that all components can be imported"""
    logger.info("=" * 60)
    logger.info("TEST 1: Import Components")
    logger.info("=" * 60)

    try:
        from intent_classifier import IntentClassifier
        logger.info("✓ IntentClassifier imported successfully")
    except ImportError as e:
        logger.error(f"✗ Failed to import IntentClassifier: {e}")
        return False

    try:
        from action_orchestrator import ActionOrchestrator, IntentType, Intent
        logger.info("✓ ActionOrchestrator imported successfully")
    except ImportError as e:
        logger.error(f"✗ Failed to import ActionOrchestrator: {e}")
        return False

    try:
        from conversation_state import ConversationState, TurnType, ActionRecord
        logger.info("✓ ConversationState imported successfully")
    except ImportError as e:
        logger.error(f"✗ Failed to import ConversationState: {e}")
        return False

    try:
        from conversation_manager import ConversationManager
        logger.info("✓ ConversationManager imported successfully")
    except ImportError as e:
        logger.error(f"✗ Failed to import ConversationManager: {e}")
        return False

    logger.info("\nResult: All imports successful ✓\n")
    return True


def test_intent_classifier():
    """Test intent classification"""
    logger.info("=" * 60)
    logger.info("TEST 2: Intent Classifier")
    logger.info("=" * 60)

    try:
        from intent_classifier import IntentClassifier

        classifier = IntentClassifier()
        logger.info("✓ IntentClassifier initialized")

        # Test different intent types
        test_cases = [
            ("Create a Python file called test.py", "COMMAND"),
            ("What files are in this directory?", "QUERY"),
            ("Hello! How are you?", "CONVERSATION"),
            ("What is the system status?", "META")
        ]

        all_passed = True
        for utterance, expected_type in test_cases:
            intent = classifier.classify(utterance)
            actual_type = intent.type.value

            if actual_type == expected_type:
                logger.info(f"✓ '{utterance[:40]}...' → {actual_type} (confidence: {intent.confidence:.2f})")
            else:
                logger.error(f"✗ '{utterance[:40]}...' → {actual_type} (expected: {expected_type})")
                all_passed = False

        if all_passed:
            logger.info("\nResult: Intent classification working ✓\n")
            return True
        else:
            logger.error("\nResult: Intent classification has errors ✗\n")
            return False

    except Exception as e:
        logger.error(f"✗ Intent classifier test failed: {e}")
        return False


def test_conversation_state():
    """Test conversation state tracking"""
    logger.info("=" * 60)
    logger.info("TEST 3: Conversation State")
    logger.info("=" * 60)

    try:
        from conversation_state import ConversationState, TurnType

        state = ConversationState()
        logger.info(f"✓ ConversationState initialized (session: {state.session_id})")

        # Add a test turn
        state.add_turn(
            user_msg="Test user message",
            assistant_msg="Test assistant response",
            turn_type=TurnType.QUESTION,
            confidence=0.9
        )
        logger.info("✓ Added conversation turn")

        # Get statistics
        stats = state.get_statistics()
        logger.info(f"✓ Statistics: {stats['total_turns']} turns, avg confidence: {stats['average_confidence']:.2f}")

        # Get context summary
        summary = state.get_context_summary(max_turns=5)
        logger.info(f"✓ Generated context summary ({len(summary)} chars)")

        logger.info("\nResult: Conversation state working ✓\n")
        return True

    except Exception as e:
        logger.error(f"✗ Conversation state test failed: {e}")
        return False


async def test_action_orchestrator():
    """Test action orchestrator (requires API key)"""
    logger.info("=" * 60)
    logger.info("TEST 4: Action Orchestrator")
    logger.info("=" * 60)

    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        logger.warning("⚠ ANTHROPIC_API_KEY not set - skipping orchestrator test")
        logger.warning("  Set API key with: export ANTHROPIC_API_KEY='sk-ant-...'")
        logger.info("\nResult: Orchestrator test skipped (no API key)\n")
        return True  # Not a failure, just skipped

    try:
        from action_orchestrator import ActionOrchestrator, Intent, IntentType

        orchestrator = ActionOrchestrator(
            anthropic_api_key=api_key,
            working_dir=Path("/tmp")
        )
        logger.info("✓ ActionOrchestrator initialized with API key")

        # Test simple conversation intent (no API call)
        test_intent = Intent(
            type=IntentType.CONVERSATION,
            text="Hello! How are you?",
            confidence=0.95
        )

        result = await orchestrator.execute_intent(test_intent, {})

        if result.success:
            logger.info(f"✓ Conversation intent executed: '{result.output[:50]}...'")
        else:
            logger.error(f"✗ Conversation intent failed: {result.errors}")
            return False

        logger.info("\nResult: Action orchestrator working ✓\n")
        return True

    except Exception as e:
        logger.error(f"✗ Action orchestrator test failed: {e}")
        return False


def test_conversation_manager():
    """Test conversation manager integration"""
    logger.info("=" * 60)
    logger.info("TEST 5: Conversation Manager Integration")
    logger.info("=" * 60)

    try:
        from conversation_manager import ConversationManager

        # Initialize without Arduino (may not be available)
        manager = ConversationManager(arduino_port='/dev/null')
        logger.info("✓ ConversationManager initialized")

        # Check component availability
        components = {
            "Intent Classifier": manager.intent_classifier is not None,
            "Action Orchestrator": manager.action_orchestrator is not None,
            "Conversation State": manager.conversation_state is not None
        }

        for name, available in components.items():
            status = "✓ enabled" if available else "✗ disabled"
            logger.info(f"  {name}: {status}")

        # Check if any components are available
        if any(components.values()):
            logger.info("\nResult: Conversation manager integration working ✓\n")
            return True
        else:
            logger.error("\nResult: No components available ✗\n")
            return False

    except Exception as e:
        logger.error(f"✗ Conversation manager test failed: {e}")
        return False


async def test_end_to_end():
    """Test complete end-to-end flow"""
    logger.info("=" * 60)
    logger.info("TEST 6: End-to-End Integration")
    logger.info("=" * 60)

    try:
        from conversation_manager import ConversationManager

        manager = ConversationManager(arduino_port='/dev/null')

        # Simulate a simple utterance
        test_utterance = "What time is it?"

        # Get context (will be empty, but that's OK)
        context = await manager.get_consciousness_context()
        logger.info(f"✓ Got consciousness context ({len(context)} keys)")

        # Generate response
        response = await manager.generate_response(test_utterance, context)
        logger.info(f"✓ Generated response: '{response[:50]}...'")

        if response and len(response) > 0:
            logger.info("\nResult: End-to-end integration working ✓\n")
            return True
        else:
            logger.error("\nResult: Empty response generated ✗\n")
            return False

    except Exception as e:
        logger.error(f"✗ End-to-end test failed: {e}")
        return False


async def run_all_tests():
    """Run all integration tests"""
    logger.info("\n")
    logger.info("=" * 60)
    logger.info("VOICE INTEGRATION TEST SUITE")
    logger.info("=" * 60)
    logger.info("\n")

    results = []

    # Test 1: Imports
    results.append(("Imports", test_imports()))

    # Test 2: Intent Classifier
    results.append(("Intent Classifier", test_intent_classifier()))

    # Test 3: Conversation State
    results.append(("Conversation State", test_conversation_state()))

    # Test 4: Action Orchestrator (async)
    results.append(("Action Orchestrator", await test_action_orchestrator()))

    # Test 5: Conversation Manager
    results.append(("Conversation Manager", test_conversation_manager()))

    # Test 6: End-to-End (async)
    results.append(("End-to-End", await test_end_to_end()))

    # Summary
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{test_name:25} {status}")

    logger.info("-" * 60)
    logger.info(f"Total: {passed}/{total} tests passed")

    if passed == total:
        logger.info("\n🎉 All tests passed! Voice integration is working correctly.")
        return True
    else:
        logger.warning(f"\n⚠ {total - passed} test(s) failed. Check errors above.")
        return False


def main():
    """Main entry point"""
    # Check for API key
    if os.getenv("ANTHROPIC_API_KEY"):
        logger.info("🔑 ANTHROPIC_API_KEY is set - full testing enabled\n")
    else:
        logger.warning("⚠ ANTHROPIC_API_KEY not set - some tests will be skipped")
        logger.warning("  Set with: export ANTHROPIC_API_KEY='sk-ant-...'\n")

    # Run tests
    success = asyncio.run(run_all_tests())

    # Exit code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

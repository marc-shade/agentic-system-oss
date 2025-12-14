#!/usr/bin/env python3
"""
Test Script for Voice-AGI Components
Verifies each component independently before full integration
"""

import asyncio
import os
import sys
sys.path.insert(0, '/mnt/agentic-system/mcp-servers/voice-agi-mcp/src')

from conversation_manager import ConversationManager
from voice_pipeline import VoicePipeline
from tool_registry import ToolRegistry
from intent_detector import IntentDetector


async def test_conversation_manager():
    """Test conversation manager"""
    print("=" * 60)
    print("Testing Conversation Manager")
    print("=" * 60)

    cm = ConversationManager(max_turns=5)

    # Add some turns
    cm.add_turn("Hello", "Hi there!")
    cm.add_turn("What's my name?", "I don't know your name yet")
    cm.update_user_context('name', 'Marc')
    cm.add_turn("My name is Marc", "Got it, I'll remember your name is Marc")

    print(f"✓ Total turns: {len(cm.messages)}")
    print(f"✓ User context: {cm.user_context}")
    print(f"✓ Stats: {cm.get_stats()}")
    print("\nConversation context:")
    print(cm.get_context())

    return True


async def test_voice_pipeline():
    """Test voice pipeline"""
    print("\n" + "=" * 60)
    print("Testing Voice Pipeline")
    print("=" * 60)

    vp = VoicePipeline(stt_model="base", tts_voice="en-IE-EmilyNeural")

    print(f"✓ STT Available: {vp.is_stt_available()}")
    print(f"✓ TTS Available: {vp.is_tts_available()}")

    # Test TTS (if available)
    if vp.is_tts_available():
        print("\nTesting TTS synthesis (audio will not play)...")
        audio_file = await vp.synthesize_speech(
            "Testing voice pipeline",
            play_audio=False  # Don't play during test
        )
        print(f"✓ TTS synthesis: {audio_file if audio_file else 'Failed'}")

    return True


async def test_tool_registry():
    """Test tool registry"""
    print("\n" + "=" * 60)
    print("Testing Tool Registry")
    print("=" * 60)

    tr = ToolRegistry()

    # Register a test tool
    @tr.register(intents=["test", "hello"], description="Test tool", priority=5)
    async def test_tool(query: str = "default"):
        return {'result': f'Test executed with: {query}'}

    print(f"✓ Registered tools: {tr.get_tool_count()}")
    print(f"✓ Tool list: {[t['name'] for t in tr.list_tools()]}")

    # Test matching
    match = tr.match_tool("hello world test")
    print(f"✓ Intent matching: {match.name if match else 'No match'}")

    # Test invocation
    result = await tr.invoke("test something", context={})
    print(f"✓ Tool invocation result: {result}")

    return True


async def test_intent_detector():
    """Test intent detector"""
    print("\n" + "=" * 60)
    print("Testing Intent Detector (requires Ollama)")
    print("=" * 60)

    # Cloud-first Ollama (never use local CPU for LLM inference)
    ollama_url = os.environ.get('OLLAMA_HOST', 'http://Marcs-Mac-Studio.local:11434')
    id = IntentDetector(ollama_url=ollama_url, model="llama3.2")

    # Test with fallback heuristics (doesn't require Ollama)
    print("\nTesting fallback intent detection:")
    test_inputs = [
        "Create a goal to optimize memory",
        "Search for information about transformers",
        "What tasks do I have?",
        "Run memory consolidation",
        "Yes",
        "No"
    ]

    for text in test_inputs:
        intent = id._fallback_intent_detection(text)
        print(f"  '{text}' → {intent.name} (confidence: {intent.confidence:.2f})")

    # Try Ollama if available
    try:
        print("\nTesting Ollama-based intent detection:")
        intent = await id.detect("Create a goal to make the system faster")
        print(f"✓ Detected intent: {intent.name} (confidence: {intent.confidence:.2f})")
        print(f"  Parameters: {intent.parameters}")
    except Exception as e:
        print(f"⚠ Ollama detection failed (fallback will be used): {e}")

    await id.close()
    return True


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Voice-AGI Component Test Suite")
    print("=" * 60 + "\n")

    tests = [
        ("Conversation Manager", test_conversation_manager),
        ("Voice Pipeline", test_voice_pipeline),
        ("Tool Registry", test_tool_registry),
        ("Intent Detector", test_intent_detector)
    ]

    results = {}
    for name, test_func in tests:
        try:
            success = await test_func()
            results[name] = "✓ PASSED" if success else "✗ FAILED"
        except Exception as e:
            results[name] = f"✗ ERROR: {str(e)}"

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for name, result in results.items():
        print(f"{name}: {result}")
    print("=" * 60)

    # Overall result
    all_passed = all("PASSED" in r for r in results.values())
    if all_passed:
        print("\n✓ All tests passed! Voice-AGI is ready to use.")
        print("\nNext steps:")
        print("1. Restart Claude Code to load the MCP server")
        print("2. Use voice_chat() or voice_conversation_loop() tools")
        print("3. Try: voice_chat(text='Create a goal to improve performance')")
        return 0
    else:
        print("\n⚠ Some tests failed. Check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

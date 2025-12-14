#!/usr/bin/env python3
"""
Voice Action Orchestrator Demo
===============================

Demonstrates the complete voice command pipeline:
1. Voice input → Intent classification
2. Intent → Action orchestration
3. Result → Voice output

This shows how the components work together in a realistic scenario.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python3 demo_voice_action_orchestrator.py
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from intent_classifier import IntentClassifier
from action_orchestrator import ActionOrchestrator, IntentType


async def demo_voice_pipeline():
    """
    Simulate complete voice interaction pipeline
    """
    print("=" * 60)
    print("VOICE ACTION ORCHESTRATOR DEMO")
    print("=" * 60)

    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n✗ ERROR: ANTHROPIC_API_KEY not set")
        print("Set with: export ANTHROPIC_API_KEY='sk-ant-...'")
        return

    # Initialize components
    print("\n📋 Initializing components...")
    classifier = IntentClassifier()
    orchestrator = ActionOrchestrator(api_key)
    print("✓ Intent classifier ready")
    print("✓ Action orchestrator ready")

    # Simulate voice commands
    voice_commands = [
        "Create a Python file called demo_example.py with a function that says hello",
        "What files are in the current directory?",
        "Hello! How are you doing?",
        "What is the current system status?",
    ]

    print(f"\n🎤 Simulating {len(voice_commands)} voice commands...\n")

    for i, utterance in enumerate(voice_commands, 1):
        print("=" * 60)
        print(f"COMMAND {i}/{len(voice_commands)}")
        print("=" * 60)

        print(f"\n🎤 Voice Input: \"{utterance}\"")

        # STEP 1: Intent Classification
        print("\n📊 Step 1: Classifying intent...")
        intent = classifier.classify(utterance)

        print(f"  ├─ Type: {intent.type.value}")
        print(f"  ├─ Confidence: {intent.confidence:.2f}")
        print(f"  ├─ Entities: {intent.entities if intent.entities else 'None'}")
        print(f"  └─ Needs Confirmation: {intent.requires_confirmation}")

        # STEP 2: Action Orchestration
        print("\n⚙️  Step 2: Executing action...")

        # Show different messages for different intent types
        if intent.type == IntentType.COMMAND:
            print("  └─ Executing code operation via Anthropic API...")
        elif intent.type == IntentType.QUERY:
            print("  └─ Retrieving information...")
        elif intent.type == IntentType.CONVERSATION:
            print("  └─ Generating conversational response...")
        elif intent.type == IntentType.META:
            print("  └─ Querying system state...")

        result = await orchestrator.execute_intent(intent)

        # STEP 3: Display Results
        print("\n📋 Step 3: Results")
        print(f"  ├─ Success: {'✓' if result.success else '✗'}")
        print(f"  ├─ Duration: {result.total_duration_ms}ms")
        print(f"  ├─ Steps: {len(result.steps)}")

        if result.tokens_used.get("input") or result.tokens_used.get("output"):
            print(f"  ├─ Tokens: {result.tokens_used.get('input', 0)} in, "
                  f"{result.tokens_used.get('output', 0)} out")

        if result.errors:
            print(f"  └─ Errors: {len(result.errors)}")
            for error in result.errors[:3]:
                print(f"      └─ {error}")
        else:
            print(f"  └─ No errors")

        # STEP 4: Voice Output (simulated)
        print("\n🔊 Step 4: Voice Output")
        output_text = result.output or result.summary

        # Truncate long outputs for voice
        if len(output_text) > 200:
            output_text = output_text[:200] + "..."

        print(f"  └─ Speaking: \"{output_text}\"")

        # Show detailed step breakdown for COMMAND intents
        if intent.type == IntentType.COMMAND and result.steps:
            print("\n📝 Execution Steps:")
            for step in result.steps:
                status = "✓" if step.status.value == "success" else "✗"
                print(f"  {status} {step.description}")
                if step.duration_ms:
                    print(f"    └─ Duration: {step.duration_ms}ms")

        print()  # Blank line between commands

    # Summary
    print("=" * 60)
    print("DEMO SUMMARY")
    print("=" * 60)

    print(f"\nTotal commands executed: {len(voice_commands)}")
    print("\nIntent type distribution:")

    intent_counts = {}
    for cmd in voice_commands:
        intent = classifier.classify(cmd)
        intent_counts[intent.type.value] = intent_counts.get(intent.type.value, 0) + 1

    for intent_type, count in sorted(intent_counts.items()):
        print(f"  └─ {intent_type}: {count}")

    print("\n✓ Demo completed successfully!")
    print("\nNext steps:")
    print("  1. Integrate with conversation_manager.py for real voice I/O")
    print("  2. Add voice feedback during execution")
    print("  3. Store execution outcomes in enhanced-memory MCP")
    print("  4. Create persistent tasks in agent-runtime MCP")


async def demo_interactive():
    """
    Interactive demo - type commands manually
    """
    print("=" * 60)
    print("INTERACTIVE VOICE ACTION ORCHESTRATOR")
    print("=" * 60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n✗ ERROR: ANTHROPIC_API_KEY not set")
        return

    classifier = IntentClassifier()
    orchestrator = ActionOrchestrator(api_key)

    print("\n✓ System ready. Type voice commands (or 'quit' to exit).\n")

    while True:
        try:
            utterance = input("🎤 Voice command: ").strip()

            if not utterance:
                continue

            if utterance.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break

            # Classify
            intent = classifier.classify(utterance)
            print(f"\n📊 Intent: {intent.type.value} (confidence: {intent.confidence:.2f})")

            if intent.entities:
                print(f"📋 Entities: {intent.entities}")

            # Execute
            print("⚙️  Executing...")
            result = await orchestrator.execute_intent(intent)

            # Show result
            if result.success:
                print(f"\n✓ Success ({result.total_duration_ms}ms)")
            else:
                print(f"\n✗ Failed ({result.total_duration_ms}ms)")

            print(f"\n🔊 Response: {result.output or result.summary}\n")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n✗ Error: {e}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Voice Action Orchestrator Demo")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode (type commands manually)"
    )

    args = parser.parse_args()

    if args.interactive:
        asyncio.run(demo_interactive())
    else:
        asyncio.run(demo_voice_pipeline())

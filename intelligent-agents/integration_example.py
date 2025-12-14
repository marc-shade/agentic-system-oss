#!/usr/bin/env python3
"""
Voice Action Orchestrator - Integration Example
================================================

Shows how to integrate the action orchestrator with conversation_manager.py
for complete voice-controlled coding workflows.

This demonstrates:
1. Voice input → Intent classification → Action execution → Voice output
2. Context preservation across commands
3. Error handling with voice feedback
4. Multi-step command execution

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python3 integration_example.py
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent))

from intent_classifier import IntentClassifier
from action_orchestrator import ActionOrchestrator, IntentType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("integration_example")


class EnhancedConversationManager:
    """
    Enhanced conversation manager with action orchestrator integration

    This shows how to extend conversation_manager.py with the orchestrator
    for full voice-controlled coding capabilities.
    """

    def __init__(self, anthropic_api_key: str):
        """Initialize with action orchestrator"""
        self.classifier = IntentClassifier()
        self.orchestrator = ActionOrchestrator(anthropic_api_key)

        # Track conversation context
        self.conversation_context = {
            "last_intent_type": None,
            "last_success": None,
            "files_mentioned": [],
            "commands_executed": 0
        }

        logger.info("Enhanced conversation manager initialized")

    async def process_voice_command(
        self,
        utterance: str,
        context: Dict[str, Any] = None
    ) -> str:
        """
        Process voice command through complete pipeline

        Args:
            utterance: User's voice input (from Whisper STT)
            context: Current context (visual, audio, system state)

        Returns:
            Response text for voice output (via Edge TTS)
        """
        logger.info(f"Processing: {utterance}")

        # STEP 1: Classify intent
        intent = self.classifier.classify(utterance)
        logger.info(f"Classified as {intent.type.value} (confidence: {intent.confidence:.2f})")

        # Update conversation context
        self.conversation_context["last_intent_type"] = intent.type.value
        self.conversation_context["commands_executed"] += 1

        # STEP 2: Handle confirmation if needed
        if intent.requires_confirmation:
            # In real implementation, this would speak confirmation request
            # and wait for user response via voice
            logger.warning(f"Confirmation required for: {utterance}")
            return f"This action requires confirmation. Please say 'yes' to proceed or 'no' to cancel."

        # STEP 3: Execute action
        try:
            # Merge context with conversation state
            full_context = {
                **(context or {}),
                **self.conversation_context,
                "working_directory": str(self.orchestrator.working_dir)
            }

            result = await self.orchestrator.execute_intent(intent, full_context)

            # Update conversation context
            self.conversation_context["last_success"] = result.success

            # Track files mentioned
            if intent.entities.get("file_name"):
                self.conversation_context["files_mentioned"].append(
                    intent.entities["file_name"]
                )

            # STEP 4: Generate voice-friendly response
            response = self._generate_voice_response(intent, result)

            return response

        except Exception as e:
            logger.error(f"Execution failed: {e}", exc_info=True)
            return f"I encountered an error: {str(e)}"

    def _generate_voice_response(self, intent, result) -> str:
        """
        Generate voice-friendly response based on intent type and result

        Args:
            intent: Classified intent
            result: Execution result

        Returns:
            Response text suitable for voice output
        """
        if not result.success:
            # Error response
            error_msg = result.errors[0] if result.errors else "Unknown error"
            return f"I couldn't complete that. {error_msg}"

        # Success responses by intent type
        if intent.type == IntentType.COMMAND:
            # Command execution
            if result.steps:
                step_summary = f"I executed {len(result.steps)} step{'s' if len(result.steps) > 1 else ''}."
            else:
                step_summary = "Done."

            # Add specific feedback based on entities
            if intent.entities.get("file_name"):
                file_name = intent.entities["file_name"]
                if intent.entities.get("action") == "create":
                    return f"I created {file_name}. {step_summary}"
                elif intent.entities.get("action") == "edit":
                    return f"I edited {file_name}. {step_summary}"
                elif intent.entities.get("action") == "delete":
                    return f"I deleted {file_name}. {step_summary}"

            return f"Command completed. {step_summary}"

        elif intent.type == IntentType.QUERY:
            # Query response - keep output concise for voice
            output = result.output

            # Truncate long outputs
            if len(output) > 300:
                output = output[:300] + "... and more. Should I continue?"

            return output

        elif intent.type == IntentType.CONVERSATION:
            # Conversational response
            return result.output

        elif intent.type == IntentType.META:
            # Meta command response
            return result.output

        # Default
        return result.output or result.summary

    async def handle_context_query(self, query: str) -> str:
        """
        Handle queries about conversation context

        Args:
            query: User query about context

        Returns:
            Context information
        """
        query_lower = query.lower()

        if "how many" in query_lower and "command" in query_lower:
            count = self.conversation_context["commands_executed"]
            return f"I've executed {count} command{'s' if count != 1 else ''} in this session."

        elif "what files" in query_lower:
            files = self.conversation_context["files_mentioned"]
            if not files:
                return "We haven't worked with any specific files yet."
            return f"We've worked with these files: {', '.join(files)}."

        elif "last" in query_lower and "success" in query_lower:
            last_success = self.conversation_context.get("last_success")
            if last_success is None:
                return "We haven't executed any commands yet."
            return "The last command succeeded." if last_success else "The last command failed."

        return "I don't have that information yet."


async def demo_integration():
    """
    Demonstrate complete integration
    """
    print("=" * 60)
    print("VOICE ACTION ORCHESTRATOR - INTEGRATION DEMO")
    print("=" * 60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n✗ ERROR: ANTHROPIC_API_KEY not set")
        print("Set with: export ANTHROPIC_API_KEY='sk-ant-...'")
        return

    # Initialize enhanced conversation manager
    manager = EnhancedConversationManager(api_key)

    # Simulate voice conversation with context
    conversation = [
        {
            "utterance": "Create a Python file called calculator.py with basic math functions",
            "context": {"visual": {"humans": {"detected": True}}}
        },
        {
            "utterance": "What files did we just create?",
            "context": {}
        },
        {
            "utterance": "Now create a test file for the calculator",
            "context": {}
        },
        {
            "utterance": "How many commands have we executed?",
            "context": {}
        }
    ]

    print("\n🎙️  Simulating voice conversation...\n")

    for i, turn in enumerate(conversation, 1):
        print("=" * 60)
        print(f"TURN {i}/{len(conversation)}")
        print("=" * 60)

        utterance = turn["utterance"]
        context = turn["context"]

        print(f"\n🎤 User: {utterance}")

        # Process through pipeline
        response = await manager.process_voice_command(utterance, context)

        print(f"🔊 Assistant: {response}\n")

        # Show conversation state
        print("📊 Conversation State:")
        print(f"  ├─ Commands executed: {manager.conversation_context['commands_executed']}")
        print(f"  ├─ Files mentioned: {manager.conversation_context['files_mentioned']}")
        print(f"  └─ Last success: {manager.conversation_context.get('last_success')}")

        # Small delay between turns
        await asyncio.sleep(0.5)

    # Final summary
    print("\n" + "=" * 60)
    print("CONVERSATION SUMMARY")
    print("=" * 60)

    print(f"\nTotal turns: {len(conversation)}")
    print(f"Commands executed: {manager.conversation_context['commands_executed']}")
    print(f"Files mentioned: {', '.join(manager.conversation_context['files_mentioned'])}")

    print("\n✓ Integration demo completed!")


async def demo_error_handling():
    """
    Demonstrate error handling in voice interface
    """
    print("\n" + "=" * 60)
    print("ERROR HANDLING DEMO")
    print("=" * 60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n✗ Skipping (no API key)")
        return

    manager = EnhancedConversationManager(api_key)

    # Commands that may fail
    error_scenarios = [
        "Read a file that doesn't exist called missing_file.txt",
        "Delete the system configuration",  # Should require confirmation
    ]

    for utterance in error_scenarios:
        print(f"\n🎤 User: {utterance}")

        response = await manager.process_voice_command(utterance)

        print(f"🔊 Assistant: {response}")


if __name__ == "__main__":
    print("\nVoice Action Orchestrator - Integration Example\n")
    print("This demonstrates how to integrate the orchestrator with")
    print("conversation_manager.py for complete voice workflows.\n")

    asyncio.run(demo_integration())
    asyncio.run(demo_error_handling())

    print("\n" + "=" * 60)
    print("INTEGRATION GUIDE")
    print("=" * 60)
    print("\nTo integrate with conversation_manager.py:")
    print("\n1. Add imports:")
    print("   from intent_classifier import IntentClassifier")
    print("   from action_orchestrator import ActionOrchestrator")
    print("\n2. Initialize in __init__:")
    print("   self.classifier = IntentClassifier()")
    print("   self.orchestrator = ActionOrchestrator(api_key)")
    print("\n3. Update generate_response method:")
    print("   intent = self.classifier.classify(user_utterance)")
    print("   result = await self.orchestrator.execute_intent(intent, context)")
    print("   return result.output or result.summary")
    print("\n4. Add voice feedback during execution:")
    print("   self.arduino.show_voice_state('processing', intent.text[:16])")
    print("\n5. Store learnings in enhanced-memory MCP:")
    print("   memory_client.record_action_outcome(...)")
    print()

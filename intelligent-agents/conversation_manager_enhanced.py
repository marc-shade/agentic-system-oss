#!/usr/bin/env python3
"""
Enhanced Conversation Manager with State Management
Integrates ConversationState with the existing conversation manager

This version adds:
- Full conversation history tracking
- Context preservation across turns
- File context management
- Action tracking
- Session persistence via enhanced-memory MCP
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from conversation_state import (
    ConversationState,
    ActionRecord,
    TurnType,
    ActionStatus
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("conversation_manager_enhanced")

# Configuration
TRANSCRIPT_QUEUE = Path("/tmp/conversation_transcript.json")
CONSCIOUSNESS_STATE = Path("/tmp/consciousness_state.json")
CONVERSATION_LOG = Path.home() / "agentic-system" / "logs" / "conversations.log"
CONVERSATION_LOG.parent.mkdir(parents=True, exist_ok=True)
SPEAKING_FLAG = Path("/tmp/agi_speaking.flag")


class EnhancedConversationManager:
    """
    Enhanced conversation manager with comprehensive state tracking

    Adds state management on top of basic conversation functionality:
    - Track all conversation turns with metadata
    - Maintain file and task context
    - Record actions and their outcomes
    - Generate context summaries for better LLM responses
    - Persist state across sessions
    """

    def __init__(self, session_id: Optional[str] = None):
        """
        Initialize enhanced conversation manager

        Args:
            session_id: Optional session ID (auto-generated if None)
        """
        # Initialize conversation state
        self.state = ConversationState(session_id=session_id)

        # Processing state
        self.last_processed_transcript_idx = 0
        self.awaiting_response = False
        self.last_speech_time = None

        logger.info(f"Enhanced conversation manager initialized: session={self.state.session_id}")

    async def get_consciousness_context(self) -> Dict[str, Any]:
        """
        Get current context from consciousness daemon

        Returns:
            Context dict with system state, visual, audio observations
        """
        try:
            if CONSCIOUSNESS_STATE.exists():
                with open(CONSCIOUSNESS_STATE, 'r') as f:
                    state = json.load(f)

                    context = {
                        "visual": state.get("working_memory", {}).get("last_observations", {}).get("visual", {}),
                        "audio": state.get("working_memory", {}).get("last_observations", {}).get("audio", {}),
                        "system": state.get("working_memory", {}).get("last_observations", {}).get("system", {}),
                        "attention": state.get("metacognitive_state", {}).get("attention_focus", []),
                        "cognitive_load": state.get("metacognitive_state", {}).get("cognitive_load", 0)
                    }

                    return context
        except Exception as e:
            logger.error(f"Failed to get consciousness context: {e}")

        return {}

    def get_new_transcripts(self) -> List[Dict[str, Any]]:
        """
        Get new transcripts since last processing

        Returns:
            List of new transcript dicts
        """
        try:
            if not TRANSCRIPT_QUEUE.exists():
                return []

            with open(TRANSCRIPT_QUEUE, 'r') as f:
                transcripts = json.load(f)

                if not isinstance(transcripts, list):
                    return []

                new_transcripts = transcripts[self.last_processed_transcript_idx:]
                self.last_processed_transcript_idx = len(transcripts)

                return new_transcripts

        except Exception as e:
            logger.error(f"Failed to get new transcripts: {e}")
            return []

    def classify_turn_type(self, text: str) -> TurnType:
        """
        Classify the type of conversation turn

        Args:
            text: User utterance

        Returns:
            TurnType classification
        """
        text_lower = text.lower().strip()

        # Greetings
        greeting_words = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]
        if any(word in text_lower for word in greeting_words):
            return TurnType.GREETING

        # Questions
        question_words = ["what", "when", "where", "who", "why", "how", "can", "could", "would", "should", "is", "are", "do", "does"]
        if any(text_lower.startswith(word) for word in question_words) or text.endswith("?"):
            return TurnType.QUESTION

        # Commands
        command_words = ["show", "tell", "explain", "describe", "list", "find", "search", "give", "turn", "start", "stop", "run", "create", "build", "make"]
        if any(text_lower.startswith(word) for word in command_words):
            return TurnType.COMMAND

        # Confirmations
        confirmation_words = ["yes", "yeah", "okay", "ok", "sure", "right", "correct", "exactly", "no", "nope"]
        if any(text_lower.strip() == word for word in confirmation_words):
            return TurnType.CONFIRMATION

        # Default to question
        return TurnType.QUESTION

    async def generate_response(
        self,
        user_utterance: str,
        context: Dict[str, Any]
    ) -> tuple[str, List[ActionRecord], float]:
        """
        Generate response to user utterance with action tracking

        Args:
            user_utterance: What user said
            context: Current consciousness context

        Returns:
            Tuple of (response_text, actions_taken, confidence)
        """
        utterance_lower = user_utterance.lower()
        actions = []
        confidence = 0.8  # Default confidence

        # Use conversation context for better responses
        context_summary = self.state.get_context_summary(max_turns=3)

        # Greetings
        if "hello" in utterance_lower or "hi" in utterance_lower:
            if self.state.total_turns == 0:
                response = "Hello! I'm your AI assistant. How can I help you today?"
            else:
                response = "Hello again! What can I do for you?"
            confidence = 1.0

        # Visual questions
        elif "can you see" in utterance_lower or "do you see" in utterance_lower:
            visual = context.get("visual", {})
            action = ActionRecord(
                action_id=f"vision_{datetime.now().timestamp()}",
                action_type="sensor_read",
                description="Reading visual sensors",
                status=ActionStatus.COMPLETED,
                result=f"Detected: {visual}"
            )
            actions.append(action)

            if visual.get("humans", {}).get("detected"):
                count = visual["humans"]["count"]
                response = f"Yes, I can see you! I detect {count} person in the room."
            else:
                response = "I can see the room, but I don't detect anyone in the camera view right now."
            confidence = 0.9

        # File operations
        elif "read file" in utterance_lower or "open file" in utterance_lower:
            # Extract potential file path (simple heuristic)
            words = user_utterance.split()
            file_path = None
            for i, word in enumerate(words):
                if word in ["read", "open"] and i + 1 < len(words):
                    file_path = words[i + 1]
                    break

            if file_path:
                action = ActionRecord(
                    action_id=f"file_read_{datetime.now().timestamp()}",
                    action_type="file_read",
                    description=f"Reading file: {file_path}",
                    status=ActionStatus.PENDING
                )
                actions.append(action)
                self.state.add_file_context(file_path)
                response = f"I'll read the file '{file_path}' for you."
            else:
                self.state.add_clarification("Which file would you like me to read?")
                response = "Which file would you like me to read? Please provide the file path."
            confidence = 0.7

        # Task tracking
        elif "start task" in utterance_lower or "new task" in utterance_lower:
            # Extract task description
            task_desc = user_utterance.replace("start task", "").replace("new task", "").strip()
            if task_desc:
                self.state.update_active_task(task_desc, task_desc)
                response = f"Started new task: {task_desc}. I'll track our progress."
                confidence = 0.9
            else:
                self.state.add_clarification("What task would you like to start?")
                response = "What task would you like to start? Please provide a description."
                confidence = 0.6

        # System status
        elif "cpu" in utterance_lower or "memory" in utterance_lower or "system" in utterance_lower:
            system = context.get("system", {})
            cpu = system.get("cpu_percent", 0)
            mem = system.get("memory_percent", 0)

            action = ActionRecord(
                action_id=f"system_status_{datetime.now().timestamp()}",
                action_type="system_read",
                description="Reading system metrics",
                status=ActionStatus.COMPLETED,
                result=f"CPU: {cpu}%, Memory: {mem}%"
            )
            actions.append(action)

            response = f"System is running at {cpu:.1f}% CPU and {mem:.1f}% memory usage."
            confidence = 1.0

        # Time questions
        elif "what time" in utterance_lower:
            now = datetime.now().strftime("%I:%M %p")
            response = f"It's currently {now}."
            confidence = 1.0

        # Context-aware response
        elif self.state.active_task:
            response = f"I'm working on: {self.state.active_task}. {user_utterance} - I'll help with that."
            confidence = 0.7

        # Default response with context
        else:
            if self.state.total_turns < 3:
                response = f"I heard: '{user_utterance}'. I'm still learning how to respond. Can you rephrase or ask something specific?"
            else:
                response = f"Based on our conversation, I understand you're asking about: {user_utterance}. Could you provide more details?"
            confidence = 0.5

        return response, actions, confidence

    async def speak_response(self, text: str):
        """
        Speak response via edge-tts (placeholder)

        Args:
            text: Text to speak
        """
        logger.info(f"Would speak: {text[:50]}...")
        # In production, this would call TTS service
        await asyncio.sleep(0.1)

    def log_conversation(self, user: str, assistant: str):
        """
        Log conversation exchange

        Args:
            user: User's utterance
            assistant: Assistant's response
        """
        try:
            timestamp = datetime.now().isoformat()
            with open(CONVERSATION_LOG, 'a') as f:
                f.write(f"\n[{timestamp}] Session: {self.state.session_id}\n")
                f.write(f"User: {user}\n")
                f.write(f"Assistant: {assistant}\n")
        except Exception as e:
            logger.error(f"Failed to log conversation: {e}")

    async def process_utterance(self, transcript: Dict[str, Any]):
        """
        Process a single transcribed utterance with full state tracking

        Args:
            transcript: Transcript dict with utterance, timestamp, etc.
        """
        utterance = transcript.get("utterance", "").strip()
        if not utterance:
            return

        logger.info(f"Processing: '{utterance}'")

        # Get consciousness context
        context = await self.get_consciousness_context()

        # Classify turn type
        turn_type = self.classify_turn_type(utterance)

        # Generate response with actions
        response, actions, confidence = await self.generate_response(utterance, context)

        # Add turn to state
        turn = self.state.add_turn(
            user_msg=utterance,
            assistant_msg=response,
            turn_type=turn_type,
            actions=actions,
            confidence=confidence,
            context=context
        )

        # Process actions
        for action in actions:
            if action.status == ActionStatus.PENDING:
                self.state.add_action(action)

        # Log conversation
        self.log_conversation(utterance, response)

        # Speak response
        await self.speak_response(response)

        # Periodically persist state (every 5 turns)
        if self.state.total_turns % 5 == 0:
            await self.state.persist()
            logger.debug(f"Persisted state at turn {self.state.total_turns}")

    def print_status(self):
        """Print current conversation status"""
        stats = self.state.get_statistics()

        print("\n" + "=" * 60)
        print("ENHANCED CONVERSATION MANAGER - STATUS")
        print("=" * 60)
        print(f"Session ID: {stats['session_id']}")
        print(f"Duration: {stats['duration_minutes']:.1f} minutes")
        print(f"Total Turns: {stats['total_turns']}")
        print(f"Average Confidence: {stats['average_confidence']:.2f}")
        print(f"Active Task: {stats['active_task'] or 'None'}")
        print(f"Files in Context: {stats['files_in_context']}")
        print(f"Pending Actions: {stats['pending_actions']}")
        print(f"Clarifications Needed: {stats['clarifications_needed']}")
        print("=" * 60)
        print()

    async def run(self):
        """
        Main conversation loop with state management

        Continuously monitors for new transcripts and processes them
        """
        logger.info("Enhanced conversation manager starting...")

        while True:
            try:
                # Get new transcripts
                new_transcripts = self.get_new_transcripts()

                # Process each new transcript
                for transcript in new_transcripts:
                    await self.process_utterance(transcript)

                # Sleep briefly
                await asyncio.sleep(0.5)

            except KeyboardInterrupt:
                logger.info("Stopping conversation manager...")
                # Final persist
                await self.state.persist()
                self.print_status()
                break
            except Exception as e:
                logger.error(f"Conversation loop error: {e}", exc_info=True)
                await asyncio.sleep(1)


async def demo_enhanced_manager():
    """Demonstrate enhanced conversation manager"""
    print("=" * 60)
    print("Enhanced Conversation Manager - Demo")
    print("=" * 60)
    print()

    manager = EnhancedConversationManager()

    # Simulate conversation with transcripts
    simulated_transcripts = [
        {"utterance": "Hello, can you help me?", "timestamp": datetime.now().isoformat()},
        {"utterance": "I need to build a REST API", "timestamp": datetime.now().isoformat()},
        {"utterance": "Can you see me?", "timestamp": datetime.now().isoformat()},
        {"utterance": "What's the system status?", "timestamp": datetime.now().isoformat()},
        {"utterance": "Start task: Build authentication system", "timestamp": datetime.now().isoformat()},
        {"utterance": "Read file auth.py", "timestamp": datetime.now().isoformat()},
    ]

    for transcript in simulated_transcripts:
        await manager.process_utterance(transcript)
        await asyncio.sleep(0.2)

    # Show final status
    manager.print_status()

    # Show context summary
    print("\nContext Summary:")
    print(manager.state.get_context_summary())

    # Persist final state
    await manager.state.persist()
    print("\n✓ State persisted to enhanced-memory MCP")


if __name__ == "__main__":
    asyncio.run(demo_enhanced_manager())

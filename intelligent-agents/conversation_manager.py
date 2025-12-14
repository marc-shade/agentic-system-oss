#!/usr/bin/env python3
"""
Conversation Manager - AGI Voice Interaction Coordinator
=========================================================

Manages bidirectional voice conversations with complete action orchestration:
- Listens for transcribed speech from conversational_audio_perceiver
- Classifies intents using IntentClassifier
- Executes actions via ActionOrchestrator (Anthropic API with tool use)
- Tracks conversation state with ConversationState
- Generates voice responses via edge-tts
- Maintains conversation context and history
- Integrates with consciousness daemon for awareness-driven responses
- Updates Arduino display for visual feedback

This is the central hub for conversational AGI interaction with full
command execution capabilities.

Integration Flow:
    User utterance → IntentClassifier → ActionOrchestrator → ConversationState
                                              ↓
                                        Response text
                                              ↓
                                        speak_response() → TTS + Arduino
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import deque

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("conversation_manager")

# Add Arduino perceiver to path
sys.path.insert(0, str(Path(__file__).parent / "perception"))

# Import Arduino perceiver
try:
    from arduino_perceiver import ArduinoPerceiver
    ARDUINO_AVAILABLE = True
except ImportError:
    ARDUINO_AVAILABLE = False
    logger.warning("Arduino perceiver not available - continuing without display")

# Import new voice processing components
try:
    from intent_classifier import IntentClassifier
    from action_orchestrator import ActionOrchestrator, IntentType
    from conversation_state import ConversationState, TurnType, ActionRecord, ActionStatus
    VOICE_COMPONENTS_AVAILABLE = True
    logger.info("✓ Voice processing components loaded")
except ImportError as e:
    VOICE_COMPONENTS_AVAILABLE = False
    logger.warning(f"Voice processing components not available: {e}")
    logger.warning("Falling back to simple rule-based responses")

# Configuration
TRANSCRIPT_QUEUE = Path("/tmp/conversation_transcript.json")
CONSCIOUSNESS_STATE = Path("/tmp/consciousness_state.json")
CONVERSATION_LOG = Path.home() / "agentic-system" / "logs" / "conversations.log"
CONVERSATION_LOG.parent.mkdir(parents=True, exist_ok=True)
SPEAKING_FLAG = Path("/tmp/agi_speaking.flag")  # Echo cancellation coordination
PTT_FLAG = Path("/tmp/ptt_active.flag")  # Push-to-talk active flag

# Voice settings
DEFAULT_VOICE = "en-IE-EmilyNeural"  # Irish female voice
SPEECH_RATE = "+0%"


class ConversationManager:
    """
    Manages conversational AI interactions with full action orchestration

    Integrates:
    - IntentClassifier: Classifies user utterances into intent types
    - ActionOrchestrator: Executes commands via Anthropic API with tool use
    - ConversationState: Tracks multi-turn conversation context
    - Arduino Display: Visual feedback for voice states
    - Edge-TTS: Text-to-speech for responses
    """

    def __init__(self, arduino_port: str = '/dev/ttyACM0'):
        """
        Initialize conversation manager with all components

        Args:
            arduino_port: Serial port for Arduino display (optional)
        """
        self.conversation_history = deque(maxlen=20)  # Keep last 20 exchanges
        self.last_processed_transcript_idx = 0
        self.awaiting_response = False
        self.last_speech_time = None

        # Initialize Arduino display (gracefully degrades if not available)
        self.arduino = None
        if ARDUINO_AVAILABLE:
            try:
                self.arduino = ArduinoPerceiver(port=arduino_port, fallback_on_error=True)
                logger.info("✓ Arduino display integration enabled")
            except Exception as e:
                logger.warning(f"Arduino display not available: {e}")

        # Initialize voice processing components
        self.intent_classifier = None
        self.action_orchestrator = None
        self.conversation_state = None

        if VOICE_COMPONENTS_AVAILABLE:
            try:
                # Initialize intent classifier (rule-based, no API key needed)
                self.intent_classifier = IntentClassifier()
                logger.info("✓ Intent classifier initialized")

                # Initialize conversation state tracker
                self.conversation_state = ConversationState()
                logger.info("✓ Conversation state tracker initialized")

                # Initialize action orchestrator (requires ANTHROPIC_API_KEY)
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if api_key:
                    self.action_orchestrator = ActionOrchestrator(
                        anthropic_api_key=api_key,
                        working_dir=Path.cwd()
                    )
                    logger.info("✓ Action orchestrator initialized with API key")
                else:
                    logger.warning("ANTHROPIC_API_KEY not set - advanced command execution disabled")
                    logger.warning("Set environment variable: export ANTHROPIC_API_KEY='sk-ant-...'")

            except Exception as e:
                logger.error(f"Failed to initialize voice components: {e}", exc_info=True)
                logger.warning("Falling back to simple rule-based responses")
                self.intent_classifier = None
                self.action_orchestrator = None
                self.conversation_state = None

        logger.info("Conversation manager initialized")

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

                    # Extract relevant context
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

                # Get only new transcripts
                new_transcripts = transcripts[self.last_processed_transcript_idx:]
                self.last_processed_transcript_idx = len(transcripts)

                return new_transcripts

        except Exception as e:
            logger.error(f"Failed to get new transcripts: {e}")
            return []

    def is_question_or_command(self, text: str) -> bool:
        """
        Determine if utterance is a question or command (fallback logic)

        Args:
            text: Transcribed speech

        Returns:
            True if needs response
        """
        text_lower = text.lower().strip()

        # Question indicators
        question_words = ["what", "when", "where", "who", "why", "how", "can", "could", "would", "should", "is", "are", "do", "does"]
        if any(text_lower.startswith(word) for word in question_words):
            return True

        if text.endswith("?"):
            return True

        # Command indicators
        command_words = ["show", "tell", "explain", "describe", "list", "find", "search", "give", "turn", "start", "stop", "run", "create", "make", "write"]
        if any(text_lower.startswith(word) for word in command_words):
            return True

        # Direct address
        if any(name in text_lower for name in ["claude", "hey", "hello", "excuse me"]):
            return True

        return False

    async def generate_response(
        self,
        user_utterance: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Generate response to user utterance using orchestrator or fallback

        Integration with ActionOrchestrator:
        1. Classify intent using IntentClassifier
        2. Execute intent using ActionOrchestrator (if API key available)
        3. Track conversation with ConversationState
        4. Return response text for TTS

        Args:
            user_utterance: What user said
            context: Current consciousness context

        Returns:
            Response text for TTS
        """
        # If advanced components available, use them
        if (self.intent_classifier and self.action_orchestrator and
            self.conversation_state):
            try:
                # Update Arduino: Classifying intent
                if self.arduino:
                    self.arduino.show_voice_state("processing", "Classifying...")

                # Step 1: Classify intent
                intent = self.intent_classifier.classify(user_utterance)
                logger.info(f"Intent: {intent.type.value} (confidence: {intent.confidence:.2f})")

                # Update Arduino: Show intent type
                if self.arduino:
                    self.arduino.show_voice_state("processing", intent.type.value[:16])

                # Step 2: Execute intent via orchestrator
                logger.info(f"Executing via orchestrator: {intent.type.value}")
                execution_result = await self.action_orchestrator.execute_intent(
                    intent=intent,
                    context=context
                )

                # Step 3: Track conversation turn
                turn_type_map = {
                    IntentType.COMMAND: TurnType.COMMAND,
                    IntentType.QUERY: TurnType.QUESTION,
                    IntentType.CONVERSATION: TurnType.GREETING,
                    IntentType.META: TurnType.QUESTION
                }

                # Convert execution steps to action records
                action_records = []
                for step in execution_result.steps:
                    action_records.append(ActionRecord(
                        action_id=f"step_{step.step_number}",
                        action_type=step.tool,
                        description=step.description,
                        status=ActionStatus.COMPLETED if step.status.value == "success" else ActionStatus.FAILED,
                        result=str(step.result) if step.result else None,
                        error=step.error,
                        duration_ms=step.duration_ms
                    ))

                # Add turn to conversation state
                self.conversation_state.add_turn(
                    user_msg=user_utterance,
                    assistant_msg=execution_result.output,
                    turn_type=turn_type_map.get(intent.type, TurnType.QUESTION),
                    actions=action_records,
                    confidence=intent.confidence
                )

                # Log execution summary
                logger.info(f"Execution result: success={execution_result.success}, "
                          f"steps={len(execution_result.steps)}, "
                          f"tokens={execution_result.tokens_used}")

                # Return the response
                if execution_result.success:
                    return execution_result.output or execution_result.summary
                else:
                    # Include error information in response
                    error_msg = "I encountered an error while processing your request."
                    if execution_result.errors:
                        error_msg += f" {execution_result.errors[0]}"
                    return error_msg

            except Exception as e:
                logger.error(f"Orchestrator execution failed: {e}", exc_info=True)
                # Fall through to simple response
                return f"I'm having trouble processing that request. Error: {str(e)}"

        # Fallback to simple rule-based responses
        logger.info("Using fallback rule-based responses")
        return await self._generate_simple_response(user_utterance, context)

    async def _generate_simple_response(
        self,
        user_utterance: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Generate simple rule-based response (fallback when orchestrator unavailable)

        Args:
            user_utterance: What user said
            context: Current consciousness context

        Returns:
            Response text
        """
        if self.arduino:
            detail = " ".join(user_utterance.split()[:3])
            self.arduino.show_voice_state("processing", detail)

        utterance_lower = user_utterance.lower()

        # Greetings
        if any(word in utterance_lower for word in ["hello", "hi", "hey", "good morning", "good afternoon"]):
            return "Hello! How can I help you?"

        # Visual questions
        if "can you see" in utterance_lower or "do you see" in utterance_lower:
            visual = context.get("visual", {})
            if visual.get("humans", {}).get("detected"):
                count = visual["humans"]["count"]
                return f"Yes, I can see you! I detect {count} person in the room."
            else:
                return "I can see the room, but I don't detect anyone in the camera view right now."

        # System status questions
        if "cpu" in utterance_lower or "memory" in utterance_lower or "system" in utterance_lower:
            system = context.get("system", {})
            cpu = system.get("cpu_percent", 0)
            mem = system.get("memory_percent", 0)
            return f"System is running at {cpu:.1f}% CPU and {mem:.1f}% memory usage."

        # Audio/listening confirmation
        if "can you hear" in utterance_lower or "are you listening" in utterance_lower:
            return "Yes, I can hear you! I'm listening continuously through the microphone with speech-to-text transcription."

        # Time questions
        if "what time" in utterance_lower or "what's the time" in utterance_lower:
            now = datetime.now().strftime("%I:%M %p")
            return f"It's currently {now}."

        # API key help
        if "api key" in utterance_lower or "anthropic" in utterance_lower:
            if self.action_orchestrator:
                return "The Anthropic API key is configured and working."
            else:
                return "The Anthropic API key is not configured. Set the ANTHROPIC_API_KEY environment variable to enable advanced command execution."

        # Default response
        if not self.action_orchestrator:
            return ("I heard you say: " + user_utterance +
                   ". Note: Advanced command execution is disabled because ANTHROPIC_API_KEY is not set. "
                   "I can only respond to simple questions about system status, time, and what I can see or hear.")
        else:
            return "I heard you say: " + user_utterance + ". I'm still learning how to respond to different questions."

    async def speak_response(self, text: str):
        """
        Speak response via edge-tts with echo cancellation

        Args:
            text: Text to speak
        """
        try:
            # Update Arduino: Responding
            if self.arduino:
                # Show response preview (first 16 chars)
                preview = text[:16]
                self.arduino.show_voice_state("responding", preview)

            # ECHO CANCELLATION: Set speaking flag to mute microphone
            SPEAKING_FLAG.touch()
            logger.debug("Speaking flag set - microphone will be muted")

            audio_file = f"/tmp/conversation-response-{int(time.time())}.mp3"

            # Generate speech
            cmd = [
                'edge-tts',
                '--voice', DEFAULT_VOICE,
                '--rate', SPEECH_RATE,
                '--text', text,
                '--write-media', audio_file
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()

            # Play audio
            if proc.returncode == 0:
                for player in ['mpg123', 'ffplay', 'aplay']:
                    if subprocess.run(['which', player], capture_output=True).returncode == 0:
                        play_proc = subprocess.Popen([player, audio_file],
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
                        # Wait for audio to finish playing
                        play_proc.wait()
                        break

            logger.info(f"Spoke response: \"{text[:50]}...\"")

            # Small delay to ensure audio playback is complete
            await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Failed to speak response: {e}")
        finally:
            # ECHO CANCELLATION: Clear speaking flag to resume listening
            if SPEAKING_FLAG.exists():
                SPEAKING_FLAG.unlink()
                logger.debug("Speaking flag cleared - microphone will resume")

            # Update Arduino: Back to listening mode
            if self.arduino:
                self.arduino.show_voice_state("listening")

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
                f.write(f"\n[{timestamp}]\n")
                f.write(f"User: {user}\n")
                f.write(f"Assistant: {assistant}\n")
        except Exception as e:
            logger.error(f"Failed to log conversation: {e}")

    async def process_utterance(self, transcript: Dict[str, Any]):
        """
        Process a single transcribed utterance with full orchestration pipeline

        Pipeline:
        1. Validate utterance
        2. Check if requires response (question/command detection)
        3. Update Arduino with processing state
        4. Get consciousness context
        5. Classify intent (if orchestrator available)
        6. Execute via orchestrator (COMMAND/QUERY) or generate response (CONVERSATION/META)
        7. Track conversation state
        8. Log conversation
        9. Speak response via TTS

        Args:
            transcript: Transcript dict with utterance, timestamp, etc.
        """
        utterance = transcript.get("utterance", "").strip()
        if not utterance:
            return

        logger.info(f"Processing utterance: \"{utterance}\"")

        # Update Arduino: Show that we heard the user
        if self.arduino:
            # Show first few words of what user said
            preview = utterance[:16]
            self.arduino.show_voice_state("processing", preview)

        # Check if needs response
        if not self.is_question_or_command(utterance):
            logger.info("Utterance is not a question/command - no response needed")
            if self.arduino:
                self.arduino.show_voice_state("listening")
            return

        # Get consciousness context
        context = await self.get_consciousness_context()

        # Generate response (uses orchestrator if available, fallback otherwise)
        response = await self.generate_response(utterance, context)

        # Add to conversation history
        self.conversation_history.append({
            "timestamp": transcript.get("timestamp"),
            "user": utterance,
            "assistant": response
        })

        # Log conversation
        self.log_conversation(utterance, response)

        # Speak response
        await self.speak_response(response)

        # Persist conversation state periodically (if available)
        if self.conversation_state and len(self.conversation_history) % 5 == 0:
            try:
                await self.conversation_state.persist()
                logger.debug("Conversation state persisted to enhanced-memory")
            except Exception as e:
                logger.warning(f"Failed to persist conversation state: {e}")

    async def run(self):
        """
        Main conversation loop - monitors transcripts and PTT status

        Continuously monitors for new transcripts and processes them.
        Also monitors PTT flag to update Arduino display status.
        """
        logger.info("Conversation manager starting main loop...")

        # Print configuration status
        logger.info("Configuration status:")
        logger.info(f"  - Arduino display: {'✓ enabled' if self.arduino else '✗ disabled'}")
        logger.info(f"  - Intent classifier: {'✓ enabled' if self.intent_classifier else '✗ disabled'}")
        logger.info(f"  - Action orchestrator: {'✓ enabled' if self.action_orchestrator else '✗ disabled (no API key)'}")
        logger.info(f"  - Conversation state: {'✓ enabled' if self.conversation_state else '✗ disabled'}")

        # Track PTT state to detect changes
        last_ptt_state = False

        # Don't set initial Arduino state - let it show rotating system status

        while True:
            try:
                # Check PTT flag status
                ptt_active = PTT_FLAG.exists()

                # Update Arduino if PTT state changed
                if self.arduino and ptt_active != last_ptt_state:
                    if ptt_active:
                        # PTT ON - Show listening state with orange pulsing LED
                        self.arduino.show_voice_state("listening", "Caps Lock ON - Speak now")
                        logger.info("🎤 PTT ACTIVE - Listening mode ON")
                    else:
                        # PTT OFF - Release control, let Arduino return to rotating system status
                        logger.info("⏸️  PTT INACTIVE - Returning to system status display")

                    last_ptt_state = ptt_active

                # Get new transcripts
                new_transcripts = self.get_new_transcripts()

                # Process each new transcript
                for transcript in new_transcripts:
                    await self.process_utterance(transcript)

                # Sleep briefly (faster polling for PTT responsiveness)
                await asyncio.sleep(0.1)

            except KeyboardInterrupt:
                logger.info("Conversation manager stopped by user")

                # Persist final state
                if self.conversation_state:
                    try:
                        await self.conversation_state.persist()
                        logger.info("Final conversation state persisted")
                    except Exception as e:
                        logger.error(f"Failed to persist final state: {e}")

                break
            except Exception as e:
                logger.error(f"Conversation loop error: {e}", exc_info=True)
                await asyncio.sleep(1)


async def main():
    """Entry point"""
    # Check for API key and provide helpful message
    if not os.getenv("ANTHROPIC_API_KEY"):
        logger.warning("="*60)
        logger.warning("ANTHROPIC_API_KEY environment variable not set!")
        logger.warning("Advanced command execution will be disabled.")
        logger.warning("")
        logger.warning("To enable full functionality, set your API key:")
        logger.warning("  export ANTHROPIC_API_KEY='sk-ant-...'")
        logger.warning("")
        logger.warning("The system will still work with simple rule-based responses.")
        logger.warning("="*60)

    manager = ConversationManager()
    await manager.run()


if __name__ == "__main__":
    asyncio.run(main())

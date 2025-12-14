"""Environmental Listener - Continuous audio awareness for Pixel.

"The mics are my ears" - Always listening, intelligently filtering.

This component:
- Continuously monitors audio via voice-mode MCP
- Filters out noise, music, and TTS feedback
- Detects speech directed at Pixel
- Provides contextual audio awareness
"""

import asyncio
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from .audio_filter import AudioFilter, AudioEvent, AudioSourceType
from ..utils.logging import get_logger


logger = get_logger(__name__)


@dataclass
class EnvironmentalState:
    """Current environmental audio state."""
    is_listening: bool
    is_muted: bool
    recent_speech_count: int
    last_directed_speech: Optional[datetime]
    ambient_noise_level: str  # "quiet", "moderate", "noisy"
    human_presence_detected: bool
    timestamp: datetime


class EnvironmentalListener:
    """
    Continuous environmental audio awareness.

    Provides:
    - Background listening with intelligent filtering
    - Speech detection and wake word recognition
    - TTS coordination to prevent feedback
    - Human presence detection through audio
    - Mute capability for privacy
    """

    def __init__(self, config: dict):
        """Initialize Environmental Listener.

        Args:
            config: Daemon configuration
        """
        self.config = config

        # Configuration
        listener_config = config.get("components", {}).get("environmental_listener", {})

        self.enabled = listener_config.get("enabled", True)
        self.poll_interval_seconds = listener_config.get("poll_interval_seconds", 3)
        self.voice_mode_host = listener_config.get("voice_mode_host", "localhost")
        self.voice_mode_port = listener_config.get("voice_mode_port", 8765)

        # Audio filter
        self.audio_filter = AudioFilter(config)

        # Add custom ignore patterns for drum machine
        drum_patterns = listener_config.get("drum_machine_patterns", [
            "boom bap",
            "kick snare",
            "one two three four",
            "bass drop",
        ])
        for pattern in drum_patterns:
            self.audio_filter.add_ignore_pattern(pattern)

        # State
        self._listening = False
        self._muted = False
        self._poll_task: Optional[asyncio.Task] = None
        self._last_check_time: Optional[datetime] = None
        self._processed_transcription_ids: set = set()

        # Callbacks for directed speech
        self._speech_handlers: List[Callable[[AudioEvent], Any]] = []

        # Stats
        self._stats = {
            "total_polls": 0,
            "transcriptions_received": 0,
            "speech_events_processed": 0,
            "directed_speech_detected": 0,
        }

        logger.info(
            "environmental_listener_initialized",
            enabled=self.enabled,
            poll_interval=self.poll_interval_seconds,
        )

    async def start(self) -> bool:
        """Start listening to the environment.

        Returns:
            True if successfully started
        """
        if not self.enabled:
            logger.info("environmental_listener_disabled")
            return False

        if self._listening:
            logger.warning("already_listening")
            return True

        # Start voice mode if not already running
        started = await self._ensure_voice_mode_running()
        if not started:
            logger.error("failed_to_start_voice_mode")
            return False

        # Start polling loop
        self._listening = True
        self._poll_task = asyncio.create_task(self._poll_loop())

        logger.info("environmental_listener_started")
        return True

    async def stop(self) -> None:
        """Stop listening."""
        self._listening = False

        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None

        logger.info("environmental_listener_stopped")

    def mute(self) -> None:
        """Mute the listener (privacy mode)."""
        self._muted = True
        logger.info("listener_muted")

    def unmute(self) -> None:
        """Unmute the listener."""
        self._muted = False
        logger.info("listener_unmuted")

    def toggle_mute(self) -> bool:
        """Toggle mute state.

        Returns:
            New mute state (True = muted)
        """
        self._muted = not self._muted
        logger.info("listener_mute_toggled", muted=self._muted)
        return self._muted

    @property
    def is_muted(self) -> bool:
        """Check if listener is muted."""
        return self._muted

    @property
    def is_listening(self) -> bool:
        """Check if listener is active."""
        return self._listening and not self._muted

    def mark_tts_start(self) -> None:
        """Mark that TTS is starting (prevent feedback)."""
        self.audio_filter.mark_tts_start()

    def mark_tts_end(self) -> None:
        """Mark that TTS has ended."""
        self.audio_filter.mark_tts_end()

    def register_speech_handler(self, handler: Callable[[AudioEvent], Any]) -> None:
        """Register a handler for directed speech events.

        Args:
            handler: Function to call when speech directed at Pixel is detected
        """
        self._speech_handlers.append(handler)
        self.audio_filter.register_speech_callback(handler)

    async def _ensure_voice_mode_running(self) -> bool:
        """Ensure voice mode is running with STT enabled.

        Returns:
            True if voice mode is ready
        """
        try:
            # Check voice mode status using MCP
            # This would call the voice-mode MCP server
            # For now, we'll use subprocess to call the CLI

            cmd = [
                "curl", "-s", "-X", "POST",
                f"http://{self.voice_mode_host}:{self.voice_mode_port}/start_voice_mode",
                "-H", "Content-Type: application/json",
                "-d", json.dumps({"model": "base", "chunk_duration": 3}),
            ]

            # Fall back to checking if voice mode is running
            # by examining the transcriptions endpoint
            status_cmd = [
                "curl", "-s",
                f"http://{self.voice_mode_host}:{self.voice_mode_port}/get_voice_mode_status",
            ]

            # For now, assume voice mode is managed externally via MCP
            # The daemon will poll transcriptions regardless
            return True

        except Exception as e:
            logger.error("voice_mode_check_failed", error=str(e))
            return True  # Continue anyway, will fail gracefully on poll

    async def _poll_loop(self) -> None:
        """Main polling loop for transcriptions."""
        while self._listening:
            try:
                if not self._muted:
                    await self._poll_transcriptions()

                self._stats["total_polls"] += 1
                await asyncio.sleep(self.poll_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("poll_loop_error", error=str(e))
                await asyncio.sleep(self.poll_interval_seconds * 2)

    async def _poll_transcriptions(self) -> None:
        """Poll voice mode for new transcriptions."""
        try:
            # Get transcriptions via MCP call
            # In the actual implementation, this would use the MCP client
            # For now, we'll read from a file or use subprocess

            # This creates a dependency on voice-mode MCP transcriptions
            transcription_file = Path("/tmp/pixel_transcriptions.json")

            if not transcription_file.exists():
                return

            with open(transcription_file) as f:
                data = json.load(f)

            transcriptions = data.get("transcriptions", [])

            for t in transcriptions:
                # Skip already processed
                t_id = f"{t.get('timestamp')}:{t.get('text', '')[:20]}"
                if t_id in self._processed_transcription_ids:
                    continue

                self._processed_transcription_ids.add(t_id)
                self._stats["transcriptions_received"] += 1

                # Process through audio filter
                text = t.get("text", "")
                timestamp_str = t.get("timestamp", "")

                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                except (ValueError, TypeError):
                    timestamp = datetime.now()

                event = await self.audio_filter.process_transcription(text, timestamp)

                if event:
                    self._stats["speech_events_processed"] += 1

                    if event.is_directed_at_pixel:
                        self._stats["directed_speech_detected"] += 1
                        await self._handle_directed_speech(event)

            # Keep only recent IDs to prevent memory growth
            if len(self._processed_transcription_ids) > 500:
                self._processed_transcription_ids = set(
                    list(self._processed_transcription_ids)[-250:]
                )

        except FileNotFoundError:
            pass  # No transcriptions file yet
        except Exception as e:
            logger.warning("poll_transcriptions_error", error=str(e))

    async def _handle_directed_speech(self, event: AudioEvent) -> None:
        """Handle speech that is directed at Pixel.

        Args:
            event: The audio event
        """
        logger.info(
            "directed_speech_detected",
            text=event.text[:100],
            confidence=event.confidence,
        )

        # Call registered handlers
        for handler in self._speech_handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error("speech_handler_error", error=str(e))

    async def get_environmental_state(self) -> EnvironmentalState:
        """Get current environmental state.

        Returns:
            Current EnvironmentalState
        """
        filter_stats = self.audio_filter.get_stats()
        recent_speech = self.audio_filter.get_recent_speech(10)
        directed_speech = self.audio_filter.get_recent_directed_speech(5)

        # Determine ambient noise level
        if filter_stats["total_processed"] == 0:
            ambient_level = "quiet"
        elif filter_stats["pass_rate"] < 0.1:
            ambient_level = "noisy"  # Lots of filtered noise
        elif filter_stats["pass_rate"] < 0.5:
            ambient_level = "moderate"
        else:
            ambient_level = "quiet"

        # Determine human presence
        recent_human_speech = [
            e for e in recent_speech
            if e.source_type == AudioSourceType.HUMAN_SPEECH
            and (datetime.now() - e.timestamp).total_seconds() < 300
        ]
        human_presence = len(recent_human_speech) > 0

        # Last directed speech time
        last_directed = None
        if directed_speech:
            last_directed = directed_speech[-1].timestamp

        return EnvironmentalState(
            is_listening=self.is_listening,
            is_muted=self._muted,
            recent_speech_count=len(recent_speech),
            last_directed_speech=last_directed,
            ambient_noise_level=ambient_level,
            human_presence_detected=human_presence,
            timestamp=datetime.now(),
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get listener statistics.

        Returns:
            Statistics dictionary
        """
        return {
            **self._stats,
            "is_listening": self._listening,
            "is_muted": self._muted,
            "filter_stats": self.audio_filter.get_stats(),
        }


class VoiceModeIntegration:
    """
    Integration layer between Environmental Listener and Voice Mode MCP.

    Coordinates:
    - TTS output marking for feedback prevention
    - STT state management
    - Transcription polling
    """

    def __init__(self, listener: EnvironmentalListener):
        """Initialize Voice Mode Integration.

        Args:
            listener: Environmental Listener instance
        """
        self.listener = listener
        self._tts_in_progress = False

    async def speak(
        self,
        text: str,
        voice: str = "en-IE-EmilyNeural",
    ) -> bool:
        """Speak text with automatic feedback prevention.

        Args:
            text: Text to speak
            voice: Voice to use

        Returns:
            True if successful
        """
        try:
            # Mark TTS start
            self.listener.mark_tts_start()
            self._tts_in_progress = True

            # Generate and play TTS
            edge_tts_cmd = [
                "edge-tts",
                "--voice", voice,
                "--text", text,
                "--write-media", "/tmp/pixel_speech.mp3",
            ]

            process = await asyncio.create_subprocess_exec(
                *edge_tts_cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )

            _, stderr = await process.communicate()

            if process.returncode == 0:
                # Play the audio
                play_cmd = ["mpv", "--no-terminal", "/tmp/pixel_speech.mp3"]
                play_process = await asyncio.create_subprocess_exec(
                    *play_cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await play_process.communicate()
                return True

            return False

        except Exception as e:
            logger.error("speak_error", error=str(e))
            return False

        finally:
            # Mark TTS end
            self.listener.mark_tts_end()
            self._tts_in_progress = False

    async def respond_to_speech(
        self,
        event: AudioEvent,
        response: str,
    ) -> None:
        """Respond to detected speech.

        Args:
            event: The detected speech event
            response: Response to speak
        """
        logger.info(
            "responding_to_speech",
            original=event.text[:50],
            response=response[:50],
        )

        await self.speak(response)

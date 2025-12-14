"""Audio Filter - Smart filtering for environmental audio awareness.

Filters out:
- Pixel's own TTS voice (prevents feedback loop)
- Background music and drum machines
- Whisper hallucinations (blank audio, music markers)
- Ambient noise patterns

Only passes through actual human speech directed at Pixel.
"""

import asyncio
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Callable, Any
from collections import deque

from ..utils.logging import get_logger


logger = get_logger(__name__)


class AudioSourceType(Enum):
    """Types of audio sources."""
    UNKNOWN = "unknown"
    HUMAN_SPEECH = "human_speech"
    TTS_OUTPUT = "tts_output"
    MUSIC = "music"
    DRUM_MACHINE = "drum_machine"
    AMBIENT_NOISE = "ambient_noise"
    WHISPER_HALLUCINATION = "whisper_hallucination"
    SYSTEM_SOUND = "system_sound"


@dataclass
class AudioEvent:
    """A filtered audio event."""
    text: str
    timestamp: datetime
    source_type: AudioSourceType
    confidence: float
    is_directed_at_pixel: bool
    raw_transcription: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class AudioFilter:
    """
    Intelligent audio filter for environmental awareness.

    Responsibilities:
    - Track TTS output windows to prevent feedback
    - Filter known noise patterns (Whisper hallucinations, music)
    - Detect speech directed at Pixel (wake words, context)
    - Maintain audio event history for context
    """

    # Whisper hallucination patterns
    WHISPER_HALLUCINATIONS = {
        "[BLANK_AUDIO]",
        "(phone ringing)",
        "(music)",
        "(music playing)",
        "(singing)",
        "(drums)",
        "(guitar)",
        "(applause)",
        "(laughter)",
        "(silence)",
        "(inaudible)",
        "(background noise)",
        "(static)",
        "(beep)",
        "(bell)",
        "(buzzing)",
        "(clicking)",
        "(coughing)",
        "(door)",
        "(footsteps)",
        "(typing)",
        "...",
        "",
        ".",
        " ",
        "Thank you.",
        "Thanks for watching!",
        "Please subscribe.",
        "See you next time.",
        "Goodbye.",
        "The end.",
    }

    # Patterns that indicate Whisper repetition/hallucination
    REPETITION_PATTERNS = [
        r"^(.{2,20})\1{3,}$",  # Same phrase repeated 4+ times
        r"^(Thank you\.?\s*){2,}$",  # Repeated "Thank you"
        r"^(Yes\.?\s*){3,}$",  # Repeated "Yes"
        r"^(No\.?\s*){3,}$",  # Repeated "No"
        r"^(Okay\.?\s*){3,}$",  # Repeated "Okay"
        r"^♪.*♪$",  # Music notes
        r"^\[.*\]$",  # Bracketed markers
        r"^\(.*\)$",  # Parenthesized markers
    ]

    # Wake words that indicate speech directed at Pixel
    WAKE_WORDS = {
        "pixel",
        "hey pixel",
        "hi pixel",
        "okay pixel",
        "yo pixel",
        "pixie",
        "pix",
    }

    # Music/drum machine detection patterns (context-dependent to reduce false positives)
    MUSIC_PATTERNS = [
        r"\bboom\s*(bap|boom|tss|chick)\b",  # Classic hip-hop beat
        r"\b(tss|snare|hi-hat|cymbal)\s+(tss|kick|snare|hi-hat|cymbal)\b",  # Multiple drum sounds together
        r"\bone\s+two\s+three\s+four\s+(one|and|beat)\b",  # Count-in with continuation
        r"\bbeat\s*(drop|drops)\b",
        r"♪|♫|🎵|🎶",
        r"\b(bass|drum|synth)\s*(line|beat|loop)\b",
        r"\bkick\s+(drum|and\s+snare|snare)\b",  # Kick only with drum context
    ]

    def __init__(self, config: dict):
        """Initialize Audio Filter.

        Args:
            config: Daemon configuration
        """
        self.config = config

        # Configuration
        filter_config = config.get("components", {}).get("audio_filter", {})

        # TTS feedback prevention
        self.tts_cooldown_seconds = filter_config.get("tts_cooldown_seconds", 2.0)
        self._last_tts_end_time: Optional[datetime] = None
        self._tts_active = False

        # Filtering settings
        self.min_text_length = filter_config.get("min_text_length", 3)
        self.max_repetition_ratio = filter_config.get("max_repetition_ratio", 0.5)

        # History for context
        self.event_history: deque = deque(maxlen=100)
        self.raw_transcription_history: deque = deque(maxlen=50)

        # Callbacks for valid speech events
        self._speech_callbacks: List[Callable[[AudioEvent], Any]] = []

        # Custom ignore patterns (can be extended)
        self._custom_ignore_patterns: Set[str] = set()

        # Stats
        self._stats = {
            "total_processed": 0,
            "passed_through": 0,
            "filtered_hallucinations": 0,
            "filtered_tts_feedback": 0,
            "filtered_music": 0,
            "filtered_noise": 0,
            "directed_at_pixel": 0,
        }

        logger.info(
            "audio_filter_initialized",
            tts_cooldown=self.tts_cooldown_seconds,
            wake_words=list(self.WAKE_WORDS),
        )

    def mark_tts_start(self) -> None:
        """Mark that TTS output has started."""
        self._tts_active = True
        logger.debug("tts_started")

    def mark_tts_end(self) -> None:
        """Mark that TTS output has ended."""
        self._tts_active = False
        self._last_tts_end_time = datetime.now()
        logger.debug("tts_ended")

    def is_in_tts_window(self) -> bool:
        """Check if we're in TTS output or cooldown window.

        Returns:
            True if TTS is active or cooldown hasn't elapsed
        """
        if self._tts_active:
            return True

        if self._last_tts_end_time:
            elapsed = (datetime.now() - self._last_tts_end_time).total_seconds()
            if elapsed < self.tts_cooldown_seconds:
                return True

        return False

    def add_ignore_pattern(self, pattern: str) -> None:
        """Add a custom pattern to ignore.

        Args:
            pattern: Text pattern to ignore
        """
        self._custom_ignore_patterns.add(pattern.lower().strip())
        logger.info("ignore_pattern_added", pattern=pattern)

    def remove_ignore_pattern(self, pattern: str) -> None:
        """Remove a custom ignore pattern.

        Args:
            pattern: Pattern to remove
        """
        self._custom_ignore_patterns.discard(pattern.lower().strip())

    def register_speech_callback(self, callback: Callable[[AudioEvent], Any]) -> None:
        """Register a callback for valid speech events.

        Args:
            callback: Function to call when valid speech is detected
        """
        self._speech_callbacks.append(callback)

    async def process_transcription(
        self,
        text: str,
        timestamp: Optional[datetime] = None,
    ) -> Optional[AudioEvent]:
        """Process a transcription and determine if it should be passed through.

        Args:
            text: Raw transcription text
            timestamp: Transcription timestamp (default: now)

        Returns:
            AudioEvent if the transcription passes filters, None otherwise
        """
        self._stats["total_processed"] += 1
        timestamp = timestamp or datetime.now()

        # Store raw transcription
        self.raw_transcription_history.append({
            "text": text,
            "timestamp": timestamp,
        })

        # Step 1: Check TTS feedback window
        if self.is_in_tts_window():
            self._stats["filtered_tts_feedback"] += 1
            logger.debug("filtered_tts_feedback", text=text[:50])
            return None

        # Step 2: Clean and normalize text
        clean_text = text.strip()

        # Step 3: Check for Whisper hallucinations
        if self._is_whisper_hallucination(clean_text):
            self._stats["filtered_hallucinations"] += 1
            logger.debug("filtered_hallucination", text=clean_text[:50])
            return None

        # Step 4: Check for music/drum patterns
        if self._is_music_pattern(clean_text):
            self._stats["filtered_music"] += 1
            logger.debug("filtered_music", text=clean_text[:50])
            return None

        # Step 5: Check custom ignore patterns
        if self._matches_custom_ignore(clean_text):
            self._stats["filtered_noise"] += 1
            logger.debug("filtered_custom", text=clean_text[:50])
            return None

        # Step 6: Check minimum length
        if len(clean_text) < self.min_text_length:
            self._stats["filtered_noise"] += 1
            return None

        # Step 7: Determine source type and if directed at Pixel
        source_type = self._classify_audio_source(clean_text)
        is_directed = self._is_directed_at_pixel(clean_text)
        confidence = self._calculate_confidence(clean_text)

        if is_directed:
            self._stats["directed_at_pixel"] += 1

        # Create event
        event = AudioEvent(
            text=clean_text,
            timestamp=timestamp,
            source_type=source_type,
            confidence=confidence,
            is_directed_at_pixel=is_directed,
            raw_transcription=text,
        )

        # Store in history
        self.event_history.append(event)
        self._stats["passed_through"] += 1

        logger.info(
            "audio_event_passed",
            text=clean_text[:100],
            directed_at_pixel=is_directed,
            confidence=confidence,
        )

        # Call registered callbacks
        for callback in self._speech_callbacks:
            try:
                result = callback(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error("speech_callback_error", error=str(e))

        return event

    def _is_whisper_hallucination(self, text: str) -> bool:
        """Check if text is a known Whisper hallucination.

        Args:
            text: Text to check

        Returns:
            True if it's a hallucination
        """
        # Exact match
        if text in self.WHISPER_HALLUCINATIONS:
            return True

        # Case-insensitive exact match
        if text.lower() in {h.lower() for h in self.WHISPER_HALLUCINATIONS}:
            return True

        # Repetition patterns
        for pattern in self.REPETITION_PATTERNS:
            if re.match(pattern, text, re.IGNORECASE):
                return True

        # Check for high repetition ratio
        if self._has_high_repetition(text):
            return True

        return False

    def _has_high_repetition(self, text: str) -> bool:
        """Check if text has high character/word repetition.

        Args:
            text: Text to check

        Returns:
            True if repetition ratio exceeds threshold
        """
        if len(text) < 10:
            return False

        words = text.lower().split()
        if len(words) < 3:
            return False

        unique_words = set(words)
        repetition_ratio = 1 - (len(unique_words) / len(words))

        return repetition_ratio > self.max_repetition_ratio

    def _is_music_pattern(self, text: str) -> bool:
        """Check if text matches music/drum patterns.

        Args:
            text: Text to check

        Returns:
            True if it's music/drums
        """
        text_lower = text.lower()

        for pattern in self.MUSIC_PATTERNS:
            if re.search(pattern, text_lower):
                return True

        return False

    def _matches_custom_ignore(self, text: str) -> bool:
        """Check if text matches custom ignore patterns.

        Args:
            text: Text to check

        Returns:
            True if it should be ignored
        """
        text_lower = text.lower()

        for pattern in self._custom_ignore_patterns:
            if pattern in text_lower:
                return True

        return False

    def _classify_audio_source(self, text: str) -> AudioSourceType:
        """Classify the source type of the audio.

        Args:
            text: Transcribed text

        Returns:
            Source type classification
        """
        text_lower = text.lower()

        # Check for music patterns
        for pattern in self.MUSIC_PATTERNS:
            if re.search(pattern, text_lower):
                return AudioSourceType.MUSIC

        # Default to human speech if it passed all filters
        return AudioSourceType.HUMAN_SPEECH

    def _is_directed_at_pixel(self, text: str) -> bool:
        """Determine if the speech is directed at Pixel.

        Args:
            text: Transcribed text

        Returns:
            True if directed at Pixel
        """
        text_lower = text.lower()

        # Check for wake words at the start
        for wake_word in self.WAKE_WORDS:
            if text_lower.startswith(wake_word):
                return True
            # Also check if wake word is early in the text
            if f" {wake_word}" in text_lower[:50]:
                return True

        # Check for direct address patterns
        direct_patterns = [
            r"^(hey|hi|hello|yo)\s+pixel",
            r"pixel[\s,]+can you",
            r"pixel[\s,]+please",
            r"pixel[\s,]+what",
            r"pixel[\s,]+how",
            r"pixel[\s,]+why",
        ]

        for pattern in direct_patterns:
            if re.search(pattern, text_lower):
                return True

        return False

    def _calculate_confidence(self, text: str) -> float:
        """Calculate confidence that this is valid human speech.

        Args:
            text: Transcribed text

        Returns:
            Confidence score 0.0-1.0
        """
        confidence = 0.5  # Base confidence

        # Longer text = higher confidence
        length = len(text)
        if length > 50:
            confidence += 0.1
        if length > 100:
            confidence += 0.1

        # Proper punctuation = higher confidence
        if any(p in text for p in ".?!,"):
            confidence += 0.1

        # Contains common words = higher confidence
        common_words = {"the", "a", "is", "are", "I", "you", "we", "it", "that", "this"}
        words = set(text.lower().split())
        if words & common_words:
            confidence += 0.1

        # Directed at Pixel = higher confidence
        if self._is_directed_at_pixel(text):
            confidence += 0.1

        return min(1.0, confidence)

    def get_recent_speech(self, count: int = 5) -> List[AudioEvent]:
        """Get recent valid speech events.

        Args:
            count: Number of events to return

        Returns:
            List of recent AudioEvents
        """
        return list(self.event_history)[-count:]

    def get_recent_directed_speech(self, count: int = 5) -> List[AudioEvent]:
        """Get recent speech directed at Pixel.

        Args:
            count: Number of events to return

        Returns:
            List of AudioEvents directed at Pixel
        """
        directed = [e for e in self.event_history if e.is_directed_at_pixel]
        return directed[-count:]

    def get_stats(self) -> Dict[str, Any]:
        """Get filter statistics.

        Returns:
            Statistics dictionary
        """
        pass_rate = 0
        if self._stats["total_processed"] > 0:
            pass_rate = self._stats["passed_through"] / self._stats["total_processed"]

        return {
            **self._stats,
            "pass_rate": pass_rate,
            "custom_ignore_count": len(self._custom_ignore_patterns),
            "history_size": len(self.event_history),
        }

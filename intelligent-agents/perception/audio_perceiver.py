#!/usr/bin/env python3
"""
Audio Perceiver - Pre-Cognition Agent for Microphone Input

This agent processes raw audio into semantic observations
before feeding them to the consciousness daemon.

Capabilities:
- Speech/voice activity detection
- Ambient sound classification
- Volume level analysis
- Silence detection
- Tone/frequency analysis

Outputs structured, tagged observations with confidence scores.
"""

import sounddevice as sd
import webrtcvad
import numpy as np
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from scipy import signal
from collections import deque

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("audio_perceiver")

# Configuration
SAMPLE_RATE = 16000  # Hz - WebRTC VAD requires 8kHz, 16kHz, 32kHz, or 48kHz
FRAME_DURATION = 30  # ms - WebRTC VAD supports 10, 20, or 30ms
CHUNK_SIZE = int(SAMPLE_RATE * FRAME_DURATION / 1000)  # samples per frame
PERCEPTION_QUEUE = Path("/tmp/perception_queue_audio.json")
ANALYSIS_WINDOW = 5  # seconds - analyze audio over 5-second windows


class AudioPerceiver:
    """
    Pre-cognition agent for audio perception
    Processes microphone input into semantic observations
    """

    def __init__(self, device: Optional[int] = None, aggressiveness: int = 2):
        """
        Initialize audio perceiver

        Args:
            device: Audio device index (None = default)
            aggressiveness: VAD aggressiveness (0-3, higher = more aggressive filtering)
        """
        self.device = device
        self.sample_rate = SAMPLE_RATE
        self.chunk_size = CHUNK_SIZE
        self.last_observation = None

        # Voice Activity Detection
        self.vad = webrtcvad.Vad(aggressiveness)

        # Sliding window for audio analysis
        self.audio_buffer = deque(maxlen=int(SAMPLE_RATE * ANALYSIS_WINDOW))
        self.speech_frames = deque(maxlen=int(ANALYSIS_WINDOW * 1000 / FRAME_DURATION))

        # State tracking
        self.silence_start = None
        self.last_speech_time = None

        logger.info(f"Audio perceiver initialized (device: {device}, rate: {SAMPLE_RATE}Hz)")

    def detect_speech(self, audio_chunk: bytes) -> bool:
        """
        Detect if audio chunk contains speech using WebRTC VAD

        Args:
            audio_chunk: Raw audio bytes (16-bit PCM)

        Returns:
            True if speech detected
        """
        try:
            # WebRTC VAD expects bytes, 16-bit PCM
            is_speech = self.vad.is_speech(audio_chunk, self.sample_rate)
            return is_speech
        except Exception as e:
            logger.error(f"Speech detection failed: {e}")
            return False

    def analyze_volume(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """
        Analyze volume levels

        Args:
            audio_data: Audio samples as numpy array

        Returns:
            Volume analysis dict
        """
        # Calculate RMS (Root Mean Square) volume
        rms = np.sqrt(np.mean(audio_data**2))

        # Convert to dB (with floor to avoid log(0))
        db = 20 * np.log10(rms + 1e-10)

        # Classify volume level
        if db < -50:
            level = "silent"
        elif db < -30:
            level = "quiet"
        elif db < -10:
            level = "normal"
        else:
            level = "loud"

        return {
            "rms": float(rms),
            "db": float(db),
            "level": level
        }

    def analyze_frequency(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """
        Basic frequency analysis

        Args:
            audio_data: Audio samples

        Returns:
            Frequency analysis dict
        """
        # Compute FFT
        fft = np.fft.rfft(audio_data)
        freqs = np.fft.rfftfreq(len(audio_data), 1/self.sample_rate)
        magnitudes = np.abs(fft)

        # Find dominant frequency
        dominant_idx = np.argmax(magnitudes)
        dominant_freq = freqs[dominant_idx]

        # Classify frequency range
        if dominant_freq < 300:
            freq_range = "low"  # Bass, rumble
        elif dominant_freq < 2000:
            freq_range = "mid"  # Human voice range
        else:
            freq_range = "high"  # Treble, hiss

        return {
            "dominant_frequency_hz": float(dominant_freq),
            "frequency_range": freq_range
        }

    def classify_ambient_sound(
        self,
        speech_ratio: float,
        volume: Dict[str, Any],
        frequency: Dict[str, Any]
    ) -> List[str]:
        """
        Classify ambient sounds based on features

        Args:
            speech_ratio: Ratio of frames with speech (0-1)
            volume: Volume analysis
            frequency: Frequency analysis

        Returns:
            List of detected sound types
        """
        sounds = []

        # Silence
        if volume["level"] == "silent":
            sounds.append("silence")
            return sounds

        # Speech
        if speech_ratio > 0.3:  # 30% of frames have speech
            sounds.append("speech")

        # Typing (high frequency, rhythmic)
        if frequency["frequency_range"] == "high" and volume["level"] in ["quiet", "normal"]:
            if speech_ratio < 0.2:  # Not much speech
                sounds.append("keyboard_typing")

        # Music (sustained mid frequencies)
        if frequency["frequency_range"] == "mid" and volume["level"] in ["normal", "loud"]:
            if speech_ratio < 0.4:  # Not continuous speech
                sounds.append("music_or_media")

        # Ambient noise
        if volume["level"] in ["quiet", "normal"] and speech_ratio < 0.1:
            if frequency["frequency_range"] == "low":
                sounds.append("ambient_noise")

        # Fan/HVAC (low frequency, constant)
        if frequency["frequency_range"] == "low" and volume["level"] == "quiet":
            sounds.append("fan_noise")

        # Unknown if nothing detected
        if not sounds:
            sounds.append("unknown")

        return sounds

    def perceive(self, audio_data: np.ndarray, audio_bytes: bytes) -> Dict[str, Any]:
        """
        Main perception function - processes audio into semantic observation

        Args:
            audio_data: Audio samples as numpy array
            audio_bytes: Raw audio bytes for VAD

        Returns:
            Semantic observation dict
        """
        # Add to buffer
        self.audio_buffer.extend(audio_data)

        # Speech detection
        is_speech = self.detect_speech(audio_bytes)
        self.speech_frames.append(is_speech)

        # Track speech timing
        if is_speech:
            self.last_speech_time = time.time()
            if self.silence_start:
                self.silence_start = None
        else:
            if not self.silence_start:
                self.silence_start = time.time()

        # Calculate speech ratio over window
        speech_ratio = sum(self.speech_frames) / max(len(self.speech_frames), 1)

        # Analyze full buffer
        buffer_array = np.array(list(self.audio_buffer))
        volume = self.analyze_volume(buffer_array)
        frequency = self.analyze_frequency(buffer_array)

        # Classify sounds
        ambient_sounds = self.classify_ambient_sound(speech_ratio, volume, frequency)

        # Calculate silence duration
        if self.silence_start:
            silence_duration = int(time.time() - self.silence_start)
        else:
            silence_duration = 0

        # Build observation
        observation = {
            "source": "audio_perceiver",
            "timestamp": datetime.now().isoformat(),
            "speech_detected": is_speech or speech_ratio > 0.2,
            "speech_ratio": float(speech_ratio),
            "ambient_sounds": ambient_sounds,
            "volume": volume,
            "frequency": frequency,
            "silence_duration_seconds": silence_duration,
            "confidence": 0.7,  # Overall confidence
            "summary": self._generate_summary(ambient_sounds, volume, speech_ratio, silence_duration)
        }

        self.last_observation = observation
        return observation

    def _generate_summary(
        self,
        sounds: List[str],
        volume: Dict[str, Any],
        speech_ratio: float,
        silence_duration: int
    ) -> str:
        """Generate human-readable summary"""

        if "silence" in sounds:
            if silence_duration > 60:
                return f"Complete silence for {silence_duration}s"
            else:
                return "Silent environment"

        if "speech" in sounds:
            return f"Human speech detected ({speech_ratio*100:.0f}% of audio)"

        if "keyboard_typing" in sounds:
            return "Keyboard typing sounds"

        if "music_or_media" in sounds:
            return f"Music or media playing ({volume['level']} volume)"

        if "ambient_noise" in sounds or "fan_noise" in sounds:
            return f"Ambient background noise ({volume['level']})"

        return f"Unknown sounds ({volume['level']} volume)"

    def write_to_perception_queue(self, observation: Dict[str, Any]):
        """Write observation to shared queue for consciousness daemon"""
        try:
            with open(PERCEPTION_QUEUE, 'w') as f:
                json.dump(observation, f, indent=2)
            logger.debug(f"Audio observation written: {observation['summary']}")
        except Exception as e:
            logger.error(f"Failed to write to perception queue: {e}")

    def audio_callback(self, indata, frames, time_info, status):
        """Callback for sounddevice stream"""
        if status:
            logger.warning(f"Audio callback status: {status}")

        # Convert to mono if stereo
        if len(indata.shape) > 1:
            audio_data = indata[:, 0]
        else:
            audio_data = indata.flatten()

        # Convert to int16 bytes for VAD
        audio_int16 = (audio_data * 32767).astype(np.int16)
        audio_bytes = audio_int16.tobytes()

        # Process observation
        observation = self.perceive(audio_data, audio_bytes)
        self.write_to_perception_queue(observation)

    def run(self, duration_seconds: Optional[int] = None):
        """
        Main loop - continuous audio perception

        Args:
            duration_seconds: Run for this many seconds (None = forever)
        """
        logger.info("Audio perceiver starting continuous perception...")
        start_time = time.time()

        try:
            # Open audio stream
            with sd.InputStream(
                device=self.device,
                samplerate=self.sample_rate,
                channels=1,
                blocksize=self.chunk_size,
                callback=self.audio_callback
            ):
                logger.info(f"Audio stream active (sample rate: {self.sample_rate}Hz)")

                # Run until duration or KeyboardInterrupt
                while True:
                    if duration_seconds and (time.time() - start_time) > duration_seconds:
                        break
                    time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Audio perceiver stopped by user")
        except Exception as e:
            logger.error(f"Audio perceiver failed: {e}", exc_info=True)


def main():
    """Entry point for standalone testing"""
    import argparse

    parser = argparse.ArgumentParser(description="Audio Perceiver - Pre-Cognition Agent")
    parser.add_argument("--duration", type=int, default=30,
                       help="Run for N seconds (default: 30, 0=forever)")
    parser.add_argument("--device", type=int, default=None,
                       help="Audio device index (default: system default)")
    parser.add_argument("--list-devices", action="store_true",
                       help="List available audio devices")
    parser.add_argument("--aggressiveness", type=int, default=2, choices=[0, 1, 2, 3],
                       help="VAD aggressiveness (0=least, 3=most, default: 2)")

    args = parser.parse_args()

    if args.list_devices:
        print("Available audio devices:")
        print(sd.query_devices())
        return

    perceiver = AudioPerceiver(device=args.device, aggressiveness=args.aggressiveness)
    perceiver.run(duration_seconds=args.duration if args.duration > 0 else None)


if __name__ == "__main__":
    main()

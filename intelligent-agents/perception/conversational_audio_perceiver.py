#!/usr/bin/env python3
"""
Conversational Audio Perceiver - Pre-Cognition Agent with Speech-to-Text

Extends audio_perceiver.py with real-time speech transcription using Vosk.

Capabilities:
- All features from audio_perceiver.py
- Speech-to-text transcription (Vosk offline STT)
- Real-time conversation tracking
- Utterance segmentation
- Transcript output to conversation queue

Outputs both perception observations AND transcribed speech.
"""

import sounddevice as sd
import webrtcvad
import numpy as np
import json
import time
import logging
import threading
import queue
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from scipy import signal as scipy_signal
from collections import deque
from vosk import Model, KaldiRecognizer
import noisereduce as nr

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("conversational_audio")

# Configuration
SAMPLE_RATE = 48000  # Hz - QuickCam Pro 9000 native rate (will be downsampled to 16kHz)
TARGET_SAMPLE_RATE = 16000  # Hz - Vosk and VAD target rate
FRAME_DURATION = 200  # ms - Larger buffer to avoid overflow (will split for VAD)
CHUNK_SIZE = int(SAMPLE_RATE * FRAME_DURATION / 1000)
PERCEPTION_QUEUE = Path("/tmp/perception_queue_audio.json")
TRANSCRIPT_QUEUE = Path("/tmp/conversation_transcript.json")
VOSK_MODEL_PATH = Path("/mnt/agentic-system/models/vosk/vosk-model-small-en-us-0.15")
SPEAKING_FLAG = Path("/tmp/agi_speaking.flag")  # Echo cancellation flag
NOISE_PROFILE_FILE = Path("/tmp/noise_profile.npy")  # Calibrated noise profile
PTT_FLAG = Path("/tmp/ptt_active.flag")  # Push-to-talk active flag


class ConversationalAudioPerceiver:
    """
    Pre-cognition agent for audio perception with speech-to-text
    """

    def __init__(self, device: Optional[int] = None, aggressiveness: int = 2):
        """
        Initialize conversational audio perceiver

        Args:
            device: Audio device index (None = default)
            aggressiveness: VAD aggressiveness (0-3)
        """
        self.device = device
        self.sample_rate = SAMPLE_RATE
        self.chunk_size = CHUNK_SIZE

        # Voice Activity Detection
        self.vad = webrtcvad.Vad(aggressiveness)

        # Vosk Speech Recognition
        if not VOSK_MODEL_PATH.exists():
            raise FileNotFoundError(f"Vosk model not found at {VOSK_MODEL_PATH}")

        logger.info(f"Loading Vosk model from {VOSK_MODEL_PATH}...")
        self.model = Model(str(VOSK_MODEL_PATH))
        self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)
        self.recognizer.SetWords(True)  # Enable word-level timestamps
        logger.info("Vosk model loaded successfully")

        # Sliding window for audio analysis
        self.audio_buffer = deque(maxlen=int(SAMPLE_RATE * 5))  # 5-second window
        self.speech_frames = deque(maxlen=int(5 * 1000 / FRAME_DURATION))

        # State tracking
        self.silence_start = None
        self.last_speech_time = None
        self.last_observation = None
        self.last_transcript = None

        # Utterance tracking
        self.current_utterance = []
        self.utterance_start_time = None
        self.min_utterance_gap = 0.5  # seconds of silence to end utterance (reduced for faster response)

        # Noise reduction
        self.noise_profile = None
        self.calibration_samples = []
        self.calibrated = False

        # Listening state tracking
        self.is_listening = True
        self.last_listening_state = True

        # User speech state tracking for beeps
        self.user_was_speaking = False

        # Audio processing queue and worker thread
        self.audio_queue = queue.Queue(maxsize=100)  # Buffer up to 100 chunks (~3 seconds at 30ms/chunk)
        self.processing_thread = None
        self.stop_processing = threading.Event()

        logger.info(f"Conversational audio perceiver initialized (device: {device}, rate: {SAMPLE_RATE}Hz)")

    def detect_speech(self, audio_chunk: bytes, sample_rate: int = None) -> bool:
        """Detect if audio chunk contains speech using WebRTC VAD

        Args:
            audio_chunk: Audio data as bytes
            sample_rate: Sample rate of audio (defaults to 16kHz after downsampling)
        """
        if sample_rate is None:
            sample_rate = TARGET_SAMPLE_RATE  # Use 16kHz after downsampling
        try:
            is_speech = self.vad.is_speech(audio_chunk, sample_rate)
            return is_speech
        except Exception as e:
            logger.error(f"Speech detection failed: {e}")
            return False

    def transcribe_audio(self, audio_data: np.ndarray) -> Optional[str]:
        """
        Transcribe audio using Vosk

        Args:
            audio_data: Audio samples as numpy array

        Returns:
            Transcribed text or None
        """
        try:
            # Convert float32 to int16 for Vosk
            audio_int16 = (audio_data * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()

            # Feed to recognizer
            if self.recognizer.AcceptWaveform(audio_bytes):
                # Full result (end of utterance)
                result = json.loads(self.recognizer.Result())
                text = result.get("text", "").strip()
                return text if text else None
            else:
                # Partial result (ongoing speech)
                partial = json.loads(self.recognizer.PartialResult())
                text = partial.get("partial", "").strip()
                return None  # Don't return partial results yet

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None

    def analyze_volume(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """Analyze volume levels"""
        rms = np.sqrt(np.mean(audio_data**2))
        db = 20 * np.log10(rms + 1e-10)

        if db < -50:
            level = "silent"
        elif db < -30:
            level = "quiet"
        elif db < -10:
            level = "normal"
        else:
            level = "loud"

        return {"rms": float(rms), "db": float(db), "level": level}

    def analyze_frequency(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """Basic frequency analysis"""
        fft = np.fft.rfft(audio_data)
        freqs = np.fft.rfftfreq(len(audio_data), 1/self.sample_rate)
        magnitudes = np.abs(fft)

        dominant_idx = np.argmax(magnitudes)
        dominant_freq = freqs[dominant_idx]

        if dominant_freq < 300:
            freq_range = "low"
        elif dominant_freq < 2000:
            freq_range = "mid"
        else:
            freq_range = "high"

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
        """Classify ambient sounds based on features"""
        sounds = []

        if volume["level"] == "silent":
            sounds.append("silence")
            return sounds

        if speech_ratio > 0.3:
            sounds.append("speech")

        if frequency["frequency_range"] == "high" and volume["level"] in ["quiet", "normal"]:
            if speech_ratio < 0.2:
                sounds.append("keyboard_typing")

        if frequency["frequency_range"] == "mid" and volume["level"] in ["normal", "loud"]:
            if speech_ratio < 0.4:
                sounds.append("music_or_media")

        if volume["level"] in ["quiet", "normal"] and speech_ratio < 0.1:
            if frequency["frequency_range"] == "low":
                sounds.append("ambient_noise")

        if frequency["frequency_range"] == "low" and volume["level"] == "quiet":
            sounds.append("fan_noise")

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

        # Calculate speech ratio for additional detection
        speech_ratio = 0.0
        if len(audio_data) > 0:
            rms = np.sqrt(np.mean(audio_data**2))
            speech_ratio = min(rms / 0.1, 1.0)  # Normalize to 0-1

        # Track speech timing and play beeps for user speech transitions
        user_is_speaking = is_speech or speech_ratio > 0.2

        if user_is_speaking:
            # User started speaking - play high beep
            if not self.user_was_speaking:
                self.play_audio_cue("listening_start")  # High beep = user started
                logger.info("🎤 User started speaking (speech_detected=%s, ratio=%.2f)", is_speech, speech_ratio)

            self.last_speech_time = time.time()
            if self.silence_start:
                self.silence_start = None
        else:
            if not self.silence_start:
                self.silence_start = time.time()

        # Update previous state
        self.user_was_speaking = user_is_speaking

        # Calculate speech ratio
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

        # Transcribe if speech detected (always listening OR push-to-talk active)
        transcribed_text = None
        ptt_active = PTT_FLAG.exists()

        # Always listen for speech, OR explicitly when PTT is active
        if is_speech or speech_ratio > 0.2 or ptt_active:
            logger.debug("🎙️ Transcribing audio (is_speech=%s, ratio=%.2f, ptt=%s)", is_speech, speech_ratio, ptt_active)
            transcribed_text = self.transcribe_audio(audio_data)
            if transcribed_text:
                logger.info("✅ Transcribed: %s", transcribed_text)
                self.handle_transcription(transcribed_text)
            else:
                logger.debug("⏳ No transcription yet (Vosk accumulating)")

        # Build observation
        observation = {
            "source": "conversational_audio_perceiver",
            "timestamp": datetime.now().isoformat(),
            "speech_detected": is_speech or speech_ratio > 0.2,
            "speech_ratio": float(speech_ratio),
            "ambient_sounds": ambient_sounds,
            "volume": volume,
            "frequency": frequency,
            "silence_duration_seconds": silence_duration,
            "transcribed_text": transcribed_text,  # NEW: Include transcription
            "confidence": 0.7,
            "summary": self._generate_summary(ambient_sounds, volume, speech_ratio, silence_duration)
        }

        self.last_observation = observation
        return observation

    def handle_transcription(self, text: str):
        """
        Handle completed transcription

        Args:
            text: Transcribed speech
        """
        current_time = time.time()

        # Start new utterance if needed
        if not self.utterance_start_time:
            self.utterance_start_time = current_time

        # Add to current utterance
        self.current_utterance.append(text)

        # Check if utterance is complete (silence gap)
        if self.silence_start and (current_time - self.silence_start) > self.min_utterance_gap:
            # Utterance complete - write to transcript queue
            complete_utterance = " ".join(self.current_utterance)
            self.write_to_transcript_queue(complete_utterance)

            # Play low beep to indicate utterance complete
            self.play_audio_cue("listening_stop")  # Low beep = utterance ended
            logger.info("📝 Utterance completed: '%s'", complete_utterance)

            # Reset utterance tracking
            self.current_utterance = []
            self.utterance_start_time = None

    def write_to_transcript_queue(self, utterance: str):
        """Write completed utterance to transcript queue"""
        try:
            transcript = {
                "timestamp": datetime.now().isoformat(),
                "speaker": "user",  # Assuming user is speaking
                "utterance": utterance,
                "confidence": 0.8
            }

            # Append to transcript log
            transcripts = []
            if TRANSCRIPT_QUEUE.exists():
                with open(TRANSCRIPT_QUEUE, 'r') as f:
                    try:
                        transcripts = json.load(f)
                        if not isinstance(transcripts, list):
                            transcripts = []
                    except json.JSONDecodeError:
                        transcripts = []

            transcripts.append(transcript)

            # Keep last 100 utterances
            if len(transcripts) > 100:
                transcripts = transcripts[-100:]

            with open(TRANSCRIPT_QUEUE, 'w') as f:
                json.dump(transcripts, f, indent=2)

            logger.info("💾 Transcript saved to file: '%s'", utterance)
            self.last_transcript = utterance

        except Exception as e:
            logger.error(f"Failed to write transcript: {e}")

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

    def audio_processing_worker(self):
        """Worker thread that processes audio from queue"""
        logger.info("Audio processing worker thread started")

        # VAD requires 30ms frames at 16kHz (480 samples)
        vad_frame_samples = int(TARGET_SAMPLE_RATE * 0.03)  # 480 samples

        while not self.stop_processing.is_set():
            try:
                # Get audio from queue (with timeout to check stop flag)
                audio_data, timestamp = self.audio_queue.get(timeout=0.1)

                # Split large frames into 30ms chunks for VAD
                # audio_data is already downsampled to 16kHz in callback
                total_samples = len(audio_data)

                # Process in 30ms segments
                for i in range(0, total_samples, vad_frame_samples):
                    chunk = audio_data[i:i+vad_frame_samples]

                    # Only process complete 30ms frames (skip partial frames at end)
                    if len(chunk) == vad_frame_samples:
                        # Convert to int16 bytes for VAD
                        audio_int16 = (chunk * 32767).astype(np.int16)
                        audio_bytes = audio_int16.tobytes()

                        # Process observation (can take time - we're in worker thread)
                        observation = self.perceive(chunk, audio_bytes)
                        self.write_to_perception_queue(observation)

            except queue.Empty:
                # No audio in queue - just continue
                continue
            except Exception as e:
                logger.error(f"Audio processing error: {e}")

        logger.info("Audio processing worker thread stopped")

    def play_audio_cue(self, cue_type: str):
        """
        Play audio feedback cue for listening state changes

        Args:
            cue_type: "listening_start" or "listening_stop"
        """
        try:
            import subprocess
            import struct
            import math

            # Generate simple sine wave tone
            # listening_start: 800Hz beep (higher pitch)
            # listening_stop: 400Hz beep (lower pitch)

            freq = 800 if cue_type == "listening_start" else 400
            duration = 0.1  # 100ms beep
            sample_rate = 16000

            # Generate sine wave samples
            num_samples = int(sample_rate * duration)
            samples = []
            for i in range(num_samples):
                # Generate sine wave
                sample = int(32767 * 0.3 * math.sin(2 * math.pi * freq * i / sample_rate))
                samples.append(struct.pack('<h', sample))  # 16-bit little-endian

            audio_data = b''.join(samples)

            # Play via paplay
            proc = subprocess.Popen(
                ['paplay', '--raw', '--rate=16000', '--channels=1', '--format=s16le'],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            proc.communicate(input=audio_data, timeout=0.5)

            logger.debug(f"Audio cue: {cue_type} ({freq}Hz)")

        except Exception as e:
            # Silently fail if audio playback not available
            logger.debug(f"Could not play audio cue: {e}")

    def apply_noise_reduction(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Apply noise reduction to filter out fan noise and ambient sounds

        Args:
            audio_data: Raw audio samples

        Returns:
            Cleaned audio samples
        """
        try:
            # Check if chunk is large enough for noise reduction
            if len(audio_data) < 512:
                # Too small - skip noise reduction but still return data
                return audio_data

            # Apply spectral gating noise reduction with small chunk parameters
            reduced = nr.reduce_noise(
                y=audio_data,
                sr=self.sample_rate,
                stationary=True,  # Fan noise is stationary
                prop_decrease=0.8,  # Aggressive reduction for loud fans
                n_fft=256,  # Smaller FFT for small chunks
                hop_length=64  # Smaller hop for better temporal resolution
            )
            return reduced
        except Exception as e:
            logger.debug(f"Noise reduction skipped: {e}")
            return audio_data  # Return original if reduction fails

    def apply_agc(self, audio_data: np.ndarray, target_db: float = -20.0) -> np.ndarray:
        """
        Apply Automatic Gain Control to normalize volume

        Args:
            audio_data: Audio samples
            target_db: Target volume in dB

        Returns:
            Gain-adjusted audio
        """
        try:
            # Calculate current RMS level
            rms = np.sqrt(np.mean(audio_data**2))
            current_db = 20 * np.log10(rms + 1e-10)

            # Calculate required gain
            gain_db = target_db - current_db
            gain_linear = 10 ** (gain_db / 20)

            # Limit gain to prevent over-amplification
            gain_linear = np.clip(gain_linear, 0.1, 10.0)

            return audio_data * gain_linear
        except Exception as e:
            logger.error(f"AGC failed: {e}")
            return audio_data

    def audio_callback(self, indata, frames, time_info, status):
        """Callback for sounddevice stream with echo cancellation and noise reduction"""
        if status:
            logger.warning(f"Audio callback status: {status}")

        # ACOUSTIC ECHO CANCELLATION: Check if AI is speaking
        if SPEAKING_FLAG.exists():
            # AI is speaking - mute microphone to prevent feedback
            if self.is_listening:
                self.is_listening = False
                logger.debug("Microphone muted - AI speaking")
            return  # Skip all processing while AI speaks

        # AI stopped speaking - resume listening (no beep here)
        if not self.is_listening:
            self.is_listening = True
            logger.debug("Microphone active - listening resumed")

        # Convert to mono if stereo
        if len(indata.shape) > 1:
            audio_data = indata[:, 0]
        else:
            audio_data = indata.flatten()

        # DOWNSAMPLE to 16kHz using simple decimation (48kHz÷3=16kHz)
        # Much faster than scipy.signal.resample for real-time processing
        if SAMPLE_RATE == 48000:
            audio_data = audio_data[::3]  # Keep every 3rd sample
        elif SAMPLE_RATE > 16000:
            # Fallback for other sample rates (shouldn't happen with QuickCam)
            num_samples_16k = int(len(audio_data) * 16000 / SAMPLE_RATE)
            audio_data = scipy_signal.resample(audio_data, num_samples_16k)

        # Skip noise reduction for now - too slow for real-time
        # audio_data = self.apply_noise_reduction(audio_data)

        # Skip AGC for now - get basic functionality working first
        # audio_data = self.apply_agc(audio_data)

        # Queue audio for processing in worker thread (non-blocking)
        try:
            # Put audio in queue without blocking (returns immediately)
            self.audio_queue.put_nowait((audio_data.copy(), time.time()))
        except queue.Full:
            logger.warning("Audio queue full - dropping frame")

    def run(self, duration_seconds: Optional[int] = None):
        """
        Main loop - continuous audio perception with transcription

        Args:
            duration_seconds: Run for this many seconds (None = forever)
        """
        logger.info("Conversational audio perceiver starting...")
        start_time = time.time()

        # Start audio processing worker thread
        self.stop_processing.clear()
        self.processing_thread = threading.Thread(target=self.audio_processing_worker, daemon=True)
        self.processing_thread.start()

        try:
            # Open audio stream
            with sd.InputStream(
                device=self.device,
                samplerate=self.sample_rate,
                channels=1,
                blocksize=self.chunk_size,
                callback=self.audio_callback
            ):
                logger.info(f"Audio stream active with speech-to-text (sample rate: {self.sample_rate}Hz)")

                # Run until duration or KeyboardInterrupt
                while True:
                    if duration_seconds and (time.time() - start_time) > duration_seconds:
                        break
                    time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Conversational audio perceiver stopped by user")
        except Exception as e:
            logger.error(f"Conversational audio perceiver failed: {e}", exc_info=True)
        finally:
            # Stop worker thread
            logger.info("Stopping audio processing worker...")
            self.stop_processing.set()
            if self.processing_thread:
                self.processing_thread.join(timeout=2.0)


def main():
    """Entry point for standalone testing"""
    import argparse

    parser = argparse.ArgumentParser(description="Conversational Audio Perceiver with STT")
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

    perceiver = ConversationalAudioPerceiver(device=args.device, aggressiveness=args.aggressiveness)
    perceiver.run(duration_seconds=args.duration if args.duration > 0 else None)


if __name__ == "__main__":
    main()

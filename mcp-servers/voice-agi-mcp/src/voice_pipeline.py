#!/usr/bin/env python3
"""
Voice Pipeline - Hybrid STT/TTS with local and cloud options
Wraps Whisper STT and Edge TTS with unified interface
"""

import asyncio
import logging
import os
import tempfile
import struct
import math
from typing import Optional, Dict, Any, AsyncIterator
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("voice-agi.pipeline")

# Try to import Whisper
try:
    from pywhispercpp.model import Model as WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    WhisperModel = None
    logger.warning("pywhispercpp not available - STT disabled")


class LatencyTracker:
    """Track STT/TTS latency metrics"""

    def __init__(self):
        self.stt_latencies = []
        self.tts_latencies = []
        self.total_latencies = []

    def track_stt(self, latency_ms: float):
        """Track STT latency"""
        self.stt_latencies.append(latency_ms)

    def track_tts(self, latency_ms: float):
        """Track TTS latency"""
        self.tts_latencies.append(latency_ms)

    def track_total(self, latency_ms: float):
        """Track total round-trip latency"""
        self.total_latencies.append(latency_ms)

    def get_summary(self) -> Dict[str, float]:
        """Get latency summary statistics"""
        def avg(lst):
            return sum(lst) / len(lst) if lst else 0

        return {
            'avg_stt_ms': avg(self.stt_latencies),
            'avg_tts_ms': avg(self.tts_latencies),
            'avg_total_ms': avg(self.total_latencies),
            'total_requests': len(self.total_latencies)
        }


class VoicePipeline:
    """Unified voice pipeline with local STT/TTS"""

    def __init__(
        self,
        stt_model: str = "base",
        tts_voice: str = "en-IE-EmilyNeural",
        enable_latency_tracking: bool = True
    ):
        """
        Initialize voice pipeline

        Args:
            stt_model: Whisper model size (tiny, base, small, medium, large)
            tts_voice: Edge TTS voice name
            enable_latency_tracking: Track latency metrics
        """
        self.stt_model_name = stt_model
        self.tts_voice = tts_voice
        self.whisper_model = None
        self.latency_tracker = LatencyTracker() if enable_latency_tracking else None

        logger.info(f"Voice pipeline initialized: STT={stt_model}, TTS={tts_voice}")

    def load_whisper_model(self):
        """Load Whisper model (lazy loading)"""
        if not WHISPER_AVAILABLE:
            logger.error("Whisper not available")
            return None

        if self.whisper_model is None:
            logger.info(f"Loading Whisper model: {self.stt_model_name}")
            try:
                self.whisper_model = WhisperModel(self.stt_model_name)
                logger.info("Whisper model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {e}")
                return None

        return self.whisper_model

    async def record_audio(self, duration: int = 5) -> Optional[str]:
        """
        Record audio from microphone

        Args:
            duration: Recording duration in seconds

        Returns:
            Path to audio file or None
        """
        try:
            audio_file = tempfile.mktemp(suffix='.wav')

            # Use arecord for Linux
            if os.system('which arecord > /dev/null 2>&1') == 0:
                cmd = [
                    'arecord',
                    '-D', 'default',
                    '-f', 'S16_LE',
                    '-c', '1',
                    '-r', '16000',
                    '-t', 'wav',
                    '-d', str(duration),
                    audio_file
                ]

                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                await process.communicate()

                if process.returncode == 0:
                    return audio_file

            logger.error("arecord not available")
            return None

        except Exception as e:
            logger.error(f"Error recording audio: {e}")
            return None

    async def transcribe_audio(self, audio_file: str) -> Optional[str]:
        """
        Transcribe audio file using Whisper

        Args:
            audio_file: Path to audio file

        Returns:
            Transcribed text or None
        """
        if not WHISPER_AVAILABLE:
            return None

        start_time = datetime.now()

        try:
            model = self.load_whisper_model()
            if model is None:
                return None

            # Run transcription in thread pool
            loop = asyncio.get_event_loop()

            def _transcribe():
                segments = model.transcribe(audio_file, language="en")
                text_parts = [segment.text for segment in segments]
                return " ".join(text_parts).strip()

            text = await loop.run_in_executor(None, _transcribe)

            # Track latency
            if self.latency_tracker:
                elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
                self.latency_tracker.track_stt(elapsed_ms)

            return text if text else None

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return None
        finally:
            # Clean up audio file
            try:
                if os.path.exists(audio_file):
                    os.remove(audio_file)
            except:
                pass

    async def synthesize_speech(
        self,
        text: str,
        play_audio: bool = True,
        rate: str = "+0%",
        volume: str = "+0%"
    ) -> Optional[str]:
        """
        Synthesize speech from text using Edge TTS

        Args:
            text: Text to synthesize
            play_audio: Play audio after synthesis
            rate: Speech rate adjustment
            volume: Volume adjustment

        Returns:
            Path to audio file or None
        """
        start_time = datetime.now()

        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                audio_file = f.name

            # Execute Edge TTS
            cmd = [
                'edge-tts',
                '--voice', self.tts_voice,
                '--rate', rate,
                '--volume', volume,
                '--text', text,
                '--write-media', audio_file
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"TTS failed: {stderr.decode()}")
                return None

            # Track latency
            if self.latency_tracker:
                elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
                self.latency_tracker.track_tts(elapsed_ms)

            # Play audio if requested
            if play_audio:
                await self._play_audio(audio_file)

            return audio_file

        except Exception as e:
            logger.error(f"Error synthesizing speech: {e}")
            return None

    async def _play_audio(self, audio_file: str):
        """Play audio file"""
        try:
            # Find available audio player
            players = ['mpg123', 'ffplay', 'mplayer', 'vlc']
            player = None

            for p in players:
                if os.system(f'which {p} > /dev/null 2>&1') == 0:
                    player = p
                    break

            if player:
                process = await asyncio.create_subprocess_exec(
                    player, audio_file,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await process.wait()
            else:
                logger.warning("No audio player available")

        except Exception as e:
            logger.error(f"Error playing audio: {e}")

    async def play_beep(self, beep_type: str = "on"):
        """
        Play audio feedback beep

        Args:
            beep_type: "on" for high beep, "off" for low beep
        """
        try:
            frequency = 1000 if beep_type == "on" else 600
            duration = 0.15
            sample_rate = 16000
            num_samples = int(sample_rate * duration)
            samples = []

            for i in range(num_samples):
                sample = int(32767 * 0.4 * math.sin(2 * math.pi * frequency * i / sample_rate))
                samples.append(struct.pack('<h', sample))

            audio_data = b''.join(samples)

            # Play using paplay
            import subprocess
            proc = subprocess.Popen(
                ['paplay', '--raw', '--rate=16000', '--channels=1', '--format=s16le'],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            proc.communicate(input=audio_data, timeout=0.5)

        except Exception as e:
            logger.debug(f"Error playing beep: {e}")

    async def listen_and_transcribe(self, duration: int = 5) -> Optional[str]:
        """
        Record audio and transcribe (combined operation)

        Args:
            duration: Recording duration

        Returns:
            Transcribed text or None
        """
        start_time = datetime.now()

        # Record
        audio_file = await self.record_audio(duration)
        if not audio_file:
            return None

        # Transcribe
        text = await self.transcribe_audio(audio_file)

        # Track total latency
        if self.latency_tracker:
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            self.latency_tracker.track_total(elapsed_ms)

        return text

    async def speak_and_listen(self, response_text: str, listen_duration: int = 5) -> Optional[str]:
        """
        Speak response and listen for next input (combined operation)

        Args:
            response_text: Text to speak
            listen_duration: How long to listen

        Returns:
            User's next input or None
        """
        # Speak
        await self.synthesize_speech(response_text, play_audio=True)

        # Listen
        user_input = await self.listen_and_transcribe(listen_duration)

        return user_input

    def get_latency_summary(self) -> Dict[str, float]:
        """Get latency tracking summary"""
        if self.latency_tracker:
            return self.latency_tracker.get_summary()
        return {}

    def is_stt_available(self) -> bool:
        """Check if STT is available"""
        return WHISPER_AVAILABLE

    def is_tts_available(self) -> bool:
        """Check if TTS is available"""
        return os.system('which edge-tts > /dev/null 2>&1') == 0

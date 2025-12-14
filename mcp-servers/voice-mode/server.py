#!/usr/bin/env python3
"""
Voice Mode MCP Server - Bidirectional Voice (Speak & Listen)
Provides TTS (Edge TTS) and STT (Whisper) with Caps Lock toggle control
"""

import asyncio
import sys
import os
import tempfile
import logging
import threading
import struct
import math
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

# FastMCP implementation
from fastmcp import FastMCP

# Keyboard listener
try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    keyboard = None

# Wayland keyboard support
try:
    import evdev
    from evdev import InputDevice, categorize, ecodes
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False
    evdev = None

# Whisper for STT (pywhispercpp - Python 3.14 compatible)
try:
    from pywhispercpp.model import Model as WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    WhisperModel = None

# HTTP client for remote GPU STT
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None

# Set up logging - use stderr for MCP compatibility
logging.basicConfig(
    level=logging.DEBUG,  # Enable debug to see all key presses
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("voice-mode")

# Initialize FastMCP app
app = FastMCP("voice-mode")

# Configuration
DEFAULT_VOICE = "en-IE-EmilyNeural"  # Irish female voice
DEFAULT_RATE = "+0%"
DEFAULT_VOLUME = "+0%"
DEFAULT_STT_DURATION = 3  # seconds per recording chunk
DEFAULT_WHISPER_MODEL = "base"  # tiny, base, small, medium, large

# GPU STT Configuration - set GPU_STT_ENDPOINT to your inference server
GPU_STT_ENDPOINT = os.environ.get("GPU_STT_ENDPOINT", "http://localhost:8765")
GPU_STT_ENABLED = os.environ.get("GPU_STT_ENABLED", "true").lower() == "true"
GPU_STT_TIMEOUT = int(os.environ.get("GPU_STT_TIMEOUT", "30"))  # seconds

# STT State Management
class STTState:
    """Thread-safe STT state manager"""
    def __init__(self):
        self._active = False
        self._lock = threading.Lock()
        self._listener = None
        self._listening_task = None
        self._whisper_model = None
        self._transcriptions = []

    @property
    def active(self) -> bool:
        with self._lock:
            return self._active

    def toggle(self) -> bool:
        """Toggle STT on/off, returns new state"""
        with self._lock:
            self._active = not self._active
            logger.info(f"STT {'activated' if self._active else 'deactivated'}")
            return self._active

    def set_active(self, active: bool):
        """Explicitly set STT state"""
        with self._lock:
            self._active = active

    def add_transcription(self, text: str):
        """Add a transcription to history"""
        with self._lock:
            self._transcriptions.append({
                'text': text,
                'timestamp': datetime.now().isoformat()
            })
            # Keep last 50 transcriptions
            if len(self._transcriptions) > 50:
                self._transcriptions.pop(0)

    def get_transcriptions(self, limit: int = 10):
        """Get recent transcriptions"""
        with self._lock:
            return self._transcriptions[-limit:]

stt_state = STTState()


# Audio Feedback Functions
async def play_beep(beep_type: str = "on"):
    """
    Play a nice beep sound using system audio

    Args:
        beep_type: "on" for power-up sound, "off" for power-down sound
    """
    try:
        # Try to use ffplay for tone generation (most flexible)
        if os.system('which ffplay > /dev/null 2>&1') == 0:
            if beep_type == "on":
                # Power-up: Higher frequency beep (800Hz, 150ms)
                cmd = [
                    'ffplay', '-nodisp', '-autoexit', '-t', '0.15',
                    '-f', 'lavfi', '-i', 'sine=frequency=800:duration=0.15'
                ]
            else:
                # Power-down: Lower frequency beep (400Hz, 150ms)
                cmd = [
                    'ffplay', '-nodisp', '-autoexit', '-t', '0.15',
                    '-f', 'lavfi', '-i', 'sine=frequency=400:duration=0.15'
                ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await process.wait()
            return

        # Fallback: Try paplay (PulseAudio)
        elif os.system('which paplay > /dev/null 2>&1') == 0:
            # Generate simple beep with paplay
            if beep_type == "on":
                freq = "800"  # Higher pitch for "on"
            else:
                freq = "400"  # Lower pitch for "off"

            cmd = f'paplay --volume=32768 /dev/zero --format=s16le --channels=1 --rate=48000 | head -c 9600'
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await asyncio.wait_for(process.wait(), timeout=0.3)
            return

        # Fallback: System beep
        elif os.system('which beep > /dev/null 2>&1') == 0:
            if beep_type == "on":
                # Two quick beeps for "on"
                cmd = ['beep', '-f', '800', '-l', '100', '-n', '-f', '1000', '-l', '100']
            else:
                # One lower beep for "off"
                cmd = ['beep', '-f', '600', '-l', '150']

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await process.wait()
            return

        else:
            # No audio tools available - log only
            logger.debug(f"No beep tool available for {beep_type} notification")

    except Exception as e:
        logger.debug(f"Error playing beep: {e}")


# Keyboard Listener Functions
def on_press(key):
    """Handle key press events"""
    # Debug: Log ALL key presses to diagnose issue
    logger.debug(f"🔑 Key pressed: {key}")

    try:
        # Check for caps lock key
        if key == keyboard.Key.caps_lock:
            new_state = stt_state.toggle()
            beep_type = "on" if new_state else "off"
            status = "ON" if new_state else "OFF"
            logger.info(f"Caps Lock pressed - STT is now {status}")

            # Play audio feedback using paplay (proven method from push_to_talk.py)
            try:
                import subprocess

                # Generate beep audio
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
                proc = subprocess.Popen(
                    ['paplay', '--raw', '--rate=16000', '--channels=1', '--format=s16le'],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                proc.communicate(input=audio_data, timeout=0.5)

                logger.info(f"✓ Beep played: {beep_type} ({frequency}Hz)")
            except Exception as e:
                logger.error(f"✗ Error playing beep: {e}")
    except AttributeError:
        pass


def start_evdev_listener():
    """Start evdev keyboard listener for Wayland"""
    import os

    def evdev_loop():
        try:
            # Find keyboard device
            devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
            keyboard_dev = None

            for device in devices:
                # Look for device with Caps Lock capability
                caps = device.capabilities().get(ecodes.EV_KEY, [])
                if ecodes.KEY_CAPSLOCK in caps:
                    keyboard_dev = device
                    logger.info(f"Found keyboard: {device.name} at {device.path}")
                    break

            if not keyboard_dev:
                logger.error("No keyboard device found with Caps Lock key")
                return

            # Monitor Caps Lock presses
            logger.info("Evdev keyboard listener started - press Caps Lock to toggle STT")
            for event in keyboard_dev.read_loop():
                if event.type == ecodes.EV_KEY:
                    key_event = categorize(event)
                    if key_event.keycode == 'KEY_CAPSLOCK' and key_event.keystate == key_event.key_down:
                        # Caps Lock pressed
                        new_state = stt_state.toggle()
                        beep_type = "on" if new_state else "off"
                        status = "ON" if new_state else "OFF"
                        logger.info(f"Caps Lock pressed (evdev) - STT is now {status}")

                        # Play audio feedback
                        try:
                            import subprocess
                            frequency = 1000 if beep_type == "on" else 600
                            duration = 0.15
                            sample_rate = 16000
                            num_samples = int(sample_rate * duration)
                            samples = []

                            for i in range(num_samples):
                                sample = int(32767 * 0.4 * math.sin(2 * math.pi * frequency * i / sample_rate))
                                samples.append(struct.pack('<h', sample))

                            audio_data = b''.join(samples)
                            proc = subprocess.Popen(
                                ['paplay', '--raw', '--rate=16000', '--channels=1', '--format=s16le'],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL
                            )
                            proc.communicate(input=audio_data, timeout=0.5)
                            logger.info(f"✓ Beep played: {beep_type} ({frequency}Hz)")
                        except Exception as e:
                            logger.error(f"✗ Error playing beep: {e}")

        except Exception as e:
            logger.error(f"Error in evdev listener: {e}")

    thread = threading.Thread(target=evdev_loop, daemon=True)
    thread.start()
    return thread

def start_keyboard_listener():
    """Start the keyboard listener in a background thread"""
    # Check if running Wayland
    session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()

    if session_type == 'wayland' and EVDEV_AVAILABLE:
        logger.info("Detected Wayland session - using evdev for keyboard input")
        return start_evdev_listener()
    elif PYNPUT_AVAILABLE:
        logger.info("Using pynput for keyboard input")
        listener = keyboard.Listener(on_press=on_press)
        listener.daemon = True
        listener.start()
        logger.info("Keyboard listener started - press Caps Lock to toggle STT")
        return listener
    else:
        logger.error("No keyboard listener available (pynput or evdev required)")
        return None


# Whisper Model Management
def load_whisper_model(model_size: str = DEFAULT_WHISPER_MODEL):
    """Load pywhispercpp model (cached)"""
    if not WHISPER_AVAILABLE:
        return None

    if stt_state._whisper_model is None:
        logger.info(f"Loading pywhispercpp model: {model_size}")
        # pywhispercpp auto-detects device (CPU/GPU)
        stt_state._whisper_model = WhisperModel(model_size)
    return stt_state._whisper_model


async def record_audio_chunk(duration: int) -> Optional[str]:
    """Record a chunk of audio and return the file path"""
    try:
        audio_file = tempfile.mktemp(suffix='.wav')

        # Try arecord (Linux) - use 16kHz mono for Whisper compatibility
        if os.system('which arecord > /dev/null 2>&1') == 0:
            cmd = [
                'arecord',
                '-D', 'default',
                '-f', 'S16_LE',       # 16-bit signed little endian
                '-c', '1',            # Mono
                '-r', '16000',        # 16kHz sample rate (required by Whisper)
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

        return None
    except Exception as e:
        logger.error(f"Error recording audio: {e}")
        return None


async def transcribe_audio_gpu(audio_file: str, model: str = DEFAULT_WHISPER_MODEL, language: str = "en") -> Optional[str]:
    """
    Transcribe audio using remote GPU STT service (AI inference node)

    10x faster than local CPU with MLX-accelerated Whisper on M4 Max
    """
    if not AIOHTTP_AVAILABLE:
        logger.warning("aiohttp not available for GPU STT, falling back to local")
        return None

    try:
        # Read audio file
        with open(audio_file, 'rb') as f:
            audio_data = f.read()

        # Encode as base64
        import base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')

        async with aiohttp.ClientSession() as session:
            url = f"{GPU_STT_ENDPOINT}/transcribe/json"
            payload = {
                "audio_base64": audio_base64,
                "model": model,
                "language": language
            }

            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=GPU_STT_TIMEOUT)) as response:
                if response.status == 200:
                    result = await response.json()
                    text = result.get("text", "").strip()
                    processing_time = result.get("processing_time_ms", 0)
                    backend = result.get("backend", "unknown")
                    logger.info(f"GPU STT ({backend}): {processing_time:.0f}ms - '{text[:50]}...' " if len(text) > 50 else f"GPU STT ({backend}): {processing_time:.0f}ms - '{text}'")
                    return text if text else None
                else:
                    error = await response.text()
                    logger.error(f"GPU STT error ({response.status}): {error}")
                    return None

    except asyncio.TimeoutError:
        logger.warning(f"GPU STT timeout after {GPU_STT_TIMEOUT}s")
        return None
    except aiohttp.ClientError as e:
        logger.warning(f"GPU STT connection error: {e}")
        return None
    except Exception as e:
        logger.error(f"GPU STT error: {e}")
        return None


async def transcribe_audio_local(audio_file: str, model_size: str = DEFAULT_WHISPER_MODEL) -> Optional[str]:
    """Transcribe audio file using local pywhispercpp (CPU)"""
    if not WHISPER_AVAILABLE:
        return None

    try:
        model = load_whisper_model(model_size)
        if model is None:
            return None

        # Run transcription in thread pool to avoid blocking
        loop = asyncio.get_event_loop()

        def _transcribe():
            # pywhispercpp returns list of Segment objects
            segments = model.transcribe(audio_file, language="en")
            # Collect all segments into a single string
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text)
            return " ".join(text_parts).strip()

        text = await loop.run_in_executor(None, _transcribe)

        return text if text else None
    except Exception as e:
        logger.error(f"Error transcribing audio locally: {e}")
        return None


async def transcribe_audio(audio_file: str, model_size: str = DEFAULT_WHISPER_MODEL, use_gpu: bool = True) -> Optional[str]:
    """
    Transcribe audio file - tries GPU first, falls back to local CPU

    Args:
        audio_file: Path to audio file
        model_size: Whisper model size
        use_gpu: Whether to try GPU STT first (default: True)

    Returns:
        Transcribed text or None
    """
    text = None

    # Try GPU STT first if enabled
    if use_gpu and GPU_STT_ENABLED and AIOHTTP_AVAILABLE:
        logger.debug("Attempting GPU STT transcription...")
        text = await transcribe_audio_gpu(audio_file, model_size)
        if text:
            # Cleanup and return
            try:
                if os.path.exists(audio_file):
                    os.remove(audio_file)
            except:
                pass
            return text
        else:
            logger.debug("GPU STT failed, falling back to local")

    # Fall back to local CPU transcription
    if WHISPER_AVAILABLE:
        logger.debug("Using local CPU transcription...")
        text = await transcribe_audio_local(audio_file, model_size)

    # Cleanup
    try:
        if os.path.exists(audio_file):
            os.remove(audio_file)
    except:
        pass

    return text


async def continuous_listening_loop(duration: int = DEFAULT_STT_DURATION, model: str = DEFAULT_WHISPER_MODEL):
    """Continuous listening loop that runs when STT is active"""
    logger.info("Starting continuous listening loop")

    while True:
        try:
            # Check if STT is still active
            if not stt_state.active:
                await asyncio.sleep(0.5)
                continue

            # Record audio chunk
            logger.debug(f"Recording {duration}s audio chunk...")
            audio_file = await record_audio_chunk(duration)

            if audio_file:
                # Transcribe
                text = await transcribe_audio(audio_file, model)

                if text:
                    logger.info(f"Transcribed: {text}")
                    stt_state.add_transcription(text)

                    # Optionally process the transcription here
                    # For now, just log it

            # Small delay before next chunk
            await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Error in listening loop: {e}")
            await asyncio.sleep(1)


async def _execute_tts(text: str, voice: str, rate: str, volume: str, audio_file: str) -> tuple[int, str, str]:
    """Execute edge-tts command"""
    cmd = [
        'edge-tts',
        '--voice', voice,
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
    return process.returncode, stdout.decode(), stderr.decode()


def _get_audio_player() -> Optional[str]:
    """Find available audio player on system"""
    players = ['mpg123', 'ffplay', 'mplayer', 'vlc']
    for player in players:
        try:
            result = os.system(f'which {player} > /dev/null 2>&1')
            if result == 0:
                return player
        except:
            continue
    return None


@app.tool()
async def speak(
    text: str,
    voice: str = DEFAULT_VOICE,
    rate: str = DEFAULT_RATE,
    volume: str = DEFAULT_VOLUME,
    play_audio: bool = True
) -> Dict[str, Any]:
    """
    Speak text using Edge TTS

    Args:
        text: Text to speak
        voice: Voice name (default: en-IE-EmilyNeural - Irish female)
        rate: Speech rate (e.g., "+10%", "-20%")
        volume: Volume (e.g., "+10%", "-20%")
        play_audio: Whether to play the audio (requires audio device)

    Returns:
        Result with success status and audio file path
    """
    try:
        # Create temporary file for audio
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
            audio_file = f.name

        # Execute TTS
        returncode, stdout, stderr = await _execute_tts(text, voice, rate, volume, audio_file)

        if returncode != 0:
            return {
                "success": False,
                "error": f"TTS failed: {stderr}",
                "audio_file": None
            }

        # Optionally play audio
        if play_audio:
            player = _get_audio_player()
            if player:
                process = await asyncio.create_subprocess_exec(
                    player, audio_file,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                # Wait for audio playback to complete (prevents overlapping audio)
                await process.wait()

        return {
            "success": True,
            "message": f"Spoke {len(text)} characters",
            "audio_file": audio_file,
            "voice": voice,
            "text_length": len(text)
        }

    except Exception as e:
        logger.error(f"Error in speak: {e}")
        return {
            "success": False,
            "error": str(e),
            "audio_file": None
        }


@app.tool()
async def list_voices(language: str = "en-US") -> Dict[str, Any]:
    """
    List available TTS voices

    Args:
        language: Language filter (e.g., "en-US", "en-GB", "en-IE")

    Returns:
        List of available voices
    """
    try:
        cmd = ['edge-tts', '--list-voices']

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            return {
                "success": False,
                "error": "Failed to list voices",
                "voices": []
            }

        # Parse output
        output = stdout.decode()
        voices = []
        for line in output.split('\n'):
            if language.lower() in line.lower():
                voices.append(line.strip())

        return {
            "success": True,
            "voices": voices[:10],  # Limit to 10 for readability
            "total_count": len(voices)
        }

    except Exception as e:
        logger.error(f"Error in list_voices: {e}")
        return {
            "success": False,
            "error": str(e),
            "voices": []
        }


@app.tool()
async def listen(
    duration: int = 5,
    language: str = "en",
    model: str = "base",
    use_gpu: bool = True
) -> Dict[str, Any]:
    """
    Listen to microphone and transcribe speech to text using Whisper (one-shot)

    Args:
        duration: Recording duration in seconds (default: 5)
        language: Language code (e.g., "en", "es", "fr")
        model: Whisper model size (tiny, base, small, medium, large)
        use_gpu: Use GPU STT on AI inference node if available (default: True, 10x faster)

    Returns:
        Transcribed text and confidence
    """
    try:
        # Check if any STT backend is available
        stt_available = WHISPER_AVAILABLE or (GPU_STT_ENABLED and AIOHTTP_AVAILABLE)
        if not stt_available:
            return {
                "success": False,
                "error": "No STT backend available. Install pywhispercpp or enable GPU STT",
                "text": None,
                "audio_file": None
            }

        # Record audio
        audio_file = await record_audio_chunk(duration)

        if not audio_file:
            return {
                "success": False,
                "error": "Failed to record audio",
                "text": None,
                "audio_file": None
            }

        # Transcribe (GPU first if enabled, then local fallback)
        text = await transcribe_audio(audio_file, model, use_gpu=use_gpu)

        if text:
            backend = "gpu" if (use_gpu and GPU_STT_ENABLED) else "local"
            return {
                "success": True,
                "text": text,
                "duration": duration,
                "model": model,
                "backend": backend
            }
        else:
            return {
                "success": False,
                "error": "No speech detected or transcription failed",
                "text": None,
                "audio_file": None
            }

    except Exception as e:
        logger.error(f"Error in listen: {e}")
        return {
            "success": False,
            "error": str(e),
            "text": None,
            "audio_file": None
        }


@app.tool()
async def start_voice_mode(
    model: str = DEFAULT_WHISPER_MODEL,
    chunk_duration: int = DEFAULT_STT_DURATION
) -> Dict[str, Any]:
    """
    Start continuous voice mode with Caps Lock toggle control

    Args:
        model: Whisper model size (tiny, base, small, medium, large)
        chunk_duration: Duration of each recording chunk in seconds

    Returns:
        Status of voice mode initialization
    """
    try:
        if not WHISPER_AVAILABLE:
            return {
                "success": False,
                "error": "pywhispercpp not available. Install with: pip install pywhispercpp",
                "instructions": "Run: pip install pywhispercpp"
            }

        # Start keyboard listener if not already running
        if stt_state._listener is None:
            stt_state._listener = start_keyboard_listener()

        # Start continuous listening loop if not already running
        if stt_state._listening_task is None:
            stt_state._listening_task = asyncio.create_task(
                continuous_listening_loop(chunk_duration, model)
            )

        return {
            "success": True,
            "message": "Voice mode started. Press Caps Lock to toggle STT on/off.",
            "model": model,
            "chunk_duration": chunk_duration,
            "stt_active": stt_state.active
        }

    except Exception as e:
        logger.error(f"Error starting voice mode: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.tool()
async def stop_voice_mode() -> Dict[str, Any]:
    """
    Stop continuous voice mode

    Returns:
        Status of voice mode shutdown
    """
    try:
        # Deactivate STT
        stt_state.set_active(False)

        # Stop keyboard listener
        if stt_state._listener is not None:
            stt_state._listener.stop()
            stt_state._listener = None

        # Cancel listening task
        if stt_state._listening_task is not None:
            stt_state._listening_task.cancel()
            stt_state._listening_task = None

        return {
            "success": True,
            "message": "Voice mode stopped"
        }

    except Exception as e:
        logger.error(f"Error stopping voice mode: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.tool()
async def toggle_stt(enable: Optional[bool] = None) -> Dict[str, Any]:
    """
    Toggle STT on/off or set explicitly (Wayland-compatible with beep feedback)

    Args:
        enable: If provided, explicitly set STT state (True=on, False=off).
                If None, toggle current state.

    Returns:
        New STT state with beep confirmation
    """
    try:
        if enable is None:
            new_state = stt_state.toggle()
        else:
            stt_state.set_active(enable)
            new_state = enable

        # Play beep feedback (Wayland-compatible)
        beep_type = "on" if new_state else "off"
        try:
            import subprocess

            frequency = 1000 if new_state else 600
            duration = 0.15
            sample_rate = 16000
            num_samples = int(sample_rate * duration)
            samples = []

            for i in range(num_samples):
                sample = int(32767 * 0.4 * math.sin(2 * math.pi * frequency * i / sample_rate))
                samples.append(struct.pack('<h', sample))

            audio_data = b''.join(samples)

            proc = subprocess.Popen(
                ['paplay', '--raw', '--rate=16000', '--channels=1', '--format=s16le'],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            proc.communicate(input=audio_data, timeout=0.5)

            logger.info(f"✓ Beep played: {beep_type} ({frequency}Hz)")
        except Exception as e:
            logger.debug(f"Could not play beep: {e}")

        return {
            "success": True,
            "stt_active": new_state,
            "message": f"🎤 Voice mode {'ON' if new_state else 'OFF'} (beep played)"
        }

    except Exception as e:
        logger.error(f"Error toggling STT: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.tool()
async def get_transcriptions(limit: int = 10) -> Dict[str, Any]:
    """
    Get recent transcriptions from voice mode

    Args:
        limit: Number of recent transcriptions to return (default: 10)

    Returns:
        List of recent transcriptions with timestamps
    """
    try:
        transcriptions = stt_state.get_transcriptions(limit)

        return {
            "success": True,
            "transcriptions": transcriptions,
            "count": len(transcriptions)
        }

    except Exception as e:
        logger.error(f"Error getting transcriptions: {e}")
        return {
            "success": False,
            "error": str(e),
            "transcriptions": []
        }


@app.tool()
async def get_voice_mode_status() -> Dict[str, Any]:
    """
    Get current status of voice mode

    Returns:
        Voice mode status including STT state, listener status, etc.
    """
    try:
        return {
            "success": True,
            "stt_active": stt_state.active,
            "keyboard_listener_running": stt_state._listener is not None,
            "listening_task_running": stt_state._listening_task is not None and not stt_state._listening_task.done(),
            "whisper_available": WHISPER_AVAILABLE,
            "whisper_model_loaded": stt_state._whisper_model is not None,
            "transcription_count": len(stt_state._transcriptions)
        }

    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    # Initialize voice mode on server startup
    logger.info("Initializing voice mode server...")

    # Note: Keyboard listener disabled on Wayland
    # Use toggle_stt() MCP tool or 'toggle-voice' shell command instead
    logger.info("Running on Wayland - using MCP tool for voice toggle")

    if WHISPER_AVAILABLE:
        logger.info("pywhispercpp available. Use start_voice_mode() to enable STT.")
        logger.info("Use toggle_stt() MCP tool or 'toggle-voice' command to toggle.")
    else:
        logger.warning("pywhispercpp not available. Voice mode limited to TTS only.")
        logger.warning("Install with: pip install pywhispercpp")

    logger.info("Voice mode server ready!")
    logger.info("Use toggle_stt() MCP tool for beep feedback!")

    # Run the FastMCP server
    app.run()

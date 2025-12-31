"""
Pytest configuration and fixtures for Voice Mode MCP Server tests.

Provides mocking for:
- External APIs (OpenAI, Kokoro, etc.)
- Audio system (arecord, paplay, ffplay)
- Whisper models
- HTTP client (aiohttp)
- Keyboard listeners (pynput, evdev)
"""

import asyncio
import os
import sys
import tempfile
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# --- Fixtures for Environment Configuration ---

@pytest.fixture
def mock_env_gpu_enabled(monkeypatch):
    """Configure environment for GPU STT enabled."""
    monkeypatch.setenv("GPU_STT_ENABLED", "true")
    monkeypatch.setenv("GPU_STT_ENDPOINT", "http://localhost:8765")
    monkeypatch.setenv("GPU_STT_TIMEOUT", "30")


@pytest.fixture
def mock_env_gpu_disabled(monkeypatch):
    """Configure environment for GPU STT disabled."""
    monkeypatch.setenv("GPU_STT_ENABLED", "false")


@pytest.fixture
def mock_env_wayland(monkeypatch):
    """Configure environment to simulate Wayland session."""
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")


@pytest.fixture
def mock_env_x11(monkeypatch):
    """Configure environment to simulate X11 session."""
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")


# --- Fixtures for Audio Files ---

@pytest.fixture
def temp_audio_file():
    """Create a temporary WAV audio file for testing."""
    import struct
    import wave

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        audio_path = f.name

    # Create a simple WAV file with 1 second of silence
    sample_rate = 16000
    duration = 1.0
    num_samples = int(sample_rate * duration)

    with wave.open(audio_path, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)

        # Write silence (zeros)
        for _ in range(num_samples):
            wav_file.writeframes(struct.pack('<h', 0))

    yield audio_path

    # Cleanup
    if os.path.exists(audio_path):
        os.remove(audio_path)


@pytest.fixture
def temp_mp3_file():
    """Create a temporary MP3 file path for TTS output."""
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
        mp3_path = f.name

    yield mp3_path

    # Cleanup
    if os.path.exists(mp3_path):
        os.remove(mp3_path)


# --- Fixtures for Mocking External Dependencies ---

@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp ClientSession for GPU STT tests."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "text": "Hello, this is a test transcription",
        "processing_time_ms": 150,
        "backend": "mlx-whisper"
    })

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.post = AsyncMock(return_value=mock_response)
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    return mock_session


@pytest.fixture
def mock_aiohttp_session_error():
    """Mock aiohttp ClientSession that returns an error."""
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.text = AsyncMock(return_value="Internal Server Error")

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.post = AsyncMock(return_value=mock_response)
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    return mock_session


@pytest.fixture
def mock_aiohttp_timeout():
    """Mock aiohttp ClientSession that times out."""
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.post = AsyncMock(side_effect=asyncio.TimeoutError())

    return mock_session


@pytest.fixture
def mock_whisper_model():
    """Mock pywhispercpp Whisper model."""
    mock_segment = MagicMock()
    mock_segment.text = "Test transcription from Whisper"

    mock_model = MagicMock()
    mock_model.transcribe = MagicMock(return_value=[mock_segment])

    return mock_model


@pytest.fixture
def mock_subprocess_success():
    """Mock subprocess for successful command execution."""
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate = AsyncMock(return_value=(b"", b""))
    mock_process.wait = AsyncMock(return_value=0)

    return mock_process


@pytest.fixture
def mock_subprocess_failure():
    """Mock subprocess for failed command execution."""
    mock_process = AsyncMock()
    mock_process.returncode = 1
    mock_process.communicate = AsyncMock(return_value=(b"", b"Error: command failed"))
    mock_process.wait = AsyncMock(return_value=1)

    return mock_process


# --- Fixtures for Keyboard Mocking ---

@pytest.fixture
def mock_pynput_keyboard():
    """Mock pynput keyboard module."""
    mock_key = MagicMock()
    mock_key.caps_lock = "caps_lock"

    mock_listener = MagicMock()
    mock_listener.daemon = True
    mock_listener.start = MagicMock()
    mock_listener.stop = MagicMock()

    mock_keyboard = MagicMock()
    mock_keyboard.Key = mock_key
    mock_keyboard.Listener = MagicMock(return_value=mock_listener)

    return mock_keyboard


@pytest.fixture
def mock_evdev():
    """Mock evdev module for Wayland keyboard input."""
    mock_device = MagicMock()
    mock_device.name = "Test Keyboard"
    mock_device.path = "/dev/input/event0"
    mock_device.capabilities = MagicMock(return_value={1: [58]})  # KEY_CAPSLOCK = 58

    mock_evdev = MagicMock()
    mock_evdev.list_devices = MagicMock(return_value=["/dev/input/event0"])
    mock_evdev.InputDevice = MagicMock(return_value=mock_device)
    mock_evdev.ecodes = MagicMock()
    mock_evdev.ecodes.EV_KEY = 1
    mock_evdev.ecodes.KEY_CAPSLOCK = 58

    return mock_evdev


# --- Fixtures for STT State ---

@pytest.fixture
def fresh_stt_state():
    """Create a fresh STTState instance for testing."""
    from server import STTState
    return STTState()


@pytest.fixture
def active_stt_state():
    """Create an STTState instance that is already active."""
    from server import STTState
    state = STTState()
    state.set_active(True)
    return state


# --- Fixtures for Audio Player Detection ---

@pytest.fixture
def mock_audio_players_available(monkeypatch):
    """Mock that audio players are available."""
    def mock_system(cmd):
        if 'which mpg123' in cmd or 'which ffplay' in cmd:
            return 0  # Success
        return 1  # Not found

    monkeypatch.setattr(os, 'system', mock_system)


@pytest.fixture
def mock_no_audio_players(monkeypatch):
    """Mock that no audio players are available."""
    def mock_system(cmd):
        return 1  # All commands fail

    monkeypatch.setattr(os, 'system', mock_system)


# --- Async Event Loop Configuration ---

@pytest.fixture(scope="session")
def event_loop_policy():
    """Configure event loop policy for the test session."""
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture
async def async_event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# --- Test Data Fixtures ---

@pytest.fixture
def sample_transcription_data():
    """Sample transcription data for testing."""
    return [
        {"text": "Hello world", "timestamp": "2024-01-01T10:00:00"},
        {"text": "How are you today", "timestamp": "2024-01-01T10:00:05"},
        {"text": "The weather is nice", "timestamp": "2024-01-01T10:00:10"},
    ]


@pytest.fixture
def edge_tts_voices():
    """Sample Edge TTS voice list."""
    return [
        "Name: en-US-JennyNeural, Gender: Female",
        "Name: en-US-GuyNeural, Gender: Male",
        "Name: en-GB-SoniaNeural, Gender: Female",
        "Name: en-IE-EmilyNeural, Gender: Female",
        "Name: en-AU-NatashaNeural, Gender: Female",
    ]


# --- Utility Fixtures ---

@pytest.fixture
def mock_logger():
    """Mock logger for testing log output."""
    with patch('server.logger') as mock:
        yield mock


@pytest.fixture
def mock_tempfile(temp_audio_file):
    """Mock tempfile to return predictable paths."""
    with patch('tempfile.mktemp', return_value=temp_audio_file):
        with patch('tempfile.NamedTemporaryFile') as mock_ntf:
            mock_file = MagicMock()
            mock_file.name = temp_audio_file
            mock_file.__enter__ = MagicMock(return_value=mock_file)
            mock_file.__exit__ = MagicMock(return_value=None)
            mock_ntf.return_value = mock_file
            yield mock_ntf

"""
Tests for transcription functionality - GPU and local STT.

Tests cover:
- GPU STT transcription via remote API
- Local Whisper transcription
- Fallback behavior between GPU and local
- Error handling and timeouts
- Provider discovery patterns
"""

import asyncio
import base64
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestGPUTranscription:
    """Test GPU STT transcription via remote API."""

    @pytest.mark.asyncio
    async def test_gpu_transcription_success(self, temp_audio_file, mock_aiohttp_session):
        """Successful GPU transcription should return text."""
        from server import transcribe_audio_gpu

        # Create dummy audio file
        with open(temp_audio_file, 'wb') as f:
            f.write(b'dummy audio data')

        with patch('aiohttp.ClientSession', return_value=mock_aiohttp_session):
            with patch('server.AIOHTTP_AVAILABLE', True):
                result = await transcribe_audio_gpu(temp_audio_file)

        assert result == "Hello, this is a test transcription"

    @pytest.mark.asyncio
    async def test_gpu_transcription_sends_correct_payload(self, temp_audio_file):
        """GPU transcription should send base64-encoded audio."""
        from server import transcribe_audio_gpu

        # Create dummy audio file
        audio_data = b'test audio bytes'
        with open(temp_audio_file, 'wb') as f:
            f.write(audio_data)

        expected_base64 = base64.b64encode(audio_data).decode('utf-8')

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "text": "Test",
            "processing_time_ms": 100,
            "backend": "mlx"
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.post = AsyncMock(return_value=mock_response)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            with patch('server.AIOHTTP_AVAILABLE', True):
                await transcribe_audio_gpu(temp_audio_file, model="base", language="en")

        # Verify the payload
        call_kwargs = mock_session.post.call_args[1]
        payload = call_kwargs['json']
        assert payload['audio_base64'] == expected_base64
        assert payload['model'] == "base"
        assert payload['language'] == "en"

    @pytest.mark.asyncio
    async def test_gpu_transcription_error_response(self, temp_audio_file, mock_aiohttp_session_error):
        """GPU transcription should return None on error response."""
        from server import transcribe_audio_gpu

        with open(temp_audio_file, 'wb') as f:
            f.write(b'test audio')

        with patch('aiohttp.ClientSession', return_value=mock_aiohttp_session_error):
            with patch('server.AIOHTTP_AVAILABLE', True):
                result = await transcribe_audio_gpu(temp_audio_file)

        assert result is None

    @pytest.mark.asyncio
    async def test_gpu_transcription_timeout(self, temp_audio_file, mock_aiohttp_timeout):
        """GPU transcription should return None on timeout."""
        from server import transcribe_audio_gpu

        with open(temp_audio_file, 'wb') as f:
            f.write(b'test audio')

        with patch('aiohttp.ClientSession', return_value=mock_aiohttp_timeout):
            with patch('server.AIOHTTP_AVAILABLE', True):
                result = await transcribe_audio_gpu(temp_audio_file)

        assert result is None

    @pytest.mark.asyncio
    async def test_gpu_transcription_connection_error(self, temp_audio_file):
        """GPU transcription should handle connection errors."""
        from server import transcribe_audio_gpu

        with open(temp_audio_file, 'wb') as f:
            f.write(b'test audio')

        # Import aiohttp for exception type
        import aiohttp

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.post = AsyncMock(side_effect=aiohttp.ClientError("Connection failed"))

        with patch('aiohttp.ClientSession', return_value=mock_session):
            with patch('server.AIOHTTP_AVAILABLE', True):
                result = await transcribe_audio_gpu(temp_audio_file)

        assert result is None

    @pytest.mark.asyncio
    async def test_gpu_transcription_aiohttp_unavailable(self, temp_audio_file):
        """GPU transcription should return None when aiohttp unavailable."""
        from server import transcribe_audio_gpu

        with patch('server.AIOHTTP_AVAILABLE', False):
            result = await transcribe_audio_gpu(temp_audio_file)

        assert result is None

    @pytest.mark.asyncio
    async def test_gpu_transcription_empty_text(self, temp_audio_file):
        """GPU transcription should return None for empty text."""
        from server import transcribe_audio_gpu

        with open(temp_audio_file, 'wb') as f:
            f.write(b'test audio')

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "text": "",
            "processing_time_ms": 50
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.post = AsyncMock(return_value=mock_response)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            with patch('server.AIOHTTP_AVAILABLE', True):
                result = await transcribe_audio_gpu(temp_audio_file)

        assert result is None


class TestLocalTranscription:
    """Test local Whisper transcription."""

    @pytest.mark.asyncio
    async def test_local_transcription_success(self, temp_audio_file, mock_whisper_model):
        """Successful local transcription should return text."""
        from server import transcribe_audio_local

        with patch('server.WHISPER_AVAILABLE', True):
            with patch('server.load_whisper_model', return_value=mock_whisper_model):
                result = await transcribe_audio_local(temp_audio_file)

        assert result == "Test transcription from Whisper"

    @pytest.mark.asyncio
    async def test_local_transcription_model_loading(self, temp_audio_file, mock_whisper_model):
        """Local transcription should load model with correct size."""
        from server import transcribe_audio_local

        with patch('server.WHISPER_AVAILABLE', True):
            with patch('server.load_whisper_model', return_value=mock_whisper_model) as mock_load:
                await transcribe_audio_local(temp_audio_file, model_size="medium")

        mock_load.assert_called_once_with("medium")

    @pytest.mark.asyncio
    async def test_local_transcription_whisper_unavailable(self, temp_audio_file):
        """Local transcription should return None when Whisper unavailable."""
        from server import transcribe_audio_local

        with patch('server.WHISPER_AVAILABLE', False):
            result = await transcribe_audio_local(temp_audio_file)

        assert result is None

    @pytest.mark.asyncio
    async def test_local_transcription_model_load_failure(self, temp_audio_file):
        """Local transcription should handle model load failure."""
        from server import transcribe_audio_local

        with patch('server.WHISPER_AVAILABLE', True):
            with patch('server.load_whisper_model', return_value=None):
                result = await transcribe_audio_local(temp_audio_file)

        assert result is None

    @pytest.mark.asyncio
    async def test_local_transcription_exception_handling(self, temp_audio_file, mock_whisper_model):
        """Local transcription should handle exceptions."""
        from server import transcribe_audio_local

        mock_whisper_model.transcribe = MagicMock(side_effect=Exception("Transcription error"))

        with patch('server.WHISPER_AVAILABLE', True):
            with patch('server.load_whisper_model', return_value=mock_whisper_model):
                result = await transcribe_audio_local(temp_audio_file)

        assert result is None

    @pytest.mark.asyncio
    async def test_local_transcription_multiple_segments(self, temp_audio_file):
        """Local transcription should concatenate multiple segments."""
        from server import transcribe_audio_local

        segment1 = MagicMock()
        segment1.text = "Hello"
        segment2 = MagicMock()
        segment2.text = "world"
        segment3 = MagicMock()
        segment3.text = "test"

        mock_model = MagicMock()
        mock_model.transcribe = MagicMock(return_value=[segment1, segment2, segment3])

        with patch('server.WHISPER_AVAILABLE', True):
            with patch('server.load_whisper_model', return_value=mock_model):
                result = await transcribe_audio_local(temp_audio_file)

        assert result == "Hello world test"


class TestTranscribeAudio:
    """Test main transcribe_audio function with fallback logic."""

    @pytest.mark.asyncio
    async def test_transcribe_audio_gpu_first(self, temp_audio_file):
        """transcribe_audio should try GPU first when enabled."""
        from server import transcribe_audio

        with open(temp_audio_file, 'wb') as f:
            f.write(b'test audio')

        mock_gpu = AsyncMock(return_value="GPU result")
        mock_local = AsyncMock(return_value="Local result")

        with patch('server.GPU_STT_ENABLED', True):
            with patch('server.AIOHTTP_AVAILABLE', True):
                with patch('server.transcribe_audio_gpu', mock_gpu):
                    with patch('server.transcribe_audio_local', mock_local):
                        result = await transcribe_audio(temp_audio_file, use_gpu=True)

        assert result == "GPU result"
        mock_gpu.assert_called_once()
        mock_local.assert_not_called()

    @pytest.mark.asyncio
    async def test_transcribe_audio_fallback_to_local(self, temp_audio_file):
        """transcribe_audio should fallback to local when GPU fails."""
        from server import transcribe_audio

        with open(temp_audio_file, 'wb') as f:
            f.write(b'test audio')

        mock_gpu = AsyncMock(return_value=None)
        mock_local = AsyncMock(return_value="Local result")

        with patch('server.GPU_STT_ENABLED', True):
            with patch('server.AIOHTTP_AVAILABLE', True):
                with patch('server.WHISPER_AVAILABLE', True):
                    with patch('server.transcribe_audio_gpu', mock_gpu):
                        with patch('server.transcribe_audio_local', mock_local):
                            result = await transcribe_audio(temp_audio_file, use_gpu=True)

        assert result == "Local result"
        mock_gpu.assert_called_once()
        mock_local.assert_called_once()

    @pytest.mark.asyncio
    async def test_transcribe_audio_skip_gpu(self, temp_audio_file):
        """transcribe_audio should skip GPU when use_gpu=False."""
        from server import transcribe_audio

        with open(temp_audio_file, 'wb') as f:
            f.write(b'test audio')

        mock_gpu = AsyncMock(return_value="GPU result")
        mock_local = AsyncMock(return_value="Local result")

        with patch('server.WHISPER_AVAILABLE', True):
            with patch('server.transcribe_audio_gpu', mock_gpu):
                with patch('server.transcribe_audio_local', mock_local):
                    result = await transcribe_audio(temp_audio_file, use_gpu=False)

        assert result == "Local result"
        mock_gpu.assert_not_called()

    @pytest.mark.asyncio
    async def test_transcribe_audio_skip_gpu_when_disabled(self, temp_audio_file):
        """transcribe_audio should skip GPU when GPU_STT_ENABLED=False."""
        from server import transcribe_audio

        with open(temp_audio_file, 'wb') as f:
            f.write(b'test audio')

        mock_gpu = AsyncMock(return_value="GPU result")
        mock_local = AsyncMock(return_value="Local result")

        with patch('server.GPU_STT_ENABLED', False):
            with patch('server.WHISPER_AVAILABLE', True):
                with patch('server.transcribe_audio_gpu', mock_gpu):
                    with patch('server.transcribe_audio_local', mock_local):
                        result = await transcribe_audio(temp_audio_file, use_gpu=True)

        assert result == "Local result"
        mock_gpu.assert_not_called()

    @pytest.mark.asyncio
    async def test_transcribe_audio_cleans_up_file(self, temp_audio_file):
        """transcribe_audio should clean up the audio file after processing."""
        from server import transcribe_audio

        # Create the file
        with open(temp_audio_file, 'wb') as f:
            f.write(b'test audio')

        assert os.path.exists(temp_audio_file)

        mock_local = AsyncMock(return_value="Result")

        with patch('server.GPU_STT_ENABLED', False):
            with patch('server.WHISPER_AVAILABLE', True):
                with patch('server.transcribe_audio_local', mock_local):
                    await transcribe_audio(temp_audio_file, use_gpu=False)

        # File should be cleaned up
        assert not os.path.exists(temp_audio_file)


class TestLoadWhisperModel:
    """Test Whisper model loading and caching."""

    def test_load_whisper_model_caching(self):
        """Whisper model should be cached after first load."""
        from server import load_whisper_model, stt_state

        mock_model = MagicMock()

        # Reset state
        stt_state._whisper_model = None

        with patch('server.WHISPER_AVAILABLE', True):
            with patch('server.WhisperModel', return_value=mock_model) as mock_class:
                # First call should create model
                result1 = load_whisper_model("base")
                assert result1 == mock_model
                mock_class.assert_called_once_with("base")

                # Second call should return cached model
                result2 = load_whisper_model("base")
                assert result2 == mock_model
                assert mock_class.call_count == 1  # No additional calls

        # Cleanup
        stt_state._whisper_model = None

    def test_load_whisper_model_unavailable(self):
        """load_whisper_model should return None when Whisper unavailable."""
        from server import load_whisper_model

        with patch('server.WHISPER_AVAILABLE', False):
            result = load_whisper_model("base")

        assert result is None


class TestProviderDiscovery:
    """Test TTS/STT provider discovery patterns."""

    def test_gpu_stt_endpoint_from_env(self, monkeypatch):
        """GPU_STT_ENDPOINT should be configurable via environment."""
        monkeypatch.setenv("GPU_STT_ENDPOINT", "http://custom-server:9000")

        # Re-import to get new env value
        import importlib
        import server
        importlib.reload(server)

        assert server.GPU_STT_ENDPOINT == "http://custom-server:9000"

    def test_gpu_stt_enabled_from_env(self, monkeypatch):
        """GPU_STT_ENABLED should be configurable via environment."""
        monkeypatch.setenv("GPU_STT_ENABLED", "false")

        import importlib
        import server
        importlib.reload(server)

        assert server.GPU_STT_ENABLED is False

    def test_gpu_stt_timeout_from_env(self, monkeypatch):
        """GPU_STT_TIMEOUT should be configurable via environment."""
        monkeypatch.setenv("GPU_STT_TIMEOUT", "60")

        import importlib
        import server
        importlib.reload(server)

        assert server.GPU_STT_TIMEOUT == 60

    def test_default_whisper_model(self):
        """Default Whisper model should be 'base'."""
        from server import DEFAULT_WHISPER_MODEL

        assert DEFAULT_WHISPER_MODEL == "base"


class TestConversationFlow:
    """Test conversation flow handling."""

    @pytest.mark.asyncio
    async def test_transcription_added_to_state(self, temp_audio_file):
        """Transcriptions should be added to STTState."""
        from server import continuous_listening_loop, stt_state

        with open(temp_audio_file, 'wb') as f:
            f.write(b'test audio')

        # Setup mocks
        mock_record = AsyncMock(return_value=temp_audio_file)
        mock_transcribe = AsyncMock(return_value="Test message")

        # Enable STT briefly
        stt_state.set_active(True)

        with patch('server.record_audio_chunk', mock_record):
            with patch('server.transcribe_audio', mock_transcribe):
                # Run one iteration then stop
                async def run_once():
                    stt_state.set_active(True)
                    # Give loop time to process
                    await asyncio.sleep(0.1)
                    stt_state.set_active(False)

                # Start the loop and let it run briefly
                task = asyncio.create_task(continuous_listening_loop())
                await run_once()
                task.cancel()

                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Cleanup
        stt_state.set_active(False)

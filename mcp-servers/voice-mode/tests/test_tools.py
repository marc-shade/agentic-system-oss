"""
Tests for MCP tool endpoints.

Tests cover:
- listen() tool functionality
- start_voice_mode() / stop_voice_mode() tools
- toggle_stt() tool
- get_transcriptions() tool
- get_voice_mode_status() tool
- Error handling for all tools
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestListenTool:
    """Test listen() MCP tool - one-shot STT."""

    @pytest.mark.asyncio
    async def test_listen_success(self, temp_audio_file):
        """Successful listen should return transcribed text."""
        from server import listen

        mock_record = AsyncMock(return_value=temp_audio_file)
        mock_transcribe = AsyncMock(return_value="Hello world")

        with patch('server.WHISPER_AVAILABLE', True):
            with patch('server.record_audio_chunk', mock_record):
                with patch('server.transcribe_audio', mock_transcribe):
                    result = await listen(duration=5)

        assert result['success'] is True
        assert result['text'] == "Hello world"
        assert result['duration'] == 5

    @pytest.mark.asyncio
    async def test_listen_with_custom_duration(self, temp_audio_file):
        """Listen should use specified duration."""
        from server import listen

        mock_record = AsyncMock(return_value=temp_audio_file)
        mock_transcribe = AsyncMock(return_value="Test")

        with patch('server.WHISPER_AVAILABLE', True):
            with patch('server.record_audio_chunk', mock_record) as mock_rec:
                with patch('server.transcribe_audio', mock_transcribe):
                    await listen(duration=10)

        mock_rec.assert_called_once_with(10)

    @pytest.mark.asyncio
    async def test_listen_with_custom_model(self, temp_audio_file):
        """Listen should use specified Whisper model."""
        from server import listen

        mock_record = AsyncMock(return_value=temp_audio_file)
        mock_transcribe = AsyncMock(return_value="Test")

        with patch('server.WHISPER_AVAILABLE', True):
            with patch('server.record_audio_chunk', mock_record):
                with patch('server.transcribe_audio', mock_transcribe) as mock_trans:
                    await listen(model="medium")

        # Check model was passed
        call_args = mock_trans.call_args
        assert call_args[0][1] == "medium"

    @pytest.mark.asyncio
    async def test_listen_gpu_enabled(self, temp_audio_file):
        """Listen should use GPU when use_gpu=True."""
        from server import listen

        mock_record = AsyncMock(return_value=temp_audio_file)
        mock_transcribe = AsyncMock(return_value="Test")

        with patch('server.GPU_STT_ENABLED', True):
            with patch('server.AIOHTTP_AVAILABLE', True):
                with patch('server.record_audio_chunk', mock_record):
                    with patch('server.transcribe_audio', mock_transcribe) as mock_trans:
                        result = await listen(use_gpu=True)

        # Verify use_gpu was passed
        call_kwargs = mock_trans.call_args[1]
        assert call_kwargs['use_gpu'] is True

    @pytest.mark.asyncio
    async def test_listen_gpu_disabled(self, temp_audio_file):
        """Listen should skip GPU when use_gpu=False."""
        from server import listen

        mock_record = AsyncMock(return_value=temp_audio_file)
        mock_transcribe = AsyncMock(return_value="Test")

        with patch('server.WHISPER_AVAILABLE', True):
            with patch('server.record_audio_chunk', mock_record):
                with patch('server.transcribe_audio', mock_transcribe) as mock_trans:
                    await listen(use_gpu=False)

        call_kwargs = mock_trans.call_args[1]
        assert call_kwargs['use_gpu'] is False

    @pytest.mark.asyncio
    async def test_listen_no_stt_available(self):
        """Listen should return error when no STT backend available."""
        from server import listen

        with patch('server.WHISPER_AVAILABLE', False):
            with patch('server.GPU_STT_ENABLED', False):
                result = await listen()

        assert result['success'] is False
        assert 'error' in result
        assert 'No STT backend available' in result['error']

    @pytest.mark.asyncio
    async def test_listen_recording_failure(self):
        """Listen should return error when recording fails."""
        from server import listen

        mock_record = AsyncMock(return_value=None)

        with patch('server.WHISPER_AVAILABLE', True):
            with patch('server.record_audio_chunk', mock_record):
                result = await listen()

        assert result['success'] is False
        assert 'Failed to record audio' in result['error']

    @pytest.mark.asyncio
    async def test_listen_no_speech_detected(self, temp_audio_file):
        """Listen should return error when no speech detected."""
        from server import listen

        mock_record = AsyncMock(return_value=temp_audio_file)
        mock_transcribe = AsyncMock(return_value=None)

        with patch('server.WHISPER_AVAILABLE', True):
            with patch('server.record_audio_chunk', mock_record):
                with patch('server.transcribe_audio', mock_transcribe):
                    result = await listen()

        assert result['success'] is False
        assert 'No speech detected' in result['error']

    @pytest.mark.asyncio
    async def test_listen_exception_handling(self):
        """Listen should handle exceptions gracefully."""
        from server import listen

        with patch('server.WHISPER_AVAILABLE', True):
            with patch('server.record_audio_chunk', side_effect=Exception("Test error")):
                result = await listen()

        assert result['success'] is False
        assert 'error' in result


class TestStartStopVoiceMode:
    """Test start_voice_mode() and stop_voice_mode() tools."""

    @pytest.mark.asyncio
    async def test_start_voice_mode_success(self):
        """start_voice_mode should initialize voice mode."""
        from server import start_voice_mode, stt_state

        mock_listener = MagicMock()

        with patch('server.WHISPER_AVAILABLE', True):
            with patch('server.start_keyboard_listener', return_value=mock_listener):
                result = await start_voice_mode()

        assert result['success'] is True
        assert 'Voice mode started' in result['message']

        # Cleanup
        stt_state._listener = None
        if stt_state._listening_task:
            stt_state._listening_task.cancel()
            stt_state._listening_task = None

    @pytest.mark.asyncio
    async def test_start_voice_mode_whisper_unavailable(self):
        """start_voice_mode should return error when Whisper unavailable."""
        from server import start_voice_mode

        with patch('server.WHISPER_AVAILABLE', False):
            result = await start_voice_mode()

        assert result['success'] is False
        assert 'pywhispercpp not available' in result['error']

    @pytest.mark.asyncio
    async def test_start_voice_mode_custom_settings(self):
        """start_voice_mode should accept custom model and duration."""
        from server import start_voice_mode, stt_state

        mock_listener = MagicMock()

        with patch('server.WHISPER_AVAILABLE', True):
            with patch('server.start_keyboard_listener', return_value=mock_listener):
                result = await start_voice_mode(model="medium", chunk_duration=5)

        assert result['success'] is True
        assert result['model'] == "medium"
        assert result['chunk_duration'] == 5

        # Cleanup
        stt_state._listener = None
        if stt_state._listening_task:
            stt_state._listening_task.cancel()
            stt_state._listening_task = None

    @pytest.mark.asyncio
    async def test_stop_voice_mode_success(self):
        """stop_voice_mode should stop voice mode."""
        from server import stop_voice_mode, stt_state

        # Setup: simulate running voice mode
        stt_state.set_active(True)
        mock_listener = MagicMock()
        mock_listener.stop = MagicMock()
        stt_state._listener = mock_listener

        mock_task = MagicMock()
        mock_task.cancel = MagicMock()
        stt_state._listening_task = mock_task

        result = await stop_voice_mode()

        assert result['success'] is True
        assert 'Voice mode stopped' in result['message']
        assert stt_state.active is False
        assert stt_state._listener is None
        assert stt_state._listening_task is None

    @pytest.mark.asyncio
    async def test_stop_voice_mode_already_stopped(self):
        """stop_voice_mode should work even when already stopped."""
        from server import stop_voice_mode, stt_state

        # Ensure everything is None
        stt_state.set_active(False)
        stt_state._listener = None
        stt_state._listening_task = None

        result = await stop_voice_mode()

        assert result['success'] is True


class TestToggleSTT:
    """Test toggle_stt() tool."""

    @pytest.mark.asyncio
    async def test_toggle_stt_on(self, fresh_stt_state):
        """toggle_stt should activate STT when inactive."""
        from server import toggle_stt, stt_state

        stt_state.set_active(False)

        with patch('subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate = MagicMock(return_value=(b"", b""))
            mock_popen.return_value = mock_proc

            result = await toggle_stt()

        assert result['success'] is True
        assert result['stt_active'] is True

        # Cleanup
        stt_state.set_active(False)

    @pytest.mark.asyncio
    async def test_toggle_stt_off(self):
        """toggle_stt should deactivate STT when active."""
        from server import toggle_stt, stt_state

        stt_state.set_active(True)

        with patch('subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate = MagicMock(return_value=(b"", b""))
            mock_popen.return_value = mock_proc

            result = await toggle_stt()

        assert result['success'] is True
        assert result['stt_active'] is False

    @pytest.mark.asyncio
    async def test_toggle_stt_explicit_enable(self):
        """toggle_stt with enable=True should activate STT."""
        from server import toggle_stt, stt_state

        stt_state.set_active(False)

        with patch('subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate = MagicMock(return_value=(b"", b""))
            mock_popen.return_value = mock_proc

            result = await toggle_stt(enable=True)

        assert result['stt_active'] is True

        # Cleanup
        stt_state.set_active(False)

    @pytest.mark.asyncio
    async def test_toggle_stt_explicit_disable(self):
        """toggle_stt with enable=False should deactivate STT."""
        from server import toggle_stt, stt_state

        stt_state.set_active(True)

        with patch('subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate = MagicMock(return_value=(b"", b""))
            mock_popen.return_value = mock_proc

            result = await toggle_stt(enable=False)

        assert result['stt_active'] is False

    @pytest.mark.asyncio
    async def test_toggle_stt_plays_beep(self):
        """toggle_stt should play beep feedback."""
        from server import toggle_stt, stt_state

        stt_state.set_active(False)

        with patch('subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate = MagicMock(return_value=(b"", b""))
            mock_popen.return_value = mock_proc

            result = await toggle_stt()

        # Popen should have been called for beep
        mock_popen.assert_called()

        # Cleanup
        stt_state.set_active(False)


class TestGetTranscriptions:
    """Test get_transcriptions() tool."""

    @pytest.mark.asyncio
    async def test_get_transcriptions_empty(self, fresh_stt_state):
        """get_transcriptions should return empty list when no transcriptions."""
        from server import get_transcriptions, stt_state

        # Clear any existing transcriptions
        stt_state._transcriptions = []

        result = await get_transcriptions()

        assert result['success'] is True
        assert result['transcriptions'] == []
        assert result['count'] == 0

    @pytest.mark.asyncio
    async def test_get_transcriptions_with_data(self):
        """get_transcriptions should return stored transcriptions."""
        from server import get_transcriptions, stt_state

        # Add some transcriptions
        stt_state._transcriptions = []
        stt_state.add_transcription("Hello")
        stt_state.add_transcription("World")
        stt_state.add_transcription("Test")

        result = await get_transcriptions()

        assert result['success'] is True
        assert result['count'] == 3
        assert len(result['transcriptions']) == 3

        # Cleanup
        stt_state._transcriptions = []

    @pytest.mark.asyncio
    async def test_get_transcriptions_with_limit(self):
        """get_transcriptions should respect limit parameter."""
        from server import get_transcriptions, stt_state

        # Add multiple transcriptions
        stt_state._transcriptions = []
        for i in range(20):
            stt_state.add_transcription(f"Message {i}")

        result = await get_transcriptions(limit=5)

        assert result['success'] is True
        assert result['count'] == 5
        assert len(result['transcriptions']) == 5

        # Cleanup
        stt_state._transcriptions = []

    @pytest.mark.asyncio
    async def test_get_transcriptions_exception_handling(self):
        """get_transcriptions should handle exceptions."""
        from server import get_transcriptions, stt_state

        with patch.object(stt_state, 'get_transcriptions', side_effect=Exception("Test error")):
            result = await get_transcriptions()

        assert result['success'] is False
        assert 'error' in result


class TestGetVoiceModeStatus:
    """Test get_voice_mode_status() tool."""

    @pytest.mark.asyncio
    async def test_get_status_inactive(self):
        """get_voice_mode_status should return correct status when inactive."""
        from server import get_voice_mode_status, stt_state

        # Ensure inactive state
        stt_state.set_active(False)
        stt_state._listener = None
        stt_state._listening_task = None
        stt_state._whisper_model = None
        stt_state._transcriptions = []

        result = await get_voice_mode_status()

        assert result['success'] is True
        assert result['stt_active'] is False
        assert result['keyboard_listener_running'] is False
        assert result['listening_task_running'] is False

    @pytest.mark.asyncio
    async def test_get_status_active(self):
        """get_voice_mode_status should return correct status when active."""
        from server import get_voice_mode_status, stt_state

        # Setup active state
        stt_state.set_active(True)
        mock_listener = MagicMock()
        stt_state._listener = mock_listener

        mock_task = MagicMock()
        mock_task.done = MagicMock(return_value=False)
        stt_state._listening_task = mock_task

        result = await get_voice_mode_status()

        assert result['success'] is True
        assert result['stt_active'] is True
        assert result['keyboard_listener_running'] is True
        assert result['listening_task_running'] is True

        # Cleanup
        stt_state.set_active(False)
        stt_state._listener = None
        stt_state._listening_task = None

    @pytest.mark.asyncio
    async def test_get_status_includes_whisper_info(self):
        """get_voice_mode_status should include Whisper availability."""
        from server import get_voice_mode_status

        with patch('server.WHISPER_AVAILABLE', True):
            result = await get_voice_mode_status()

        assert 'whisper_available' in result
        assert result['whisper_available'] is True

    @pytest.mark.asyncio
    async def test_get_status_includes_transcription_count(self):
        """get_voice_mode_status should include transcription count."""
        from server import get_voice_mode_status, stt_state

        stt_state._transcriptions = []
        stt_state.add_transcription("Test 1")
        stt_state.add_transcription("Test 2")

        result = await get_voice_mode_status()

        assert 'transcription_count' in result
        assert result['transcription_count'] == 2

        # Cleanup
        stt_state._transcriptions = []

    @pytest.mark.asyncio
    async def test_get_status_exception_handling(self):
        """get_voice_mode_status should handle exceptions."""
        from server import get_voice_mode_status, stt_state

        with patch.object(stt_state, '__getattribute__', side_effect=Exception("Test error")):
            result = await get_voice_mode_status()

        assert result['success'] is False
        assert 'error' in result


class TestToolIntegration:
    """Integration tests for tool interactions."""

    @pytest.mark.asyncio
    async def test_start_listen_stop_flow(self):
        """Test complete voice mode lifecycle."""
        from server import start_voice_mode, listen, stop_voice_mode, stt_state

        mock_listener = MagicMock()
        mock_listener.stop = MagicMock()

        # Start voice mode
        with patch('server.WHISPER_AVAILABLE', True):
            with patch('server.start_keyboard_listener', return_value=mock_listener):
                start_result = await start_voice_mode()

        assert start_result['success'] is True

        # Do a listen (mock recording and transcription)
        mock_record = AsyncMock(return_value="/tmp/test.wav")
        mock_transcribe = AsyncMock(return_value="Test message")

        with patch('server.record_audio_chunk', mock_record):
            with patch('server.transcribe_audio', mock_transcribe):
                listen_result = await listen()

        assert listen_result['success'] is True

        # Stop voice mode
        stop_result = await stop_voice_mode()

        assert stop_result['success'] is True
        assert stt_state.active is False

    @pytest.mark.asyncio
    async def test_transcription_accumulation(self):
        """Test that transcriptions accumulate correctly."""
        from server import listen, get_transcriptions, stt_state

        stt_state._transcriptions = []

        mock_record = AsyncMock(return_value="/tmp/test.wav")

        # Simulate multiple listens
        transcripts = ["Hello", "World", "Test"]
        for text in transcripts:
            mock_transcribe = AsyncMock(return_value=text)

            with patch('server.WHISPER_AVAILABLE', True):
                with patch('server.record_audio_chunk', mock_record):
                    with patch('server.transcribe_audio', mock_transcribe):
                        # Note: listen() doesn't add to transcriptions by default
                        # Only continuous_listening_loop does
                        stt_state.add_transcription(text)

        result = await get_transcriptions()

        assert result['count'] == 3
        texts = [t['text'] for t in result['transcriptions']]
        assert texts == transcripts

        # Cleanup
        stt_state._transcriptions = []

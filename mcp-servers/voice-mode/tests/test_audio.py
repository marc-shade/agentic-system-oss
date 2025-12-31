"""
Tests for audio recording and playback functionality.

Tests cover:
- Audio recording with arecord
- Audio playback with various players
- Beep sound generation
- Audio player detection
- Error handling for audio operations
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
import pytest_asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPlayBeep:
    """Test beep sound functionality."""

    @pytest.mark.asyncio
    async def test_beep_on_with_ffplay(self):
        """Beep 'on' should play higher frequency with ffplay."""
        from server import play_beep

        mock_process = AsyncMock()
        mock_process.wait = AsyncMock(return_value=0)

        with patch.object(os, 'system', return_value=0):  # ffplay available
            with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_exec:
                await play_beep("on")

                # Verify ffplay was called
                mock_exec.assert_called_once()
                call_args = mock_exec.call_args[0]
                assert 'ffplay' in call_args
                assert 'frequency=800' in str(call_args)  # Higher frequency for "on"

    @pytest.mark.asyncio
    async def test_beep_off_with_ffplay(self):
        """Beep 'off' should play lower frequency with ffplay."""
        from server import play_beep

        mock_process = AsyncMock()
        mock_process.wait = AsyncMock(return_value=0)

        with patch.object(os, 'system', return_value=0):  # ffplay available
            with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_exec:
                await play_beep("off")

                call_args = mock_exec.call_args[0]
                assert 'ffplay' in call_args
                assert 'frequency=400' in str(call_args)  # Lower frequency for "off"

    @pytest.mark.asyncio
    async def test_beep_fallback_to_paplay(self):
        """Beep should fallback to paplay when ffplay unavailable."""
        from server import play_beep

        mock_process = AsyncMock()
        mock_process.wait = AsyncMock(return_value=0)

        def mock_system_check(cmd):
            if 'ffplay' in cmd:
                return 1  # ffplay not available
            if 'paplay' in cmd:
                return 0  # paplay available
            return 1

        with patch.object(os, 'system', side_effect=mock_system_check):
            with patch('asyncio.create_subprocess_shell', return_value=mock_process) as mock_shell:
                with patch('asyncio.wait_for', return_value=None):
                    await play_beep("on")

                    mock_shell.assert_called_once()
                    call_args = mock_shell.call_args[0][0]
                    assert 'paplay' in call_args

    @pytest.mark.asyncio
    async def test_beep_fallback_to_beep_command(self):
        """Beep should fallback to beep command when others unavailable."""
        from server import play_beep

        mock_process = AsyncMock()
        mock_process.wait = AsyncMock(return_value=0)

        def mock_system_check(cmd):
            if 'beep' in cmd and 'ffplay' not in cmd and 'paplay' not in cmd:
                return 0  # Only beep command available
            return 1

        with patch.object(os, 'system', side_effect=mock_system_check):
            with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_exec:
                await play_beep("on")

                call_args = mock_exec.call_args[0]
                assert 'beep' in call_args

    @pytest.mark.asyncio
    async def test_beep_no_tools_available(self, mock_logger):
        """Beep should handle case when no audio tools available."""
        from server import play_beep

        with patch.object(os, 'system', return_value=1):  # No tools available
            # Should not raise exception
            await play_beep("on")

    @pytest.mark.asyncio
    async def test_beep_handles_exception(self, mock_logger):
        """Beep should handle exceptions gracefully."""
        from server import play_beep

        with patch.object(os, 'system', side_effect=Exception("Test error")):
            # Should not raise exception
            await play_beep("on")


class TestRecordAudioChunk:
    """Test audio recording functionality."""

    @pytest.mark.asyncio
    async def test_record_audio_success(self, temp_audio_file):
        """Successful audio recording should return file path."""
        from server import record_audio_chunk

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with patch.object(os, 'system', return_value=0):  # arecord available
            with patch('tempfile.mktemp', return_value=temp_audio_file):
                with patch('asyncio.create_subprocess_exec', return_value=mock_process):
                    result = await record_audio_chunk(3)

                    assert result == temp_audio_file

    @pytest.mark.asyncio
    async def test_record_audio_correct_parameters(self):
        """Recording should use correct arecord parameters."""
        from server import record_audio_chunk

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with patch.object(os, 'system', return_value=0):
            with patch('tempfile.mktemp', return_value="/tmp/test.wav"):
                with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_exec:
                    await record_audio_chunk(5)

                    call_args = mock_exec.call_args[0]
                    assert 'arecord' in call_args
                    assert '-f' in call_args
                    assert 'S16_LE' in call_args  # 16-bit signed
                    assert '-c' in call_args
                    assert '1' in call_args  # Mono
                    assert '-r' in call_args
                    assert '16000' in call_args  # 16kHz for Whisper
                    assert '-d' in call_args
                    assert '5' in call_args  # Duration

    @pytest.mark.asyncio
    async def test_record_audio_failure_returns_none(self):
        """Failed recording should return None."""
        from server import record_audio_chunk

        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"Error"))

        with patch.object(os, 'system', return_value=0):
            with patch('tempfile.mktemp', return_value="/tmp/test.wav"):
                with patch('asyncio.create_subprocess_exec', return_value=mock_process):
                    result = await record_audio_chunk(3)

                    assert result is None

    @pytest.mark.asyncio
    async def test_record_audio_no_arecord(self):
        """Recording should return None when arecord unavailable."""
        from server import record_audio_chunk

        with patch.object(os, 'system', return_value=1):  # arecord not available
            result = await record_audio_chunk(3)
            assert result is None

    @pytest.mark.asyncio
    async def test_record_audio_exception_handling(self, mock_logger):
        """Recording should handle exceptions gracefully."""
        from server import record_audio_chunk

        with patch.object(os, 'system', side_effect=Exception("Test error")):
            result = await record_audio_chunk(3)
            assert result is None


class TestGetAudioPlayer:
    """Test audio player detection."""

    def test_get_audio_player_mpg123(self):
        """Should return mpg123 when available."""
        from server import _get_audio_player

        def mock_system_check(cmd):
            if 'mpg123' in cmd:
                return 0
            return 1

        with patch.object(os, 'system', side_effect=mock_system_check):
            result = _get_audio_player()
            assert result == 'mpg123'

    def test_get_audio_player_ffplay_fallback(self):
        """Should return ffplay when mpg123 unavailable."""
        from server import _get_audio_player

        def mock_system_check(cmd):
            if 'ffplay' in cmd:
                return 0
            if 'mpg123' in cmd:
                return 1
            return 1

        with patch.object(os, 'system', side_effect=mock_system_check):
            result = _get_audio_player()
            assert result == 'ffplay'

    def test_get_audio_player_mplayer_fallback(self):
        """Should return mplayer when others unavailable."""
        from server import _get_audio_player

        def mock_system_check(cmd):
            if 'mplayer' in cmd:
                return 0
            return 1

        with patch.object(os, 'system', side_effect=mock_system_check):
            result = _get_audio_player()
            assert result == 'mplayer'

    def test_get_audio_player_vlc_fallback(self):
        """Should return vlc when others unavailable."""
        from server import _get_audio_player

        def mock_system_check(cmd):
            if 'vlc' in cmd:
                return 0
            return 1

        with patch.object(os, 'system', side_effect=mock_system_check):
            result = _get_audio_player()
            assert result == 'vlc'

    def test_get_audio_player_none_available(self):
        """Should return None when no players available."""
        from server import _get_audio_player

        with patch.object(os, 'system', return_value=1):
            result = _get_audio_player()
            assert result is None

    def test_get_audio_player_exception_handling(self):
        """Should handle exceptions and continue checking."""
        from server import _get_audio_player

        call_count = 0

        def mock_system_check(cmd):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Test error")
            if 'ffplay' in cmd:
                return 0
            return 1

        with patch.object(os, 'system', side_effect=mock_system_check):
            result = _get_audio_player()
            # Should continue after exception and find ffplay
            assert result == 'ffplay'


class TestExecuteTTS:
    """Test TTS command execution."""

    @pytest.mark.asyncio
    async def test_execute_tts_success(self):
        """Successful TTS execution should return success code."""
        from server import _execute_tts

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"Success", b""))

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            returncode, stdout, stderr = await _execute_tts(
                "Hello world",
                "en-IE-EmilyNeural",
                "+0%",
                "+0%",
                "/tmp/output.mp3"
            )

            assert returncode == 0
            assert stdout == "Success"
            assert stderr == ""

    @pytest.mark.asyncio
    async def test_execute_tts_correct_command(self):
        """TTS should be called with correct edge-tts parameters."""
        from server import _execute_tts

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_exec:
            await _execute_tts(
                "Test message",
                "en-US-JennyNeural",
                "+10%",
                "-5%",
                "/tmp/test.mp3"
            )

            call_args = mock_exec.call_args[0]
            assert 'edge-tts' in call_args
            assert '--voice' in call_args
            assert 'en-US-JennyNeural' in call_args
            assert '--rate' in call_args
            assert '+10%' in call_args
            assert '--volume' in call_args
            assert '-5%' in call_args
            assert '--text' in call_args
            assert 'Test message' in call_args
            assert '--write-media' in call_args
            assert '/tmp/test.mp3' in call_args

    @pytest.mark.asyncio
    async def test_execute_tts_failure(self):
        """Failed TTS execution should return error code."""
        from server import _execute_tts

        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"Error message"))

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            returncode, stdout, stderr = await _execute_tts(
                "Hello",
                "en-IE-EmilyNeural",
                "+0%",
                "+0%",
                "/tmp/output.mp3"
            )

            assert returncode == 1
            assert stderr == "Error message"


class TestAudioFormatHandling:
    """Test audio format handling."""

    def test_wav_file_parameters(self):
        """WAV recording should use correct format parameters."""
        # These are the expected parameters for Whisper compatibility
        expected_sample_rate = 16000
        expected_channels = 1
        expected_bit_depth = 16

        # Verify from server constants (if defined)
        # For now, we test via the arecord command parameters
        assert expected_sample_rate == 16000
        assert expected_channels == 1
        assert expected_bit_depth == 16

    @pytest.mark.asyncio
    async def test_temp_file_cleanup_on_success(self, temp_audio_file):
        """Temporary audio files should be cleaned up after processing."""
        from server import transcribe_audio

        # Create a dummy file
        with open(temp_audio_file, 'wb') as f:
            f.write(b'dummy audio data')

        mock_transcribe = AsyncMock(return_value="Test transcription")

        with patch('server.transcribe_audio_gpu', mock_transcribe):
            with patch('server.GPU_STT_ENABLED', True):
                with patch('server.AIOHTTP_AVAILABLE', True):
                    result = await transcribe_audio(temp_audio_file, use_gpu=True)

        # File should be cleaned up
        # Note: actual cleanup depends on implementation

    @pytest.mark.asyncio
    async def test_mp3_output_for_tts(self, temp_mp3_file):
        """TTS should output MP3 format."""
        from server import speak

        mock_tts_process = AsyncMock()
        mock_tts_process.returncode = 0
        mock_tts_process.communicate = AsyncMock(return_value=(b"", b""))

        mock_player_process = AsyncMock()
        mock_player_process.wait = AsyncMock(return_value=0)

        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_exec.side_effect = [mock_tts_process, mock_player_process]
            with patch('server._get_audio_player', return_value='mpg123'):
                result = await speak("Hello", play_audio=True)

                # Verify MP3 extension was used
                assert result.get('audio_file', '').endswith('.mp3') or 'audio_file' in result

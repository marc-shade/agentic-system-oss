"""
Tests for TTS (Text-to-Speech) functionality using Edge TTS.

Tests cover:
- speak() tool functionality
- list_voices() tool functionality
- Voice configuration options
- Rate and volume adjustments
- Audio playback options
- Error handling

Note: All subprocess calls are mocked - no actual commands are run.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSpeak:
    """Test speak() TTS functionality."""

    @pytest.mark.asyncio
    async def test_speak_success(self):
        """Successful speak should return success with audio file."""
        from server import speak

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_process.wait = AsyncMock(return_value=0)

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('server._get_audio_player', return_value='mpg123'):
                result = await speak("Hello world")

        assert result['success'] is True
        assert 'audio_file' in result
        assert result['audio_file'].endswith('.mp3')
        assert result['text_length'] == len("Hello world")

    @pytest.mark.asyncio
    async def test_speak_with_custom_voice(self):
        """Speak should use custom voice when specified."""
        from server import speak

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_subprocess:
            with patch('server._get_audio_player', return_value=None):
                result = await speak("Hello", voice="en-US-JennyNeural", play_audio=False)

        # Verify the custom voice was used
        call_args = mock_subprocess.call_args[0]
        assert 'en-US-JennyNeural' in call_args
        assert result['voice'] == "en-US-JennyNeural"

    @pytest.mark.asyncio
    async def test_speak_with_rate_adjustment(self):
        """Speak should apply rate adjustment."""
        from server import speak

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_subprocess:
            with patch('server._get_audio_player', return_value=None):
                await speak("Hello", rate="+20%", play_audio=False)

        call_args = mock_subprocess.call_args[0]
        assert '+20%' in call_args

    @pytest.mark.asyncio
    async def test_speak_with_volume_adjustment(self):
        """Speak should apply volume adjustment."""
        from server import speak

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_subprocess:
            with patch('server._get_audio_player', return_value=None):
                await speak("Hello", volume="-10%", play_audio=False)

        call_args = mock_subprocess.call_args[0]
        assert '-10%' in call_args

    @pytest.mark.asyncio
    async def test_speak_default_voice(self):
        """Speak should use Irish Emily voice by default."""
        from server import speak, DEFAULT_VOICE

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_subprocess:
            with patch('server._get_audio_player', return_value=None):
                await speak("Hello", play_audio=False)

        call_args = mock_subprocess.call_args[0]
        assert DEFAULT_VOICE in call_args

    @pytest.mark.asyncio
    async def test_speak_plays_audio_when_enabled(self):
        """Speak should play audio when play_audio=True."""
        from server import speak

        mock_tts_process = AsyncMock()
        mock_tts_process.returncode = 0
        mock_tts_process.communicate = AsyncMock(return_value=(b"", b""))

        mock_player_process = AsyncMock()
        mock_player_process.wait = AsyncMock(return_value=0)

        call_count = 0

        async def mock_create_subprocess(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_tts_process
            return mock_player_process

        with patch('asyncio.create_subprocess_exec', side_effect=mock_create_subprocess):
            with patch('server._get_audio_player', return_value='mpg123'):
                await speak("Hello", play_audio=True)

        # Should call subprocess twice: once for TTS, once for player
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_speak_skips_audio_when_disabled(self):
        """Speak should not play audio when play_audio=False."""
        from server import speak

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        call_count = 0

        async def mock_create_subprocess(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_process

        with patch('asyncio.create_subprocess_exec', side_effect=mock_create_subprocess):
            with patch('server._get_audio_player', return_value='mpg123'):
                await speak("Hello", play_audio=False)

        # Should only call subprocess once for TTS
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_speak_skips_audio_when_no_player(self):
        """Speak should skip audio when no player available."""
        from server import speak

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        call_count = 0

        async def mock_create_subprocess(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_process

        with patch('asyncio.create_subprocess_exec', side_effect=mock_create_subprocess):
            with patch('server._get_audio_player', return_value=None):
                result = await speak("Hello", play_audio=True)

        # Should only call subprocess once for TTS (no player call)
        assert call_count == 1
        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_speak_tts_failure(self):
        """Speak should return error when TTS fails."""
        from server import speak

        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"TTS error message"))

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            result = await speak("Hello")

        assert result['success'] is False
        assert 'error' in result
        assert 'TTS error message' in result['error']

    @pytest.mark.asyncio
    async def test_speak_exception_handling(self):
        """Speak should handle exceptions gracefully."""
        from server import speak

        with patch('tempfile.NamedTemporaryFile', side_effect=Exception("File error")):
            result = await speak("Hello")

        assert result['success'] is False
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_speak_empty_text(self):
        """Speak should handle empty text."""
        from server import speak

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('server._get_audio_player', return_value=None):
                result = await speak("", play_audio=False)

        assert result['success'] is True
        assert result['text_length'] == 0

    @pytest.mark.asyncio
    async def test_speak_long_text(self):
        """Speak should handle long text."""
        from server import speak

        long_text = "This is a test. " * 100

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('server._get_audio_player', return_value=None):
                result = await speak(long_text, play_audio=False)

        assert result['success'] is True
        assert result['text_length'] == len(long_text)

    @pytest.mark.asyncio
    async def test_speak_unicode_text(self):
        """Speak should handle unicode characters."""
        from server import speak

        unicode_text = "Hello world Bonjour"

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('server._get_audio_player', return_value=None):
                result = await speak(unicode_text, play_audio=False)

        assert result['success'] is True


class TestListVoices:
    """Test list_voices() functionality."""

    @pytest.mark.asyncio
    async def test_list_voices_success(self, edge_tts_voices):
        """list_voices should return matching voices."""
        from server import list_voices

        mock_process = AsyncMock()
        mock_process.returncode = 0
        output = "\n".join(edge_tts_voices)
        mock_process.communicate = AsyncMock(return_value=(output.encode(), b""))

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            result = await list_voices("en-US")

        assert result['success'] is True
        assert len(result['voices']) > 0
        assert any('en-US' in v for v in result['voices'])

    @pytest.mark.asyncio
    async def test_list_voices_filter_by_language(self, edge_tts_voices):
        """list_voices should filter by language prefix."""
        from server import list_voices

        mock_process = AsyncMock()
        mock_process.returncode = 0
        output = "\n".join(edge_tts_voices)
        mock_process.communicate = AsyncMock(return_value=(output.encode(), b""))

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            result = await list_voices("en-GB")

        assert result['success'] is True
        # Should only include en-GB voices
        for voice in result['voices']:
            assert 'en-GB' in voice.lower() or 'en-gb' in voice.lower()

    @pytest.mark.asyncio
    async def test_list_voices_case_insensitive(self, edge_tts_voices):
        """list_voices should be case-insensitive."""
        from server import list_voices

        mock_process = AsyncMock()
        mock_process.returncode = 0
        output = "\n".join(edge_tts_voices)
        mock_process.communicate = AsyncMock(return_value=(output.encode(), b""))

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            result1 = await list_voices("en-us")
            result2 = await list_voices("EN-US")

        # Both should find the same voices
        assert result1['total_count'] == result2['total_count']

    @pytest.mark.asyncio
    async def test_list_voices_limit(self, edge_tts_voices):
        """list_voices should limit results to 10."""
        from server import list_voices

        # Create more than 10 voices
        many_voices = [f"Name: en-US-Voice{i}, Gender: Female" for i in range(20)]

        mock_process = AsyncMock()
        mock_process.returncode = 0
        output = "\n".join(many_voices)
        mock_process.communicate = AsyncMock(return_value=(output.encode(), b""))

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            result = await list_voices("en-US")

        assert len(result['voices']) == 10
        assert result['total_count'] == 20

    @pytest.mark.asyncio
    async def test_list_voices_failure(self):
        """list_voices should handle failure gracefully."""
        from server import list_voices

        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"Error"))

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            result = await list_voices("en-US")

        assert result['success'] is False
        assert result['voices'] == []

    @pytest.mark.asyncio
    async def test_list_voices_exception_handling(self):
        """list_voices should handle exceptions gracefully."""
        from server import list_voices

        with patch('asyncio.create_subprocess_exec', side_effect=Exception("Test error")):
            result = await list_voices("en-US")

        assert result['success'] is False
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_list_voices_no_matches(self):
        """list_voices should return empty when no matches."""
        from server import list_voices

        mock_process = AsyncMock()
        mock_process.returncode = 0
        output = "Name: fr-FR-VoiceFrench, Gender: Female"
        mock_process.communicate = AsyncMock(return_value=(output.encode(), b""))

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            result = await list_voices("zh-CN")  # Chinese - no matches

        assert result['success'] is True
        assert len(result['voices']) == 0


class TestTTSConfiguration:
    """Test TTS configuration options."""

    def test_default_voice_constant(self):
        """Default voice should be Irish Emily."""
        from server import DEFAULT_VOICE

        assert DEFAULT_VOICE == "en-IE-EmilyNeural"

    def test_default_rate_constant(self):
        """Default rate should be +0%."""
        from server import DEFAULT_RATE

        assert DEFAULT_RATE == "+0%"

    def test_default_volume_constant(self):
        """Default volume should be +0%."""
        from server import DEFAULT_VOLUME

        assert DEFAULT_VOLUME == "+0%"


class TestTTSEdgeCases:
    """Test TTS edge cases."""

    @pytest.mark.asyncio
    async def test_speak_with_special_characters(self):
        """Speak should handle special characters."""
        from server import speak

        special_text = "Hello! Test 'quotes' and more"

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('server._get_audio_player', return_value=None):
                result = await speak(special_text, play_audio=False)

        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_speak_with_newlines(self):
        """Speak should handle newlines."""
        from server import speak

        text_with_newlines = "Line 1\nLine 2\nLine 3"

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('server._get_audio_player', return_value=None):
                result = await speak(text_with_newlines, play_audio=False)

        assert result['success'] is True

    @pytest.mark.asyncio
    async def test_speak_rate_percentage_formats(self):
        """Speak should accept various rate formats."""
        from server import speak

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        rates = ["+50%", "-25%", "+0%", "+100%", "-100%"]

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('server._get_audio_player', return_value=None):
                for rate in rates:
                    result = await speak("Test", rate=rate, play_audio=False)
                    assert result['success'] is True

    @pytest.mark.asyncio
    async def test_speak_waits_for_playback(self):
        """Speak should wait for audio playback to complete."""
        from server import speak

        mock_tts_process = AsyncMock()
        mock_tts_process.returncode = 0
        mock_tts_process.communicate = AsyncMock(return_value=(b"", b""))

        mock_player_process = AsyncMock()
        wait_called = False

        async def mock_wait():
            nonlocal wait_called
            wait_called = True
            return 0

        mock_player_process.wait = mock_wait

        call_count = 0

        async def mock_create_subprocess(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_tts_process
            return mock_player_process

        with patch('asyncio.create_subprocess_exec', side_effect=mock_create_subprocess):
            with patch('server._get_audio_player', return_value='mpg123'):
                await speak("Hello", play_audio=True)

        # Verify wait was called on player
        assert wait_called

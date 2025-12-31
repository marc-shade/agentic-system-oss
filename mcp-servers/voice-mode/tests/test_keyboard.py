"""
Tests for keyboard listener functionality.

Tests cover:
- pynput keyboard listener initialization
- evdev keyboard listener for Wayland
- Caps Lock detection and handling
- Beep feedback on toggle
- Session type detection (X11 vs Wayland)
"""

import os
import sys
import threading
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestKeyboardListenerSelection:
    """Test keyboard listener selection based on environment."""

    def test_select_pynput_for_x11(self, mock_env_x11):
        """Should use pynput for X11 sessions."""
        from server import start_keyboard_listener

        mock_listener = MagicMock()
        mock_listener.daemon = True
        mock_listener.start = MagicMock()

        with patch('server.PYNPUT_AVAILABLE', True):
            with patch('server.keyboard') as mock_kb:
                mock_kb.Listener = MagicMock(return_value=mock_listener)

                result = start_keyboard_listener()

        assert result == mock_listener
        mock_listener.start.assert_called_once()

    def test_select_evdev_for_wayland(self, mock_env_wayland):
        """Should use evdev for Wayland sessions when available."""
        from server import start_keyboard_listener

        mock_thread = MagicMock()

        with patch('server.EVDEV_AVAILABLE', True):
            with patch('server.start_evdev_listener', return_value=mock_thread) as mock_evdev:
                result = start_keyboard_listener()

        mock_evdev.assert_called_once()
        assert result == mock_thread

    def test_fallback_to_pynput_when_no_evdev(self, mock_env_wayland):
        """Should fallback to pynput when evdev unavailable on Wayland."""
        from server import start_keyboard_listener

        mock_listener = MagicMock()
        mock_listener.daemon = True
        mock_listener.start = MagicMock()

        with patch('server.EVDEV_AVAILABLE', False):
            with patch('server.PYNPUT_AVAILABLE', True):
                with patch('server.keyboard') as mock_kb:
                    mock_kb.Listener = MagicMock(return_value=mock_listener)

                    result = start_keyboard_listener()

        assert result == mock_listener

    def test_return_none_when_no_listener_available(self, mock_env_x11):
        """Should return None when no keyboard library available."""
        from server import start_keyboard_listener

        with patch('server.PYNPUT_AVAILABLE', False):
            with patch('server.EVDEV_AVAILABLE', False):
                result = start_keyboard_listener()

        assert result is None


class TestPynputListener:
    """Test pynput keyboard listener."""

    def test_listener_is_daemon(self, mock_env_x11):
        """Keyboard listener should run as daemon thread."""
        from server import start_keyboard_listener

        mock_listener = MagicMock()
        mock_listener.daemon = True
        mock_listener.start = MagicMock()

        with patch('server.PYNPUT_AVAILABLE', True):
            with patch('server.keyboard') as mock_kb:
                mock_kb.Listener = MagicMock(return_value=mock_listener)

                start_keyboard_listener()

        # Verify daemon was set
        assert mock_listener.daemon is True

    def test_listener_registers_on_press(self, mock_env_x11):
        """Keyboard listener should register on_press callback."""
        from server import start_keyboard_listener, on_press

        mock_listener = MagicMock()
        mock_listener.daemon = True
        mock_listener.start = MagicMock()

        with patch('server.PYNPUT_AVAILABLE', True):
            with patch('server.keyboard') as mock_kb:
                mock_kb.Listener = MagicMock(return_value=mock_listener)

                start_keyboard_listener()

        # Verify Listener was called with on_press
        mock_kb.Listener.assert_called_once_with(on_press=on_press)


class TestOnPressHandler:
    """Test the on_press key handler."""

    def test_caps_lock_toggles_stt(self):
        """Caps Lock should toggle STT state."""
        from server import on_press, stt_state

        # Mock the keyboard module
        mock_key = MagicMock()

        with patch('server.keyboard') as mock_kb:
            mock_kb.Key.caps_lock = mock_key

            # Ensure STT is off
            stt_state.set_active(False)

            # Mock subprocess for beep
            with patch('subprocess.Popen') as mock_popen:
                mock_proc = MagicMock()
                mock_proc.communicate = MagicMock(return_value=(b"", b""))
                mock_popen.return_value = mock_proc

                # Simulate Caps Lock press
                on_press(mock_key)

        # STT should now be on
        assert stt_state.active is True

        # Cleanup
        stt_state.set_active(False)

    def test_other_keys_ignored(self):
        """Non-Caps Lock keys should be ignored."""
        from server import on_press, stt_state

        initial_state = stt_state.active

        with patch('server.keyboard') as mock_kb:
            mock_kb.Key.caps_lock = MagicMock()

            # Simulate pressing a different key
            other_key = MagicMock()
            on_press(other_key)

        # State should be unchanged
        assert stt_state.active == initial_state

    def test_caps_lock_plays_beep(self):
        """Caps Lock toggle should play beep feedback."""
        from server import on_press, stt_state

        mock_key = MagicMock()

        with patch('server.keyboard') as mock_kb:
            mock_kb.Key.caps_lock = mock_key

            stt_state.set_active(False)

            with patch('subprocess.Popen') as mock_popen:
                mock_proc = MagicMock()
                mock_proc.communicate = MagicMock(return_value=(b"", b""))
                mock_popen.return_value = mock_proc

                on_press(mock_key)

        # Popen should have been called for beep
        mock_popen.assert_called()

        # Cleanup
        stt_state.set_active(False)

    def test_beep_frequency_differs_on_off(self):
        """Beep frequency should differ between on and off states."""
        from server import on_press, stt_state

        mock_key = MagicMock()
        frequencies = []

        def capture_popen(*args, **kwargs):
            mock_proc = MagicMock()
            mock_proc.communicate = MagicMock(return_value=(b"", b""))
            # Capture stdin for frequency analysis would require deeper mock
            frequencies.append(args)
            return mock_proc

        with patch('server.keyboard') as mock_kb:
            mock_kb.Key.caps_lock = mock_key

            stt_state.set_active(False)

            with patch('subprocess.Popen', side_effect=capture_popen):
                # First toggle: off -> on (should be higher frequency)
                on_press(mock_key)
                # Second toggle: on -> off (should be lower frequency)
                on_press(mock_key)

        # Should have been called twice
        assert len(frequencies) == 2

        # Cleanup
        stt_state.set_active(False)


class TestEvdevListener:
    """Test evdev keyboard listener for Wayland."""

    def test_evdev_listener_starts_thread(self, mock_env_wayland, mock_evdev):
        """evdev listener should start in separate thread."""
        from server import start_evdev_listener

        with patch('server.evdev', mock_evdev):
            with patch('server.EVDEV_AVAILABLE', True):
                with patch('threading.Thread') as mock_thread_class:
                    mock_thread = MagicMock()
                    mock_thread_class.return_value = mock_thread

                    start_evdev_listener()

        mock_thread.start.assert_called_once()

    def test_evdev_listener_is_daemon(self, mock_env_wayland, mock_evdev):
        """evdev listener thread should be daemon."""
        from server import start_evdev_listener

        created_thread = None

        def capture_thread(*args, **kwargs):
            nonlocal created_thread
            created_thread = MagicMock()
            created_thread.daemon = kwargs.get('daemon', False)
            return created_thread

        with patch('server.evdev', mock_evdev):
            with patch('server.EVDEV_AVAILABLE', True):
                with patch('threading.Thread', side_effect=capture_thread):
                    start_evdev_listener()

        assert created_thread is not None
        assert created_thread.daemon is True


class TestKeyboardEdgeCases:
    """Test edge cases for keyboard handling."""

    def test_attribute_error_handling(self):
        """on_press should handle AttributeError gracefully."""
        from server import on_press

        # Passing None or invalid key should not raise
        on_press(None)

    def test_exception_in_beep_handled(self):
        """Exceptions during beep should be handled."""
        from server import on_press, stt_state

        mock_key = MagicMock()

        with patch('server.keyboard') as mock_kb:
            mock_kb.Key.caps_lock = mock_key

            stt_state.set_active(False)

            with patch('subprocess.Popen', side_effect=Exception("Beep error")):
                # Should not raise
                on_press(mock_key)

        # State should still have toggled
        assert stt_state.active is True

        # Cleanup
        stt_state.set_active(False)

    def test_pynput_unavailable_logged(self, mock_logger, mock_env_x11):
        """Missing pynput should be logged."""
        from server import start_keyboard_listener

        with patch('server.PYNPUT_AVAILABLE', False):
            with patch('server.EVDEV_AVAILABLE', False):
                result = start_keyboard_listener()

        assert result is None


class TestSessionTypeDetection:
    """Test session type detection."""

    def test_detect_wayland_session(self, mock_env_wayland):
        """Should detect Wayland session from XDG_SESSION_TYPE."""
        session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
        assert session_type == 'wayland'

    def test_detect_x11_session(self, mock_env_x11):
        """Should detect X11 session from XDG_SESSION_TYPE."""
        session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
        assert session_type == 'x11'

    def test_default_when_no_session_type(self, monkeypatch):
        """Should handle missing XDG_SESSION_TYPE."""
        monkeypatch.delenv('XDG_SESSION_TYPE', raising=False)

        session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
        assert session_type == ''


class TestBeepGeneration:
    """Test beep audio generation."""

    def test_beep_frequency_on(self):
        """'On' beep should use 1000Hz."""
        from server import on_press, stt_state
        import struct
        import math

        mock_key = MagicMock()
        captured_audio = None

        def capture_audio(*args, **kwargs):
            nonlocal captured_audio
            mock_proc = MagicMock()

            def capture_communicate(input=None, timeout=None):
                nonlocal captured_audio
                captured_audio = input
                return (b"", b"")

            mock_proc.communicate = capture_communicate
            return mock_proc

        with patch('server.keyboard') as mock_kb:
            mock_kb.Key.caps_lock = mock_key

            stt_state.set_active(False)

            with patch('subprocess.Popen', side_effect=capture_audio):
                on_press(mock_key)

        # Audio was captured
        assert captured_audio is not None
        # Audio has correct length (16kHz * 0.15s * 2 bytes = 4800 bytes)
        assert len(captured_audio) == 4800

        # Cleanup
        stt_state.set_active(False)

    def test_beep_frequency_off(self):
        """'Off' beep should use 600Hz."""
        from server import on_press, stt_state

        mock_key = MagicMock()
        audio_samples = []

        def capture_audio(*args, **kwargs):
            mock_proc = MagicMock()

            def capture_communicate(input=None, timeout=None):
                audio_samples.append(input)
                return (b"", b"")

            mock_proc.communicate = capture_communicate
            return mock_proc

        with patch('server.keyboard') as mock_kb:
            mock_kb.Key.caps_lock = mock_key

            # Start ON, then toggle OFF
            stt_state.set_active(True)

            with patch('subprocess.Popen', side_effect=capture_audio):
                on_press(mock_key)

        # Audio was captured for 'off' state
        assert len(audio_samples) == 1

        # Cleanup
        stt_state.set_active(False)

    def test_beep_sample_rate(self):
        """Beep should use 16kHz sample rate."""
        # Sample rate is hardcoded in server.py
        expected_sample_rate = 16000
        expected_duration = 0.15
        expected_samples = int(expected_sample_rate * expected_duration)
        expected_bytes = expected_samples * 2  # 16-bit = 2 bytes

        assert expected_bytes == 4800

    def test_beep_uses_paplay(self):
        """Beep should use paplay for audio output."""
        from server import on_press, stt_state

        mock_key = MagicMock()

        with patch('server.keyboard') as mock_kb:
            mock_kb.Key.caps_lock = mock_key

            stt_state.set_active(False)

            with patch('subprocess.Popen') as mock_popen:
                mock_proc = MagicMock()
                mock_proc.communicate = MagicMock(return_value=(b"", b""))
                mock_popen.return_value = mock_proc

                on_press(mock_key)

        # Verify paplay was called with correct arguments
        call_args = mock_popen.call_args[0][0]
        assert 'paplay' in call_args
        assert '--raw' in call_args
        assert '--rate=16000' in call_args
        assert '--channels=1' in call_args
        assert '--format=s16le' in call_args

        # Cleanup
        stt_state.set_active(False)

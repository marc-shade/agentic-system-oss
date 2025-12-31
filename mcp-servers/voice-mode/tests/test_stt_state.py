"""
Tests for STTState class - Thread-safe STT state manager.

Tests cover:
- State initialization
- Thread-safe toggle operations
- Active state management
- Transcription history management
- Concurrent access scenarios
"""

import os
import sys
import threading
import time
from datetime import datetime
from unittest.mock import patch

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import STTState


class TestSTTStateInitialization:
    """Test STTState initialization."""

    def test_initial_state_is_inactive(self):
        """STTState should start as inactive."""
        state = STTState()
        assert state.active is False

    def test_initial_listener_is_none(self):
        """Keyboard listener should be None initially."""
        state = STTState()
        assert state._listener is None

    def test_initial_listening_task_is_none(self):
        """Listening task should be None initially."""
        state = STTState()
        assert state._listening_task is None

    def test_initial_whisper_model_is_none(self):
        """Whisper model should be None initially."""
        state = STTState()
        assert state._whisper_model is None

    def test_initial_transcriptions_is_empty(self):
        """Transcriptions list should be empty initially."""
        state = STTState()
        assert state._transcriptions == []


class TestSTTStateToggle:
    """Test STTState toggle functionality."""

    def test_toggle_activates_when_inactive(self, fresh_stt_state):
        """Toggle should activate STT when inactive."""
        assert fresh_stt_state.active is False
        new_state = fresh_stt_state.toggle()
        assert new_state is True
        assert fresh_stt_state.active is True

    def test_toggle_deactivates_when_active(self, active_stt_state):
        """Toggle should deactivate STT when active."""
        assert active_stt_state.active is True
        new_state = active_stt_state.toggle()
        assert new_state is False
        assert active_stt_state.active is False

    def test_toggle_returns_new_state(self, fresh_stt_state):
        """Toggle should return the new state value."""
        result1 = fresh_stt_state.toggle()
        assert result1 is True

        result2 = fresh_stt_state.toggle()
        assert result2 is False

    def test_multiple_toggles(self, fresh_stt_state):
        """Multiple toggles should alternate state correctly."""
        states = []
        for _ in range(10):
            states.append(fresh_stt_state.toggle())

        expected = [True, False, True, False, True, False, True, False, True, False]
        assert states == expected


class TestSTTStateSetActive:
    """Test explicit state setting."""

    def test_set_active_true(self, fresh_stt_state):
        """set_active(True) should activate STT."""
        fresh_stt_state.set_active(True)
        assert fresh_stt_state.active is True

    def test_set_active_false(self, active_stt_state):
        """set_active(False) should deactivate STT."""
        active_stt_state.set_active(False)
        assert active_stt_state.active is False

    def test_set_active_idempotent_true(self, active_stt_state):
        """Setting active to True when already active should be idempotent."""
        active_stt_state.set_active(True)
        assert active_stt_state.active is True
        active_stt_state.set_active(True)
        assert active_stt_state.active is True

    def test_set_active_idempotent_false(self, fresh_stt_state):
        """Setting active to False when already inactive should be idempotent."""
        fresh_stt_state.set_active(False)
        assert fresh_stt_state.active is False


class TestSTTStateTranscriptions:
    """Test transcription history management."""

    def test_add_transcription_stores_text(self, fresh_stt_state):
        """add_transcription should store the text."""
        fresh_stt_state.add_transcription("Hello world")
        transcriptions = fresh_stt_state.get_transcriptions()

        assert len(transcriptions) == 1
        assert transcriptions[0]['text'] == "Hello world"

    def test_add_transcription_includes_timestamp(self, fresh_stt_state):
        """add_transcription should include a timestamp."""
        fresh_stt_state.add_transcription("Test message")
        transcriptions = fresh_stt_state.get_transcriptions()

        assert 'timestamp' in transcriptions[0]
        # Verify timestamp is ISO format
        datetime.fromisoformat(transcriptions[0]['timestamp'])

    def test_get_transcriptions_with_limit(self, fresh_stt_state):
        """get_transcriptions should respect the limit parameter."""
        for i in range(20):
            fresh_stt_state.add_transcription(f"Message {i}")

        limited = fresh_stt_state.get_transcriptions(limit=5)
        assert len(limited) == 5

        # Should return most recent (last 5)
        assert limited[0]['text'] == "Message 15"
        assert limited[-1]['text'] == "Message 19"

    def test_get_transcriptions_default_limit(self, fresh_stt_state):
        """Default limit should be 10."""
        for i in range(20):
            fresh_stt_state.add_transcription(f"Message {i}")

        default_result = fresh_stt_state.get_transcriptions()
        assert len(default_result) == 10

    def test_max_transcriptions_is_50(self, fresh_stt_state):
        """Transcription history should be limited to 50 entries."""
        for i in range(100):
            fresh_stt_state.add_transcription(f"Message {i}")

        # Internal storage should only have 50
        assert len(fresh_stt_state._transcriptions) == 50

        # Should have the most recent 50 (50-99)
        all_transcriptions = fresh_stt_state.get_transcriptions(limit=100)
        assert len(all_transcriptions) == 50
        assert all_transcriptions[0]['text'] == "Message 50"
        assert all_transcriptions[-1]['text'] == "Message 99"

    def test_get_transcriptions_returns_copy(self, fresh_stt_state):
        """get_transcriptions should return a copy, not the original list."""
        fresh_stt_state.add_transcription("Original")
        transcriptions = fresh_stt_state.get_transcriptions()

        # Modifying the returned list should not affect the original
        transcriptions.append({"text": "Modified", "timestamp": "2024-01-01"})

        assert len(fresh_stt_state.get_transcriptions()) == 1

    def test_empty_transcription(self, fresh_stt_state):
        """Empty transcriptions should still be stored."""
        fresh_stt_state.add_transcription("")
        transcriptions = fresh_stt_state.get_transcriptions()

        assert len(transcriptions) == 1
        assert transcriptions[0]['text'] == ""


class TestSTTStateThreadSafety:
    """Test thread safety of STTState operations."""

    def test_concurrent_toggles(self, fresh_stt_state):
        """Concurrent toggles should not cause race conditions."""
        toggle_count = 1000
        results = []
        errors = []

        def toggle_worker():
            try:
                for _ in range(toggle_count):
                    fresh_stt_state.toggle()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=toggle_worker) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_transcription_adds(self, fresh_stt_state):
        """Concurrent transcription adds should not lose data."""
        add_count = 100  # Per thread (50 max limit means some will be pruned)
        thread_count = 5
        errors = []

        def add_worker(thread_id):
            try:
                for i in range(add_count):
                    fresh_stt_state.add_transcription(f"Thread {thread_id} Message {i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_worker, args=(i,)) for i in range(thread_count)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # Should have exactly 50 (the max limit)
        assert len(fresh_stt_state._transcriptions) == 50

    def test_concurrent_read_write(self, fresh_stt_state):
        """Concurrent reads and writes should not cause issues."""
        errors = []
        stop_event = threading.Event()

        def writer():
            try:
                counter = 0
                while not stop_event.is_set():
                    fresh_stt_state.add_transcription(f"Message {counter}")
                    fresh_stt_state.toggle()
                    counter += 1
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                while not stop_event.is_set():
                    _ = fresh_stt_state.active
                    _ = fresh_stt_state.get_transcriptions()
            except Exception as e:
                errors.append(e)

        writers = [threading.Thread(target=writer) for _ in range(3)]
        readers = [threading.Thread(target=reader) for _ in range(3)]

        for t in writers + readers:
            t.start()

        time.sleep(0.5)  # Let threads run for a bit
        stop_event.set()

        for t in writers + readers:
            t.join()

        assert len(errors) == 0


class TestSTTStateEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_transcription_with_unicode(self, fresh_stt_state):
        """Transcriptions with unicode characters should work."""
        fresh_stt_state.add_transcription("Hello 世界 Bonjour")
        transcriptions = fresh_stt_state.get_transcriptions()

        assert transcriptions[0]['text'] == "Hello 世界 Bonjour"

    def test_transcription_with_special_characters(self, fresh_stt_state):
        """Transcriptions with special characters should work."""
        special_text = "Hello! @#$%^&*()_+ \n\t\r quotes: 'single' \"double\""
        fresh_stt_state.add_transcription(special_text)
        transcriptions = fresh_stt_state.get_transcriptions()

        assert transcriptions[0]['text'] == special_text

    def test_transcription_with_very_long_text(self, fresh_stt_state):
        """Very long transcriptions should be stored correctly."""
        long_text = "x" * 10000
        fresh_stt_state.add_transcription(long_text)
        transcriptions = fresh_stt_state.get_transcriptions()

        assert transcriptions[0]['text'] == long_text

    def test_get_transcriptions_limit_zero(self, fresh_stt_state):
        """Limit of 0 should return empty list."""
        fresh_stt_state.add_transcription("Test")
        transcriptions = fresh_stt_state.get_transcriptions(limit=0)

        assert transcriptions == []

    def test_get_transcriptions_limit_negative(self, fresh_stt_state):
        """Negative limit should work (Python slicing behavior)."""
        for i in range(10):
            fresh_stt_state.add_transcription(f"Message {i}")

        # Negative limit in Python slicing returns from end
        transcriptions = fresh_stt_state.get_transcriptions(limit=-5)
        # This depends on implementation - testing current behavior
        assert isinstance(transcriptions, list)

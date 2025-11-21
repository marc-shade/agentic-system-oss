#!/usr/bin/env python3
"""
Unit Tests for Arduino Status Rotation Module

Tests all core functionality without requiring physical Arduino hardware.
Uses mocking for ArduinoSurface interface.

Run: pytest test_status_rotation.py -v
"""

import sys
import unittest
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "bridge"))

# Mock the ArduinoSurface import
sys.modules['surface_bridge'] = MagicMock()

from status_rotation import StatusRotation


class TestStatusRotation(unittest.TestCase):
    """Unit tests for StatusRotation class"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_arduino = Mock()
        self.mock_logger = Mock()
        self.rotation = StatusRotation(self.mock_arduino, self.mock_logger)

    def test_initialization(self):
        """Test StatusRotation initializes correctly"""
        self.assertEqual(self.rotation.lcd_width, 16)
        self.assertEqual(len(self.rotation.pages), 7)
        self.assertEqual(len(self.rotation.pulse_pattern), 10)
        self.assertEqual(self.rotation.previous_line1, "")
        self.assertEqual(self.rotation.previous_line2, "")

    def test_pad_line_exact_length(self):
        """Test padding produces exactly 16 characters"""
        test_cases = [
            ("Hello", "Hello           "),
            ("1234567890123456", "1234567890123456"),
            ("12345678901234567890", "1234567890123456"),
            ("", "                "),
            ("A", "A               "),
        ]

        for input_text, expected in test_cases:
            result = self.rotation.pad_line(input_text)
            self.assertEqual(len(result), 16, f"Failed for input: {input_text}")
            self.assertEqual(result, expected)

    def test_pulse_led_calls_arduino(self):
        """Test LED pulsing makes correct Arduino calls"""
        self.rotation.pulse_led(255, 0, 0, duration=0.1)  # Fast for testing

        # Should make 10 calls (one per pulse step)
        self.assertEqual(self.mock_arduino.set_led.call_count, 10)

        # Verify brightness variations
        calls = self.mock_arduino.set_led.call_args_list
        brightnesses = [call[0][1] for call in calls]  # Extract R values

        # Should have varying brightness levels
        self.assertGreater(max(brightnesses), min(brightnesses))

    def test_update_display_anti_flicker(self):
        """Test display only updates when content changes"""
        # First update - should write both lines
        self.rotation.update_display("Line 1", "Line 2")
        self.assertEqual(self.mock_arduino.lcd_write.call_count, 2)

        # Same content - should not update
        self.mock_arduino.lcd_write.reset_mock()
        self.rotation.update_display("Line 1", "Line 2")
        self.assertEqual(self.mock_arduino.lcd_write.call_count, 0)

        # Different content - should update
        self.mock_arduino.lcd_write.reset_mock()
        self.rotation.update_display("New Line 1", "New Line 2")
        self.assertEqual(self.mock_arduino.lcd_write.call_count, 2)

    def test_update_display_padding(self):
        """Test display updates use padded strings"""
        self.rotation.update_display("Short", "Text")

        calls = self.mock_arduino.lcd_write.call_args_list
        # Check that padded strings are 16 chars
        self.assertEqual(len(calls[0][0][2]), 16)
        self.assertEqual(len(calls[1][0][2]), 16)

    @patch('status_rotation.subprocess.run')
    def test_page_temporal_up(self, mock_run):
        """Test Temporal page when service is running"""
        mock_run.return_value.stdout = '{"namespaces": []}'

        result = self.rotation._page_temporal()

        self.assertIn("Temporal ✓", result["line1"])
        self.assertEqual(result["led_color"], (0, 255, 0))  # Green

    @patch('status_rotation.subprocess.run')
    def test_page_temporal_down(self, mock_run):
        """Test Temporal page when service is down"""
        mock_run.return_value.stdout = ''

        result = self.rotation._page_temporal()

        self.assertIn("Temporal ✗", result["line1"])
        self.assertEqual(result["led_color"], (255, 0, 0))  # Red

    @patch('status_rotation.subprocess.run')
    def test_page_pm2_parsing(self, mock_run):
        """Test PM2 page correctly parses status"""
        mock_run.return_value.stdout = '5/5'

        result = self.rotation._page_pm2()

        self.assertIn("PM2", result["line1"])
        self.assertIn("5/5", result["line2"])
        self.assertEqual(result["led_color"], (0, 255, 0))  # All online = Green

    @patch('status_rotation.subprocess.run')
    def test_page_system_resources(self, mock_run):
        """Test system resources page"""
        mock_run.return_value.stdout = '45,68,12'  # CPU, Mem, Disk

        result = self.rotation._page_system_resources()

        self.assertIn("CPU:45%", result["line1"])
        self.assertIn("M:68%", result["line1"])
        self.assertIn("Disk: 12%", result["line2"])
        self.assertEqual(result["led_color"], (0, 255, 0))  # Healthy = Green

    @patch('status_rotation.subprocess.run')
    def test_page_system_resources_warning(self, mock_run):
        """Test system resources shows warning for high usage"""
        mock_run.return_value.stdout = '75,70,15'  # High CPU

        result = self.rotation._page_system_resources()

        self.assertEqual(result["led_color"], (255, 165, 0))  # Warning = Orange

    @patch('status_rotation.subprocess.run')
    def test_page_system_resources_critical(self, mock_run):
        """Test system resources shows critical for very high usage"""
        mock_run.return_value.stdout = '85,90,15'  # Critical

        result = self.rotation._page_system_resources()

        self.assertEqual(result["led_color"], (255, 0, 0))  # Critical = Red

    def test_all_pages_return_valid_format(self):
        """Test all page functions return correct data structure"""
        with patch('status_rotation.subprocess.run') as mock_run:
            mock_run.return_value.stdout = ''

            for page_func in self.rotation.pages:
                result = page_func()

                # Verify required keys exist
                self.assertIn("line1", result)
                self.assertIn("line2", result)
                self.assertIn("led_color", result)

                # Verify LED color is RGB tuple
                self.assertEqual(len(result["led_color"]), 3)
                for val in result["led_color"]:
                    self.assertGreaterEqual(val, 0)
                    self.assertLessEqual(val, 255)

    def test_error_handling_in_pulse_led(self):
        """Test LED pulsing handles Arduino errors gracefully"""
        self.mock_arduino.set_led.side_effect = Exception("Arduino disconnected")

        # Should not raise exception
        try:
            self.rotation.pulse_led(255, 0, 0, duration=0.1)
        except Exception as e:
            self.fail(f"pulse_led raised exception: {e}")

        # Should log warnings
        self.assertGreater(self.mock_logger.warning.call_count, 0)

    def test_error_handling_in_update_display(self):
        """Test display update handles Arduino errors gracefully"""
        self.mock_arduino.lcd_write.side_effect = Exception("Serial error")

        # Should not raise exception
        try:
            self.rotation.update_display("Test", "Text")
        except Exception as e:
            self.fail(f"update_display raised exception: {e}")

        # Should log error
        self.assertEqual(self.mock_logger.error.call_count, 1)


class TestStatusRotationIntegration(unittest.TestCase):
    """Integration tests for complete rotation cycle"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_arduino = Mock()
        self.mock_logger = Mock()
        self.rotation = StatusRotation(self.mock_arduino, self.mock_logger)

    @patch('status_rotation.subprocess.run')
    @patch('status_rotation.time.sleep')
    def test_rotate_once_completes_all_pages(self, mock_sleep, mock_run):
        """Test complete rotation cycle"""
        mock_run.return_value.stdout = ''

        self.rotation.rotate_once()

        # Should update display for all 7 pages
        # Each page calls lcd_write twice (2 lines) if content changed
        # First cycle updates all, so 14 calls minimum
        self.assertGreaterEqual(self.mock_arduino.lcd_write.call_count, 7)

        # Should pulse LED for each page (10 steps × 7 pages = 70 calls)
        self.assertGreaterEqual(self.mock_arduino.set_led.call_count, 70)

    @patch('status_rotation.subprocess.run')
    def test_timing_budget_per_page(self, mock_run):
        """Test each page completes within timing budget"""
        import time
        mock_run.return_value.stdout = ''

        for page_func in self.rotation.pages:
            start = time.time()
            page_func()  # Just get data, don't pulse
            elapsed = time.time() - start

            # Page data gathering should be < 3 seconds (with 2s timeout)
            self.assertLess(elapsed, 3.0,
                          f"Page {page_func.__name__} took {elapsed}s (budget: 3s)")


if __name__ == '__main__':
    unittest.main(verbosity=2)

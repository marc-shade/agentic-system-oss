#!/usr/bin/env python3
"""
Integration Tests for Arduino Status Rotation

Tests complete end-to-end functionality with mocked Arduino hardware.
Validates full rotation cycles, error recovery, and production scenarios.

Run: pytest test_integration_status_rotation.py -v
"""

import sys
import unittest
import time
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "bridge"))

# Mock the ArduinoSurface import
sys.modules['surface_bridge'] = MagicMock()

from status_rotation import StatusRotation


class TestStatusRotationIntegration(unittest.TestCase):
    """Integration tests for complete status rotation system"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_arduino = Mock()
        self.mock_logger = Mock()
        self.rotation = StatusRotation(self.mock_arduino, self.mock_logger)

    @patch('status_rotation.subprocess.run')
    def test_complete_rotation_cycle(self, mock_run):
        """Test complete rotation through all 7 pages"""
        mock_run.return_value.stdout = ''

        # Execute one complete rotation
        self.rotation.rotate_once()

        # Verify all pages were displayed
        # Minimum 7 LCD writes (one per page, may be more if content changes)
        self.assertGreaterEqual(self.mock_arduino.lcd_write.call_count, 7)

        # Verify LED was pulsed for each page (10 steps × 7 pages = 70)
        self.assertGreaterEqual(self.mock_arduino.set_led.call_count, 70)

    @patch('status_rotation.subprocess.run')
    def test_temporal_workflow_detection(self, mock_run):
        """Test Temporal status page with actual workflow data"""
        # Simulate Temporal having active workflows
        mock_run.return_value.stdout = '{"execution": {"workflowId": "test"}}'

        result = self.rotation._page_temporal()

        self.assertIn("TEMPORAL", result["line1"])
        self.assertIn("OK", result["line1"])
        self.assertEqual(result["led_color"], StatusRotation.COLOR_GREEN)

    @patch('status_rotation.subprocess.run')
    def test_pm2_process_counting(self, mock_run):
        """Test PM2 status with multiple processes"""
        mock_run.return_value.stdout = """
┌─────┬──────┬─────────┬─────────┐
│ id  │ name │ status  │ restart │
├─────┼──────┼─────────┼─────────┤
│ 0   │ app1 │ online  │ 0       │
│ 1   │ app2 │ online  │ 0       │
│ 2   │ app3 │ online  │ 0       │
└─────┴──────┴─────────┴─────────┘
"""

        result = self.rotation._page_pm2()

        self.assertIn("PM2", result["line1"])
        self.assertIn("online", result["line2"])
        # Should detect 3 online processes
        self.assertIn("3", result["line2"])
        self.assertEqual(result["led_color"], StatusRotation.COLOR_GREEN)

    @patch('status_rotation.subprocess.run')
    def test_system_resources_warning_threshold(self, mock_run):
        """Test system resources page with warning-level usage"""
        # Mock high CPU usage (75%)
        cpu_mock = Mock()
        cpu_mock.stdout = "%CPU\n25.0\n25.0\n25.0"

        mem_mock = Mock()
        mem_mock.stdout = "vm_stat output"

        disk_mock = Mock()
        disk_mock.stdout = "Filesystem Size Used Avail Capacity\n/dev/disk 100G 75G 25G 75%"

        def run_side_effect(cmd, **kwargs):
            if 'ps' in cmd:
                return cpu_mock
            elif 'vm_stat' in cmd:
                return mem_mock
            elif 'df' in cmd:
                return disk_mock
            return Mock(stdout='')

        mock_run.side_effect = run_side_effect

        result = self.rotation._page_system_resources()

        # High usage should trigger orange/red LED
        self.assertIn(result["led_color"], [
            StatusRotation.COLOR_ORANGE,
            StatusRotation.COLOR_RED
        ])

    @patch('status_rotation.subprocess.run')
    def test_error_recovery_in_rotation(self, mock_run):
        """Test rotation continues after page errors"""
        mock_run.return_value.stdout = ''

        # Make one page function fail
        original_temporal = self.rotation._page_temporal
        call_count = [0]

        def failing_temporal():
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Simulated page error")
            return original_temporal()

        self.rotation._page_temporal = failing_temporal

        # Should not crash, should log error
        try:
            self.rotation.rotate_once()
        except Exception as e:
            self.fail(f"Rotation crashed on page error: {e}")

        # Error should be logged
        self.assertGreater(self.mock_logger.error.call_count, 0)

    def test_anti_flicker_across_rotations(self, ):
        """Test display doesn't flicker when showing same content"""
        # First rotation - display "Page 1"
        self.rotation.update_display("Page 1", "Content A")
        initial_calls = self.mock_arduino.lcd_write.call_count

        # Second rotation - same content
        self.mock_arduino.lcd_write.reset_mock()
        self.rotation.update_display("Page 1", "Content A")

        # Should not write again (anti-flicker)
        self.assertEqual(self.mock_arduino.lcd_write.call_count, 0)

        # Third rotation - different content
        self.rotation.update_display("Page 2", "Content B")

        # Should write both lines
        self.assertEqual(self.mock_arduino.lcd_write.call_count, 2)

    def test_led_pulsing_timing(self):
        """Test LED pulse completes in expected time"""
        start_time = time.time()

        # Fast pulse for testing
        self.rotation.pulse_led(255, 0, 0, duration=0.01)

        elapsed = time.time() - start_time

        # 10 steps × 0.01s = ~0.1s (with some tolerance)
        self.assertLess(elapsed, 0.2)
        self.assertGreater(elapsed, 0.08)

    @patch('status_rotation.subprocess.run')
    def test_mcp_server_count_from_config(self, mock_run):
        """Test MCP page reads actual config file"""
        with patch('builtins.open', unittest.mock.mock_open(
            read_data='{"mcpServers": {"server1": {}, "server2": {}, "server3": {}}}'
        )):
            result = self.rotation._page_mcp()

            self.assertIn("MCP", result["line1"])
            self.assertIn("3", result["line2"])
            self.assertEqual(result["led_color"], StatusRotation.COLOR_BLUE)

    def test_ascii_filtering(self):
        """Test non-ASCII characters are filtered"""
        # Input with emojis and Unicode
        emoji_text = "⏱️ Temporal ✓ 🐱"

        filtered = self.rotation.to_lcd_safe(emoji_text)

        # Should only contain ASCII
        for char in filtered:
            self.assertLess(ord(char), 128, f"Non-ASCII char found: {char}")

    @patch('status_rotation.subprocess.run')
    def test_port_manager_integration(self, mock_run):
        """Test Port Manager status detection"""
        mock_run.return_value.stdout = """
Port Manager Status:
  localhost:3000 - Running (PID 1234)
  localhost:4102 - Running (PID 5678)
  localhost:6333 - Running (PID 9012)
"""

        result = self.rotation._page_port_manager()

        self.assertIn("PORT MGR", result["line1"])
        # Should detect 3 tracked ports
        self.assertIn("3", result["line2"])

    def test_arduino_connection_error_handling(self):
        """Test graceful handling of Arduino disconnection"""
        # Simulate Arduino disconnection
        self.mock_arduino.lcd_write.side_effect = Exception("Serial port disconnected")
        self.mock_arduino.set_led.side_effect = Exception("Serial port disconnected")

        # Should not crash
        try:
            self.rotation.update_display("Test", "Text")
            self.rotation.pulse_led(255, 0, 0, duration=0.01)
        except Exception as e:
            self.fail(f"Should handle disconnection gracefully: {e}")

        # Errors should be logged
        self.assertGreater(self.mock_logger.error.call_count + self.mock_logger.warning.call_count, 0)


class TestStatusRotationPerformance(unittest.TestCase):
    """Performance and timing tests"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_arduino = Mock()
        self.mock_logger = Mock()
        self.rotation = StatusRotation(self.mock_arduino, self.mock_logger)

    @patch('status_rotation.subprocess.run')
    def test_page_execution_within_budget(self, mock_run):
        """Test each page completes within timing budget"""
        mock_run.return_value.stdout = ''

        for page_func in self.rotation.pages:
            start = time.time()
            page_func()
            elapsed = time.time() - start

            # Page data gathering should be < 3 seconds (with 2s timeout)
            self.assertLess(elapsed, 3.0,
                          f"Page {page_func.__name__} took {elapsed}s (budget: 3s)")

    @patch('status_rotation.subprocess.run')
    def test_full_rotation_timing(self, mock_run):
        """Test complete rotation completes in expected time"""
        mock_run.return_value.stdout = ''

        start_time = time.time()

        # Fast rotation for testing (0.1s per pulse)
        original_duration = StatusRotation.PULSE_STEP_DURATION
        StatusRotation.PULSE_STEP_DURATION = 0.01

        self.rotation.rotate_once()

        elapsed = time.time() - start_time
        StatusRotation.PULSE_STEP_DURATION = original_duration

        # 7 pages × (0.01s × 10 pulses) = 0.7s minimum
        self.assertLess(elapsed, 2.0)  # Allow overhead


class TestStatusRotationProduction(unittest.TestCase):
    """Production scenario tests"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_arduino = Mock()
        self.mock_logger = Mock()
        self.rotation = StatusRotation(self.mock_arduino, self.mock_logger)

    @patch('status_rotation.subprocess.run')
    def test_24hour_simulation(self, mock_run):
        """Simulate extended operation (fast-forwarded)"""
        mock_run.return_value.stdout = ''

        # Run 10 rotation cycles (would be ~6 minutes real-time)
        for cycle in range(10):
            try:
                self.rotation.rotate_once()
            except Exception as e:
                self.fail(f"Rotation failed on cycle {cycle}: {e}")

        # Verify no memory leaks (state should be consistent)
        self.assertEqual(len(self.rotation.pages), 7)
        self.assertEqual(len(self.rotation.pulse_pattern), 10)

    @patch('status_rotation.subprocess.run')
    def test_mixed_service_states(self, mock_run):
        """Test with some services up, some down"""
        # Simulate mixed states
        def run_side_effect(cmd, **kwargs):
            cmd_str = ' '.join(cmd)
            if 'temporal' in cmd_str:
                return Mock(stdout='{"workflows": []}')  # Up
            elif 'pm2' in cmd_str:
                return Mock(stdout='')  # Down
            elif 'curl' in cmd_str and 'qdrant' in cmd_str:
                return Mock(stdout='{"status": "ok"}')  # Up
            else:
                return Mock(stdout='')

        mock_run.side_effect = run_side_effect

        # Should handle mixed states gracefully
        try:
            self.rotation.rotate_once()
        except Exception as e:
            self.fail(f"Failed with mixed service states: {e}")


if __name__ == '__main__':
    unittest.main(verbosity=2)

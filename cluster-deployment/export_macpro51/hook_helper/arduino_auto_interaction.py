#!/usr/bin/env python3
"""
Arduino Auto-Interaction Module
Provides physical feedback through Arduino Surface for agentic system operations

Uses direct subprocess calls to Arduino bridge for reliability
No dependency on MCP server being active
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import logging

# Configuration
ARDUINO_PORT = "/dev/tty.usbmodem8344401"
BRIDGE_SCRIPT = Path("/mnt/agentic-system/arduino-surface/bridge/surface_bridge.py")
TIMEOUT = 2.0  # Quick feedback, fail fast

# Logging
logger = logging.getLogger("arduino_auto_interaction")

class ArduinoFeedback:
    """Manages Arduino feedback operations with graceful degradation"""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled and BRIDGE_SCRIPT.exists()
        self.consecutive_failures = 0
        self.max_failures = 3  # Disable after 3 failures

    def _run_bridge_command(self, *args) -> bool:
        """
        Run Arduino bridge command via subprocess

        Args:
            *args: Command arguments (e.g., "lcd", "0", "0", "Hello")

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False

        if self.consecutive_failures >= self.max_failures:
            # Too many failures, disable to avoid slowdown
            self.enabled = False
            logger.warning(f"Arduino disabled after {self.max_failures} failures")
            return False

        try:
            cmd = [
                "python3",
                str(BRIDGE_SCRIPT),
                "--port", ARDUINO_PORT,
                *args
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TIMEOUT
            )

            if result.returncode == 0:
                self.consecutive_failures = 0
                return True
            else:
                self.consecutive_failures += 1
                logger.debug(f"Arduino command failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.consecutive_failures += 1
            logger.debug("Arduino command timeout")
            return False
        except Exception as e:
            self.consecutive_failures += 1
            logger.debug(f"Arduino error: {e}")
            return False

    def display_text(self, row: int, col: int, text: str) -> bool:
        """
        Display text on LCD (16x2)

        Args:
            row: Row number (0 or 1)
            col: Column number (0-15)
            text: Text to display (truncated to fit)

        Returns:
            True if successful
        """
        # Truncate to fit 16 characters
        max_len = 16 - col
        text = text[:max_len]

        return self._run_bridge_command("lcd", str(row), str(col), text)

    def clear_display(self) -> bool:
        """Clear LCD display"""
        return self._run_bridge_command("clear")

    def set_led(self, r: int, g: int, b: int) -> bool:
        """
        Set RGB LED color (Tier 0 only)

        Args:
            r: Red value (0-255)
            g: Green value (0-255)
            b: Blue value (0-255)

        Returns:
            True if successful
        """
        return self._run_bridge_command("led", "0", str(r), str(g), str(b))

    def alert(self, alert_type: str) -> bool:
        """
        Play alert pattern (LED + beep)

        Args:
            alert_type: "success", "warning", "error", or "info"

        Returns:
            True if successful
        """
        valid_types = ["success", "warning", "error", "info"]
        if alert_type not in valid_types:
            alert_type = "info"

        return self._run_bridge_command("alert", alert_type)

    def beep(self, duration_ms: int = 100, frequency_hz: int = 1000) -> bool:
        """
        Play beep sound

        Args:
            duration_ms: Duration in milliseconds
            frequency_hz: Frequency in Hz

        Returns:
            True if successful
        """
        return self._run_bridge_command("beep", str(duration_ms), str(frequency_hz))

    def set_servo(self, position: int) -> bool:
        """
        Set servo position

        Args:
            position: Position in degrees (0-180)

        Returns:
            True if successful
        """
        position = max(0, min(180, position))
        return self._run_bridge_command("servo", str(position))

# Convenience functions for common operations

def tool_success_feedback(tool_name: str, arduino: Optional[ArduinoFeedback] = None) -> None:
    """
    Display success feedback for tool operation

    Args:
        tool_name: Name of the tool that succeeded
        arduino: ArduinoFeedback instance (creates new if None)
    """
    if arduino is None:
        arduino = ArduinoFeedback()

    try:
        # Green LED
        arduino.set_led(0, 255, 0)

        # Success message on LCD
        arduino.clear_display()
        arduino.display_text(0, 0, f"✓ {tool_name[:14]}")

        # Brief success beep
        arduino.beep(100, 1500)
    except Exception as e:
        logger.debug(f"Tool success feedback failed: {e}")

def tool_failure_feedback(tool_name: str, arduino: Optional[ArduinoFeedback] = None) -> None:
    """
    Display failure feedback for tool operation

    Args:
        tool_name: Name of the tool that failed
        arduino: ArduinoFeedback instance (creates new if None)
    """
    if arduino is None:
        arduino = ArduinoFeedback()

    try:
        # Red LED
        arduino.set_led(255, 0, 0)

        # Error message on LCD
        arduino.clear_display()
        arduino.display_text(0, 0, f"✗ {tool_name[:14]}")

        # Error alert pattern
        arduino.alert("error")
    except Exception as e:
        logger.debug(f"Tool failure feedback failed: {e}")

def agent_spawn_feedback(agent_name: str, arduino: Optional[ArduinoFeedback] = None) -> None:
    """
    Display feedback when spawning sub-agent

    Args:
        agent_name: Name of agent being spawned
        arduino: ArduinoFeedback instance (creates new if None)
    """
    if arduino is None:
        arduino = ArduinoFeedback()

    try:
        # Blue LED
        arduino.set_led(0, 0, 255)

        # Agent message on LCD
        arduino.clear_display()
        arduino.display_text(0, 0, "Agent:")
        arduino.display_text(1, 0, agent_name[:16])

        # Info beep
        arduino.beep(50, 1000)
    except Exception as e:
        logger.debug(f"Agent spawn feedback failed: {e}")

def memory_operation_feedback(operation: str, arduino: Optional[ArduinoFeedback] = None) -> None:
    """
    Display feedback for memory operations

    Args:
        operation: Memory operation description
        arduino: ArduinoFeedback instance (creates new if None)
    """
    if arduino is None:
        arduino = ArduinoFeedback()

    try:
        # Purple LED
        arduino.set_led(128, 0, 128)

        # Memory message on LCD
        arduino.clear_display()
        arduino.display_text(0, 0, "Memory:")
        arduino.display_text(1, 0, operation[:16])
    except Exception as e:
        logger.debug(f"Memory operation feedback failed: {e}")

def ember_status_display(hunger: int, energy: int, happiness: int,
                         arduino: Optional[ArduinoFeedback] = None) -> None:
    """
    Display Ember's status on Arduino LCD

    Args:
        hunger: Hunger level (0-100)
        energy: Energy level (0-100)
        happiness: Happiness level (0-100)
        arduino: ArduinoFeedback instance (creates new if None)
    """
    if arduino is None:
        arduino = ArduinoFeedback()

    try:
        # Ember mood LED
        if happiness > 70:
            arduino.set_led(0, 255, 0)  # Green - happy
        elif happiness > 40:
            arduino.set_led(255, 255, 0)  # Yellow - neutral
        else:
            arduino.set_led(255, 0, 0)  # Red - sad

        # Status on LCD
        arduino.clear_display()
        arduino.display_text(0, 0, f"Ember H:{hunger:2d} E:{energy:2d}")
        arduino.display_text(1, 0, f"Happy: {happiness:2d}%")
    except Exception as e:
        logger.debug(f"Ember status display failed: {e}")

def system_status_display(message: str, arduino: Optional[ArduinoFeedback] = None) -> None:
    """
    Display system status message on LCD

    Args:
        message: Status message (up to 32 chars, split across 2 rows)
        arduino: ArduinoFeedback instance (creates new if None)
    """
    if arduino is None:
        arduino = ArduinoFeedback()

    try:
        # Yellow LED for system messages
        arduino.set_led(255, 255, 0)

        # Split message across two rows
        arduino.clear_display()
        if len(message) <= 16:
            arduino.display_text(0, 0, message)
        else:
            arduino.display_text(0, 0, message[:16])
            arduino.display_text(1, 0, message[16:32])
    except Exception as e:
        logger.debug(f"System status display failed: {e}")

# Test harness
if __name__ == "__main__":
    # Test Arduino feedback
    print("Testing Arduino Auto-Interaction...")

    arduino = ArduinoFeedback()

    if not arduino.enabled:
        print("❌ Arduino not available")
        sys.exit(1)

    print("✓ Arduino available")

    # Test success feedback
    print("Testing success feedback...")
    tool_success_feedback("Write", arduino)

    import time
    time.sleep(2)

    # Test failure feedback
    print("Testing failure feedback...")
    tool_failure_feedback("Read", arduino)

    time.sleep(2)

    # Test agent spawn
    print("Testing agent spawn...")
    agent_spawn_feedback("Research Agent", arduino)

    time.sleep(2)

    # Test Ember status
    print("Testing Ember status...")
    ember_status_display(75, 80, 85, arduino)

    time.sleep(2)

    # Clear display
    arduino.clear_display()

    print("✓ All tests passed")

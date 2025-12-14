#!/usr/bin/env python3
"""
Arduino Approval Controller - Linux Edition
===========================================

Cluster-wide human-in-the-loop approval using Arduino hardware on Linux.

Supports:
- Linux (real hardware via /dev/ttyACM*)
- macOS (real hardware via /dev/tty.usbmodem*)
- Fallback simulation mode

Hardware Integration:
Uses existing ArduinoSurface bridge for protocol compatibility.
"""

import glob
import json
import logging
import platform
import threading
import time
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any

# Add arduino-surface bridge to path
sys.path.insert(0, '/mnt/agentic-system/arduino-surface/bridge')
from surface_bridge import ArduinoSurface

from approval_workflow import ApprovalWorkflow, ApprovalRequest, ApprovalChannel
from risk_assessment import RiskLevel

logger = logging.getLogger(__name__)

# Platform detection
IS_MACOS = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"


@dataclass
class ArduinoConfig:
    """Arduino hardware configuration."""
    port: Optional[str] = None
    baud_rate: int = 115200
    lcd_cols: int = 16
    lcd_rows: int = 2


class ArduinoApprovalControllerLinux:
    """
    Physical approval controller using Arduino hardware.

    Works on both Linux and macOS with real hardware.
    Falls back to simulation if hardware unavailable.
    """

    def __init__(
        self,
        workflow: ApprovalWorkflow,
        port: Optional[str] = None,
        config: Optional[ArduinoConfig] = None,
        simulation_mode: bool = False
    ):
        """
        Initialize Arduino approval controller.

        Args:
            workflow: Approval workflow to integrate with
            port: Serial port (auto-detect if None)
            config: Hardware configuration
            simulation_mode: Force simulation (no hardware)
        """
        self.workflow = workflow
        self.config = config or ArduinoConfig(port=port)

        # Determine mode - try hardware first unless forced simulation
        self.simulation_mode = simulation_mode
        self.arduino: Optional[ArduinoSurface] = None

        if not self.simulation_mode:
            # Try to connect to real hardware
            port = self._auto_detect_port()
            if port:
                try:
                    self.arduino = ArduinoSurface(port)
                    if self.arduino.connect():
                        logger.info(f"✓ Connected to Arduino hardware on {port}")
                    else:
                        logger.warning("Arduino connection failed - falling back to simulation")
                        self.simulation_mode = True
                        self.arduino = None
                except Exception as e:
                    logger.error(f"Arduino initialization error: {e}")
                    self.simulation_mode = True
                    self.arduino = None
            else:
                logger.warning("No Arduino port found - using simulation mode")
                self.simulation_mode = True

        if self.simulation_mode:
            logger.info("Arduino controller in SIMULATION MODE")

        # State
        self.current_request: Optional[ApprovalRequest] = None
        self.request_lock = threading.Lock()

        # Monitoring thread
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None

        # Register with workflow
        workflow.register_channel_callback(
            ApprovalChannel.ARDUINO,
            self.on_approval_request
        )

        logger.info(f"Arduino approval controller initialized (simulation={self.simulation_mode})")

    def _auto_detect_port(self) -> Optional[str]:
        """Auto-detect Arduino serial port for current platform."""
        # Explicit port provided
        if self.config.port:
            return self.config.port

        # Linux: /dev/ttyACM* or /dev/ttyUSB*
        if IS_LINUX:
            for pattern in ["/dev/ttyACM*", "/dev/ttyUSB*"]:
                ports = glob.glob(pattern)
                if ports:
                    logger.info(f"Auto-detected Arduino port: {ports[0]} (Linux)")
                    return ports[0]

        # macOS: /dev/tty.usbmodem*
        if IS_MACOS:
            ports = glob.glob("/dev/tty.usbmodem*")
            if ports:
                logger.info(f"Auto-detected Arduino port: {ports[0]} (macOS)")
                return ports[0]

        logger.warning(f"No Arduino ports found (tried Linux: /dev/ttyACM*, /dev/ttyUSB*; macOS: /dev/tty.usbmodem*)")
        return None

    def start(self):
        """Start monitoring Arduino for button presses."""
        if self.running:
            return

        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self.monitor_thread.start()

        logger.info("Arduino monitoring started")

    def stop(self):
        """Stop monitoring."""
        self.running = False

        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        if self.arduino:
            self.arduino.disconnect()

        logger.info("Arduino monitoring stopped")

    def on_approval_request(self, request: ApprovalRequest):
        """
        Handle new approval request.

        Updates display, sets LED color, plays alert sound.
        """
        with self.request_lock:
            self.current_request = request

        logger.info(f"Arduino: Displaying approval request {request.request_id}")

        # Update display
        self._update_display(request)

        # Set LED color based on risk
        self._set_risk_indicator(request.risk_assessment.risk_level)

        # Play alert sound
        self._play_alert(request.risk_assessment.risk_level)

    def _monitor_loop(self):
        """Monitor Arduino for button presses."""
        # TODO: Implement button monitoring via surface_bridge event system
        # For now, this is a placeholder
        while self.running:
            time.sleep(0.1)

    def _update_display(self, request: ApprovalRequest):
        """Update LCD display with approval request."""
        # Format display text (16x2 LCD)
        risk_str = request.risk_assessment.risk_level.value.upper()
        task_str = self._truncate(request.task_description, 16)

        line1 = "APPROVAL REQ"
        line2 = f"{risk_str[:4]}: {task_str[:10]}"

        if self.simulation_mode:
            logger.info("Arduino Display:")
            logger.info(f"  Row 1: {line1}")
            logger.info(f"  Row 2: {line2}")
        else:
            if self.arduino:
                self.arduino.lcd_clear()
                self.arduino.lcd_write(0, 0, line1)
                self.arduino.lcd_write(1, 0, line2)

    def _set_risk_indicator(self, risk_level: RiskLevel):
        """Set RGB LED color based on risk level."""
        # Color mapping (tier 0 LED only)
        colors = {
            RiskLevel.LOW: (0, 255, 0),      # Green
            RiskLevel.MEDIUM: (255, 255, 0), # Yellow
            RiskLevel.HIGH: (255, 128, 0),   # Orange
            RiskLevel.CRITICAL: (255, 0, 0)  # Red
        }

        r, g, b = colors.get(risk_level, (255, 255, 255))

        if self.simulation_mode:
            logger.info(f"LED Color: RGB({r}, {g}, {b}) - {risk_level.value}")
        else:
            if self.arduino:
                self.arduino.set_led(0, r, g, b)  # Tier 0 LED

    def _play_alert(self, risk_level: RiskLevel):
        """Play buzzer alert based on risk level."""
        # Alert patterns (frequency, duration_ms)
        patterns = {
            RiskLevel.LOW: (1000, 100),       # Quiet beep
            RiskLevel.MEDIUM: (1500, 200),    # Moderate beep
            RiskLevel.HIGH: (2000, 300),      # Loud beep
            RiskLevel.CRITICAL: (2500, 500)   # Urgent beep
        }

        freq, duration = patterns.get(risk_level, (1000, 100))

        if self.simulation_mode:
            logger.info(f"Buzzer: {freq}Hz for {duration}ms")
        else:
            if self.arduino:
                self.arduino.beep(duration, freq)

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        """Truncate text to fit display."""
        if len(text) <= max_len:
            return text
        return text[:max_len-3] + "..."


# ============================================================================
# Example Usage
# ============================================================================

def example_arduino_controller():
    """Example: Arduino approval controller on Linux."""
    from risk_assessment import RiskScoringEngine

    print("\n" + "=" * 70)
    print("Arduino Approval Controller - Linux Edition")
    print("=" * 70)

    # Initialize workflow
    workflow = ApprovalWorkflow(default_timeout=60)

    # Initialize Arduino controller (auto-detects hardware)
    controller = ArduinoApprovalControllerLinux(workflow=workflow)

    # Start monitoring
    controller.start()

    # Create risk engine
    engine = RiskScoringEngine()

    # High risk task that triggers Arduino display
    print("\n1. Triggering Arduino approval request:")
    task = {
        "task_id": "task-arduino-001",
        "type": "code_execution",
        "target_node": "*",
        "payload": {
            "code": "import shutil; shutil.rmtree('/tmp/data')",
            "code_language": "python"
        }
    }

    assessment = engine.assess_task_risk(task)
    request_id = workflow.request_approval(
        task,
        assessment,
        requester="example"
    )

    print(f"\n2. Check Arduino display - should show approval request")
    print(f"   Request ID: {request_id}")
    print(f"   Risk: {assessment.risk_level.value}")

    time.sleep(3)

    # Stop controller
    controller.stop()

    print("\n" + "=" * 70)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    example_arduino_controller()
    print("\nArduino approval controller (Linux) ready ✓")

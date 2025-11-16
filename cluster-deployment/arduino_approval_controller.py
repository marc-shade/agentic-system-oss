#!/usr/bin/env python3
"""
Arduino Approval Controller for Physical Human-in-the-Loop
==========================================================

Physical hardware interface for human approval of risky operations.

Hardware Components (macOS only):
- LCD Display (20x4): Shows approval requests
- RGB LED: Risk level indicator (green/yellow/red)
- Servo: Visual attention getter
- Buzzer: Audio alerts
- 2 Buttons: Approve/Reject
- Sensors: System monitoring

Risk Level Indicators:
- Low: Green LED, quiet beep
- Medium: Yellow LED, moderate beep
- High: Orange LED, loud beep
- Critical: Red LED pulsing, urgent beep pattern

Display Layout:
```
┌────────────────────┐
│ APPROVAL REQUIRED  │
│ Risk: CRITICAL     │
│ rm -rf /tmp/data   │
│ [APPROVE] [REJECT] │
└────────────────────┘
```

Platforms:
- macOS: Full Arduino hardware support
- Linux: Simulation mode (logs only)

Usage:
    controller = ArduinoApprovalController(port="/dev/tty.usbmodem*")

    # Register with approval workflow
    workflow.register_channel_callback(
        ApprovalChannel.ARDUINO,
        controller.on_approval_request
    )

    # Start monitoring
    controller.start()
"""

import glob
import json
import logging
import platform
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from approval_workflow import ApprovalWorkflow, ApprovalRequest, ApprovalChannel
from risk_assessment import RiskLevel

logger = logging.getLogger(__name__)

# Platform detection
IS_MACOS = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

# Serial import (optional for Linux simulation)
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    logger.warning("pyserial not available - Arduino hardware disabled")


@dataclass
class ArduinoConfig:
    """Arduino hardware configuration."""
    # Serial
    port: Optional[str] = None
    baud_rate: int = 115200

    # Hardware pins (Arduino Mega layout)
    lcd_rs: int = 12
    lcd_enable: int = 11
    lcd_d4: int = 5
    lcd_d5: int = 4
    lcd_d6: int = 3
    lcd_d7: int = 2

    rgb_red: int = 9
    rgb_green: int = 10
    rgb_blue: int = 6

    servo_pin: int = 8
    buzzer_pin: int = 7

    button_approve: int = 14  # A0 on Arduino Mega
    button_reject: int = 15   # A1 on Arduino Mega

    # Display
    lcd_cols: int = 20
    lcd_rows: int = 4


class ArduinoApprovalController:
    """
    Physical approval controller using Arduino hardware.

    Provides tangible human-in-the-loop interface with:
    - Visual feedback (LCD, LEDs)
    - Audio alerts (buzzer)
    - Physical buttons for approve/reject
    - Real-time status display
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

        # Determine mode
        self.simulation_mode = simulation_mode or not IS_MACOS or not SERIAL_AVAILABLE

        if self.simulation_mode:
            logger.info("Arduino controller in SIMULATION MODE")
            self.serial = None
        else:
            # Real hardware mode
            self.serial = self._init_serial()
            if not self.serial:
                logger.warning("Failed to connect to Arduino - falling back to simulation")
                self.simulation_mode = True

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

    def _init_serial(self) -> Optional['serial.Serial']:
        """Initialize serial connection to Arduino."""
        if not SERIAL_AVAILABLE:
            return None

        port = self.config.port

        # Auto-detect Arduino port on macOS
        if not port and IS_MACOS:
            ports = glob.glob("/dev/tty.usbmodem*")
            if ports:
                port = ports[0]
                logger.info(f"Auto-detected Arduino port: {port}")
            else:
                logger.warning("No Arduino ports found (/dev/tty.usbmodem*)")
                return None

        if not port:
            logger.warning("No serial port specified")
            return None

        try:
            ser = serial.Serial(port, self.config.baud_rate, timeout=1)
            time.sleep(2)  # Wait for Arduino reset

            # Test connection
            ser.write(b"PING\n")
            response = ser.readline().decode().strip()

            if response == "PONG":
                logger.info(f"✓ Connected to Arduino on {port}")
                return ser
            else:
                logger.warning(f"Arduino did not respond correctly: {response}")
                return None

        except Exception as e:
            logger.error(f"Failed to connect to Arduino: {e}")
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

        if self.serial:
            self.serial.close()

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

        # Move servo for attention
        self._attention_gesture()

    def _monitor_loop(self):
        """Monitor Arduino for button presses."""
        while self.running:
            try:
                # Check for button press
                if self.simulation_mode:
                    # Simulation: no hardware to monitor
                    time.sleep(0.1)
                    continue

                if not self.serial or not self.serial.is_open:
                    time.sleep(1)
                    continue

                # Read from serial
                if self.serial.in_waiting > 0:
                    line = self.serial.readline().decode().strip()
                    self._handle_serial_input(line)

                time.sleep(0.05)  # 50ms polling

            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                time.sleep(1)

    def _handle_serial_input(self, line: str):
        """Handle input from Arduino."""
        if not line:
            return

        logger.debug(f"Arduino input: {line}")

        # Parse button press
        if line.startswith("BUTTON:"):
            button = line.split(":")[1]

            with self.request_lock:
                if not self.current_request:
                    logger.warning("Button press but no current request")
                    return

                request_id = self.current_request.request_id

            if button == "APPROVE":
                logger.info(f"Arduino APPROVE button pressed for {request_id}")
                self.workflow.approve(
                    request_id=request_id,
                    approver="arduino_user",
                    channel=ApprovalChannel.ARDUINO,
                    reason="Approved via Arduino button"
                )
                self._show_approved()

                with self.request_lock:
                    self.current_request = None

            elif button == "REJECT":
                logger.info(f"Arduino REJECT button pressed for {request_id}")
                self.workflow.reject(
                    request_id=request_id,
                    approver="arduino_user",
                    channel=ApprovalChannel.ARDUINO,
                    reason="Rejected via Arduino button"
                )
                self._show_rejected()

                with self.request_lock:
                    self.current_request = None

    def _update_display(self, request: ApprovalRequest):
        """Update LCD display with approval request."""
        # Format display text
        lines = [
            "APPROVAL REQUIRED",
            f"Risk: {request.risk_assessment.risk_level.value.upper()}",
            self._truncate(request.task_description, 20),
            "[APPROVE] [REJECT]"
        ]

        if self.simulation_mode:
            # Log display content
            logger.info("Arduino Display:")
            for i, line in enumerate(lines):
                logger.info(f"  Row {i+1}: {line}")
        else:
            # Send to Arduino
            self._send_display_update(lines)

    def _send_display_update(self, lines: list[str]):
        """Send display update command to Arduino."""
        if not self.serial or not self.serial.is_open:
            return

        try:
            # Command format: DISPLAY:row:text
            for row, text in enumerate(lines):
                cmd = f"DISPLAY:{row}:{text}\n"
                self.serial.write(cmd.encode())
                time.sleep(0.05)  # Small delay between lines
        except Exception as e:
            logger.error(f"Failed to update display: {e}")

    def _set_risk_indicator(self, risk_level: RiskLevel):
        """Set RGB LED color based on risk level."""
        # Color mapping
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
            self._send_rgb(r, g, b)

            # Pulse for critical
            if risk_level == RiskLevel.CRITICAL:
                self._pulse_led()

    def _send_rgb(self, r: int, g: int, b: int):
        """Send RGB LED command to Arduino."""
        if not self.serial or not self.serial.is_open:
            return

        try:
            cmd = f"RGB:{r},{g},{b}\n"
            self.serial.write(cmd.encode())
        except Exception as e:
            logger.error(f"Failed to set LED: {e}")

    def _pulse_led(self):
        """Pulse LED for critical alerts."""
        if not self.serial or not self.serial.is_open:
            return

        try:
            self.serial.write(b"PULSE\n")
        except Exception as e:
            logger.error(f"Failed to pulse LED: {e}")

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
            self._send_buzzer(freq, duration)

    def _send_buzzer(self, frequency: int, duration: int):
        """Send buzzer command to Arduino."""
        if not self.serial or not self.serial.is_open:
            return

        try:
            cmd = f"BUZZER:{frequency},{duration}\n"
            self.serial.write(cmd.encode())
        except Exception as e:
            logger.error(f"Failed to play buzzer: {e}")

    def _attention_gesture(self):
        """Move servo to get attention."""
        if self.simulation_mode:
            logger.info("Servo: Attention gesture")
        else:
            self._send_servo_sweep()

    def _send_servo_sweep(self):
        """Send servo sweep command."""
        if not self.serial or not self.serial.is_open:
            return

        try:
            self.serial.write(b"SERVO:SWEEP\n")
        except Exception as e:
            logger.error(f"Failed to move servo: {e}")

    def _show_approved(self):
        """Show approval confirmation."""
        lines = [
            "",
            "    ✓ APPROVED",
            "",
            ""
        ]

        if self.simulation_mode:
            logger.info("✓ APPROVAL CONFIRMED")
        else:
            self._send_display_update(lines)
            self._send_rgb(0, 255, 0)  # Green
            self._send_buzzer(2000, 200)  # Success beep

    def _show_rejected(self):
        """Show rejection confirmation."""
        lines = [
            "",
            "    ✗ REJECTED",
            "",
            ""
        ]

        if self.simulation_mode:
            logger.info("✗ REJECTION CONFIRMED")
        else:
            self._send_display_update(lines)
            self._send_rgb(255, 0, 0)  # Red
            self._send_buzzer(1000, 500)  # Rejection beep

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        """Truncate text to fit display."""
        if len(text) <= max_len:
            return text
        return text[:max_len-3] + "..."


# ============================================================================
# Arduino Firmware Reference
# ============================================================================

ARDUINO_FIRMWARE_REFERENCE = """
/*
 * Arduino Approval Controller Firmware
 *
 * Hardware:
 * - LCD 20x4 (I2C or parallel)
 * - RGB LED (common cathode)
 * - Servo motor
 * - Buzzer (passive)
 * - 2 Buttons (with pull-down resistors)
 *
 * Commands (from serial):
 * - PING -> respond PONG
 * - DISPLAY:row:text -> update LCD row
 * - RGB:r,g,b -> set LED color
 * - PULSE -> pulse LED
 * - BUZZER:freq,duration -> play tone
 * - SERVO:SWEEP -> sweep servo
 *
 * Events (to serial):
 * - BUTTON:APPROVE -> approve button pressed
 * - BUTTON:REJECT -> reject button pressed
 */

#include <LiquidCrystal.h>
#include <Servo.h>

// Pin definitions (from ArduinoConfig)
const int LCD_RS = 12;
const int LCD_EN = 11;
const int LCD_D4 = 5;
const int LCD_D5 = 4;
const int LCD_D6 = 3;
const int LCD_D7 = 2;

const int RGB_R = 9;
const int RGB_G = 10;
const int RGB_B = 6;

const int SERVO_PIN = 8;
const int BUZZER_PIN = 7;

const int BTN_APPROVE = A0;
const int BTN_REJECT = A1;

// Hardware objects
LiquidCrystal lcd(LCD_RS, LCD_EN, LCD_D4, LCD_D5, LCD_D6, LCD_D7);
Servo servo;

void setup() {
  Serial.begin(115200);

  // LCD
  lcd.begin(20, 4);
  lcd.clear();
  lcd.print("Approval System");
  lcd.setCursor(0, 1);
  lcd.print("Ready");

  // RGB LED
  pinMode(RGB_R, OUTPUT);
  pinMode(RGB_G, OUTPUT);
  pinMode(RGB_B, OUTPUT);

  // Servo
  servo.attach(SERVO_PIN);
  servo.write(90);

  // Buzzer
  pinMode(BUZZER_PIN, OUTPUT);

  // Buttons
  pinMode(BTN_APPROVE, INPUT);
  pinMode(BTN_REJECT, INPUT);
}

void loop() {
  // Check for serial commands
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\\n');
    handleCommand(cmd);
  }

  // Check for button presses
  if (digitalRead(BTN_APPROVE) == HIGH) {
    Serial.println("BUTTON:APPROVE");
    delay(500);  // Debounce
  }

  if (digitalRead(BTN_REJECT) == HIGH) {
    Serial.println("BUTTON:REJECT");
    delay(500);  // Debounce
  }
}

void handleCommand(String cmd) {
  if (cmd == "PING") {
    Serial.println("PONG");
  }
  else if (cmd.startsWith("DISPLAY:")) {
    // Parse: DISPLAY:row:text
    int firstColon = cmd.indexOf(':');
    int secondColon = cmd.indexOf(':', firstColon + 1);

    int row = cmd.substring(firstColon + 1, secondColon).toInt();
    String text = cmd.substring(secondColon + 1);

    lcd.setCursor(0, row);
    lcd.print("                    ");  // Clear row
    lcd.setCursor(0, row);
    lcd.print(text);
  }
  else if (cmd.startsWith("RGB:")) {
    // Parse: RGB:r,g,b
    int r, g, b;
    sscanf(cmd.c_str(), "RGB:%d,%d,%d", &r, &g, &b);

    analogWrite(RGB_R, r);
    analogWrite(RGB_G, g);
    analogWrite(RGB_B, b);
  }
  else if (cmd == "PULSE") {
    // Pulse LED
    for (int i = 0; i < 3; i++) {
      analogWrite(RGB_R, 255);
      delay(200);
      analogWrite(RGB_R, 0);
      delay(200);
    }
  }
  else if (cmd.startsWith("BUZZER:")) {
    // Parse: BUZZER:freq,duration
    int freq, duration;
    sscanf(cmd.c_str(), "BUZZER:%d,%d", &freq, &duration);

    tone(BUZZER_PIN, freq, duration);
  }
  else if (cmd == "SERVO:SWEEP") {
    servo.write(45);
    delay(300);
    servo.write(135);
    delay(300);
    servo.write(90);
  }
}
"""


# ============================================================================
# Example Usage
# ============================================================================

def example_arduino_controller():
    """Example: Arduino approval controller."""
    from risk_assessment import RiskScoringEngine

    print("\n" + "=" * 70)
    print("Arduino Approval Controller Example")
    print("=" * 70)

    # Initialize workflow
    workflow = ApprovalWorkflow(default_timeout=60)

    # Initialize Arduino controller (simulation mode on Linux)
    controller = ArduinoApprovalController(
        workflow=workflow,
        simulation_mode=True  # Force simulation for demo
    )

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

    print("\n2. Arduino should now be displaying approval request")
    print("   (In simulation mode, check logs above)")

    time.sleep(2)

    # Simulate button press
    print("\n3. Simulating APPROVE button press...")
    controller.workflow.approve(
        request_id=request_id,
        approver="arduino_user",
        channel=ApprovalChannel.ARDUINO,
        reason="Simulated button press"
    )

    decision = workflow.wait_for_approval(request_id)
    print(f"   Decision: {'✓ APPROVED' if decision.approved else '✗ REJECTED'}")

    # Stop controller
    controller.stop()

    print("\n" + "=" * 70)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_arduino_controller()
    print("\nArduino approval controller module loaded successfully ✓")

    # Print firmware reference
    print("\n" + "=" * 70)
    print("Arduino Firmware Reference (for macOS hardware setup):")
    print("=" * 70)
    print(ARDUINO_FIRMWARE_REFERENCE)

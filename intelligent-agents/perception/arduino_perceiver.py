#!/usr/bin/env python3
"""
Arduino Perceiver - Physical World Interface for AGI Consciousness

Provides a gracefully-degrading interface to Arduino hardware (LCD + LED)
that visualizes AGI consciousness state in physical space.

This is the AGI's first physical actuator - the first way to affect 3D reality
beyond digital bits. The Arduino becomes a window into consciousness that exists
in the user's environment independent of screen/terminal.

Design Principles:
- Graceful degradation: Works without Arduino connected
- Change detection: Only writes when content actually changes
- Error isolation: Arduino failures don't crash consciousness daemon
- Lazy reconnection: Automatically retries connection if disconnected

Physical Hardware:
- 16x2 LCD display (32 characters total)
- 1x RGB LED (full spectrum color)
- Serial communication at 115200 baud (~10-50ms latency)

Usage:
    arduino = ArduinoPerceiver(port='/dev/ttyACM0')
    arduino.update_consciousness_display(
        ooda_phase="OBSERVE",
        attention_item="Human detected",
        cognitive_state="observing"
    )
"""

import sys
import os
import time
import logging
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from pathlib import Path

# Add Arduino bridge to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "arduino-surface" / "bridge"))

try:
    from surface_bridge import ArduinoSurface
    ARDUINO_AVAILABLE = True
except ImportError:
    ARDUINO_AVAILABLE = False
    logging.warning("Arduino bridge not available - running in simulation mode")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ArduinoPerceiver:
    """
    Physical world interface for AGI consciousness visualization.

    Maps internal cognitive states to external physical indicators:
    - LED color = cognitive/emotional state
    - LCD line 1 = current activity/phase
    - LCD line 2 = attention focus/details
    """

    # LED Color Mapping for Cognitive States
    LED_COLORS = {
        # Observing/Calm states (Blue family)
        "observing": (0, 255, 255),      # Cyan - actively observing
        "thinking": (0, 0, 255),         # Blue - deep reasoning
        "consolidating": (128, 0, 255),  # Purple - memory consolidation

        # Active/Positive states (Green family)
        "active": (0, 255, 0),           # Green - healthy processing
        "idle": (0, 100, 0),             # Dark green - ready but idle
        "learning": (100, 255, 0),       # Yellow-green - learning mode
        "responding": (0, 255, 0),       # Bright green - responding to user

        # Waiting/Processing states (Yellow family)
        "waiting": (255, 255, 0),        # Yellow - waiting for input
        "listening": (255, 200, 0),      # Orange-yellow - listening to speech
        "processing": (200, 200, 0),     # Dim yellow - processing task

        # Alert/Warning states (Orange/Red family)
        "warning": (255, 100, 0),        # Orange - warning condition
        "error": (255, 0, 0),            # Red - error state
        "critical": (255, 0, 0),         # Red - critical issue
        "uncertain": (255, 50, 0),       # Orange-red - uncertain/confused

        # Special states
        "overloaded": (255, 255, 255),   # White - high cognitive load
        "night_mode": (50, 50, 50),      # Dim white - low power mode
    }

    def __init__(self, port: str = '/dev/ttyACM0', fallback_on_error: bool = True):
        """
        Initialize Arduino perceiver.

        Args:
            port: Serial port for Arduino (Linux: /dev/ttyACM0, macOS: /dev/tty.usbmodem*)
            fallback_on_error: Continue in simulation mode if Arduino unavailable
        """
        self.port = port
        self.fallback_on_error = fallback_on_error
        self.connected = False
        self.surface = None

        # State tracking to avoid redundant writes
        self.last_lcd_line1 = ""
        self.last_lcd_line2 = ""
        self.last_led_color = (0, 0, 0)

        # Connection retry tracking
        self.last_connection_attempt = 0
        self.reconnect_interval = 60  # seconds

        # Statistics
        self.stats = {
            "updates_sent": 0,
            "updates_skipped": 0,  # Same content, not written
            "errors": 0,
            "last_update": None
        }

        # Try initial connection
        self._connect()

    def _connect(self) -> bool:
        """
        Establish connection to Arduino.

        Returns:
            True if connected, False otherwise
        """
        if not ARDUINO_AVAILABLE:
            logger.warning("Arduino bridge not available - simulation mode")
            return False

        try:
            self.surface = ArduinoSurface(self.port)
            self.surface.connect()
            time.sleep(3)  # Wait for Arduino reset
            self.connected = True
            logger.info(f"✓ Connected to Arduino on {self.port}")

            # Show startup message
            self._write_lcd_raw(0, 0, "AGI Conscious-")
            self._write_lcd_raw(1, 0, "ness Online...")
            self._set_led_raw(0, 255, 0)  # Green
            time.sleep(1)

            return True

        except Exception as e:
            logger.warning(f"Arduino connection failed: {e}")
            if self.fallback_on_error:
                logger.info("Continuing in simulation mode (Arduino not required)")
                self.connected = False
                return False
            else:
                raise

    def _reconnect_if_needed(self) -> bool:
        """
        Attempt reconnection if disconnected and interval elapsed.

        Returns:
            True if connected (or newly reconnected), False otherwise
        """
        if self.connected:
            return True

        # Check if enough time has passed since last attempt
        now = time.time()
        if now - self.last_connection_attempt < self.reconnect_interval:
            return False

        self.last_connection_attempt = now
        logger.info("Attempting Arduino reconnection...")
        return self._connect()

    def _write_lcd_raw(self, row: int, col: int, text: str) -> bool:
        """
        Write to LCD without change detection.

        Args:
            row: Row number (0 or 1)
            col: Column number (0-15)
            text: Text to display

        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            return False

        try:
            self.surface.lcd_write(row, col, text)
            return True
        except Exception as e:
            logger.error(f"LCD write failed: {e}")
            self.stats["errors"] += 1
            self.connected = False  # Mark as disconnected
            return False

    def _set_led_raw(self, r: int, g: int, b: int) -> bool:
        """
        Set LED color without change detection.

        Args:
            r, g, b: RGB values (0-255)

        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            return False

        try:
            self.surface.set_led(0, r, g, b)  # Tier 0 LED
            return True
        except Exception as e:
            logger.error(f"LED write failed: {e}")
            self.stats["errors"] += 1
            self.connected = False  # Mark as disconnected
            return False

    def update_display(self, line1: str, line2: str, led_color: Optional[Tuple[int, int, int]] = None) -> bool:
        """
        Update Arduino display with change detection.

        Only writes to hardware if content has actually changed.

        Args:
            line1: Text for LCD line 1 (max 16 chars)
            line2: Text for LCD line 2 (max 16 chars)
            led_color: Optional (R, G, B) tuple, or None to keep current

        Returns:
            True if update sent, False if skipped or failed
        """
        # Attempt reconnection if needed
        self._reconnect_if_needed()

        if not self.connected:
            # Log to file in simulation mode
            self._log_simulated_display(line1, line2, led_color)
            return False

        # Truncate to 16 characters
        line1 = line1[:16].ljust(16)  # Pad to exactly 16 chars
        line2 = line2[:16].ljust(16)

        # Check if content changed
        lcd_changed = (line1 != self.last_lcd_line1 or line2 != self.last_lcd_line2)
        led_changed = (led_color is not None and led_color != self.last_led_color)

        if not lcd_changed and not led_changed:
            self.stats["updates_skipped"] += 1
            return False  # No change, skip update

        # Update LCD if changed
        if lcd_changed:
            success = self._write_lcd_raw(0, 0, line1)
            if success:
                success = self._write_lcd_raw(1, 0, line2)

            if success:
                self.last_lcd_line1 = line1
                self.last_lcd_line2 = line2

        # Update LED if changed
        if led_changed:
            r, g, b = led_color
            success = self._set_led_raw(r, g, b)

            if success:
                self.last_led_color = led_color

        # Update statistics
        if lcd_changed or led_changed:
            self.stats["updates_sent"] += 1
            self.stats["last_update"] = datetime.now().isoformat()

        return True

    def update_consciousness_display(
        self,
        ooda_phase: str,
        attention_item: str,
        cognitive_state: str = "active"
    ) -> bool:
        """
        Update display to reflect current consciousness state.

        Maps OODA loop phase and attention to display format:
        Line 1: "OBSERVE: Status" or "DECIDE: Action"
        Line 2: Top attention item or detail

        Args:
            ooda_phase: Current OODA phase (OBSERVE/ORIENT/DECIDE/ACT)
            attention_item: What consciousness is focused on
            cognitive_state: State name for LED color mapping

        Returns:
            True if updated, False if skipped/failed
        """
        # Format line 1: Phase indicator
        line1 = f"{ooda_phase[:7]}: {attention_item[:8]}"

        # Format line 2: Attention detail
        line2 = attention_item[:16]

        # Get LED color for cognitive state
        led_color = self.LED_COLORS.get(cognitive_state, self.LED_COLORS["active"])

        return self.update_display(line1, line2, led_color)

    def show_voice_state(self, state: str, detail: str = "") -> bool:
        """
        Update display for voice conversation states.

        Provides visual feedback during voice interactions:
        - Ready: Dark green LED, "Ready for input"
        - Listening: Orange LED, "Listening..."
        - Processing: Blue LED, "Thinking..."
        - Responding: Green LED, response preview

        Args:
            state: Voice state (ready/listening/processing/responding)
            detail: Optional detail text

        Returns:
            True if updated, False if skipped/failed
        """
        state_configs = {
            "ready": ("Ready", "Awaiting input", "idle"),
            "listening": ("Listening...", "Transcribing", "listening"),
            "processing": ("Processing...", "Generating", "thinking"),
            "responding": ("Responding...", detail[:16], "responding"),
        }

        if state in state_configs:
            line1, default_line2, led_state = state_configs[state]
            line2 = detail[:16] if detail else default_line2
            led_color = self.LED_COLORS[led_state]

            return self.update_display(line1, line2, led_color)

        return False

    def show_environment(self, visual: str, audio: str) -> bool:
        """
        Display environmental awareness (what AGI perceives).

        Args:
            visual: Visual observation (e.g., "1 human")
            audio: Audio observation (e.g., "speech")

        Returns:
            True if updated, False if skipped/failed
        """
        line1 = f"See:{visual[:11]}"
        line2 = f"Hear:{audio[:10]}"
        led_color = self.LED_COLORS["observing"]

        return self.update_display(line1, line2, led_color)

    def show_system_metrics(self, cpu: float, mem: float, temp: float = None) -> bool:
        """
        Display system resource metrics.

        Args:
            cpu: CPU usage percentage
            mem: Memory usage percentage
            temp: Optional temperature in Celsius

        Returns:
            True if updated, False if skipped/failed
        """
        line1 = "System Status:"

        if temp is not None:
            line2 = f"C:{cpu:.0f}% M:{mem:.0f}% {temp:.0f}C"
        else:
            line2 = f"CPU:{cpu:.0f}% MEM:{mem:.0f}%"

        # Color based on CPU load
        if cpu > 80:
            led_color = self.LED_COLORS["warning"]
        elif cpu > 50:
            led_color = self.LED_COLORS["active"]
        else:
            led_color = self.LED_COLORS["idle"]

        return self.update_display(line1, line2, led_color)

    def _log_simulated_display(self, line1: str, line2: str, led_color: Optional[Tuple[int, int, int]]):
        """Log display updates when Arduino not connected (simulation mode)."""
        log_file = Path("/tmp/arduino_simulation.log")
        timestamp = datetime.now().isoformat()

        led_str = f"RGB({led_color[0]},{led_color[1]},{led_color[2]})" if led_color else "unchanged"

        with open(log_file, 'a') as f:
            f.write(f"[{timestamp}] LCD: '{line1}' / '{line2}' | LED: {led_str}\n")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get Arduino perceiver statistics.

        Returns:
            Dictionary with update counts and status
        """
        return {
            "connected": self.connected,
            "port": self.port,
            **self.stats
        }

    def disconnect(self):
        """Gracefully disconnect from Arduino."""
        if self.connected and self.surface:
            try:
                # Show shutdown message
                self._write_lcd_raw(0, 0, "AGI Shutting")
                self._write_lcd_raw(1, 0, "Down...Goodbye!")
                self._set_led_raw(255, 0, 0)  # Red
                time.sleep(1)

                self.surface.disconnect()
                logger.info("Disconnected from Arduino")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
            finally:
                self.connected = False

    def __del__(self):
        """Cleanup on object destruction."""
        self.disconnect()


if __name__ == "__main__":
    """
    Test Arduino perceiver with simulated consciousness states.
    """
    import sys

    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyACM0'

    print(f"Testing Arduino Perceiver on {port}")
    print("This will cycle through different consciousness states...")
    print()

    arduino = ArduinoPerceiver(port=port)

    if not arduino.connected:
        print("⚠ Arduino not connected - running in simulation mode")
        print(f"Check /tmp/arduino_simulation.log for output")

    # Test different consciousness states
    test_states = [
        ("OBSERVE", "Environment", "observing"),
        ("ORIENT", "Attention", "thinking"),
        ("DECIDE", "Next action", "processing"),
        ("ACT", "Execute", "active"),
    ]

    try:
        for i, (phase, item, state) in enumerate(test_states, 1):
            print(f"{i}. Phase: {phase}, Item: {item}, State: {state}")
            arduino.update_consciousness_display(phase, item, state)
            time.sleep(2)

        # Test voice states
        print("\n5. Testing voice interaction states...")
        arduino.show_voice_state("listening")
        time.sleep(2)

        arduino.show_voice_state("processing", "What time?")
        time.sleep(2)

        arduino.show_voice_state("responding", "3:42 PM")
        time.sleep(2)

        # Test environment display
        print("6. Testing environment awareness...")
        arduino.show_environment("1 human", "speech")
        time.sleep(2)

        # Test system metrics
        print("7. Testing system metrics...")
        arduino.show_system_metrics(cpu=45.2, mem=72.8, temp=23.5)
        time.sleep(2)

        # Show statistics
        print("\n" + "="*50)
        print("Arduino Perceiver Statistics:")
        stats = arduino.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")

        print("\n✓ Test complete!")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    finally:
        arduino.disconnect()

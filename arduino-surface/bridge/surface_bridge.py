#!/usr/bin/env python3
"""
Arduino Surface Bridge
Serial communication bridge for Arduino physical control surface
"""

import serial
import time
import json
import sys
import threading
from typing import Optional, Dict, Callable


class ArduinoSurface:
    """Python interface to Arduino physical control surface"""

    def __init__(self, port: str, baud: int = 115200):
        self.port = port
        self.baud = baud
        self.serial = None
        self.event_handlers = {}
        self.event_thread = None
        self.listening = False

    def connect(self) -> bool:
        """
        Establish serial connection to Arduino

        Returns:
            True if connected successfully
        """
        try:
            self.serial = serial.Serial(self.port, self.baud, timeout=2)
            time.sleep(3)  # Wait for Arduino reset and startup sequence

            # Read and discard startup message
            time.sleep(0.5)  # Give more time for ready message
            while self.serial.in_waiting:
                try:
                    line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        print(f"Arduino: {line}")
                except UnicodeDecodeError:
                    # Skip malformed bytes
                    pass

            # Send ping to verify connection
            response = self._send_command("PING")
            if response and response.get("status") == "ok":
                print(f"✓ Connected to Arduino on {self.port}")
                return True

            print("✗ Arduino not responding to ping")
            return False

        except serial.SerialException as e:
            print(f"✗ Serial connection failed: {e}")
            return False

    def disconnect(self):
        """Close serial connection"""
        self.listening = False
        if self.event_thread:
            self.event_thread.join(timeout=1)

        if self.serial and self.serial.is_open:
            self.serial.close()
            print("Disconnected from Arduino")

    def _send_command(self, command: str) -> Optional[Dict]:
        """
        Send command to Arduino and wait for response

        Args:
            command: Command string

        Returns:
            Parsed JSON response or None
        """
        if not self.serial or not self.serial.is_open:
            print("✗ Serial port not open")
            return None

        try:
            # Send command
            self.serial.write((command + '\n').encode('utf-8'))
            self.serial.flush()

            # Read response (with timeout)
            start_time = time.time()
            while time.time() - start_time < 1.0:
                if self.serial.in_waiting:
                    line = self.serial.readline().decode('utf-8').strip()
                    if line:
                        try:
                            return json.loads(line)
                        except json.JSONDecodeError:
                            print(f"Invalid JSON: {line}")
                time.sleep(0.01)

            print(f"✗ Timeout waiting for response to: {command}")
            return None

        except Exception as e:
            print(f"✗ Command error: {e}")
            return None

    # ==================== LCD METHODS ====================

    def lcd_write(self, row: int, col: int, text: str) -> bool:
        """
        Write text to LCD display

        Args:
            row: Row number (0 or 1)
            col: Column number (0-15)
            text: Text to display

        Returns:
            True if successful
        """
        # Truncate text to fit on display
        max_length = 16 - col
        text = text[:max_length]

        command = f"LCD {row} {col} {text}"
        response = self._send_command(command)
        return response is not None and response.get("status") == "ok"

    def lcd_clear(self) -> bool:
        """
        Clear LCD display

        Returns:
            True if successful
        """
        response = self._send_command("CLEAR")
        return response is not None and response.get("status") == "ok"

    # ==================== LED METHODS ====================

    def set_led(self, tier: int, r: int, g: int, b: int) -> bool:
        """
        Set RGB LED color

        Args:
            tier: LED tier (0, 1, or 2)
            r: Red value (0-255)
            g: Green value (0-255)
            b: Blue value (0-255)

        Returns:
            True if successful
        """
        command = f"LED {tier} {r} {g} {b}"
        response = self._send_command(command)
        return response is not None and response.get("status") == "ok"

    # ==================== SERVO METHODS ====================

    def set_servo(self, position: int) -> bool:
        """
        Set servo position

        Args:
            position: Servo position (0-180 degrees)

        Returns:
            True if successful
        """
        command = f"SERVO {position}"
        response = self._send_command(command)
        return response is not None and response.get("status") == "ok"

    # ==================== BUZZER METHODS ====================

    def beep(self, duration_ms: int = 200, frequency_hz: int = 1000) -> bool:
        """
        Play beep sound

        Args:
            duration_ms: Duration in milliseconds
            frequency_hz: Frequency in Hz

        Returns:
            True if successful
        """
        command = f"BEEP {duration_ms} {frequency_hz}"
        response = self._send_command(command)
        return response is not None and response.get("status") == "ok"

    def alert(self, alert_type: str) -> bool:
        """
        Play alert pattern

        Args:
            alert_type: Type of alert (success, warning, error, info)

        Returns:
            True if successful
        """
        command = f"ALERT {alert_type}"
        response = self._send_command(command)
        return response is not None and response.get("status") == "ok"

    # ==================== STATUS METHODS ====================

    def get_status(self) -> Optional[Dict]:
        """
        Get full status including sensor readings

        Returns:
            Dict with pot, temp_c, light values
        """
        return self._send_command("STATUS")

    # ==================== EVENT METHODS ====================

    def start_event_listener(self):
        """Start background thread to listen for events"""
        if not self.listening:
            self.listening = True
            self.event_thread = threading.Thread(target=self._event_loop, daemon=True)
            self.event_thread.start()

    def stop_event_listener(self):
        """Stop background event listener"""
        self.listening = False
        if self.event_thread:
            self.event_thread.join(timeout=1)

    def register_handler(self, event_type: str, handler: Callable):
        """
        Register event handler

        Args:
            event_type: Event type (button, tilt)
            handler: Function to call with event data
        """
        self.event_handlers[event_type] = handler

    def wait_event(self, timeout: float = 10.0) -> Optional[Dict]:
        """
        Wait for single event (blocking)

        Args:
            timeout: Timeout in seconds

        Returns:
            Event dict or None if timeout
        """
        if not self.serial or not self.serial.is_open:
            return None

        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.serial.in_waiting:
                line = self.serial.readline().decode('utf-8').strip()
                if line:
                    try:
                        data = json.loads(line)
                        if "event" in data:
                            return data
                    except json.JSONDecodeError:
                        pass
            time.sleep(0.01)

        return None

    def _event_loop(self):
        """Background event listener loop"""
        while self.listening and self.serial and self.serial.is_open:
            try:
                if self.serial.in_waiting:
                    line = self.serial.readline().decode('utf-8').strip()
                    if line:
                        try:
                            data = json.loads(line)
                            if "event" in data:
                                event_type = data.get("event")
                                if event_type in self.event_handlers:
                                    self.event_handlers[event_type](data)
                        except json.JSONDecodeError:
                            pass
                time.sleep(0.01)
            except Exception as e:
                print(f"Event loop error: {e}")
                time.sleep(0.1)


# ==================== CLI INTERFACE ====================

def main():
    """Command-line interface"""
    if len(sys.argv) < 2:
        print("Usage: surface_bridge.py <port> [command] [args...]")
        print("\nCommands:")
        print("  lcd <row> <col> <text>   - Write to LCD")
        print("  led <tier> <r> <g> <b>   - Set LED color")
        print("  servo <position>         - Set servo position")
        print("  beep [duration] [freq]   - Play beep")
        print("  alert <type>             - Play alert (success/warning/error/info)")
        print("  clear                    - Clear LCD")
        print("  status                   - Get sensor readings")
        print("  listen                   - Listen for events")
        print("  (no command)             - Interactive mode")
        print("\nExamples:")
        print('  surface_bridge.py /dev/tty.usbmodem14101 lcd 0 0 "Hello"')
        print("  surface_bridge.py /dev/tty.usbmodem14101 led 0 0 255 0")
        print("  surface_bridge.py /dev/tty.usbmodem14101 servo 90")
        sys.exit(1)

    port = sys.argv[1]
    surface = ArduinoSurface(port)

    if not surface.connect():
        sys.exit(1)

    try:
        if len(sys.argv) > 2:
            # Single command mode
            command = sys.argv[2]

            if command == "lcd" and len(sys.argv) >= 6:
                row = int(sys.argv[3])
                col = int(sys.argv[4])
                text = " ".join(sys.argv[5:])
                if surface.lcd_write(row, col, text):
                    print(f"✓ LCD: '{text}' at ({row},{col})")

            elif command == "led" and len(sys.argv) == 7:
                tier = int(sys.argv[3])
                r = int(sys.argv[4])
                g = int(sys.argv[5])
                b = int(sys.argv[6])
                if surface.set_led(tier, r, g, b):
                    print(f"✓ LED Tier{tier}: RGB({r},{g},{b})")

            elif command == "servo" and len(sys.argv) == 4:
                position = int(sys.argv[3])
                if surface.set_servo(position):
                    print(f"✓ Servo: {position}°")

            elif command == "beep":
                duration = int(sys.argv[3]) if len(sys.argv) > 3 else 200
                freq = int(sys.argv[4]) if len(sys.argv) > 4 else 1000
                if surface.beep(duration, freq):
                    print(f"✓ Beep: {duration}ms @ {freq}Hz")

            elif command == "alert" and len(sys.argv) == 4:
                alert_type = sys.argv[3]
                if surface.alert(alert_type):
                    print(f"✓ Alert: {alert_type}")

            elif command == "clear":
                if surface.lcd_clear():
                    print("✓ LCD cleared")

            elif command == "status":
                status = surface.get_status()
                if status:
                    print(f"✓ Status:")
                    print(f"  Potentiometer: {status.get('pot')}")
                    print(f"  Temperature: {status.get('temp_c')}°C")
                    print(f"  Light: {status.get('light')}")

            elif command == "listen":
                print("Listening for events (Ctrl+C to stop)...")
                surface.start_event_listener()

                def print_event(event):
                    print(f"Event: {json.dumps(event)}")

                surface.register_handler("button", print_event)
                surface.register_handler("tilt", print_event)

                while True:
                    time.sleep(0.1)

            else:
                print(f"✗ Unknown command: {command}")

        else:
            # Interactive mode
            print("\nInteractive Mode (type 'quit' to exit)")
            print("Commands: lcd, led, servo, beep, alert, clear, status, listen\n")

            while True:
                try:
                    cmd = input("> ").strip()

                    if cmd == "quit":
                        break

                    if not cmd:
                        continue

                    parts = cmd.split()
                    command = parts[0]

                    if command == "lcd" and len(parts) >= 4:
                        row = int(parts[1])
                        col = int(parts[2])
                        text = " ".join(parts[3:])
                        surface.lcd_write(row, col, text)

                    elif command == "led" and len(parts) == 5:
                        tier = int(parts[1])
                        r = int(parts[2])
                        g = int(parts[3])
                        b = int(parts[4])
                        surface.set_led(tier, r, g, b)

                    elif command == "servo" and len(parts) == 2:
                        position = int(parts[1])
                        surface.set_servo(position)

                    elif command == "beep":
                        duration = int(parts[1]) if len(parts) > 1 else 200
                        freq = int(parts[2]) if len(parts) > 2 else 1000
                        surface.beep(duration, freq)

                    elif command == "alert" and len(parts) == 2:
                        surface.alert(parts[1])

                    elif command == "clear":
                        surface.lcd_clear()

                    elif command == "status":
                        status = surface.get_status()
                        if status:
                            print(f"Pot: {status.get('pot')}, Temp: {status.get('temp_c')}°C, Light: {status.get('light')}")

                    else:
                        print("Unknown command")

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"Error: {e}")

    except KeyboardInterrupt:
        print("\nInterrupted")

    finally:
        surface.disconnect()


if __name__ == "__main__":
    main()

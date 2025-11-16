#!/usr/bin/env python3
"""
Arduino Surface Hardware Test
Systematic test of all hardware components to verify correct wiring and operation

Tests:
1. Serial connection
2. LCD display (all positions)
3. RGB LEDs (all tiers, all colors)
4. Servo motor (full sweep)
5. Buzzer (various frequencies)
6. Buttons (confirm and cancel)
7. Sensors (pot, temp, light)
8. Tilt switch

Run this script after assembling hardware to verify everything works.
"""

import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "bridge"))
from surface_bridge import ArduinoSurface


class HardwareTest:
    """Systematic hardware testing"""

    def __init__(self, surface: ArduinoSurface):
        self.surface = surface
        self.passed = []
        self.failed = []

    def test_serial_connection(self):
        """Test 1: Serial connection"""
        print("\n" + "="*60)
        print("TEST 1: Serial Connection")
        print("="*60)

        try:
            if self.surface.serial and self.surface.serial.is_open:
                print("✅ Serial port open")
                print(f"   Port: {self.surface.port}")
                print(f"   Baud: {self.surface.baud}")
                self.passed.append("Serial Connection")
                return True
            else:
                print("❌ Serial port not open")
                self.failed.append("Serial Connection")
                return False
        except Exception as e:
            print(f"❌ Serial connection error: {e}")
            self.failed.append("Serial Connection")
            return False

    def test_lcd_display(self):
        """Test 2: LCD Display"""
        print("\n" + "="*60)
        print("TEST 2: LCD Display")
        print("="*60)

        try:
            # Test clear
            if not self.surface.lcd_clear():
                print("❌ LCD clear failed")
                self.failed.append("LCD Display")
                return False

            print("✅ LCD clear works")
            time.sleep(1)

            # Test writing to different positions
            positions = [
                (0, 0, "Test Row 0"),
                (1, 0, "Test Row 1"),
                (0, 0, "Right align"),
                (1, 8, "Position"),
            ]

            for row, col, text in positions:
                if self.surface.lcd_write(row, col, text):
                    print(f"✅ LCD write ({row},{col}): '{text}'")
                    time.sleep(1)
                else:
                    print(f"❌ LCD write failed ({row},{col})")
                    self.failed.append("LCD Display")
                    return False

            self.passed.append("LCD Display")
            return True

        except Exception as e:
            print(f"❌ LCD test error: {e}")
            self.failed.append("LCD Display")
            return False

    def test_rgb_leds(self):
        """Test 3: RGB LEDs"""
        print("\n" + "="*60)
        print("TEST 3: RGB LEDs (3 tiers x 3 colors)")
        print("="*60)

        try:
            colors = [
                ("Red", 255, 0, 0),
                ("Green", 0, 255, 0),
                ("Blue", 0, 0, 255),
                ("Yellow", 255, 255, 0),
                ("Cyan", 0, 255, 255),
                ("Magenta", 255, 0, 255),
                ("White", 255, 255, 255),
            ]

            for tier in range(3):
                print(f"\nTier {tier}:")
                for color_name, r, g, b in colors:
                    if self.surface.set_led(tier, r, g, b):
                        print(f"  ✅ {color_name} (RGB: {r},{g},{b})")
                        time.sleep(0.5)
                    else:
                        print(f"  ❌ {color_name} failed")
                        self.failed.append(f"LED Tier{tier}")
                        return False

            # Turn off all LEDs
            for tier in range(3):
                self.surface.set_led(tier, 0, 0, 0)

            print("\n✅ All LEDs working")
            self.passed.append("RGB LEDs")
            return True

        except Exception as e:
            print(f"❌ LED test error: {e}")
            self.failed.append("RGB LEDs")
            return False

    def test_servo(self):
        """Test 4: Servo Motor"""
        print("\n" + "="*60)
        print("TEST 4: Servo Motor")
        print("="*60)

        try:
            positions = [0, 45, 90, 135, 180, 90]

            for pos in positions:
                if self.surface.set_servo(pos):
                    print(f"✅ Servo position {pos}° - observe movement")
                    time.sleep(1)
                else:
                    print(f"❌ Servo position {pos}° failed")
                    self.failed.append("Servo Motor")
                    return False

            print("✅ Servo sweep complete")
            self.passed.append("Servo Motor")
            return True

        except Exception as e:
            print(f"❌ Servo test error: {e}")
            self.failed.append("Servo Motor")
            return False

    def test_buzzer(self):
        """Test 5: Buzzer"""
        print("\n" + "="*60)
        print("TEST 5: Buzzer (Audio Output)")
        print("="*60)

        try:
            frequencies = [
                ("Low", 200, 200),
                ("Mid", 1000, 200),
                ("High", 2000, 200),
            ]

            for name, freq, duration in frequencies:
                if self.surface.beep(duration, freq):
                    print(f"✅ {name} frequency ({freq}Hz) - listen for tone")
                    time.sleep(0.5)
                else:
                    print(f"❌ Buzzer failed at {freq}Hz")
                    self.failed.append("Buzzer")
                    return False

            # Test alert patterns
            alerts = ["success", "warning", "error", "info"]
            for alert_type in alerts:
                if self.surface.alert(alert_type):
                    print(f"✅ Alert pattern: {alert_type}")
                    time.sleep(1)
                else:
                    print(f"❌ Alert {alert_type} failed")
                    self.failed.append("Buzzer")
                    return False

            print("✅ Buzzer and alerts working")
            self.passed.append("Buzzer")
            return True

        except Exception as e:
            print(f"❌ Buzzer test error: {e}")
            self.failed.append("Buzzer")
            return False

    def test_buttons(self):
        """Test 6: Buttons"""
        print("\n" + "="*60)
        print("TEST 6: Buttons (Interactive)")
        print("="*60)

        try:
            self.surface.lcd_clear()
            self.surface.lcd_write(0, 0, "Press CONFIRM")
            print("\n👆 Press the CONFIRM button (10s timeout)...")

            self.surface.start_event_listener()
            event = self.surface.wait_event(timeout=10)

            if event and event.get("event") == "button" and event.get("button") == "confirm":
                print("✅ CONFIRM button works")
                self.surface.alert("success")
            else:
                print("❌ CONFIRM button not detected (timeout or wrong button)")
                self.failed.append("Confirm Button")
                return False

            time.sleep(1)

            self.surface.lcd_clear()
            self.surface.lcd_write(0, 0, "Press CANCEL")
            print("\n👆 Press the CANCEL button (10s timeout)...")

            event = self.surface.wait_event(timeout=10)

            if event and event.get("event") == "button" and event.get("button") == "cancel":
                print("✅ CANCEL button works")
                self.surface.alert("success")
            else:
                print("❌ CANCEL button not detected (timeout or wrong button)")
                self.failed.append("Cancel Button")
                return False

            print("\n✅ Both buttons working")
            self.passed.append("Buttons")
            return True

        except Exception as e:
            print(f"❌ Button test error: {e}")
            self.failed.append("Buttons")
            return False

    def test_sensors(self):
        """Test 7: Sensors"""
        print("\n" + "="*60)
        print("TEST 7: Sensors (Analog Inputs)")
        print("="*60)

        try:
            self.surface.lcd_clear()
            self.surface.lcd_write(0, 0, "Reading sensors")

            print("\n📊 Reading sensor values (5 readings over 5 seconds)...")

            for i in range(5):
                status = self.surface.get_status()

                if status:
                    pot = status.get("pot", "N/A")
                    temp = status.get("temp_c", "N/A")
                    light = status.get("light", "N/A")

                    print(f"\nReading {i+1}:")
                    print(f"  Potentiometer: {pot} (0-1023)")
                    print(f"  Temperature: {temp}°C")
                    print(f"  Light: {light} (0-1023)")

                    self.surface.lcd_clear()
                    self.surface.lcd_write(0, 0, f"Pot:{pot} L:{light}")
                    self.surface.lcd_write(1, 0, f"Temp: {temp}C")

                    time.sleep(1)
                else:
                    print(f"❌ Failed to read sensors (attempt {i+1})")
                    self.failed.append("Sensors")
                    return False

            print("\n✅ All sensors readable")
            print("\n💡 Try adjusting the potentiometer and covering the light sensor")
            print("   to verify they respond to changes")

            self.passed.append("Sensors")
            return True

        except Exception as e:
            print(f"❌ Sensor test error: {e}")
            self.failed.append("Sensors")
            return False

    def test_tilt_switch(self):
        """Test 8: Tilt Switch"""
        print("\n" + "="*60)
        print("TEST 8: Tilt Switch (Emergency Stop)")
        print("="*60)

        try:
            self.surface.lcd_clear()
            self.surface.lcd_write(0, 0, "Tilt Arduino")
            self.surface.lcd_write(1, 0, "to test switch")

            print("\n🔄 Tilt the Arduino to trigger the tilt switch (10s timeout)...")
            print("   (The tilt switch may be sensitive - gentle tilt should trigger)")

            event = self.surface.wait_event(timeout=10)

            if event and event.get("event") == "tilt":
                print("✅ Tilt switch triggered!")
                self.surface.lcd_clear()
                self.surface.lcd_write(0, 0, "TILT DETECTED!")
                self.surface.alert("error")
                time.sleep(2)
                self.passed.append("Tilt Switch")
                return True
            else:
                print("❌ Tilt switch not detected (timeout)")
                print("   Check wiring: Tilt switch to A6 and GND")
                self.failed.append("Tilt Switch")
                return False

        except Exception as e:
            print(f"❌ Tilt switch test error: {e}")
            self.failed.append("Tilt Switch")
            return False

    def run_all_tests(self):
        """Run complete test suite"""
        print("\n" + "="*60)
        print("ARDUINO SURFACE HARDWARE TEST SUITE")
        print("="*60)
        print("\nThis will systematically test all hardware components.")
        print("Follow the instructions for interactive tests.\n")

        input("Press ENTER to start...")

        # Run all tests
        self.test_serial_connection()
        self.test_lcd_display()
        self.test_rgb_leds()
        self.test_servo()
        self.test_buzzer()
        self.test_buttons()
        self.test_sensors()
        self.test_tilt_switch()

        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)

        if self.passed:
            print(f"\n✅ PASSED ({len(self.passed)}):")
            for test in self.passed:
                print(f"   • {test}")

        if self.failed:
            print(f"\n❌ FAILED ({len(self.failed)}):")
            for test in self.failed:
                print(f"   • {test}")
            print("\nCheck wiring and pin assignments in ARDUINO_SURFACE_GUIDE.md")

        total = len(self.passed) + len(self.failed)
        success_rate = (len(self.passed) / total * 100) if total > 0 else 0

        print(f"\n📊 Success Rate: {success_rate:.1f}% ({len(self.passed)}/{total})")

        # Final display
        self.surface.lcd_clear()
        if len(self.failed) == 0:
            self.surface.lcd_write(0, 0, "All tests PASS!")
            self.surface.lcd_write(1, 0, "Hardware OK")
            self.surface.alert("success")
            print("\n🎉 All hardware tests passed! Arduino Surface ready for use.")
        else:
            self.surface.lcd_write(0, 0, f"{len(self.failed)} tests FAIL")
            self.surface.lcd_write(1, 0, "Check wiring")
            self.surface.alert("error")
            print("\n⚠️  Some tests failed. Review wiring and pin assignments.")

        return len(self.failed) == 0


def main():
    if len(sys.argv) < 2:
        print("Usage: test_hardware.py <serial_port>")
        print("Example: test_hardware.py /dev/tty.usbmodem14101")
        print("\nFind your port:")
        print("  macOS:   ls /dev/tty.usbmodem*")
        print("  Linux:   ls /dev/ttyACM*")
        print("  Windows: Check Device Manager → Ports (COM & LPT)")
        sys.exit(1)

    port = sys.argv[1]

    print("Connecting to Arduino...")
    surface = ArduinoSurface(port)

    if not surface.connect():
        print("❌ Failed to connect to Arduino")
        print("\nTroubleshooting:")
        print("  1. Check USB cable is connected")
        print("  2. Verify correct serial port")
        print("  3. Ensure firmware is flashed to Arduino")
        print("  4. Check baud rate is 115200")
        sys.exit(1)

    try:
        tester = HardwareTest(surface)
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n👋 Tests interrupted by user")
        surface.lcd_clear()
        surface.lcd_write(0, 0, "Tests stopped")

    finally:
        time.sleep(2)
        surface.disconnect()


if __name__ == "__main__":
    main()

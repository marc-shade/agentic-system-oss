#!/usr/bin/env python3
"""
Direct HID Gamepad Reader using hidapi

Reads USB game controller input directly via HID interface.
Bypasses pygame to work with devices that macOS recognizes but pygame doesn't.
"""

import hid
import sys
import time
from typing import Optional, Dict, List

class GamepadReader:
    """Direct HID gamepad interface"""

    def __init__(self, vendor_id: int = 0x0810, product_id: int = 0xE501):
        """
        Initialize gamepad reader

        Args:
            vendor_id: USB vendor ID (default: 0x0810 for detected gamepad)
            product_id: USB product ID (default: 0xE501 for detected gamepad)
        """
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.device = None
        self.button_state = [False] * 10  # 10 buttons detected
        self.axis_state = [0.0, 0.0]  # 2 axes detected

    def list_devices(self) -> List[Dict]:
        """List all HID devices"""
        devices = []
        for device_dict in hid.enumerate():
            devices.append({
                'vendor_id': device_dict['vendor_id'],
                'product_id': device_dict['product_id'],
                'manufacturer': device_dict['manufacturer_string'],
                'product': device_dict['product_string'],
                'path': device_dict['path']
            })
        return devices

    def find_gamepad(self) -> Optional[Dict]:
        """Find the specific gamepad by vendor/product ID"""
        for device in self.list_devices():
            if device['vendor_id'] == self.vendor_id and device['product_id'] == self.product_id:
                return device
        return None

    def connect(self) -> bool:
        """Connect to the gamepad"""
        try:
            self.device = hid.device()
            self.device.open(self.vendor_id, self.product_id)

            # Get device info
            manufacturer = self.device.get_manufacturer_string()
            product = self.device.get_product_string()

            print(f"✅ Connected to {product} by {manufacturer}")
            print(f"   Vendor ID: 0x{self.vendor_id:04X}")
            print(f"   Product ID: 0x{self.product_id:04X}")

            # Set non-blocking mode
            self.device.set_nonblocking(1)

            return True
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False

    def disconnect(self):
        """Disconnect from gamepad"""
        if self.device:
            self.device.close()
            self.device = None
            print("🔌 Disconnected from gamepad")

    def parse_report(self, data: bytes) -> Dict:
        """
        Parse HID report data into button and axis states

        Note: This is a generic parser. Actual format depends on gamepad.
        May need adjustment based on observed data patterns.
        """
        if not data or len(data) < 4:
            return None

        result = {
            'buttons': [],
            'axes': [],
            'raw': data.hex()
        }

        # Common gamepad report format:
        # Byte 0-1: Button bits (each bit = button)
        # Byte 2+: Axis values (signed or unsigned)

        # Parse buttons from first 2 bytes (16 buttons max)
        button_bytes = data[0:2]
        for byte_idx, byte_val in enumerate(button_bytes):
            for bit_idx in range(8):
                button_num = byte_idx * 8 + bit_idx
                if button_num < 10:  # We know there are 10 buttons
                    pressed = bool(byte_val & (1 << bit_idx))
                    result['buttons'].append({
                        'number': button_num,
                        'pressed': pressed
                    })

        # Parse axes from remaining bytes (typically 1 byte per axis)
        if len(data) >= 4:
            # Axes are usually at bytes 2-3 for X and Y
            # Values typically 0-255 (center at 127) or signed -128 to 127
            for axis_idx in range(min(2, len(data) - 2)):
                raw_value = data[2 + axis_idx]
                # Normalize to -1.0 to 1.0 range (assuming 0-255 input)
                normalized = (raw_value - 127.5) / 127.5
                result['axes'].append({
                    'number': axis_idx,
                    'value': normalized,
                    'raw': raw_value
                })

        return result

    def read_state(self) -> Optional[Dict]:
        """Read current gamepad state"""
        if not self.device:
            return None

        try:
            data = self.device.read(64)  # Read up to 64 bytes
            if data:
                return self.parse_report(bytes(data))
            return None
        except Exception as e:
            print(f"❌ Read error: {e}")
            return None

    def monitor(self, duration: float = 10.0, callback=None):
        """
        Monitor gamepad input for specified duration

        Args:
            duration: How long to monitor (seconds)
            callback: Optional function called on each state change
        """
        if not self.device:
            print("❌ Not connected to gamepad")
            return

        print(f"\n🎮 Monitoring gamepad for {duration} seconds...")
        print("Press buttons or move axes to see input\n")

        start_time = time.time()
        last_state = None

        while time.time() - start_time < duration:
            state = self.read_state()

            if state and state != last_state:
                # Print state changes
                print(f"⚡ Input detected:")

                # Show pressed buttons
                pressed = [b['number'] for b in state['buttons'] if b['pressed']]
                if pressed:
                    print(f"   Buttons: {pressed}")

                # Show axis movements
                for axis in state['axes']:
                    if abs(axis['value']) > 0.1:  # Ignore small noise
                        print(f"   Axis {axis['number']}: {axis['value']:.2f}")

                print(f"   Raw: {state['raw']}")
                print()

                if callback:
                    callback(state)

                last_state = state

            time.sleep(0.01)  # 100Hz polling

        print(f"✅ Monitoring complete ({duration}s)")


def quick_test():
    """Quick test of gamepad functionality"""
    reader = GamepadReader()

    print("🔍 Searching for gamepad...")
    gamepad = reader.find_gamepad()

    if not gamepad:
        print("\n❌ Gamepad not found!")
        print("\nAvailable HID devices:")
        for device in reader.list_devices():
            print(f"  - {device['product']} (VID: 0x{device['vendor_id']:04X}, PID: 0x{device['product_id']:04X})")
        return False

    print(f"✅ Found: {gamepad['product']}")
    print(f"   Path: {gamepad['path']}")

    if reader.connect():
        reader.monitor(duration=10.0)
        reader.disconnect()
        return True

    return False


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'list':
        # List all HID devices
        reader = GamepadReader()
        print("\n📋 All HID Devices:")
        for device in reader.list_devices():
            print(f"\n  VID: 0x{device['vendor_id']:04X}  PID: 0x{device['product_id']:04X}")
            print(f"  Product: {device['product']}")
            print(f"  Manufacturer: {device['manufacturer']}")
    else:
        # Run quick test
        success = quick_test()
        sys.exit(0 if success else 1)

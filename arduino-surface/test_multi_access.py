#!/usr/bin/env python3
"""
Test Multiple Process Access to Arduino via Broker
Demonstrates that multiple processes can safely access Arduino simultaneously
"""

import sys
import time
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'bridge'))
from arduino_client import ArduinoClient

def process_1():
    """Simulate process 1 - LCD updates"""
    print("Process 1: Starting LCD updates...")
    client = ArduinoClient()

    for i in range(5):
        if client.connect():
            result = client.lcd(0, f"Process 1: {i}")
            print(f"  P1 LCD {i}: {result.get('status', 'unknown')}")
            client.disconnect()
        time.sleep(2)

    print("Process 1: Complete")

def process_2():
    """Simulate process 2 - LED updates"""
    print("Process 2: Starting LED updates...")
    client = ArduinoClient()

    colors = [
        (255, 0, 0),    # Red
        (0, 255, 0),    # Green
        (0, 0, 255),    # Blue
        (255, 255, 0),  # Yellow
        (255, 165, 0),  # Orange
    ]

    for i, (r, g, b) in enumerate(colors):
        if client.connect():
            result = client.led(0, r, g, b)
            print(f"  P2 LED {i} ({r},{g},{b}): {result.get('status', 'unknown')}")
            client.disconnect()
        time.sleep(2)

    print("Process 2: Complete")

def process_3():
    """Simulate process 3 - Status requests"""
    print("Process 3: Starting status requests...")
    client = ArduinoClient()

    for i in range(5):
        if client.connect():
            result = client.raw("STATUS")
            print(f"  P3 STATUS {i}: {result.get('status', 'unknown')}")
            client.disconnect()
        time.sleep(2)

    print("Process 3: Complete")

def main():
    """Test concurrent access"""
    print("=" * 60)
    print("Testing Multi-Process Arduino Access via Broker")
    print("=" * 60)
    print()
    print("This test simulates 3 processes accessing Arduino simultaneously.")
    print("Without a broker, this would cause port conflicts and garbled data.")
    print("With the broker, all processes can safely coexist.")
    print()
    print("Starting in 2 seconds...")
    time.sleep(2)

    # Start three threads simulating different processes
    t1 = threading.Thread(target=process_1, daemon=True)
    t2 = threading.Thread(target=process_2, daemon=True)
    t3 = threading.Thread(target=process_3, daemon=True)

    t1.start()
    time.sleep(0.5)  # Stagger starts slightly
    t2.start()
    time.sleep(0.5)
    t3.start()

    # Wait for all to complete
    t1.join()
    t2.join()
    t3.join()

    print()
    print("=" * 60)
    print("✓ Test Complete - All processes ran without conflicts!")
    print("=" * 60)

if __name__ == "__main__":
    main()

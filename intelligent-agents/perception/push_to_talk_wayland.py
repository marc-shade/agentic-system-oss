#!/usr/bin/env python3
"""
Push-to-Talk Controller for Wayland - Monitors Caps Lock LED state

Works on Wayland by monitoring the Caps Lock LED state file in /sys/class/leds/
instead of using global keyboard listeners (which Wayland blocks for security).

Caps Lock ON = LED brightness 1 = Listening mode ACTIVE
Caps Lock OFF = LED brightness 0 = Stop listening
"""

import logging
import subprocess
import struct
import math
import time
from pathlib import Path
import glob

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("push_to_talk_wayland")

PTT_FLAG = Path("/tmp/ptt_active.flag")


def find_capslock_led() -> Path:
    """
    Find the Caps Lock LED brightness file in sysfs

    Returns:
        Path to capslock brightness file, or None if not found
    """
    # Common locations for Caps Lock LED
    patterns = [
        "/sys/class/leds/*capslock*/brightness",
        "/sys/class/leds/*caps*/brightness",
        "/sys/class/input/input*/capslock/brightness",
    ]

    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            logger.info(f"Found Caps Lock LED: {matches[0]}")
            return Path(matches[0])

    logger.warning("Could not find Caps Lock LED in sysfs")
    return None


def read_capslock_state(led_path: Path) -> bool:
    """
    Read Caps Lock LED state

    Args:
        led_path: Path to LED brightness file

    Returns:
        True if Caps Lock is ON, False if OFF
    """
    try:
        brightness = led_path.read_text().strip()
        return brightness == "1"
    except Exception as e:
        logger.debug(f"Could not read LED state: {e}")
        return False


def play_beep(frequency: int = 800, duration: float = 0.15):
    """
    Play audio beep for PTT feedback

    Args:
        frequency: Beep frequency in Hz (higher = higher pitch)
        duration: Beep duration in seconds
    """
    try:
        sample_rate = 16000
        num_samples = int(sample_rate * duration)
        samples = []

        for i in range(num_samples):
            sample = int(32767 * 0.4 * math.sin(2 * math.pi * frequency * i / sample_rate))
            samples.append(struct.pack('<h', sample))

        audio_data = b''.join(samples)

        proc = subprocess.Popen(
            ['paplay', '--raw', '--rate=16000', '--channels=1', '--format=s16le'],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        proc.communicate(input=audio_data, timeout=0.5)

    except Exception as e:
        logger.debug(f"Could not play beep: {e}")


def main():
    """
    Main loop: Monitor Caps Lock LED state and control PTT flag
    """
    logger.info("Push-to-Talk Controller (Wayland-compatible)")
    logger.info("Press Caps Lock to toggle listening mode")

    # Find Caps Lock LED
    led_path = find_capslock_led()
    if not led_path:
        logger.error("Could not find Caps Lock LED - exiting")
        logger.info("Try running: ls -la /sys/class/leds/*caps*")
        return

    # Track previous state
    prev_state = False
    ptt_active = False

    logger.info("Monitoring Caps Lock LED state...")

    try:
        while True:
            # Read current Caps Lock state
            current_state = read_capslock_state(led_path)

            # Detect state change
            if current_state != prev_state:
                if current_state:
                    # Caps Lock turned ON
                    PTT_FLAG.touch()
                    play_beep(1000, 0.15)  # High beep
                    logger.info("✓ CAPS LOCK ON - listening mode ACTIVE")
                    ptt_active = True
                else:
                    # Caps Lock turned OFF
                    if PTT_FLAG.exists():
                        PTT_FLAG.unlink()
                    play_beep(600, 0.15)  # Low beep
                    logger.info("✓ CAPS LOCK OFF - stopped listening")
                    ptt_active = False

                prev_state = current_state

            # Poll every 100ms for responsive detection
            time.sleep(0.1)

    except KeyboardInterrupt:
        logger.info("\nExiting push-to-talk controller")
        if PTT_FLAG.exists():
            PTT_FLAG.unlink()


if __name__ == "__main__":
    main()

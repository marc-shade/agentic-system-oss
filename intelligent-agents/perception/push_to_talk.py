#!/usr/bin/env python3
"""
Push-to-Talk Controller - Hold key to enable transcription

Press and hold F9 key to enable speech transcription.
Release F9 to stop transcription and finalize utterance.
"""

import logging
import subprocess
import struct
import math
from pathlib import Path
from pynput import keyboard

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Enable debug logging to see all key presses
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("push_to_talk")

PTT_FLAG = Path("/tmp/ptt_active.flag")
PTT_KEY = keyboard.Key.caps_lock  # Caps Lock for push-to-talk


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


class PushToTalkController:
    """
    Push-to-talk keyboard controller using Caps Lock toggle

    Caps Lock ON = Listening and transcribing
    Caps Lock OFF = Stop listening and finalize utterance
    """

    def __init__(self, ptt_key=PTT_KEY):
        self.ptt_key = ptt_key
        self.is_active = False
        logger.info(f"Push-to-talk initialized (key: Caps Lock)")

    def on_press(self, key):
        """Handle key press - toggle on Caps Lock"""
        # Debug: Log ALL key presses to diagnose issue
        logger.debug(f"Key pressed: {key}")

        try:
            if key == self.ptt_key:
                # Toggle PTT state
                self.is_active = not self.is_active

                if self.is_active:
                    # Caps Lock turned ON - start listening
                    PTT_FLAG.touch()
                    play_beep(1000, 0.15)  # High beep = PTT activated
                    logger.info("CAPS LOCK ON - listening mode ACTIVE")
                else:
                    # Caps Lock turned OFF - stop listening
                    if PTT_FLAG.exists():
                        PTT_FLAG.unlink()
                    play_beep(600, 0.15)  # Lower beep = PTT deactivated
                    logger.info("CAPS LOCK OFF - stopped listening, finalizing utterance")
                return
        except AttributeError:
            pass

        # Exit on Esc
        if key == keyboard.Key.esc:
            logger.info("Exiting push-to-talk controller")
            if PTT_FLAG.exists():
                PTT_FLAG.unlink()
            return False

    def on_release(self, key):
        """Handle key release - not used for toggle mode"""
        pass

    def run(self):
        """Start keyboard listener"""
        logger.info(f"Press and hold {self.ptt_key} to speak, ESC to exit")

        with keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        ) as listener:
            listener.join()


def main():
    """Entry point"""
    controller = PushToTalkController()
    controller.run()


if __name__ == "__main__":
    main()

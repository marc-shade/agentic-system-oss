#!/usr/bin/env python3
"""
Display Dispatcher - Centralized Arduino Display Controller

Acts as a message dispatcher that controls and filters all display updates
sent by various agents (consciousness daemon, conversation manager, etc.).

Priority System:
- CRITICAL (1): Emergency/alerts
- HIGH (2): Voice conversation, user interaction
- MEDIUM (3): Consciousness state changes
- LOW (4): Idle status, ambient monitoring

Design:
- Agents write display requests to queue file
- Dispatcher reads queue and prioritizes messages
- Only highest priority message is shown
- Messages auto-expire after TTL
- Ensures 16x2 character limit (no emojis)
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

# Add Arduino perceiver to path
sys.path.insert(0, str(Path(__file__).parent / "perception"))

from arduino_perceiver import ArduinoPerceiver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("display_dispatcher")

# Configuration
DISPLAY_QUEUE = Path("/tmp/arduino_display_queue.json")
ARDUINO_PORT = os.environ.get("ARDUINO_PORT", "/dev/ttyACM0")
UPDATE_INTERVAL = 0.5  # Check queue every 0.5 seconds


@dataclass
class DisplayMessage:
    """Represents a display message request"""
    source: str  # Which agent sent this (consciousness, conversation, etc.)
    priority: int  # 1=CRITICAL, 2=HIGH, 3=MEDIUM, 4=LOW
    line1: str  # Line 1 text (max 16 chars)
    line2: str  # Line 2 text (max 16 chars)
    led_color: tuple  # RGB tuple (r, g, b)
    ttl_seconds: float  # How long this message is valid
    timestamp: float  # When message was created

    def is_expired(self) -> bool:
        """Check if message has expired"""
        return time.time() > (self.timestamp + self.ttl_seconds)

    def format_for_display(self) -> tuple:
        """Format message ensuring 16 char limit per line"""
        # Remove any emojis and ensure ASCII
        line1_clean = self.line1.encode('ascii', 'ignore').decode('ascii')
        line2_clean = self.line2.encode('ascii', 'ignore').decode('ascii')

        # Truncate and pad to exactly 16 characters
        line1_formatted = line1_clean[:16].ljust(16)
        line2_formatted = line2_clean[:16].ljust(16)

        return line1_formatted, line2_formatted, self.led_color


class DisplayDispatcher:
    """
    Centralized display controller for Arduino

    Manages display updates from multiple agents with priority-based routing
    """

    def __init__(self, arduino_port: str = ARDUINO_PORT):
        self.arduino = ArduinoPerceiver(port=arduino_port, fallback_on_error=True)
        self.current_message = None
        self.message_queue = []

        logger.info(f"Display Dispatcher initialized on {arduino_port}")

    def read_queue(self) -> List[DisplayMessage]:
        """
        Read display messages from queue file

        Returns:
            List of DisplayMessage objects
        """
        if not DISPLAY_QUEUE.exists():
            return []

        try:
            with open(DISPLAY_QUEUE, 'r') as f:
                data = json.load(f)

            messages = []
            for msg_data in data.get("messages", []):
                msg = DisplayMessage(
                    source=msg_data["source"],
                    priority=msg_data["priority"],
                    line1=msg_data["line1"],
                    line2=msg_data["line2"],
                    led_color=tuple(msg_data["led_color"]),
                    ttl_seconds=msg_data["ttl_seconds"],
                    timestamp=msg_data["timestamp"]
                )
                messages.append(msg)

            return messages

        except Exception as e:
            logger.error(f"Failed to read queue: {e}")
            return []

    def write_queue(self, messages: List[DisplayMessage]):
        """
        Write updated message queue back to file

        Args:
            messages: List of DisplayMessage objects to save
        """
        try:
            data = {
                "messages": [asdict(msg) for msg in messages],
                "last_update": datetime.now().isoformat()
            }

            with open(DISPLAY_QUEUE, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to write queue: {e}")

    def get_highest_priority_message(self, messages: List[DisplayMessage]) -> Optional[DisplayMessage]:
        """
        Get highest priority non-expired message

        Args:
            messages: List of messages to filter

        Returns:
            Highest priority message or None
        """
        # Filter out expired messages
        valid_messages = [msg for msg in messages if not msg.is_expired()]

        if not valid_messages:
            return None

        # Sort by priority (1=highest) then by timestamp (newest first)
        sorted_messages = sorted(valid_messages, key=lambda m: (m.priority, -m.timestamp))

        return sorted_messages[0] if sorted_messages else None

    def update_display(self, message: DisplayMessage):
        """
        Update Arduino display with message

        Args:
            message: DisplayMessage to show
        """
        line1, line2, led_color = message.format_for_display()

        success = self.arduino.update_display(line1, line2, led_color)

        if success:
            logger.debug(f"Display updated: [{message.source}] P{message.priority} | {line1.strip()} / {line2.strip()}")

        self.current_message = message

    def cleanup_expired(self, messages: List[DisplayMessage]) -> List[DisplayMessage]:
        """
        Remove expired messages from queue

        Args:
            messages: Current message list

        Returns:
            Filtered list with only valid messages
        """
        valid = [msg for msg in messages if not msg.is_expired()]
        expired_count = len(messages) - len(valid)

        if expired_count > 0:
            logger.debug(f"Cleaned up {expired_count} expired messages")

        return valid

    def run(self):
        """
        Main dispatcher loop

        Continuously monitors queue and updates display with highest priority message
        """
        logger.info("Display Dispatcher starting main loop...")

        # Show startup message
        startup_msg = DisplayMessage(
            source="dispatcher",
            priority=2,
            line1="Display Ready",
            line2="Awaiting msgs...",
            led_color=(0, 255, 0),
            ttl_seconds=5,
            timestamp=time.time()
        )
        self.update_display(startup_msg)

        while True:
            try:
                # Read queue from file
                messages = self.read_queue()

                # Cleanup expired messages
                messages = self.cleanup_expired(messages)

                # Write cleaned queue back
                if messages:
                    self.write_queue(messages)

                # Get highest priority message
                top_message = self.get_highest_priority_message(messages)

                # Update display if message changed
                if top_message:
                    # Check if different from current
                    if (not self.current_message or
                        top_message.source != self.current_message.source or
                        top_message.line1 != self.current_message.line1 or
                        top_message.line2 != self.current_message.line2):

                        self.update_display(top_message)
                else:
                    # No messages - show idle state
                    if self.current_message and self.current_message.source != "idle":
                        idle_msg = DisplayMessage(
                            source="idle",
                            priority=4,
                            line1="AGI Idle",
                            line2="No activity",
                            led_color=(0, 100, 0),
                            ttl_seconds=60,
                            timestamp=time.time()
                        )
                        self.update_display(idle_msg)

                # Sleep before next check
                time.sleep(UPDATE_INTERVAL)

            except KeyboardInterrupt:
                logger.info("Display Dispatcher stopped by user")
                break
            except Exception as e:
                logger.error(f"Dispatcher loop error: {e}", exc_info=True)
                time.sleep(1)


def send_display_message(source: str, priority: int, line1: str, line2: str,
                         led_color: tuple, ttl_seconds: float = 10):
    """
    Helper function for agents to send display messages

    Args:
        source: Agent name (e.g., "consciousness", "conversation")
        priority: 1=CRITICAL, 2=HIGH, 3=MEDIUM, 4=LOW
        line1: First line of text (max 16 chars)
        line2: Second line of text (max 16 chars)
        led_color: RGB tuple
        ttl_seconds: How long message is valid
    """
    message = DisplayMessage(
        source=source,
        priority=priority,
        line1=line1,
        line2=line2,
        led_color=led_color,
        ttl_seconds=ttl_seconds,
        timestamp=time.time()
    )

    try:
        # Read existing queue
        messages = []
        if DISPLAY_QUEUE.exists():
            with open(DISPLAY_QUEUE, 'r') as f:
                data = json.load(f)
                for msg_data in data.get("messages", []):
                    messages.append(msg_data)

        # Add new message
        messages.append(asdict(message))

        # Write back
        data = {
            "messages": messages,
            "last_update": datetime.now().isoformat()
        }

        with open(DISPLAY_QUEUE, 'w') as f:
            json.dump(data, f, indent=2)

        return True

    except Exception as e:
        logger.error(f"Failed to send display message: {e}")
        return False


if __name__ == "__main__":
    """Run the dispatcher"""
    dispatcher = DisplayDispatcher()
    dispatcher.run()

#!/usr/bin/env python3
"""
Voice Conversation Monitor
Watches for new speech transcriptions and automatically triggers Claude Code responses
"""

import asyncio
import json
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Set

# Add MCP server path
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-servers/voice-mode"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("voice-monitor")


class VoiceConversationMonitor:
    """Monitor voice transcriptions and trigger responses"""

    def __init__(self, poll_interval: float = 2.0):
        self.poll_interval = poll_interval
        self.seen_transcriptions: Set[str] = set()
        self.last_check = datetime.now()

    async def get_new_transcriptions(self) -> list:
        """Get new transcriptions since last check"""
        try:
            # Import voice mode server state
            from server import stt_state

            # Get recent transcriptions
            transcriptions = stt_state.get_recent_transcriptions(limit=10)

            # Filter out blank audio and already-seen transcriptions
            new_transcriptions = []
            for t in transcriptions:
                text = t.get("text", "")
                timestamp = t.get("timestamp", "")

                # Skip blank audio
                if text == "[BLANK_AUDIO]":
                    continue

                # Check if we've seen this before
                key = f"{timestamp}:{text}"
                if key not in self.seen_transcriptions:
                    self.seen_transcriptions.add(key)
                    new_transcriptions.append(t)

            return new_transcriptions

        except Exception as e:
            logger.error(f"Error getting transcriptions: {e}")
            return []

    async def trigger_claude_response(self, transcription: dict):
        """Trigger Claude Code to respond to transcription"""
        text = transcription.get("text", "")
        timestamp = transcription.get("timestamp", "")

        logger.info(f"New transcription at {timestamp}: {text}")

        # Create a notification file that Claude Code hooks can watch
        notification_file = Path("/tmp/claude-voice-input.json")
        notification_file.write_text(json.dumps({
            "text": text,
            "timestamp": timestamp,
            "action": "respond"
        }))

        logger.info(f"Created notification: {notification_file}")

    async def monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Starting voice conversation monitor...")
        logger.info(f"Polling every {self.poll_interval} seconds")

        while True:
            try:
                # Get new transcriptions
                new_transcriptions = await self.get_new_transcriptions()

                # Trigger response for each new transcription
                for transcription in new_transcriptions:
                    await self.trigger_claude_response(transcription)

                # Wait before next poll
                await asyncio.sleep(self.poll_interval)

            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(self.poll_interval)


async def main():
    """Main entry point"""
    monitor = VoiceConversationMonitor(poll_interval=2.0)
    await monitor.monitor_loop()


if __name__ == "__main__":
    asyncio.run(main())

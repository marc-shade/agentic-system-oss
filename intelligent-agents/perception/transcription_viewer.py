#!/usr/bin/env python3
"""
Real-time Transcription Viewer
Displays speech-to-text transcriptions in a visual speech bubble format.
Monitors /tmp/conversation_transcript.json and shows new transcriptions as they arrive.
"""

import json
import time
import os
import sys
from datetime import datetime
from pathlib import Path

TRANSCRIPT_FILE = "/tmp/conversation_transcript.json"
POLL_INTERVAL = 0.1  # seconds

def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name == 'posix' else 'cls')

def draw_speech_bubble(text, speaker="user", confidence=0.0, timestamp=""):
    """Draw a speech bubble around text"""
    lines = []

    # Wrap text to max 70 characters per line
    words = text.split()
    current_line = []
    for word in words:
        test_line = ' '.join(current_line + [word])
        if len(test_line) <= 70:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))

    # Calculate bubble width
    max_width = max(len(line) for line in lines) if lines else 0
    bubble_width = max_width + 4  # padding

    # Top of bubble
    bubble = []
    bubble.append("  " + "┌" + "─" * bubble_width + "┐")

    # Content lines
    for line in lines:
        padding = bubble_width - len(line) - 2
        bubble.append("  │ " + line + " " * padding + " │")

    # Bottom of bubble
    bubble.append("  └" + "─" * bubble_width + "┘")

    # Add tail for speech bubble
    if speaker == "user":
        bubble.append("   ╲")
        bubble.append("    ╲")
        bubble.append("     🗣️  YOU")
    else:
        bubble.append("   ╱")
        bubble.append("  ╱")
        bubble.append(" 🤖 AI")

    # Add metadata
    confidence_bar = "█" * int(confidence * 10) + "░" * (10 - int(confidence * 10))
    bubble.append(f"\n  ⏱️  {timestamp}")
    bubble.append(f"  📊 Confidence: [{confidence_bar}] {confidence:.1%}")

    return "\n".join(bubble)

def load_transcriptions():
    """Load all transcriptions from file"""
    try:
        if not Path(TRANSCRIPT_FILE).exists():
            return []

        with open(TRANSCRIPT_FILE, 'r') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []
    except Exception as e:
        print(f"Error loading transcriptions: {e}")
        return []

def format_timestamp(ts_str):
    """Format ISO timestamp to human-readable"""
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime("%H:%M:%S")
    except:
        return ts_str

def main():
    """Main viewer loop"""
    print("🎙️  Real-time Transcription Viewer")
    print("=" * 80)
    print("Monitoring:", TRANSCRIPT_FILE)
    print("Press Ctrl+C to exit")
    print("=" * 80)
    print()

    last_count = 0
    displayed_transcriptions = []

    try:
        while True:
            transcriptions = load_transcriptions()

            # Check if there are new transcriptions
            if len(transcriptions) > last_count:
                # Display only new transcriptions
                new_transcriptions = transcriptions[last_count:]

                for trans in new_transcriptions:
                    utterance = trans.get('utterance', '')
                    speaker = trans.get('speaker', 'user')
                    confidence = trans.get('confidence', 0.0)
                    timestamp = format_timestamp(trans.get('timestamp', ''))

                    # Clear and redisplay recent history
                    clear_screen()

                    print("🎙️  Real-time Transcription Viewer")
                    print("=" * 80)
                    print()

                    # Show last 5 transcriptions for context
                    display_count = min(5, len(transcriptions))
                    for t in transcriptions[-display_count:]:
                        bubble = draw_speech_bubble(
                            t.get('utterance', ''),
                            t.get('speaker', 'user'),
                            t.get('confidence', 0.0),
                            format_timestamp(t.get('timestamp', ''))
                        )
                        print(bubble)
                        print()

                    print("=" * 80)
                    print(f"Total transcriptions: {len(transcriptions)} | Waiting for speech...")

                last_count = len(transcriptions)

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n👋 Transcription viewer stopped")
        sys.exit(0)

if __name__ == "__main__":
    main()

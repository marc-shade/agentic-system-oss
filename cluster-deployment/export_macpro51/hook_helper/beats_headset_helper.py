#!/usr/bin/env python3
"""
Beats Headset Audio Router
Switches audio output to Beats Fit Pro for voice communication
"""
import subprocess
import sys

def switch_to_beats():
    """Switch audio output to Beats Fit Pro"""
    # AppleScript to set audio output device
    applescript = '''
    tell application "System Events"
        tell application process "SystemUIServer"
            set audioDevice to "Beats Fit Pro"
        end tell
    end tell

    do shell script "defaults write com.apple.sound.output device -string 'Beats Fit Pro'"
    '''

    try:
        # Try direct AppleScript approach
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            return True

        # Alternative: Use SwitchAudioSource if installed via Homebrew
        result = subprocess.run(
            ['which', 'SwitchAudioSource'],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            subprocess.run(
                ['SwitchAudioSource', '-s', 'Beats Fit Pro'],
                capture_output=True,
                timeout=5
            )
            return True

        return False

    except Exception as e:
        print(f"Error switching audio: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    if switch_to_beats():
        print("Audio routed to Beats Fit Pro")
    else:
        print("Failed to route audio", file=sys.stderr)
        sys.exit(1)

#!/usr/bin/env python3
"""Audio feedback - chimes/pips for voice interaction"""

import subprocess
import tempfile
import numpy as np
import wave

def play_sound(frequency=1000, duration=0.2, volume=0.3):
    """Generate and play a tone"""
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration))
    tone = (np.sin(2 * np.pi * frequency * t) * volume * 32767).astype(np.int16)
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        wf = wave.open(f.name, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(tone.tobytes())
        wf.close()
        
        # Play with afplay (macOS)
        subprocess.run(['afplay', f.name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        import os
        os.unlink(f.name)

def listening_start():
    """Play 'start listening' chime"""
    play_sound(frequency=800, duration=0.15)

def listening_end():
    """Play 'stop listening' chime"""
    play_sound(frequency=600, duration=0.15)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'start':
        listening_start()
    elif len(sys.argv) > 1 and sys.argv[1] == 'end':
        listening_end()
    else:
        print("Usage: audio_feedback.py start|end")

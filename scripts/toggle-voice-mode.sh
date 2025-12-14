#!/bin/bash
# Toggle voice mode for Wayland - plays beep and toggles flag

FLAG_FILE="/tmp/voice_mode_active.flag"

if [ -f "$FLAG_FILE" ]; then
    # Turn OFF
    rm "$FLAG_FILE"
    echo "Voice mode: OFF"
    
    # Play low beep (600Hz)
    python3 << 'PYEOF'
import subprocess, struct, math
frequency, duration, sample_rate = 600, 0.15, 16000
samples = [struct.pack('<h', int(32767 * 0.4 * math.sin(2 * math.pi * frequency * i / sample_rate))) for i in range(int(sample_rate * duration))]
subprocess.run(['paplay', '--raw', '--rate=16000', '--channels=1', '--format=s16le'], input=b''.join(samples), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
PYEOF
else
    # Turn ON
    touch "$FLAG_FILE"
    echo "Voice mode: ON"
    
    # Play high beep (1000Hz)
    python3 << 'PYEOF'
import subprocess, struct, math
frequency, duration, sample_rate = 1000, 0.15, 16000
samples = [struct.pack('<h', int(32767 * 0.4 * math.sin(2 * math.pi * frequency * i / sample_rate))) for i in range(int(sample_rate * duration))]
subprocess.run(['paplay', '--raw', '--rate=16000', '--channels=1', '--format=s16le'], input=b''.join(samples), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
PYEOF
fi

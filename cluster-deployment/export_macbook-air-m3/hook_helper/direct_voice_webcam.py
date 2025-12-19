#!/usr/bin/env python3
"""
Direct Voice with Webcam Microphone Fallback
==============================================

Alternative version that uses HD Pro Webcam C920 instead of Beats Fit Pro
if Bluetooth microphone levels are too low.
"""

import pyaudio
import wave
import tempfile
import requests
import os
import subprocess
import numpy as np
from typing import Optional, Tuple


class DirectVoiceWebcam:
    """Direct voice using webcam microphone instead of Bluetooth"""

    def __init__(self, audio_feedback: bool = True):
        self.whisper_url = "http://127.0.0.1:2022/v1/audio/transcriptions"
        self.kokoro_url = "http://127.0.0.1:8880/v1/audio/speech"
        self.rate = 16000
        self.channels = 2  # Webcam is stereo
        self.chunk = 1024
        self.audio_feedback = audio_feedback
        self.device_index = 4  # HD Pro Webcam C920

        print("🎥 Using HD Pro Webcam C920 microphone")

    def _play_chime(self, frequency: int = 800, duration: float = 0.15, volume: float = 0.3):
        """Play audio feedback chime"""
        if not self.audio_feedback:
            return

        try:
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

                subprocess.run(['afplay', f.name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                os.unlink(f.name)
        except:
            pass

    def _listening_start_chime(self):
        """Play 'start listening' chime"""
        self._play_chime(frequency=800, duration=0.15)

    def _listening_end_chime(self):
        """Play 'stop listening' chime"""
        self._play_chime(frequency=600, duration=0.15)

    def record_audio(self, duration: float = 10.0) -> bytes:
        """Record audio from webcam microphone"""
        self._listening_start_chime()

        p = pyaudio.PyAudio()

        stream = p.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.rate,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=self.chunk
        )

        print(f"🎤 Recording for {duration} seconds from webcam...")

        frames = []
        num_chunks = int(self.rate / self.chunk * duration)
        for _ in range(num_chunks):
            data = stream.read(self.chunk, exception_on_overflow=False)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        p.terminate()

        self._listening_end_chime()

        # Convert stereo to mono for Whisper
        audio_data = b''.join(frames)
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        audio_mono = audio_array[::2]  # Take left channel only

        # Check levels
        max_amp = np.max(np.abs(audio_mono))
        print(f"📊 Audio level: {max_amp} (target: >1000)")

        # Convert to WAV bytes
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wf = wave.open(f.name, 'wb')
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.rate)
            wf.writeframes(audio_mono.tobytes())
            wf.close()

            with open(f.name, 'rb') as audio_file:
                wav_data = audio_file.read()

            os.unlink(f.name)

        return wav_data

    def transcribe(self, audio_data: bytes) -> Optional[str]:
        """Transcribe audio using local Whisper"""
        try:
            response = requests.post(
                self.whisper_url,
                files={'file': ('audio.wav', audio_data, 'audio/wav')},
                data={'model': 'whisper-1'},
                timeout=30
            )

            if response.ok:
                result = response.json()
                return result.get('text', '').strip()
            else:
                print(f"❌ Whisper error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            return None

    def speak(self, text: str, voice: str = "af_sky") -> bool:
        """Speak text using local Kokoro TTS"""
        try:
            response = requests.post(
                self.kokoro_url,
                json={
                    'model': 'tts-1',
                    'input': text,
                    'voice': voice
                },
                timeout=30
            )

            if response.ok:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    f.write(response.content)
                    f.flush()
                    subprocess.run(['afplay', f.name], check=True)
                    os.unlink(f.name)
                return True
            else:
                print(f"❌ TTS error: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Speech error: {e}")
            return False

    def listen_only(self, duration: float = 10.0) -> Optional[str]:
        """Listen and transcribe"""
        audio = self.record_audio(duration=duration)
        return self.transcribe(audio)


if __name__ == '__main__':
    import sys

    voice = DirectVoiceWebcam()

    if len(sys.argv) < 2:
        print("Usage: python3 direct_voice_webcam.py listen [seconds]")
        sys.exit(1)

    if sys.argv[1] == 'listen':
        duration = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
        text = voice.listen_only(duration)
        if text:
            print(f"\n✅ YOU SAID: {text}")
        else:
            print("\n❌ No speech detected")

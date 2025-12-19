#!/usr/bin/env python3
"""
Direct Voice Integration - No MCP Dependency

This provides direct access to voice services without relying on MCP,
ensuring voice works even if MCP connections drop.
"""

import pyaudio
import wave
import tempfile
import requests
import os
import subprocess
import numpy as np
from typing import Optional, Tuple

class DirectVoice:
    """Direct voice interface bypassing MCP"""

    def __init__(self, audio_feedback: bool = True):
        self.whisper_url = "http://127.0.0.1:2022/v1/audio/transcriptions"
        self.kokoro_url = "http://127.0.0.1:8880/v1/audio/speech"
        self.rate = 16000
        self.channels = 1
        self.chunk = 1024
        self.audio_feedback = audio_feedback

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
            pass  # Silently fail if chime doesn't work

    def _listening_start_chime(self):
        """Play 'start listening' chime"""
        self._play_chime(frequency=800, duration=0.15)

    def _listening_end_chime(self):
        """Play 'stop listening' chime"""
        self._play_chime(frequency=600, duration=0.15)

    def list_microphones(self):
        """List all available input devices"""
        p = pyaudio.PyAudio()
        mics = []
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                mics.append({
                    'index': i,
                    'name': info['name'],
                    'channels': info['maxInputChannels']
                })
        p.terminate()
        return mics

    def record_audio(self, duration: float = 10.0, device_index: Optional[int] = None) -> bytes:
        """
        Record audio from microphone

        Args:
            duration: Recording duration in seconds
            device_index: Specific device to use (None = default)

        Returns:
            WAV audio data as bytes
        """
        # Play start chime
        self._listening_start_chime()

        p = pyaudio.PyAudio()

        stream = p.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=self.chunk
        )

        print(f"🎤 Recording for {duration} seconds...")

        frames = []
        num_chunks = int(self.rate / self.chunk * duration)
        for _ in range(num_chunks):
            data = stream.read(self.chunk, exception_on_overflow=False)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        p.terminate()

        # Play end chime
        self._listening_end_chime()

        # Convert to WAV bytes
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wf = wave.open(f.name, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(frames))
            wf.close()

            with open(f.name, 'rb') as audio_file:
                wav_data = audio_file.read()

            os.unlink(f.name)

        return wav_data

    def transcribe(self, audio_data: bytes) -> Optional[str]:
        """
        Transcribe audio using local Whisper

        Args:
            audio_data: WAV audio bytes

        Returns:
            Transcribed text or None on error
        """
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
        """
        Speak text using local Kokoro TTS

        Args:
            text: Text to speak
            voice: Voice to use (default: af_sky)

        Returns:
            True on success
        """
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
                # Play audio
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    f.write(response.content)
                    f.flush()

                    # Use afplay (macOS native)
                    subprocess.run(['afplay', f.name], check=True)
                    os.unlink(f.name)

                return True
            else:
                print(f"❌ TTS error: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Speech error: {e}")
            return False

    def converse(self, message: str, listen_duration: float = 10.0) -> Tuple[bool, Optional[str]]:
        """
        Speak a message and listen for response

        Args:
            message: Message to speak
            listen_duration: How long to listen for response

        Returns:
            (success, response_text)
        """
        # Speak
        print(f"🔊 Speaking: {message}")
        if not self.speak(message):
            return (False, None)

        # Listen
        audio = self.record_audio(duration=listen_duration)

        # Transcribe
        print("🎯 Transcribing...")
        text = self.transcribe(audio)

        if text:
            print(f"✅ Heard: {text}")
            return (True, text)
        else:
            print("❌ No speech detected")
            return (False, None)

    def listen_only(self, duration: float = 10.0) -> Optional[str]:
        """
        Just listen without speaking first

        Args:
            duration: How long to listen

        Returns:
            Transcribed text or None
        """
        audio = self.record_audio(duration=duration)
        return self.transcribe(audio)


def quick_listen(duration: float = 10.0) -> Optional[str]:
    """Quick function to listen and transcribe"""
    voice = DirectVoice()
    return voice.listen_only(duration)


def quick_speak(text: str) -> bool:
    """Quick function to speak"""
    voice = DirectVoice()
    return voice.speak(text)


def quick_converse(message: str, listen_duration: float = 10.0) -> Optional[str]:
    """Quick function for speak + listen"""
    voice = DirectVoice()
    success, response = voice.converse(message, listen_duration)
    return response if success else None


if __name__ == '__main__':
    import sys

    voice = DirectVoice()

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 direct_voice.py list          # List microphones")
        print("  python3 direct_voice.py listen [secs] # Listen and transcribe")
        print("  python3 direct_voice.py speak 'text'  # Speak text")
        print("  python3 direct_voice.py converse 'text' [secs]  # Speak and listen")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'list':
        mics = voice.list_microphones()
        print("\nAvailable Microphones:")
        for mic in mics:
            print(f"  [{mic['index']}] {mic['name']} ({mic['channels']} channels)")

    elif command == 'listen':
        duration = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
        text = voice.listen_only(duration)
        if text:
            print(f"\n✅ YOU SAID: {text}")
        else:
            print("\n❌ No speech detected")

    elif command == 'speak':
        if len(sys.argv) < 3:
            print("Error: Provide text to speak")
            sys.exit(1)
        text = sys.argv[2]
        voice.speak(text)

    elif command == 'converse':
        if len(sys.argv) < 3:
            print("Error: Provide message to speak")
            sys.exit(1)
        message = sys.argv[2]
        duration = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0
        success, response = voice.converse(message, duration)
        if success:
            print(f"\n✅ USER RESPONSE: {response}")
        else:
            print("\n❌ No response detected")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

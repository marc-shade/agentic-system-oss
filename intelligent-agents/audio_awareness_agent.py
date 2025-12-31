#!/usr/bin/env python3
"""
Audio Awareness Agent
=====================
Continuous audio monitoring and transcription for AGI environmental awareness.

Uses local Whisper STT to:
- Listen for ambient audio
- Transcribe speech to text
- Detect conversations, commands, announcements
- Store insights in enhanced-memory

Audio is processed in real-time and NOT stored permanently to save space.
Only transcriptions and insights are persisted.
"""

import asyncio
import json
import sqlite3
import subprocess
import tempfile
import os
import socket
import wave
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import threading
import time

# Configuration
STORAGE_BASE = Path("/Volumes/SSDRAID0/agentic-system")
SENSORY_DIR = STORAGE_BASE / "databases" / "sensory"
DB_PATH = SENSORY_DIR / f"sensory_memory_{socket.gethostname().lower().replace(' ', '-')}.db"

# Whisper STT endpoint (local)
WHISPER_ENDPOINT = "http://127.0.0.1:2022/v1/audio/transcriptions"

# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_DURATION_SECONDS = 10  # Process audio in 10-second chunks
SILENCE_THRESHOLD = 500  # RMS threshold for silence detection
MIN_AUDIO_LENGTH_SECONDS = 2  # Minimum audio to transcribe

# Processing settings
LISTEN_INTERVAL_SECONDS = 5  # Time between listen cycles
MAX_AUDIO_BUFFER_SECONDS = 60  # Maximum audio to buffer before forcing process


@dataclass
class AudioChunk:
    """Represents a chunk of recorded audio."""
    filepath: Path
    duration_seconds: float
    timestamp: datetime
    rms_level: float


class AudioAwarenessAgent:
    """Agent for continuous audio awareness."""

    def __init__(self):
        self.node_id = socket.gethostname().lower().replace(" ", "-")
        self.running = False
        self.audio_dir = SENSORY_DIR / "audio" / self.node_id
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_db()
        self._check_dependencies()

    def _ensure_db(self):
        """Ensure database has required tables."""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audio_transcripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    duration_seconds REAL,
                    transcript TEXT,
                    confidence REAL,
                    language TEXT,
                    insights_json TEXT,
                    stored_in_memory BOOLEAN DEFAULT FALSE,
                    memory_entity_id TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audio_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT,
                    description TEXT,
                    metadata TEXT
                )
            """)
            conn.commit()

    def _check_dependencies(self):
        """Check for required audio tools."""
        # Check for sox (audio recording tool)
        result = subprocess.run(['which', 'sox'], capture_output=True)
        if result.returncode != 0:
            print("Warning: sox not found. Install with: brew install sox")
            self.sox_available = False
        else:
            self.sox_available = True

        # Check for rec (part of sox)
        result = subprocess.run(['which', 'rec'], capture_output=True)
        if result.returncode != 0:
            print("Warning: rec not found. Audio recording may not work.")
            self.rec_available = False
        else:
            self.rec_available = True

        # Check Whisper endpoint
        try:
            # Just check if endpoint responds (even with error is fine)
            requests.get(WHISPER_ENDPOINT.replace('/audio/transcriptions', ''), timeout=2)
            self.whisper_available = True
        except:
            print(f"Warning: Whisper STT not available at {WHISPER_ENDPOINT}")
            self.whisper_available = False

    async def record_audio(self, duration_seconds: float) -> Optional[AudioChunk]:
        """Record audio for specified duration."""
        if not self.rec_available:
            return None

        timestamp = datetime.now()
        filename = f"audio_{timestamp.strftime('%Y%m%d_%H%M%S')}.wav"
        filepath = self.audio_dir / filename

        try:
            # Record using sox/rec
            # -q: quiet, -r: sample rate, -c: channels, -b: bits
            cmd = [
                'rec', '-q',
                '-r', str(SAMPLE_RATE),
                '-c', str(CHANNELS),
                '-b', '16',
                str(filepath),
                'trim', '0', str(duration_seconds),
                'silence', '1', '0.1', '3%', '1', '0.5', '3%'  # Stop on silence
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )

            try:
                await asyncio.wait_for(process.wait(), timeout=duration_seconds + 5)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

            if not filepath.exists():
                return None

            # Get actual duration
            with wave.open(str(filepath), 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                actual_duration = frames / float(rate)

            # Calculate RMS level (proxy for audio energy)
            rms = self._calculate_rms(filepath)

            return AudioChunk(
                filepath=filepath,
                duration_seconds=actual_duration,
                timestamp=timestamp,
                rms_level=rms
            )

        except Exception as e:
            self._log_event('error', f'Audio recording failed: {e}')
            if filepath.exists():
                filepath.unlink()
            return None

    def _calculate_rms(self, filepath: Path) -> float:
        """Calculate RMS level of audio file."""
        try:
            with wave.open(str(filepath), 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                # Simple RMS calculation
                import struct
                count = len(frames) // 2
                shorts = struct.unpack(f'{count}h', frames)
                sum_squares = sum(s * s for s in shorts)
                return (sum_squares / count) ** 0.5 if count > 0 else 0
        except:
            return 0

    async def transcribe_audio(self, audio_chunk: AudioChunk) -> Optional[Dict]:
        """Transcribe audio using Whisper STT."""
        if not self.whisper_available:
            return None

        if audio_chunk.duration_seconds < MIN_AUDIO_LENGTH_SECONDS:
            return None

        if audio_chunk.rms_level < SILENCE_THRESHOLD:
            # Audio is mostly silence
            return None

        try:
            with open(audio_chunk.filepath, 'rb') as f:
                files = {'file': (audio_chunk.filepath.name, f, 'audio/wav')}
                data = {'model': 'whisper-1'}

                response = requests.post(
                    WHISPER_ENDPOINT,
                    files=files,
                    data=data,
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    transcript = result.get('text', '').strip()

                    if transcript:
                        return {
                            'transcript': transcript,
                            'duration': audio_chunk.duration_seconds,
                            'timestamp': audio_chunk.timestamp.isoformat(),
                            'language': result.get('language', 'unknown')
                        }

        except Exception as e:
            self._log_event('error', f'Transcription failed: {e}')

        return None

    def store_transcript(self, transcript_data: Dict) -> int:
        """Store transcript in database."""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("""
                INSERT INTO audio_transcripts
                (duration_seconds, transcript, language, insights_json)
                VALUES (?, ?, ?, ?)
            """, (
                transcript_data['duration'],
                transcript_data['transcript'],
                transcript_data.get('language', 'unknown'),
                json.dumps(transcript_data)
            ))
            conn.commit()
            return cursor.lastrowid

    def analyze_transcript(self, transcript: str) -> Dict:
        """Analyze transcript for insights."""
        # Simple keyword-based analysis
        insights = {
            'word_count': len(transcript.split()),
            'mentions_ai': any(kw in transcript.lower() for kw in ['ai', 'claude', 'assistant', 'agent']),
            'is_question': '?' in transcript,
            'is_command': any(transcript.lower().startswith(cmd) for cmd in ['hey', 'ok', 'please', 'can you']),
            'sentiment': 'neutral'  # Would use sentiment analysis in production
        }
        return insights

    def _log_event(self, event_type: str, description: str, metadata: Dict = None):
        """Log an audio event."""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO audio_events (event_type, description, metadata)
                VALUES (?, ?, ?)
            """, (event_type, description, json.dumps(metadata) if metadata else None))
            conn.commit()

    def cleanup_audio_files(self):
        """Delete all processed audio files to save space."""
        for audio_file in self.audio_dir.glob("*.wav"):
            try:
                audio_file.unlink()
            except:
                pass

    def get_recent_transcripts(self, limit: int = 10) -> List[Dict]:
        """Get recent transcripts."""
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM audio_transcripts
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(row) for row in rows]

    def get_status(self) -> Dict:
        """Get agent status."""
        with sqlite3.connect(DB_PATH) as conn:
            total_transcripts = conn.execute(
                "SELECT COUNT(*) FROM audio_transcripts"
            ).fetchone()[0]

            total_words = conn.execute(
                "SELECT COALESCE(SUM(LENGTH(transcript) - LENGTH(REPLACE(transcript, ' ', '')) + 1), 0) FROM audio_transcripts"
            ).fetchone()[0]

        # Check audio directory size
        audio_size_mb = sum(f.stat().st_size for f in self.audio_dir.glob("*")) / 1048576

        return {
            "node_id": self.node_id,
            "running": self.running,
            "sox_available": self.sox_available,
            "whisper_available": self.whisper_available,
            "total_transcripts": total_transcripts,
            "total_words_heard": total_words,
            "temp_audio_size_mb": round(audio_size_mb, 2),
            "settings": {
                "chunk_duration_sec": CHUNK_DURATION_SECONDS,
                "listen_interval_sec": LISTEN_INTERVAL_SECONDS
            }
        }

    async def run(self):
        """Main listening loop."""
        self.running = True
        print(f"Audio Awareness Agent starting on {self.node_id}")
        print(f"Listening in {CHUNK_DURATION_SECONDS}s chunks")
        print(f"Whisper STT: {WHISPER_ENDPOINT}")

        if not self.rec_available:
            print("ERROR: Audio recording not available. Install sox: brew install sox")
            return

        self._log_event('startup', f'Audio Awareness Agent started')

        try:
            while self.running:
                # Record audio chunk
                chunk = await self.record_audio(CHUNK_DURATION_SECONDS)

                if chunk:
                    # Transcribe
                    result = await self.transcribe_audio(chunk)

                    if result and result.get('transcript'):
                        # Analyze and store
                        insights = self.analyze_transcript(result['transcript'])
                        result['insights'] = insights

                        transcript_id = self.store_transcript(result)
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Heard: {result['transcript'][:100]}...")

                    # Clean up audio file immediately
                    if chunk.filepath.exists():
                        chunk.filepath.unlink()

                await asyncio.sleep(LISTEN_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.running = False
            self.cleanup_audio_files()
            self._log_event('shutdown', 'Audio Awareness Agent stopped')

    def stop(self):
        """Stop the agent."""
        self.running = False


async def main():
    """Main entry point."""
    agent = AudioAwarenessAgent()

    # Print initial status
    status = agent.get_status()
    print(f"\nInitial Status: {json.dumps(status, indent=2)}")

    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())

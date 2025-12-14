#!/usr/bin/env python3
"""
TPU Keyword Spotter - Edge TPU Accelerated Wake Word Detection

Provides fast (~35ms) keyword spotting using Google Coral Edge TPU.
Detects predefined keywords like "hey claude", "stop", "help", etc.

Uses subprocess to call coral-venv Python for pycoral access.

Integration with audio_perceiver.py and consciousness daemon.

Usage:
    from tpu_keyword_spotter import TPUKeywordSpotter

    spotter = TPUKeywordSpotter()
    if spotter.is_available:
        keywords = spotter.detect_keywords(audio_samples)
        if "hey_claude" in keywords:
            print("Wake word detected!")
"""
import platform

import os
import sys
import json
import time
import logging
import tempfile
import subprocess
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tpu_keyword_spotter")

# Paths
AGENTIC_SYSTEM_PATH = os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE))
CORAL_VENV_PYTHON = Path(f"{AGENTIC_SYSTEM_PATH}/coral-venv/bin/python")
CORAL_TPU_SRC = Path(f"{AGENTIC_SYSTEM_PATH}/mcp-servers/coral-tpu-mcp/src")
MODELS_DIR = Path(f"{AGENTIC_SYSTEM_PATH}/models/coral")

# Try to import tpu_monitor
try:
    sys.path.insert(0, os.path.join(AGENTIC_SYSTEM_PATH, "scripts/hooks"))
    from tpu_monitor import record_tpu_usage
    HAS_TPU_MONITOR = True
except ImportError:
    HAS_TPU_MONITOR = False

# Keyword labels from the EdgeTPU keyword spotter model
# These are the 12 keywords the model can detect
KEYWORD_LABELS = [
    "silence",      # 0 - Background silence
    "unknown",      # 1 - Unknown word
    "yes",          # 2
    "no",           # 3
    "up",           # 4
    "down",         # 5
    "left",         # 6
    "right",        # 7
    "on",           # 8
    "off",          # 9
    "stop",         # 10
    "go"            # 11
]

# Custom wake word mappings (map sequences to actions)
WAKE_WORD_PATTERNS = {
    "hey_claude": ["yes", "go"],  # "yes" followed by "go" = wake
    "stop_listening": ["stop"],   # Just "stop"
    "confirm": ["yes"],           # Just "yes"
    "deny": ["no"],               # Just "no"
}


@dataclass
class KeywordDetection:
    """Result of keyword detection"""
    keyword: str
    confidence: float
    timestamp_ms: float
    latency_ms: float


class TPUKeywordSpotter:
    """
    Edge TPU accelerated keyword spotting.

    Uses subprocess calls to coral-venv for pycoral access.
    Provides fast wake word detection for voice control.
    """

    def __init__(self, lazy_load: bool = True, sample_rate: int = 16000):
        """
        Initialize keyword spotter.

        Args:
            lazy_load: If True, TPU is checked on first use
            sample_rate: Audio sample rate (must be 16000Hz for model)
        """
        self._tpu_available: Optional[bool] = None
        self.sample_rate = sample_rate
        self.model_path = MODELS_DIR / "keyword_spotter_edgetpu.tflite"

        # Detection history for pattern matching
        self.recent_detections: List[KeywordDetection] = []
        self.max_history = 10
        self.pattern_window_ms = 2000  # 2 second window for patterns

        if not lazy_load:
            _ = self.is_available

    @property
    def is_available(self) -> bool:
        """Check if TPU is available for keyword spotting."""
        if self._tpu_available is not None:
            return self._tpu_available

        if not CORAL_VENV_PYTHON.exists():
            logger.info("coral-venv not found, TPU keyword spotting unavailable")
            self._tpu_available = False
            return False

        if not self.model_path.exists():
            logger.warning(f"Keyword spotter model not found: {self.model_path}")
            self._tpu_available = False
            return False

        try:
            result = subprocess.run(
                [str(CORAL_VENV_PYTHON), "-c",
                 "from pycoral.utils import edgetpu; print(len(edgetpu.list_edge_tpus()))"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and int(result.stdout.strip()) > 0:
                self._tpu_available = True
                logger.info("TPU keyword spotting available")
                return True
        except Exception as e:
            logger.warning(f"TPU check failed: {e}")

        self._tpu_available = False
        return False

    def _call_coral_keyword_spot(self, audio_path: str) -> Optional[Dict]:
        """
        Call coral-venv to run keyword spotting inference.

        Args:
            audio_path: Path to audio file (WAV, 16kHz, mono)

        Returns:
            Result dict with detections or None
        """
        if not self.is_available:
            return None

        code = f'''
import sys
import json
import time
import numpy as np
sys.path.insert(0, "{CORAL_TPU_SRC}")

try:
    import librosa
except ImportError:
    print(json.dumps({{"error": "librosa not available"}}))
    sys.exit(1)

from pycoral.utils import edgetpu
from pycoral.adapters import common

MODEL_PATH = "{self.model_path}"
AUDIO_PATH = "{audio_path}"

# Load model
interpreter = edgetpu.make_interpreter(MODEL_PATH)
interpreter.allocate_tensors()

# Get input details
input_details = interpreter.get_input_details()[0]
input_shape = input_details["shape"]

# Load audio
audio, sr = librosa.load(AUDIO_PATH, sr=16000, mono=True)

# Model expects specific input size (e.g., 1 second at 16kHz = 16000 samples)
# Typically uses mel spectrogram features
# For keyword_spotter model, input is usually (1, num_frames, num_mels, 1)

# Extract MFCC features (common for keyword spotting)
mfccs = librosa.feature.mfcc(y=audio, sr=16000, n_mfcc=40, hop_length=160, n_fft=480)

# Reshape to match model input
# Model typically expects (batch, time, features) or similar
expected_time = input_shape[1] if len(input_shape) > 1 else 98
expected_features = input_shape[2] if len(input_shape) > 2 else 40

# Pad or trim
if mfccs.shape[1] < expected_time:
    mfccs = np.pad(mfccs, ((0, 0), (0, expected_time - mfccs.shape[1])))
else:
    mfccs = mfccs[:, :expected_time]

# Reshape for model
if len(input_shape) == 4:
    input_data = mfccs.T.reshape(1, expected_time, expected_features, 1).astype(np.float32)
elif len(input_shape) == 3:
    input_data = mfccs.T.reshape(1, expected_time, expected_features).astype(np.float32)
else:
    input_data = mfccs.T.flatten().reshape(input_shape).astype(np.float32)

# Normalize
input_data = (input_data - input_data.mean()) / (input_data.std() + 1e-6)

# Run inference
common.set_input(interpreter, input_data)
start = time.perf_counter()
interpreter.invoke()
latency_ms = (time.perf_counter() - start) * 1000

# Get output
output_details = interpreter.get_output_details()[0]
output = interpreter.get_tensor(output_details["index"]).flatten()

# Apply softmax
output = np.exp(output) / np.sum(np.exp(output))

# Get top predictions
top_indices = np.argsort(output)[::-1][:3]

labels = {json.dumps(KEYWORD_LABELS)}
detections = []
for idx in top_indices:
    if output[idx] > 0.1:  # Threshold
        detections.append({{
            "keyword": labels[int(idx)] if int(idx) < len(labels) else f"class_{{idx}}",
            "confidence": float(output[idx]),
            "class_id": int(idx)
        }})

print(json.dumps({{
    "detections": detections,
    "latency_ms": latency_ms,
    "audio_duration_s": len(audio) / 16000
}}))
'''

        try:
            result = subprocess.run(
                [str(CORAL_VENV_PYTHON), "-c", code],
                capture_output=True, text=True, timeout=15,
                env={**os.environ, "PYTHONPATH": str(CORAL_TPU_SRC)}
            )

            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout.strip())
            else:
                if result.stderr:
                    logger.warning(f"Keyword spot stderr: {result.stderr[:300]}")
                return None

        except subprocess.TimeoutExpired:
            logger.warning("Keyword spotting timed out")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON from keyword spotter: {e}")
            return None
        except Exception as e:
            logger.warning(f"Keyword spotting failed: {e}")
            return None

    def _save_audio_temp(self, audio_samples: np.ndarray) -> Optional[str]:
        """Save audio samples to temporary WAV file."""
        try:
            import wave

            fd, path = tempfile.mkstemp(suffix='.wav')
            os.close(fd)

            # Ensure int16 format
            if audio_samples.dtype == np.float32 or audio_samples.dtype == np.float64:
                audio_samples = (audio_samples * 32767).astype(np.int16)
            elif audio_samples.dtype != np.int16:
                audio_samples = audio_samples.astype(np.int16)

            with wave.open(path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_samples.tobytes())

            return path
        except Exception as e:
            logger.error(f"Failed to save audio: {e}")
            return None

    def detect_keywords(
        self,
        audio_samples: np.ndarray,
        threshold: float = 0.5
    ) -> List[KeywordDetection]:
        """
        Detect keywords in audio samples.

        Args:
            audio_samples: Audio samples (int16 or float32, 16kHz mono)
            threshold: Minimum confidence threshold

        Returns:
            List of detected keywords above threshold
        """
        if not self.is_available:
            return []

        temp_path = self._save_audio_temp(audio_samples)
        if not temp_path:
            return []

        try:
            result = self._call_coral_keyword_spot(temp_path)

            if not result or "error" in result:
                return []

            detections = []
            current_time_ms = time.time() * 1000

            for det in result.get("detections", []):
                if det["confidence"] >= threshold:
                    # Skip silence and unknown
                    if det["keyword"] in ["silence", "unknown"]:
                        continue

                    detection = KeywordDetection(
                        keyword=det["keyword"],
                        confidence=det["confidence"],
                        timestamp_ms=current_time_ms,
                        latency_ms=result.get("latency_ms", 0)
                    )
                    detections.append(detection)

                    # Add to history
                    self.recent_detections.append(detection)

            # Trim history
            while len(self.recent_detections) > self.max_history:
                self.recent_detections.pop(0)

            # Record TPU usage
            if HAS_TPU_MONITOR and detections:
                record_tpu_usage(
                    "keyword_spotting",
                    latency_ms=result.get("latency_ms", 0),
                    source="keyword_spotter",
                    metadata={
                        "detected": [d.keyword for d in detections],
                        "threshold": threshold
                    }
                )

            return detections

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def check_wake_patterns(self) -> List[str]:
        """
        Check recent detections for wake word patterns.

        Returns:
            List of triggered pattern names
        """
        if not self.recent_detections:
            return []

        current_time_ms = time.time() * 1000
        window_start = current_time_ms - self.pattern_window_ms

        # Get recent keywords
        recent_keywords = [
            d.keyword for d in self.recent_detections
            if d.timestamp_ms >= window_start
        ]

        if not recent_keywords:
            return []

        triggered = []

        for pattern_name, pattern_keywords in WAKE_WORD_PATTERNS.items():
            # Check if pattern matches end of recent keywords
            if len(recent_keywords) >= len(pattern_keywords):
                if recent_keywords[-len(pattern_keywords):] == pattern_keywords:
                    triggered.append(pattern_name)

        return triggered

    def get_supported_keywords(self) -> List[str]:
        """Get list of supported keywords."""
        return [k for k in KEYWORD_LABELS if k not in ["silence", "unknown"]]

    def get_wake_patterns(self) -> Dict[str, List[str]]:
        """Get configured wake word patterns."""
        return WAKE_WORD_PATTERNS.copy()


# Singleton instance
_spotter: Optional[TPUKeywordSpotter] = None


def get_keyword_spotter() -> TPUKeywordSpotter:
    """Get or create singleton keyword spotter instance."""
    global _spotter
    if _spotter is None:
        _spotter = TPUKeywordSpotter()
    return _spotter


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TPU Keyword Spotter")
    parser.add_argument("--audio", type=str, help="Audio file to process")
    parser.add_argument("--record", type=float, default=0, help="Record N seconds from mic")
    parser.add_argument("--threshold", type=float, default=0.5, help="Detection threshold")

    args = parser.parse_args()

    spotter = TPUKeywordSpotter(lazy_load=False)
    print(f"TPU Available: {spotter.is_available}")
    print(f"Supported keywords: {spotter.get_supported_keywords()}")

    if args.audio:
        try:
            import librosa
            audio, sr = librosa.load(args.audio, sr=16000, mono=True)
            audio_int16 = (audio * 32767).astype(np.int16)

            print(f"\nProcessing: {args.audio}")
            detections = spotter.detect_keywords(audio_int16, args.threshold)

            print(f"Detections ({len(detections)}):")
            for d in detections:
                print(f"  - {d.keyword}: {d.confidence:.2f} ({d.latency_ms:.1f}ms)")

            patterns = spotter.check_wake_patterns()
            if patterns:
                print(f"Wake patterns triggered: {patterns}")

        except ImportError:
            print("librosa required: pip install librosa")

    elif args.record > 0:
        try:
            import sounddevice as sd

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

            print(f"\nRecording {args.record} seconds...")
            audio = sd.rec(int(args.record * 16000), samplerate=16000, channels=1, dtype='int16')
            sd.wait()
            audio = audio.flatten()

            print("Processing...")
            detections = spotter.detect_keywords(audio, args.threshold)

            print(f"Detections ({len(detections)}):")
            for d in detections:
                print(f"  - {d.keyword}: {d.confidence:.2f} ({d.latency_ms:.1f}ms)")

        except ImportError:
            print("sounddevice required: pip install sounddevice")

    else:
        print("\nUse --audio <file.wav> or --record <seconds> to test")

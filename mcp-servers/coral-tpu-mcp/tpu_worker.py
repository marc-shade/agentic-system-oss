#!/usr/bin/env python3
"""
TPU Worker - Python 3.9 subprocess for EdgeTPU inference.

This worker handles actual TPU operations and communicates via JSON over stdio.
The MCP server (Python 3.12) calls this subprocess for TPU inference.

Usage: python3.9 tpu_worker.py
"""

import sys
import json
import base64
import io
import time
import logging
from pathlib import Path

import numpy as np
from PIL import Image

# Configure logging to stderr (stdout reserved for JSON communication)
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s:%(name)s:%(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Try to import pycoral
try:
    from pycoral.utils import edgetpu
    from pycoral.adapters import common, classify
    PYCORAL_AVAILABLE = True
except ImportError:
    PYCORAL_AVAILABLE = False
    logger.warning("pycoral not available, using tflite_runtime directly")

# Fallback to tflite_runtime with EdgeTPU delegate
try:
    import tflite_runtime.interpreter as tflite
    TFLITE_AVAILABLE = True
except ImportError:
    TFLITE_AVAILABLE = False

MODELS_DIR = Path("/mnt/agentic-system/models/coral")

# Cached interpreters
_interpreters = {}


def get_interpreter(model_path: str, use_tpu: bool = True):
    """Get or create a TFLite interpreter."""
    cache_key = f"{model_path}:{use_tpu}"
    if cache_key not in _interpreters:
        if use_tpu:
            if PYCORAL_AVAILABLE:
                interp = edgetpu.make_interpreter(model_path)
            elif TFLITE_AVAILABLE:
                delegate = tflite.load_delegate('libedgetpu.so.1')
                interp = tflite.Interpreter(model_path, experimental_delegates=[delegate])
            else:
                raise RuntimeError("No TPU runtime available")
        else:
            interp = tflite.Interpreter(model_path)
        interp.allocate_tensors()
        _interpreters[cache_key] = interp
    return _interpreters[cache_key]


def list_tpus():
    """List available Edge TPUs."""
    if PYCORAL_AVAILABLE:
        return edgetpu.list_edge_tpus()
    elif TFLITE_AVAILABLE:
        try:
            delegate = tflite.load_delegate('libedgetpu.so.1')
            return [{"type": "usb", "status": "available"}]
        except:
            return []
    return []


def classify_image(model_name: str, image_b64: str, top_k: int = 5):
    """Classify an image using TPU."""
    model_path = str(MODELS_DIR / f"{model_name}_edgetpu.tflite")
    labels_path = MODELS_DIR / "imagenet_labels.txt"

    # Decode image
    image_data = base64.b64decode(image_b64)
    image = Image.open(io.BytesIO(image_data)).convert('RGB')

    # Get interpreter
    interp = get_interpreter(model_path)

    # Get input details
    input_details = interp.get_input_details()[0]
    input_shape = input_details['shape']
    height, width = input_shape[1], input_shape[2]

    # Resize and prepare input
    image = image.resize((width, height), Image.LANCZOS)
    input_data = np.array(image, dtype=np.uint8)
    input_data = np.expand_dims(input_data, axis=0)

    # Run inference
    start_time = time.time()
    interp.set_tensor(input_details['index'], input_data)
    interp.invoke()
    inference_time = (time.time() - start_time) * 1000

    # Get output
    output_details = interp.get_output_details()[0]
    output = interp.get_tensor(output_details['index'])[0]

    # Load labels
    labels = []
    if labels_path.exists():
        with open(labels_path) as f:
            labels = [line.strip() for line in f]

    # Get top-k results
    top_indices = np.argsort(output)[-top_k:][::-1]
    results = []
    for idx in top_indices:
        label = labels[idx] if idx < len(labels) else f"class_{idx}"
        score = float(output[idx]) / 255.0 if output.dtype == np.uint8 else float(output[idx])
        results.append({"label": label, "score": score})

    return {
        "results": results,
        "inference_time_ms": inference_time,
        "model": model_name
    }


def handle_command(cmd: dict) -> dict:
    """Handle a command from the MCP server."""
    action = cmd.get("action")

    try:
        if action == "ping":
            return {"status": "ok", "pycoral": PYCORAL_AVAILABLE, "tflite": TFLITE_AVAILABLE}

        elif action == "list_tpus":
            return {"tpus": list_tpus()}

        elif action == "classify":
            return classify_image(
                cmd.get("model", "mobilenet_v2"),
                cmd["image"],
                cmd.get("top_k", 5)
            )

        elif action == "status":
            tpus = list_tpus()
            return {
                "available": len(tpus) > 0,
                "tpus": tpus,
                "pycoral": PYCORAL_AVAILABLE,
                "tflite": TFLITE_AVAILABLE,
                "models_dir": str(MODELS_DIR),
                "models_exist": MODELS_DIR.exists()
            }

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        return {"error": str(e)}


def main():
    """Main loop - read JSON commands from stdin, write responses to stdout."""
    # Initial status message to stderr
    print(f"TPU Worker started (pycoral={PYCORAL_AVAILABLE}, tflite={TFLITE_AVAILABLE})", file=sys.stderr)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            cmd = json.loads(line)
            result = handle_command(cmd)
            print(json.dumps(result), flush=True)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"Invalid JSON: {e}"}), flush=True)
        except Exception as e:
            print(json.dumps({"error": str(e)}), flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
TOON Codec - Python wrapper for @toon-format/toon
Provides encode/decode functionality using Node.js CLI
"""

import json
import subprocess
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Path to TOON CLI (case-insensitive for macOS)
_parent = Path(__file__).parent
if not _parent.exists():
    # Handle case-sensitivity issues
    _parent_str = str(_parent)
    if _parent_str.endswith("SHARED"):
        _parent = Path(_parent_str.replace("SHARED", "shared"))
    elif _parent_str.endswith("shared"):
        _parent = Path(_parent_str.replace("shared", "SHARED"))

TOON_CLI_PATH = _parent / "node_modules" / "@toon-format" / "cli" / "bin" / "toon.mjs"
NODE_PATH = os.popen("which node").read().strip()


class ToonCodec:
    """TOON encoder/decoder using Node.js CLI"""

    def __init__(self):
        """Initialize TOON codec"""
        if not TOON_CLI_PATH.exists():
            raise RuntimeError(
                f"TOON CLI not found at {TOON_CLI_PATH}. "
                "Run: cd /Volumes/SSDRAID0/agentic-system/mcp-servers/shared && "
                "npm install @toon-format/toon @toon-format/cli"
            )
        if not NODE_PATH:
            raise RuntimeError("Node.js not found in PATH")

    def encode(self, data: Any, pretty: bool = False) -> str:
        """
        Encode Python object to TOON format

        Args:
            data: Python object (dict, list, str, int, etc.)
            pretty: Enable pretty-printing with indentation

        Returns:
            TOON-encoded string
        """
        try:
            # Convert Python object to JSON
            json_str = json.dumps(data, ensure_ascii=False)

            # Call TOON CLI with stdin input
            cmd = [NODE_PATH, str(TOON_CLI_PATH), "--encode", "-"]
            if pretty:
                cmd.extend(["--indent", "2"])

            result = subprocess.run(
                cmd,
                input=json_str,
                capture_output=True,
                text=True,
                check=True
            )

            return result.stdout.strip()

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"TOON encoding failed: {e.stderr}")
        except Exception as e:
            raise RuntimeError(f"TOON encoding error: {str(e)}")

    def decode(self, toon_str: str) -> Any:
        """
        Decode TOON format to Python object

        Args:
            toon_str: TOON-encoded string

        Returns:
            Python object (dict, list, str, int, etc.)
        """
        try:
            # Call TOON CLI with stdin input
            cmd = [NODE_PATH, str(TOON_CLI_PATH), "--decode", "-"]

            result = subprocess.run(
                cmd,
                input=toon_str,
                capture_output=True,
                text=True,
                check=True
            )

            # Parse JSON output
            return json.loads(result.stdout)

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"TOON decoding failed: {e.stderr}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"TOON decode JSON parse error: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"TOON decoding error: {str(e)}")

    def validate(self, toon_str: str) -> bool:
        """
        Validate TOON format string

        Args:
            toon_str: TOON-encoded string

        Returns:
            True if valid, False otherwise
        """
        try:
            self.decode(toon_str)
            return True
        except:
            return False

    def get_compression_ratio(self, data: Any) -> Dict[str, Any]:
        """
        Calculate compression ratio of TOON vs JSON

        Args:
            data: Python object to encode

        Returns:
            Dict with json_size, toon_size, ratio, tokens_saved
        """
        json_str = json.dumps(data, ensure_ascii=False)
        toon_str = self.encode(data)

        json_size = len(json_str)
        toon_size = len(toon_str)
        ratio = json_size / toon_size if toon_size > 0 else 1.0

        # Rough token estimate (1 token ≈ 4 chars)
        json_tokens = json_size / 4
        toon_tokens = toon_size / 4
        tokens_saved = json_tokens - toon_tokens

        return {
            "json_size": json_size,
            "toon_size": toon_size,
            "ratio": round(ratio, 2),
            "tokens_saved": round(tokens_saved, 1),
            "reduction_percent": round((1 - toon_size/json_size) * 100, 1)
        }


# Global codec instance
_codec = None

def get_codec() -> ToonCodec:
    """Get or create global TOON codec instance"""
    global _codec
    if _codec is None:
        _codec = ToonCodec()
    return _codec


# Convenience functions
def encode(data: Any, pretty: bool = False) -> str:
    """Encode data to TOON format"""
    return get_codec().encode(data, pretty)


def decode(toon_str: str) -> Any:
    """Decode TOON format to Python object"""
    return get_codec().decode(toon_str)


def validate(toon_str: str) -> bool:
    """Validate TOON format string"""
    return get_codec().validate(toon_str)


def compression_ratio(data: Any) -> Dict[str, Any]:
    """Calculate TOON vs JSON compression ratio"""
    return get_codec().get_compression_ratio(data)

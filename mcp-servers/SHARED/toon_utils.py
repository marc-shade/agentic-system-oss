#!/usr/bin/env python3
"""
TOON Utilities for MCP Servers
Shared helpers for TOON-encoded MCP responses using @toon-format/toon
"""

import json
from typing import Any, Dict, List, Optional, Union
try:
    from . import toon_codec
except ImportError:
    import toon_codec


def toon_response(data: Any, error: Optional[str] = None, metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Create MCP response with TOON-encoded content

    Args:
        data: Response data to encode
        error: Optional error message
        metadata: Optional metadata dict

    Returns:
        MCP response dict with TOON content
    """
    response = {
        "content": [
            {
                "type": "text",
                "text": toon_codec.encode(data)
            }
        ]
    }

    if error:
        response["isError"] = True
        response["error"] = error

    if metadata:
        # Add metadata as TOON-encoded annotation
        response["content"].append({
            "type": "text",
            "text": f"\n\n// Metadata\n{toon_codec.encode(metadata)}",
            "annotations": {"role": "metadata"}
        })

    return response


def encode_with_fallback(data: Any, pretty: bool = False) -> str:
    """
    Encode data with TOON, fallback to JSON on error

    Args:
        data: Data to encode
        pretty: Enable pretty-printing

    Returns:
        TOON-encoded string, or JSON if TOON fails
    """
    try:
        return toon_codec.encode(data, pretty)
    except Exception as e:
        # Fallback to JSON
        if pretty:
            return json.dumps(data, indent=2, ensure_ascii=False)
        else:
            return json.dumps(data, ensure_ascii=False)


def smart_decode(text: str) -> Any:
    """
    Auto-detect and decode TOON or JSON format

    Args:
        text: TOON or JSON encoded string

    Returns:
        Decoded Python object
    """
    text = text.strip()

    # Try TOON first (check for TOON markers)
    if any(marker in text[:50] for marker in ['[', '{', ':', '=']):
        try:
            return toon_codec.decode(text)
        except:
            pass

    # Fallback to JSON
    try:
        return json.loads(text)
    except:
        raise ValueError(f"Failed to decode as TOON or JSON: {text[:100]}...")


def batch_encode(items: List[Any], pretty: bool = False) -> List[str]:
    """
    Encode multiple items to TOON format

    Args:
        items: List of items to encode
        pretty: Enable pretty-printing

    Returns:
        List of TOON-encoded strings
    """
    return [toon_codec.encode(item, pretty) for item in items]


def batch_decode(toon_strings: List[str]) -> List[Any]:
    """
    Decode multiple TOON strings

    Args:
        toon_strings: List of TOON-encoded strings

    Returns:
        List of decoded Python objects
    """
    return [toon_codec.decode(s) for s in toon_strings]


def compare_encodings(data: Any) -> Dict[str, Any]:
    """
    Compare TOON vs JSON encoding for data

    Args:
        data: Data to compare

    Returns:
        Dict with comparison metrics
    """
    json_str = json.dumps(data, ensure_ascii=False)
    json_pretty = json.dumps(data, indent=2, ensure_ascii=False)
    toon_str = toon_codec.encode(data)
    toon_pretty = toon_codec.encode(data, pretty=True)

    return {
        "json": {
            "compact": len(json_str),
            "pretty": len(json_pretty),
            "sample": json_str[:100] + "..." if len(json_str) > 100 else json_str
        },
        "toon": {
            "compact": len(toon_str),
            "pretty": len(toon_pretty),
            "sample": toon_str[:100] + "..." if len(toon_str) > 100 else toon_str
        },
        "compression": toon_codec.compression_ratio(data),
        "winner": "TOON" if len(toon_str) < len(json_str) else "JSON"
    }


def mcp_tool_response(
    tool_name: str,
    result: Any,
    format: str = "toon",
    include_stats: bool = True
) -> Dict[str, Any]:
    """
    Create standardized MCP tool response

    Args:
        tool_name: Name of the tool
        result: Tool execution result
        format: "toon" or "json" (default: "toon")
        include_stats: Include compression stats

    Returns:
        MCP tool response dict
    """
    if format == "toon":
        encoded = toon_codec.encode(result)
    else:
        encoded = json.dumps(result, ensure_ascii=False)

    response = {
        "content": [
            {
                "type": "text",
                "text": encoded
            }
        ]
    }

    if include_stats and format == "toon":
        stats = toon_codec.compression_ratio(result)
        response["_meta"] = {
            "tool": tool_name,
            "encoding": "toon",
            "compression": f"{stats['reduction_percent']}% smaller",
            "tokens_saved": stats['tokens_saved']
        }

    return response


def detect_format(text: str) -> str:
    """
    Detect if text is TOON or JSON format

    Args:
        text: Encoded text

    Returns:
        "toon", "json", or "unknown"
    """
    text = text.strip()

    # JSON typically starts with { or [
    if text.startswith('{') or text.startswith('['):
        try:
            json.loads(text)
            return "json"
        except:
            pass

    # Try TOON decode
    try:
        toon_codec.decode(text)
        return "toon"
    except:
        pass

    return "unknown"


def optimize_mcp_payload(data: Any, threshold: int = 1000) -> Dict[str, Any]:
    """
    Optimize MCP payload by choosing best encoding

    Args:
        data: Data to encode
        threshold: Size threshold for using TOON (chars)

    Returns:
        Dict with optimized encoding and metadata
    """
    json_size = len(json.dumps(data, ensure_ascii=False))

    # For small payloads, JSON is fine
    if json_size < threshold:
        return {
            "encoding": "json",
            "content": json.dumps(data, ensure_ascii=False),
            "size": json_size,
            "reason": "payload too small for TOON optimization"
        }

    # For larger payloads, use TOON
    toon_str = toon_codec.encode(data)
    stats = toon_codec.compression_ratio(data)

    return {
        "encoding": "toon",
        "content": toon_str,
        "size": len(toon_str),
        "json_size": json_size,
        "tokens_saved": stats['tokens_saved'],
        "reduction": f"{stats['reduction_percent']}%",
        "reason": "TOON optimization applied"
    }

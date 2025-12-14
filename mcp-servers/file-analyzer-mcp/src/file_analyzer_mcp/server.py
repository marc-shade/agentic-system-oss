#!/usr/bin/env python3
"""
File Analyzer MCP Server

Identifies files by magic numbers, calculates hashes, and detects
extension mismatches that may indicate malware disguise attempts.
"""

import asyncio
import hashlib
import json
import logging
import math
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

# Configure logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("file-analyzer-mcp")

mcp = FastMCP("file-analyzer")

# Magic number signatures (first bytes -> file type)
MAGIC_SIGNATURES = {
    # Executables
    b'\x4D\x5A': {'type': 'executable', 'name': 'PE Executable (EXE/DLL)', 'extensions': ['.exe', '.dll', '.sys', '.scr']},
    b'\x7F\x45\x4C\x46': {'type': 'executable', 'name': 'ELF Binary', 'extensions': ['.elf', '.so', '.bin', '']},
    b'\xCA\xFE\xBA\xBE': {'type': 'executable', 'name': 'Mach-O Binary (macOS)', 'extensions': ['', '.dylib']},
    b'\xCF\xFA\xED\xFE': {'type': 'executable', 'name': 'Mach-O 64-bit', 'extensions': ['', '.dylib']},
    b'\xFE\xED\xFA\xCE': {'type': 'executable', 'name': 'Mach-O 32-bit', 'extensions': ['', '.dylib']},

    # Scripts (check first bytes)
    b'#!': {'type': 'script', 'name': 'Shell/Script', 'extensions': ['.sh', '.py', '.pl', '.rb']},
    b'<?php': {'type': 'script', 'name': 'PHP Script', 'extensions': ['.php']},

    # Documents
    b'%PDF': {'type': 'document', 'name': 'PDF Document', 'extensions': ['.pdf']},
    b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1': {'type': 'document', 'name': 'MS Office (OLE)', 'extensions': ['.doc', '.xls', '.ppt', '.msg']},
    b'PK\x03\x04': {'type': 'archive', 'name': 'ZIP/Office XML', 'extensions': ['.zip', '.docx', '.xlsx', '.pptx', '.jar', '.apk']},

    # Archives
    b'\x1F\x8B': {'type': 'archive', 'name': 'GZIP', 'extensions': ['.gz', '.tgz']},
    b'BZh': {'type': 'archive', 'name': 'BZIP2', 'extensions': ['.bz2']},
    b'\xFD\x37\x7A\x58\x5A\x00': {'type': 'archive', 'name': 'XZ', 'extensions': ['.xz']},
    b'Rar!\x1A\x07': {'type': 'archive', 'name': 'RAR', 'extensions': ['.rar']},
    b'7z\xBC\xAF\x27\x1C': {'type': 'archive', 'name': '7-Zip', 'extensions': ['.7z']},
    b'\x75\x73\x74\x61\x72': {'type': 'archive', 'name': 'TAR', 'extensions': ['.tar']},

    # Images
    b'\xFF\xD8\xFF': {'type': 'image', 'name': 'JPEG', 'extensions': ['.jpg', '.jpeg']},
    b'\x89PNG\r\n\x1A\n': {'type': 'image', 'name': 'PNG', 'extensions': ['.png']},
    b'GIF87a': {'type': 'image', 'name': 'GIF87', 'extensions': ['.gif']},
    b'GIF89a': {'type': 'image', 'name': 'GIF89', 'extensions': ['.gif']},
    b'BM': {'type': 'image', 'name': 'BMP', 'extensions': ['.bmp']},
    b'RIFF': {'type': 'media', 'name': 'RIFF (AVI/WAV/WebP)', 'extensions': ['.avi', '.wav', '.webp']},

    # Media
    b'\x00\x00\x00\x1CftypM4A': {'type': 'media', 'name': 'M4A Audio', 'extensions': ['.m4a']},
    b'\x00\x00\x00\x20ftypisom': {'type': 'media', 'name': 'MP4 Video', 'extensions': ['.mp4']},
    b'\x00\x00\x00\x18ftypmp42': {'type': 'media', 'name': 'MP4 Video', 'extensions': ['.mp4']},
    b'ID3': {'type': 'media', 'name': 'MP3 (ID3)', 'extensions': ['.mp3']},
    b'\xFF\xFB': {'type': 'media', 'name': 'MP3', 'extensions': ['.mp3']},
    b'OggS': {'type': 'media', 'name': 'OGG', 'extensions': ['.ogg', '.oga', '.ogv']},
    b'fLaC': {'type': 'media', 'name': 'FLAC', 'extensions': ['.flac']},

    # Web
    b'<!DOCTYPE html': {'type': 'web', 'name': 'HTML', 'extensions': ['.html', '.htm']},
    b'<html': {'type': 'web', 'name': 'HTML', 'extensions': ['.html', '.htm']},
    b'<?xml': {'type': 'data', 'name': 'XML', 'extensions': ['.xml', '.svg']},

    # Data
    b'SQLite format 3': {'type': 'database', 'name': 'SQLite', 'extensions': ['.db', '.sqlite', '.sqlite3']},

    # Certificates/Keys
    b'-----BEGIN CERTIFICATE': {'type': 'certificate', 'name': 'PEM Certificate', 'extensions': ['.pem', '.crt']},
    b'-----BEGIN PRIVATE KEY': {'type': 'key', 'name': 'Private Key', 'extensions': ['.pem', '.key']},
    b'-----BEGIN RSA PRIVATE': {'type': 'key', 'name': 'RSA Private Key', 'extensions': ['.pem', '.key']},
}

# Dangerous file types
DANGEROUS_TYPES = ['executable', 'script']
SUSPICIOUS_EXTENSIONS = ['.txt', '.pdf', '.doc', '.jpg', '.png', '.gif', '.mp3', '.mp4']


def read_file_header(file_path: str, num_bytes: int = 32) -> bytes:
    """Read first N bytes of a file."""
    with open(file_path, 'rb') as f:
        return f.read(num_bytes)


def identify_by_magic(header: bytes) -> dict:
    """Identify file type by magic bytes."""
    for magic, info in MAGIC_SIGNATURES.items():
        if header.startswith(magic):
            return {
                'identified': True,
                'magic_bytes': magic.hex(),
                **info
            }

    # Check for text content
    try:
        header.decode('utf-8')
        return {
            'identified': True,
            'type': 'text',
            'name': 'Text/ASCII',
            'extensions': ['.txt', '.md', '.csv', '.json', '.yaml', '.log']
        }
    except:
        pass

    return {
        'identified': False,
        'type': 'unknown',
        'name': 'Unknown binary',
        'extensions': []
    }


def calculate_hashes(file_path: str) -> dict:
    """Calculate MD5, SHA1, and SHA256 hashes."""
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()

    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5.update(chunk)
            sha1.update(chunk)
            sha256.update(chunk)

    return {
        'md5': md5.hexdigest(),
        'sha1': sha1.hexdigest(),
        'sha256': sha256.hexdigest()
    }


def calculate_entropy(data: bytes) -> float:
    """Calculate Shannon entropy of data."""
    if not data:
        return 0.0

    counter = Counter(data)
    length = len(data)
    entropy = 0.0

    for count in counter.values():
        probability = count / length
        entropy -= probability * math.log2(probability)

    return entropy


@mcp.tool()
async def identify_file(file_path: str) -> str:
    """
    Identify a file's true type using magic number analysis.

    Args:
        file_path: Path to the file to analyze

    Returns:
        JSON with file type identification, magic bytes, and metadata
    """
    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        return json.dumps({"success": False, "error": f"File not found: {file_path}"})

    if not path.is_file():
        return json.dumps({"success": False, "error": "Not a regular file"})

    try:
        header = read_file_header(str(path))
        file_info = identify_by_magic(header)

        extension = path.suffix.lower()
        size = path.stat().st_size

        result = {
            "success": True,
            "file_path": str(path),
            "file_name": path.name,
            "extension": extension,
            "size_bytes": size,
            "size_human": f"{size / 1024:.1f} KB" if size < 1024*1024 else f"{size / (1024*1024):.1f} MB",
            "magic_analysis": file_info,
            "header_hex": header[:16].hex(),
            "header_ascii": ''.join(chr(b) if 32 <= b < 127 else '.' for b in header[:16])
        }

        # Check for extension mismatch
        if file_info['identified'] and file_info.get('extensions'):
            expected_exts = file_info['extensions']
            if extension and extension not in expected_exts and '' not in expected_exts:
                result['extension_mismatch'] = True
                result['expected_extensions'] = expected_exts
                result['warning'] = f"Extension mismatch: File appears to be {file_info['name']} but has {extension} extension"

                # High alert for dangerous types disguised as safe files
                if file_info['type'] in DANGEROUS_TYPES and extension in SUSPICIOUS_EXTENSIONS:
                    result['alert'] = "CRITICAL: Executable disguised as safe file type!"
                    result['threat_level'] = 'critical'

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
async def calculate_file_hashes(file_path: str) -> str:
    """
    Calculate MD5, SHA1, and SHA256 hashes of a file.

    Args:
        file_path: Path to the file

    Returns:
        JSON with hash values
    """
    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        return json.dumps({"success": False, "error": "File not found"})

    try:
        hashes = calculate_hashes(str(path))
        return json.dumps({
            "success": True,
            "file_path": str(path),
            "file_name": path.name,
            "size_bytes": path.stat().st_size,
            "hashes": hashes
        }, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
async def analyze_entropy(file_path: str) -> str:
    """
    Analyze file entropy to detect encryption or packing.

    High entropy (>7.0) may indicate:
    - Encrypted content
    - Compressed/packed executables
    - Random data

    Args:
        file_path: Path to the file

    Returns:
        JSON with entropy analysis
    """
    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        return json.dumps({"success": False, "error": "File not found"})

    try:
        with open(path, 'rb') as f:
            data = f.read(1024 * 1024)  # First 1MB

        entropy = calculate_entropy(data)

        assessment = "normal"
        if entropy > 7.5:
            assessment = "very_high - likely encrypted or compressed"
        elif entropy > 7.0:
            assessment = "high - possibly packed or encrypted"
        elif entropy > 6.0:
            assessment = "elevated - may contain compressed sections"
        elif entropy < 1.0:
            assessment = "very_low - sparse or repetitive data"

        return json.dumps({
            "success": True,
            "file_path": str(path),
            "entropy": round(entropy, 4),
            "max_entropy": 8.0,
            "assessment": assessment,
            "bytes_analyzed": len(data)
        }, indent=2)

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
async def scan_directory(
    directory: str,
    recursive: bool = True,
    check_mismatches: bool = True,
    max_files: int = 1000
) -> str:
    """
    Scan a directory for files with suspicious characteristics.

    Args:
        directory: Path to scan
        recursive: Scan subdirectories
        check_mismatches: Check for extension mismatches
        max_files: Maximum files to scan

    Returns:
        JSON with scan results including suspicious files
    """
    dir_path = Path(directory).expanduser().resolve()

    if not dir_path.exists():
        return json.dumps({"success": False, "error": "Directory not found"})

    results = {
        "success": True,
        "directory": str(dir_path),
        "scanned_at": datetime.now().isoformat(),
        "files_scanned": 0,
        "suspicious_files": [],
        "by_type": {},
        "errors": []
    }

    pattern = '**/*' if recursive else '*'

    for file_path in dir_path.glob(pattern):
        if results["files_scanned"] >= max_files:
            results["truncated"] = True
            break

        if not file_path.is_file():
            continue

        results["files_scanned"] += 1

        try:
            header = read_file_header(str(file_path), 32)
            file_info = identify_by_magic(header)
            extension = file_path.suffix.lower()

            # Track by type
            file_type = file_info.get('type', 'unknown')
            results["by_type"][file_type] = results["by_type"].get(file_type, 0) + 1

            # Check for suspicious files
            suspicious = None

            if check_mismatches and file_info['identified']:
                expected_exts = file_info.get('extensions', [])
                if extension and expected_exts and extension not in expected_exts and '' not in expected_exts:
                    suspicious = {
                        "file": str(file_path),
                        "reason": "extension_mismatch",
                        "detected_type": file_info['name'],
                        "extension": extension,
                        "expected_extensions": expected_exts
                    }

                    # Critical if executable disguised
                    if file_info['type'] in DANGEROUS_TYPES and extension in SUSPICIOUS_EXTENSIONS:
                        suspicious["threat_level"] = "critical"
                        suspicious["alert"] = "Executable disguised as safe file!"

            if suspicious:
                results["suspicious_files"].append(suspicious)

        except Exception as e:
            results["errors"].append({"file": str(file_path), "error": str(e)})

    results["suspicious_count"] = len(results["suspicious_files"])

    return json.dumps(results, indent=2)


@mcp.tool()
async def check_file_reputation(file_path: str) -> str:
    """
    Check a file's hash against threat intelligence.

    Calculates hashes and provides guidance for manual checks.

    Args:
        file_path: Path to the file

    Returns:
        JSON with hashes and reputation check guidance
    """
    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        return json.dumps({"success": False, "error": "File not found"})

    try:
        hashes = calculate_hashes(str(path))
        header = read_file_header(str(path))
        file_info = identify_by_magic(header)

        return json.dumps({
            "success": True,
            "file_path": str(path),
            "file_name": path.name,
            "size_bytes": path.stat().st_size,
            "detected_type": file_info.get('name', 'Unknown'),
            "hashes": hashes,
            "reputation_links": {
                "virustotal": f"https://www.virustotal.com/gui/file/{hashes['sha256']}",
                "hybrid_analysis": f"https://www.hybrid-analysis.com/search?query={hashes['sha256']}",
                "malwarebazaar": f"https://bazaar.abuse.ch/sample/{hashes['sha256']}/",
            },
            "note": "Use threat-intel MCP check_hash_reputation tool for automated lookup with API key"
        }, indent=2)

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
async def get_magic_signatures() -> str:
    """
    Get list of all supported magic number signatures.

    Returns:
        JSON with all recognized file signatures
    """
    signatures = []
    for magic, info in MAGIC_SIGNATURES.items():
        signatures.append({
            "magic_hex": magic.hex(),
            "magic_preview": ''.join(chr(b) if 32 <= b < 127 else '.' for b in magic[:8]),
            **info
        })

    return json.dumps({
        "success": True,
        "total_signatures": len(signatures),
        "signatures": signatures
    }, indent=2)


# Import password analyzer tools
try:
    from .password_analyzer import (
        analyze_password,
        analyze_password_policy,
        generate_password_requirements
    )
except ImportError:
    from password_analyzer import (
        analyze_password,
        analyze_password_policy,
        generate_password_requirements
    )

# Register password tools
mcp.tool()(analyze_password)
mcp.tool()(analyze_password_policy)
mcp.tool()(generate_password_requirements)


def main():
    """Entry point."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

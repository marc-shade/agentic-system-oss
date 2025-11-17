#!/usr/bin/env python3
"""
Code Transfer Manager for GitMQ Cluster
========================================

Handles code and file transfer between nodes with automatic transport selection
based on file size and type.

Transport Methods:
- Inline (< 50KB): Base64-encoded in Git commit message
- Git LFS (50KB - 10MB): Git Large File Storage
- Chunked (> 10MB): Split into 5MB chunks, transferred via LFS

Features:
- Automatic transport selection based on size
- Checksum verification (SHA256)
- Compression (Zstandard for >1KB files)
- Dependency bundling
- Retry logic with exponential backoff

Usage:
    manager = CodeTransferManager(repo_path="/path/to/repo")

    # Prepare code for transmission
    payload = manager.prepare_code_payload(code_path)

    # Receive and reconstruct code
    code_file = manager.receive_code(payload, target_path)
"""

import base64
import hashlib
import json
import logging
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False
    logging.warning("zstandard not installed, compression disabled")

logger = logging.getLogger(__name__)


class TransferMethod(str, Enum):
    """Code transfer method based on file size."""
    INLINE = "inline"           # < 50KB: Base64 in commit
    GIT_LFS = "git_lfs"        # 50KB - 10MB: Git LFS
    CHUNKED = "chunked"        # > 10MB: Chunked LFS
    EXTERNAL = "external"      # > 100MB: External storage (S3/MinIO)


class CompressionType(str, Enum):
    """Compression algorithms."""
    NONE = "none"
    ZSTD = "zstd"      # Preferred: Fast + high ratio
    GZIP = "gzip"      # Fallback: Widely available


@dataclass
class CodePayload:
    """
    Code transfer payload with metadata.

    All code transfers include:
    - Transfer method (inline, lfs, chunked)
    - Original file metadata
    - Checksum for integrity
    - Compression info
    """
    transfer_method: TransferMethod
    filename: str
    original_size: int
    compressed_size: int
    checksum: str  # SHA256 of original file
    compression: CompressionType

    # Method-specific data
    inline_data: Optional[str] = None  # Base64 for inline
    lfs_path: Optional[str] = None     # LFS path
    chunk_info: Optional[Dict[str, Any]] = None  # Chunk metadata

    # Code metadata
    language: Optional[str] = None
    dependencies: List[str] = None
    entry_point: Optional[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class CodeTransferManager:
    """
    Manages code transfer between cluster nodes.

    Automatically selects optimal transport method based on file size:
    - Small files (< 50KB): Inline in commit message
    - Medium files (50KB - 10MB): Git LFS
    - Large files (> 10MB): Chunked transfer
    - Huge files (> 100MB): External storage
    """

    # Size thresholds
    INLINE_THRESHOLD = 50_000       # 50 KB
    LFS_THRESHOLD = 10_000_000      # 10 MB
    CHUNKED_THRESHOLD = 100_000_000 # 100 MB
    CHUNK_SIZE = 5_000_000          # 5 MB chunks

    # Compression threshold (compress if > 1KB)
    COMPRESSION_THRESHOLD = 1024

    def __init__(self, repo_path: Optional[Path] = None):
        """
        Initialize code transfer manager.

        Args:
            repo_path: Path to Git repository (default: ~/agentic-system/agentic-cluster-comms)
        """
        if repo_path is None:
            repo_path = Path.home() / "agentic-system" / "agentic-cluster-comms"

        self.repo_path = Path(repo_path)
        self.lfs_dir = self.repo_path / "lfs-objects"
        self.lfs_dir.mkdir(parents=True, exist_ok=True)

        # Check if Git LFS is available
        self.git_lfs_available = self._check_git_lfs()

        logger.info(f"Code transfer manager initialized")
        logger.info(f"Repository: {self.repo_path}")
        logger.info(f"Git LFS available: {self.git_lfs_available}")
        logger.info(f"Zstandard available: {ZSTD_AVAILABLE}")

    def _check_git_lfs(self) -> bool:
        """Check if Git LFS is installed and initialized."""
        try:
            result = subprocess.run(
                ["git", "lfs", "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _compute_checksum(self, file_path: Path) -> str:
        """Compute SHA256 checksum of file."""
        sha256 = hashlib.sha256()

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)

        return sha256.hexdigest()

    def _compress_data(self, data: bytes) -> Tuple[bytes, CompressionType]:
        """
        Compress data using best available algorithm.

        Returns:
            (compressed_data, compression_type)
        """
        if len(data) < self.COMPRESSION_THRESHOLD:
            return data, CompressionType.NONE

        if ZSTD_AVAILABLE:
            # Zstandard: Fast + excellent compression
            compressor = zstd.ZstdCompressor(level=3)
            compressed = compressor.compress(data)

            # Only use if we got >5% compression
            if len(compressed) < len(data) * 0.95:
                return compressed, CompressionType.ZSTD

        # Fallback: gzip (always available)
        import gzip
        compressed = gzip.compress(data, compresslevel=6)

        if len(compressed) < len(data) * 0.95:
            return compressed, CompressionType.GZIP

        # No benefit from compression
        return data, CompressionType.NONE

    def _decompress_data(self, data: bytes, compression: CompressionType) -> bytes:
        """Decompress data based on compression type."""
        if compression == CompressionType.NONE:
            return data

        elif compression == CompressionType.ZSTD:
            if not ZSTD_AVAILABLE:
                raise RuntimeError("Zstandard decompression required but not available")
            decompressor = zstd.ZstdDecompressor()
            return decompressor.decompress(data)

        elif compression == CompressionType.GZIP:
            import gzip
            return gzip.decompress(data)

        else:
            raise ValueError(f"Unknown compression type: {compression}")

    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension."""
        extension_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".sh": "bash",
            ".bash": "bash",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".hpp": "cpp",
        }

        return extension_map.get(file_path.suffix.lower(), "unknown")

    def prepare_code_payload(
        self,
        code_path: Path,
        dependencies: Optional[List[str]] = None,
        entry_point: Optional[str] = None
    ) -> CodePayload:
        """
        Prepare code for transfer to another node.

        Automatically selects optimal transfer method based on file size.

        Args:
            code_path: Path to code file
            dependencies: Optional list of dependencies
            entry_point: Optional entry point filename

        Returns:
            CodePayload ready for transmission
        """
        if not code_path.exists():
            raise FileNotFoundError(f"Code file not found: {code_path}")

        # Get file info
        file_size = code_path.stat().st_size
        checksum = self._compute_checksum(code_path)
        language = self._detect_language(code_path)

        logger.info(f"Preparing code transfer: {code_path.name} ({file_size:,} bytes)")

        # Read and potentially compress
        with open(code_path, "rb") as f:
            original_data = f.read()

        compressed_data, compression = self._compress_data(original_data)
        compressed_size = len(compressed_data)

        if compression != CompressionType.NONE:
            ratio = (1 - compressed_size / file_size) * 100
            logger.info(f"Compressed: {file_size:,} → {compressed_size:,} bytes ({ratio:.1f}% reduction)")

        # Select transfer method based on size
        if compressed_size < self.INLINE_THRESHOLD:
            # Small file: Inline in commit message
            method = TransferMethod.INLINE
            inline_data = base64.b64encode(compressed_data).decode('ascii')

            payload = CodePayload(
                transfer_method=method,
                filename=code_path.name,
                original_size=file_size,
                compressed_size=compressed_size,
                checksum=checksum,
                compression=compression,
                inline_data=inline_data,
                language=language,
                dependencies=dependencies or [],
                entry_point=entry_point
            )

            logger.info(f"Transfer method: INLINE (base64: {len(inline_data)} chars)")

        elif compressed_size < self.LFS_THRESHOLD:
            # Medium file: Git LFS
            method = TransferMethod.GIT_LFS

            # Store in LFS directory
            lfs_path = self._store_in_lfs(compressed_data, code_path.name, checksum)

            payload = CodePayload(
                transfer_method=method,
                filename=code_path.name,
                original_size=file_size,
                compressed_size=compressed_size,
                checksum=checksum,
                compression=compression,
                lfs_path=str(lfs_path.relative_to(self.repo_path)),
                language=language,
                dependencies=dependencies or [],
                entry_point=entry_point
            )

            logger.info(f"Transfer method: GIT_LFS (path: {payload.lfs_path})")

        elif compressed_size < self.CHUNKED_THRESHOLD:
            # Large file: Chunked transfer
            method = TransferMethod.CHUNKED

            chunk_info = self._create_chunks(compressed_data, code_path.name, checksum)

            payload = CodePayload(
                transfer_method=method,
                filename=code_path.name,
                original_size=file_size,
                compressed_size=compressed_size,
                checksum=checksum,
                compression=compression,
                chunk_info=chunk_info,
                language=language,
                dependencies=dependencies or [],
                entry_point=entry_point
            )

            logger.info(f"Transfer method: CHUNKED ({chunk_info['chunk_count']} chunks)")

        else:
            # Huge file: External storage required
            raise ValueError(
                f"File too large for current transport methods: {compressed_size:,} bytes. "
                f"External storage (S3/MinIO) not yet implemented."
            )

        return payload

    def _store_in_lfs(self, data: bytes, filename: str, checksum: str) -> Path:
        """
        Store data in Git LFS directory.

        Uses content-addressed storage: lfs-objects/{checksum[:2]}/{checksum}/filename
        """
        # Create subdirectory based on checksum prefix (like Git)
        prefix = checksum[:2]
        storage_dir = self.lfs_dir / prefix / checksum
        storage_dir.mkdir(parents=True, exist_ok=True)

        # Store file
        lfs_file = storage_dir / filename
        with open(lfs_file, "wb") as f:
            f.write(data)

        logger.debug(f"Stored in LFS: {lfs_file}")
        return lfs_file

    def _create_chunks(
        self,
        data: bytes,
        filename: str,
        checksum: str
    ) -> Dict[str, Any]:
        """
        Split large file into chunks for transfer.

        Returns:
            Chunk metadata including paths and checksums
        """
        total_size = len(data)
        chunk_count = (total_size + self.CHUNK_SIZE - 1) // self.CHUNK_SIZE

        chunks = []
        for i in range(chunk_count):
            start = i * self.CHUNK_SIZE
            end = min(start + self.CHUNK_SIZE, total_size)
            chunk_data = data[start:end]

            # Compute chunk checksum
            chunk_checksum = hashlib.sha256(chunk_data).hexdigest()

            # Store chunk in LFS
            chunk_filename = f"{filename}.chunk{i:04d}"
            chunk_path = self._store_in_lfs(chunk_data, chunk_filename, chunk_checksum)

            chunks.append({
                "index": i,
                "size": len(chunk_data),
                "checksum": chunk_checksum,
                "path": str(chunk_path.relative_to(self.repo_path))
            })

        return {
            "chunk_count": chunk_count,
            "chunk_size": self.CHUNK_SIZE,
            "total_size": total_size,
            "original_checksum": checksum,
            "chunks": chunks
        }

    def receive_code(
        self,
        payload: Dict[str, Any],
        target_path: Path
    ) -> Path:
        """
        Receive code from another node and reconstruct.

        Args:
            payload: CodePayload dictionary
            target_path: Where to save the reconstructed file

        Returns:
            Path to reconstructed file
        """
        # Parse payload
        code_payload = CodePayload(**payload)

        logger.info(f"Receiving code: {code_payload.filename}")
        logger.info(f"Transfer method: {code_payload.transfer_method}")
        logger.info(f"Size: {code_payload.original_size:,} bytes")

        # Reconstruct data based on transfer method
        if code_payload.transfer_method == TransferMethod.INLINE:
            # Decode base64
            compressed_data = base64.b64decode(code_payload.inline_data)

        elif code_payload.transfer_method == TransferMethod.GIT_LFS:
            # Read from LFS
            lfs_path = self.repo_path / code_payload.lfs_path
            if not lfs_path.exists():
                raise FileNotFoundError(f"LFS file not found: {lfs_path}")

            with open(lfs_path, "rb") as f:
                compressed_data = f.read()

        elif code_payload.transfer_method == TransferMethod.CHUNKED:
            # Reassemble chunks
            compressed_data = self._reassemble_chunks(code_payload.chunk_info)

        else:
            raise ValueError(f"Unsupported transfer method: {code_payload.transfer_method}")

        # Decompress if needed
        original_data = self._decompress_data(compressed_data, code_payload.compression)

        # Verify checksum
        actual_checksum = hashlib.sha256(original_data).hexdigest()
        if actual_checksum != code_payload.checksum:
            raise ValueError(
                f"Checksum mismatch! Expected {code_payload.checksum}, "
                f"got {actual_checksum}"
            )

        logger.info(f"✓ Checksum verified: {actual_checksum[:8]}...")

        # Write to target path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "wb") as f:
            f.write(original_data)

        logger.info(f"✓ Code saved to: {target_path}")

        return target_path

    def _reassemble_chunks(self, chunk_info: Dict[str, Any]) -> bytes:
        """Reassemble file from chunks."""
        chunk_count = chunk_info["chunk_count"]
        chunks_data = []

        logger.info(f"Reassembling {chunk_count} chunks...")

        for chunk_meta in chunk_info["chunks"]:
            chunk_path = self.repo_path / chunk_meta["path"]

            if not chunk_path.exists():
                raise FileNotFoundError(f"Chunk not found: {chunk_path}")

            with open(chunk_path, "rb") as f:
                chunk_data = f.read()

            # Verify chunk checksum
            actual_checksum = hashlib.sha256(chunk_data).hexdigest()
            if actual_checksum != chunk_meta["checksum"]:
                raise ValueError(
                    f"Chunk {chunk_meta['index']} checksum mismatch! "
                    f"Expected {chunk_meta['checksum']}, got {actual_checksum}"
                )

            chunks_data.append(chunk_data)
            logger.debug(f"✓ Chunk {chunk_meta['index']} verified")

        # Concatenate chunks
        full_data = b"".join(chunks_data)

        logger.info(f"✓ Reassembled {len(full_data):,} bytes from {chunk_count} chunks")

        return full_data

    def cleanup_lfs_object(self, checksum: str):
        """Remove LFS object by checksum (for cleanup)."""
        prefix = checksum[:2]
        lfs_path = self.lfs_dir / prefix / checksum

        if lfs_path.exists():
            shutil.rmtree(lfs_path)
            logger.info(f"Cleaned up LFS object: {checksum[:8]}...")


# ============================================================================
# Helper Functions
# ============================================================================

def estimate_transfer_time(
    file_size: int,
    bandwidth_mbps: float = 10.0
) -> float:
    """
    Estimate transfer time for a file.

    Args:
        file_size: File size in bytes
        bandwidth_mbps: Network bandwidth in Mbps

    Returns:
        Estimated time in seconds
    """
    bandwidth_bytes_per_sec = (bandwidth_mbps * 1_000_000) / 8
    return file_size / bandwidth_bytes_per_sec


def format_size(size_bytes: int) -> str:
    """Format byte size as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


# ============================================================================
# CLI for testing
# ============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 code_transfer.py prepare <file>")
        print("  python3 code_transfer.py receive <payload.json> <output-file>")
        sys.exit(1)

    command = sys.argv[1]
    manager = CodeTransferManager()

    if command == "prepare":
        # Prepare code for transfer
        code_file = Path(sys.argv[2])

        payload = manager.prepare_code_payload(code_file)

        # Save payload to JSON
        payload_file = code_file.parent / f"{code_file.name}.payload.json"
        with open(payload_file, "w") as f:
            json.dump(asdict(payload), f, indent=2)

        print(f"\n✓ Payload saved to: {payload_file}")
        print(f"  Transfer method: {payload.transfer_method}")
        print(f"  Original size: {format_size(payload.original_size)}")
        print(f"  Compressed size: {format_size(payload.compressed_size)}")
        print(f"  Compression: {payload.compression}")
        print(f"  Checksum: {payload.checksum[:16]}...")

    elif command == "receive":
        # Receive and reconstruct code
        payload_file = Path(sys.argv[2])
        output_file = Path(sys.argv[3])

        with open(payload_file) as f:
            payload = json.load(f)

        result_path = manager.receive_code(payload, output_file)

        print(f"\n✓ Code reconstructed to: {result_path}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

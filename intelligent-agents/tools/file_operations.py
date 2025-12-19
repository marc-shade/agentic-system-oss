"""
Deterministic File Operations

NO AI - Pure code for file handling.
Following Kai pattern: "If I can do it in code, I do it in code first."

Security: Path traversal protection added per security review 2025-12-19
"""

import os
import json
import hashlib
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime


class PathTraversalError(ValueError):
    """Raised when path traversal attack detected."""
    pass


class FileOps:
    """Deterministic file operations - no AI required."""

    # Configurable base directory for sandboxed operations
    _sandbox_base: Optional[Path] = None

    @classmethod
    def set_sandbox(cls, base_dir: Union[str, Path, None]) -> None:
        """Set sandbox base directory. All paths must be within this directory."""
        cls._sandbox_base = Path(base_dir).resolve() if base_dir else None

    @classmethod
    def get_sandbox(cls) -> Optional[Path]:
        """Get current sandbox base directory."""
        return cls._sandbox_base

    @staticmethod
    def validate_path(path: Union[str, Path], base_dir: Optional[Path] = None) -> Path:
        """
        Validate path for traversal attacks.

        Args:
            path: Path to validate
            base_dir: Optional base directory to constrain paths within

        Returns:
            Resolved absolute path

        Raises:
            PathTraversalError: If path contains traversal sequences or escapes base_dir
        """
        path_obj = Path(path)

        # Check for traversal sequences in original path
        path_str = str(path)
        if '..' in path_str:
            raise PathTraversalError(f"Path contains traversal sequence '..': {path}")

        # Check for null bytes (common attack vector)
        if '\x00' in path_str:
            raise PathTraversalError(f"Path contains null byte: {path}")

        # Resolve to absolute path
        resolved = path_obj.resolve()

        # Use class sandbox if no base_dir provided
        effective_base = base_dir or FileOps._sandbox_base

        # If base directory specified, ensure path is within it
        if effective_base:
            base_resolved = Path(effective_base).resolve()
            try:
                resolved.relative_to(base_resolved)
            except ValueError:
                raise PathTraversalError(
                    f"Path '{path}' resolves to '{resolved}' which is outside "
                    f"base directory '{base_resolved}'"
                )

        return resolved

    @staticmethod
    def read_file(path: Union[str, Path], encoding: str = 'utf-8',
                  base_dir: Optional[Path] = None) -> str:
        """Read file contents with path validation."""
        validated_path = FileOps.validate_path(path, base_dir)
        with open(validated_path, 'r', encoding=encoding) as f:
            return f.read()

    @staticmethod
    def write_file(path: Union[str, Path], content: str, encoding: str = 'utf-8',
                   base_dir: Optional[Path] = None) -> None:
        """Write content to file with path validation."""
        validated_path = FileOps.validate_path(path, base_dir)
        validated_path.parent.mkdir(parents=True, exist_ok=True)
        with open(validated_path, 'w', encoding=encoding) as f:
            f.write(content)

    @staticmethod
    def append_file(path: Union[str, Path], content: str, encoding: str = 'utf-8',
                    base_dir: Optional[Path] = None) -> None:
        """Append content to file with path validation."""
        validated_path = FileOps.validate_path(path, base_dir)
        validated_path.parent.mkdir(parents=True, exist_ok=True)
        with open(validated_path, 'a', encoding=encoding) as f:
            f.write(content)

    @staticmethod
    def read_json(path: Union[str, Path], base_dir: Optional[Path] = None) -> Dict[str, Any]:
        """Read JSON file with path validation."""
        validated_path = FileOps.validate_path(path, base_dir)
        with open(validated_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def write_json(path: Union[str, Path], data: Dict[str, Any], indent: int = 2,
                   base_dir: Optional[Path] = None) -> None:
        """Write JSON file with path validation."""
        validated_path = FileOps.validate_path(path, base_dir)
        validated_path.parent.mkdir(parents=True, exist_ok=True)
        with open(validated_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, default=str)

    @staticmethod
    def file_exists(path: Union[str, Path], base_dir: Optional[Path] = None) -> bool:
        """Check if file exists with path validation."""
        validated_path = FileOps.validate_path(path, base_dir)
        return validated_path.exists()

    @staticmethod
    def get_file_hash(path: Union[str, Path], algorithm: str = 'sha256',
                      base_dir: Optional[Path] = None) -> str:
        """Get hash of file contents with path validation."""
        validated_path = FileOps.validate_path(path, base_dir)
        hash_func = getattr(hashlib, algorithm)()
        with open(validated_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hash_func.update(chunk)
        return hash_func.hexdigest()

    @staticmethod
    def get_file_size(path: Union[str, Path], base_dir: Optional[Path] = None) -> int:
        """Get file size in bytes with path validation."""
        validated_path = FileOps.validate_path(path, base_dir)
        return validated_path.stat().st_size

    @staticmethod
    def get_file_modified_time(path: Union[str, Path], base_dir: Optional[Path] = None) -> datetime:
        """Get file modification time with path validation."""
        validated_path = FileOps.validate_path(path, base_dir)
        return datetime.fromtimestamp(validated_path.stat().st_mtime)

    @staticmethod
    def list_files(directory: Union[str, Path], pattern: str = '*', recursive: bool = False,
                   base_dir: Optional[Path] = None) -> List[Path]:
        """List files matching pattern with path validation."""
        validated_path = FileOps.validate_path(directory, base_dir)
        if recursive:
            return list(validated_path.rglob(pattern))
        return list(validated_path.glob(pattern))

    @staticmethod
    def copy_file(src: Union[str, Path], dst: Union[str, Path],
                  base_dir: Optional[Path] = None) -> None:
        """Copy file to destination with path validation."""
        validated_src = FileOps.validate_path(src, base_dir)
        validated_dst = FileOps.validate_path(dst, base_dir)
        validated_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(validated_src, validated_dst)

    @staticmethod
    def move_file(src: Union[str, Path], dst: Union[str, Path],
                  base_dir: Optional[Path] = None) -> None:
        """Move file to destination with path validation."""
        validated_src = FileOps.validate_path(src, base_dir)
        validated_dst = FileOps.validate_path(dst, base_dir)
        validated_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(validated_src, validated_dst)

    @staticmethod
    def delete_file(path: Union[str, Path], base_dir: Optional[Path] = None) -> None:
        """Delete file with path validation."""
        validated_path = FileOps.validate_path(path, base_dir)
        validated_path.unlink(missing_ok=True)

    @staticmethod
    def ensure_directory(path: Union[str, Path], base_dir: Optional[Path] = None) -> Path:
        """Ensure directory exists, create if not, with path validation."""
        validated_path = FileOps.validate_path(path, base_dir)
        validated_path.mkdir(parents=True, exist_ok=True)
        return validated_path

    @staticmethod
    def get_extension(path: Union[str, Path]) -> str:
        """Get file extension (no validation needed - no I/O)."""
        return Path(path).suffix

    @staticmethod
    def get_stem(path: Union[str, Path]) -> str:
        """Get filename without extension (no validation needed - no I/O)."""
        return Path(path).stem

    @staticmethod
    def safe_filename(name: str) -> str:
        """Convert string to safe filename."""
        # Remove/replace unsafe characters
        unsafe = '<>:"/\\|?*'
        for char in unsafe:
            name = name.replace(char, '_')
        # Also remove path traversal attempts
        name = name.replace('..', '_')
        return name.strip()

    @staticmethod
    def backup_file(path: Union[str, Path], backup_dir: Optional[Union[str, Path]] = None,
                    base_dir: Optional[Path] = None) -> Path:
        """Create timestamped backup of file with path validation."""
        validated_src = FileOps.validate_path(path, base_dir)

        if backup_dir is None:
            backup_path = validated_src.parent / 'backups'
        else:
            backup_path = FileOps.validate_path(backup_dir, base_dir)

        backup_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{validated_src.stem}_{timestamp}{validated_src.suffix}"
        dst = backup_path / backup_name

        shutil.copy2(validated_src, dst)
        return dst


if __name__ == '__main__':
    # Self-test
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        test_file = tmpdir_path / 'test.txt'

        # Test write/read
        FileOps.write_file(test_file, 'Hello, World!')
        assert FileOps.read_file(test_file) == 'Hello, World!'

        # Test exists
        assert FileOps.file_exists(test_file)

        # Test hash
        hash_val = FileOps.get_file_hash(test_file)
        assert len(hash_val) == 64  # SHA256

        # Test JSON
        json_file = tmpdir_path / 'test.json'
        FileOps.write_json(json_file, {'key': 'value'})
        assert FileOps.read_json(json_file) == {'key': 'value'}

        print('✓ Basic FileOps tests passed!')

        # === Security Tests: Path Traversal Protection ===
        print('\nTesting path traversal protection...')

        # Test 1: Reject paths with ..
        try:
            FileOps.validate_path('../etc/passwd')
            assert False, "Should have raised PathTraversalError"
        except PathTraversalError as e:
            print(f"  ✓ Blocked traversal: {e}")

        # Test 2: Reject paths with null bytes
        try:
            FileOps.validate_path('/tmp/file\x00.txt')
            assert False, "Should have raised PathTraversalError"
        except PathTraversalError as e:
            print(f"  ✓ Blocked null byte: {e}")

        # Test 3: Sandbox enforcement
        FileOps.set_sandbox(tmpdir_path)
        try:
            FileOps.validate_path('/etc/passwd')
            assert False, "Should have raised PathTraversalError for path outside sandbox"
        except PathTraversalError as e:
            print(f"  ✓ Blocked outside sandbox: {e}")

        # Test 4: Valid path within sandbox works
        valid_path = FileOps.validate_path(test_file)
        assert valid_path.exists(), "Valid path should work"
        print(f"  ✓ Valid path accepted: {valid_path}")

        # Test 5: safe_filename removes traversal
        safe = FileOps.safe_filename('../../evil.txt')
        assert '..' not in safe, f"safe_filename should remove ..: got {safe}"
        print(f"  ✓ safe_filename sanitized: '../../evil.txt' -> '{safe}'")

        # Reset sandbox
        FileOps.set_sandbox(None)

        print('\n✅ All FileOps tests passed (including security tests)!')

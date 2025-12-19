"""
Tests for tools/file_operations.py

Tests path traversal protection, sandbox enforcement, and file operations.
"""

import pytest
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.file_operations import FileOps, PathTraversalError


class TestPathValidation:
    """Test path traversal protection."""

    def test_reject_dot_dot_traversal(self):
        """Paths with .. should be rejected."""
        with pytest.raises(PathTraversalError, match="traversal sequence"):
            FileOps.validate_path("../etc/passwd")

    def test_reject_nested_traversal(self):
        """Nested traversal attempts should be rejected."""
        with pytest.raises(PathTraversalError, match="traversal sequence"):
            FileOps.validate_path("foo/../../bar")

    def test_reject_null_bytes(self):
        """Paths with null bytes should be rejected."""
        with pytest.raises(PathTraversalError, match="null byte"):
            FileOps.validate_path("/tmp/file\x00.txt")

    def test_accept_valid_absolute_path(self, temp_dir):
        """Valid absolute paths should be accepted."""
        test_file = temp_dir / "valid.txt"
        test_file.touch()
        result = FileOps.validate_path(str(test_file))
        assert result == test_file.resolve()

    def test_accept_valid_relative_path(self, temp_dir):
        """Valid paths within sandbox should be accepted."""
        test_file = temp_dir / "subdir" / "file.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.touch()
        # Use full path within base_dir
        result = FileOps.validate_path(str(test_file), base_dir=temp_dir)
        assert result.exists()


class TestSandboxEnforcement:
    """Test sandbox directory enforcement."""

    def test_sandbox_blocks_outside_paths(self, temp_dir):
        """Paths outside sandbox should be blocked."""
        FileOps.set_sandbox(temp_dir)
        try:
            with pytest.raises(PathTraversalError, match="outside.*base directory"):
                FileOps.validate_path("/etc/passwd")
        finally:
            FileOps.set_sandbox(None)

    def test_sandbox_allows_inside_paths(self, temp_dir):
        """Paths inside sandbox should be allowed."""
        FileOps.set_sandbox(temp_dir)
        try:
            test_file = temp_dir / "allowed.txt"
            test_file.touch()
            result = FileOps.validate_path(str(test_file))
            assert result == test_file.resolve()
        finally:
            FileOps.set_sandbox(None)

    def test_sandbox_can_be_cleared(self, temp_dir):
        """Sandbox can be cleared to allow any path."""
        FileOps.set_sandbox(temp_dir)
        FileOps.set_sandbox(None)
        # Should not raise - sandbox is cleared
        result = FileOps.validate_path("/tmp")
        assert result == Path("/tmp").resolve()

    def test_get_sandbox_returns_current(self, temp_dir):
        """get_sandbox should return current sandbox."""
        assert FileOps.get_sandbox() is None
        FileOps.set_sandbox(temp_dir)
        try:
            assert FileOps.get_sandbox() == temp_dir.resolve()
        finally:
            FileOps.set_sandbox(None)


class TestFileOperations:
    """Test actual file operations with validation."""

    def test_write_and_read_file(self, temp_dir):
        """Write and read should work with valid paths."""
        test_file = temp_dir / "test.txt"
        FileOps.write_file(test_file, "Hello, World!")
        content = FileOps.read_file(test_file)
        assert content == "Hello, World!"

    def test_append_file(self, temp_dir):
        """Append should add to existing content."""
        test_file = temp_dir / "append.txt"
        FileOps.write_file(test_file, "Line 1\n")
        FileOps.append_file(test_file, "Line 2\n")
        content = FileOps.read_file(test_file)
        assert content == "Line 1\nLine 2\n"

    def test_json_operations(self, temp_dir):
        """JSON read/write should work correctly."""
        test_file = temp_dir / "data.json"
        data = {"key": "value", "number": 42, "nested": {"a": 1}}
        FileOps.write_json(test_file, data)
        loaded = FileOps.read_json(test_file)
        assert loaded == data

    def test_file_exists(self, temp_dir):
        """file_exists should detect file presence."""
        test_file = temp_dir / "exists.txt"
        assert not FileOps.file_exists(test_file)
        test_file.touch()
        assert FileOps.file_exists(test_file)

    def test_get_file_hash(self, temp_dir):
        """File hash should be consistent."""
        test_file = temp_dir / "hash.txt"
        FileOps.write_file(test_file, "test content")
        hash1 = FileOps.get_file_hash(test_file)
        hash2 = FileOps.get_file_hash(test_file)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256

    def test_get_file_size(self, temp_dir):
        """File size should be accurate."""
        test_file = temp_dir / "size.txt"
        content = "12345"
        FileOps.write_file(test_file, content)
        assert FileOps.get_file_size(test_file) == len(content)

    def test_list_files(self, temp_dir):
        """list_files should find matching files."""
        (temp_dir / "file1.txt").touch()
        (temp_dir / "file2.txt").touch()
        (temp_dir / "file3.py").touch()

        txt_files = FileOps.list_files(temp_dir, "*.txt")
        assert len(txt_files) == 2

        all_files = FileOps.list_files(temp_dir, "*")
        assert len(all_files) == 3

    def test_copy_file(self, temp_dir):
        """Copy should duplicate file contents."""
        src = temp_dir / "source.txt"
        dst = temp_dir / "dest.txt"
        FileOps.write_file(src, "copy me")
        FileOps.copy_file(src, dst)
        assert FileOps.read_file(dst) == "copy me"
        assert src.exists()  # Original still exists

    def test_move_file(self, temp_dir):
        """Move should relocate file."""
        src = temp_dir / "source.txt"
        dst = temp_dir / "dest.txt"
        FileOps.write_file(src, "move me")
        FileOps.move_file(src, dst)
        assert FileOps.read_file(dst) == "move me"
        assert not src.exists()  # Original removed

    def test_delete_file(self, temp_dir):
        """Delete should remove file."""
        test_file = temp_dir / "delete.txt"
        test_file.touch()
        assert test_file.exists()
        FileOps.delete_file(test_file)
        assert not test_file.exists()

    def test_ensure_directory(self, temp_dir):
        """ensure_directory should create nested dirs."""
        new_dir = temp_dir / "a" / "b" / "c"
        assert not new_dir.exists()
        result = FileOps.ensure_directory(new_dir)
        assert new_dir.exists()
        assert result == new_dir.resolve()

    def test_backup_file(self, temp_dir):
        """Backup should create timestamped copy."""
        test_file = temp_dir / "backup.txt"
        FileOps.write_file(test_file, "backup content")
        backup_path = FileOps.backup_file(test_file)
        assert backup_path.exists()
        assert "backup_" in backup_path.name
        assert FileOps.read_file(backup_path) == "backup content"


class TestSafeFilename:
    """Test filename sanitization."""

    def test_removes_unsafe_chars(self):
        """Unsafe characters should be replaced."""
        unsafe = 'file<>:"/\\|?*.txt'
        safe = FileOps.safe_filename(unsafe)
        for char in '<>:"/\\|?*':
            assert char not in safe

    def test_removes_traversal(self):
        """Traversal sequences should be removed."""
        malicious = "../../evil.txt"
        safe = FileOps.safe_filename(malicious)
        assert ".." not in safe

    def test_preserves_valid_names(self):
        """Valid filenames should be unchanged."""
        valid = "my_file-2024.txt"
        assert FileOps.safe_filename(valid) == valid


class TestHelperMethods:
    """Test helper methods that don't do I/O."""

    def test_get_extension(self):
        """Should extract file extension."""
        assert FileOps.get_extension("file.txt") == ".txt"
        assert FileOps.get_extension("file.tar.gz") == ".gz"
        assert FileOps.get_extension("noext") == ""

    def test_get_stem(self):
        """Should extract filename without extension."""
        assert FileOps.get_stem("file.txt") == "file"
        assert FileOps.get_stem("path/to/file.py") == "file"
        assert FileOps.get_stem("noext") == "noext"


class TestSecurityEdgeCases:
    """Test security edge cases from malicious_inputs fixture."""

    def test_all_traversal_patterns_blocked(self, temp_dir, malicious_inputs):
        """All path traversal patterns should be blocked when sandbox is set."""
        # Set sandbox so absolute paths outside are also blocked
        FileOps.set_sandbox(temp_dir)
        try:
            for path in malicious_inputs["path_traversal"]:
                with pytest.raises(PathTraversalError):
                    FileOps.validate_path(path)
        finally:
            FileOps.set_sandbox(None)

    def test_operations_with_sandbox(self, temp_dir, malicious_inputs):
        """Operations should fail for malicious paths even with sandbox."""
        FileOps.set_sandbox(temp_dir)
        try:
            for path in malicious_inputs["path_traversal"]:
                with pytest.raises(PathTraversalError):
                    FileOps.read_file(path)
        finally:
            FileOps.set_sandbox(None)

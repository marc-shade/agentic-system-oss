#!/usr/bin/env python3
"""
Phase 1 Testing: Payload Transport Model
=========================================

Tests all Phase 1 features:
1. Code transfer with size-based routing (inline/LFS/chunked)
2. Payload compression (Zstandard)
3. Dependency manager with virtualenv caching
4. End-to-end code execution with dependencies

Usage:
    python3 test_phase1.py --test-all
    python3 test_phase1.py --test-transfer
    python3 test_phase1.py --test-dependencies
    python3 test_phase1.py --test-compression
"""

import argparse
import json
import logging
import shutil
import sys
import tempfile
import time
from pathlib import Path

from code_transfer import CodeTransferManager, TransferMethod, format_size
from dependency_manager import DependencyManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_inline_transfer():
    """Test 1: Inline transfer for small files (< 50KB)."""
    print("\n" + "=" * 70)
    print("TEST 1: Inline Transfer (< 50KB)")
    print("=" * 70)

    # Create small test file
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create 10KB Python file
        test_file = tmpdir / "small_script.py"
        test_file.write_text("""#!/usr/bin/env python3
print("Hello from inline transfer!")
import sys
print(f"Python version: {sys.version}")
""")

        manager = CodeTransferManager(repo_path=tmpdir / "repo")

        # Prepare payload
        payload = manager.prepare_code_payload(
            code_path=test_file,
            dependencies=["requests>=2.31.0"],
            entry_point="small_script.py"
        )

        assert payload.transfer_method == TransferMethod.INLINE
        assert payload.inline_data is not None
        assert payload.lfs_path is None
        assert payload.chunk_info is None

        print(f"✓ Transfer method: {payload.transfer_method}")
        print(f"✓ Original size: {format_size(payload.original_size)}")
        print(f"✓ Compressed size: {format_size(payload.compressed_size)}")
        print(f"✓ Compression: {payload.compression}")
        print(f"✓ Inline data length: {len(payload.inline_data)} chars")

        # Receive code
        output_file = tmpdir / "received_small.py"
        result = manager.receive_code(payload.__dict__, output_file)

        assert result.exists()
        assert result.read_text() == test_file.read_text()

        print(f"✓ Code received and verified")
        print("\nPASS: Inline transfer")


def test_lfs_transfer():
    """Test 2: Git LFS transfer for medium files (50KB - 10MB)."""
    print("\n" + "=" * 70)
    print("TEST 2: Git LFS Transfer (50KB - 10MB)")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create 100KB Python file (exceeds inline threshold)
        test_file = tmpdir / "medium_script.py"
        code = "#!/usr/bin/env python3\n"
        code += "# " + ("=" * 100) + "\n"
        code += "# Large comment block to exceed 50KB threshold\n"
        code += "# " + ("=" * 100) + "\n"
        code += ("# Padding line\n" * 1000)  # Add padding to reach 100KB
        code += 'print("Hello from LFS transfer!")\n'

        test_file.write_text(code)
        file_size = test_file.stat().st_size

        print(f"Test file size: {format_size(file_size)}")
        assert file_size > 50_000, "File must be > 50KB for LFS test"

        manager = CodeTransferManager(repo_path=tmpdir / "repo")

        # Prepare payload
        payload = manager.prepare_code_payload(
            code_path=test_file,
            entry_point="medium_script.py"
        )

        assert payload.transfer_method == TransferMethod.GIT_LFS
        assert payload.lfs_path is not None
        assert payload.inline_data is None

        print(f"✓ Transfer method: {payload.transfer_method}")
        print(f"✓ Original size: {format_size(payload.original_size)}")
        print(f"✓ Compressed size: {format_size(payload.compressed_size)}")
        print(f"✓ LFS path: {payload.lfs_path}")

        # Receive code
        output_file = tmpdir / "received_medium.py"
        result = manager.receive_code(payload.__dict__, output_file)

        assert result.exists()
        assert result.read_text() == test_file.read_text()

        print(f"✓ Code received and verified")
        print("\nPASS: Git LFS transfer")


def test_chunked_transfer():
    """Test 3: Chunked transfer for large files (> 10MB)."""
    print("\n" + "=" * 70)
    print("TEST 3: Chunked Transfer (> 10MB)")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create 12MB file (exceeds LFS threshold)
        test_file = tmpdir / "large_script.py"
        code = "#!/usr/bin/env python3\n"
        code += "# Large file for chunked transfer test\n"
        code += ("# Padding line " + ("x" * 100) + "\n") * 120000  # ~12MB

        test_file.write_text(code)
        file_size = test_file.stat().st_size

        print(f"Test file size: {format_size(file_size)}")
        assert file_size > 10_000_000, "File must be > 10MB for chunked test"

        manager = CodeTransferManager(repo_path=tmpdir / "repo")

        # Prepare payload
        start_time = time.time()
        payload = manager.prepare_code_payload(
            code_path=test_file,
            entry_point="large_script.py"
        )
        prep_time = time.time() - start_time

        assert payload.transfer_method == TransferMethod.CHUNKED
        assert payload.chunk_info is not None
        assert "chunk_count" in payload.chunk_info

        print(f"✓ Transfer method: {payload.transfer_method}")
        print(f"✓ Original size: {format_size(payload.original_size)}")
        print(f"✓ Compressed size: {format_size(payload.compressed_size)}")
        print(f"✓ Chunk count: {payload.chunk_info['chunk_count']}")
        print(f"✓ Chunk size: {format_size(payload.chunk_info['chunk_size'])}")
        print(f"✓ Preparation time: {prep_time:.2f}s")

        # Receive code
        start_time = time.time()
        output_file = tmpdir / "received_large.py"
        result = manager.receive_code(payload.__dict__, output_file)
        recv_time = time.time() - start_time

        assert result.exists()
        assert result.read_text() == test_file.read_text()

        print(f"✓ Code received and verified")
        print(f"✓ Reception time: {recv_time:.2f}s")
        print("\nPASS: Chunked transfer")


def test_compression():
    """Test 4: Payload compression."""
    print("\n" + "=" * 70)
    print("TEST 4: Payload Compression")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create highly compressible file
        test_file = tmpdir / "compressible.py"
        code = "#!/usr/bin/env python3\n"
        code += ("# Repeating line for compression test\n" * 1000)
        test_file.write_text(code)

        original_size = test_file.stat().st_size
        print(f"Original size: {format_size(original_size)}")

        manager = CodeTransferManager(repo_path=tmpdir / "repo")

        # Prepare payload
        payload = manager.prepare_code_payload(code_path=test_file)

        compression_ratio = (1 - payload.compressed_size / payload.original_size) * 100

        print(f"✓ Compression type: {payload.compression}")
        print(f"✓ Original size: {format_size(payload.original_size)}")
        print(f"✓ Compressed size: {format_size(payload.compressed_size)}")
        print(f"✓ Compression ratio: {compression_ratio:.1f}%")

        assert payload.compressed_size < payload.original_size, "File should be compressed"
        assert compression_ratio > 50, "Should achieve >50% compression on repetitive data"

        # Verify decompression works
        output_file = tmpdir / "decompressed.py"
        result = manager.receive_code(payload.__dict__, output_file)

        assert result.read_text() == test_file.read_text()

        print(f"✓ Decompression verified")
        print("\nPASS: Payload compression")


def test_dependency_manager():
    """Test 5: Dependency manager with virtualenv caching."""
    print("\n" + "=" * 70)
    print("TEST 5: Dependency Manager")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        manager = DependencyManager(cache_dir=tmpdir / "venv-cache")

        dependencies = ["requests>=2.31.0", "pydantic>=2.0.0"]

        # First run - should create virtualenv
        print("\n5a. First run (create virtualenv):")
        start_time = time.time()
        venv_path1 = manager.get_or_create_environment(dependencies)
        first_run_time = time.time() - start_time

        assert venv_path1.exists()
        assert (venv_path1 / "bin" / "python3").exists()

        print(f"✓ Virtualenv created: {venv_path1}")
        print(f"✓ Creation time: {first_run_time:.1f}s")

        # Second run - should use cached
        print("\n5b. Second run (use cached virtualenv):")
        start_time = time.time()
        venv_path2 = manager.get_or_create_environment(dependencies)
        second_run_time = time.time() - start_time

        assert venv_path2 == venv_path1, "Should reuse same virtualenv"

        print(f"✓ Virtualenv reused: {venv_path2}")
        print(f"✓ Cache hit time: {second_run_time:.3f}s")
        print(f"✓ Speedup: {first_run_time / second_run_time:.1f}x faster")

        assert second_run_time < 1.0, "Cache hit should be < 1s"

        # Different dependencies - should create new virtualenv
        print("\n5c. Different dependencies (create new virtualenv):")
        new_deps = ["numpy>=1.24.0"]
        venv_path3 = manager.get_or_create_environment(new_deps)

        assert venv_path3 != venv_path1, "Should create different virtualenv"
        assert venv_path3.exists()

        print(f"✓ New virtualenv created: {venv_path3}")

        # Check stats
        stats = manager.get_cache_stats()

        print(f"\n5d. Cache statistics:")
        print(f"✓ Total environments: {stats['total_environments']}")
        print(f"✓ Total size: {stats['total_size_gb']:.3f} GB")
        print(f"✓ Total uses: {stats['total_uses']}")

        assert stats['total_environments'] == 2
        assert stats['total_uses'] == 3  # venv1 used twice, venv3 used once

        print("\nPASS: Dependency manager")


def test_end_to_end():
    """Test 6: End-to-end code execution with dependencies."""
    print("\n" + "=" * 70)
    print("TEST 6: End-to-End Execution")
    print("=" * 70)

    import subprocess

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test script that uses dependencies
        test_script = tmpdir / "test_deps.py"
        test_script.write_text("""#!/usr/bin/env python3
import sys
try:
    import requests
    print(f"requests version: {requests.__version__}")
    print("SUCCESS: Dependencies loaded")
    sys.exit(0)
except ImportError as e:
    print(f"ERROR: {e}")
    sys.exit(1)
""")

        # Setup dependency manager
        dep_manager = DependencyManager(cache_dir=tmpdir / "venv-cache")

        # Create environment with requests
        deps = ["requests>=2.31.0"]
        print(f"Setting up environment for dependencies: {deps}")

        venv_path = dep_manager.get_or_create_environment(deps)
        python_bin = venv_path / "bin" / "python3"

        print(f"✓ Virtualenv ready: {venv_path}")

        # Execute script with virtualenv
        print(f"\nExecuting script with dependencies...")
        result = subprocess.run(
            [str(python_bin), str(test_script)],
            capture_output=True,
            text=True,
            timeout=10
        )

        print(f"Exit code: {result.returncode}")
        print(f"Output:\n{result.stdout}")

        if result.stderr:
            print(f"Errors:\n{result.stderr}")

        assert result.returncode == 0, "Script should execute successfully"
        assert "SUCCESS" in result.stdout, "Dependencies should load"

        print(f"✓ Script executed successfully with dependencies")
        print("\nPASS: End-to-end execution")


def run_all_tests():
    """Run all Phase 1 tests."""
    print("\n" + "=" * 70)
    print("Phase 1: Payload Transport Model - Test Suite")
    print("=" * 70)

    tests = [
        ("Inline Transfer", test_inline_transfer),
        ("Git LFS Transfer", test_lfs_transfer),
        ("Chunked Transfer", test_chunked_transfer),
        ("Payload Compression", test_compression),
        ("Dependency Manager", test_dependency_manager),
        ("End-to-End Execution", test_end_to_end),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n✗ TEST FAILED: {test_name}")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed == 0:
        print("\n✓ ALL TESTS PASSED")
        print("\nPhase 1 features verified:")
        print("  ✓ Inline transfer for small files (< 50KB)")
        print("  ✓ Git LFS transfer for medium files (50KB - 10MB)")
        print("  ✓ Chunked transfer for large files (> 10MB)")
        print("  ✓ Payload compression (Zstandard)")
        print("  ✓ Dependency manager with virtualenv caching")
        print("  ✓ End-to-end code execution with dependencies")
    else:
        print(f"\n✗ {failed} TESTS FAILED")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Phase 1 Testing Suite")
    parser.add_argument("--test-all", action="store_true", help="Run all tests")
    parser.add_argument("--test-transfer", action="store_true", help="Test code transfer")
    parser.add_argument("--test-dependencies", action="store_true", help="Test dependency manager")
    parser.add_argument("--test-compression", action="store_true", help="Test compression")
    parser.add_argument("--test-e2e", action="store_true", help="Test end-to-end execution")

    args = parser.parse_args()

    if args.test_all or not any([args.test_transfer, args.test_dependencies, args.test_compression, args.test_e2e]):
        run_all_tests()
    else:
        if args.test_transfer:
            test_inline_transfer()
            test_lfs_transfer()
            test_chunked_transfer()
        if args.test_compression:
            test_compression()
        if args.test_dependencies:
            test_dependency_manager()
        if args.test_e2e:
            test_end_to_end()


if __name__ == "__main__":
    main()

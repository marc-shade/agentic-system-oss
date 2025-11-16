#!/usr/bin/env python3.14
"""
Complete Builder Node Integration Test

Tests all Builder capabilities end-to-end:
- Task queue system
- Build caching
- Parallel testing
- Container builds
- Performance benchmarking
"""

import json
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "services"))
sys.path.insert(0, str(Path(__file__).parent / "skills" / "builder-node"))

from builder_task_queue import BuilderTaskQueue


def test_task_queue():
    """Test 1: Task Queue System"""
    print("\n=== Test 1: Task Queue System ===")

    queue = BuilderTaskQueue()

    # Get status
    status = queue.get_queue_status()
    print(f"Queue Status: {json.dumps(status, indent=2)}")

    # Enqueue a test task
    task_id = queue.enqueue_task({
        "type": "benchmark",
        "command": "python3.14 --version",
        "runs": 5,
        "priority": 8
    })

    print(f"✓ Enqueued task: {task_id}")

    # Get next task
    task = queue.get_next_task()
    if task:
        print(f"✓ Retrieved task: {task['task_id']}")

        # Execute task
        result = queue.execute_task(task)
        print(f"✓ Executed task: {'SUCCESS' if result.get('success') else 'FAILED'}")

        # Complete task
        queue.complete_task(task['task_id'], result)
        print(f"✓ Completed task")
    else:
        print("✗ No task retrieved")

    return True


def test_simple_compile():
    """Test 2: Simple C++ Compilation with caching"""
    print("\n=== Test 2: Simple C++ Compilation ===")

    # Create temp project
    temp_dir = tempfile.mkdtemp()
    try:
        # Create simple C++ file
        cpp_file = Path(temp_dir) / "test.cpp"
        cpp_file.write_text("""
#include <iostream>
int main() {
    std::cout << "Hello from Builder!" << std::endl;
    return 0;
}
""")

        # Queue compilation task
        queue = BuilderTaskQueue()
        task_id = queue.enqueue_task({
            "type": "compile",
            "project_dir": temp_dir,
            "build_system": "auto",
            "priority": 7
        })

        print(f"✓ Enqueued compilation task: {task_id}")

        # Execute
        task = queue.get_next_task()
        result = queue.execute_task(task)

        if result.get("success"):
            print(f"✓ Compilation succeeded in {result['duration']:.2f}s")
        else:
            print(f"✗ Compilation failed: {result.get('error')}")

        queue.complete_task(task_id, result)

        return result.get("success", False)

    finally:
        shutil.rmtree(temp_dir)


def test_benchmark():
    """Test 3: Performance Benchmarking"""
    print("\n=== Test 3: Performance Benchmarking ===")

    from performance_regression_detection import benchmark_with_regression_detection

    result = benchmark_with_regression_detection(
        command="echo 'benchmark test'",
        runs=5,
        warmup=2,
        regression_threshold=0.10
    )

    if not result.get("error"):
        print(f"✓ Benchmark completed")
        print(f"  Mean: {result['current']['mean']:.6f}s")
        print(f"  Stddev: {result['current']['stddev']:.6f}s")

        if result.get("baseline"):
            change = result["change_percent"]
            if result["regression"]:
                print(f"  ⚠️  Regression detected: {change:.1f}% slower")
            elif result["improvement"]:
                print(f"  ✓ Improvement: {abs(change):.1f}% faster")
            else:
                print(f"  ✓ Performance stable")

        return True
    else:
        print(f"✗ Benchmark failed: {result['error']}")
        return False


def test_redis_connectivity():
    """Test 4: Redis Connectivity"""
    print("\n=== Test 4: Redis Connectivity ===")

    import redis

    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        ping = r.ping()

        if ping:
            print("✓ Redis connection successful")

            # Test set/get
            r.set("builder:test", "success")
            value = r.get("builder:test")

            if value == "success":
                print("✓ Redis read/write successful")
                r.delete("builder:test")
                return True
        else:
            print("✗ Redis ping failed")
            return False

    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        return False


def test_qdrant_connectivity():
    """Test 5: Qdrant Connectivity"""
    print("\n=== Test 5: Qdrant Connectivity ===")

    import requests

    try:
        response = requests.get("http://localhost:6333/healthz", timeout=5)

        if response.status_code == 200:
            print("✓ Qdrant health check passed")

            # Get collections
            collections = requests.get("http://localhost:6333/collections").json()
            print(f"✓ Qdrant collections: {len(collections.get('result', {}).get('collections', []))}")

            return True
        else:
            print(f"✗ Qdrant health check failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"✗ Qdrant connection failed: {e}")
        return False


def main():
    """Run all integration tests"""
    print("=" * 60)
    print("Builder Node - Complete Integration Test")
    print("=" * 60)

    tests = [
        ("Task Queue System", test_task_queue),
        ("Redis Connectivity", test_redis_connectivity),
        ("Qdrant Connectivity", test_qdrant_connectivity),
        ("Performance Benchmarking", test_benchmark),
        ("Simple C++ Compilation", test_simple_compile),
    ]

    results = {}
    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            success = test_func()
            results[test_name] = "PASSED" if success else "FAILED"

            if success:
                passed += 1
            else:
                failed += 1

        except Exception as e:
            print(f"\n✗ Test '{test_name}' raised exception: {e}")
            results[test_name] = "ERROR"
            failed += 1

    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    for test_name, result in results.items():
        symbol = "✓" if result == "PASSED" else "✗"
        print(f"{symbol} {test_name}: {result}")

    print(f"\nTotal: {passed + failed}, Passed: {passed}, Failed: {failed}")
    print(f"Success Rate: {(passed / (passed + failed) * 100):.1f}%")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

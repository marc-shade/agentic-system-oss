#!/usr/bin/env python3
"""
Test script for Build Executor
Submits sample build jobs and monitors execution
"""

import json
import time
import uuid
import redis
from pathlib import Path

# Configuration
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 2


def create_test_build_job(
    project_id: str,
    build_type: str = "test",
    build_env: str = "node:20",
    build_command: str = "echo 'Hello from build'",
    git_repo: str = None,
):
    """Create a test build job"""

    build_id = str(uuid.uuid4())

    job = {
        "build_id": build_id,
        "project_id": project_id,
        "build_type": build_type,
        "build_env": build_env,
        "build_command": build_command,
        "timeout_seconds": 300,  # 5 minutes
        "tags": ["test"],
    }

    if git_repo:
        job["git_repo"] = git_repo
        job["git_branch"] = "main"

    return job


def submit_build_job(job: dict):
    """Submit build job to Redis queue"""

    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

    # Push to build queue
    r.lpush("build_queue", json.dumps(job))

    print(f"Submitted build job: {job['build_id']}")
    print(f"  Project: {job['project_id']}")
    print(f"  Environment: {job['build_env']}")
    print(f"  Command: {job['build_command']}")

    return job['build_id']


def monitor_build(build_id: str, timeout: int = 600):
    """Monitor build execution"""

    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

    print(f"\nMonitoring build: {build_id}")
    print("=" * 60)

    start_time = time.time()
    last_status = None

    while True:
        elapsed = time.time() - start_time

        if elapsed > timeout:
            print(f"\nMonitoring timeout after {elapsed:.1f}s")
            break

        # Check build status in Redis
        status_key = f"build:{build_id}:status"
        status_data = r.get(status_key)

        if status_data:
            status_obj = json.loads(status_data)
            current_status = status_obj['status']

            if current_status != last_status:
                print(f"\n[{elapsed:.1f}s] Status: {current_status}")

                if 'metadata' in status_obj:
                    metadata = status_obj['metadata']
                    if 'build_number' in metadata:
                        print(f"  Build number: {metadata['build_number']}")
                    if 'duration_seconds' in metadata and metadata['duration_seconds']:
                        print(f"  Duration: {metadata['duration_seconds']}s")
                    if 'artifacts_count' in metadata:
                        print(f"  Artifacts: {metadata['artifacts_count']}")

                last_status = current_status

            # Exit if build is complete
            if current_status in ['success', 'failed']:
                print(f"\nBuild finished: {current_status}")

                if 'metadata' in status_obj:
                    print("\nFinal metadata:")
                    print(json.dumps(status_obj['metadata'], indent=2))

                return current_status == 'success'

        else:
            if last_status != 'queued':
                print(f"\n[{elapsed:.1f}s] Status: queued (waiting for worker)")
                last_status = 'queued'

        time.sleep(2)

    return False


def test_simple_build():
    """Test 1: Simple echo build"""

    print("\n" + "=" * 60)
    print("TEST 1: Simple Echo Build")
    print("=" * 60)

    job = create_test_build_job(
        project_id="test-echo",
        build_env="alpine:latest",
        build_command="echo 'Hello from Alpine' && mkdir -p /output && echo 'test artifact' > /output/test.txt"
    )

    build_id = submit_build_job(job)
    success = monitor_build(build_id, timeout=120)

    print(f"\nTest 1 result: {'PASS' if success else 'FAIL'}")
    return success


def test_node_build():
    """Test 2: Node.js build"""

    print("\n" + "=" * 60)
    print("TEST 2: Node.js Build")
    print("=" * 60)

    # Create a simple package.json and build script
    job = create_test_build_job(
        project_id="test-node",
        build_env="node:20",
        build_command="""
            echo '{"name":"test","version":"1.0.0"}' > package.json &&
            echo 'console.log("Built successfully")' > index.js &&
            node index.js &&
            mkdir -p /output &&
            cp index.js /output/
        """
    )

    build_id = submit_build_job(job)
    success = monitor_build(build_id, timeout=180)

    print(f"\nTest 2 result: {'PASS' if success else 'FAIL'}")
    return success


def test_timeout_build():
    """Test 3: Build timeout"""

    print("\n" + "=" * 60)
    print("TEST 3: Build Timeout")
    print("=" * 60)

    job = create_test_build_job(
        project_id="test-timeout",
        build_env="alpine:latest",
        build_command="sleep 120",  # Sleep for 2 minutes
    )

    # Set short timeout
    job['timeout_seconds'] = 10

    build_id = submit_build_job(job)
    success = monitor_build(build_id, timeout=60)

    # This should fail due to timeout
    print(f"\nTest 3 result: {'PASS (timeout detected)' if not success else 'FAIL (should timeout)'}")
    return not success  # Expect failure


def test_failed_build():
    """Test 4: Build failure"""

    print("\n" + "=" * 60)
    print("TEST 4: Failed Build")
    print("=" * 60)

    job = create_test_build_job(
        project_id="test-failure",
        build_env="alpine:latest",
        build_command="exit 1"  # Explicit failure
    )

    build_id = submit_build_job(job)
    success = monitor_build(build_id, timeout=120)

    # This should fail
    print(f"\nTest 4 result: {'PASS (failure detected)' if not success else 'FAIL (should fail)'}")
    return not success  # Expect failure


def test_python_build():
    """Test 5: Python build with artifact"""

    print("\n" + "=" * 60)
    print("TEST 5: Python Build with Artifact")
    print("=" * 60)

    job = create_test_build_job(
        project_id="test-python",
        build_env="python:3.12",
        build_command="""
            echo 'print("Building Python project")' > app.py &&
            python app.py &&
            mkdir -p /output &&
            echo 'Binary artifact' > /output/app.bin &&
            echo 'Documentation' > /output/README.md
        """
    )

    build_id = submit_build_job(job)
    success = monitor_build(build_id, timeout=180)

    print(f"\nTest 5 result: {'PASS' if success else 'FAIL'}")
    return success


def check_executor_running():
    """Check if build executor is running"""

    import subprocess

    try:
        result = subprocess.run(
            ["/home/marc/agentic-system/services/build-executor-daemon.sh", "status"],
            capture_output=True,
            text=True,
        )

        running = result.returncode == 0

        if running:
            print("Build executor is running")
            print(result.stdout)
        else:
            print("WARNING: Build executor is not running")
            print("Start it with: ./build-executor-daemon.sh start")

        return running

    except Exception as e:
        print(f"Error checking executor status: {e}")
        return False


def main():
    """Run all tests"""

    print("=" * 60)
    print("Build Executor Test Suite")
    print("=" * 60)

    # Check if executor is running
    if not check_executor_running():
        print("\nPlease start the build executor before running tests:")
        print("  cd /home/marc/agentic-system/services")
        print("  ./build-executor-daemon.sh start")
        return

    # Run tests
    tests = [
        ("Simple Echo Build", test_simple_build),
        ("Node.js Build", test_node_build),
        ("Build Timeout", test_timeout_build),
        ("Failed Build", test_failed_build),
        ("Python Build", test_python_build),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\nTest '{test_name}' raised exception: {e}")
            results.append((test_name, False))

        # Wait between tests
        time.sleep(5)

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {status}: {test_name}")

    print(f"\nTotal: {passed}/{total} passed")

    if passed == total:
        print("\nAll tests passed!")
    else:
        print(f"\n{total - passed} test(s) failed")


if __name__ == "__main__":
    main()

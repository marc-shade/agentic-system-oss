#!/usr/bin/env python3.14
"""
Orchestrator Task Test

Simulates an orchestrator node enqueueing tasks to the Builder
and monitoring for completion.
"""

import sys
import time
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "services"))
from builder_task_queue import BuilderTaskQueue


def test_orchestrator_workflow():
    """Test complete orchestrator -> builder workflow."""
    print("=" * 60)
    print("Orchestrator -> Builder End-to-End Test")
    print("=" * 60)

    queue = BuilderTaskQueue()

    # Test 1: Enqueue a benchmark task
    print("\n[Orchestrator] Enqueuing benchmark task...")
    task_id = queue.enqueue_task({
        "type": "benchmark",
        "command": "echo 'Builder test'",
        "runs": 3,
        "warmup": 1,
        "priority": 8,
        "created_by": "orchestrator-test"
    })
    print(f"[Orchestrator] Task enqueued: {task_id}")

    # Monitor queue status
    print("\n[Orchestrator] Monitoring queue status...")
    status = queue.get_queue_status()
    print(f"  Queued: {status['queued_tasks']}")
    print(f"  Active: {status['active_tasks']}")
    print(f"  Utilization: {status['utilization']:.1f}%")

    # Wait for task completion
    print(f"\n[Orchestrator] Waiting for task {task_id} to complete...")
    max_wait = 30  # 30 seconds timeout
    start_time = time.time()

    while time.time() - start_time < max_wait:
        # Check if task is complete
        result_key = f"builder:results:{task_id}"
        result = queue.redis_client.get(result_key)

        if result:
            result_data = json.loads(result)
            print(f"\n[Orchestrator] Task completed!")
            print(f"  Success: {result_data.get('success')}")
            print(f"  Duration: {result_data.get('duration', 0):.2f}s")

            if result_data.get('error'):
                print(f"  Error: {result_data['error']}")

            return result_data.get('success', False)

        # Check if still in queue or active
        task_data = queue.redis_client.hgetall(f"task:{task_id}")
        if task_data:
            print(f"  Status: {task_data.get('status', 'unknown')}")

        time.sleep(2)

    print(f"\n[Orchestrator] Timeout waiting for task completion")
    return False


if __name__ == "__main__":
    success = test_orchestrator_workflow()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Cluster Task Offloading Library

Simple API for offloading work to cluster nodes automatically.
Use this in any Python code to leverage distributed execution.

Examples:
    # Simple command offload
    from cluster_offload import offload

    result = offload("python3 my_script.py")
    # Automatically routes to best node based on requirements

    # Specify requirements
    result = offload(
        "make build",
        requires_os="linux",
        requires_capabilities=["docker"]
    )
    # Routes to macpro51 (Linux builder)

    # Background execution
    task_id = offload("long_running_task.sh", wait=False)
    # Do other work...
    result = get_result(task_id)

    # Bulk operations
    tasks = [
        "python3 test1.py",
        "python3 test2.py",
        "python3 test3.py"
    ]
    results = offload_many(tasks)
"""

from typing import Optional, List, Dict, Any
from distributed_task_router import DistributedTaskRouter, Task
import time


# Global router instance
_router = None

def get_router() -> DistributedTaskRouter:
    """Get or create global router instance"""
    global _router
    if _router is None:
        _router = DistributedTaskRouter()
    return _router


def offload(
    command: str,
    requires_os: Optional[str] = None,
    requires_arch: Optional[str] = None,
    requires_capabilities: Optional[List[str]] = None,
    priority: int = 5,
    wait: bool = True,
    timeout: int = 300
) -> Optional[Dict]:
    """
    Offload a command to the cluster

    Args:
        command: Shell command to execute
        requires_os: Required OS (linux, macos)
        requires_arch: Required architecture (x86_64, arm64)
        requires_capabilities: Required capabilities list
        priority: Task priority (1-10, lower = higher priority)
        wait: Wait for result before returning
        timeout: Max seconds to wait for result

    Returns:
        Task result dict if wait=True, task_id if wait=False
    """
    router = get_router()

    task_def = {
        "type": "shell",
        "command": command,
        "requires_os": requires_os,
        "requires_arch": requires_arch,
        "requires_capabilities": requires_capabilities,
        "priority": priority
    }

    task_id = router.submit_task(task_def)

    if not wait:
        return task_id

    result = router.wait_for_result(task_id, timeout=timeout)
    return result


def offload_script(
    script: str,
    requires_os: Optional[str] = None,
    requires_arch: Optional[str] = None,
    requires_capabilities: Optional[List[str]] = None,
    priority: int = 5,
    wait: bool = True,
    timeout: int = 300
) -> Optional[Dict]:
    """
    Offload a shell script to the cluster

    Args:
        script: Shell script content to execute
        (other args same as offload())

    Returns:
        Task result dict if wait=True, task_id if wait=False
    """
    router = get_router()

    task_def = {
        "type": "script",
        "script": script,
        "requires_os": requires_os,
        "requires_arch": requires_arch,
        "requires_capabilities": requires_capabilities,
        "priority": priority
    }

    task_id = router.submit_task(task_def)

    if not wait:
        return task_id

    result = router.wait_for_result(task_id, timeout=timeout)
    return result


def offload_many(
    commands: List[str],
    requires_os: Optional[str] = None,
    requires_arch: Optional[str] = None,
    requires_capabilities: Optional[List[str]] = None,
    priority: int = 5,
    timeout: int = 300
) -> List[Optional[Dict]]:
    """
    Offload multiple commands in parallel

    Each command routes to optimal node independently.
    All commands execute in parallel across the cluster.

    Args:
        commands: List of shell commands
        (other args same as offload())

    Returns:
        List of result dicts (same order as input)
    """
    router = get_router()

    # Submit all tasks
    task_ids = []
    for command in commands:
        task_def = {
            "type": "shell",
            "command": command,
            "requires_os": requires_os,
            "requires_arch": requires_arch,
            "requires_capabilities": requires_capabilities,
            "priority": priority
        }
        task_id = router.submit_task(task_def)
        task_ids.append(task_id)

    # Wait for all results
    results = []
    for task_id in task_ids:
        result = router.wait_for_result(task_id, timeout=timeout)
        results.append(result)

    return results


def get_result(task_id: str, timeout: int = 300) -> Optional[Dict]:
    """
    Get result of a background task

    Args:
        task_id: Task ID from offload(..., wait=False)
        timeout: Max seconds to wait

    Returns:
        Task result dict
    """
    router = get_router()
    return router.wait_for_result(task_id, timeout=timeout)


def get_cluster_status() -> Dict[str, Any]:
    """Get current cluster status and load distribution"""
    router = get_router()
    return router.get_cluster_status()


# Convenience functions for common operations

def build_on_linux(command: str, wait: bool = True) -> Optional[Dict]:
    """Shortcut to run build commands on Linux node"""
    return offload(
        command,
        requires_os="linux",
        requires_capabilities=["docker"],
        wait=wait
    )


def research_on_air(command: str, wait: bool = True) -> Optional[Dict]:
    """Shortcut to run research tasks on MacBook Air"""
    return offload(
        command,
        requires_os="macos",
        requires_arch="arm64",
        requires_capabilities=["research"],
        wait=wait
    )


def coordinate_on_studio(command: str, wait: bool = True) -> Optional[Dict]:
    """Shortcut to run coordination tasks on Mac Studio"""
    return offload(
        command,
        requires_os="macos",
        requires_arch="arm64",
        requires_capabilities=["orchestration"],
        wait=wait
    )


# Example usage
if __name__ == "__main__":
    print("Cluster Task Offloading Examples\n")

    # Example 1: Simple command
    print("Example 1: Simple command offload")
    result = offload("echo 'Hello from cluster!' && hostname")
    if result:
        print(f"  Executed on: {result['assigned_to']}")
        print(f"  Output: {result['result']}")

    # Example 2: Linux-specific task
    print("\nExample 2: Linux-specific build")
    result = offload(
        "uname -a",
        requires_os="linux"
    )
    if result:
        print(f"  Executed on: {result['assigned_to']}")
        print(f"  Output: {result['result']}")

    # Example 3: Parallel execution
    print("\nExample 3: Parallel execution")
    tasks = [
        "echo 'Task 1' && sleep 1 && hostname",
        "echo 'Task 2' && sleep 1 && hostname",
        "echo 'Task 3' && sleep 1 && hostname"
    ]
    results = offload_many(tasks)
    for i, result in enumerate(results):
        if result:
            print(f"  Task {i+1}: {result['assigned_to']} - {result['status']}")

    # Example 4: Background task
    print("\nExample 4: Background execution")
    task_id = offload("sleep 2 && echo 'Background done'", wait=False)
    print(f"  Task submitted: {task_id}")
    print("  Doing other work...")
    time.sleep(1)
    result = get_result(task_id)
    if result:
        print(f"  Result: {result['result']}")

    # Example 5: Cluster status
    print("\nExample 5: Cluster status")
    status = get_cluster_status()
    print(f"  Local node: {status['local_node']}")
    print(f"  Task distribution: {status['task_distribution']}")

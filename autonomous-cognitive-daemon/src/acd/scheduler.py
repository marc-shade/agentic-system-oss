"""Task scheduler for ACD with priority queue and cron-like scheduling."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from heapq import heappush, heappop
from typing import Callable, Coroutine, Optional, Any, Dict, List

from .utils.logging import get_logger


logger = get_logger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 0  # Run immediately
    HIGH = 1      # Run within 1 minute
    NORMAL = 2    # Run within 5 minutes
    LOW = 3       # Run when idle
    BACKGROUND = 4  # Run only when system is idle


@dataclass(order=True)
class ScheduledTask:
    """A task scheduled for execution.

    Sorted by (scheduled_time, priority) so tasks run when due,
    with priority as tiebreaker.
    """
    scheduled_time: datetime = field(compare=True)
    priority: int = field(compare=True)
    task_id: str = field(compare=False)
    name: str = field(compare=False)
    coroutine_factory: Callable[[], Coroutine] = field(compare=False)
    interval_seconds: Optional[int] = field(compare=False, default=None)
    last_run: Optional[datetime] = field(compare=False, default=None)
    run_count: int = field(compare=False, default=0)
    enabled: bool = field(compare=False, default=True)


class Scheduler:
    """Async task scheduler with priority queue.

    Features:
    - Priority-based execution
    - Recurring tasks with intervals
    - Event-triggered tasks
    - Graceful handling of failures
    """

    def __init__(self, max_concurrent: int = 3):
        """Initialize scheduler.

        Args:
            max_concurrent: Maximum concurrent tasks
        """
        self._task_queue: List[ScheduledTask] = []
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._max_concurrent = max_concurrent
        self._active_tasks: set = set()
        self._task_id_counter = 0

    def add_recurring_task(
        self,
        name: str,
        coroutine_factory: Callable[[], Coroutine],
        interval_seconds: int,
        priority: TaskPriority = TaskPriority.NORMAL,
        initial_delay_seconds: int = 0,
    ) -> str:
        """Add a recurring task.

        Args:
            name: Human-readable task name
            coroutine_factory: Function that returns a coroutine
            interval_seconds: Seconds between runs
            priority: Task priority
            initial_delay_seconds: Delay before first run

        Returns:
            Task ID
        """
        self._task_id_counter += 1
        task_id = f"task_{self._task_id_counter}_{name.lower().replace(' ', '_')}"

        scheduled_time = datetime.now() + timedelta(seconds=initial_delay_seconds)

        task = ScheduledTask(
            priority=priority.value,
            scheduled_time=scheduled_time,
            task_id=task_id,
            name=name,
            coroutine_factory=coroutine_factory,
            interval_seconds=interval_seconds,
        )

        self._tasks[task_id] = task
        heappush(self._task_queue, task)

        logger.info(
            "scheduled_recurring_task",
            task_id=task_id,
            name=name,
            interval=interval_seconds,
            first_run=scheduled_time.isoformat(),
        )

        return task_id

    def add_one_time_task(
        self,
        name: str,
        coroutine_factory: Callable[[], Coroutine],
        delay_seconds: int = 0,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> str:
        """Add a one-time task.

        Args:
            name: Human-readable task name
            coroutine_factory: Function that returns a coroutine
            delay_seconds: Delay before execution
            priority: Task priority

        Returns:
            Task ID
        """
        self._task_id_counter += 1
        task_id = f"once_{self._task_id_counter}_{name.lower().replace(' ', '_')}"

        scheduled_time = datetime.now() + timedelta(seconds=delay_seconds)

        task = ScheduledTask(
            priority=priority.value,
            scheduled_time=scheduled_time,
            task_id=task_id,
            name=name,
            coroutine_factory=coroutine_factory,
            interval_seconds=None,  # One-time
        )

        self._tasks[task_id] = task
        heappush(self._task_queue, task)

        logger.info(
            "scheduled_one_time_task",
            task_id=task_id,
            name=name,
            run_at=scheduled_time.isoformat(),
        )

        return task_id

    def trigger_task(self, task_id: str) -> bool:
        """Trigger a task to run immediately.

        Args:
            task_id: Task ID to trigger

        Returns:
            True if task was triggered
        """
        if task_id not in self._tasks:
            logger.warning("trigger_unknown_task", task_id=task_id)
            return False

        task = self._tasks[task_id]
        task.scheduled_time = datetime.now()

        # Re-add to queue with updated time
        heappush(self._task_queue, task)

        logger.info("triggered_task", task_id=task_id, name=task.name)
        return True

    def disable_task(self, task_id: str) -> bool:
        """Disable a task.

        Args:
            task_id: Task ID to disable

        Returns:
            True if task was disabled
        """
        if task_id not in self._tasks:
            return False

        self._tasks[task_id].enabled = False
        logger.info("disabled_task", task_id=task_id)
        return True

    def enable_task(self, task_id: str) -> bool:
        """Enable a task.

        Args:
            task_id: Task ID to enable

        Returns:
            True if task was enabled
        """
        if task_id not in self._tasks:
            return False

        self._tasks[task_id].enabled = True
        logger.info("enabled_task", task_id=task_id)
        return True

    async def start(self) -> None:
        """Start the scheduler loop."""
        self._running = True
        logger.info("scheduler_started", max_concurrent=self._max_concurrent)

        while self._running:
            try:
                await self._process_queue()
                await asyncio.sleep(1)  # Check queue every second
            except Exception as e:
                logger.error("scheduler_error", error=str(e))
                await asyncio.sleep(5)

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        logger.info("scheduler_stopping")

    async def _process_queue(self) -> None:
        """Process tasks from the queue."""
        now = datetime.now()

        while self._task_queue and len(self._active_tasks) < self._max_concurrent:
            # Peek at next task
            if not self._task_queue:
                break

            task = self._task_queue[0]

            # Check if it's time to run
            if task.scheduled_time > now:
                break

            # Pop the task
            heappop(self._task_queue)

            # Skip if disabled or already running
            if not task.enabled or task.task_id in self._active_tasks:
                continue

            # Run the task
            self._active_tasks.add(task.task_id)
            asyncio.create_task(self._run_task(task))

    async def _run_task(self, task: ScheduledTask) -> None:
        """Run a single task.

        Args:
            task: Task to run
        """
        start_time = datetime.now()
        success = False

        try:
            logger.info("task_starting", task_id=task.task_id, name=task.name)

            # Create and run coroutine
            coro = task.coroutine_factory()
            await coro

            success = True
            task.run_count += 1
            task.last_run = datetime.now()

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(
                "task_completed",
                task_id=task.task_id,
                name=task.name,
                duration_seconds=duration,
                run_count=task.run_count,
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(
                "task_failed",
                task_id=task.task_id,
                name=task.name,
                error=str(e),
                duration_seconds=duration,
            )

        finally:
            self._active_tasks.discard(task.task_id)

            # Reschedule if recurring
            if task.interval_seconds is not None and task.enabled:
                task.scheduled_time = datetime.now() + timedelta(seconds=task.interval_seconds)
                heappush(self._task_queue, task)

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status.

        Returns:
            Status dictionary
        """
        return {
            "running": self._running,
            "total_tasks": len(self._tasks),
            "queued_tasks": len(self._task_queue),
            "active_tasks": len(self._active_tasks),
            "tasks": {
                task_id: {
                    "name": task.name,
                    "enabled": task.enabled,
                    "run_count": task.run_count,
                    "last_run": task.last_run.isoformat() if task.last_run else None,
                    "next_run": task.scheduled_time.isoformat(),
                    "interval_seconds": task.interval_seconds,
                }
                for task_id, task in self._tasks.items()
            },
        }

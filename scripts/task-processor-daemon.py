#!/usr/bin/env python3
"""
Task Processor Daemon for Autonomous Claude Code Execution

Polls agent-runtime-mcp task queue and executes tasks via headless Claude Code.
Integrates with enhanced-memory-mcp for outcome recording and learning.

Based on architecture defined in:
/mnt/agentic-system/docs/HEADLESS-CLAUDE-ARCHITECTURE.md
"""

import asyncio
import json
import logging
import os
import re
import signal
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import yaml

# Import notification helper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from notification_helper import notify_sync, notify_task_complete, notify_task_failed
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False

# Configuration
DEFAULT_CONFIG = {
    "db_path": os.path.expanduser("~/.claude/agent_runtime.db"),
    "kill_switch": "/mnt/agentic-system/config/autonomous-mode-enabled",
    "cost_limits_file": "/mnt/agentic-system/config/autonomous-cost-limits.yaml",
    "log_file": "/var/log/claude-task-processor.log",
    "state_file": "/mnt/agentic-system/databases/task_processor_state.json",
    "max_tasks_per_run": 3,
    "min_priority": 5,
    "execution_timeout_seconds": 1800,  # 30 minutes
    "retry_max_attempts": 3,
    "retry_backoff_base": 60,  # seconds
    "circuit_breaker_threshold": 3,
    "cooldown_after_failure_minutes": 15,
    "max_tasks_per_hour": 10,
    "max_cost_per_day_usd": 50.0,
    "default_model": "sonnet",
    "fallback_model": "haiku",
    "max_turns": 50,
}

FORBIDDEN_PATTERNS = [
    r'rm\s+-rf\s+/',           # Recursive delete from root
    r'sudo\s+',                 # Privilege escalation
    r'chmod\s+777',             # Insecure permissions
    r'curl.*\|\s*bash',         # Pipe to shell
    r'eval\s*\(',               # Dynamic code execution
    r'\.\./',                   # Path traversal
    r'/etc/(passwd|shadow)',    # Sensitive files
    r'~/.ssh/',                 # SSH keys
    r'\.env\b',                 # Environment files (secrets)
    r'--dangerously',           # Meta: prevent recursive bypass
    r'\breboot\b|\bshutdown\b|\bhalt\b',  # System control
    r'docker\s+rm\s+-f',        # Force container removal
    r'systemctl\s+(stop|disable)\s+', # Service disruption
    r'DROP\s+DATABASE',         # Database destruction
    r'TRUNCATE\s+TABLE',        # Data destruction
]

ALLOWED_TOOLS = [
    "Bash",
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "WebFetch",
    "WebSearch",
    "mcp__agent-runtime__*",
    "mcp__enhanced-memory__*",
    "mcp__code-execution__*",
]

DISALLOWED_TOOLS = [
    "Bash(rm -rf:*)",
    "Bash(sudo:*)",
    "Bash(chmod 777:*)",
    "Bash(shutdown:*)",
    "Bash(reboot:*)",
]


def setup_logging(log_file: str) -> logging.Logger:
    """Configure logging to both console and file"""
    logger = logging.getLogger("TaskProcessor")
    logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler (if writable)
    log_path = Path(log_file)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(console_format)
        logger.addHandler(file_handler)
    except PermissionError:
        logger.warning(f"Cannot write to {log_file}, using console only")

    return logger


@dataclass
class Task:
    id: int
    goal_id: Optional[int]
    title: str
    description: Optional[str]
    status: str
    priority: int
    dependencies: Optional[str] = None
    metadata: Optional[str] = None
    retry_count: int = 0


@dataclass
class ExecutionResult:
    success: bool
    output: str
    error: Optional[str]
    tokens_used: int
    execution_time_seconds: float
    cost_estimate_usd: float
    model_used: str = "unknown"


@dataclass
class ProcessorState:
    last_run: Optional[str] = None
    tasks_processed_today: int = 0
    cost_today_usd: float = 0.0
    consecutive_failures: int = 0
    tasks_this_hour: int = 0
    hour_started: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "last_run": self.last_run,
            "tasks_processed_today": self.tasks_processed_today,
            "cost_today_usd": self.cost_today_usd,
            "consecutive_failures": self.consecutive_failures,
            "tasks_this_hour": self.tasks_this_hour,
            "hour_started": self.hour_started,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ProcessorState':
        return cls(
            last_run=data.get("last_run"),
            tasks_processed_today=data.get("tasks_processed_today", 0),
            cost_today_usd=data.get("cost_today_usd", 0.0),
            consecutive_failures=data.get("consecutive_failures", 0),
            tasks_this_hour=data.get("tasks_this_hour", 0),
            hour_started=data.get("hour_started"),
        )


class TaskProcessor:
    def __init__(self, config: Optional[dict] = None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.logger = setup_logging(self.config["log_file"])
        self.state = self._load_state()
        self._reset_hourly_counter_if_needed()
        self._reset_daily_counter_if_needed()

    def _load_state(self) -> ProcessorState:
        """Load processor state from file"""
        state_file = Path(self.config["state_file"])
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                return ProcessorState.from_dict(data)
            except Exception as e:
                self.logger.warning(f"Failed to load state: {e}")
        return ProcessorState()

    def _save_state(self):
        """Save processor state to file"""
        state_file = Path(self.config["state_file"])
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(self.state.to_dict(), indent=2))

    def _reset_hourly_counter_if_needed(self):
        """Reset hourly task counter if hour changed"""
        current_hour = datetime.now().strftime("%Y-%m-%d-%H")
        if self.state.hour_started != current_hour:
            self.state.tasks_this_hour = 0
            self.state.hour_started = current_hour

    def _reset_daily_counter_if_needed(self):
        """Reset daily counters if day changed"""
        if self.state.last_run:
            last_date = self.state.last_run[:10]  # YYYY-MM-DD
            current_date = datetime.now().strftime("%Y-%m-%d")
            if last_date != current_date:
                self.state.tasks_processed_today = 0
                self.state.cost_today_usd = 0.0
                self.logger.info("Daily counters reset")

    def check_kill_switch(self) -> bool:
        """Check if autonomous mode is enabled"""
        enabled = Path(self.config["kill_switch"]).exists()
        if not enabled:
            self.logger.info("Autonomous mode disabled (kill switch file missing)")
        return enabled

    def check_circuit_breaker(self) -> bool:
        """Check if we should pause due to consecutive failures"""
        if self.state.consecutive_failures >= self.config["circuit_breaker_threshold"]:
            self.logger.warning(
                f"Circuit breaker tripped: {self.state.consecutive_failures} consecutive failures. "
                f"Waiting {self.config['cooldown_after_failure_minutes']} minutes."
            )
            return False
        return True

    def check_rate_limits(self) -> bool:
        """Check if we're within rate limits"""
        # Hourly limit
        if self.state.tasks_this_hour >= self.config["max_tasks_per_hour"]:
            self.logger.warning(f"Hourly task limit reached ({self.config['max_tasks_per_hour']})")
            return False

        # Daily cost limit
        if self.state.cost_today_usd >= self.config["max_cost_per_day_usd"]:
            self.logger.warning(f"Daily cost limit reached (${self.config['max_cost_per_day_usd']:.2f})")
            return False

        return True

    def validate_task(self, task: Task) -> tuple[bool, str]:
        """Validate task content against security rules"""
        content = f"{task.title} {task.description or ''}"

        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return False, f"Forbidden pattern detected: {pattern}"

        # Check for minimum content
        if len(task.title.strip()) < 5:
            return False, "Task title too short (min 5 characters)"

        return True, "OK"

    def get_db_connection(self) -> sqlite3.Connection:
        """Get SQLite database connection"""
        return sqlite3.connect(self.config["db_path"])

    def get_pending_tasks(self) -> List[Task]:
        """Fetch pending tasks from queue ordered by priority"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, goal_id, title, description, status, priority, dependencies, metadata
                FROM tasks
                WHERE status = 'pending' AND priority >= ?
                ORDER BY priority DESC, created_at ASC
                LIMIT ?
            """, (self.config["min_priority"], self.config["max_tasks_per_run"]))

            tasks = []
            for row in cursor.fetchall():
                tasks.append(Task(
                    id=row[0],
                    goal_id=row[1],
                    title=row[2],
                    description=row[3],
                    status=row[4],
                    priority=row[5],
                    dependencies=row[6],
                    metadata=row[7]
                ))

            return tasks
        finally:
            conn.close()

    def check_dependencies(self, task: Task) -> bool:
        """Check if task dependencies are satisfied"""
        if not task.dependencies:
            return True

        try:
            dep_ids = json.loads(task.dependencies)
            if not dep_ids:
                return True

            conn = self.get_db_connection()
            cursor = conn.cursor()

            placeholders = ','.join('?' * len(dep_ids))
            cursor.execute(f"""
                SELECT COUNT(*) FROM tasks
                WHERE id IN ({placeholders}) AND status != 'completed'
            """, dep_ids)

            incomplete_count = cursor.fetchone()[0]
            conn.close()

            if incomplete_count > 0:
                self.logger.info(f"Task {task.id} has {incomplete_count} incomplete dependencies")
                return False

            return True
        except (json.JSONDecodeError, TypeError):
            return True

    def update_task_status(
        self,
        task_id: int,
        status: str,
        result: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Update task status in database"""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            if status == "in_progress":
                cursor.execute("""
                    UPDATE tasks
                    SET status = ?, started_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, task_id))
            elif status == "completed":
                cursor.execute("""
                    UPDATE tasks
                    SET status = ?, result = ?, completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, result, task_id))
            elif status == "failed":
                cursor.execute("""
                    UPDATE tasks
                    SET status = ?, error = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, error, task_id))
            else:
                cursor.execute("""
                    UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, task_id))

            conn.commit()
        finally:
            conn.close()

    def build_prompt(self, task: Task) -> str:
        """Build execution prompt for headless Claude Code"""
        goal_context = ""
        if task.goal_id:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name, description FROM goals WHERE id = ?", (task.goal_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                goal_context = f"""
## Parent Goal
- **Name**: {row[0]}
- **Description**: {row[1]}
"""

        return f"""# Autonomous Task Execution

## Task Details
- **Task ID**: {task.id}
- **Title**: {task.title}
- **Priority**: {task.priority}/10
- **Description**: {task.description or 'No additional description provided'}
{goal_context}
## Execution Instructions

You are executing this task autonomously as part of the AGI task queue system.
Complete the task to the best of your ability using available tools.

### Available Resources
- File operations: Read, Write, Edit, Glob, Grep
- Bash commands (with safety restrictions)
- Web search and fetch capabilities
- agent-runtime-mcp: Task queue management
- enhanced-memory-mcp: Persistent memory and learning

### Required Actions
1. Analyze the task requirements
2. Plan your approach
3. Execute using appropriate tools
4. Record the outcome for learning
5. Provide a clear summary of what was accomplished

### Safety Constraints
- Do not modify system files outside /mnt/agentic-system and /home/marc
- Do not execute destructive commands (rm -rf, etc.)
- Do not access credentials, secrets, or SSH keys
- Stay within the scope of this specific task
- If uncertain, document uncertainty rather than proceeding blindly

### Outcome Recording
After completing the task, use enhanced-memory-mcp to record:
- What was attempted
- What was achieved
- Any insights or learnings
- Suggested follow-up tasks (if any)

Begin execution now. Work methodically and explain your reasoning.
"""

    def estimate_cost(self, tokens: int, model: str = "sonnet") -> float:
        """Estimate cost based on token usage and model"""
        # Approximate costs per million tokens (combined input/output average)
        costs_per_million = {
            "sonnet": 10.0,   # ~$3 input, $15 output -> avg ~$10
            "haiku": 1.0,    # Much cheaper
            "opus": 50.0,    # Premium
        }
        rate = costs_per_million.get(model, 10.0)
        return (tokens / 1_000_000) * rate

    def execute_task(self, task: Task) -> ExecutionResult:
        """Execute task via headless Claude Code"""
        start_time = time.time()
        prompt = self.build_prompt(task)

        # Build command
        cmd = [
            "claude",
            "--print",
            "--dangerously-skip-permissions",
            "--output-format", "json",
            "--model", self.config["default_model"],
            "--fallback-model", self.config["fallback_model"],
            "--max-turns", str(self.config["max_turns"]),
            "--allowedTools", ",".join(ALLOWED_TOOLS),
            "--disallowedTools", ",".join(DISALLOWED_TOOLS),
            "--append-system-prompt",
            "AUTONOMOUS MODE: You are executing a queued task. Record outcomes to enhanced-memory-mcp.",
        ]

        self.logger.info(f"Executing: claude --print ... (task {task.id})")

        try:
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.config["execution_timeout_seconds"],
                env={
                    **os.environ,
                    "HOME": os.path.expanduser("~"),
                    "PATH": f"{os.path.expanduser('~')}/.local/bin:{os.environ.get('PATH', '')}"
                },
                cwd=os.path.expanduser("~")
            )

            execution_time = time.time() - start_time

            if result.returncode == 0:
                try:
                    output_data = json.loads(result.stdout)
                    usage = output_data.get("usage", {})
                    tokens_used = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                    model_used = output_data.get("model", self.config["default_model"])
                    cost_estimate = self.estimate_cost(tokens_used, model_used)

                    return ExecutionResult(
                        success=True,
                        output=output_data.get("content", result.stdout),
                        error=None,
                        tokens_used=tokens_used,
                        execution_time_seconds=execution_time,
                        cost_estimate_usd=cost_estimate,
                        model_used=model_used
                    )
                except json.JSONDecodeError:
                    # Non-JSON output, still success
                    return ExecutionResult(
                        success=True,
                        output=result.stdout,
                        error=None,
                        tokens_used=0,
                        execution_time_seconds=execution_time,
                        cost_estimate_usd=0.0,
                        model_used="unknown"
                    )
            else:
                error_msg = result.stderr or "Unknown error (non-zero exit code)"
                return ExecutionResult(
                    success=False,
                    output=result.stdout,
                    error=error_msg,
                    tokens_used=0,
                    execution_time_seconds=execution_time,
                    cost_estimate_usd=0.0
                )

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Execution timed out after {self.config['execution_timeout_seconds']} seconds",
                tokens_used=0,
                execution_time_seconds=self.config["execution_timeout_seconds"],
                cost_estimate_usd=0.0
            )
        except FileNotFoundError:
            return ExecutionResult(
                success=False,
                output="",
                error="Claude CLI not found. Ensure 'claude' is in PATH.",
                tokens_used=0,
                execution_time_seconds=0,
                cost_estimate_usd=0.0
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                tokens_used=0,
                execution_time_seconds=time.time() - start_time,
                cost_estimate_usd=0.0
            )

    def process_tasks(self) -> dict:
        """Main task processing loop - returns summary of run"""
        run_summary = {
            "started_at": datetime.now().isoformat(),
            "tasks_found": 0,
            "tasks_processed": 0,
            "tasks_succeeded": 0,
            "tasks_failed": 0,
            "tasks_skipped": 0,
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "errors": [],
        }

        self.logger.info("=" * 60)
        self.logger.info("Starting task processing run")

        # Pre-flight checks
        if not self.check_kill_switch():
            run_summary["errors"].append("Autonomous mode disabled")
            return run_summary

        if not self.check_circuit_breaker():
            run_summary["errors"].append("Circuit breaker active")
            return run_summary

        if not self.check_rate_limits():
            run_summary["errors"].append("Rate limit reached")
            return run_summary

        # Get pending tasks
        tasks = self.get_pending_tasks()
        run_summary["tasks_found"] = len(tasks)

        if not tasks:
            self.logger.info("No pending tasks to process")
            return run_summary

        self.logger.info(f"Found {len(tasks)} pending tasks")

        for task in tasks:
            # Check rate limits again (may have changed during processing)
            if not self.check_rate_limits():
                self.logger.warning("Rate limit reached mid-run, stopping")
                break

            # Check dependencies
            if not self.check_dependencies(task):
                self.logger.info(f"Task {task.id} has unmet dependencies, skipping")
                run_summary["tasks_skipped"] += 1
                continue

            # Validate task
            valid, reason = self.validate_task(task)
            if not valid:
                self.logger.warning(f"Task {task.id} failed validation: {reason}")
                self.update_task_status(task.id, "failed", error=f"Validation failed: {reason}")
                run_summary["tasks_failed"] += 1
                run_summary["errors"].append(f"Task {task.id}: {reason}")
                continue

            # Mark as in progress
            self.update_task_status(task.id, "in_progress")
            self.logger.info(f"Executing task {task.id}: {task.title}")

            # Execute
            result = self.execute_task(task)
            run_summary["tasks_processed"] += 1

            if result.success:
                self.update_task_status(task.id, "completed", result=result.output[:10000])  # Truncate
                self.state.consecutive_failures = 0
                self.state.tasks_processed_today += 1
                self.state.tasks_this_hour += 1
                self.state.cost_today_usd += result.cost_estimate_usd
                run_summary["tasks_succeeded"] += 1
                run_summary["total_cost_usd"] += result.cost_estimate_usd
                run_summary["total_tokens"] += result.tokens_used

                self.logger.info(
                    f"Task {task.id} completed successfully "
                    f"(tokens: {result.tokens_used}, cost: ${result.cost_estimate_usd:.4f}, "
                    f"time: {result.execution_time_seconds:.1f}s)"
                )

                # Send notification
                if NOTIFICATIONS_AVAILABLE:
                    import asyncio
                    try:
                        asyncio.run(notify_task_complete(task.title, task.id, "success"))
                    except Exception as e:
                        self.logger.warning(f"Notification failed: {e}")
            else:
                self.update_task_status(task.id, "failed", error=result.error)
                self.state.consecutive_failures += 1
                run_summary["tasks_failed"] += 1
                run_summary["errors"].append(f"Task {task.id}: {result.error}")

                self.logger.error(f"Task {task.id} failed: {result.error}")

                # Send failure notification
                if NOTIFICATIONS_AVAILABLE:
                    import asyncio
                    try:
                        asyncio.run(notify_task_failed(task.title, task.id, result.error or "Unknown error"))
                    except Exception as e:
                        self.logger.warning(f"Notification failed: {e}")

        # Update state
        self.state.last_run = datetime.now().isoformat()
        self._save_state()

        run_summary["ended_at"] = datetime.now().isoformat()
        self.logger.info(
            f"Task processing complete: {run_summary['tasks_succeeded']} succeeded, "
            f"{run_summary['tasks_failed']} failed, {run_summary['tasks_skipped']} skipped"
        )
        self.logger.info("=" * 60)

        return run_summary


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Claude Code Autonomous Task Processor")
    parser.add_argument("--dry-run", action="store_true", help="Show pending tasks without executing")
    parser.add_argument("--status", action="store_true", help="Show processor status")
    parser.add_argument("--reset-circuit-breaker", action="store_true", help="Reset circuit breaker")
    args = parser.parse_args()

    processor = TaskProcessor()

    if args.status:
        print(json.dumps(processor.state.to_dict(), indent=2))
        print(f"\nKill switch: {'ENABLED' if processor.check_kill_switch() else 'DISABLED'}")
        print(f"Circuit breaker: {'OK' if processor.check_circuit_breaker() else 'TRIPPED'}")
        print(f"Rate limits: {'OK' if processor.check_rate_limits() else 'EXCEEDED'}")
        return

    if args.reset_circuit_breaker:
        processor.state.consecutive_failures = 0
        processor._save_state()
        print("Circuit breaker reset")
        return

    if args.dry_run:
        tasks = processor.get_pending_tasks()
        print(f"Found {len(tasks)} pending tasks:")
        for task in tasks:
            print(f"  [{task.id}] Priority {task.priority}: {task.title}")
        return

    # Normal execution
    summary = processor.process_tasks()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

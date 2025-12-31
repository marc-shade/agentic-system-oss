"""
Todo Manager - Attention manipulation via todo.md pattern.

Key insight from Manus context engineering:
- Constantly rewriting todo.md "recites objectives into the end of context"
- Pushes goals into model's recent attention span
- Combats "lost in the middle" issues in 50+ tool call sequences
"""

import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class StepStatus(Enum):
    """Status of a plan step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """Single step in the plan."""
    number: int
    description: str
    tools: list[str]
    expected_outcome: str = ""
    status: StepStatus = StepStatus.PENDING
    notes: str = ""

    def to_markdown(self) -> str:
        """Format step as markdown checkbox."""
        checkbox = {
            StepStatus.PENDING: "[ ]",
            StepStatus.IN_PROGRESS: "[>]",
            StepStatus.COMPLETED: "[x]",
            StepStatus.FAILED: "[!]",
            StepStatus.SKIPPED: "[-]"
        }[self.status]

        tools_str = f" (tools: {', '.join(self.tools)})" if self.tools else ""
        notes_str = f" - {self.notes}" if self.notes else ""

        return f"- {checkbox} {self.number}. {self.description}{tools_str}{notes_str}"


class TodoManager:
    """
    Manages todo.md for attention manipulation.

    The key insight: By rewriting todo.md after each step,
    we push the current goals into the recent part of the
    context window, keeping the model focused on what matters.
    """

    def __init__(self, workspace: Path):
        self.workspace = Path(workspace)
        self.todo_path = self.workspace / "todo.md"
        self.steps: list[PlanStep] = []
        self.task_description = ""
        self.created_at = time.time()

    def initialize(self, task: str, steps: list[dict]) -> None:
        """
        Initialize todo.md with a new task plan.

        Args:
            task: The original task description
            steps: List of dicts with 'description' and optional 'tools' keys
        """
        self.task_description = task
        self.steps = []

        for i, step in enumerate(steps, 1):
            self.steps.append(PlanStep(
                number=i,
                description=step.get("description", str(step)),
                tools=step.get("tools", []),
                status=StepStatus.PENDING
            ))

        self._write()

    def start_step(self, step_number: int) -> None:
        """Mark a step as in progress."""
        for step in self.steps:
            if step.number == step_number:
                step.status = StepStatus.IN_PROGRESS
                break
        self._write()

    def complete_step(self, step_number: int, notes: str = "") -> None:
        """Mark a step as completed."""
        for step in self.steps:
            if step.number == step_number:
                step.status = StepStatus.COMPLETED
                if notes:
                    step.notes = notes
                break
        self._write()

    def fail_step(self, step_number: int, error: str) -> None:
        """Mark a step as failed."""
        for step in self.steps:
            if step.number == step_number:
                step.status = StepStatus.FAILED
                step.notes = f"ERROR: {error}"
                break
        self._write()

    def skip_step(self, step_number: int, reason: str = "") -> None:
        """Mark a step as skipped."""
        for step in self.steps:
            if step.number == step_number:
                step.status = StepStatus.SKIPPED
                step.notes = f"Skipped: {reason}" if reason else "Skipped"
                break
        self._write()

    def add_step(self, description: str, tools: list[str] = None, after: int = None) -> int:
        """Add a new step (for replanning)."""
        new_number = len(self.steps) + 1

        if after is not None:
            # Insert after specific step, renumber subsequent
            new_step = PlanStep(
                number=after + 1,
                description=description,
                tools=tools or []
            )
            # Renumber
            for step in self.steps:
                if step.number > after:
                    step.number += 1
            self.steps.insert(after, new_step)
            new_number = after + 1
        else:
            self.steps.append(PlanStep(
                number=new_number,
                description=description,
                tools=tools or []
            ))

        self._write()
        return new_number

    def get_current_step(self) -> Optional[PlanStep]:
        """Get the current in-progress step."""
        for step in self.steps:
            if step.status == StepStatus.IN_PROGRESS:
                return step
        # If no in_progress, get first pending
        for step in self.steps:
            if step.status == StepStatus.PENDING:
                return step
        return None

    def get_pending_steps(self) -> list[PlanStep]:
        """Get all pending steps."""
        return [s for s in self.steps if s.status == StepStatus.PENDING]

    def get_focus_context(self) -> str:
        """
        Get focused context for attention manipulation.

        This is the key method - returns the current state
        in a format that pushes goals into recent attention.
        """
        current = self.get_current_step()
        pending = self.get_pending_steps()[:3]  # Top 3 pending

        lines = ["## Current Focus"]

        if current:
            lines.append(f"NOW: {current.description}")
            if current.tools:
                lines.append(f"Tools: {', '.join(current.tools)}")

        if pending:
            lines.append("\n## Next Steps")
            for step in pending:
                lines.append(f"- {step.number}. {step.description}")

        return "\n".join(lines)

    def is_complete(self) -> bool:
        """Check if all steps are done."""
        return all(
            s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
            for s in self.steps
        )

    def get_progress(self) -> tuple[int, int]:
        """Get (completed_count, total_count)."""
        completed = sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)
        return completed, len(self.steps)

    def _write(self) -> None:
        """
        Write todo.md to disk.

        CRITICAL: This is called after every state change.
        The act of rewriting pushes goals into recent context.
        """
        self.workspace.mkdir(parents=True, exist_ok=True)

        content = self._generate_markdown()

        with open(self.todo_path, "w") as f:
            f.write(content)

    def _generate_markdown(self) -> str:
        """Generate full markdown content."""
        lines = [
            f"# Task: {self.task_description}",
            "",
            f"Progress: {self.get_progress()[0]}/{self.get_progress()[1]}",
            "",
            "## Steps",
            ""
        ]

        for step in self.steps:
            lines.append(step.to_markdown())

        lines.extend([
            "",
            "---",
            self.get_focus_context()
        ])

        return "\n".join(lines)

    def read(self) -> str:
        """Read current todo.md content."""
        if self.todo_path.exists():
            return self.todo_path.read_text()
        return ""

    def __str__(self) -> str:
        return self._generate_markdown()

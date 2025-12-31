"""
Event Stream - Chronological log of agent actions and observations.

Based on Manus context engineering patterns:
- Preserve errors in context (model learns from them)
- Truncate old events when approaching token limit
- Format for LLM context consumption
"""

import json
import time
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Any, Optional
from pathlib import Path


class EventType(Enum):
    """Types of events in the stream."""
    MESSAGE_USER = "message_user"
    MESSAGE_AGENT = "message_agent"
    ACTION = "action"
    OBSERVATION = "observation"
    PLAN = "plan"
    PLAN_UPDATE = "plan_update"
    KNOWLEDGE = "knowledge"
    ERROR = "error"
    SYSTEM = "system"


@dataclass
class Event:
    """Single event in the stream."""
    event_type: EventType
    data: dict
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: f"evt_{int(time.time()*1000)}")

    def to_dict(self) -> dict:
        return {
            "id": self.event_id,
            "type": self.event_type.value,
            "timestamp": self.timestamp,
            "data": self.data
        }

    def format_for_context(self) -> str:
        """Format event for LLM context window."""
        type_label = self.event_type.value.upper()

        if self.event_type == EventType.ACTION:
            tool = self.data.get("tool", "unknown")
            params = json.dumps(self.data.get("params", {}), indent=2)
            return f"[{type_label}] Tool: {tool}\nParams: {params}"

        elif self.event_type == EventType.OBSERVATION:
            result = self.data.get("result", "")
            # Truncate very long observations
            if len(result) > 2000:
                result = result[:1000] + "\n...[truncated]...\n" + result[-500:]
            return f"[{type_label}]\n{result}"

        elif self.event_type == EventType.ERROR:
            error = self.data.get("error", "Unknown error")
            trace = self.data.get("traceback", "")
            # IMPORTANT: Keep errors visible - model learns from them
            return f"[{type_label}] {error}\n{trace}"

        elif self.event_type == EventType.PLAN:
            steps = self.data.get("steps", [])
            return f"[{type_label}]\n" + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps))

        else:
            return f"[{type_label}] {json.dumps(self.data)}"

    @classmethod
    def action(cls, tool: str, params: dict) -> "Event":
        """Create an action event."""
        return cls(
            event_type=EventType.ACTION,
            data={"tool": tool, "params": params}
        )

    @classmethod
    def observation(cls, result: str, success: bool = True) -> "Event":
        """Create an observation event."""
        return cls(
            event_type=EventType.OBSERVATION,
            data={"result": result, "success": success}
        )

    @classmethod
    def error(cls, error: str, traceback: str = "") -> "Event":
        """Create an error event. PRESERVED in context for learning."""
        return cls(
            event_type=EventType.ERROR,
            data={"error": error, "traceback": traceback}
        )

    @classmethod
    def plan(cls, steps: list, current_step: int = 0) -> "Event":
        """Create a plan event."""
        return cls(
            event_type=EventType.PLAN,
            data={"steps": steps, "current_step": current_step}
        )


class EventStream:
    """
    Chronological log of all agent events.

    Key patterns from Manus:
    - One tool call per iteration (enforced by caller)
    - Errors preserved (not hidden) - model learns from failures
    - Truncation of old events when approaching token limit
    - File-based persistence for long tasks
    """

    def __init__(self, max_tokens: int = 32000, workspace: Optional[Path] = None):
        self.events: list[Event] = []
        self.max_tokens = max_tokens
        self.workspace = workspace
        self._token_count = 0

    def append(self, event: Event) -> None:
        """Add event to stream."""
        self.events.append(event)
        self._update_token_count()

        # Persist if workspace configured
        if self.workspace:
            self._persist_event(event)

    def append_action_observation(self, tool: str, params: dict, result: str, success: bool = True) -> None:
        """Convenience method to add action and its observation."""
        self.append(Event.action(tool, params))
        self.append(Event.observation(result, success))

    def append_error(self, error: str, traceback: str = "") -> None:
        """Add error event. CRITICAL: Errors are preserved for learning."""
        self.append(Event.error(error, traceback))

    def append_plan(self, steps: list, current_step: int = 0) -> None:
        """Add or update plan."""
        self.append(Event.plan(steps, current_step))

    def to_context(self) -> str:
        """Format entire stream for LLM context."""
        self._truncate_if_needed()
        return "\n\n".join(e.format_for_context() for e in self.events)

    def get_recent(self, n: int = 10) -> list[Event]:
        """Get n most recent events."""
        return self.events[-n:]

    def get_errors(self) -> list[Event]:
        """Get all error events (for analysis)."""
        return [e for e in self.events if e.event_type == EventType.ERROR]

    def _update_token_count(self) -> None:
        """Estimate token count (rough: 4 chars per token)."""
        total = sum(len(e.format_for_context()) for e in self.events)
        self._token_count = total // 4

    def _truncate_if_needed(self) -> None:
        """Remove old events if exceeding token limit."""
        while self._token_count > self.max_tokens and len(self.events) > 5:
            # Keep at least recent 5 events
            removed = self.events.pop(0)

            # But NEVER remove errors - they're learning opportunities
            if removed.event_type == EventType.ERROR:
                self.events.insert(0, removed)
                if len(self.events) > 1:
                    self.events.pop(1)

            self._update_token_count()

    def _persist_event(self, event: Event) -> None:
        """Save event to file for recovery."""
        if not self.workspace:
            return
        events_file = self.workspace / "events.jsonl"
        with open(events_file, "a") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

    def save(self, path: Path) -> None:
        """Save entire stream to file."""
        with open(path, "w") as f:
            json.dump([e.to_dict() for e in self.events], f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "EventStream":
        """Load stream from file."""
        stream = cls()
        with open(path) as f:
            data = json.load(f)
        for item in data:
            event = Event(
                event_type=EventType(item["type"]),
                data=item["data"],
                timestamp=item["timestamp"],
                event_id=item["id"]
            )
            stream.events.append(event)
        return stream

    def __len__(self) -> int:
        return len(self.events)

    def __iter__(self):
        return iter(self.events)

"""
Real-Time Streaming - WebSocket-based output streaming for Prometheus.

This is the final piece for full Manus parity: streaming execution
output in real-time rather than batch responses.

Features:
- WebSocket server for live updates
- Event types: plan, action, observation, error, complete
- Client subscription management
- Buffered replay for late joiners
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Optional, Any, Callable, Set
from enum import Enum
from datetime import datetime
import weakref

logger = logging.getLogger(__name__)

# Check for websockets availability
WEBSOCKETS_AVAILABLE = False
try:
    import websockets
    from websockets.server import serve
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    logger.debug("websockets not available, streaming disabled")


class StreamEventType(Enum):
    """Types of streaming events."""
    # Lifecycle events
    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"
    TASK_ERROR = "task_error"

    # Planning events
    PLAN_START = "plan_start"
    PLAN_STEP = "plan_step"
    PLAN_COMPLETE = "plan_complete"

    # Execution events
    ACTION_START = "action_start"
    ACTION_PROGRESS = "action_progress"
    ACTION_COMPLETE = "action_complete"

    # Observation events
    OBSERVATION = "observation"
    VISUAL_OBSERVATION = "visual_observation"

    # Parallel execution events
    PARALLEL_GROUP_START = "parallel_group_start"
    PARALLEL_STEP_COMPLETE = "parallel_step_complete"
    PARALLEL_GROUP_COMPLETE = "parallel_group_complete"

    # System events
    HEARTBEAT = "heartbeat"
    ERROR = "error"


@dataclass
class StreamEvent:
    """A single streaming event."""
    event_type: StreamEventType
    task_id: str
    data: dict
    timestamp: str = ""
    sequence: int = 0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_json(self) -> str:
        """Convert to JSON string for transmission."""
        return json.dumps({
            "type": self.event_type.value,
            "task_id": self.task_id,
            "data": self.data,
            "timestamp": self.timestamp,
            "sequence": self.sequence
        })

    @classmethod
    def from_json(cls, json_str: str) -> "StreamEvent":
        """Parse from JSON string."""
        data = json.loads(json_str)
        return cls(
            event_type=StreamEventType(data["type"]),
            task_id=data["task_id"],
            data=data["data"],
            timestamp=data["timestamp"],
            sequence=data["sequence"]
        )


class StreamBuffer:
    """
    Circular buffer for event replay.

    Allows late-joining clients to catch up on recent events.
    """

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._buffer: list[StreamEvent] = []
        self._sequence = 0

    def append(self, event: StreamEvent) -> int:
        """Add event to buffer, return sequence number."""
        self._sequence += 1
        event.sequence = self._sequence

        self._buffer.append(event)
        if len(self._buffer) > self.max_size:
            self._buffer.pop(0)

        return self._sequence

    def get_since(self, sequence: int) -> list[StreamEvent]:
        """Get all events since a sequence number."""
        return [e for e in self._buffer if e.sequence > sequence]

    def get_all(self) -> list[StreamEvent]:
        """Get all buffered events."""
        return self._buffer.copy()

    def clear(self):
        """Clear buffer."""
        self._buffer.clear()
        self._sequence = 0


class StreamingServer:
    """
    WebSocket server for real-time event streaming.

    Usage:
        server = StreamingServer(port=8765)
        await server.start()

        # Emit events
        server.emit(StreamEvent(
            event_type=StreamEventType.ACTION_START,
            task_id="task_123",
            data={"tool": "bash", "params": {...}}
        ))

        # Stop when done
        await server.stop()
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8765,
        buffer_size: int = 100
    ):
        self.host = host
        self.port = port
        self.buffer = StreamBuffer(max_size=buffer_size)

        self._clients: Set[Any] = set()
        self._server = None
        self._running = False
        self._task_subscriptions: dict[str, Set[Any]] = {}  # task_id -> clients

    async def start(self):
        """Start the WebSocket server."""
        if not WEBSOCKETS_AVAILABLE:
            logger.warning("websockets not installed, streaming unavailable")
            return

        if self._running:
            return

        self._server = await serve(
            self._handle_client,
            self.host,
            self.port
        )
        self._running = True
        logger.info(f"Streaming server started on ws://{self.host}:{self.port}")

        # Start heartbeat task
        asyncio.create_task(self._heartbeat_loop())

    async def stop(self):
        """Stop the WebSocket server."""
        self._running = False

        # Close all client connections
        for client in self._clients.copy():
            try:
                await client.close()
            except Exception:
                pass

        self._clients.clear()

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        logger.info("Streaming server stopped")

    async def _handle_client(self, websocket):
        """Handle a new WebSocket client connection."""
        self._clients.add(websocket)
        logger.info(f"Client connected ({len(self._clients)} total)")

        try:
            # Send buffered events for replay
            for event in self.buffer.get_all():
                await websocket.send(event.to_json())

            # Handle incoming messages (subscriptions, etc.)
            async for message in websocket:
                await self._handle_message(websocket, message)

        except Exception as e:
            logger.debug(f"Client connection error: {e}")
        finally:
            self._clients.discard(websocket)
            # Remove from task subscriptions
            for task_clients in self._task_subscriptions.values():
                task_clients.discard(websocket)
            logger.info(f"Client disconnected ({len(self._clients)} remaining)")

    async def _handle_message(self, websocket, message: str):
        """Handle incoming client message."""
        try:
            data = json.loads(message)
            action = data.get("action")

            if action == "subscribe":
                # Subscribe to specific task
                task_id = data.get("task_id")
                if task_id:
                    if task_id not in self._task_subscriptions:
                        self._task_subscriptions[task_id] = set()
                    self._task_subscriptions[task_id].add(websocket)

            elif action == "unsubscribe":
                task_id = data.get("task_id")
                if task_id and task_id in self._task_subscriptions:
                    self._task_subscriptions[task_id].discard(websocket)

            elif action == "replay":
                # Replay events since sequence
                since = data.get("since", 0)
                for event in self.buffer.get_since(since):
                    await websocket.send(event.to_json())

        except json.JSONDecodeError:
            logger.debug(f"Invalid message from client: {message}")

    async def _heartbeat_loop(self):
        """Send periodic heartbeats to keep connections alive."""
        while self._running:
            await asyncio.sleep(30)  # Every 30 seconds

            event = StreamEvent(
                event_type=StreamEventType.HEARTBEAT,
                task_id="system",
                data={"clients": len(self._clients)}
            )

            await self._broadcast(event)

    async def _broadcast(self, event: StreamEvent):
        """Broadcast event to all connected clients."""
        if not self._clients:
            return

        message = event.to_json()
        dead_clients = set()

        for client in self._clients:
            try:
                await client.send(message)
            except Exception:
                dead_clients.add(client)

        # Clean up dead connections
        self._clients -= dead_clients

    async def _broadcast_to_task(self, event: StreamEvent):
        """Broadcast event to clients subscribed to a specific task."""
        task_id = event.task_id
        clients = self._task_subscriptions.get(task_id, set()) | self._clients

        if not clients:
            return

        message = event.to_json()
        dead_clients = set()

        for client in clients:
            try:
                await client.send(message)
            except Exception:
                dead_clients.add(client)

        # Clean up
        self._clients -= dead_clients
        if task_id in self._task_subscriptions:
            self._task_subscriptions[task_id] -= dead_clients

    def emit(self, event: StreamEvent):
        """
        Emit an event to all connected clients.

        This is fire-and-forget - schedules the broadcast asynchronously.
        """
        # Add to buffer
        self.buffer.append(event)

        # Schedule broadcast
        if self._running and self._clients:
            asyncio.create_task(self._broadcast_to_task(event))

    def emit_task_start(self, task_id: str, description: str):
        """Emit task start event."""
        self.emit(StreamEvent(
            event_type=StreamEventType.TASK_START,
            task_id=task_id,
            data={"description": description}
        ))

    def emit_task_complete(self, task_id: str, success: bool, summary: str):
        """Emit task completion event."""
        self.emit(StreamEvent(
            event_type=StreamEventType.TASK_COMPLETE,
            task_id=task_id,
            data={"success": success, "summary": summary}
        ))

    def emit_plan_step(self, task_id: str, step_number: int, description: str):
        """Emit planning step event."""
        self.emit(StreamEvent(
            event_type=StreamEventType.PLAN_STEP,
            task_id=task_id,
            data={"step": step_number, "description": description}
        ))

    def emit_action_start(self, task_id: str, tool: str, params: dict):
        """Emit action start event."""
        self.emit(StreamEvent(
            event_type=StreamEventType.ACTION_START,
            task_id=task_id,
            data={"tool": tool, "params": params}
        ))

    def emit_action_progress(self, task_id: str, progress: str):
        """Emit action progress event."""
        self.emit(StreamEvent(
            event_type=StreamEventType.ACTION_PROGRESS,
            task_id=task_id,
            data={"progress": progress}
        ))

    def emit_action_complete(self, task_id: str, tool: str, success: bool, result: str):
        """Emit action completion event."""
        self.emit(StreamEvent(
            event_type=StreamEventType.ACTION_COMPLETE,
            task_id=task_id,
            data={"tool": tool, "success": success, "result": result[:500]}
        ))

    def emit_observation(self, task_id: str, observation: str):
        """Emit observation event."""
        self.emit(StreamEvent(
            event_type=StreamEventType.OBSERVATION,
            task_id=task_id,
            data={"observation": observation[:1000]}
        ))

    def emit_visual_observation(
        self,
        task_id: str,
        description: str,
        elements: list[str],
        image_path: Optional[str] = None
    ):
        """Emit visual observation event."""
        self.emit(StreamEvent(
            event_type=StreamEventType.VISUAL_OBSERVATION,
            task_id=task_id,
            data={
                "description": description,
                "elements": elements[:10],
                "image_path": image_path
            }
        ))

    def emit_parallel_group_start(self, task_id: str, group_idx: int, step_count: int):
        """Emit parallel group start event."""
        self.emit(StreamEvent(
            event_type=StreamEventType.PARALLEL_GROUP_START,
            task_id=task_id,
            data={"group": group_idx, "step_count": step_count}
        ))

    def emit_parallel_group_complete(
        self,
        task_id: str,
        group_idx: int,
        success_count: int,
        failed_count: int,
        time_seconds: float
    ):
        """Emit parallel group completion event."""
        self.emit(StreamEvent(
            event_type=StreamEventType.PARALLEL_GROUP_COMPLETE,
            task_id=task_id,
            data={
                "group": group_idx,
                "success_count": success_count,
                "failed_count": failed_count,
                "time_seconds": time_seconds
            }
        ))

    def emit_error(self, task_id: str, error: str, traceback: str = ""):
        """Emit error event."""
        self.emit(StreamEvent(
            event_type=StreamEventType.ERROR,
            task_id=task_id,
            data={"error": error, "traceback": traceback[:500]}
        ))


# Global streaming server instance
_streaming_server: Optional[StreamingServer] = None


def get_streaming_server(
    host: str = "localhost",
    port: int = 8765,
    auto_start: bool = False  # Changed to False to avoid event loop issues
) -> StreamingServer:
    """
    Get or create the global streaming server.

    Args:
        host: Server host
        port: Server port
        auto_start: Whether to start the server if not running

    Returns:
        StreamingServer instance
    """
    global _streaming_server

    if _streaming_server is None:
        _streaming_server = StreamingServer(host=host, port=port)

    if auto_start and WEBSOCKETS_AVAILABLE and not _streaming_server._running:
        try:
            # Only auto-start if we're in an async context
            loop = asyncio.get_running_loop()
            asyncio.create_task(_streaming_server.start())
        except RuntimeError:
            # No running event loop, skip auto-start
            pass

    return _streaming_server


class StreamingMixin:
    """
    Mixin class to add streaming capabilities to any agent component.

    Usage:
        class MyAgent(StreamingMixin):
            def __init__(self, task_id: str):
                self.init_streaming(task_id)

            def do_work(self):
                self.stream_action_start("bash", {"cmd": "ls"})
                # ... do work ...
                self.stream_action_complete("bash", True, "output")
    """

    def init_streaming(self, task_id: str = "", enable: bool = True):
        """Initialize streaming for this component."""
        self._stream_task_id = task_id
        self._stream_enabled = enable and WEBSOCKETS_AVAILABLE
        self._stream_server = get_streaming_server() if enable else None

    def set_stream_task_id(self, task_id: str):
        """Set the current task ID for streaming."""
        self._stream_task_id = task_id

    def stream_task_start(self, description: str):
        """Stream task start event."""
        if self._stream_enabled and self._stream_server:
            self._stream_server.emit_task_start(self._stream_task_id, description)

    def stream_task_complete(self, success: bool, summary: str):
        """Stream task completion event."""
        if self._stream_enabled and self._stream_server:
            self._stream_server.emit_task_complete(self._stream_task_id, success, summary)

    def stream_plan_step(self, step_number: int, description: str):
        """Stream planning step."""
        if self._stream_enabled and self._stream_server:
            self._stream_server.emit_plan_step(self._stream_task_id, step_number, description)

    def stream_action_start(self, tool: str, params: dict):
        """Stream action start."""
        if self._stream_enabled and self._stream_server:
            self._stream_server.emit_action_start(self._stream_task_id, tool, params)

    def stream_action_progress(self, progress: str):
        """Stream action progress."""
        if self._stream_enabled and self._stream_server:
            self._stream_server.emit_action_progress(self._stream_task_id, progress)

    def stream_action_complete(self, tool: str, success: bool, result: str):
        """Stream action completion."""
        if self._stream_enabled and self._stream_server:
            self._stream_server.emit_action_complete(self._stream_task_id, tool, success, result)

    def stream_observation(self, observation: str):
        """Stream observation."""
        if self._stream_enabled and self._stream_server:
            self._stream_server.emit_observation(self._stream_task_id, observation)

    def stream_visual(self, description: str, elements: list[str], image_path: str = None):
        """Stream visual observation."""
        if self._stream_enabled and self._stream_server:
            self._stream_server.emit_visual_observation(
                self._stream_task_id, description, elements, image_path
            )

    def stream_error(self, error: str, traceback: str = ""):
        """Stream error event."""
        if self._stream_enabled and self._stream_server:
            self._stream_server.emit_error(self._stream_task_id, error, traceback)


# Simple test
async def _test_streaming():
    """Test streaming functionality."""
    if not WEBSOCKETS_AVAILABLE:
        print("websockets not installed, skipping test")
        return

    server = StreamingServer(port=8766)
    await server.start()

    # Emit some events
    server.emit_task_start("test_task", "Testing streaming")
    server.emit_plan_step("test_task", 1, "First step")
    server.emit_action_start("test_task", "bash", {"cmd": "echo hello"})
    server.emit_action_complete("test_task", "bash", True, "hello")
    server.emit_task_complete("test_task", True, "Test complete")

    print(f"Emitted 5 events, buffer has {len(server.buffer.get_all())} events")

    await asyncio.sleep(1)
    await server.stop()

    print("Streaming test complete")


if __name__ == "__main__":
    asyncio.run(_test_streaming())

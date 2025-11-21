"""Checkpointing system for durable LangGraph execution."""
import uuid
from datetime import datetime
from typing import Any, Optional
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata, CheckpointTuple
from langgraph.checkpoint.memory import MemorySaver
import persistence

class SQLiteCheckpointer(BaseCheckpointSaver):
    """SQLite-based checkpoint saver for LangGraph."""

    def __init__(self, graph_id: str):
        super().__init__()
        self.graph_id = graph_id

    async def aget(self, config: dict) -> Optional[CheckpointTuple]:
        """Get checkpoint from database."""
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id")

        state = await persistence.load_state(self.graph_id, thread_id, checkpoint_id)
        if not state:
            return None

        return CheckpointTuple(
            config=config,
            checkpoint=Checkpoint(
                v=1,
                id=state.get("checkpoint_id", str(uuid.uuid4())),
                ts=state.get("timestamp", datetime.now().isoformat()),
                channel_values=state.get("channel_values", {}),
                channel_versions=state.get("channel_versions", {}),
                versions_seen=state.get("versions_seen", {}),
                pending_sends=state.get("pending_sends", [])
            ),
            metadata=CheckpointMetadata(
                source=state.get("source", "input"),
                step=state.get("step", 0),
                writes=state.get("writes"),
                parents=state.get("parents", {})
            ),
            parent_config=state.get("parent_config")
        )

    async def aput(self, config: dict, checkpoint: Checkpoint, metadata: CheckpointMetadata, new_versions: dict) -> dict:
        """Save checkpoint to database."""
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        checkpoint_id = checkpoint.id

        state = {
            "checkpoint_id": checkpoint_id,
            "timestamp": checkpoint.ts,
            "channel_values": checkpoint.channel_values,
            "channel_versions": checkpoint.channel_versions,
            "versions_seen": checkpoint.versions_seen,
            "pending_sends": checkpoint.pending_sends,
            "source": metadata.source,
            "step": metadata.step,
            "writes": metadata.writes,
            "parents": metadata.parents,
            "parent_config": config
        }

        await persistence.save_state(self.graph_id, thread_id, state, checkpoint_id)

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id
            }
        }

    async def alist(self, config: dict, *, filter: Optional[dict] = None, before: Optional[dict] = None, limit: Optional[int] = None):
        """List checkpoints for a thread."""
        thread_id = config.get("configurable", {}).get("thread_id", "default")
        checkpoints = await persistence.list_checkpoints(self.graph_id, thread_id)

        for cp in checkpoints[:limit] if limit else checkpoints:
            state = await persistence.load_state(self.graph_id, thread_id, cp["checkpoint_id"])
            if state:
                yield CheckpointTuple(
                    config={"configurable": {"thread_id": thread_id, "checkpoint_id": cp["checkpoint_id"]}},
                    checkpoint=Checkpoint(
                        v=1,
                        id=cp["checkpoint_id"],
                        ts=state.get("timestamp"),
                        channel_values=state.get("channel_values", {}),
                        channel_versions=state.get("channel_versions", {}),
                        versions_seen=state.get("versions_seen", {}),
                        pending_sends=state.get("pending_sends", [])
                    ),
                    metadata=CheckpointMetadata(
                        source=state.get("source", "input"),
                        step=state.get("step", 0),
                        writes=state.get("writes"),
                        parents=state.get("parents", {})
                    ),
                    parent_config=state.get("parent_config")
                )

def get_checkpointer(graph_id: str, use_memory: bool = False) -> BaseCheckpointSaver:
    """Get appropriate checkpointer based on configuration."""
    if use_memory:
        return MemorySaver()
    return SQLiteCheckpointer(graph_id)

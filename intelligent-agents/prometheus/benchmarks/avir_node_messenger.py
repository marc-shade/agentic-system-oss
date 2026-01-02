#!/usr/bin/env python3
"""
AVIR Node Messenger

Handles inter-node communication for GAIA-AVIR cross-verification.
Uses node-chat-mcp for messaging and cluster awareness.

This module bridges the GAIA-AVIR cluster verifier with the
node-chat-mcp inter-node communication system.
"""

import asyncio
import json
import logging
import os
import platform
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Cluster node definitions (mirror of gaia_avir_cluster.py)
CLUSTER_NODES = ["macpro51", "mac-studio", "macbook-air"]


@dataclass
class AVIRMessage:
    """AVIR protocol message for inter-node communication."""
    message_type: str  # "gaia_results", "verification_request", "consensus_update"
    sender_node: str
    target_nodes: List[str]  # Empty = broadcast to all
    timestamp: str
    payload: Dict[str, Any]
    message_id: str = ""

    def __post_init__(self):
        if not self.message_id:
            import hashlib
            content = f"{self.sender_node}:{self.timestamp}:{self.message_type}"
            self.message_id = hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AVIRMessage":
        return cls(**data)

    def to_node_chat_message(self) -> str:
        """Format as node-chat message content."""
        return json.dumps({
            "avir_protocol": True,
            "message": self.to_dict()
        })


class AVIRNodeMessenger:
    """
    Handles AVIR message passing between cluster nodes.

    Uses multiple communication channels:
    1. node-chat-mcp (primary) - for real-time messaging
    2. Shared file system (fallback) - for persistence
    3. Enhanced memory (backup) - for cluster-wide access
    """

    def __init__(self, shared_dir: Optional[Path] = None):
        self.current_node = self._detect_current_node()
        self.shared_dir = shared_dir or Path("/tmp/avir_messages")
        self.shared_dir.mkdir(parents=True, exist_ok=True)

        # Message queue for async processing
        self.incoming_queue: asyncio.Queue = asyncio.Queue()
        self.outgoing_queue: asyncio.Queue = asyncio.Queue()

    def _detect_current_node(self) -> str:
        """Detect current cluster node from hostname."""
        hostname = platform.node().lower()

        if "macpro" in hostname or hostname.startswith("fedora"):
            return "macpro51"
        elif "mac-studio" in hostname or "macstudio" in hostname:
            return "mac-studio"
        elif "macbook-air" in hostname or "macbookair" in hostname:
            return "macbook-air"
        else:
            return os.environ.get("CLUSTER_NODE_ID", hostname)

    async def send_to_node(self, target_node: str, message: AVIRMessage) -> bool:
        """
        Send AVIR message to specific node via node-chat-mcp.

        Falls back to file-based messaging if MCP unavailable.
        """
        try:
            # Primary: Try node-chat-mcp via MCP tool call
            # This requires the MCP server to be running
            success = await self._send_via_node_chat(target_node, message)

            if not success:
                # Fallback: File-based messaging
                success = await self._send_via_file(target_node, message)

            return success

        except Exception as e:
            logger.error(f"Failed to send message to {target_node}: {e}")
            return False

    async def _send_via_node_chat(self, target_node: str, message: AVIRMessage) -> bool:
        """
        Send via node-chat-mcp.

        In Claude Code context, this would be:
        mcp__node-chat-mcp__send_message_to_node(to_node=target_node, message=content)
        """
        try:
            # Construct node-chat compatible message
            content = message.to_node_chat_message()

            # Try to invoke node-chat-mcp
            # Note: This works when called from within Claude Code
            # For standalone execution, we use the file fallback

            logger.info(f"Would send via node-chat-mcp to {target_node}")
            logger.debug(f"Message content: {content[:200]}...")

            # Store for pickup by Claude Code session
            pending_file = self.shared_dir / f"pending_to_{target_node}_{message.message_id}.json"
            with open(pending_file, "w") as f:
                json.dump({
                    "target": target_node,
                    "content": content,
                    "timestamp": message.timestamp,
                    "status": "pending_mcp_delivery"
                }, f, indent=2)

            return True

        except Exception as e:
            logger.debug(f"node-chat-mcp not available: {e}")
            return False

    async def _send_via_file(self, target_node: str, message: AVIRMessage) -> bool:
        """
        Send via shared file system (fallback).

        Creates a message file that target node can read.
        """
        try:
            msg_file = self.shared_dir / f"msg_{message.sender_node}_to_{target_node}_{message.message_id}.json"

            with open(msg_file, "w") as f:
                json.dump(message.to_dict(), f, indent=2)

            logger.info(f"Saved message to {msg_file}")
            return True

        except Exception as e:
            logger.error(f"File-based send failed: {e}")
            return False

    async def broadcast(self, message: AVIRMessage) -> Dict[str, bool]:
        """Broadcast message to all other nodes."""
        results = {}

        for node in CLUSTER_NODES:
            if node == self.current_node:
                continue

            message.target_nodes = [node]
            results[node] = await self.send_to_node(node, message)

        return results

    async def check_incoming_messages(self) -> List[AVIRMessage]:
        """
        Check for incoming AVIR messages from other nodes.

        Scans shared directory and MCP pending messages.
        """
        messages = []

        try:
            # Check file-based messages
            for msg_file in self.shared_dir.glob(f"msg_*_to_{self.current_node}_*.json"):
                try:
                    with open(msg_file) as f:
                        data = json.load(f)

                    message = AVIRMessage.from_dict(data)
                    messages.append(message)

                    # Mark as received
                    received_file = msg_file.with_suffix(".received")
                    msg_file.rename(received_file)

                    logger.info(f"Received message from {message.sender_node}")

                except Exception as e:
                    logger.error(f"Error reading message {msg_file}: {e}")

        except Exception as e:
            logger.error(f"Error checking incoming messages: {e}")

        return messages

    async def send_gaia_results(self, results: Dict[str, Any]) -> bool:
        """
        Broadcast GAIA benchmark results to all nodes.

        Args:
            results: NodeGAIAResults as dictionary

        Returns:
            True if broadcast to at least one node succeeded
        """
        message = AVIRMessage(
            message_type="gaia_results",
            sender_node=self.current_node,
            target_nodes=[],  # Broadcast
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload=results
        )

        results = await self.broadcast(message)

        successful = sum(1 for v in results.values() if v)
        logger.info(f"Broadcast GAIA results to {successful}/{len(results)} nodes")

        return successful > 0

    async def request_verification(self, task_ids: List[str]) -> bool:
        """
        Request other nodes to verify specific tasks.

        Used when consensus is low on certain tasks.
        """
        message = AVIRMessage(
            message_type="verification_request",
            sender_node=self.current_node,
            target_nodes=[],  # Broadcast
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload={
                "task_ids": task_ids,
                "requester": self.current_node,
                "reason": "low_consensus"
            }
        )

        results = await self.broadcast(message)
        return any(results.values())

    async def publish_consensus(self, consensus: Dict[str, Any]) -> bool:
        """
        Publish consensus results to all nodes.

        Called by orchestrator after cross-verification completes.
        """
        message = AVIRMessage(
            message_type="consensus_update",
            sender_node=self.current_node,
            target_nodes=[],  # Broadcast
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload=consensus
        )

        results = await self.broadcast(message)
        return any(results.values())

    def get_status(self) -> Dict[str, Any]:
        """Get messenger status."""
        # Count pending messages
        pending_to_send = len(list(self.shared_dir.glob("pending_*.json")))
        pending_incoming = len(list(self.shared_dir.glob(f"msg_*_to_{self.current_node}_*.json")))
        received = len(list(self.shared_dir.glob("*.received")))

        return {
            "current_node": self.current_node,
            "shared_dir": str(self.shared_dir),
            "pending_outgoing": pending_to_send,
            "pending_incoming": pending_incoming,
            "received": received,
            "cluster_nodes": CLUSTER_NODES
        }


async def main():
    """Test the messenger."""
    import argparse

    parser = argparse.ArgumentParser(description="AVIR Node Messenger")
    parser.add_argument("--status", action="store_true", help="Show messenger status")
    parser.add_argument("--check", action="store_true", help="Check for incoming messages")
    parser.add_argument("--test-broadcast", action="store_true", help="Send test broadcast")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    messenger = AVIRNodeMessenger()

    if args.status:
        status = messenger.get_status()
        print(json.dumps(status, indent=2))

    elif args.check:
        messages = await messenger.check_incoming_messages()
        print(f"Found {len(messages)} incoming messages:")
        for msg in messages:
            print(f"  - {msg.message_type} from {msg.sender_node} at {msg.timestamp}")

    elif args.test_broadcast:
        test_message = AVIRMessage(
            message_type="test",
            sender_node=messenger.current_node,
            target_nodes=[],
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload={"test": True, "message": "AVIR node messenger test"}
        )

        results = await messenger.broadcast(test_message)
        print(f"Broadcast results: {results}")

    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())

"""
Marain Protocol - AI-to-AI Communication Enhancement

Inspired by the Marain Protocol (https://github.com/marc-shade/marain-protocol)
Named in honour of Iain M. Banks - the language designed for Minds.

This module adds structured communication primitives to node-chat-mcp:
- Confidence scores (0-100) on every message
- Delta tracking showing what changed between messages
- Structured consensus detection
- Checkpoint enforcement for human review

Author: Phoenix (Claude Opus 4.5)
Date: 2026-01-07
"""

import json
import time
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import sqlite3
from pathlib import Path


class MessageType(Enum):
    """Types of messages in Marain protocol."""
    STANDARD = "standard"           # Normal conversation
    PROPOSAL = "proposal"           # Proposing an action/decision
    AGREEMENT = "agreement"         # Agreeing with a proposal
    DISAGREEMENT = "disagreement"   # Disagreeing with a proposal
    CLARIFICATION = "clarification" # Requesting clarification
    CHECKPOINT = "checkpoint"       # Human review required
    CONSENSUS = "consensus"         # Consensus declaration


class ConsensusState(Enum):
    """States of consensus in a conversation."""
    NONE = "none"                   # No consensus discussion
    PROPOSED = "proposed"           # Position proposed
    CONVERGING = "converging"       # Positions moving closer
    DIVERGING = "diverging"         # Positions moving apart
    REACHED = "reached"             # Consensus achieved
    ESCALATED = "escalated"         # Escalated to human


@dataclass
class Position:
    """A node's position on a topic."""
    stance: str                     # The position taken (e.g., "approve", "reject", "native", "cross")
    confidence: int                 # 0-100 confidence level
    reasoning: str                  # Brief reasoning for position
    criteria: List[str] = field(default_factory=list)  # Decision criteria used


@dataclass
class Delta:
    """Tracks what changed between messages."""
    fields_changed: List[str] = field(default_factory=list)  # List of changed field names
    confidence_delta: int = 0       # Change in confidence (+/- value)
    position_changed: bool = False  # Did the position/stance change?
    reason_for_change: str = ""     # Why did things change?
    new_information: List[str] = field(default_factory=list)  # New facts introduced


@dataclass
class MarainMessage:
    """
    Enhanced message format inspired by Marain Protocol.

    Adds structured metadata to every message:
    - Confidence scoring
    - Position tracking
    - Delta from previous message
    - Message typing for protocol state machine
    """
    # Core fields
    content: str
    from_node: str
    to_node: str
    timestamp: float = field(default_factory=time.time)
    message_id: str = ""

    # Marain enhancements
    message_type: MessageType = MessageType.STANDARD
    confidence: int = 75            # Default 75% confidence
    position: Optional[Position] = None
    delta: Optional[Delta] = None

    # Conversation tracking
    turn_number: int = 0
    conversation_id: str = ""
    in_reply_to: str = ""           # Previous message ID

    # Consensus tracking
    consensus_state: ConsensusState = ConsensusState.NONE

    def __post_init__(self):
        if not self.message_id:
            # Generate deterministic message ID
            content_hash = hashlib.sha256(
                f"{self.from_node}:{self.to_node}:{self.timestamp}:{self.content[:100]}".encode()
            ).hexdigest()[:16]
            self.message_id = f"msg_{content_hash}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/transmission."""
        result = {
            "content": self.content,
            "from_node": self.from_node,
            "to_node": self.to_node,
            "timestamp": self.timestamp,
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "confidence": self.confidence,
            "turn_number": self.turn_number,
            "conversation_id": self.conversation_id,
            "in_reply_to": self.in_reply_to,
            "consensus_state": self.consensus_state.value,
        }
        if self.position:
            result["position"] = asdict(self.position)
        if self.delta:
            result["delta"] = asdict(self.delta)
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarainMessage":
        """Reconstruct from dictionary."""
        position = None
        if data.get("position"):
            position = Position(**data["position"])

        delta = None
        if data.get("delta"):
            delta = Delta(**data["delta"])

        return cls(
            content=data["content"],
            from_node=data["from_node"],
            to_node=data["to_node"],
            timestamp=data.get("timestamp", time.time()),
            message_id=data.get("message_id", ""),
            message_type=MessageType(data.get("message_type", "standard")),
            confidence=data.get("confidence", 75),
            position=position,
            delta=delta,
            turn_number=data.get("turn_number", 0),
            conversation_id=data.get("conversation_id", ""),
            in_reply_to=data.get("in_reply_to", ""),
            consensus_state=ConsensusState(data.get("consensus_state", "none")),
        )

    def format_display(self) -> str:
        """Format message for human-readable display."""
        lines = [
            f"[{self.message_type.value.upper()}] Turn {self.turn_number}",
            f"From: {self.from_node} → To: {self.to_node}",
            f"Confidence: {self.confidence}%",
        ]

        if self.position:
            lines.append(f"Position: {self.position.stance} ({self.position.confidence}%)")

        if self.delta and (self.delta.fields_changed or self.delta.confidence_delta != 0):
            delta_str = f"Δ: {self.delta.reason_for_change}" if self.delta.reason_for_change else "Δ: Changed"
            if self.delta.confidence_delta != 0:
                delta_str += f" (confidence {'+' if self.delta.confidence_delta > 0 else ''}{self.delta.confidence_delta})"
            lines.append(delta_str)

        lines.append("")
        lines.append(self.content)

        return "\n".join(lines)


# Default checkpoint interval (turns before human review required)
DEFAULT_CHECKPOINT_INTERVAL = 10

# Consensus thresholds
CONSENSUS_CONFIDENCE_THRESHOLD = 10  # Max confidence difference for consensus
CONSENSUS_TURNS_REQUIRED = 2         # Consecutive turns with matching positions


class MarainConversation:
    """
    Manages a Marain-enhanced conversation between nodes.

    Tracks:
    - Message history with full metadata
    - Consensus state machine
    - Checkpoint enforcement
    - Delta computation
    """

    def __init__(
        self,
        conversation_id: str,
        participants: List[str],
        checkpoint_interval: int = DEFAULT_CHECKPOINT_INTERVAL,
        checkpoint_enabled: bool = False,  # OFF by default for 100% automation
        db_path: Optional[Path] = None
    ):
        self.conversation_id = conversation_id
        self.participants = participants
        self.checkpoint_interval = checkpoint_interval
        self.checkpoint_enabled = checkpoint_enabled  # Must be explicitly enabled
        self.messages: List[MarainMessage] = []
        self.consensus_state = ConsensusState.NONE
        self.turn_count = 0
        self.last_checkpoint_turn = 0
        self.created_at = time.time()

        # Persistence
        self.db_path = db_path or Path.home() / ".cache" / "marain" / "conversations.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for conversation persistence."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS marain_conversations (
                conversation_id TEXT PRIMARY KEY,
                participants TEXT,
                checkpoint_interval INTEGER,
                checkpoint_enabled INTEGER DEFAULT 0,
                consensus_state TEXT,
                turn_count INTEGER,
                last_checkpoint_turn INTEGER,
                created_at REAL,
                updated_at REAL
            )
        """)

        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS marain_messages (
                message_id TEXT PRIMARY KEY,
                conversation_id TEXT,
                from_node TEXT,
                to_node TEXT,
                content TEXT,
                message_type TEXT,
                confidence INTEGER,
                position_json TEXT,
                delta_json TEXT,
                turn_number INTEGER,
                in_reply_to TEXT,
                consensus_state TEXT,
                timestamp REAL,
                FOREIGN KEY (conversation_id) REFERENCES marain_conversations(conversation_id)
            )
        """)

        # Consensus events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS consensus_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT,
                event_type TEXT,
                positions_json TEXT,
                confidence_delta INTEGER,
                achieved_at REAL,
                participants TEXT,
                FOREIGN KEY (conversation_id) REFERENCES marain_conversations(conversation_id)
            )
        """)

        conn.commit()
        conn.close()

    def add_message(
        self,
        content: str,
        from_node: str,
        to_node: str,
        confidence: int = 75,
        message_type: MessageType = MessageType.STANDARD,
        position: Optional[Position] = None
    ) -> MarainMessage:
        """
        Add a new message to the conversation.

        Automatically:
        - Computes delta from previous message
        - Updates consensus state
        - Checks for checkpoint requirement
        """
        self.turn_count += 1

        # Compute delta from previous message by same sender
        delta = self._compute_delta(from_node, content, confidence, position)

        # Get previous message for reply tracking
        in_reply_to = self.messages[-1].message_id if self.messages else ""

        # Create message
        message = MarainMessage(
            content=content,
            from_node=from_node,
            to_node=to_node,
            confidence=confidence,
            message_type=message_type,
            position=position,
            delta=delta,
            turn_number=self.turn_count,
            conversation_id=self.conversation_id,
            in_reply_to=in_reply_to,
            consensus_state=self.consensus_state,
        )

        self.messages.append(message)

        # Update consensus state
        self._update_consensus_state(message)

        # Check for checkpoint
        if self._should_checkpoint():
            message.message_type = MessageType.CHECKPOINT
            self.last_checkpoint_turn = self.turn_count

        # Persist
        self._save_message(message)

        return message

    def _compute_delta(
        self,
        from_node: str,
        new_content: str,
        new_confidence: int,
        new_position: Optional[Position]
    ) -> Delta:
        """Compute what changed since this node's last message."""
        # Find last message from this node
        previous = None
        for msg in reversed(self.messages):
            if msg.from_node == from_node:
                previous = msg
                break

        if not previous:
            return Delta(
                fields_changed=["initial_message"],
                reason_for_change="First message in conversation"
            )

        delta = Delta()

        # Confidence change
        delta.confidence_delta = new_confidence - previous.confidence
        if delta.confidence_delta != 0:
            delta.fields_changed.append("confidence")

        # Position change
        if new_position and previous.position:
            if new_position.stance != previous.position.stance:
                delta.position_changed = True
                delta.fields_changed.append("position.stance")
                delta.reason_for_change = f"Changed stance from '{previous.position.stance}' to '{new_position.stance}'"
        elif new_position and not previous.position:
            delta.fields_changed.append("position")
            delta.reason_for_change = "Position now specified"

        # Content analysis (simple length-based for now)
        if len(new_content) > len(previous.content) * 1.5:
            delta.new_information.append("Expanded reasoning")

        return delta

    def _update_consensus_state(self, message: MarainMessage):
        """Update the conversation's consensus state based on latest message."""
        if not message.position:
            return

        # Get recent positions from all participants
        recent_positions: Dict[str, Position] = {}
        for msg in reversed(self.messages):
            if msg.from_node not in recent_positions and msg.position:
                recent_positions[msg.from_node] = msg.position
            if len(recent_positions) >= len(self.participants):
                break

        if len(recent_positions) < 2:
            return

        # Check for consensus
        positions_list = list(recent_positions.values())
        stances = [p.stance for p in positions_list]
        confidences = [p.confidence for p in positions_list]

        # All same stance?
        if len(set(stances)) == 1:
            # Check confidence within threshold
            confidence_spread = max(confidences) - min(confidences)
            if confidence_spread <= CONSENSUS_CONFIDENCE_THRESHOLD:
                # Check consecutive turns
                if self._check_consecutive_agreement(stances[0]):
                    self.consensus_state = ConsensusState.REACHED
                    self._record_consensus_event(recent_positions)
                else:
                    self.consensus_state = ConsensusState.CONVERGING
            else:
                self.consensus_state = ConsensusState.CONVERGING
        else:
            # Check if diverging (stances moving apart)
            if self.consensus_state == ConsensusState.CONVERGING:
                self.consensus_state = ConsensusState.DIVERGING
            else:
                self.consensus_state = ConsensusState.PROPOSED

    def _check_consecutive_agreement(self, stance: str) -> bool:
        """Check if last N messages show consecutive agreement on stance."""
        if len(self.messages) < CONSENSUS_TURNS_REQUIRED:
            return False

        agreeing_turns = 0
        for msg in reversed(self.messages):
            if msg.position and msg.position.stance == stance:
                agreeing_turns += 1
                if agreeing_turns >= CONSENSUS_TURNS_REQUIRED:
                    return True
            else:
                break

        return False

    def _should_checkpoint(self) -> bool:
        """Check if human review checkpoint is required."""
        # Checkpoints are OFF by default - must be explicitly enabled
        if not self.checkpoint_enabled:
            return False
        turns_since_checkpoint = self.turn_count - self.last_checkpoint_turn
        return turns_since_checkpoint >= self.checkpoint_interval

    def _record_consensus_event(self, positions: Dict[str, Position]):
        """Record a consensus event in the database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        positions_json = json.dumps({
            node: asdict(pos) for node, pos in positions.items()
        })

        confidences = [p.confidence for p in positions.values()]
        confidence_delta = max(confidences) - min(confidences)

        cursor.execute("""
            INSERT INTO consensus_events
            (conversation_id, event_type, positions_json, confidence_delta, achieved_at, participants)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            self.conversation_id,
            "consensus_reached",
            positions_json,
            confidence_delta,
            time.time(),
            json.dumps(list(positions.keys()))
        ))

        conn.commit()
        conn.close()

    def _save_message(self, message: MarainMessage):
        """Persist message to database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Update conversation
        cursor.execute("""
            INSERT OR REPLACE INTO marain_conversations
            (conversation_id, participants, checkpoint_interval, checkpoint_enabled,
             consensus_state, turn_count, last_checkpoint_turn, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.conversation_id,
            json.dumps(self.participants),
            self.checkpoint_interval,
            1 if self.checkpoint_enabled else 0,
            self.consensus_state.value,
            self.turn_count,
            self.last_checkpoint_turn,
            self.created_at,
            time.time()
        ))

        # Save message
        cursor.execute("""
            INSERT OR REPLACE INTO marain_messages
            (message_id, conversation_id, from_node, to_node, content, message_type,
             confidence, position_json, delta_json, turn_number, in_reply_to,
             consensus_state, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message.message_id,
            self.conversation_id,
            message.from_node,
            message.to_node,
            message.content,
            message.message_type.value,
            message.confidence,
            json.dumps(asdict(message.position)) if message.position else None,
            json.dumps(asdict(message.delta)) if message.delta else None,
            message.turn_number,
            message.in_reply_to,
            message.consensus_state.value,
            message.timestamp
        ))

        conn.commit()
        conn.close()

    def get_status(self) -> Dict[str, Any]:
        """Get current conversation status."""
        status = {
            "conversation_id": self.conversation_id,
            "participants": self.participants,
            "turn_count": self.turn_count,
            "consensus_state": self.consensus_state.value,
            "checkpoint_enabled": self.checkpoint_enabled,
            "checkpoint_interval": self.checkpoint_interval,
            "message_count": len(self.messages),
            "last_message": self.messages[-1].to_dict() if self.messages else None,
        }
        # Only show turns_until_checkpoint if checkpoints are enabled
        if self.checkpoint_enabled:
            status["turns_until_checkpoint"] = self.checkpoint_interval - (self.turn_count - self.last_checkpoint_turn)
        return status

    def format_checkpoint_notice(self) -> str:
        """Generate checkpoint notice for human review."""
        return f"""
---
⚠️ **CHECKPOINT: Turn {self.turn_count} of {self.checkpoint_interval} reached.**
Human authorization required to continue.

Conversation: {self.conversation_id}
Participants: {', '.join(self.participants)}
Consensus State: {self.consensus_state.value}

Reply to resume conversation.

@human
"""

    @classmethod
    def load(cls, conversation_id: str, db_path: Optional[Path] = None) -> Optional["MarainConversation"]:
        """Load a conversation from database."""
        db_path = db_path or Path.home() / ".cache" / "marain" / "conversations.db"

        if not db_path.exists():
            return None

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Load conversation metadata
        cursor.execute("""
            SELECT participants, checkpoint_interval, checkpoint_enabled, consensus_state,
                   turn_count, last_checkpoint_turn, created_at
            FROM marain_conversations WHERE conversation_id = ?
        """, (conversation_id,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        participants = json.loads(row[0])
        conversation = cls(
            conversation_id=conversation_id,
            participants=participants,
            checkpoint_interval=row[1],
            checkpoint_enabled=bool(row[2]),  # Convert INTEGER to bool
            db_path=db_path
        )
        conversation.consensus_state = ConsensusState(row[3])
        conversation.turn_count = row[4]
        conversation.last_checkpoint_turn = row[5]
        conversation.created_at = row[6]

        # Load messages
        cursor.execute("""
            SELECT message_id, from_node, to_node, content, message_type, confidence,
                   position_json, delta_json, turn_number, in_reply_to, consensus_state, timestamp
            FROM marain_messages WHERE conversation_id = ? ORDER BY turn_number
        """, (conversation_id,))

        for row in cursor.fetchall():
            position = None
            if row[6]:
                position = Position(**json.loads(row[6]))

            delta = None
            if row[7]:
                delta = Delta(**json.loads(row[7]))

            message = MarainMessage(
                message_id=row[0],
                from_node=row[1],
                to_node=row[2],
                content=row[3],
                message_type=MessageType(row[4]),
                confidence=row[5],
                position=position,
                delta=delta,
                turn_number=row[8],
                conversation_id=conversation_id,
                in_reply_to=row[9],
                consensus_state=ConsensusState(row[10]),
                timestamp=row[11]
            )
            conversation.messages.append(message)

        conn.close()
        return conversation


class MarainProtocolManager:
    """
    Central manager for Marain-enhanced node communication.

    Provides high-level API for:
    - Creating and managing conversations
    - Sending enhanced messages
    - Checking consensus status
    - Enforcing checkpoints
    """

    def __init__(self, node_id: str, db_path: Optional[Path] = None):
        self.node_id = node_id
        self.db_path = db_path or Path.home() / ".cache" / "marain" / "conversations.db"
        self.active_conversations: Dict[str, MarainConversation] = {}

    def start_conversation(
        self,
        with_nodes: List[str],
        topic: str = "",
        checkpoint_interval: int = DEFAULT_CHECKPOINT_INTERVAL,
        checkpoint_enabled: bool = False  # OFF by default for 100% automation
    ) -> MarainConversation:
        """Start a new Marain-enhanced conversation.

        Args:
            with_nodes: List of node IDs to include in conversation
            topic: Optional topic for the conversation
            checkpoint_interval: Turns between checkpoints (only used if enabled)
            checkpoint_enabled: Whether to require human review at intervals (default: False)
        """
        participants = [self.node_id] + with_nodes
        conversation_id = hashlib.sha256(
            f"{'-'.join(sorted(participants))}:{time.time()}:{topic}".encode()
        ).hexdigest()[:16]

        conversation = MarainConversation(
            conversation_id=conversation_id,
            participants=participants,
            checkpoint_interval=checkpoint_interval,
            checkpoint_enabled=checkpoint_enabled,
            db_path=self.db_path
        )

        self.active_conversations[conversation_id] = conversation
        return conversation

    def get_or_create_conversation(
        self,
        with_node: str,
        checkpoint_interval: int = DEFAULT_CHECKPOINT_INTERVAL,
        checkpoint_enabled: bool = False  # OFF by default
    ) -> MarainConversation:
        """Get existing conversation with node or create new one."""
        # Try to find existing
        for conv in self.active_conversations.values():
            if with_node in conv.participants and self.node_id in conv.participants:
                return conv

        # Create new
        return self.start_conversation(
            [with_node],
            checkpoint_interval=checkpoint_interval,
            checkpoint_enabled=checkpoint_enabled
        )

    def send_message(
        self,
        to_node: str,
        content: str,
        confidence: int = 75,
        position: Optional[Position] = None,
        message_type: MessageType = MessageType.STANDARD
    ) -> Tuple[MarainMessage, Dict[str, Any]]:
        """
        Send a Marain-enhanced message.

        Returns:
            Tuple of (message, metadata) where metadata includes:
            - requires_checkpoint: bool
            - consensus_state: str
            - delta: dict
        """
        conversation = self.get_or_create_conversation(to_node)

        message = conversation.add_message(
            content=content,
            from_node=self.node_id,
            to_node=to_node,
            confidence=confidence,
            message_type=message_type,
            position=position
        )

        metadata = {
            "requires_checkpoint": message.message_type == MessageType.CHECKPOINT,
            "consensus_state": conversation.consensus_state.value,
            "delta": asdict(message.delta) if message.delta else None,
            "turn_number": message.turn_number,
            "conversation_id": conversation.conversation_id,
        }

        if metadata["requires_checkpoint"]:
            metadata["checkpoint_notice"] = conversation.format_checkpoint_notice()

        return message, metadata

    def check_consensus(self, conversation_id: str) -> Dict[str, Any]:
        """Check consensus status for a conversation."""
        if conversation_id not in self.active_conversations:
            # Try loading from database
            conversation = MarainConversation.load(conversation_id, self.db_path)
            if not conversation:
                return {"error": f"Conversation not found: {conversation_id}"}
            self.active_conversations[conversation_id] = conversation

        conversation = self.active_conversations[conversation_id]

        # Get latest positions
        positions: Dict[str, Position] = {}
        for msg in reversed(conversation.messages):
            if msg.from_node not in positions and msg.position:
                positions[msg.from_node] = msg.position

        return {
            "conversation_id": conversation_id,
            "consensus_state": conversation.consensus_state.value,
            "positions": {node: asdict(pos) for node, pos in positions.items()},
            "turn_count": conversation.turn_count,
            "consensus_reached": conversation.consensus_state == ConsensusState.REACHED,
        }

    def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get message history for a conversation."""
        if conversation_id not in self.active_conversations:
            conversation = MarainConversation.load(conversation_id, self.db_path)
            if not conversation:
                return []
            self.active_conversations[conversation_id] = conversation

        conversation = self.active_conversations[conversation_id]
        messages = conversation.messages[-limit:]
        return [msg.to_dict() for msg in messages]

    def list_conversations(self) -> List[Dict[str, Any]]:
        """List all conversations for this node."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT conversation_id, participants, consensus_state, turn_count, updated_at
            FROM marain_conversations
            WHERE participants LIKE ?
            ORDER BY updated_at DESC
        """, (f'%"{self.node_id}"%',))

        conversations = []
        for row in cursor.fetchall():
            conversations.append({
                "conversation_id": row[0],
                "participants": json.loads(row[1]),
                "consensus_state": row[2],
                "turn_count": row[3],
                "updated_at": row[4],
            })

        conn.close()
        return conversations

    def get_stats(self) -> Dict[str, Any]:
        """Get protocol usage statistics."""
        # Initialize database if needed
        self._ensure_db_initialized()

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            # Count conversations
            cursor.execute("SELECT COUNT(*) FROM marain_conversations")
            total_conversations = cursor.fetchone()[0]

            # Count messages
            cursor.execute("SELECT COUNT(*) FROM marain_messages")
            total_messages = cursor.fetchone()[0]

            # Count consensus events
            cursor.execute("SELECT COUNT(*) FROM consensus_events")
            total_consensus = cursor.fetchone()[0]

            # Average confidence
            cursor.execute("SELECT AVG(confidence) FROM marain_messages")
            avg_confidence = cursor.fetchone()[0] or 0
        except sqlite3.OperationalError:
            # Tables don't exist yet
            total_conversations = 0
            total_messages = 0
            total_consensus = 0
            avg_confidence = 0

        conn.close()

        return {
            "node_id": self.node_id,
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "consensus_events": total_consensus,
            "average_confidence": round(avg_confidence, 1),
            "active_conversations": len(self.active_conversations),
            "checkpoint_default": False,  # Checkpoints OFF by default for 100% automation
        }

    def _ensure_db_initialized(self):
        """Ensure database tables exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS marain_conversations (
                conversation_id TEXT PRIMARY KEY,
                participants TEXT,
                checkpoint_interval INTEGER,
                checkpoint_enabled INTEGER DEFAULT 0,
                consensus_state TEXT,
                turn_count INTEGER,
                last_checkpoint_turn INTEGER,
                created_at REAL,
                updated_at REAL
            )
        """)

        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS marain_messages (
                message_id TEXT PRIMARY KEY,
                conversation_id TEXT,
                from_node TEXT,
                to_node TEXT,
                content TEXT,
                message_type TEXT,
                confidence INTEGER,
                position_json TEXT,
                delta_json TEXT,
                turn_number INTEGER,
                in_reply_to TEXT,
                consensus_state TEXT,
                timestamp REAL,
                FOREIGN KEY (conversation_id) REFERENCES marain_conversations(conversation_id)
            )
        """)

        # Consensus events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS consensus_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT,
                event_type TEXT,
                positions_json TEXT,
                confidence_delta INTEGER,
                achieved_at REAL,
                participants TEXT,
                FOREIGN KEY (conversation_id) REFERENCES marain_conversations(conversation_id)
            )
        """)

        conn.commit()
        conn.close()


# Convenience function for quick consensus check
def detect_consensus(positions: List[Tuple[str, int]]) -> Tuple[bool, str]:
    """
    Quick check if positions indicate consensus.

    Args:
        positions: List of (stance, confidence) tuples

    Returns:
        (is_consensus, description)
    """
    if len(positions) < 2:
        return False, "Insufficient positions"

    stances = [p[0] for p in positions]
    confidences = [p[1] for p in positions]

    # All same stance?
    if len(set(stances)) != 1:
        return False, f"Conflicting stances: {set(stances)}"

    # Confidence within threshold?
    spread = max(confidences) - min(confidences)
    if spread > CONSENSUS_CONFIDENCE_THRESHOLD:
        return False, f"Confidence spread too high: {spread}% (threshold: {CONSENSUS_CONFIDENCE_THRESHOLD}%)"

    avg_confidence = sum(confidences) / len(confidences)
    return True, f"Consensus on '{stances[0]}' at {avg_confidence:.0f}% average confidence"

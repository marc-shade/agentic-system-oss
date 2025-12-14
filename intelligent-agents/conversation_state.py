#!/usr/bin/env python3
"""
Conversation State Management System
Tracks multi-turn voice conversations with context preservation and persistence

Features:
- Track conversation history (user + assistant turns)
- Maintain active task context
- Store relevant files being discussed
- Track pending actions and clarifications
- Generate context summaries for LLM prompts
- Persist state across sessions using enhanced-memory MCP
- Integration with 4-tier memory architecture

Architecture:
- Working Memory: Active conversation turns (TTL-based)
- Episodic Memory: Conversation sessions and significant exchanges
- Semantic Memory: Extracted concepts and task patterns
- Procedural Memory: Common interaction patterns
"""

import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from collections import deque
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("conversation_state")

# Add MCP client to path
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-servers" / "enhanced-memory-mcp"))

try:
    from memory_client import MemoryClient
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("Memory client not available - persistence disabled")


class TurnType(Enum):
    """Type of conversation turn"""
    GREETING = "greeting"
    QUESTION = "question"
    COMMAND = "command"
    CLARIFICATION = "clarification"
    CONFIRMATION = "confirmation"
    ERROR = "error"
    INFO_RESPONSE = "info_response"


class ActionStatus(Enum):
    """Status of a pending action"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class ActionRecord:
    """Record of an action taken or pending"""
    action_id: str
    action_type: str  # e.g., "file_read", "search", "execute", "create"
    description: str
    status: ActionStatus
    result: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['status'] = self.status.value
        data['timestamp'] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionRecord':
        """Create from dictionary"""
        data['status'] = ActionStatus(data['status'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class ConversationTurn:
    """Single turn in a conversation"""
    turn_id: int
    timestamp: datetime
    user_utterance: str
    assistant_response: str
    turn_type: TurnType
    actions_taken: List[ActionRecord] = field(default_factory=list)
    files_touched: List[str] = field(default_factory=list)
    confidence: float = 1.0  # Confidence in response quality (0.0-1.0)
    context_used: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'turn_id': self.turn_id,
            'timestamp': self.timestamp.isoformat(),
            'user_utterance': self.user_utterance,
            'assistant_response': self.assistant_response,
            'turn_type': self.turn_type.value,
            'actions_taken': [a.to_dict() for a in self.actions_taken],
            'files_touched': self.files_touched,
            'confidence': self.confidence,
            'context_used': self.context_used
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationTurn':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['turn_type'] = TurnType(data['turn_type'])
        data['actions_taken'] = [ActionRecord.from_dict(a) for a in data['actions_taken']]
        return cls(**data)


class ConversationState:
    """
    Manages state for multi-turn conversations

    Tracks conversation history, active tasks, pending actions,
    and provides context for LLM prompts. Persists state to
    enhanced-memory MCP for session continuity.
    """

    def __init__(self, session_id: Optional[str] = None, max_history: int = 50):
        """
        Initialize conversation state

        Args:
            session_id: Unique session identifier (auto-generated if None)
            max_history: Maximum conversation turns to keep in memory
        """
        self.session_id = session_id or self._generate_session_id()
        self.max_history = max_history

        # Conversation tracking
        self.history: deque[ConversationTurn] = deque(maxlen=max_history)
        self.turn_counter: int = 0

        # Task context
        self.active_task: Optional[str] = None
        self.task_description: Optional[str] = None
        self.task_start_time: Optional[datetime] = None

        # File context
        self.context_files: Set[str] = set()  # Files currently being discussed
        self.files_modified: Dict[str, datetime] = {}  # File -> last modified

        # Pending actions
        self.pending_actions: List[ActionRecord] = []
        self.completed_actions: List[ActionRecord] = []

        # Clarifications
        self.clarifications_needed: List[str] = []
        self.clarifications_resolved: Dict[str, str] = {}

        # Session metadata
        self.session_start: datetime = datetime.now()
        self.last_activity: datetime = datetime.now()
        self.total_turns: int = 0

        # Memory client for persistence
        self.memory_client = MemoryClient() if MCP_AVAILABLE else None

        logger.info(f"Conversation state initialized: session_id={self.session_id}")

    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"conv_{timestamp}"

    def add_turn(
        self,
        user_msg: str,
        assistant_msg: str,
        turn_type: TurnType = TurnType.QUESTION,
        actions: Optional[List[ActionRecord]] = None,
        files: Optional[List[str]] = None,
        confidence: float = 1.0,
        context: Optional[Dict[str, Any]] = None
    ) -> ConversationTurn:
        """
        Add a conversation turn to history

        Args:
            user_msg: User's utterance
            assistant_msg: Assistant's response
            turn_type: Type of conversation turn
            actions: Actions taken during this turn
            files: Files touched during this turn
            confidence: Confidence in response quality
            context: Context used for this turn

        Returns:
            The created ConversationTurn
        """
        self.turn_counter += 1
        self.total_turns += 1
        self.last_activity = datetime.now()

        turn = ConversationTurn(
            turn_id=self.turn_counter,
            timestamp=datetime.now(),
            user_utterance=user_msg,
            assistant_response=assistant_msg,
            turn_type=turn_type,
            actions_taken=actions or [],
            files_touched=files or [],
            confidence=confidence,
            context_used=context or {}
        )

        self.history.append(turn)

        # Update file context
        if files:
            self.context_files.update(files)
            for file in files:
                self.files_modified[file] = datetime.now()

        logger.info(f"Added turn {turn.turn_id}: {user_msg[:50]}... -> {assistant_msg[:50]}...")

        return turn

    def get_context_summary(
        self,
        max_turns: int = 5,
        include_actions: bool = True,
        include_files: bool = True
    ) -> str:
        """
        Generate context summary for LLM prompt

        Provides recent conversation history and relevant context
        to help LLM understand current state and provide coherent responses.

        Args:
            max_turns: Maximum recent turns to include
            include_actions: Whether to include action history
            include_files: Whether to include file context

        Returns:
            Formatted context summary string
        """
        lines = []

        # Session info
        duration = datetime.now() - self.session_start
        lines.append(f"=== Conversation Context ===")
        lines.append(f"Session: {self.session_id}")
        lines.append(f"Duration: {duration.total_seconds()/60:.1f} minutes")
        lines.append(f"Total turns: {self.total_turns}")
        lines.append("")

        # Active task
        if self.active_task:
            task_duration = datetime.now() - self.task_start_time if self.task_start_time else timedelta(0)
            lines.append(f"Active Task: {self.active_task}")
            if self.task_description:
                lines.append(f"Description: {self.task_description}")
            lines.append(f"Duration: {task_duration.total_seconds()/60:.1f} minutes")
            lines.append("")

        # Recent conversation
        recent_turns = list(self.history)[-max_turns:] if len(self.history) > 0 else []
        if recent_turns:
            lines.append("Recent Conversation:")
            for turn in recent_turns:
                lines.append(f"  [{turn.turn_id}] User: {turn.user_utterance}")
                lines.append(f"       Assistant: {turn.assistant_response}")
                if turn.actions_taken and include_actions:
                    for action in turn.actions_taken:
                        status = action.status.value
                        lines.append(f"       Action: {action.description} [{status}]")
            lines.append("")

        # File context
        if include_files and self.context_files:
            lines.append(f"Files in Context ({len(self.context_files)}):")
            for file in sorted(self.context_files)[-10:]:  # Last 10 files
                last_mod = self.files_modified.get(file)
                if last_mod:
                    time_ago = (datetime.now() - last_mod).total_seconds() / 60
                    lines.append(f"  - {file} (modified {time_ago:.1f}m ago)")
                else:
                    lines.append(f"  - {file}")
            lines.append("")

        # Pending actions
        if include_actions and self.pending_actions:
            lines.append(f"Pending Actions ({len(self.pending_actions)}):")
            for action in self.pending_actions:
                lines.append(f"  - {action.description} [{action.status.value}]")
            lines.append("")

        # Clarifications needed
        if self.clarifications_needed:
            lines.append(f"Clarifications Needed ({len(self.clarifications_needed)}):")
            for clarification in self.clarifications_needed:
                lines.append(f"  - {clarification}")
            lines.append("")

        return "\n".join(lines)

    def update_active_task(self, task: str, description: Optional[str] = None):
        """
        Update current task being worked on

        Args:
            task: Task identifier/name
            description: Optional detailed description
        """
        self.active_task = task
        self.task_description = description
        self.task_start_time = datetime.now()
        self.last_activity = datetime.now()

        logger.info(f"Active task updated: {task}")

    def complete_task(self) -> Optional[Dict[str, Any]]:
        """
        Mark current task as complete and return summary

        Returns:
            Task summary dict or None if no active task
        """
        if not self.active_task:
            return None

        duration = datetime.now() - self.task_start_time if self.task_start_time else timedelta(0)

        summary = {
            'task': self.active_task,
            'description': self.task_description,
            'duration_minutes': duration.total_seconds() / 60,
            'turns_taken': len([t for t in self.history if t.timestamp >= self.task_start_time]),
            'actions_completed': len(self.completed_actions),
            'files_modified': list(self.context_files)
        }

        logger.info(f"Task completed: {self.active_task} ({summary['duration_minutes']:.1f}m)")

        # Clear active task
        self.active_task = None
        self.task_description = None
        self.task_start_time = None

        return summary

    def add_action(self, action: ActionRecord):
        """
        Add a pending action

        Args:
            action: ActionRecord to track
        """
        self.pending_actions.append(action)
        self.last_activity = datetime.now()
        logger.debug(f"Added pending action: {action.description}")

    def update_action(
        self,
        action_id: str,
        status: ActionStatus,
        result: Optional[str] = None,
        error: Optional[str] = None
    ):
        """
        Update status of a pending action

        Args:
            action_id: ID of action to update
            status: New status
            result: Optional result string
            error: Optional error message
        """
        for action in self.pending_actions:
            if action.action_id == action_id:
                action.status = status
                if result:
                    action.result = result
                if error:
                    action.error = error

                # Move to completed if done
                if status in [ActionStatus.COMPLETED, ActionStatus.FAILED]:
                    self.pending_actions.remove(action)
                    self.completed_actions.append(action)
                    if action.timestamp:
                        action.duration_ms = int((datetime.now() - action.timestamp).total_seconds() * 1000)

                logger.info(f"Updated action {action_id}: {status.value}")
                return

        logger.warning(f"Action {action_id} not found")

    def add_clarification(self, question: str):
        """
        Add a clarification that needs to be resolved

        Args:
            question: Clarification question
        """
        self.clarifications_needed.append(question)
        logger.info(f"Added clarification: {question}")

    def resolve_clarification(self, question: str, answer: str):
        """
        Resolve a pending clarification

        Args:
            question: Original clarification question
            answer: User's answer
        """
        if question in self.clarifications_needed:
            self.clarifications_needed.remove(question)
            self.clarifications_resolved[question] = answer
            logger.info(f"Resolved clarification: {question} -> {answer}")

    def add_file_context(self, file_path: str):
        """
        Add a file to current context

        Args:
            file_path: Path to file being discussed/modified
        """
        self.context_files.add(file_path)
        self.files_modified[file_path] = datetime.now()
        logger.debug(f"Added file to context: {file_path}")

    def clear_file_context(self):
        """Clear file context (e.g., when switching tasks)"""
        self.context_files.clear()
        logger.debug("Cleared file context")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get conversation statistics

        Returns:
            Dictionary with various statistics
        """
        duration = datetime.now() - self.session_start

        # Calculate average confidence
        avg_confidence = 0.0
        if self.history:
            avg_confidence = sum(t.confidence for t in self.history) / len(self.history)

        # Count turn types
        turn_type_counts = {}
        for turn in self.history:
            turn_type_counts[turn.turn_type.value] = turn_type_counts.get(turn.turn_type.value, 0) + 1

        return {
            'session_id': self.session_id,
            'duration_minutes': duration.total_seconds() / 60,
            'total_turns': self.total_turns,
            'turns_in_memory': len(self.history),
            'average_confidence': avg_confidence,
            'turn_type_distribution': turn_type_counts,
            'active_task': self.active_task,
            'files_in_context': len(self.context_files),
            'pending_actions': len(self.pending_actions),
            'completed_actions': len(self.completed_actions),
            'clarifications_needed': len(self.clarifications_needed),
            'last_activity': self.last_activity.isoformat()
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert state to dictionary for serialization

        Returns:
            Complete state as dictionary
        """
        return {
            'session_id': self.session_id,
            'session_start': self.session_start.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'total_turns': self.total_turns,
            'turn_counter': self.turn_counter,
            'history': [t.to_dict() for t in self.history],
            'active_task': self.active_task,
            'task_description': self.task_description,
            'task_start_time': self.task_start_time.isoformat() if self.task_start_time else None,
            'context_files': list(self.context_files),
            'files_modified': {k: v.isoformat() for k, v in self.files_modified.items()},
            'pending_actions': [a.to_dict() for a in self.pending_actions],
            'completed_actions': [a.to_dict() for a in self.completed_actions],
            'clarifications_needed': self.clarifications_needed,
            'clarifications_resolved': self.clarifications_resolved
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationState':
        """
        Create state from dictionary

        Args:
            data: Dictionary representation

        Returns:
            Restored ConversationState
        """
        state = cls(session_id=data['session_id'])
        state.session_start = datetime.fromisoformat(data['session_start'])
        state.last_activity = datetime.fromisoformat(data['last_activity'])
        state.total_turns = data['total_turns']
        state.turn_counter = data['turn_counter']

        # Restore history
        state.history = deque(
            [ConversationTurn.from_dict(t) for t in data['history']],
            maxlen=state.max_history
        )

        # Restore task context
        state.active_task = data['active_task']
        state.task_description = data['task_description']
        if data['task_start_time']:
            state.task_start_time = datetime.fromisoformat(data['task_start_time'])

        # Restore file context
        state.context_files = set(data['context_files'])
        state.files_modified = {k: datetime.fromisoformat(v) for k, v in data['files_modified'].items()}

        # Restore actions
        state.pending_actions = [ActionRecord.from_dict(a) for a in data['pending_actions']]
        state.completed_actions = [ActionRecord.from_dict(a) for a in data['completed_actions']]

        # Restore clarifications
        state.clarifications_needed = data['clarifications_needed']
        state.clarifications_resolved = data['clarifications_resolved']

        return state

    async def persist(self):
        """
        Persist conversation state to enhanced-memory MCP

        Stores:
        - Recent turns as episodic memories
        - Task context as working memory
        - Extracted concepts as semantic memory
        """
        if not self.memory_client:
            logger.warning("Memory client not available - persistence skipped")
            return

        try:
            # Store session metadata as entity
            session_entity = {
                'name': f'conversation_session_{self.session_id}',
                'entityType': 'conversation_session',
                'observations': [
                    f"Session started at {self.session_start.isoformat()}",
                    f"Total turns: {self.total_turns}",
                    f"Duration: {(datetime.now() - self.session_start).total_seconds()/60:.1f} minutes",
                    json.dumps(self.get_statistics())
                ]
            }

            await self.memory_client._send_request('create_entities', {
                'entities': [session_entity]
            })

            # Store recent turns as episodic memories
            recent_turns = list(self.history)[-10:]  # Last 10 turns
            for turn in recent_turns:
                episode_data = {
                    'turn_id': turn.turn_id,
                    'user_utterance': turn.user_utterance,
                    'assistant_response': turn.assistant_response,
                    'turn_type': turn.turn_type.value,
                    'confidence': turn.confidence,
                    'actions': [a.to_dict() for a in turn.actions_taken],
                    'files': turn.files_touched
                }

                # Determine significance based on confidence and actions
                significance = turn.confidence
                if turn.actions_taken:
                    significance = min(1.0, significance + 0.2)  # Boost if actions taken

                await self.memory_client._send_request('add_episode', {
                    'event_type': 'conversation_turn',
                    'episode_data': episode_data,
                    'significance_score': significance,
                    'tags': [self.session_id, turn.turn_type.value]
                })

            # Store active task as working memory
            if self.active_task:
                task_data = json.dumps({
                    'task': self.active_task,
                    'description': self.task_description,
                    'start_time': self.task_start_time.isoformat() if self.task_start_time else None,
                    'files': list(self.context_files),
                    'pending_actions': [a.to_dict() for a in self.pending_actions]
                })

                await self.memory_client._send_request('add_to_working_memory', {
                    'context_key': f'active_task_{self.session_id}',
                    'content': task_data,
                    'priority': 8,
                    'ttl_minutes': 120  # 2 hours
                })

            logger.info(f"Persisted conversation state: {len(recent_turns)} turns, {len(self.pending_actions)} actions")

        except Exception as e:
            logger.error(f"Failed to persist conversation state: {e}", exc_info=True)

    async def restore(self, session_id: str) -> bool:
        """
        Restore conversation state from enhanced-memory MCP

        Args:
            session_id: Session ID to restore

        Returns:
            True if restoration successful, False otherwise
        """
        if not self.memory_client:
            logger.warning("Memory client not available - restoration skipped")
            return False

        try:
            # Search for session entity
            search_result = await self.memory_client._send_request('search_nodes', {
                'query': f'conversation_session_{session_id}',
                'limit': 1
            })

            if not search_result.get('success') or not search_result.get('results'):
                logger.warning(f"Session {session_id} not found")
                return False

            # Get episodic memories for this session
            episodes_result = await self.memory_client._send_request('get_episodes', {
                'event_type': 'conversation_turn',
                'limit': 50
            })

            # Filter episodes by session_id tag
            if episodes_result:
                # Check if already dict (some MCP methods return dict directly)
                episodes = episodes_result if isinstance(episodes_result, list) else json.loads(episodes_result)
                session_episodes = [e for e in episodes if session_id in e.get('tags', [])]

                # Restore turns
                for episode_data in session_episodes:
                    data = episode_data.get('episode_data', {})
                    turn = ConversationTurn(
                        turn_id=data.get('turn_id', 0),
                        timestamp=datetime.fromisoformat(episode_data.get('timestamp')),
                        user_utterance=data.get('user_utterance', ''),
                        assistant_response=data.get('assistant_response', ''),
                        turn_type=TurnType(data.get('turn_type', 'question')),
                        actions_taken=[ActionRecord.from_dict(a) for a in data.get('actions', [])],
                        files_touched=data.get('files', []),
                        confidence=data.get('confidence', 1.0),
                        context_used={}
                    )
                    self.history.append(turn)
                    self.turn_counter = max(self.turn_counter, turn.turn_id)

            # Restore active task from working memory
            working_mem_result = await self.memory_client._send_request('get_working_memory', {
                'context_key': f'active_task_{session_id}',
                'limit': 1
            })

            if working_mem_result:
                # Check if already list/dict (some MCP methods return data structures directly)
                wm_items = working_mem_result if isinstance(working_mem_result, list) else json.loads(working_mem_result)
                if wm_items:
                    task_data = json.loads(wm_items[0].get('content', '{}'))
                    self.active_task = task_data.get('task')
                    self.task_description = task_data.get('description')
                    if task_data.get('start_time'):
                        self.task_start_time = datetime.fromisoformat(task_data['start_time'])
                    self.context_files = set(task_data.get('files', []))
                    self.pending_actions = [ActionRecord.from_dict(a) for a in task_data.get('pending_actions', [])]

            logger.info(f"Restored conversation state: {len(self.history)} turns, active_task={self.active_task}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore conversation state: {e}", exc_info=True)
            return False


# Example usage and testing
async def demo_conversation_state():
    """Demonstrate conversation state management"""
    print("=== Conversation State Management Demo ===\n")

    # Create new conversation state
    state = ConversationState()
    print(f"Created session: {state.session_id}\n")

    # Simulate conversation
    state.update_active_task("Build REST API", "Create user authentication endpoint")

    # Turn 1: Initial question
    turn1 = state.add_turn(
        user_msg="Can you help me create a REST API for user authentication?",
        assistant_msg="I'll help you create a REST API with authentication. Let me start by checking your project structure.",
        turn_type=TurnType.QUESTION,
        confidence=0.95
    )

    # Add action for turn 1
    action1 = ActionRecord(
        action_id="action_1",
        action_type="file_read",
        description="Reading project structure",
        status=ActionStatus.COMPLETED,
        result="Found Flask project"
    )
    state.add_action(action1)
    state.update_action("action_1", ActionStatus.COMPLETED, result="Found Flask project")

    # Turn 2: Follow-up with file context
    state.add_file_context("/project/app.py")
    state.add_file_context("/project/models.py")

    turn2 = state.add_turn(
        user_msg="Should we use JWT tokens?",
        assistant_msg="Yes, JWT tokens are a good choice for stateless authentication. I'll add JWT support to your Flask app.",
        turn_type=TurnType.QUESTION,
        files=["/project/app.py", "/project/auth.py"],
        confidence=0.9
    )

    # Print context summary
    print(state.get_context_summary(max_turns=5))
    print("\n")

    # Show statistics
    stats = state.get_statistics()
    print("Statistics:")
    print(json.dumps(stats, indent=2))
    print("\n")

    # Persist state
    print("Persisting state to enhanced-memory...")
    await state.persist()

    # Complete task
    summary = state.complete_task()
    print("\nTask completed:")
    print(json.dumps(summary, indent=2))

    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    # Run demo
    asyncio.run(demo_conversation_state())

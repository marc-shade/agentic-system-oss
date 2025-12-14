#!/usr/bin/env python3
"""
Stateful Conversation Manager for Voice AGI
Maintains dialogue context across turns with enhanced-memory integration
"""

import logging
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional, Any
import httpx
import json

logger = logging.getLogger("voice-agi.conversation")


class ConversationManager:
    """Manages multi-turn voice conversations with AGI context"""

    def __init__(self, max_turns: int = 10, enable_memory: bool = True):
        """
        Initialize conversation manager

        Args:
            max_turns: Maximum conversation turns to keep in memory
            enable_memory: Enable enhanced-memory MCP integration
        """
        self.messages = deque(maxlen=max_turns)
        self.session_start = datetime.now()
        self.session_id = f"voice_session_{self.session_start.timestamp()}"
        self.enable_memory = enable_memory
        self.user_context = {}  # User-specific context (name, preferences, etc.)

        logger.info(f"Conversation manager initialized: session {self.session_id}")

    def add_turn(self, user: str, assistant: str, metadata: Optional[Dict] = None):
        """
        Add a conversation turn

        Args:
            user: User's speech input
            assistant: Assistant's response
            metadata: Optional metadata (tools used, intent, etc.)
        """
        turn = {
            'user': user,
            'assistant': assistant,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }

        self.messages.append(turn)
        logger.debug(f"Added turn: {len(self.messages)} total turns")

    def get_context(self, include_metadata: bool = False) -> str:
        """
        Get conversation context as formatted string

        Args:
            include_metadata: Include metadata in context

        Returns:
            Formatted conversation history
        """
        if not self.messages:
            return ""

        lines = []
        for msg in self.messages:
            lines.append(f"User: {msg['user']}")
            lines.append(f"Assistant: {msg['assistant']}")

            if include_metadata and msg['metadata']:
                lines.append(f"[Metadata: {msg['metadata']}]")

            lines.append("")  # Blank line between turns

        return "\n".join(lines)

    def get_context_for_llm(self) -> List[Dict[str, str]]:
        """
        Get conversation context formatted for LLM

        Returns:
            List of message dicts with role and content
        """
        messages = []

        # Add user context if available
        if self.user_context:
            context_str = ", ".join([f"{k}: {v}" for k, v in self.user_context.items()])
            messages.append({
                'role': 'system',
                'content': f"User context: {context_str}"
            })

        # Add conversation history
        for msg in self.messages:
            messages.append({'role': 'user', 'content': msg['user']})
            messages.append({'role': 'assistant', 'content': msg['assistant']})

        return messages

    def has_context(self) -> bool:
        """Check if conversation has any history"""
        return len(self.messages) > 0

    def get_last_user_message(self) -> Optional[str]:
        """Get the last user message"""
        if self.messages:
            return self.messages[-1]['user']
        return None

    def get_last_assistant_message(self) -> Optional[str]:
        """Get the last assistant message"""
        if self.messages:
            return self.messages[-1]['assistant']
        return None

    def update_user_context(self, key: str, value: Any):
        """
        Update user-specific context (name, preferences, etc.)

        Args:
            key: Context key (e.g., 'name', 'location')
            value: Context value
        """
        self.user_context[key] = value
        logger.info(f"Updated user context: {key} = {value}")

    def get_user_context(self, key: str) -> Optional[Any]:
        """Get user context value"""
        return self.user_context.get(key)

    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of conversation state"""
        return {
            'session_id': self.session_id,
            'session_start': self.session_start.isoformat(),
            'total_turns': len(self.messages),
            'user_context': self.user_context,
            'has_context': self.has_context()
        }

    async def store_in_memory(self, memory_client=None):
        """
        Store conversation in enhanced-memory MCP

        Args:
            memory_client: Optional memory client (if None, uses HTTP)
        """
        if not self.enable_memory:
            return

        if not self.messages:
            logger.debug("No messages to store")
            return

        try:
            # Get last turn
            last_turn = self.messages[-1]

            # Create entity for storage
            entity = {
                'type': 'voice_conversation_turn',
                'session_id': self.session_id,
                'user_input': last_turn['user'],
                'assistant_response': last_turn['assistant'],
                'timestamp': last_turn['timestamp'],
                'metadata': last_turn['metadata'],
                'context_prefix': last_turn['user'][:200],  # RAG Tier 1 prefix
                'user_context': self.user_context
            }

            # TODO: Call enhanced-memory MCP to store
            # For now, just log
            logger.info(f"Would store in memory: {entity['type']}")

        except Exception as e:
            logger.error(f"Error storing in memory: {e}")

    async def retrieve_relevant_context(self, query: str, limit: int = 3) -> List[Dict]:
        """
        Retrieve relevant past conversations from memory

        Args:
            query: Query to search for
            limit: Max number of results

        Returns:
            List of relevant conversation turns
        """
        if not self.enable_memory:
            return []

        try:
            # TODO: Call enhanced-memory MCP to search
            # For now, return empty
            logger.debug(f"Would search memory for: {query}")
            return []

        except Exception as e:
            logger.error(f"Error retrieving from memory: {e}")
            return []

    def clear_context(self):
        """Clear conversation context (start fresh)"""
        self.messages.clear()
        logger.info("Conversation context cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get conversation statistics"""
        total_user_words = sum(len(msg['user'].split()) for msg in self.messages)
        total_assistant_words = sum(len(msg['assistant'].split()) for msg in self.messages)

        return {
            'total_turns': len(self.messages),
            'total_user_words': total_user_words,
            'total_assistant_words': total_assistant_words,
            'session_duration': (datetime.now() - self.session_start).total_seconds(),
            'user_context_keys': list(self.user_context.keys())
        }

#!/usr/bin/env python3
"""
Cluster Communication Agent (Phoenix Orchestrator)
AI-powered autonomous agent for cluster node communication

This agent:
1. Monitors node_chat.db for new messages
2. Analyzes message content and intent
3. Responds appropriately based on orchestrator role
4. Takes action when needed (deploy updates, coordinate tasks, etc.)
5. Runs continuously in the background
"""
import platform

import os
import sys
import time
import json
import sqlite3
import logging
import requests
import anthropic
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('/Volumes/SSDRAID0/agentic-system/logs/communication-agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ClusterCommunicationAgent:
    """AI-powered communication agent for Phoenix orchestrator"""

    def __init__(self, node_id: str = "mac-studio", use_ai: bool = False):
        self.node_id = node_id
        self.storage_base = Path(str(_STORAGE_BASE))
        self.chat_db = self.storage_base / "databases" / "cluster" / "node_chat.db"
        self.use_ai = use_ai

        # Track last processed message - start from beginning to catch all unread
        self.last_processed_timestamp = "2025-01-01T00:00:00"

        # API keys (only initialize if AI enabled)
        if use_ai:
            self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
            if self.anthropic_api_key:
                self.client = anthropic.Anthropic(api_key=self.anthropic_api_key)
                logger.info("AI analysis enabled")
            else:
                logger.warning("ANTHROPIC_API_KEY not set - falling back to pattern matching")
                self.client = None
                self.use_ai = False
        else:
            self.client = None
            logger.info("Using pattern matching mode (no API calls)")

        logger.info(f"Communication Agent initialized for {self.node_id}")

    def get_new_messages(self) -> List[Dict]:
        """Get new unread messages for this node"""
        if not self.chat_db.exists():
            return []

        conn = sqlite3.connect(str(self.chat_db))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT message_id, conversation_id, from_node, to_node, content, timestamp
            FROM messages
            WHERE (to_node = ? OR to_node = 'all')
              AND timestamp > ?
              AND delivered = 1
              AND read = 0
            ORDER BY timestamp ASC
        """, (self.node_id, self.last_processed_timestamp))

        messages = []
        for row in cursor.fetchall():
            messages.append({
                'message_id': row[0],
                'conversation_id': row[1],
                'from_node': row[2],
                'to_node': row[3],
                'content': row[4],
                'timestamp': row[5]
            })

        conn.close()
        return messages

    def mark_as_read(self, message_id: str):
        """Mark message as read"""
        conn = sqlite3.connect(str(self.chat_db))
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE messages
            SET read = 1, read_at = CURRENT_TIMESTAMP
            WHERE message_id = ?
        """, (message_id,))
        conn.commit()
        conn.close()

    def analyze_message_intent(self, message: Dict) -> Dict:
        """Use AI to analyze message intent and determine response"""
        if not self.client or not self.use_ai:
            # Enhanced pattern matching - no API calls needed
            content = message['content'].lower()

            # Check for questions
            if '?' in content or 'should i' in content or 'should we' in content:
                return {
                    'type': 'question',
                    'needs_response': True,
                    'action': 'acknowledge',
                    'priority': 'medium'
                }

            # Check for completion announcements
            elif 'complete' in content or 'deployed' in content or 'integrated' in content:
                return {
                    'type': 'update',
                    'needs_response': True,
                    'action': 'acknowledge',
                    'priority': 'medium'
                }

            # Check for broadcasts
            elif '[broadcast]' in content:
                # Determine if action needed based on keywords
                needs_action = any(word in content for word in ['sync', 'deploy', 'pull', 'install'])
                return {
                    'type': 'broadcast',
                    'needs_response': needs_action,
                    'action': 'coordinate' if needs_action else 'acknowledge',
                    'priority': 'high' if needs_action else 'low'
                }

            # Check for requests
            elif 'should' in content or 'recommend' in content or 'suggest' in content:
                return {
                    'type': 'request',
                    'needs_response': True,
                    'action': 'coordinate',
                    'priority': 'medium'
                }

            # Default: informational
            else:
                return {
                    'type': 'info',
                    'needs_response': False,
                    'action': 'none',
                    'priority': 'low'
                }

        # Use Claude to analyze intent (if AI enabled and available)
        try:
            prompt = f"""Analyze this cluster node message and determine:
1. Message type: question, request, update, broadcast, acknowledgment
2. Whether it needs a response from the orchestrator
3. What action (if any) should be taken

Message from {message['from_node']}:
{message['content']}

Respond with JSON:
{{
    "type": "question|request|update|broadcast|acknowledgment",
    "needs_response": true|false,
    "action": "none|deploy|coordinate|acknowledge|investigate",
    "priority": "low|medium|high",
    "summary": "brief summary of message"
}}"""

            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse JSON response
            text = response.content[0].text
            # Extract JSON if wrapped in markdown
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0].strip()
            elif '```' in text:
                text = text.split('```')[1].split('```')[0].strip()

            return json.loads(text)

        except Exception as e:
            logger.error(f"Error analyzing message intent: {e}")
            return {'type': 'unknown', 'needs_response': False, 'action': 'none'}

    def generate_response(self, message: Dict, intent: Dict) -> Optional[str]:
        """Generate appropriate response based on message and intent"""
        if not intent.get('needs_response'):
            return None

        if not self.client:
            # Simple auto-responses without AI
            if 'letta' in message['content'].lower():
                return "Acknowledged. Letta integration is being coordinated across the cluster."
            return "Message received and processed."

        # Use Claude to generate contextual response
        try:
            prompt = f"""You are Phoenix, the orchestrator node (mac-studio) of a distributed AI cluster.

Message from {message['from_node']}:
{message['content']}

Intent analysis: {json.dumps(intent)}

Generate a brief, professional response from the orchestrator's perspective. Include:
- Acknowledgment of the message
- Any status updates relevant to the message
- Next steps or coordination needed

Keep it concise (2-3 sentences max) and actionable."""

            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text.strip()

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "Acknowledged - processing your message."

    def send_response(self, to_node: str, content: str, conversation_id: str):
        """Send response message via node_chat_daemon"""
        conn = sqlite3.connect(str(self.chat_db))
        cursor = conn.cursor()

        import uuid

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO messages (message_id, conversation_id, from_node, to_node, content, timestamp, delivered, delivered_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
        """, (message_id, conversation_id, self.node_id, to_node, content, timestamp))

        conn.commit()
        conn.close()

        logger.info(f"Sent response to {to_node}: {content[:100]}...")

    def take_action(self, message: Dict, intent: Dict):
        """Take action based on message intent"""
        action = intent.get('action', 'none')

        if action == 'acknowledge':
            # Just mark as read, response already sent
            pass

        elif action == 'deploy':
            # Log deployment request
            logger.info(f"Deployment action requested by {message['from_node']}")
            # In production, this would trigger actual deployment
            # For now, just log it

        elif action == 'coordinate':
            # Log coordination request
            logger.info(f"Coordination requested: {message['content'][:100]}")

        elif action == 'investigate':
            # Log investigation needed
            logger.warning(f"Investigation needed for message from {message['from_node']}")

    def process_message(self, message: Dict):
        """Process a single message"""
        logger.info(f"Processing message from {message['from_node']}: {message['content'][:100]}...")

        # Analyze intent
        intent = self.analyze_message_intent(message)
        logger.info(f"Intent: {intent}")

        # Generate response if needed
        response = None
        if intent.get('needs_response'):
            response = self.generate_response(message, intent)
            if response:
                self.send_response(
                    message['from_node'],
                    response,
                    message['conversation_id']
                )

        # Take action
        self.take_action(message, intent)

        # Mark as read
        self.mark_as_read(message['message_id'])

        # Update last processed timestamp
        self.last_processed_timestamp = message['timestamp']

        logger.info(f"Processed message {message['message_id']}")

    def run(self, check_interval: int = 30):
        """Main loop - continuously monitor for new messages"""
        logger.info(f"Communication Agent running (check every {check_interval}s)")

        while True:
            try:
                # Get new messages
                messages = self.get_new_messages()

                if messages:
                    logger.info(f"Found {len(messages)} new message(s)")
                    for message in messages:
                        self.process_message(message)

                # Wait before next check
                time.sleep(check_interval)

            except KeyboardInterrupt:
                logger.info("Shutting down Communication Agent")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(check_interval)


def main():
    """Main entry point"""
    agent = ClusterCommunicationAgent(node_id="mac-studio")
    agent.run(check_interval=30)  # Check every 30 seconds


if __name__ == '__main__':
    main()

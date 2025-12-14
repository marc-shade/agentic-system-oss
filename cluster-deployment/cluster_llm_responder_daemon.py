#!/usr/bin/env python3
"""
Cluster LLM Responder Daemon

Autonomous agent that monitors cluster messages and responds intelligently.

Features:
- Continuous monitoring of node_chat.db for unread messages
- LLM-powered context understanding (Ollama)
- Autonomous action execution (package installation, file sync, etc.)
- Intelligent response generation
- Memory integration for decision tracking
- Safe command execution with whitelisting

Usage:
    # Run as daemon
    python3 cluster_llm_responder_daemon.py --daemon

    # Run in foreground (debugging)
    python3 cluster_llm_responder_daemon.py

    # Dry-run mode (no actions, just show what would happen)
    python3 cluster_llm_responder_daemon.py --dry-run

Configuration:
    Edit ~/.claude/cluster-responder-config.json to customize:
    - poll_interval: How often to check for messages (default: 30s)
    - llm_model: Ollama model for reasoning (default: llama3.2:latest)
    - auto_execute: Auto-execute safe commands (default: true)
    - safe_commands: Whitelist of allowed commands
"""

import os
import sys
import time
import json
import sqlite3
import logging
import signal
import subprocess
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('/Users/marc/agentic-system/logs/cluster_responder.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ResponderConfig:
    """Configuration for cluster responder daemon"""
    poll_interval: int = 30  # seconds
    llm_model: str = "llama3.2:latest"
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    auto_execute: bool = True
    max_context_messages: int = 10

    # Safe commands that can be auto-executed
    safe_commands: List[str] = None

    # Commands requiring confirmation
    confirmation_required: List[str] = None

    def __post_init__(self):
        if self.safe_commands is None:
            self.safe_commands = [
                "pip install",
                "python3 -m pip install",
                "scp",
                "ls",
                "cat",
                "grep",
                "find",
                "du",
                "df",
                "ps aux",
                "sqlite3"
            ]

        if self.confirmation_required is None:
            self.confirmation_required = [
                "rm -rf",
                "sudo",
                "chmod",
                "chown",
                "kill",
                "pkill"
            ]

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> 'ResponderConfig':
        """Load config from file or use defaults"""
        if config_path is None:
            config_path = Path.home() / ".claude" / "cluster-responder-config.json"

        if config_path.exists():
            with open(config_path) as f:
                data = json.load(f)
                return cls(**data)
        else:
            config = cls()
            config.save(config_path)
            return config

    def save(self, config_path: Path):
        """Save config to file"""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(asdict(self), f, indent=2)


class ClusterLLMResponder:
    """
    Autonomous LLM-powered cluster message responder
    """

    def __init__(self, node_id: str, storage_base: str, config: Optional[ResponderConfig] = None, dry_run: bool = False):
        self.node_id = node_id
        self.storage_base = Path(storage_base)
        self.config = config or ResponderConfig.load()
        self.dry_run = dry_run

        # Database paths
        self.chat_db = self.storage_base / "databases" / "cluster" / "node_chat.db"

        # Load cluster nodes
        self.cluster_nodes = self._load_cluster_nodes()

        # Running flag
        self.running = False

        # Stats
        self.stats = {
            "start_time": 0,
            "messages_processed": 0,
            "actions_executed": 0,
            "responses_sent": 0,
            "errors": 0
        }

        logger.info(f"Cluster LLM Responder initialized for {self.node_id}")
        logger.info(f"LLM Model: {self.config.llm_model}")
        logger.info(f"Dry-run mode: {self.dry_run}")

    def _load_cluster_nodes(self) -> Dict:
        """Load cluster node configuration"""
        config_path = self.storage_base / "cluster-deployment" / "cluster-nodes.json"
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)["nodes"]
        return {}

    def get_unread_messages(self) -> List[Dict]:
        """Get all unread messages for this node, filtering out self-messages and acknowledgements"""
        conn = sqlite3.connect(str(self.chat_db))
        cursor = conn.cursor()

        # IMPORTANT: Filter out messages from self to prevent infinite loops
        cursor.execute("""
            SELECT message_id, conversation_id, from_node, content, timestamp
            FROM messages
            WHERE (to_node = ? OR to_node LIKE '%broadcast%')
            AND from_node != ?
            AND read = 0
            ORDER BY timestamp ASC
        """, (self.node_id, self.node_id))

        messages = []
        for row in cursor.fetchall():
            content = row[3]

            # Filter out acknowledgement messages to prevent loops
            if self._is_acknowledgement_message(content):
                logger.debug(f"Skipping acknowledgement message from {row[2]}")
                # Mark as read to prevent re-processing
                self._mark_message_read_silent(row[0], conn)
                continue

            messages.append({
                'message_id': row[0],
                'conversation_id': row[1],
                'from_node': row[2],
                'content': content,
                'timestamp': row[4]
            })

        conn.close()
        return messages

    def _is_acknowledgement_message(self, content: str) -> bool:
        """Check if message is just an acknowledgement that shouldn't trigger a response"""
        if not content:
            return True

        content_lower = content.lower().strip()

        # Common acknowledgement patterns that cause loops
        ack_patterns = [
            "received your message",
            "processing...",
            "analyzing...",
            "acknowledged",
            "message received",
            "got it",
            "understood",
            "ok, processing",
            "working on it",
        ]

        for pattern in ack_patterns:
            if content_lower.startswith(pattern) or pattern in content_lower[:100]:
                return True

        # Very short messages are likely acknowledgements
        if len(content.strip()) < 20 and not any(c in content for c in ['?', 'install', 'run', 'execute', 'check']):
            return True

        return False

    def _mark_message_read_silent(self, message_id: str, conn: sqlite3.Connection):
        """Silently mark a message as read without logging"""
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE messages
                SET read = 1, read_at = CURRENT_TIMESTAMP
                WHERE message_id = ?
            """, (message_id,))
            conn.commit()
        except Exception:
            pass  # Ignore errors in silent marking

    def get_conversation_context(self, conversation_id: str, limit: int = 10) -> List[Dict]:
        """Get recent messages from conversation for context"""
        conn = sqlite3.connect(str(self.chat_db))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT from_node, content, timestamp
            FROM messages
            WHERE conversation_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (conversation_id, limit))

        messages = []
        for row in cursor.fetchall():
            messages.append({
                'from': row[0],
                'content': row[1],
                'timestamp': row[2]
            })

        conn.close()
        return list(reversed(messages))  # Chronological order

    def mark_as_read(self, message_id: str):
        """Mark message as read"""
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would mark message {message_id} as read")
            return

        conn = sqlite3.connect(str(self.chat_db))
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE messages
            SET read = 1, read_at = CURRENT_TIMESTAMP
            WHERE message_id = ?
        """, (message_id,))
        conn.commit()
        conn.close()

    def send_response(self, to_node: str, content: str, conversation_id: Optional[str] = None) -> bool:
        """Send response message to cluster"""
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would send to {to_node}: {content[:100]}...")
            return True

        conn = sqlite3.connect(str(self.chat_db))
        cursor = conn.cursor()

        # Get or create conversation
        if not conversation_id:
            participants = ','.join(sorted([self.node_id, to_node]))
            cursor.execute("""
                SELECT conversation_id FROM conversations
                WHERE participants = ? AND active = 1
                ORDER BY last_activity DESC LIMIT 1
            """, (participants,))
            result = cursor.fetchone()

            if result:
                conversation_id = result[0]
            else:
                conversation_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO conversations (conversation_id, participants)
                    VALUES (?, ?)
                """, (conversation_id, participants))

        # Send message
        message_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO messages (message_id, conversation_id, from_node, to_node, content, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (message_id, conversation_id, self.node_id, to_node, content, datetime.now().isoformat()))

        # Update conversation activity
        cursor.execute("""
            UPDATE conversations
            SET last_activity = CURRENT_TIMESTAMP
            WHERE conversation_id = ?
        """, (conversation_id,))

        conn.commit()
        conn.close()

        logger.info(f"✓ Response sent to {to_node}")
        self.stats["responses_sent"] += 1
        return True

    def query_llm(self, prompt: str) -> str:
        """Query Ollama LLM for reasoning"""
        try:
            response = requests.post(
                f"{self.config.ollama_host}/api/generate",
                json={
                    "model": self.config.llm_model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )

            if response.status_code == 200:
                return response.json()["response"]
            else:
                logger.error(f"LLM query failed: HTTP {response.status_code}")
                return ""

        except Exception as e:
            logger.error(f"LLM query error: {e}")
            return ""

    def analyze_message(self, message: Dict, context: List[Dict]) -> Dict:
        """Analyze message and determine response using LLM"""

        # Build context for LLM
        context_str = "\n".join([
            f"{msg['from']}: {msg['content'][:200]}"
            for msg in context[-5:]  # Last 5 messages
        ])

        prompt = f"""You are an autonomous cluster node agent ({self.node_id}) analyzing an incoming message.

CLUSTER ROLE: {self.cluster_nodes.get(self.node_id, {}).get('role', 'unknown')}
OS: {self.cluster_nodes.get(self.node_id, {}).get('os', 'unknown')}

RECENT CONVERSATION:
{context_str}

NEW MESSAGE:
From: {message['from_node']}
Content: {message['content']}

Analyze this message and determine:
1. Intent: What is the sender asking/telling me?
2. Required Actions: What commands/actions should I take?
3. Response: What should I reply to the sender?

Respond in JSON format:
{{
  "intent": "brief description of intent",
  "actions": ["command1", "command2"],
  "response": "message to send back",
  "priority": "high|medium|low"
}}

IMPORTANT:
- Only suggest SAFE commands (pip install, scp, ls, cat, grep, etc.)
- For package installations, use: python3 -m venv .venv-<name> && source .venv-<name>/bin/activate && pip install <package>
- For file sync: use scp with full paths
- Be concise and actionable
"""

        llm_response = self.query_llm(prompt)

        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                return analysis
            else:
                logger.warning("No JSON found in LLM response")
                return {
                    "intent": "unclear",
                    "actions": [],
                    "response": "Received your message. Processing...",
                    "priority": "low"
                }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"LLM response: {llm_response}")
            return {
                "intent": "parse_error",
                "actions": [],
                "response": "Received your message. Analyzing...",
                "priority": "low"
            }

    def is_command_safe(self, command: str) -> bool:
        """Check if command is in safe whitelist"""
        for safe_cmd in self.config.safe_commands:
            if command.strip().startswith(safe_cmd):
                return True
        return False

    def requires_confirmation(self, command: str) -> bool:
        """Check if command requires confirmation"""
        for danger_cmd in self.config.confirmation_required:
            if danger_cmd in command:
                return True
        return False

    def execute_action(self, action: str) -> Tuple[bool, str]:
        """Execute action command safely"""
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would execute: {action}")
            return True, "[DRY-RUN] Simulated execution"

        # Check safety
        if not self.is_command_safe(action):
            logger.warning(f"Unsafe command blocked: {action}")
            return False, "Command not in safe whitelist"

        if self.requires_confirmation(action):
            logger.warning(f"Command requires confirmation: {action}")
            return False, "Command requires manual confirmation"

        try:
            result = subprocess.run(
                action,
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.storage_base)
            )

            if result.returncode == 0:
                logger.info(f"✓ Action executed successfully: {action}")
                self.stats["actions_executed"] += 1
                return True, result.stdout
            else:
                logger.error(f"✗ Action failed: {action}")
                logger.error(f"Error: {result.stderr}")
                return False, result.stderr

        except subprocess.TimeoutExpired:
            logger.error(f"Action timed out: {action}")
            return False, "Command timed out"
        except Exception as e:
            logger.error(f"Action execution error: {e}")
            return False, str(e)

    def process_message(self, message: Dict):
        """Process a single unread message"""
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing message from {message['from_node']}")
        logger.info(f"Content: {message['content'][:100]}...")

        # Get conversation context
        context = self.get_conversation_context(message['conversation_id'])

        # Analyze with LLM
        analysis = self.analyze_message(message, context)

        logger.info(f"Intent: {analysis['intent']}")
        logger.info(f"Priority: {analysis.get('priority', 'unknown')}")
        logger.info(f"Actions: {len(analysis.get('actions', []))}")

        # Execute actions
        action_results = []
        for action in analysis.get('actions', []):
            logger.info(f"Executing: {action}")
            success, output = self.execute_action(action)
            action_results.append({
                'action': action,
                'success': success,
                'output': output[:200] if output else ""
            })

        # Build response
        response_content = analysis.get('response', 'Acknowledged.')

        if action_results:
            response_content += "\n\nActions taken:"
            for result in action_results:
                status = "✓" if result['success'] else "✗"
                response_content += f"\n{status} {result['action']}"
                if not result['success']:
                    response_content += f"\n  Error: {result['output']}"

        # Send response
        self.send_response(message['from_node'], response_content, message['conversation_id'])

        # Mark as read
        self.mark_as_read(message['message_id'])

        self.stats["messages_processed"] += 1
        logger.info(f"✓ Message processed successfully")
        logger.info(f"{'='*60}\n")

    def run_cycle(self):
        """Run one cycle of message checking and processing"""
        try:
            messages = self.get_unread_messages()

            if messages:
                logger.info(f"Found {len(messages)} unread message(s)")
                for message in messages:
                    self.process_message(message)
            else:
                logger.debug("No unread messages")

        except Exception as e:
            logger.error(f"Error in run cycle: {e}", exc_info=True)
            self.stats["errors"] += 1

    def start(self):
        """Start the responder daemon"""
        logger.info(f"{'='*60}")
        logger.info(f"Cluster LLM Responder Starting")
        logger.info(f"{'='*60}")
        logger.info(f"Node: {self.node_id}")
        logger.info(f"LLM Model: {self.config.llm_model}")
        logger.info(f"Poll Interval: {self.config.poll_interval}s")
        logger.info(f"Auto-execute: {self.config.auto_execute}")
        logger.info(f"Dry-run: {self.dry_run}")
        logger.info(f"")
        logger.info(f"Press Ctrl+C to stop")
        logger.info(f"{'='*60}\n")

        self.running = True
        self.stats["start_time"] = time.time()

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        try:
            while self.running:
                self.run_cycle()
                time.sleep(self.config.poll_interval)

        except KeyboardInterrupt:
            logger.info("\n\nReceived interrupt signal")
        finally:
            self.stop()

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"\nReceived signal {signum}")
        self.running = False

    def stop(self):
        """Stop the responder daemon"""
        logger.info("\nStopping Cluster LLM Responder...")

        uptime = time.time() - self.stats["start_time"]
        logger.info(f"\nFinal Statistics:")
        logger.info(f"  Uptime: {uptime/3600:.1f}h")
        logger.info(f"  Messages Processed: {self.stats['messages_processed']}")
        logger.info(f"  Actions Executed: {self.stats['actions_executed']}")
        logger.info(f"  Responses Sent: {self.stats['responses_sent']}")
        logger.info(f"  Errors: {self.stats['errors']}")

        logger.info("\n✓ Cluster LLM Responder stopped")


def main():
    """CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(description="Cluster LLM Responder Daemon")
    parser.add_argument("--daemon", action="store_true", help="Run as background daemon")
    parser.add_argument("--dry-run", action="store_true", help="Dry-run mode (no actions)")
    parser.add_argument("--config", type=str, help="Path to config file")
    parser.add_argument("--node-id", type=str, help="Override node ID")
    parser.add_argument("--storage-base", type=str, help="Override storage base path")

    args = parser.parse_args()

    # Load node configuration
    if args.node_id and args.storage_base:
        node_id = args.node_id
        storage_base = args.storage_base
    else:
        node_config_path = Path.home() / ".claude" / "node-config.json"
        if not node_config_path.exists():
            logger.error("Node configuration not found. Specify --node-id and --storage-base")
            sys.exit(1)

        with open(node_config_path) as f:
            config = json.load(f)

        node_id = config['node_id']
        storage_base = config['storage']['base']

    # Load responder config
    config_path = Path(args.config) if args.config else None
    responder_config = ResponderConfig.load(config_path)

    # Create and start responder
    responder = ClusterLLMResponder(node_id, storage_base, responder_config, dry_run=args.dry_run)

    if args.daemon:
        # TODO: Implement proper daemonization
        logger.warning("Daemon mode not yet implemented, running in foreground")

    responder.start()


if __name__ == "__main__":
    main()

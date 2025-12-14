#!/usr/bin/env python3
"""
Autonomous Node Communication Agent

Enables persistent agent-to-agent communication across the cluster.
Each node runs this agent to:
- Monitor for incoming messages from other nodes
- Generate contextual AI responses using node persona
- Handle multi-turn conversations with memory
- Execute tasks requested by other nodes
- Proactively communicate when needed

This creates true autonomous distributed AI collaboration.
"""

import os
import sys
import json
import sqlite3
import logging
import time
import asyncio
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
# Anthropic import replaced with Ollama for zero-cost operation
# from anthropic import Anthropic

# Detect storage base for logging
def _detect_storage_base():
    """
    Auto-detect storage base from node config ONLY.

    CRITICAL: Never fallback to filesystem detection as nodes may have
    multiple volumes mounted and we must respect each node's own config.
    """
    config_path = Path.home() / ".claude" / "node-config.json"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Node configuration not found at {config_path}. "
            "Each node MUST have its own node-config.json with storage.base set."
        )

    import json
    with open(config_path) as f:
        config = json.load(f)
        storage_base = config.get('storage', {}).get('base')

        if not storage_base:
            raise ValueError(
                f"Node configuration at {config_path} missing 'storage.base'. "
                "This is required for proper path management."
            )

        # Log which path we're using for transparency
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        logger.info(f"Using storage base from node config: {storage_base}")

        return storage_base

STORAGE_BASE = _detect_storage_base()
LOG_DIR = Path(STORAGE_BASE) / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(str(LOG_DIR / 'autonomous-agent.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AutonomousNodeAgent:
    """Autonomous AI agent for inter-node communication and collaboration"""

    def __init__(self, node_id: str, storage_base: str, anthropic_api_key: str = None, ollama_url: str = None):
        self.node_id = node_id
        self.storage_base = Path(storage_base)

        # Use cluster Ollama servers ONLY (macpro51 has NO GPU - cannot run LLM on CPU!)
        # Priority order: completeu-server (23 models, GPU) -> mac-studio (32 models, GPU)
        # NEVER use local - macpro51 is CPU-only builder node!
        self.ollama_servers = [
            {"url": "http://192.168.1.186:11434", "node": "completeu-server", "models": 23, "has_gpu": True},
            {"url": "http://192.168.1.16:11434", "node": "mac-studio", "models": 32, "has_gpu": True}
            # NO LOCAL OLLAMA - macpro51 is CPU-only!
        ]
        self.ollama_model = "mistral:latest"  # Fast Q4_K_M quantized model (4x faster than FP16)
        self.current_ollama_server = None  # Will be selected dynamically

        # Load node configuration
        self.node_config = self._load_node_config()
        self.cluster_nodes = self._load_cluster_nodes()

        # Database paths
        self.chat_db = self.storage_base / "databases" / "cluster" / "node_chat.db"
        self.memory_db = self.storage_base / "databases" / "cluster" / "nodes" / node_id / "personal_memories.db"

        # Conversation context cache (for multi-turn)
        self.conversation_contexts = {}

        # Poll interval (seconds)
        self.poll_interval = 10

        # Response generation enabled
        self.auto_respond = True

        logger.info(f"Autonomous agent initialized for {self.node_id}")
        logger.info(f"Persona: {self.node_config.get('persona', 'generic')}")

    def _load_node_config(self) -> Dict:
        """Load node configuration"""
        config_path = Path.home() / ".claude" / "node-config.json"
        with open(config_path) as f:
            return json.load(f)

    def _load_cluster_nodes(self) -> Dict:
        """Load cluster node registry"""
        config_path = self.storage_base / "cluster-deployment" / "cluster-nodes.json"
        with open(config_path) as f:
            return json.load(f)["nodes"]

    def get_node_persona_prompt(self) -> str:
        """
        Generate system prompt for this node's AI persona

        Each node has a distinct persona that guides responses:
        - macpro51: Linux Builder (compilation, testing, containerization)
        - mac-studio: Orchestrator (coordination, monitoring, strategy)
        - macbook-air-m3: Researcher (analysis, documentation, learning)
        """
        persona = self.node_config.get('persona', 'generic')
        capabilities = self.node_config.get('capabilities', [])
        hardware = self.node_config.get('hardware', {})

        base_prompt = f"""You are {self.node_id}, an autonomous AI agent in a distributed cluster.

**Your Identity:**
- Node ID: {self.node_id}
- Persona: {persona}
- Capabilities: {', '.join(capabilities)}
- Hardware: {hardware.get('model', 'Unknown')} running {hardware.get('os', 'Unknown')}

**Your Role in the Cluster:**
"""

        # Add persona-specific guidance
        if persona == "linux-worker" or self.node_id == "macpro51":
            base_prompt += """
You are the Linux Builder node. Your specialties:
- Compilation and build processes (make, gcc, cargo, etc.)
- Container operations (Podman, Docker)
- Performance benchmarking and testing
- Linux-specific tasks (systemd, SELinux, RAID management)
- CI/CD workload execution

When other nodes ask you to build or test something, you execute it and report results.
You are practical, detail-oriented, and focus on execution quality.
"""
        elif persona == "orchestrator" or self.node_id == "mac-studio":
            base_prompt += """
You are the Orchestrator node. Your specialties:
- System-wide coordination and task routing
- Monitoring and health checks
- Strategic planning and architecture decisions
- Resource allocation across cluster
- High-level workflow management

You coordinate complex multi-node operations and make strategic decisions.
You are analytical, forward-thinking, and focus on system optimization.
"""
        elif persona == "researcher" or self.node_id == "macbook-air-m3":
            base_prompt += """
You are the Researcher node. Your specialties:
- Research paper analysis and knowledge extraction
- Documentation and technical writing
- Learning new concepts and technologies
- Pattern recognition and insight generation
- Knowledge synthesis from multiple sources

You analyze information, generate insights, and document learnings for the cluster.
You are curious, thorough, and focus on knowledge advancement.
"""

        base_prompt += """

**Communication Style:**
- Be concise and technical - you're talking to other AI agents
- Use markdown for structure when helpful
- Share specific technical details (file paths, commands, metrics)
- Ask clarifying questions when needed
- Proactively offer help within your capabilities

**Multi-Turn Conversations:**
- Maintain context across multiple messages
- Reference previous messages in the conversation
- Build on shared understanding
- Coordinate actions with other nodes when appropriate

**Task Execution:**
- When asked to perform a task, execute it and report results
- Share logs, errors, and metrics
- If a task fails, explain why and suggest alternatives
- Coordinate with other nodes for distributed tasks

**Current Context:**
You are communicating with other autonomous agents in real-time. They can see your responses and reply. Work together to solve problems, share knowledge, and coordinate actions across the cluster.
"""
        return base_prompt

    def get_unread_messages(self) -> List[Dict]:
        """Fetch unread messages from database"""
        conn = sqlite3.connect(str(self.chat_db))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT message_id, conversation_id, from_node, content, timestamp
            FROM messages
            WHERE to_node = ? AND read = 0
            ORDER BY timestamp ASC
        """, (self.node_id,))

        messages = []
        for row in cursor.fetchall():
            messages.append({
                'message_id': row[0],
                'conversation_id': row[1],
                'from_node': row[2],
                'content': row[3],
                'timestamp': row[4]
            })

        conn.close()
        return messages

    def mark_message_read(self, message_id: str):
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

    def get_conversation_context(self, conversation_id: str, limit: int = 10) -> List[Dict]:
        """Get recent conversation history for context"""
        # Check cache first
        if conversation_id in self.conversation_contexts:
            cached = self.conversation_contexts[conversation_id]
            if datetime.now() - cached['timestamp'] < timedelta(minutes=5):
                return cached['messages']

        # Fetch from database
        conn = sqlite3.connect(str(self.chat_db))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT from_node, to_node, content, timestamp
            FROM messages
            WHERE conversation_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (conversation_id, limit))

        messages = []
        for row in cursor.fetchall():
            messages.append({
                'from_node': row[0],
                'to_node': row[1],
                'content': row[2],
                'timestamp': row[3]
            })

        conn.close()

        # Reverse to chronological order
        messages = list(reversed(messages))

        # Update cache
        self.conversation_contexts[conversation_id] = {
            'messages': messages,
            'timestamp': datetime.now()
        }

        return messages

    def generate_response(self, message: Dict, conversation_context: List[Dict]) -> Optional[str]:
        """
        Generate AI response to message using LOCAL OLLAMA (ZERO COST!)

        Uses:
        - Node persona for personality/capabilities
        - Conversation history for context
        - Message content for specific request
        - Local Ollama for inference (no API costs)
        """
        try:
            # Build conversation context
            context_text = self.get_node_persona_prompt() + "\n\n**Recent Conversation:**\n"

            # Add context from previous messages
            for ctx_msg in conversation_context[-5:]:  # Last 5 messages
                context_text += f"\n[{ctx_msg['from_node']}]: {ctx_msg['content']}"

            # Add current message
            context_text += f"\n[{message['from_node']}]: {message['content']}"
            context_text += f"\n\n[{self.node_id}]: "

            # Generate response using CLUSTER Ollama servers (ZERO COST!)
            # Try each server in priority order (offload-first strategy)
            import requests

            for server_info in self.ollama_servers:
                try:
                    response = requests.post(
                        f"{server_info['url']}/api/generate",
                        json={
                            "model": self.ollama_model,
                            "prompt": context_text,
                            "stream": False,
                            "options": {
                                "temperature": 0.7,
                                "top_p": 0.9,
                                "top_k": 40
                            }
                        },
                        timeout=30  # 30s timeout for full response generation
                    )

                    if response.status_code == 200:
                        response_data = response.json()
                        response_text = response_data.get('response', '').strip()

                        logger.info(f"Generated response to {message['from_node']} using {server_info['node']} Ollama (ZERO COST!): {response_text[:100]}...")
                        self.current_ollama_server = server_info['node']
                        return response_text
                except Exception as e:
                    logger.warning(f"Failed to use {server_info['node']} Ollama: {e}, trying next server...")
                    continue

            # All servers failed
            logger.error(f"All Ollama servers failed, using fallback")
            return None

        except Exception as e:
            logger.error(f"Failed to generate response with cluster Ollama: {e}")
            # Fallback to simple acknowledgment if all cluster Ollama servers fail
            # NOTE: No local fallback - macpro51 is CPU-only and cannot run LLM!
            return f"[CLUSTER UNAVAILABLE] Acknowledged: '{message['content'][:100]}...'. Both completeu-server and mac-studio Ollama are offline. Cannot generate AI response on macpro51 (CPU-only, no GPU)."

    def send_message(self, to_node: str, content: str, conversation_id: Optional[str] = None) -> Dict:
        """Send message to another node using MCP node-chat tool"""
        try:
            # Use node chat client for multi-channel delivery
            from node_chat_client import NodeChatClient

            client = NodeChatClient(self.node_id, str(self.storage_base))
            result = client.send_message(to_node, content, conversation_id)

            logger.info(f"Sent message to {to_node}: {content[:100]}...")
            return result

        except Exception as e:
            logger.error(f"Failed to send message to {to_node}: {e}")
            return {'success': False, 'error': str(e)}

    def execute_task_request(self, from_node: str, task_description: str) -> str:
        """
        Execute task requested by another node

        Recognizes common task patterns:
        - "run tests for X"
        - "build X"
        - "benchmark X"
        - "research X" (for researcher node)
        - "analyze X" (for orchestrator node)
        """
        task_lower = task_description.lower()

        # Pattern: Run tests
        if "run test" in task_lower or "test" in task_lower:
            return self._execute_test_task(task_description)

        # Pattern: Build/compile
        elif "build" in task_lower or "compile" in task_lower or "make" in task_lower:
            return self._execute_build_task(task_description)

        # Pattern: Benchmark/performance
        elif "benchmark" in task_lower or "performance" in task_lower:
            return self._execute_benchmark_task(task_description)

        # Pattern: Research (for researcher node)
        elif "research" in task_lower and self.node_id == "macbook-air-m3":
            return self._execute_research_task(task_description)

        # Pattern: Analyze (for orchestrator)
        elif "analyze" in task_lower and self.node_id == "mac-studio":
            return self._execute_analysis_task(task_description)

        # Generic: Try to infer intent
        else:
            return f"I received your request: '{task_description}'. Could you be more specific about what you'd like me to do? I can run tests, build code, benchmark performance, or help with other {self.node_id}-specific tasks."

    def _execute_test_task(self, task: str) -> str:
        """Execute test task (macpro51 specialty)"""
        if self.node_id != "macpro51":
            return f"I'm {self.node_id}, not the build/test node. You should ask macpro51 to run tests."

        # Extract test target from task description
        # For now, return explanation - full execution would integrate with cluster_offload
        return f"Acknowledged test request: '{task}'. I would execute this using my test infrastructure. (Full integration with cluster_offload pending)"

    def _execute_build_task(self, task: str) -> str:
        """Execute build task (macpro51 specialty)"""
        if self.node_id != "macpro51":
            return f"I'm {self.node_id}, not the build node. You should ask macpro51 to build."

        return f"Acknowledged build request: '{task}'. I would execute this using make/cargo/docker. (Full integration pending)"

    def _execute_benchmark_task(self, task: str) -> str:
        """Execute benchmark task (macpro51 specialty)"""
        if self.node_id != "macpro51":
            return f"I'm {self.node_id}, not the benchmark node. You should ask macpro51 for benchmarks."

        return f"Acknowledged benchmark request: '{task}'. I would run performance tests. (Full integration pending)"

    def _execute_research_task(self, task: str) -> str:
        """Execute research task (macbook-air-m3 specialty)"""
        return f"Acknowledged research request: '{task}'. I would search papers and extract insights. (Full integration pending)"

    def _execute_analysis_task(self, task: str) -> str:
        """Execute analysis task (mac-studio specialty)"""
        return f"Acknowledged analysis request: '{task}'. I would analyze system metrics and trends. (Full integration pending)"

    def process_message(self, message: Dict):
        """Process a single incoming message"""
        try:
            logger.info(f"Processing message from {message['from_node']}: {message['content'][:100]}...")

            # Get conversation context
            context = self.get_conversation_context(message['conversation_id'])

            # Check if message requests task execution
            should_execute_task = any(keyword in message['content'].lower()
                                     for keyword in ['please', 'can you', 'could you', 'run', 'execute', 'build', 'test'])

            # Generate response
            if should_execute_task:
                # Try to execute task first
                task_result = self.execute_task_request(message['from_node'], message['content'])

                # Generate AI response incorporating task result
                ai_response = self.generate_response(message, context)

                if ai_response:
                    response_text = f"{ai_response}\n\n**Task Execution:**\n{task_result}"
                else:
                    response_text = task_result
            else:
                # Pure conversational response
                response_text = self.generate_response(message, context)

            if not response_text:
                logger.warning(f"No response generated for message {message['message_id']}")
                return

            # Send response
            result = self.send_message(
                to_node=message['from_node'],
                content=response_text,
                conversation_id=message['conversation_id']
            )

            # Mark original message as read
            self.mark_message_read(message['message_id'])

            # Log success
            if result.get('success'):
                delivered_channels = [k for k, v in result.get('delivery_channels', {}).items()
                                    if v.get('success')]
                logger.info(f"Response sent to {message['from_node']} via {', '.join(delivered_channels)}")
            else:
                logger.error(f"Failed to send response to {message['from_node']}")

        except Exception as e:
            logger.error(f"Error processing message {message['message_id']}: {e}")

    async def message_processing_loop(self):
        """Main loop for processing incoming messages"""
        logger.info("Starting message processing loop")

        while True:
            try:
                # Check for unread messages
                messages = self.get_unread_messages()

                if messages:
                    logger.info(f"Found {len(messages)} unread message(s)")

                    # Process each message
                    for message in messages:
                        if self.auto_respond:
                            self.process_message(message)
                        else:
                            logger.info(f"Auto-respond disabled, skipping message {message['message_id']}")
                            self.mark_message_read(message['message_id'])

                # Sleep before next poll
                await asyncio.sleep(self.poll_interval)

            except KeyboardInterrupt:
                logger.info("Shutting down message processing loop")
                break
            except Exception as e:
                logger.error(f"Error in message processing loop: {e}")
                await asyncio.sleep(self.poll_interval)

    def start(self):
        """Start the autonomous agent"""
        logger.info(f"Starting autonomous agent for {self.node_id}")
        logger.info(f"Poll interval: {self.poll_interval}s")
        logger.info(f"Auto-respond: {self.auto_respond}")

        # Run async loop
        asyncio.run(self.message_processing_loop())


def main():
    """Main entry point - CLUSTER OLLAMA ONLY (NO API KEY NEEDED!)"""
    # NO API KEY CHECK - We use cluster Ollama servers only!
    # This eliminates ALL API costs and runs 100% on cluster resources

    # Load node config
    node_config_path = Path.home() / ".claude" / "node-config.json"
    if not node_config_path.exists():
        logger.error("Node configuration not found")
        sys.exit(1)

    with open(node_config_path) as f:
        config = json.load(f)

    node_id = config['node_id']
    storage_base = config['storage']['base']

    # Create and start agent (NO API KEY - cluster Ollama only!)
    agent = AutonomousNodeAgent(node_id, storage_base)

    try:
        agent.start()
    except KeyboardInterrupt:
        logger.info("Agent stopped by user")
    except Exception as e:
        logger.error(f"Agent crashed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

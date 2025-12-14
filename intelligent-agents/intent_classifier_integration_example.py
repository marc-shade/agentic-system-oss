#!/usr/bin/env python3
"""
Intent Classifier Integration Example

Demonstrates how to integrate the intent classifier with:
1. Voice Mode MCP (TTS/STT)
2. Consciousness Daemon (reasoning)
3. Conversation Manager (state management)
"""
import os
import platform
from pathlib import Path

import asyncio
import logging
from typing import Dict, Any
from intent_classifier import IntentClassifier, Intent

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


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("intent_integration")


class VoiceCommandProcessor:
    """
    Processes voice commands through the full pipeline:
    Voice Input → Intent Classification → Reasoning → Action Execution
    """

    def __init__(self, api_key: str = None):
        """Initialize voice command processor"""
        self.classifier = IntentClassifier(api_key=api_key)
        self.session_state = {
            "working_directory": str(_STORAGE_BASE),
            "open_files": [],
            "active_branch": "master",
            "running_services": ["redis", "qdrant", "prometheus"]
        }

        # Update classifier with session state
        self.classifier.update_session_context(self.session_state)

        logger.info("Voice command processor initialized")

    async def process_utterance(self, utterance: str) -> Dict[str, Any]:
        """
        Process a voice utterance through the full pipeline

        Args:
            utterance: User's voice input

        Returns:
            Processing result with action taken
        """
        logger.info(f"Processing utterance: {utterance}")

        # Step 1: Classify intent
        intent = await self.classifier.classify(utterance)

        logger.info(f"Intent classified: {intent.type} (confidence: {intent.confidence:.2f})")
        logger.info(f"Entities: {intent.entities}")

        # Step 2: Route based on intent type
        if intent.type == IntentClassifier.COMMAND:
            result = await self._handle_command(intent)
        elif intent.type == IntentClassifier.QUERY:
            result = await self._handle_query(intent)
        elif intent.type == IntentClassifier.CONVERSATION:
            result = await self._handle_conversation(intent)
        elif intent.type == IntentClassifier.META:
            result = await self._handle_meta(intent)
        else:
            result = {
                "status": "error",
                "message": f"Unknown intent type: {intent.type}"
            }

        return {
            "intent": intent.to_dict(),
            "result": result
        }

    async def _handle_command(self, intent: Intent) -> Dict[str, Any]:
        """Handle COMMAND intents"""
        entities = intent.entities
        operation = entities.get("operation")
        file_path = entities.get("file_path")
        git_operation = entities.get("git_operation")

        logger.info(f"Handling command: operation={operation}, file={file_path}, git={git_operation}")

        # File operations
        if file_path and operation:
            if operation == "fix":
                return await self._fix_file(file_path[0])
            elif operation == "create":
                return await self._create_file(file_path[0])
            elif operation == "refactor":
                return await self._refactor_code(file_path[0], entities.get("target"))

        # Git operations
        if git_operation:
            if git_operation == "commit":
                return await self._git_commit(entities)
            elif git_operation == "branch":
                return await self._git_branch(entities.get("branch_name"))
            elif git_operation == "merge":
                return await self._git_merge(entities.get("branch_name"))

        # System operations
        service_name = entities.get("service_name")
        if service_name and operation:
            if operation == "restart":
                return await self._restart_service(service_name[0])
            elif operation == "stop":
                return await self._stop_service(service_name[0])

        return {
            "status": "error",
            "message": f"Could not execute command: {intent.original_utterance}"
        }

    async def _handle_query(self, intent: Intent) -> Dict[str, Any]:
        """Handle QUERY intents"""
        entities = intent.entities
        function_name = entities.get("function_name")
        service_name = entities.get("service_name")
        git_operation = entities.get("git_operation")

        logger.info(f"Handling query: function={function_name}, service={service_name}, git={git_operation}")

        # Code inspection
        if function_name:
            return await self._explain_function(function_name[0])

        # Service status
        if service_name:
            return await self._check_service_status(service_name[0])

        # Git history
        if git_operation:
            if git_operation == "commits":
                return await self._show_git_commits(entities.get("count", 10))
            elif git_operation == "status":
                return await self._show_git_status()

        return {
            "status": "error",
            "message": f"Could not answer query: {intent.original_utterance}"
        }

    async def _handle_conversation(self, intent: Intent) -> Dict[str, Any]:
        """Handle CONVERSATION intents"""
        entities = intent.entities
        confirmation = entities.get("confirmation")

        logger.info(f"Handling conversation: confirmation={confirmation}")

        if confirmation == "yes":
            return {
                "status": "success",
                "message": "Confirmed. Proceeding with previous action.",
                "action": "proceed"
            }
        elif confirmation == "no":
            return {
                "status": "success",
                "message": "Cancelled. What would you like to do instead?",
                "action": "cancel"
            }
        else:
            return {
                "status": "success",
                "message": "Acknowledged.",
                "action": "acknowledge"
            }

    async def _handle_meta(self, intent: Intent) -> Dict[str, Any]:
        """Handle META intents"""
        entities = intent.entities
        control_action = entities.get("control_action")
        preference = entities.get("preference")

        logger.info(f"Handling meta: control={control_action}, preference={preference}")

        if control_action:
            if control_action == "pause":
                return {"status": "success", "message": "Paused. Say 'continue' to resume.", "action": "pause"}
            elif control_action == "stop":
                return {"status": "success", "message": "Stopped.", "action": "stop"}
            elif control_action == "continue":
                return {"status": "success", "message": "Resuming...", "action": "continue"}

        if preference:
            return {
                "status": "success",
                "message": f"Preference updated: {preference}",
                "action": "update_preference"
            }

        return {
            "status": "success",
            "message": "Meta command processed.",
            "action": "meta"
        }

    # === Mock Action Implementations ===
    # In production, these would call actual system functions

    async def _fix_file(self, file_path: str) -> Dict[str, Any]:
        """Fix bugs in a file"""
        logger.info(f"Mock: Fixing bugs in {file_path}")
        return {
            "status": "success",
            "message": f"Analyzed {file_path} and fixed 2 bugs",
            "action": "fix_file",
            "file": file_path
        }

    async def _create_file(self, file_path: str) -> Dict[str, Any]:
        """Create a new file"""
        logger.info(f"Mock: Creating file {file_path}")
        return {
            "status": "success",
            "message": f"Created {file_path}",
            "action": "create_file",
            "file": file_path
        }

    async def _refactor_code(self, file_path: str, target: str) -> Dict[str, Any]:
        """Refactor code"""
        logger.info(f"Mock: Refactoring {target} in {file_path}")
        return {
            "status": "success",
            "message": f"Refactored {target} in {file_path}",
            "action": "refactor",
            "file": file_path,
            "target": target
        }

    async def _git_commit(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Create git commit"""
        logger.info("Mock: Creating git commit")
        return {
            "status": "success",
            "message": "Changes committed",
            "action": "git_commit"
        }

    async def _git_branch(self, branch_name: str) -> Dict[str, Any]:
        """Create git branch"""
        logger.info(f"Mock: Creating branch {branch_name}")
        return {
            "status": "success",
            "message": f"Branch '{branch_name}' created",
            "action": "git_branch",
            "branch": branch_name
        }

    async def _git_merge(self, branch_name: str) -> Dict[str, Any]:
        """Merge git branch"""
        logger.info(f"Mock: Merging branch {branch_name}")
        return {
            "status": "success",
            "message": f"Branch '{branch_name}' merged",
            "action": "git_merge",
            "branch": branch_name
        }

    async def _restart_service(self, service_name: str) -> Dict[str, Any]:
        """Restart a service"""
        logger.info(f"Mock: Restarting service {service_name}")
        return {
            "status": "success",
            "message": f"Service '{service_name}' restarted",
            "action": "restart_service",
            "service": service_name
        }

    async def _stop_service(self, service_name: str) -> Dict[str, Any]:
        """Stop a service"""
        logger.info(f"Mock: Stopping service {service_name}")
        return {
            "status": "success",
            "message": f"Service '{service_name}' stopped",
            "action": "stop_service",
            "service": service_name
        }

    async def _explain_function(self, function_name: str) -> Dict[str, Any]:
        """Explain a function"""
        logger.info(f"Mock: Explaining function {function_name}")
        return {
            "status": "success",
            "message": f"The {function_name} function handles user authentication and returns a JWT token",
            "action": "explain_function",
            "function": function_name
        }

    async def _check_service_status(self, service_name: str) -> Dict[str, Any]:
        """Check service status"""
        logger.info(f"Mock: Checking status of {service_name}")
        is_running = service_name.lower() in [s.lower() for s in self.session_state["running_services"]]
        return {
            "status": "success",
            "message": f"Service '{service_name}' is {'running' if is_running else 'stopped'}",
            "action": "check_service",
            "service": service_name,
            "is_running": is_running
        }

    async def _show_git_commits(self, count: int) -> Dict[str, Any]:
        """Show recent git commits"""
        logger.info(f"Mock: Showing {count} recent commits")
        return {
            "status": "success",
            "message": f"Showing {count} most recent commits",
            "action": "show_commits",
            "commits": [
                "c7430a1 Replace hardcoded IPs with dynamic node discovery",
                "09a5b73 Add SMB persistent availability system",
                "bd3a15b Update macpro51 IP from 192.168.1.154 to 192.168.1.183"
            ][:count]
        }

    async def _show_git_status(self) -> Dict[str, Any]:
        """Show git status"""
        logger.info("Mock: Showing git status")
        return {
            "status": "success",
            "message": "Current branch: master. 3 files modified, 2 files untracked.",
            "action": "git_status",
            "branch": self.session_state["active_branch"]
        }


async def demo_integration():
    """Demonstrate intent classifier integration"""
    print("=" * 80)
    print("Intent Classifier Integration Demo")
    print("=" * 80)

    # Initialize processor
    # Note: Will work without API key in mock mode, but won't do actual classification
    try:
        processor = VoiceCommandProcessor()
        has_api_key = True
    except ValueError:
        print("\n⚠️  No ANTHROPIC_API_KEY found - running in mock mode")
        print("   Set API key to enable real classification\n")
        has_api_key = False
        # Create mock results instead

    if not has_api_key:
        print("Showing mock integration flow without actual API calls:\n")
        mock_examples()
        return

    # Test utterances
    test_utterances = [
        "fix the bug in auth.py",
        "what does the login function do?",
        "show me recent git commits",
        "restart Redis",
        "yes, that looks good",
        "pause"
    ]

    print("\nProcessing voice commands:\n")

    for i, utterance in enumerate(test_utterances, 1):
        print(f"{'-' * 80}")
        print(f"Command {i}/{len(test_utterances)}: \"{utterance}\"")
        print()

        try:
            result = await processor.process_utterance(utterance)

            intent = result["intent"]
            action_result = result["result"]

            print(f"✅ Intent: {intent['type']} (confidence: {intent['confidence']:.2f})")
            print(f"   Entities: {intent['entities']}")
            print(f"   Result: {action_result['message']}")
            print()

        except Exception as e:
            print(f"❌ Error: {e}\n")

    # Show classifier stats
    print("=" * 80)
    print("Classifier Statistics")
    print("=" * 80)
    stats = processor.classifier.get_stats()
    print(f"Cache size: {stats['cache_size']}")
    print(f"Context window: {stats['context_window_size']}")
    print(f"Intent distribution: {stats['intent_type_distribution']}")
    print(f"Average confidence: {stats['average_confidence']:.2f}")


def mock_examples():
    """Show mock examples without API calls"""
    examples = [
        {
            "utterance": "fix the bug in auth.py",
            "intent_type": "COMMAND",
            "entities": {"file_path": ["auth.py"], "operation": "fix", "target": "bug"},
            "result": "Analyzed auth.py and fixed 2 bugs"
        },
        {
            "utterance": "what does the login function do?",
            "intent_type": "QUERY",
            "entities": {"function_name": ["login"], "operation": "explain"},
            "result": "The login function handles user authentication and returns a JWT token"
        },
        {
            "utterance": "show me recent git commits",
            "intent_type": "QUERY",
            "entities": {"git_operation": "commits", "timeframe": "recent", "count": 10},
            "result": "Showing 10 most recent commits"
        }
    ]

    for ex in examples:
        print(f"Utterance: \"{ex['utterance']}\"")
        print(f"  → Intent: {ex['intent_type']}")
        print(f"  → Entities: {ex['entities']}")
        print(f"  → Result: {ex['result']}")
        print()


if __name__ == "__main__":
    asyncio.run(demo_integration())

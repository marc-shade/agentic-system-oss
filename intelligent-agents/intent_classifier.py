#!/usr/bin/env python3
"""
Intent Classifier - Voice Command Classification
=================================================

Classifies voice commands into intent types for action orchestrator.

Intent Types:
- COMMAND: Code execution, file operations (create, edit, run, etc.)
- QUERY: Information retrieval (search, read, analyze)
- CONVERSATION: Natural language (greetings, questions, explanations)
- META: System control (status, configuration, help)

This classifier uses rule-based heuristics for fast, local classification
without API calls. Can be enhanced with TPU for better accuracy on
ambiguous cases.

TPU Integration:
    When rule-based confidence is low (< 0.7), falls back to Google Coral
    TPU's classify_intent for improved accuracy using neural classification.

Usage:
    classifier = IntentClassifier(use_tpu=True)
    intent = classifier.classify("Create a Python file called test.py")
    print(f"Type: {intent.type}, Confidence: {intent.confidence}")
"""
import platform
from pathlib import Path

import logging
import os
import re
import sys
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from action_orchestrator import Intent, IntentType

# TPU support - optional, graceful degradation if unavailable
# Uses tpu_importance module which handles pycoral via subprocess to coral-venv
TPU_AVAILABLE = False
_tpu_classify_intent = None

try:
    # Import from tpu_importance module (handles pycoral in coral-venv via subprocess)
    hooks_path = os.path.join(
        os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)),
        "scripts/hooks"
    )
    if hooks_path not in sys.path:
        sys.path.insert(0, hooks_path)

    from tpu_importance import classify_intent as tpu_classify, is_tpu_available

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

    if is_tpu_available():
        _tpu_classify_intent = tpu_classify
        TPU_AVAILABLE = True
except ImportError:
    pass
except Exception:
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("intent_classifier")


class IntentClassifier:
    """
    Classifies voice commands into intent types

    Uses rule-based pattern matching and keyword analysis for fast,
    local classification without requiring API calls.

    Optionally uses Google Coral TPU for improved accuracy when
    rule-based confidence is low.
    """

    def __init__(self, use_tpu: bool = True, tpu_threshold: float = 0.7):
        """
        Initialize intent classifier with pattern definitions

        Args:
            use_tpu: Enable TPU fallback for low-confidence cases
            tpu_threshold: Confidence threshold below which TPU is used
        """
        self.use_tpu = use_tpu and TPU_AVAILABLE
        self.tpu_threshold = tpu_threshold

        if self.use_tpu:
            logger.info("TPU-enhanced intent classification enabled")
        elif use_tpu and not TPU_AVAILABLE:
            logger.info("TPU requested but not available, using rule-based only")

        # COMMAND patterns
        self.command_patterns = [
            # File operations
            (r'\b(create|make|write|generate)\b.*\b(file|script|program|code)\b', 0.9),
            (r'\b(edit|modify|change|update)\b.*\b(file|code|function)\b', 0.9),
            (r'\b(delete|remove|erase)\b.*\b(file|directory)\b', 0.85),
            (r'\b(run|execute|start)\b.*\b(command|script|program)\b', 0.9),

            # Git operations
            (r'\b(commit|push|pull|checkout|branch)\b', 0.85),
            (r'\b(git)\b', 0.8),

            # Build/test operations
            (r'\b(build|compile|test|deploy)\b', 0.85),
            (r'\b(install|uninstall)\b.*\b(package|dependency)\b', 0.85),

            # System operations
            (r'\b(restart|stop|start)\b.*\b(service|daemon|server)\b', 0.85),
        ]

        # QUERY patterns
        self.query_patterns = [
            # Search/find operations
            (r'\b(search|find|look for|locate)\b', 0.85),
            (r'\b(what|where|which|who)\b.*\b(file|function|class|variable)\b', 0.85),
            (r'\b(show|display|list)\b.*\b(files|directories|functions)\b', 0.85),

            # Read operations
            (r'\b(read|view|see|check)\b.*\b(file|code|log)\b', 0.85),
            (r'\b(what (is|are))\b', 0.8),
            (r'\b(tell me about|explain)\b', 0.8),

            # Analysis operations
            (r'\b(analyze|review|inspect)\b', 0.85),
            (r'\b(how many|count)\b', 0.8),
        ]

        # CONVERSATION patterns
        self.conversation_patterns = [
            # Greetings
            (r'\b(hello|hi|hey|good morning|good afternoon|good evening)\b', 0.95),
            (r'\b(how are you|how\'s it going)\b', 0.95),

            # Questions about assistant
            (r'\b(can you|do you|are you)\b(?!.*\b(file|code|run|create)\b)', 0.85),
            (r'\b(what can you do|what are you|who are you)\b', 0.9),

            # Thank you / acknowledgment
            (r'\b(thank|thanks|appreciate)\b', 0.95),
            (r'\b(okay|ok|sure|fine|great|nice)\b', 0.7),

            # Help requests
            (r'\b(help|assist|support)\b', 0.85),
        ]

        # META patterns
        self.meta_patterns = [
            # System status
            (r'\b(status|health|state)\b', 0.9),
            (r'\b(what (are you|is the system))\b.*\b(doing|working on)\b', 0.85),

            # Configuration
            (r'\b(configure|config|settings|preferences)\b', 0.9),
            (r'\b(enable|disable|turn on|turn off)\b.*\b(feature|mode)\b', 0.85),

            # Context queries
            (r'\b(current|active)\b.*\b(context|directory|branch)\b', 0.85),
            (r'\b(what did you|recent)\b.*\b(do|action|change)\b', 0.85),
        ]

        # Command verbs for entity extraction
        self.command_verbs = {
            'create', 'make', 'write', 'generate', 'build',
            'edit', 'modify', 'change', 'update',
            'delete', 'remove', 'erase',
            'run', 'execute', 'start', 'stop',
            'commit', 'push', 'pull', 'checkout',
            'test', 'deploy', 'install'
        }

        # Query verbs
        self.query_verbs = {
            'search', 'find', 'look', 'locate',
            'show', 'display', 'list',
            'read', 'view', 'see', 'check',
            'tell', 'explain', 'describe',
            'analyze', 'review', 'inspect',
            'count'
        }

        logger.info("Intent classifier initialized")

    def classify(self, utterance: str) -> Intent:
        """
        Classify voice utterance into intent type

        Uses rule-based classification first, then TPU fallback for
        low-confidence cases when TPU is available.

        Args:
            utterance: User's voice command

        Returns:
            Intent with type, entities, and confidence
        """
        utterance_lower = utterance.lower().strip()

        # Try each intent type with pattern matching
        command_score = self._match_patterns(utterance_lower, self.command_patterns)
        query_score = self._match_patterns(utterance_lower, self.query_patterns)
        conversation_score = self._match_patterns(utterance_lower, self.conversation_patterns)
        meta_score = self._match_patterns(utterance_lower, self.meta_patterns)

        # Find highest scoring intent
        scores = [
            (IntentType.COMMAND, command_score),
            (IntentType.QUERY, query_score),
            (IntentType.CONVERSATION, conversation_score),
            (IntentType.META, meta_score)
        ]

        intent_type, confidence = max(scores, key=lambda x: x[1])

        # Use TPU for ambiguous cases (low confidence)
        if self.use_tpu and confidence < self.tpu_threshold:
            tpu_result = self._classify_with_tpu(utterance)
            if tpu_result and tpu_result[1] > confidence:
                intent_type, confidence = tpu_result
                logger.info(f"TPU improved classification: {intent_type.value} ({confidence:.2f})")

        # Default to conversation if confidence too low
        if confidence < 0.5:
            intent_type = IntentType.CONVERSATION
            confidence = 0.6

        # Extract entities
        entities = self._extract_entities(utterance, intent_type)

        # Determine if confirmation needed (destructive operations)
        requires_confirmation = self._requires_confirmation(utterance_lower, intent_type)

        logger.info(f"Classified: {intent_type.value} (confidence: {confidence:.2f})")

        return Intent(
            type=intent_type,
            text=utterance,
            entities=entities,
            confidence=confidence,
            requires_confirmation=requires_confirmation
        )

    def _classify_with_tpu(self, utterance: str) -> Optional[tuple]:
        """
        Use TPU's classify_intent for neural classification

        Args:
            utterance: User's voice command

        Returns:
            Tuple of (IntentType, confidence) or None if TPU fails
        """
        if not _tpu_classify_intent:
            return None

        try:
            # Map TPU intent categories to IntentType
            intent_map = {
                "command": IntentType.COMMAND,
                "action": IntentType.COMMAND,
                "query": IntentType.QUERY,
                "question": IntentType.QUERY,
                "conversation": IntentType.CONVERSATION,
                "chat": IntentType.CONVERSATION,
                "statement": IntentType.CONVERSATION,
                "meta": IntentType.META,
                "system": IntentType.META
            }

            # Call tpu_importance.classify_intent (synchronous function)
            # Returns dict with "intent", "confidence", "reasoning"
            result = _tpu_classify_intent(utterance)

            if result:
                intent_category = result.get("intent", "").lower()
                confidence = result.get("confidence", 0.0)

                # Map category to IntentType
                for key, intent_type in intent_map.items():
                    if key in intent_category:
                        return (intent_type, confidence)

            return None

        except Exception as e:
            logger.warning(f"TPU classification failed: {e}")
            return None

    def _match_patterns(
        self,
        text: str,
        patterns: List[tuple]
    ) -> float:
        """
        Match text against patterns and return max confidence

        Args:
            text: Text to match
            patterns: List of (pattern, confidence) tuples

        Returns:
            Maximum confidence from matching patterns
        """
        max_confidence = 0.0

        for pattern, confidence in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                max_confidence = max(max_confidence, confidence)

        return max_confidence

    def _extract_entities(
        self,
        utterance: str,
        intent_type: IntentType
    ) -> Dict[str, Any]:
        """
        Extract entities from utterance based on intent type

        Args:
            utterance: User utterance
            intent_type: Classified intent type

        Returns:
            Dictionary of extracted entities
        """
        entities = {}

        if intent_type == IntentType.COMMAND:
            entities.update(self._extract_command_entities(utterance))
        elif intent_type == IntentType.QUERY:
            entities.update(self._extract_query_entities(utterance))

        return entities

    def _extract_command_entities(self, utterance: str) -> Dict[str, Any]:
        """Extract entities for COMMAND intents"""
        entities = {}

        # Extract file names (common patterns)
        file_match = re.search(r'\b([a-z_][a-z0-9_]*\.(py|js|txt|md|json|yaml|sh))\b', utterance, re.IGNORECASE)
        if file_match:
            entities['file_name'] = file_match.group(1)

        # Extract file paths
        path_match = re.search(r'([/~]?[\w/.-]+/[\w.-]+)', utterance)
        if path_match:
            entities['file_path'] = path_match.group(1)

        # Extract function/class names
        func_match = re.search(r'\b(function|class|method)\s+([a-z_][a-z0-9_]*)\b', utterance, re.IGNORECASE)
        if func_match:
            entities['identifier'] = func_match.group(2)

        # Extract command verb
        for verb in self.command_verbs:
            if verb in utterance.lower():
                entities['action'] = verb
                break

        # Extract programming language
        languages = ['python', 'javascript', 'typescript', 'bash', 'shell', 'go', 'rust', 'java']
        for lang in languages:
            if lang in utterance.lower():
                entities['language'] = lang
                break

        return entities

    def _extract_query_entities(self, utterance: str) -> Dict[str, Any]:
        """Extract entities for QUERY intents"""
        entities = {}

        # Extract search terms (quoted strings)
        quoted_match = re.search(r'["\']([^"\']+)["\']', utterance)
        if quoted_match:
            entities['search_term'] = quoted_match.group(1)

        # Extract file types
        file_types = ['python', 'javascript', 'typescript', 'json', 'yaml', 'markdown', 'text']
        for ftype in file_types:
            if ftype in utterance.lower():
                entities['file_type'] = ftype
                break

        # Extract query verb
        for verb in self.query_verbs:
            if verb in utterance.lower():
                entities['action'] = verb
                break

        # Extract directory references
        dir_keywords = ['directory', 'folder', 'current', 'this']
        if any(kw in utterance.lower() for kw in dir_keywords):
            entities['scope'] = 'current_directory'

        return entities

    def _requires_confirmation(
        self,
        utterance: str,
        intent_type: IntentType
    ) -> bool:
        """
        Determine if intent requires user confirmation

        Args:
            utterance: User utterance (lowercase)
            intent_type: Classified intent type

        Returns:
            True if confirmation needed
        """
        # Only COMMAND intents may need confirmation
        if intent_type != IntentType.COMMAND:
            return False

        # Destructive operations
        destructive_patterns = [
            r'\b(delete|remove|erase|drop)\b',
            r'\b(overwrite|replace)\b',
            r'\b(force|--force|-f)\b',
            r'\b(rm|rmdir)\b'
        ]

        for pattern in destructive_patterns:
            if re.search(pattern, utterance):
                return True

        return False


def main():
    """Test intent classifier"""
    classifier = IntentClassifier()

    test_utterances = [
        # COMMAND intents
        "Create a Python file called test.py",
        "Edit the main function in app.py",
        "Run the test suite",
        "Commit these changes with message fix bug",
        "Delete the temporary files",

        # QUERY intents
        "What Python files are in this directory?",
        "Search for the function process_data",
        "Show me the contents of config.json",
        "How many test files do we have?",
        "Find all TODO comments",

        # CONVERSATION intents
        "Hello! How are you?",
        "Can you hear me?",
        "Thank you for your help",
        "What can you do?",
        "That's great!",

        # META intents
        "What is the system status?",
        "What are you currently working on?",
        "Show me recent actions",
        "What's the current directory?",
    ]

    print("=" * 60)
    print("INTENT CLASSIFIER TEST")
    print("=" * 60)

    for utterance in test_utterances:
        print(f"\nUtterance: {utterance}")
        intent = classifier.classify(utterance)
        print(f"  Type: {intent.type.value}")
        print(f"  Confidence: {intent.confidence:.2f}")
        print(f"  Entities: {intent.entities}")
        print(f"  Requires Confirmation: {intent.requires_confirmation}")


if __name__ == "__main__":
    main()

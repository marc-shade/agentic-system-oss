#!/usr/bin/env python3
"""
Intent Detector using local Ollama LLM
Provides sophisticated NLU for voice input processing
"""

import logging
import httpx
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger("voice-agi.intent")


@dataclass
class Intent:
    """Detected intent from user input"""
    name: str  # Intent name (e.g., 'create_goal', 'search_memory')
    confidence: float  # Confidence score (0.0-1.0)
    parameters: Dict[str, Any]  # Extracted parameters
    requires_memory: bool = False  # Whether memory retrieval is needed
    requires_confirmation: bool = False  # Whether action needs confirmation


class IntentDetector:
    """Intent detection using cloud Ollama LLM (never use local CPU for inference)"""
    # Cloud-first Ollama endpoint
    DEFAULT_OLLAMA_URL = os.getenv('OLLAMA_HOST', 'http://Marcs-Mac-Studio.local:11434')

    def __init__(
        self,
        ollama_url: str = None,
        model: str = "llama3.2"
    ):
        """
        Initialize intent detector

        Args:
            ollama_url: Ollama API URL (defaults to cluster AI node)
            model: LLM model to use for intent detection
        """
        self.ollama_url = ollama_url or self.DEFAULT_OLLAMA_URL
        self.model = model
        self.client = httpx.AsyncClient(timeout=30.0)

        logger.info(f"Intent detector initialized: {model} @ {ollama_url}")

    async def detect(
        self,
        user_input: str,
        context: Optional[str] = None,
        available_tools: Optional[List[Dict]] = None
    ) -> Intent:
        """
        Detect intent from user input

        Args:
            user_input: User's speech input
            context: Optional conversation context
            available_tools: Optional list of available tools

        Returns:
            Detected intent
        """
        try:
            # Build prompt for intent detection
            prompt = self._build_intent_prompt(user_input, context, available_tools)

            # Call Ollama
            response = await self._call_ollama(prompt)

            # Parse response
            intent = self._parse_intent_response(response, user_input)

            logger.info(f"Detected intent: {intent.name} (confidence: {intent.confidence:.2f})")

            return intent

        except Exception as e:
            logger.error(f"Error detecting intent: {e}")
            # Return default intent
            return Intent(
                name='unknown',
                confidence=0.0,
                parameters={'query': user_input}
            )

    def _build_intent_prompt(
        self,
        user_input: str,
        context: Optional[str],
        available_tools: Optional[List[Dict]]
    ) -> str:
        """Build prompt for intent detection"""
        prompt_parts = [
            "You are an intent classifier for a voice-controlled AGI system.",
            "Analyze the user's speech input and classify it into one of these categories:",
            "",
            "1. create_goal - User wants to create a new goal",
            "2. search_memory - User wants to search memories or recall information",
            "3. list_tasks - User wants to see pending tasks",
            "4. check_status - User wants to check system or task status",
            "5. trigger_consolidation - User wants to run memory consolidation",
            "6. start_research - User wants to start research on a topic",
            "7. general_query - General question or statement",
            "8. confirmation - User is confirming or denying something (yes/no)",
            "",
            f"User input: {user_input}"
        ]

        if context:
            prompt_parts.extend([
                "",
                f"Conversation context:\n{context}"
            ])

        if available_tools:
            tool_descriptions = "\n".join([
                f"- {tool['name']}: {tool['description']}"
                for tool in available_tools[:10]  # Limit to avoid token overflow
            ])
            prompt_parts.extend([
                "",
                f"Available tools:\n{tool_descriptions}"
            ])

        prompt_parts.extend([
            "",
            "Respond with JSON format:",
            "{",
            '  "intent": "intent_name",',
            '  "confidence": 0.95,',
            '  "parameters": {"key": "value"},',
            '  "requires_memory": false,',
            '  "requires_confirmation": false',
            "}",
            "",
            "JSON response:"
        ])

        return "\n".join(prompt_parts)

    async def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API for intent detection"""
        try:
            response = await self.client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.1,  # Low temperature for consistent classification
                    "options": {
                        "num_predict": 150  # Limit response length
                    }
                }
            )

            if response.status_code == 200:
                data = response.json()
                return data.get('response', '')
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return ""

        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return ""

    def _parse_intent_response(self, response: str, user_input: str) -> Intent:
        """Parse LLM response into Intent object"""
        try:
            # Try to extract JSON from response
            # LLM might include extra text, so find JSON block
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)

                return Intent(
                    name=data.get('intent', 'unknown'),
                    confidence=float(data.get('confidence', 0.5)),
                    parameters=data.get('parameters', {'query': user_input}),
                    requires_memory=data.get('requires_memory', False),
                    requires_confirmation=data.get('requires_confirmation', False)
                )

        except Exception as e:
            logger.error(f"Error parsing intent response: {e}")

        # Fallback: use simple heuristics
        return self._fallback_intent_detection(user_input)

    def _fallback_intent_detection(self, user_input: str) -> Intent:
        """Fallback intent detection using simple heuristics"""
        user_lower = user_input.lower()

        # Check for common patterns
        if any(word in user_lower for word in ['create', 'make', 'new', 'add']) and 'goal' in user_lower:
            return Intent(
                name='create_goal',
                confidence=0.7,
                parameters={'description': user_input}
            )

        if any(word in user_lower for word in ['search', 'find', 'remember', 'recall', 'what']):
            return Intent(
                name='search_memory',
                confidence=0.7,
                parameters={'query': user_input},
                requires_memory=True
            )

        if any(word in user_lower for word in ['task', 'todo', 'pending']):
            return Intent(
                name='list_tasks',
                confidence=0.7,
                parameters={}
            )

        if any(word in user_lower for word in ['status', 'how', "what's"]):
            return Intent(
                name='check_status',
                confidence=0.6,
                parameters={}
            )

        if any(word in user_lower for word in ['consolidate', 'consolidation']):
            return Intent(
                name='trigger_consolidation',
                confidence=0.8,
                parameters={}
            )

        if any(word in user_lower for word in ['research', 'investigate', 'study']):
            return Intent(
                name='start_research',
                confidence=0.7,
                parameters={'topic': user_input}
            )

        if user_lower in ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'correct', 'right']:
            return Intent(
                name='confirmation',
                confidence=0.9,
                parameters={'confirmed': True}
            )

        if user_lower in ['no', 'nope', 'nah', 'cancel', 'nevermind']:
            return Intent(
                name='confirmation',
                confidence=0.9,
                parameters={'confirmed': False}
            )

        # Default: general query
        return Intent(
            name='general_query',
            confidence=0.5,
            parameters={'query': user_input}
        )

    async def extract_parameters(
        self,
        user_input: str,
        parameter_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract specific parameters from user input

        Args:
            user_input: User's speech input
            parameter_schema: Schema of parameters to extract

        Returns:
            Extracted parameters
        """
        try:
            # Build prompt for parameter extraction
            schema_str = json.dumps(parameter_schema, indent=2)
            prompt = f"""Extract parameters from user input according to this schema:

{schema_str}

User input: {user_input}

Respond with JSON containing the extracted parameters.
JSON response:"""

            # Call Ollama
            response = await self._call_ollama(prompt)

            # Parse response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)

        except Exception as e:
            logger.error(f"Error extracting parameters: {e}")

        return {}

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

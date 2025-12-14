#!/usr/bin/env python3
"""
Natural Language Parameter Extraction
Uses Ollama to extract structured parameters from conversational input
"""

import logging
import json
import os
import re
import aiohttp
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger("voice-agi.params")


@dataclass
class ToolDefinition:
    """Tool definition for parameter extraction"""
    name: str
    description: str
    parameters: Dict[str, Any]


class ParameterExtractor:
    """
    Extract structured parameters from natural language using Ollama
    """
    # Cloud-first Ollama endpoint (never use local CPU for LLM inference)
    DEFAULT_OLLAMA_URL = os.getenv('OLLAMA_HOST', 'http://Marcs-Mac-Studio.local:11434')

    def __init__(self, ollama_url: str = None, model: str = "llama3.2"):
        self.ollama_url = ollama_url or self.DEFAULT_OLLAMA_URL
        self.model = model
        self.ollama_available = False
        logger.info(f"Parameter extractor initialized (model: {model})")

    async def check_availability(self) -> bool:
        """Check if Ollama is available"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_url}/api/tags", timeout=aiohttp.ClientTimeout(total=2)) as resp:
                    self.ollama_available = resp.status == 200
                    return self.ollama_available
        except Exception as e:
            logger.debug(f"Ollama not available: {e}")
            self.ollama_available = False
            return False

    async def extract_parameters(
        self,
        user_input: str,
        tool: ToolDefinition,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract parameters from natural language input for a specific tool

        Args:
            user_input: User's natural language input
            tool: Tool definition with parameter schema
            context: Optional conversation context

        Returns:
            Dictionary of extracted parameters
        """
        # Try Ollama extraction first
        if self.ollama_available or await self.check_availability():
            extracted = await self._extract_with_ollama(user_input, tool, context)
            if extracted:
                logger.info(f"Extracted params with Ollama: {extracted}")
                return extracted

        # Fallback to heuristic extraction
        logger.debug("Using fallback heuristic extraction")
        return self._extract_with_heuristics(user_input, tool, context)

    async def _extract_with_ollama(
        self,
        user_input: str,
        tool: ToolDefinition,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Use Ollama to extract parameters from natural language
        """
        # Build parameter schema description
        param_descriptions = []
        for param_name, param_info in tool.parameters.items():
            param_type = param_info.get('type', 'str')
            required = param_info.get('required', False)
            default = param_info.get('default', None)

            desc = f"- {param_name} ({param_type})"
            if required:
                desc += " [REQUIRED]"
            if default is not None:
                desc += f" [default: {default}]"
            param_descriptions.append(desc)

        params_text = "\n".join(param_descriptions)

        # Build extraction prompt
        prompt = f"""Extract parameters from the user's input for this tool.

Tool: {tool.name}
Description: {tool.description}

Parameters needed:
{params_text}

User input: "{user_input}"

Extract ONLY the parameter values mentioned in the user's input. Return JSON with parameter names as keys.
For example, if user says "Create a goal to optimize memory", extract: {{"description": "optimize memory"}}
If user says "Research transformer architectures", extract: {{"topic": "transformer architectures"}}
If user says "My name is Marc", extract: {{"name": "Marc"}}

Return ONLY valid JSON, nothing else. If no parameters found, return {{}}.
"""

        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.1,  # Low temperature for consistent extraction
                }

                async with session.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"Ollama returned status {resp.status}")
                        return None

                    result = await resp.json()
                    response_text = result.get('response', '').strip()

                    # Extract JSON from response
                    json_match = re.search(r'\{[^{}]*\}', response_text)
                    if json_match:
                        json_str = json_match.group(0)
                        extracted = json.loads(json_str)

                        # Validate extracted parameters
                        validated = self._validate_parameters(extracted, tool)
                        return validated

                    logger.debug(f"No JSON found in Ollama response: {response_text[:100]}")
                    return None

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Ollama JSON response: {e}")
            return None
        except Exception as e:
            logger.warning(f"Ollama extraction failed: {e}")
            return None

    def _extract_with_heuristics(
        self,
        user_input: str,
        tool: ToolDefinition,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Fallback heuristic parameter extraction using regex and patterns
        """
        extracted = {}
        user_lower = user_input.lower()

        # Common parameter extraction patterns
        for param_name, param_info in tool.parameters.items():
            param_type = param_info.get('type', 'str')

            # Pattern-based extraction
            if param_name == 'name':
                # Extract name patterns: "my name is X", "I'm X", "call me X"
                patterns = [
                    r"(?:my name is|i'm|i am|call me)\s+(\w+)",
                    r"(?:name|called)\s+(\w+)",
                ]
                for pattern in patterns:
                    match = re.search(pattern, user_lower)
                    if match:
                        extracted[param_name] = match.group(1).capitalize()
                        break

            elif param_name in ['description', 'goal', 'goal_description']:
                # Extract description after action verb
                patterns = [
                    r"(?:create|make|add|new)\s+(?:goal|task)?\s+(?:to|for)?\s+(.+)",
                    r"(?:goal|task):\s*(.+)",
                    r"(?:optimize|improve|fix|enhance)\s+(.+)",
                ]
                for pattern in patterns:
                    match = re.search(pattern, user_lower)
                    if match:
                        desc = match.group(1).strip()
                        # Remove trailing punctuation
                        desc = re.sub(r'[.!?]+$', '', desc)
                        extracted[param_name] = desc
                        break

            elif param_name in ['topic', 'query']:
                # Extract topic after action verb
                patterns = [
                    r"(?:research|study|learn about|investigate)\s+(.+)",
                    r"(?:search|find|look for)\s+(?:about|for)?\s*(.+)",
                ]
                for pattern in patterns:
                    match = re.search(pattern, user_lower)
                    if match:
                        topic = match.group(1).strip()
                        topic = re.sub(r'[.!?]+$', '', topic)
                        extracted[param_name] = topic
                        break

            elif param_name == 'target_metric':
                # Extract metric to optimize
                patterns = [
                    r"(?:optimize|improve|speed up|make faster)\s+(.+)",
                    r"(?:performance|speed|efficiency)\s+(?:of|for)?\s*(.+)?",
                ]
                for pattern in patterns:
                    match = re.search(pattern, user_lower)
                    if match:
                        metric = match.group(1).strip() if match.group(1) else "overall_performance"
                        extracted[param_name] = metric
                        break

            elif param_name == 'limit' and param_type == 'int':
                # Extract numeric limits
                match = re.search(r'(\d+)', user_input)
                if match:
                    extracted[param_name] = int(match.group(1))

        # Validate and apply defaults
        validated = self._validate_parameters(extracted, tool)
        return validated

    def _validate_parameters(
        self,
        extracted: Dict[str, Any],
        tool: ToolDefinition
    ) -> Dict[str, Any]:
        """
        Validate extracted parameters and apply defaults
        """
        validated = {}

        for param_name, param_info in tool.parameters.items():
            param_type = param_info.get('type', 'str')
            required = param_info.get('required', False)
            default = param_info.get('default', None)

            if param_name in extracted:
                # Type conversion
                value = extracted[param_name]
                try:
                    if param_type == 'int':
                        validated[param_name] = int(value)
                    elif param_type == 'float':
                        validated[param_name] = float(value)
                    elif param_type == 'bool':
                        validated[param_name] = str(value).lower() in ['true', '1', 'yes']
                    else:
                        validated[param_name] = str(value)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to convert {param_name}={value} to {param_type}: {e}")
                    if default is not None:
                        validated[param_name] = default

            elif not required and default is not None:
                # Apply default
                validated[param_name] = default

            elif required:
                logger.warning(f"Required parameter '{param_name}' not extracted from input")

        return validated


# Singleton instance
_extractor: Optional[ParameterExtractor] = None


def get_extractor() -> ParameterExtractor:
    """Get singleton parameter extractor"""
    global _extractor
    if _extractor is None:
        # Cloud-first Ollama (never use local CPU for LLM inference)
        ollama_url = os.getenv('OLLAMA_URL', os.getenv('OLLAMA_HOST', 'http://Marcs-Mac-Studio.local:11434'))
        model = os.getenv('OLLAMA_MODEL', 'llama3.2')
        _extractor = ParameterExtractor(ollama_url=ollama_url, model=model)
    return _extractor

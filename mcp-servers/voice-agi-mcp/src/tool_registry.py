#!/usr/bin/env python3
"""
Tool Registry for Voice-Callable Functions
Manages registration and invocation of tools during voice conversations
"""

import logging
import inspect
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
import re

logger = logging.getLogger("voice-agi.tools")

# Import parameter extractor
try:
    from parameter_extractor import ParameterExtractor, ToolDefinition as ExtractorToolDef
    _EXTRACTOR_AVAILABLE = True
except ImportError:
    _EXTRACTOR_AVAILABLE = False
    logger.warning("Parameter extractor not available, using fallback extraction")


@dataclass
class ToolDefinition:
    """Definition of a voice-callable tool"""
    name: str
    function: Callable
    description: str
    parameters: Dict[str, Any]
    intents: List[str]  # Intent keywords that trigger this tool
    priority: int = 5  # Higher priority tools matched first


class ToolRegistry:
    """Registry for voice-callable tools"""

    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self._intent_map: Dict[str, List[str]] = {}  # intent -> tool names
        self.param_extractor: Optional[ParameterExtractor] = None

        # Initialize parameter extractor if available
        if _EXTRACTOR_AVAILABLE:
            import os
            # Cloud-first Ollama (never use local CPU for LLM inference)
            ollama_url = os.getenv('OLLAMA_URL', os.getenv('OLLAMA_HOST', 'http://Marcs-Mac-Studio.local:11434'))
            model = os.getenv('OLLAMA_MODEL', 'llama3.2')
            self.param_extractor = ParameterExtractor(ollama_url=ollama_url, model=model)
            logger.info("Parameter extractor initialized")

        logger.info("Tool registry initialized")

    def register(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        intents: Optional[List[str]] = None,
        priority: int = 5
    ):
        """
        Decorator to register a voice-callable tool

        Args:
            name: Tool name (defaults to function name)
            description: Tool description (defaults to docstring)
            intents: Intent keywords that trigger this tool
            priority: Tool priority (higher = matched first)

        Example:
            @tool_registry.register(intents=["memory", "remember", "recall"])
            async def search_memory(query: str):
                '''Search AGI memory'''
                return results
        """
        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            tool_desc = description or (func.__doc__ or "No description")
            tool_intents = intents or []

            # Extract parameters from function signature
            sig = inspect.signature(func)
            parameters = {}
            for param_name, param in sig.parameters.items():
                if param_name in ('self', 'cls'):
                    continue
                parameters[param_name] = {
                    'type': param.annotation.__name__ if param.annotation != inspect.Parameter.empty else 'any',
                    'default': param.default if param.default != inspect.Parameter.empty else None,
                    'required': param.default == inspect.Parameter.empty
                }

            # Create tool definition
            tool_def = ToolDefinition(
                name=tool_name,
                function=func,
                description=tool_desc,
                parameters=parameters,
                intents=tool_intents,
                priority=priority
            )

            # Register tool
            self.tools[tool_name] = tool_def

            # Build intent map
            for intent in tool_intents:
                intent_lower = intent.lower()
                if intent_lower not in self._intent_map:
                    self._intent_map[intent_lower] = []
                self._intent_map[intent_lower].append(tool_name)

            logger.info(f"Registered tool: {tool_name} with intents {tool_intents}")

            return func

        return decorator

    def match_tool(self, user_input: str) -> Optional[ToolDefinition]:
        """
        Match user input to a tool based on intent keywords with enhanced scoring

        Args:
            user_input: User's speech input

        Returns:
            Matched tool definition or None
        """
        user_lower = user_input.lower()
        user_words = set(user_lower.split())

        # Score each tool based on intent matching
        tool_scores = []

        for tool_name, tool in self.tools.items():
            score = 0
            matched_intents = []
            best_match_type = None

            for intent in tool.intents:
                intent_lower = intent.lower()
                intent_words = set(intent_lower.split())

                # 1. Exact phrase match (highest score)
                if intent_lower == user_lower:
                    score += 1000  # Increased from 100
                    matched_intents.append(intent)
                    best_match_type = "exact"

                # 2. Full intent phrase in input (word boundary aware)
                elif re.search(rf'\b{re.escape(intent_lower)}\b', user_lower):
                    # Give higher score if it's at the start
                    if user_lower.startswith(intent_lower):
                        score += 200  # Increased from 50
                    else:
                        score += 100  # Increased from 30
                    matched_intents.append(intent)
                    if not best_match_type:
                        best_match_type = "phrase"

                # 3. Partial phrase match (multi-word intents)
                elif len(intent_words) > 1 and intent_lower in user_lower:
                    score += 60
                    matched_intents.append(intent)
                    if not best_match_type:
                        best_match_type = "partial"

                # 4. Word-level matching with enhanced scoring
                else:
                    common_words = user_words.intersection(intent_words)
                    if common_words:
                        # Score based on percentage of intent words matched
                        match_ratio = len(common_words) / len(intent_words)

                        # Bonus for matching longer intents (more specific)
                        length_bonus = len(intent_words) * 2

                        # Penalty for common words that cause false positives
                        common_stopwords = {'a', 'the', 'is', 'my', 'to', 'for', 'in', 'on'}
                        meaningful_matches = common_words - common_stopwords

                        if meaningful_matches:
                            word_score = int(match_ratio * 20) + length_bonus
                            score += word_score

                            if match_ratio > 0.5:  # More than half the words match
                                matched_intents.append(intent)
                                if not best_match_type:
                                    best_match_type = "word"

            # Apply priority multiplier (higher priority = more specific tools)
            if score > 0:
                priority_multiplier = 1 + (tool.priority / 10)
                final_score = score * priority_multiplier

                # Bonus for more specific match types
                if best_match_type == "exact":
                    final_score *= 1.5
                elif best_match_type == "phrase":
                    final_score *= 1.2

                tool_scores.append((tool, final_score, matched_intents, best_match_type))

        if not tool_scores:
            return None

        # Sort by score (highest first)
        tool_scores.sort(key=lambda x: x[1], reverse=True)

        # Log top matches for debugging
        logger.debug(f"Tool matching for '{user_input}':")
        for tool, score, intents, match_type in tool_scores[:3]:
            logger.debug(f"  {tool.name}: score={score:.1f}, type={match_type}, intents={intents}")

        # Check if top match is significantly better than second
        if len(tool_scores) > 1:
            top_score = tool_scores[0][1]
            second_score = tool_scores[1][1]
            if top_score < second_score * 1.2:
                logger.warning(f"Ambiguous match: {tool_scores[0][0].name} ({top_score:.1f}) vs {tool_scores[1][0].name} ({second_score:.1f})")

        return tool_scores[0][0]

    def should_invoke(self, user_input: str) -> bool:
        """Check if user input should trigger a tool"""
        return self.match_tool(user_input) is not None

    async def invoke(self, user_input: str, context: Optional[Dict] = None) -> Optional[Any]:
        """
        Invoke appropriate tool based on user input

        Args:
            user_input: User's speech input
            context: Optional conversation context

        Returns:
            Tool result or None
        """
        # Match tool
        tool = self.match_tool(user_input)
        if not tool:
            logger.debug(f"No tool matched for: {user_input}")
            return None

        logger.info(f"Invoking tool: {tool.name}")

        try:
            # Extract parameters from user input
            params = await self._extract_parameters(user_input, tool, context)

            # Invoke tool
            if inspect.iscoroutinefunction(tool.function):
                result = await tool.function(**params)
            else:
                result = tool.function(**params)

            logger.info(f"Tool {tool.name} executed successfully")
            return result

        except Exception as e:
            logger.error(f"Error invoking tool {tool.name}: {e}")
            return {
                'error': str(e),
                'tool': tool.name
            }

    async def _extract_parameters(
        self,
        user_input: str,
        tool: ToolDefinition,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Extract parameters from user input for tool invocation

        Args:
            user_input: User's speech input
            tool: Tool definition
            context: Optional conversation context

        Returns:
            Extracted parameters
        """
        # Use parameter extractor if available
        if self.param_extractor and _EXTRACTOR_AVAILABLE:
            # Convert ToolDefinition to ExtractorToolDef format
            extractor_tool = ExtractorToolDef(
                name=tool.name,
                description=tool.description,
                parameters=tool.parameters
            )

            params = await self.param_extractor.extract_parameters(
                user_input,
                extractor_tool,
                context
            )

            logger.debug(f"Extracted parameters: {params}")
            return params

        # Fallback to simple extraction
        params = {}

        # Simple extraction: for now, if tool has a 'query' param, use the entire input
        if 'query' in tool.parameters:
            # Remove intent keywords from query
            query = user_input
            for intent in tool.intents:
                query = re.sub(rf'\b{re.escape(intent)}\b', '', query, flags=re.IGNORECASE)
            params['query'] = query.strip()

        # For other parameters, try to extract from context or use defaults
        for param_name, param_info in tool.parameters.items():
            if param_name == 'query':
                continue  # Already handled

            # Check context
            if context and param_name in context:
                params[param_name] = context[param_name]
            # Use default if available
            elif param_info['default'] is not None:
                params[param_name] = param_info['default']
            # For required params without value, try to extract from input
            elif param_info['required']:
                # Simple extraction: look for patterns like "name is Marc"
                pattern = rf'{param_name}\s+(?:is|:)\s+(\w+)'
                match = re.search(pattern, user_input, re.IGNORECASE)
                if match:
                    params[param_name] = match.group(1)

        return params

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get tool by name"""
        return self.tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools"""
        return [
            {
                'name': tool.name,
                'description': tool.description,
                'intents': tool.intents,
                'parameters': tool.parameters,
                'priority': tool.priority
            }
            for tool in self.tools.values()
        ]

    def get_tool_count(self) -> int:
        """Get number of registered tools"""
        return len(self.tools)

    def clear(self):
        """Clear all registered tools"""
        self.tools.clear()
        self._intent_map.clear()
        logger.info("Tool registry cleared")

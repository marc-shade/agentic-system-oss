#!/usr/bin/env python3
"""Outlines MCP Server - Constrained generation with guaranteed schema compliance."""
import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from fastmcp import FastMCP

from generators import ConstrainedGenerator, PATTERNS, GRAMMARS, get_generator
from ollama_integration import get_ollama_client, OllamaClient
from schemas import (
    FunctionSignature, ClassDefinition, CodeBlock, CodeReview,
    ExtractedData, ContactInfo, StructuredDocument, DataValidation,
    AgentDecision, TaskDecomposition, AgentResponse, ExecutionPlan
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("outlines-mcp")

# Default model configuration
DEFAULT_MODEL = "mistral"


class GenerationConfig(BaseModel):
    """Configuration for generation."""
    model: str = Field(DEFAULT_MODEL, description="Model name (Ollama model)")
    temperature: float = Field(0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(2048, ge=1, le=32768)


@mcp.tool()
async def generate_constrained(
    prompt: str,
    schema: Dict[str, Any],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.3,
) -> Dict[str, Any]:
    """Generate output constrained to a JSON schema.

    Args:
        prompt: The generation prompt
        schema: JSON schema the output must conform to
        model: Ollama model name
        temperature: Sampling temperature

    Returns:
        Generated output conforming to schema
    """
    generator = get_generator(model)
    try:
        result = await generator.generate_json(
            prompt=prompt,
            schema=schema,
            temperature=temperature
        )
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Constrained generation failed: {e}")
        return {"success": False, "error": str(e)}


@mcp.tool()
async def generate_choice(
    prompt: str,
    choices: List[str],
    model: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    """Generate output constrained to specific choices.

    Args:
        prompt: The generation prompt
        choices: List of valid output choices
        model: Ollama model name

    Returns:
        One of the specified choices
    """
    if not choices:
        return {"success": False, "error": "Choices list cannot be empty"}

    generator = get_generator(model)
    try:
        result = await generator.generate_choice(prompt=prompt, choices=choices)
        return {"success": True, "result": result, "choices": choices}
    except Exception as e:
        logger.error(f"Choice generation failed: {e}")
        return {"success": False, "error": str(e)}


@mcp.tool()
async def generate_regex(
    prompt: str,
    pattern: str,
    model: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    """Generate output matching a regex pattern.

    Args:
        prompt: The generation prompt
        pattern: Regex pattern the output must match
        model: Ollama model name

    Returns:
        Output matching the regex pattern
    """
    generator = get_generator(model)
    try:
        result = await generator.generate_regex(prompt=prompt, pattern=pattern)
        return {"success": True, "result": result, "pattern": pattern}
    except Exception as e:
        logger.error(f"Regex generation failed: {e}")
        return {"success": False, "error": str(e)}


@mcp.tool()
async def generate_json(
    prompt: str,
    schema_name: Optional[str] = None,
    custom_schema: Optional[Dict[str, Any]] = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.3,
) -> Dict[str, Any]:
    """Generate guaranteed valid JSON with optional schema.

    Args:
        prompt: The generation prompt
        schema_name: Built-in schema name (agent_decision, task_decomposition, etc.)
        custom_schema: Custom JSON schema (used if schema_name not provided)
        model: Ollama model name
        temperature: Sampling temperature

    Returns:
        Valid JSON output
    """
    # Schema lookup
    builtin_schemas = {
        "function_signature": FunctionSignature,
        "class_definition": ClassDefinition,
        "code_block": CodeBlock,
        "code_review": CodeReview,
        "extracted_data": ExtractedData,
        "contact_info": ContactInfo,
        "structured_document": StructuredDocument,
        "data_validation": DataValidation,
        "agent_decision": AgentDecision,
        "task_decomposition": TaskDecomposition,
        "agent_response": AgentResponse,
        "execution_plan": ExecutionPlan,
    }

    schema = None
    if schema_name and schema_name in builtin_schemas:
        schema = builtin_schemas[schema_name].model_json_schema()
    elif custom_schema:
        schema = custom_schema

    generator = get_generator(model)
    try:
        if schema:
            result = await generator.generate_json(
                prompt=prompt,
                schema=schema,
                temperature=temperature
            )
        else:
            # Generate any valid JSON
            client = get_ollama_client()
            response = await client.generate(
                model=model,
                prompt=f"{prompt}\n\nRespond with valid JSON only.",
                format="json",
                temperature=temperature
            )
            result = json.loads(response)

        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"JSON generation failed: {e}")
        return {"success": False, "error": str(e)}


@mcp.tool()
async def generate_code(
    prompt: str,
    language: str = "python",
    model: str = DEFAULT_MODEL,
    include_imports: bool = True,
) -> Dict[str, Any]:
    """Generate syntactically valid code.

    Args:
        prompt: Description of code to generate
        language: Programming language (python, javascript, typescript, etc.)
        model: Ollama model name
        include_imports: Whether to include necessary imports

    Returns:
        Generated code
    """
    generator = get_generator(model)

    full_prompt = prompt
    if include_imports:
        full_prompt = f"{prompt}\n\nInclude all necessary imports at the top."

    try:
        result = await generator.generate_code(
            prompt=full_prompt,
            language=language
        )
        return {
            "success": True,
            "code": result,
            "language": language
        }
    except Exception as e:
        logger.error(f"Code generation failed: {e}")
        return {"success": False, "error": str(e)}


@mcp.tool()
async def generate_grammar(
    prompt: str,
    grammar: str,
    model: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    """Generate output conforming to a context-free grammar.

    Args:
        prompt: The generation prompt
        grammar: EBNF grammar specification
        model: Ollama model name

    Returns:
        Output conforming to grammar
    """
    generator = get_generator(model)
    try:
        result = await generator.generate_grammar(prompt=prompt, grammar=grammar)
        return {"success": True, "result": result, "grammar": grammar}
    except Exception as e:
        logger.error(f"Grammar generation failed: {e}")
        return {"success": False, "error": str(e)}


@mcp.tool()
async def list_available_patterns() -> Dict[str, Any]:
    """List available regex patterns for constrained generation.

    Returns:
        Dictionary of pattern names and their regex strings
    """
    return {
        "success": True,
        "patterns": PATTERNS,
        "description": "Use these pattern names or custom regex with generate_regex"
    }


@mcp.tool()
async def list_available_grammars() -> Dict[str, Any]:
    """List available grammars for grammar-based generation.

    Returns:
        Dictionary of grammar names and their EBNF definitions
    """
    return {
        "success": True,
        "grammars": GRAMMARS,
        "description": "Use these grammar names or custom EBNF with generate_grammar"
    }


@mcp.tool()
async def list_available_schemas() -> Dict[str, Any]:
    """List available built-in schemas for JSON generation.

    Returns:
        List of schema names and their descriptions
    """
    schemas = {
        "function_signature": "Function definition with parameters and return type",
        "class_definition": "Class with attributes and methods",
        "code_block": "Code with language, imports, and explanation",
        "code_review": "Code review with issues and suggestions",
        "extracted_data": "Entities, keywords, summary from text",
        "contact_info": "Name, email, phone, company info",
        "structured_document": "Document with title, sections, metadata",
        "data_validation": "Validation result with errors and warnings",
        "agent_decision": "Agent action decision with reasoning",
        "task_decomposition": "Break task into subtasks with dependencies",
        "agent_response": "Structured agent response with sources",
        "execution_plan": "Multi-step plan with success criteria",
    }
    return {"success": True, "schemas": schemas}


@mcp.tool()
async def check_ollama_status() -> Dict[str, Any]:
    """Check Ollama availability and list models.

    Returns:
        Ollama status and available models
    """
    client = get_ollama_client()
    available = await client.is_available()

    if not available:
        return {
            "success": False,
            "available": False,
            "error": "Ollama not running. Start with: ollama serve"
        }

    models = await client.list_models()
    return {
        "success": True,
        "available": True,
        "models": [{"name": m.name, "size_gb": round(m.size / 1e9, 2)} for m in models]
    }


@mcp.tool()
async def generate_with_pattern(
    prompt: str,
    pattern_name: str,
    model: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    """Generate output using a named pattern.

    Args:
        prompt: The generation prompt
        pattern_name: One of: email, phone, url, date_iso, time_24h, uuid, semantic_version, ip_address
        model: Ollama model name

    Returns:
        Output matching the named pattern
    """
    if pattern_name not in PATTERNS:
        return {
            "success": False,
            "error": f"Unknown pattern: {pattern_name}",
            "available_patterns": list(PATTERNS.keys())
        }

    pattern = PATTERNS[pattern_name]
    generator = get_generator(model)

    try:
        result = await generator.generate_regex(prompt=prompt, pattern=pattern)
        return {
            "success": True,
            "result": result,
            "pattern_name": pattern_name,
            "pattern": pattern
        }
    except Exception as e:
        logger.error(f"Pattern generation failed: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    mcp.run()

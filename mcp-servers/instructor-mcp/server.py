#!/usr/bin/env python3
"""
Instructor MCP Server
Structured output extraction with Pydantic validation for agentic systems.

Provides:
- Structured data extraction using Anthropic Claude
- Automatic validation and intelligent retry logic
- Complex nested schema support
- Streaming partial objects
- Integration with enhanced-memory-mcp
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

import anthropic
import instructor
from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio
from pydantic import BaseModel, ValidationError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from models import (
    MODEL_REGISTRY,
    ExtractionResult,
    ExtractedEntity,
    KnowledgeGraph,
    TaskExtraction,
    MeetingNotes,
    CodeAnalysis,
    MemoryEntry,
    get_model,
    list_available_models,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("instructor-mcp")

# Initialize server
server = Server("instructor-mcp")

# Anthropic client with instructor
client = instructor.from_anthropic(anthropic.Anthropic())

# Default model
DEFAULT_MODEL = "claude-sonnet-4-20250514"
MAX_RETRIES = 3


class ExtractionError(Exception):
    """Custom exception for extraction failures."""
    pass


def create_dynamic_model(schema: Dict[str, Any]) -> Type[BaseModel]:
    """
    Create a dynamic Pydantic model from a JSON schema.

    Args:
        schema: JSON schema dict with properties and types

    Returns:
        Dynamically created Pydantic model class
    """
    from pydantic import create_model

    field_definitions = {}
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    type_mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    for field_name, field_schema in properties.items():
        field_type = type_mapping.get(field_schema.get("type", "string"), str)
        default = ... if field_name in required else None
        field_definitions[field_name] = (Optional[field_type] if default is None else field_type, default)

    return create_model("DynamicModel", **field_definitions)


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((ValidationError, anthropic.APIError)),
)
async def extract_with_retry(
    content: str,
    model_class: Type[BaseModel],
    system_prompt: Optional[str] = None,
    model: str = DEFAULT_MODEL,
) -> BaseModel:
    """
    Extract structured data with automatic retry on validation failures.

    Args:
        content: Text content to extract from
        model_class: Pydantic model to extract into
        system_prompt: Optional custom system prompt
        model: Claude model to use

    Returns:
        Validated Pydantic model instance
    """
    default_system = f"""You are a precise data extraction assistant.
Extract structured information from the provided text according to the schema.
Be accurate and include only information explicitly stated or strongly implied.
If a field cannot be determined, use null/None for optional fields."""

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt or default_system,
        messages=[{"role": "user", "content": content}],
        response_model=model_class,
    )

    return response


async def extract_streaming(
    content: str,
    model_class: Type[BaseModel],
    system_prompt: Optional[str] = None,
    model: str = DEFAULT_MODEL,
) -> BaseModel:
    """
    Extract with streaming for partial object updates.
    Useful for large extractions where partial progress is valuable.
    """
    default_system = """You are a precise data extraction assistant.
Extract structured information progressively, filling fields as you analyze."""

    partial_results = []

    with client.messages.stream(
        model=model,
        max_tokens=4096,
        system=system_prompt or default_system,
        messages=[{"role": "user", "content": content}],
        response_model=model_class,
    ) as stream:
        for partial in stream:
            partial_results.append(partial)

    # Return final complete result
    return partial_results[-1] if partial_results else None


# Tool definitions

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available instructor tools."""
    return [
        Tool(
            name="extract_structured",
            description="Extract structured data from text using a predefined or custom schema. "
                       "Available models: entity, relation, knowledge_graph, task, action_item, "
                       "meeting_notes, code_analysis, memory_entry",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Text content to extract from"
                    },
                    "model_name": {
                        "type": "string",
                        "description": "Predefined model name (e.g., 'task', 'entity', 'knowledge_graph')"
                    },
                    "custom_schema": {
                        "type": "object",
                        "description": "Optional custom JSON schema if not using predefined model"
                    },
                    "system_prompt": {
                        "type": "string",
                        "description": "Optional custom system prompt for extraction"
                    },
                    "claude_model": {
                        "type": "string",
                        "description": "Claude model to use (default: claude-sonnet-4-20250514)"
                    }
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="extract_entities",
            description="Extract named entities and their relationships from text",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Text to extract entities from"
                    },
                    "entity_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Types of entities to extract (person, organization, concept, etc.)"
                    },
                    "include_relations": {
                        "type": "boolean",
                        "description": "Whether to extract relationships between entities"
                    }
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="extract_tasks",
            description="Extract actionable tasks from text (meeting notes, emails, documents)",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Text containing potential tasks"
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context about the project/meeting"
                    }
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="extract_for_memory",
            description="Extract information formatted for enhanced-memory-mcp storage",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Text to extract memory entries from"
                    },
                    "source": {
                        "type": "string",
                        "description": "Source of the information (url, document name, etc.)"
                    }
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="validate_schema",
            description="Validate data against a Pydantic schema without extraction",
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "description": "Data to validate"
                    },
                    "model_name": {
                        "type": "string",
                        "description": "Model name to validate against"
                    }
                },
                "required": ["data", "model_name"]
            }
        ),
        Tool(
            name="list_models",
            description="List all available predefined extraction models",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="analyze_code",
            description="Analyze code structure and extract insights",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Code to analyze"
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language (optional, will be detected)"
                    }
                },
                "required": ["code"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    start_time = time.time()
    retries = 0

    try:
        if name == "extract_structured":
            content = arguments["content"]
            model_name = arguments.get("model_name")
            custom_schema = arguments.get("custom_schema")
            system_prompt = arguments.get("system_prompt")
            claude_model = arguments.get("claude_model", DEFAULT_MODEL)

            # Determine model class
            if model_name:
                model_class = get_model(model_name)
                if not model_class:
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": f"Unknown model: {model_name}",
                            "available_models": list_available_models()
                        })
                    )]
            elif custom_schema:
                model_class = create_dynamic_model(custom_schema)
            else:
                # Default to entity extraction
                model_class = ExtractedEntity

            result = await extract_with_retry(
                content=content,
                model_class=model_class,
                system_prompt=system_prompt,
                model=claude_model,
            )

            extraction_time = (time.time() - start_time) * 1000

            return [TextContent(
                type="text",
                text=json.dumps(ExtractionResult(
                    success=True,
                    data=result.model_dump(),
                    model_used=claude_model,
                    extraction_time_ms=round(extraction_time, 2),
                    retries=retries,
                ).model_dump())
            )]

        elif name == "extract_entities":
            content = arguments["content"]
            include_relations = arguments.get("include_relations", True)

            if include_relations:
                result = await extract_with_retry(
                    content=content,
                    model_class=KnowledgeGraph,
                    system_prompt="Extract all entities and their relationships from the text. "
                                "Include confidence scores based on how clearly the entity is mentioned."
                )
            else:
                from typing import List as TList

                class EntityList(BaseModel):
                    entities: TList[ExtractedEntity]

                result = await extract_with_retry(
                    content=content,
                    model_class=EntityList,
                )

            extraction_time = (time.time() - start_time) * 1000

            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "data": result.model_dump(),
                    "extraction_time_ms": round(extraction_time, 2)
                })
            )]

        elif name == "extract_tasks":
            content = arguments["content"]
            context = arguments.get("context", "")

            from typing import List as TList

            class TaskList(BaseModel):
                tasks: TList[TaskExtraction]
                summary: str

            full_content = f"Context: {context}\n\nContent:\n{content}" if context else content

            result = await extract_with_retry(
                content=full_content,
                model_class=TaskList,
                system_prompt="Extract all actionable tasks from the content. "
                            "Identify owners, deadlines, priorities, and dependencies where mentioned."
            )

            extraction_time = (time.time() - start_time) * 1000

            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "data": result.model_dump(),
                    "task_count": len(result.tasks),
                    "extraction_time_ms": round(extraction_time, 2)
                })
            )]

        elif name == "extract_for_memory":
            content = arguments["content"]
            source = arguments.get("source", "unknown")

            from typing import List as TList

            class MemoryEntryList(BaseModel):
                entries: TList[MemoryEntry]

            result = await extract_with_retry(
                content=content,
                model_class=MemoryEntryList,
                system_prompt=f"""Extract information as memory entries for storage.
Source: {source}

Each entry should have:
- A clear, unique name (use entity_name format)
- An entity_type (person, concept, project, tool, fact, etc.)
- Multiple observations (facts learned about this entity)
- A confidence score based on how certain the information is

Focus on extracting knowledge that would be useful to remember long-term."""
            )

            # Format for enhanced-memory-mcp compatibility
            memory_format = []
            for entry in result.entries:
                memory_format.append({
                    "name": entry.name,
                    "entityType": entry.entity_type,
                    "observations": entry.observations,
                    "confidence": entry.confidence,
                    "source": source
                })

            extraction_time = (time.time() - start_time) * 1000

            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "entries": memory_format,
                    "entry_count": len(memory_format),
                    "extraction_time_ms": round(extraction_time, 2),
                    "ready_for_memory": True
                })
            )]

        elif name == "validate_schema":
            data = arguments["data"]
            model_name = arguments["model_name"]

            model_class = get_model(model_name)
            if not model_class:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "valid": False,
                        "error": f"Unknown model: {model_name}",
                        "available_models": list_available_models()
                    })
                )]

            try:
                validated = model_class(**data)
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "valid": True,
                        "data": validated.model_dump()
                    })
                )]
            except ValidationError as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "valid": False,
                        "errors": e.errors()
                    })
                )]

        elif name == "list_models":
            models_info = {}
            for model_name in list_available_models():
                model_class = get_model(model_name)
                if model_class:
                    models_info[model_name] = {
                        "fields": list(model_class.model_fields.keys()),
                        "description": model_class.__doc__ or "No description"
                    }

            return [TextContent(
                type="text",
                text=json.dumps({
                    "models": models_info,
                    "count": len(models_info)
                })
            )]

        elif name == "analyze_code":
            code = arguments["code"]
            language = arguments.get("language")

            prompt = f"Programming language: {language}\n\n" if language else ""
            prompt += f"Code:\n```\n{code}\n```"

            result = await extract_with_retry(
                content=prompt,
                model_class=CodeAnalysis,
                system_prompt="Analyze the provided code and extract structured insights. "
                            "Identify the language, purpose, complexity, key functions, "
                            "dependencies, potential issues, and improvement suggestions."
            )

            extraction_time = (time.time() - start_time) * 1000

            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "analysis": result.model_dump(),
                    "extraction_time_ms": round(extraction_time, 2)
                })
            )]

        else:
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Unknown tool: {name}"})
            )]

    except ValidationError as e:
        logger.error(f"Validation error in {name}: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": "Validation failed after retries",
                "validation_errors": e.errors()
            })
        )]
    except anthropic.APIError as e:
        logger.error(f"API error in {name}: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": f"API error: {str(e)}"
            })
        )]
    except Exception as e:
        logger.error(f"Error in {name}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e)
            })
        )]


async def main():
    """Run the MCP server."""
    logger.info("Starting Instructor MCP Server")
    logger.info(f"Available models: {list_available_models()}")

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())

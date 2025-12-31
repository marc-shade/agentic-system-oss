#!/usr/bin/env python3
"""
Visual Perception MCP Server

Provides visual perception capabilities via MCP protocol:
- Multi-provider image analysis (Claude, Gemini, Codex CLI)
- Screenshot capture and analysis
- Privacy-aware processing with face blur
- Confidence tracking across providers
- Visual memory integration

STATUS: Production Ready
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# MCP SDK
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Add paths
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-agents')
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/shared')

from visual_perception_agent import (
    VisualPerceptionAgent,
    VisualPerception,
    ImageSource,
    VisionProvider
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize server
server = Server("visual-perception-mcp")

# Global agent instance
_agent: Optional[VisualPerceptionAgent] = None


def get_agent() -> VisualPerceptionAgent:
    """Get or create the visual perception agent."""
    global _agent
    if _agent is None:
        _agent = VisualPerceptionAgent(
            providers=[VisionProvider.CLAUDE, VisionProvider.GEMINI, VisionProvider.CODEX],
            enable_privacy=True,
            enable_face_blur=True,
            min_confidence=0.6
        )
    return _agent


def perception_to_dict(perception: VisualPerception) -> Dict[str, Any]:
    """Convert VisualPerception to serializable dict."""
    return {
        "image_source": perception.image_source,
        "image_hash": perception.image_hash,
        "timestamp": perception.timestamp,
        "consensus": perception.consensus,
        "confidence": perception.confidence,
        "conflicts": perception.conflicts,
        "observations": [
            {
                "provider": obs.provider,
                "confidence": obs.confidence,
                "latency_ms": obs.latency_ms,
                "analysis": obs.analysis
            }
            for obs in perception.observations
        ],
        "metadata": perception.metadata
    }


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available visual perception tools."""
    return [
        Tool(
            name="perceive_image",
            description="Analyze an image using multiple vision providers (Claude, Gemini, Codex). Returns consensus analysis with confidence tracking.",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to the image file to analyze"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Analysis prompt (default: 'Describe what you see in detail.')",
                        "default": "Describe what you see in detail."
                    },
                    "use_all_providers": {
                        "type": "boolean",
                        "description": "Query all available providers for consensus (default: true)",
                        "default": True
                    },
                    "apply_privacy": {
                        "type": "boolean",
                        "description": "Apply privacy filters (face blur) before analysis (default: true)",
                        "default": True
                    }
                },
                "required": ["image_path"]
            }
        ),
        Tool(
            name="capture_screenshot",
            description="Capture a screenshot of the current display and optionally analyze it.",
            inputSchema={
                "type": "object",
                "properties": {
                    "analyze": {
                        "type": "boolean",
                        "description": "Whether to analyze the screenshot (default: true)",
                        "default": True
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Analysis prompt if analyzing",
                        "default": "Describe what you see on screen."
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Optional path to save the screenshot"
                    }
                }
            }
        ),
        Tool(
            name="analyze_url",
            description="Download and analyze an image from a URL using multiple vision providers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL of the image to analyze"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Analysis prompt",
                        "default": "Describe what you see in detail."
                    }
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="check_visual_providers",
            description="Check which vision providers (CLI tools) are available on this system.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="compare_images",
            description="Compare two images and identify differences using vision providers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "image1_path": {
                        "type": "string",
                        "description": "Path to first image"
                    },
                    "image2_path": {
                        "type": "string",
                        "description": "Path to second image"
                    },
                    "focus": {
                        "type": "string",
                        "description": "What to focus on when comparing (e.g., 'layout', 'text', 'colors')",
                        "default": "all differences"
                    }
                },
                "required": ["image1_path", "image2_path"]
            }
        ),
        Tool(
            name="extract_text_from_image",
            description="Extract text content from an image using OCR via vision providers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to the image containing text"
                    },
                    "language": {
                        "type": "string",
                        "description": "Expected language of the text (default: 'english')",
                        "default": "english"
                    }
                },
                "required": ["image_path"]
            }
        ),
        Tool(
            name="visual_qa",
            description="Ask a specific question about an image and get an answer from vision providers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to the image"
                    },
                    "question": {
                        "type": "string",
                        "description": "Question to ask about the image"
                    }
                },
                "required": ["image_path", "question"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    try:
        agent = get_agent()

        if name == "perceive_image":
            image_path = arguments["image_path"]
            prompt = arguments.get("prompt", "Describe what you see in detail.")
            use_all = arguments.get("use_all_providers", True)
            apply_privacy = arguments.get("apply_privacy", True)

            perception = await agent.perceive(
                image_source=image_path,
                source_type=ImageSource.FILE,
                prompt=prompt,
                use_all_providers=use_all,
                apply_privacy=apply_privacy
            )

            result = perception_to_dict(perception)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "capture_screenshot":
            analyze = arguments.get("analyze", True)
            prompt = arguments.get("prompt", "Describe what you see on screen.")
            output_path = arguments.get("output_path")

            if analyze:
                perception = await agent.capture_and_analyze(prompt)
                result = perception_to_dict(perception)
            else:
                from visual_perception_agent import ScreenshotCapture
                path = await ScreenshotCapture.capture(output_path)
                result = {"screenshot_path": path, "timestamp": datetime.now().isoformat()}

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "analyze_url":
            url = arguments["url"]
            prompt = arguments.get("prompt", "Describe what you see in detail.")

            perception = await agent.analyze_url(url, prompt)
            result = perception_to_dict(perception)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "check_visual_providers":
            available = agent.get_available_providers()
            result = {
                "available_providers": available,
                "total_configured": len(agent.providers),
                "providers_configured": [p.value for p in agent.providers],
                "status": "ready" if available else "no_providers_available"
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "compare_images":
            image1 = arguments["image1_path"]
            image2 = arguments["image2_path"]
            focus = arguments.get("focus", "all differences")

            prompt = f"""Compare these two images and identify {focus}.

Respond with:
- "similarities": List of things that are the same
- "differences": List of differences found
- "change_magnitude": How different are they (low/medium/high)
- "summary": Brief comparison summary
"""
            # Analyze both images
            p1 = await agent.analyze_file(image1, "Describe this image in detail for comparison.")
            p2 = await agent.analyze_file(image2, "Describe this image in detail for comparison.")

            # Use first provider to compare descriptions
            comparison_prompt = f"""Compare these two image descriptions and identify {focus}:

Image 1: {p1.consensus.get('description', '')}
Objects in Image 1: {p1.consensus.get('objects', [])}

Image 2: {p2.consensus.get('description', '')}
Objects in Image 2: {p2.consensus.get('objects', [])}

Provide comparison in JSON format with similarities, differences, change_magnitude, and summary.
"""
            # Use Claude for comparison reasoning
            from providers.cli_providers import query_cli_provider
            comparison = await query_cli_provider("claude", comparison_prompt)

            result = {
                "image1": {"path": image1, "description": p1.consensus.get('description', '')},
                "image2": {"path": image2, "description": p2.consensus.get('description', '')},
                "comparison": comparison.get("response", ""),
                "timestamp": datetime.now().isoformat()
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "extract_text_from_image":
            image_path = arguments["image_path"]
            language = arguments.get("language", "english")

            prompt = f"""Extract ALL text visible in this image. The text is in {language}.

Respond with:
- "text_blocks": List of text blocks found, in reading order
- "full_text": All text concatenated
- "text_type": Type of text (handwritten, printed, mixed)
- "confidence": How confident you are in the extraction (0-1)
"""
            perception = await agent.analyze_file(image_path, prompt)

            result = {
                "extracted_text": perception.consensus.get("text", []),
                "full_analysis": perception.consensus,
                "confidence": perception.confidence,
                "providers_used": [o.provider for o in perception.observations]
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "visual_qa":
            image_path = arguments["image_path"]
            question = arguments["question"]

            prompt = f"""Answer this question about the image: {question}

Provide a clear, direct answer. If you cannot determine the answer from the image, say so.
"""
            perception = await agent.analyze_file(image_path, prompt)

            result = {
                "question": question,
                "answer": perception.consensus.get("description", ""),
                "confidence": perception.confidence,
                "providers_agreed": len([o for o in perception.observations if o.confidence > 0.6])
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def main():
    """Run the MCP server."""
    logger.info("Starting Visual Perception MCP Server...")
    logger.info("Available tools: perceive_image, capture_screenshot, analyze_url, check_visual_providers, compare_images, extract_text_from_image, visual_qa")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())

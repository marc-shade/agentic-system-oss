"""
Latent Manipulation MCP Tools
=============================

MCP tool definitions for latent space manipulation.

These tools expose the mathematical hacking capabilities as MCP endpoints,
enabling Claude to:
- Capture style latents from generated images
- Apply cached styles to new generations
- Transfer styles between models
- Interpolate and blend styles
- Explore latent space similarities
"""

import logging
from typing import Any, Dict, List, Optional

import mcp.types as types

from .latent_hacker import DiffusionLatentHacker, image_from_base64
from .latent_guided_provider import LatentGuidedProvider, MultiProviderLatentRouter

logger = logging.getLogger("latent-tools")


def create_latent_tools(
    latent_hacker: DiffusionLatentHacker,
) -> List[types.Tool]:
    """
    Create MCP tool definitions for latent manipulation.

    Args:
        latent_hacker: DiffusionLatentHacker instance

    Returns:
        List of MCP Tool definitions
    """
    return [
        types.Tool(
            name="latent_capture_style",
            description="""Capture a style latent from an image for reuse.

Extracts the "style essence" from a generated image by recovering
the noise pattern used in diffusion. This latent can then be applied
to guide future generations toward the same style.

Mathematical basis: Recovers epsilon from diffusion equation
x_t = sqrt(alpha_t) * x_0 + sqrt(1 - alpha_t) * epsilon

Use cases:
- Create consistent visual styles across multiple images
- Build a library of reusable artistic styles
- Enable persona-consistent character generation""",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_base64": {
                        "type": "string",
                        "description": "Base64 encoded image to capture style from"
                    },
                    "name": {
                        "type": "string",
                        "description": "Unique name for this style (e.g., 'watercolor_japan', 'cyberpunk_neon')"
                    },
                    "model_id": {
                        "type": "string",
                        "description": "Model that generated the image (e.g., 'flux-dev', 'sdxl')"
                    },
                    "provider": {
                        "type": "string",
                        "description": "Provider name (e.g., 'huggingface', 'together')"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Original prompt used to generate the image"
                    },
                    "description": {
                        "type": "string",
                        "description": "Human-readable description of the style"
                    },
                    "timestep": {
                        "type": "integer",
                        "description": "Diffusion timestep for noise recovery (default: 50, higher = more noise influence)",
                        "default": 50
                    }
                },
                "required": ["image_base64", "name"]
            }
        ),
        types.Tool(
            name="latent_apply_style",
            description="""Apply a cached style latent to guide new image generation.

Uses the recovered noise pattern from a captured style to influence
new generations, producing images with similar visual characteristics
but different content.

This is "sidecar control" - guides generation without modifying model weights.

Returns:
- Guided prompt (optionally enhanced with style cues)
- Guided seed (derived from style latent)
- Additional parameters for generation""",
            inputSchema={
                "type": "object",
                "properties": {
                    "target_prompt": {
                        "type": "string",
                        "description": "Prompt for the new image to generate"
                    },
                    "style_name": {
                        "type": "string",
                        "description": "Name of cached style to apply"
                    },
                    "strength": {
                        "type": "number",
                        "description": "How strongly to apply style (0.0-1.0, default 0.7)",
                        "default": 0.7
                    },
                    "extract_style_cues": {
                        "type": "boolean",
                        "description": "Add style keywords from original prompt (default: true)",
                        "default": True
                    }
                },
                "required": ["target_prompt", "style_name"]
            }
        ),
        types.Tool(
            name="latent_cross_model_transfer",
            description="""Transfer style from one model to another.

Enables "capability arbitrage" - generate high-quality image with
expensive/slow model, then apply its style to fast/cheap model.

Example: Flux.1-dev quality -> SDXL-turbo speed

The style essence is preserved while gaining the target model's
speed/cost advantages.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_image_base64": {
                        "type": "string",
                        "description": "Base64 encoded source image"
                    },
                    "source_model": {
                        "type": "string",
                        "description": "Model that created source image"
                    },
                    "target_model": {
                        "type": "string",
                        "description": "Model to use for new generation"
                    },
                    "target_prompt": {
                        "type": "string",
                        "description": "Prompt for target generation"
                    },
                    "strength": {
                        "type": "number",
                        "description": "Transfer strength (0.0-1.0, default 0.8)",
                        "default": 0.8
                    }
                },
                "required": ["source_image_base64", "source_model", "target_model", "target_prompt"]
            }
        ),
        types.Tool(
            name="latent_interpolate_styles",
            description="""Blend two cached styles via latent interpolation.

Creates novel styles by navigating the constraint surface between
two known style points.

Example: Blend "watercolor" (alpha=0.3) with "cyberpunk" (alpha=0.7)
to get a futuristic watercolor aesthetic.

Mathematical basis: Linear interpolation in noise space
blended_noise = (1-alpha) * noise_a + alpha * noise_b""",
            inputSchema={
                "type": "object",
                "properties": {
                    "style_a": {
                        "type": "string",
                        "description": "First style name"
                    },
                    "style_b": {
                        "type": "string",
                        "description": "Second style name"
                    },
                    "alpha": {
                        "type": "number",
                        "description": "Blend factor (0.0 = all A, 1.0 = all B, 0.5 = equal blend)",
                        "default": 0.5
                    },
                    "target_prompt": {
                        "type": "string",
                        "description": "Prompt for generation with blended style"
                    }
                },
                "required": ["style_a", "style_b", "target_prompt"]
            }
        ),
        types.Tool(
            name="latent_list_styles",
            description="""List all cached style latents.

Returns metadata for each cached style including:
- Name and description
- Source model and provider
- Original generation parameters
- Creation timestamp
- Noise shape and timestep used""",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="latent_style_similarity",
            description="""Compute similarity between two cached styles.

Uses cosine similarity in noise space to measure how similar
two styles are. Useful for:
- Finding related styles
- Detecting duplicate captures
- Organizing style libraries

Returns similarity score from 0.0 (opposite) to 1.0 (identical).""",
            inputSchema={
                "type": "object",
                "properties": {
                    "style_a": {
                        "type": "string",
                        "description": "First style name"
                    },
                    "style_b": {
                        "type": "string",
                        "description": "Second style name"
                    }
                },
                "required": ["style_a", "style_b"]
            }
        ),
        types.Tool(
            name="latent_delete_style",
            description="""Delete a cached style latent.

Removes the style from both memory and disk cache.
Use to clean up unused or experimental styles.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of style to delete"
                    }
                },
                "required": ["name"]
            }
        ),
    ]


async def handle_latent_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    latent_hacker: DiffusionLatentHacker,
) -> Dict[str, Any]:
    """
    Handle latent manipulation tool calls.

    Args:
        tool_name: Name of the tool being called
        arguments: Tool arguments
        latent_hacker: DiffusionLatentHacker instance

    Returns:
        Tool result dictionary
    """
    try:
        if tool_name == "latent_capture_style":
            # Decode image
            image = image_from_base64(arguments["image_base64"])

            # Create style latent
            latent = latent_hacker.create_style_latent(
                image=image,
                name=arguments["name"],
                model_id=arguments.get("model_id", "unknown"),
                provider=arguments.get("provider", "unknown"),
                generation_params={
                    "prompt": arguments.get("prompt", ""),
                },
                timestep=arguments.get("timestep", 50),
                description=arguments.get("description"),
            )

            return {
                "success": True,
                "style_name": arguments["name"],
                "message": f"Style '{arguments['name']}' captured successfully",
                "details": latent.to_dict(),
            }

        elif tool_name == "latent_apply_style":
            result = latent_hacker.apply_style_latent(
                target_prompt=arguments["target_prompt"],
                style_name=arguments["style_name"],
                strength=arguments.get("strength", 0.7),
                extract_style_cues=arguments.get("extract_style_cues", True),
            )

            return {
                "success": True,
                "guided_prompt": result.guided_prompt,
                "guided_seed": result.guided_seed,
                "guidance_strength": result.guidance_strength,
                "source_style": result.source_style,
                "params": result.params,
                "message": f"Style '{arguments['style_name']}' applied with strength {result.guidance_strength}",
            }

        elif tool_name == "latent_cross_model_transfer":
            # Decode source image
            source_image = image_from_base64(arguments["source_image_base64"])

            result = latent_hacker.cross_model_transfer(
                source_image=source_image,
                source_model=arguments["source_model"],
                target_model=arguments["target_model"],
                target_prompt=arguments["target_prompt"],
                strength=arguments.get("strength", 0.8),
            )

            return {
                "success": True,
                "guided_prompt": result.guided_prompt,
                "guided_seed": result.guided_seed,
                "source_model": arguments["source_model"],
                "target_model": arguments["target_model"],
                "transfer_strength": result.guidance_strength,
                "params": result.params,
                "message": f"Style transferred from {arguments['source_model']} to {arguments['target_model']}",
            }

        elif tool_name == "latent_interpolate_styles":
            result = latent_hacker.interpolate_styles(
                style_a=arguments["style_a"],
                style_b=arguments["style_b"],
                alpha=arguments.get("alpha", 0.5),
                target_prompt=arguments["target_prompt"],
            )

            return {
                "success": True,
                "guided_prompt": result.guided_prompt,
                "guided_seed": result.guided_seed,
                "style_a": arguments["style_a"],
                "style_b": arguments["style_b"],
                "alpha": arguments.get("alpha", 0.5),
                "params": result.params,
                "message": f"Interpolated {arguments['style_a']} and {arguments['style_b']} at alpha={arguments.get('alpha', 0.5)}",
            }

        elif tool_name == "latent_list_styles":
            styles = latent_hacker.list_cached_styles()
            return {
                "success": True,
                "count": len(styles),
                "styles": styles,
                "message": f"Found {len(styles)} cached styles",
            }

        elif tool_name == "latent_style_similarity":
            similarity = latent_hacker.compute_style_similarity(
                style_a=arguments["style_a"],
                style_b=arguments["style_b"],
            )
            return {
                "success": True,
                "style_a": arguments["style_a"],
                "style_b": arguments["style_b"],
                "similarity": similarity,
                "interpretation": (
                    "nearly identical" if similarity > 0.9 else
                    "very similar" if similarity > 0.7 else
                    "somewhat similar" if similarity > 0.5 else
                    "different" if similarity > 0.3 else
                    "very different"
                ),
                "message": f"Similarity between '{arguments['style_a']}' and '{arguments['style_b']}': {similarity:.3f}",
            }

        elif tool_name == "latent_delete_style":
            deleted = latent_hacker.delete_style(arguments["name"])
            return {
                "success": deleted,
                "style_name": arguments["name"],
                "message": f"Style '{arguments['name']}' {'deleted' if deleted else 'not found'}",
            }

        else:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
            }

    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
        }
    except Exception as e:
        logger.exception(f"Error in latent tool {tool_name}")
        return {
            "success": False,
            "error": f"Internal error: {str(e)}",
        }


def is_latent_tool(tool_name: str) -> bool:
    """Check if a tool name is a latent manipulation tool."""
    return tool_name.startswith("latent_")

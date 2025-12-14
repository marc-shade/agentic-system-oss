#!/usr/bin/env python3
"""
Image Generation MCP Server
============================

Multi-provider image generation for AGI visual communication.

Provides tools for:
- Text-to-image generation with multiple providers
- Provider health monitoring and auto-fallback
- Specialized pixel art generation
- Image saving and management

Providers (in fallback order):
1. Pollinations.ai - FREE, no API key
2. Cloudflare Workers AI - 10K neurons/day free
3. Together AI - Very cheap ($0.003/image)
4. Hugging Face - Free tier
5. Replicate - 50/month free

MCP Tools:
- generate_image: Generate image from text prompt
- list_providers: List available providers and status
- list_models: List models for a provider
- get_provider_status: Check provider health
- generate_pixel_art: Specialized pixel art generation
- save_image: Save generated image to file
"""

import asyncio
import base64
import json
import logging
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import mcp.types as types

from .providers import (
    ImageProvider,
    GenerationResult,
    ImageFormat,
    detect_image_format,
    convert_to_png,
    PollinationsProvider,
    CloudflareProvider,
    HuggingFaceProvider,
    TogetherProvider,
    ReplicateProvider,
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("image-gen-mcp")

# Output directory for generated images
OUTPUT_DIR = Path(os.getenv("IMAGE_GEN_OUTPUT_DIR", "/mnt/agentic-system/generated-images"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Create MCP server
server = Server("image-gen-mcp")

# Initialize providers
PROVIDERS: Dict[str, ImageProvider] = {}


def init_providers():
    """Initialize all image providers."""
    global PROVIDERS
    PROVIDERS = {
        "pollinations": PollinationsProvider(),
        "cloudflare": CloudflareProvider(),
        "huggingface": HuggingFaceProvider(),
        "together": TogetherProvider(),
        "replicate": ReplicateProvider(),
    }
    logger.info(f"Initialized {len(PROVIDERS)} image providers")


# Initialize on module load
init_providers()


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available image generation tools."""
    return [
        types.Tool(
            name="generate_image",
            description="""Generate an image from a text prompt using AI.

Uses multiple providers with automatic fallback:
- Pollinations.ai (FREE, default)
- Cloudflare Workers AI
- Together AI
- Hugging Face
- Replicate

Returns base64-encoded image and metadata.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Text description of the image to generate"
                    },
                    "negative_prompt": {
                        "type": "string",
                        "description": "What to avoid in the image (not supported by all models)"
                    },
                    "width": {
                        "type": "integer",
                        "description": "Image width in pixels (default: 1024)",
                        "default": 1024
                    },
                    "height": {
                        "type": "integer",
                        "description": "Image height in pixels (default: 1024)",
                        "default": 1024
                    },
                    "provider": {
                        "type": "string",
                        "description": "Provider to use (pollinations, cloudflare, huggingface, together, replicate)",
                        "enum": ["pollinations", "cloudflare", "huggingface", "together", "replicate"]
                    },
                    "model": {
                        "type": "string",
                        "description": "Model to use (provider-specific)"
                    },
                    "seed": {
                        "type": "integer",
                        "description": "Random seed for reproducibility"
                    },
                    "save_to_file": {
                        "type": "boolean",
                        "description": "Save image to file (default: true)",
                        "default": True
                    }
                },
                "required": ["prompt"]
            }
        ),
        types.Tool(
            name="generate_pixel_art",
            description="""Generate pixel art style images.

Optimized for:
- Sprites and game assets
- Retro/NES-era style
- Clean pixel aesthetics

Uses pixel-art specialized models when available.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Description of the pixel art to generate"
                    },
                    "style": {
                        "type": "string",
                        "description": "Pixel art style",
                        "enum": ["nes", "snes", "gameboy", "modern", "isometric"],
                        "default": "nes"
                    },
                    "size": {
                        "type": "integer",
                        "description": "Canvas size (64, 128, 256, 512)",
                        "enum": [64, 128, 256, 512],
                        "default": 64
                    },
                    "colors": {
                        "type": "integer",
                        "description": "Color palette limit (4, 8, 16, 32, 256)",
                        "default": 16
                    },
                    "seed": {
                        "type": "integer",
                        "description": "Random seed"
                    }
                },
                "required": ["prompt"]
            }
        ),
        types.Tool(
            name="list_providers",
            description="List all available image generation providers with their status and capabilities.",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        ),
        types.Tool(
            name="list_models",
            description="List available models for a specific provider.",
            inputSchema={
                "type": "object",
                "properties": {
                    "provider": {
                        "type": "string",
                        "description": "Provider name",
                        "enum": ["pollinations", "cloudflare", "huggingface", "together", "replicate"]
                    }
                },
                "required": ["provider"]
            }
        ),
        types.Tool(
            name="get_provider_status",
            description="Get detailed status of a provider including health check.",
            inputSchema={
                "type": "object",
                "properties": {
                    "provider": {
                        "type": "string",
                        "description": "Provider name",
                        "enum": ["pollinations", "cloudflare", "huggingface", "together", "replicate"]
                    }
                },
                "required": ["provider"]
            }
        ),
        types.Tool(
            name="save_image",
            description="Save a base64-encoded image to a file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_base64": {
                        "type": "string",
                        "description": "Base64-encoded image data"
                    },
                    "filename": {
                        "type": "string",
                        "description": "Filename (without extension)"
                    },
                    "format": {
                        "type": "string",
                        "description": "Image format",
                        "enum": ["png", "jpg", "webp"],
                        "default": "png"
                    }
                },
                "required": ["image_base64", "filename"]
            }
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests."""

    if name == "generate_image":
        return await generate_image(arguments or {})
    elif name == "generate_pixel_art":
        return await generate_pixel_art(arguments or {})
    elif name == "list_providers":
        return await list_providers(arguments or {})
    elif name == "list_models":
        return await list_models(arguments or {})
    elif name == "get_provider_status":
        return await get_provider_status(arguments or {})
    elif name == "save_image":
        return await save_image(arguments or {})
    else:
        raise ValueError(f"Unknown tool: {name}")


async def generate_image(args: Dict) -> List[types.TextContent | types.ImageContent]:
    """Generate an image using the specified or best available provider."""
    prompt = args.get("prompt", "")
    negative_prompt = args.get("negative_prompt")
    width = args.get("width", 1024)
    height = args.get("height", 1024)
    provider_name = args.get("provider")
    model = args.get("model")
    seed = args.get("seed")
    save_to_file = args.get("save_to_file", True)

    if not prompt:
        return [types.TextContent(type="text", text=json.dumps({"success": False, "error": "Prompt required"}))]

    logger.info(f"Generating image: '{prompt[:50]}...' (provider={provider_name}, model={model})")

    # Provider priority for fallback
    provider_order = ["pollinations", "cloudflare", "together", "huggingface", "replicate"]

    if provider_name:
        provider_order = [provider_name] + [p for p in provider_order if p != provider_name]

    result = None
    tried_providers = []

    for pname in provider_order:
        provider = PROVIDERS.get(pname)
        if not provider:
            continue

        # Check if provider is configured
        if provider.status.value == "unconfigured":
            tried_providers.append(f"{pname}: unconfigured")
            continue

        logger.info(f"Trying provider: {pname}")
        tried_providers.append(pname)

        result = await provider.generate(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            seed=seed,
            model=model,
        )

        if result.success:
            logger.info(f"Generation successful with {pname} in {result.generation_time_ms}ms")
            break
        else:
            logger.warning(f"Provider {pname} failed: {result.error}")

    if not result or not result.success:
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": result.error if result else "All providers failed",
                "tried_providers": tried_providers,
            })
        )]

    # Save to file if requested (use detected format)
    file_path = None
    if save_to_file and result.image_base64:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_prompt = "".join(c if c.isalnum() or c in "- " else "_" for c in prompt[:30])
        filename = f"{timestamp}_{safe_prompt}_{result.provider}"
        # Use detected format extension (e.g., .jpg for JPEG)
        ext = result.image_format.extension.lstrip(".")
        file_path = await _save_image_to_file(result.image_base64, filename, ext)

    # Return both text metadata and image
    response = []

    # Add image content with correct MIME type
    if result.image_base64:
        response.append(types.ImageContent(
            type="image",
            data=result.image_base64,
            mimeType=result.mime_type,
        ))

    # Add metadata
    metadata = {
        "success": True,
        "provider": result.provider,
        "model": result.model,
        "prompt": prompt,
        "width": result.width,
        "height": result.height,
        "seed": result.seed,
        "generation_time_ms": result.generation_time_ms,
        "cost": result.cost,
        "file_path": str(file_path) if file_path else None,
        "image_url": result.image_url,
        "image_format": result.image_format.value,
        "mime_type": result.mime_type,
    }
    response.append(types.TextContent(type="text", text=json.dumps(metadata, indent=2)))

    return response


async def generate_pixel_art(args: Dict) -> List[types.TextContent | types.ImageContent]:
    """Generate pixel art with specialized prompting."""
    prompt = args.get("prompt", "")
    style = args.get("style", "nes")
    size = args.get("size", 64)
    colors = args.get("colors", 16)
    seed = args.get("seed")

    if not prompt:
        return [types.TextContent(type="text", text=json.dumps({"success": False, "error": "Prompt required"}))]

    # Style-specific prompt enhancements
    style_prompts = {
        "nes": f"8-bit NES pixel art sprite, {colors} color palette, clean pixels, retro game style, {prompt}",
        "snes": f"16-bit SNES pixel art, {colors} color palette, detailed sprites, retro gaming, {prompt}",
        "gameboy": f"Gameboy style pixel art, 4 shades of green, monochrome palette, classic handheld game, {prompt}",
        "modern": f"Modern pixel art, detailed high-resolution pixels, indie game style, {prompt}",
        "isometric": f"Isometric pixel art, 3D perspective, clean pixel edges, strategy game style, {prompt}",
    }

    enhanced_prompt = style_prompts.get(style, f"Pixel art style, {prompt}")

    logger.info(f"Generating pixel art: '{prompt[:50]}...' (style={style}, size={size})")

    # Try Hugging Face pixel-art model first, then fallback
    providers_to_try = [
        ("huggingface", "pixel-art"),  # Specialized pixel art model
        ("pollinations", "flux"),
        ("cloudflare", "sdxl"),
    ]

    result = None
    for pname, model in providers_to_try:
        provider = PROVIDERS.get(pname)
        if not provider or provider.status.value == "unconfigured":
            continue

        result = await provider.generate(
            prompt=enhanced_prompt,
            width=size,
            height=size,
            seed=seed,
            model=model,
        )

        if result.success:
            break

    if not result or not result.success:
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": result.error if result else "All providers failed",
            })
        )]

    # Save pixel art with correct format
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_prompt = "".join(c if c.isalnum() or c in "- " else "_" for c in prompt[:20])
    filename = f"pixelart_{timestamp}_{style}_{safe_prompt}"
    ext = result.image_format.extension.lstrip(".")
    file_path = await _save_image_to_file(result.image_base64, filename, ext)

    response = []

    if result.image_base64:
        response.append(types.ImageContent(
            type="image",
            data=result.image_base64,
            mimeType=result.mime_type,
        ))

    metadata = {
        "success": True,
        "type": "pixel_art",
        "style": style,
        "size": size,
        "colors": colors,
        "provider": result.provider,
        "model": result.model,
        "generation_time_ms": result.generation_time_ms,
        "file_path": str(file_path) if file_path else None,
        "image_format": result.image_format.value,
    }
    response.append(types.TextContent(type="text", text=json.dumps(metadata, indent=2)))

    return response


async def list_providers(args: Dict) -> List[types.TextContent]:
    """List all providers and their status."""
    providers_info = []

    for name, provider in PROVIDERS.items():
        info = {
            "name": name,
            "display_name": provider.display_name,
            "status": provider.status.value,
            "requires_api_key": provider.requires_api_key,
            "free_tier": provider.free_tier,
            "request_count": provider._request_count,
            "total_cost": provider._total_cost,
        }
        providers_info.append(info)

    return [types.TextContent(
        type="text",
        text=json.dumps({
            "providers": providers_info,
            "default": "pollinations",
            "fallback_order": ["pollinations", "cloudflare", "together", "huggingface", "replicate"],
        }, indent=2)
    )]


async def list_models(args: Dict) -> List[types.TextContent]:
    """List models for a provider."""
    provider_name = args.get("provider", "pollinations")
    provider = PROVIDERS.get(provider_name)

    if not provider:
        return [types.TextContent(
            type="text",
            text=json.dumps({"success": False, "error": f"Unknown provider: {provider_name}"})
        )]

    models = await provider.list_models()
    models_info = [
        {
            "id": m.id,
            "name": m.name,
            "description": m.description,
            "max_width": m.max_width,
            "max_height": m.max_height,
            "supports_negative_prompt": m.supports_negative_prompt,
            "cost_per_image": m.cost_per_image,
            "average_generation_time_ms": m.average_generation_time_ms,
        }
        for m in models
    ]

    return [types.TextContent(
        type="text",
        text=json.dumps({
            "provider": provider_name,
            "models": models_info,
        }, indent=2)
    )]


async def get_provider_status(args: Dict) -> List[types.TextContent]:
    """Get detailed provider status."""
    provider_name = args.get("provider", "pollinations")
    provider = PROVIDERS.get(provider_name)

    if not provider:
        return [types.TextContent(
            type="text",
            text=json.dumps({"success": False, "error": f"Unknown provider: {provider_name}"})
        )]

    health = await provider.check_health()

    return [types.TextContent(
        type="text",
        text=json.dumps(health, indent=2)
    )]


async def save_image(args: Dict) -> List[types.TextContent]:
    """Save a base64 image to file."""
    image_base64 = args.get("image_base64", "")
    filename = args.get("filename", f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    fmt = args.get("format", "png")

    if not image_base64:
        return [types.TextContent(
            type="text",
            text=json.dumps({"success": False, "error": "image_base64 required"})
        )]

    file_path = await _save_image_to_file(image_base64, filename, fmt)

    if file_path:
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "file_path": str(file_path),
                "size_bytes": file_path.stat().st_size,
            })
        )]
    else:
        return [types.TextContent(
            type="text",
            text=json.dumps({"success": False, "error": "Failed to save image"})
        )]


async def _save_image_to_file(image_base64: str, filename: str, fmt: str = "png") -> Optional[Path]:
    """Save base64 image to file with format auto-detection."""
    try:
        image_bytes = base64.b64decode(image_base64)

        # Detect actual format from bytes and override if different
        detected_format = detect_image_format(image_bytes)
        if detected_format != ImageFormat.UNKNOWN:
            actual_ext = detected_format.extension.lstrip(".")
            if actual_ext != fmt:
                logger.info(f"Format mismatch: requested {fmt}, detected {actual_ext}. Using detected.")
                fmt = actual_ext

        file_path = OUTPUT_DIR / f"{filename}.{fmt}"
        file_path.write_bytes(image_bytes)
        logger.info(f"Saved image to {file_path} ({len(image_bytes)} bytes)")
        return file_path
    except Exception as e:
        logger.error(f"Failed to save image: {e}")
        return None


async def main():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Image Generation MCP Server starting...")
        logger.info(f"Output directory: {OUTPUT_DIR}")

        # Log provider status
        for name, provider in PROVIDERS.items():
            logger.info(f"  {name}: {provider.status.value}")

        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="image-gen-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())

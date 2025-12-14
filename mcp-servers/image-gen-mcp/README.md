# Image Generation MCP Server

Multi-provider image generation for AGI visual communication.

## Features

- **Multi-Provider Support**: Automatic fallback across 5 providers
- **FREE Default**: Pollinations.ai requires no API key
- **Pixel Art Mode**: Specialized generation for sprites and game assets
- **Auto-Save**: Generated images automatically saved to disk
- **Cost Tracking**: Monitor usage and costs per provider

## Providers

| Provider | Cost | API Key | Best For |
|----------|------|---------|----------|
| **Pollinations.ai** | FREE | None | Default, general use |
| **Cloudflare Workers AI** | 10K neurons/day FREE | Required | Fast, production |
| **Together AI** | ~$0.003/image | Required | Bulk generation |
| **Hugging Face** | Free tier | Required | Model variety |
| **Replicate** | 50/mo free | Required | High quality |

## Installation

```bash
cd /mnt/agentic-system/mcp-servers/image-gen-mcp
pip install -e .
```

## Configuration

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "image-gen": {
      "command": "python",
      "args": ["-m", "image_gen_mcp.server"],
      "env": {
        "CLOUDFLARE_API_TOKEN": "your-token",
        "CLOUDFLARE_ACCOUNT_ID": "your-account-id",
        "HUGGINGFACE_API_TOKEN": "your-hf-token",
        "TOGETHER_API_KEY": "your-together-key",
        "REPLICATE_API_TOKEN": "your-replicate-token",
        "IMAGE_GEN_OUTPUT_DIR": "/mnt/agentic-system/generated-images"
      }
    }
  }
}
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `IMAGE_GEN_OUTPUT_DIR` | No | Where to save images (default: `/mnt/agentic-system/generated-images`) |
| `CLOUDFLARE_API_TOKEN` | For CF | Cloudflare API token |
| `CLOUDFLARE_ACCOUNT_ID` | For CF | Cloudflare account ID |
| `HUGGINGFACE_API_TOKEN` | For HF | Hugging Face token |
| `TOGETHER_API_KEY` | For Together | Together AI key |
| `REPLICATE_API_TOKEN` | For Replicate | Replicate token |

## MCP Tools

### `generate_image`

Generate an image from a text prompt.

```json
{
  "prompt": "A corgi wearing a space helmet, pixel art style",
  "width": 1024,
  "height": 1024,
  "provider": "pollinations",
  "model": "flux",
  "seed": 42,
  "save_to_file": true
}
```

### `generate_pixel_art`

Specialized pixel art generation.

```json
{
  "prompt": "cute corgi sprite, side view",
  "style": "nes",
  "size": 64,
  "colors": 16
}
```

Styles: `nes`, `snes`, `gameboy`, `modern`, `isometric`

### `list_providers`

List all providers with status.

### `list_models`

List models for a provider.

```json
{
  "provider": "huggingface"
}
```

### `get_provider_status`

Health check for a provider.

### `save_image`

Save base64 image to file.

## Models by Provider

### Pollinations.ai
- `flux` (default) - High quality
- `flux-realism` - Photorealistic
- `flux-anime` - Anime style
- `flux-3d` - 3D renders
- `turbo` - Fast generation

### Cloudflare Workers AI
- `sdxl` - Stable Diffusion XL
- `sdxl-lightning` - Fast 4-step SDXL
- `flux-schnell` - Fast Flux
- `dreamshaper` - Photorealistic

### Hugging Face
- `sdxl` - Stable Diffusion XL
- `sdxl-turbo` - Fast SDXL
- `flux-dev` - Flux development
- `flux-schnell` - Fast Flux
- `playground-v2.5` - Aesthetic
- `realvisxl` - Photorealistic
- `pixel-art` - Pixel art specialized

### Together AI
- `flux-schnell` - FREE tier available
- `flux-dev` - Higher quality
- `flux-pro` - Best quality
- `sd3` - Stable Diffusion 3

### Replicate
- `flux-schnell` - Fast Flux
- `flux-dev` - Higher quality
- `flux-pro` - Best quality
- `sdxl` - Stable Diffusion XL
- `playground-v2.5` - Aesthetic

## Usage Examples

### Basic Image Generation
```
Generate an image of a mountain landscape at sunset
```

### Pixel Art for Sprites
```
Generate pixel art of a corgi walking animation, NES style, 64x64
```

### With Specific Provider
```
Generate a photorealistic portrait using Cloudflare's SDXL model
```

## Output

Images are saved to `IMAGE_GEN_OUTPUT_DIR` with format:
```
{timestamp}_{prompt_snippet}_{provider}.png
```

Example: `20241128_143022_mountain_landscape_pollinations.png`

## Error Handling

The server automatically falls back through providers if one fails:

1. Try requested provider (or Pollinations)
2. If failed, try Cloudflare
3. If failed, try Together AI
4. If failed, try Hugging Face
5. If failed, try Replicate
6. Return error with all attempted providers

## Future Enhancements

- [ ] Local GPU support (Flux/ComfyUI) when 12GB GPU available
- [ ] Image-to-image generation
- [ ] Inpainting and outpainting
- [ ] Upscaling
- [ ] Style transfer
- [ ] Animation generation

## License

MIT

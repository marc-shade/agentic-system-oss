#!/usr/bin/env python3
"""
Exo Distributed Inference MCP Server

Provides unified access to Exo distributed LLM inference cluster from any node.
Tested with Exo 1.0 on macOS (December 2025).

Requirements:
- Exo installed (/Applications/EXO.app or via pip)
- Python 3.12+
"""

import asyncio
import json
import os
from typing import Any, AsyncIterator

import httpx
from mcp.server import Server
from mcp.types import Tool, TextContent

# Configuration
EXO_API_URL = os.getenv("EXO_API_URL", "http://localhost:8000")
EXO_TIMEOUT = int(os.getenv("EXO_TIMEOUT", "300"))  # 5 minutes for large models


class ExoClusterClient:
    """Client for interacting with Exo distributed inference cluster."""

    def __init__(self, base_url: str = EXO_API_URL):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=EXO_TIMEOUT)

    async def get_state(self) -> dict:
        """Get full cluster state including topology, instances, runners."""
        # Try multiple possible endpoints
        endpoints = ["/state", "/api/state", "/v1/state"]

        for endpoint in endpoints:
            try:
                response = await self.client.get(f"{self.base_url}{endpoint}")
                if response.status_code == 200:
                    return response.json()
            except Exception:
                continue

        # Fallback: construct basic state from available endpoints
        return {"error": "state_endpoint_not_available", "fallback": True}

    async def get_cluster_status(self) -> dict:
        """Get cluster status with node and instance counts."""
        try:
            # First try to get state from dedicated endpoint
            state = await self.get_state()

            # If state endpoint not available, use fallback
            if state.get("fallback"):
                return await self._get_fallback_status()

            if "error" in state and not state.get("fallback"):
                return state

            topology = state.get("topology", {})
            nodes = topology.get("nodes", [])
            instances = state.get("instances", {})
            runners = state.get("runners", {})

            # Extract node info
            node_info = []
            total_memory = 0
            for node in nodes:
                profile = node.get("nodeProfile", {})
                memory = profile.get("memory", {})
                ram_total = memory.get("ramTotal", {}).get("inBytes", 0)
                ram_available = memory.get("ramAvailable", {}).get("inBytes", 0)
                total_memory += ram_available

                node_info.append({
                    "id": node.get("nodeId", "unknown")[:20] + "...",
                    "chip": profile.get("chipId", "unknown"),
                    "ram_total_gb": round(ram_total / (1024**3), 1),
                    "ram_available_gb": round(ram_available / (1024**3), 1),
                })

            # Extract instance info
            instance_info = []
            for inst_id, inst_data in instances.items():
                inst_type = list(inst_data.keys())[0] if inst_data else "unknown"
                inst = list(inst_data.values())[0] if inst_data else {}
                model_id = inst.get("shardAssignments", {}).get("modelId", "unknown")
                instance_info.append({
                    "id": inst_id[:8] + "...",
                    "type": inst_type,
                    "model": model_id.split("/")[-1] if "/" in model_id else model_id,
                })

            # Extract runner status
            runner_status = {}
            for runner_id, runner_data in runners.items():
                status = list(runner_data.keys())[0] if runner_data else "unknown"
                runner_status[runner_id[:8] + "..."] = status

            return {
                "status": "operational" if nodes else "no_nodes",
                "nodes": len(nodes),
                "instances": len(instances),
                "runners": len(runners),
                "total_available_memory_gb": round(total_memory / (1024**3), 1),
                "node_details": node_info,
                "instance_details": instance_info,
                "runner_status": runner_status,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _get_fallback_status(self) -> dict:
        """Fallback status using available OpenAI-compatible endpoints."""
        try:
            # Check if server is responsive by getting models
            models = await self.list_models()
            if models and isinstance(models[0], dict) and "error" in models[0]:
                return {"status": "error", "error": models[0]["error"]}

            # Try health check endpoint
            health_ok = False
            try:
                response = await self.client.get(f"{self.base_url}/health")
                health_ok = response.status_code == 200
            except Exception:
                # Server responding to /v1/models means it's healthy
                health_ok = len(models) > 0

            return {
                "status": "operational" if health_ok else "degraded",
                "api_type": "openai_compatible",
                "nodes": 1,  # At least local node
                "instances": 0,  # Cannot determine without /state
                "runners": 0,
                "total_available_memory_gb": 0,
                "node_details": [{"id": "local", "chip": "unknown", "ram_total_gb": 0, "ram_available_gb": 0}],
                "instance_details": [],
                "runner_status": {},
                "available_models": len(models),
                "note": "Using fallback status (full state endpoint not available)"
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def list_models(self) -> list[dict]:
        """List available models on the cluster."""
        try:
            response = await self.client.get(f"{self.base_url}/v1/models")
            response.raise_for_status()
            data = response.json().get("data", [])
            return [
                {
                    "id": m.get("id", "unknown"),
                    "name": m.get("name", m.get("id", "unknown")),
                    "huggingface_id": m.get("hugging_face_id", ""),
                }
                for m in data
            ]
        except Exception as e:
            return [{"error": str(e)}]

    async def get_placement(self, model_id: str) -> dict:
        """Get placement preview for a model."""
        try:
            response = await self.client.get(
                f"{self.base_url}/instance/placement",
                params={"model_id": model_id}
            )
            if response.status_code == 400:
                return {"error": response.json().get("detail", "Placement failed")}
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def create_instance(self, model_id: str) -> dict:
        """Create an instance for a model (required before inference)."""
        try:
            # First get placement
            placement = await self.get_placement(model_id)
            if "error" in placement:
                return placement

            # Create instance from placement
            response = await self.client.post(
                f"{self.base_url}/instance",
                json={"instance": placement}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def delete_instance(self, instance_id: str) -> dict:
        """Delete an instance."""
        try:
            response = await self.client.delete(f"{self.base_url}/instance/{instance_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def wait_for_runner(self, timeout: int = 60) -> bool:
        """Wait for at least one runner to be ready."""
        for _ in range(timeout):
            state = await self.get_state()
            runners = state.get("runners", {})
            for runner_data in runners.values():
                if "RunnerReady" in runner_data:
                    return True
            await asyncio.sleep(1)
        return False

    async def chat_completion(
        self,
        messages: list[dict],
        model: str = "llama-3.2-1b",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False
    ) -> dict | AsyncIterator[dict]:
        """Run chat completion on the distributed Exo cluster."""
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }

        if stream:
            return self._stream_chat_completion(payload)

        response = await self.client.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload
        )
        response.raise_for_status()
        return response.json()

    async def _stream_chat_completion(self, payload: dict) -> AsyncIterator[dict]:
        """Stream chat completion responses."""
        async with self.client.stream(
            "POST",
            f"{self.base_url}/v1/chat/completions",
            json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        continue

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Initialize MCP server
server = Server("exo-inference-mcp")
client = ExoClusterClient()


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available Exo inference tools."""
    return [
        Tool(
            name="exo_chat",
            description="Run chat completion on distributed Exo cluster. No explicit loading required - just specify the model.",
            inputSchema={
                "type": "object",
                "properties": {
                    "messages": {
                        "type": "array",
                        "description": "List of chat messages with role and content",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string", "enum": ["system", "user", "assistant"]},
                                "content": {"type": "string"}
                            },
                            "required": ["role", "content"]
                        }
                    },
                    "model": {
                        "type": "string",
                        "description": "Model short name (e.g., llama-3.2-1b, llama-3.1-8b)",
                        "default": "llama-3.2-1b"
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Sampling temperature (0.0 - 2.0)",
                        "default": 0.7
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens to generate",
                        "default": 4096
                    }
                },
                "required": ["messages"]
            }
        ),
        Tool(
            name="exo_load_model",
            description="Load a model into the Exo cluster (legacy API). Note: OpenAI-compatible mode doesn't require explicit loading - just use exo_chat directly.",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "Model short name (e.g., llama-3.2-1b, llama-3.1-8b, llama-3.3-70b)"
                    }
                },
                "required": ["model"]
            }
        ),
        Tool(
            name="exo_unload_model",
            description="Unload a model instance to free memory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "instance_id": {
                        "type": "string",
                        "description": "Instance ID to unload (from exo_status)"
                    }
                },
                "required": ["instance_id"]
            }
        ),
        Tool(
            name="exo_status",
            description="Get Exo cluster status: nodes, instances, runners, memory.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="exo_models",
            description="List all models available on the Exo cluster.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""

    if name == "exo_chat":
        messages = arguments.get("messages", [])
        model = arguments.get("model", "llama-3.2-1b")
        temperature = arguments.get("temperature", 0.7)
        max_tokens = arguments.get("max_tokens", 4096)

        try:
            result = await client.chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )

            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content", "")
                model_used = result.get("model", model)
                return [TextContent(
                    type="text",
                    text=f"**Model**: {model_used}\n\n{content}"
                )]
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                detail = e.response.json().get("detail", "")
                if "No instance found" in detail:
                    return [TextContent(
                        type="text",
                        text=f"**Error**: Model not loaded. Use `exo_load_model` first.\n\nDetails: {detail}"
                    )]
            return [TextContent(type="text", text=f"**Error**: {str(e)}")]
        except httpx.ConnectError:
            return [TextContent(
                type="text",
                text="**Error**: Cannot connect to Exo. Start with:\n`/Applications/EXO.app/Contents/Resources/exo/exo --verbose`"
            )]
        except Exception as e:
            return [TextContent(type="text", text=f"**Error**: {str(e)}")]

    elif name == "exo_load_model":
        model = arguments.get("model", "llama-3.2-1b")

        try:
            # Create instance
            result = await client.create_instance(model)
            if "error" in result:
                return [TextContent(type="text", text=f"**Error**: {result['error']}")]

            command_id = result.get("command_id", "unknown")
            model_meta = result.get("model_meta", {})
            model_name = model_meta.get("prettyName", model)
            size_bytes = model_meta.get("storageSize", {}).get("inBytes", 0)
            size_gb = round(size_bytes / (1024**3), 2)

            output = f"""## Loading Model: {model_name}

**Size**: {size_gb} GB
**Command ID**: {command_id}

Waiting for model to be ready..."""

            # Wait for runner to be ready
            ready = await client.wait_for_runner(timeout=120)
            if ready:
                output += "\n\n**Status**: Ready for inference"
            else:
                output += "\n\n**Status**: Still loading (may take longer for large models)"

            return [TextContent(type="text", text=output)]

        except Exception as e:
            return [TextContent(type="text", text=f"**Error**: {str(e)}")]

    elif name == "exo_unload_model":
        instance_id = arguments.get("instance_id", "")
        if not instance_id:
            return [TextContent(type="text", text="**Error**: instance_id required")]

        try:
            result = await client.delete_instance(instance_id)
            if "error" in result:
                return [TextContent(type="text", text=f"**Error**: {result['error']}")]
            return [TextContent(type="text", text=f"Instance {instance_id} unloaded successfully")]
        except Exception as e:
            return [TextContent(type="text", text=f"**Error**: {str(e)}")]

    elif name == "exo_status":
        status = await client.get_cluster_status()

        if "error" in status and status.get("status") == "error":
            return [TextContent(
                type="text",
                text=f"**Error**: {status['error']}\n\nEnsure Exo is running."
            )]

        # Check if using fallback status
        is_fallback = status.get("api_type") == "openai_compatible"

        output = f"""## Exo Cluster Status

**Status**: {status.get('status', 'unknown')}
"""
        if is_fallback:
            output += f"""**API Type**: OpenAI-compatible
**Available Models**: {status.get('available_models', 0)}

*Note: {status.get('note', 'Full cluster state not available')}*

To load a model, use:
```
exo_load_model(model="llama-3.2-1b")
```

To list all available models:
```
exo_models()
```
"""
        else:
            output += f"""**Nodes**: {status.get('nodes', 0)}
**Instances**: {status.get('instances', 0)}
**Runners**: {status.get('runners', 0)}
**Available Memory**: {status.get('total_available_memory_gb', 0)} GB

### Nodes
"""
            for node in status.get("node_details", []):
                output += f"- `{node['id']}` - {node['ram_available_gb']}/{node['ram_total_gb']} GB available\n"

            output += "\n### Loaded Models\n"
            instances = status.get("instance_details", [])
            if instances:
                for inst in instances:
                    output += f"- `{inst['id']}` - {inst['model']} ({inst['type']})\n"
            else:
                output += "*No models loaded. Use `exo_load_model` to load one.*\n"

            output += "\n### Runner Status\n"
            runners = status.get("runner_status", {})
            if runners:
                for runner_id, runner_status in runners.items():
                    status_emoji = "+" if "Ready" in runner_status else "~"
                    output += f"- [{status_emoji}] `{runner_id}`: {runner_status}\n"
            else:
                output += "*No runners*\n"

        return [TextContent(type="text", text=output)]

    elif name == "exo_models":
        models = await client.list_models()

        if models and isinstance(models[0], dict) and "error" in models[0]:
            return [TextContent(
                type="text",
                text=f"**Error**: {models[0]['error']}\n\nEnsure Exo is running."
            )]

        output = f"""## Available Models ({len(models)} total)

| Model ID | Name |
|----------|------|
"""
        for model in models[:20]:  # Limit to 20
            output += f"| {model.get('id', 'unknown')} | {model.get('name', '')} |\n"

        if len(models) > 20:
            output += f"\n*...and {len(models) - 20} more*\n"

        output += """
### Quick Start
```
1. exo_load_model(model="llama-3.2-1b")  # Small, fast
2. exo_chat(messages=[{"role":"user","content":"Hi"}])
```
"""
        return [TextContent(type="text", text=output)]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

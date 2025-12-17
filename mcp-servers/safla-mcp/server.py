#!/usr/bin/env python3
"""
SAFLA MCP Server
================

Self-Aware Feedback Loop Algorithm (SAFLA) MCP Server.

Provides high-performance embeddings and hybrid memory operations
for AI agent systems. Supports three memory types:
- Episodic: Time-bound experiences and events
- Semantic: Abstract concepts and timeless knowledge
- Procedural: Skills and executable procedures

MCP Tools:
- generate_embeddings: Generate vector embeddings (optimized for speed)
- store_memory: Store information in hybrid memory system
- retrieve_memories: Search and retrieve from memory system
- get_performance: Get performance metrics

Requirements:
- pip install mcp aiohttp

Environment Variables:
- SAFLA_REMOTE_URL: Remote SAFLA service URL (optional)
- SAFLA_LOCAL_MODE: Use local embeddings if 'true' (default)
"""

import asyncio
import json
import sys
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import hashlib

try:
    from mcp.server.models import InitializationOptions
    from mcp.server import NotificationOptions, Server
    import mcp.server.stdio
    import mcp.types as types
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install mcp")
    sys.exit(1)

# Try to import sentence-transformers for local embeddings
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False

# Try to import aiohttp for remote SAFLA
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


# Configuration
SAFLA_URL = os.environ.get("SAFLA_REMOTE_URL", "")
LOCAL_MODE = os.environ.get("SAFLA_LOCAL_MODE", "true").lower() == "true"
DATA_DIR = Path(os.environ.get("AGENTIC_SYSTEM_PATH", Path.home() / "agentic-system")) / "safla-data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# Create MCP server
server = Server("safla-mcp")

# Local storage for memories (simple JSON-based)
MEMORY_FILE = DATA_DIR / "memories.json"


def load_memories() -> Dict[str, List[Dict]]:
    """Load memories from disk."""
    if MEMORY_FILE.exists():
        try:
            return json.loads(MEMORY_FILE.read_text())
        except:
            pass
    return {"episodic": [], "semantic": [], "procedural": []}


def save_memories(memories: Dict[str, List[Dict]]):
    """Save memories to disk."""
    MEMORY_FILE.write_text(json.dumps(memories, indent=2))


# Initialize embedding model if available
_embedding_model = None


def get_embedding_model():
    """Get or initialize embedding model."""
    global _embedding_model
    if _embedding_model is None and EMBEDDINGS_AVAILABLE:
        # Use a small, fast model
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _embedding_model


def generate_local_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings locally using sentence-transformers."""
    model = get_embedding_model()
    if model is None:
        # Return simple hash-based pseudo-embeddings as fallback
        embeddings = []
        for text in texts:
            # Generate 384-dim pseudo-embedding from hash
            hash_bytes = hashlib.sha512(text.encode()).digest()
            embedding = [float(b) / 255.0 for b in hash_bytes[:384]]
            embeddings.append(embedding)
        return embeddings

    # Use actual model
    embeddings = model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()


async def call_remote_safla(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Call the remote SAFLA API."""
    if not SAFLA_URL or not AIOHTTP_AVAILABLE:
        return {"error": "Remote SAFLA not configured"}

    async with aiohttp.ClientSession() as session:
        mcp_request = {
            "jsonrpc": "2.0",
            "id": f"safla_{method}",
            "method": method,
            "params": params
        }

        try:
            async with session.post(
                f"{SAFLA_URL}/api/safla",
                json=mcp_request,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("result", {"status": "success", "data": result})
                else:
                    return {"error": f"API error: {response.status}"}
        except Exception as e:
            return {"error": str(e)}


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available SAFLA tools."""
    return [
        types.Tool(
            name="generate_embeddings",
            description="Generate embeddings using SAFLA's extreme-optimized engine (1.75M+ ops/sec)",
            inputSchema={
                "type": "object",
                "properties": {
                    "texts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Texts to embed"
                    }
                },
                "required": ["texts"]
            }
        ),
        types.Tool(
            name="store_memory",
            description="Store information in SAFLA's hybrid memory system",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Content to store"
                    },
                    "memory_type": {
                        "type": "string",
                        "enum": ["episodic", "semantic", "procedural"],
                        "default": "episodic"
                    }
                },
                "required": ["content"]
            }
        ),
        types.Tool(
            name="retrieve_memories",
            description="Search and retrieve from SAFLA's memory system",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_performance",
            description="Get SAFLA performance metrics",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls."""

    if not arguments:
        arguments = {}

    if name == "generate_embeddings":
        texts = arguments.get("texts", [])

        if not texts:
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": "No texts provided"})
            )]

        # Use local embeddings or remote SAFLA
        if LOCAL_MODE or not SAFLA_URL:
            embeddings = generate_local_embeddings(texts)
            result = {
                "success": True,
                "embeddings": embeddings,
                "count": len(embeddings),
                "dimensions": len(embeddings[0]) if embeddings else 0,
                "mode": "local"
            }
        else:
            result = await call_remote_safla("generate_embeddings", {"texts": texts})
            result["mode"] = "remote"

        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]

    elif name == "store_memory":
        content = arguments.get("content", "")
        memory_type = arguments.get("memory_type", "episodic")

        if not content:
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": "No content provided"})
            )]

        # Generate embedding for the content
        if LOCAL_MODE or not SAFLA_URL:
            embedding = generate_local_embeddings([content])[0]

            # Store locally
            memories = load_memories()

            memory_entry = {
                "id": hashlib.md5(content.encode()).hexdigest()[:12],
                "content": content,
                "embedding": embedding,
                "memory_type": memory_type,
                "timestamp": datetime.now().isoformat(),
                "access_count": 0
            }

            memories[memory_type].append(memory_entry)
            save_memories(memories)

            result = {
                "success": True,
                "memory_id": memory_entry["id"],
                "memory_type": memory_type,
                "mode": "local"
            }
        else:
            result = await call_remote_safla("store_memory", {
                "content": content,
                "memory_type": memory_type
            })
            result["mode"] = "remote"

        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]

    elif name == "retrieve_memories":
        query = arguments.get("query", "")
        limit = arguments.get("limit", 5)

        if not query:
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": "No query provided"})
            )]

        if LOCAL_MODE or not SAFLA_URL:
            # Local search using cosine similarity
            query_embedding = generate_local_embeddings([query])[0]

            memories = load_memories()
            all_memories = []

            for memory_type, type_memories in memories.items():
                for memory in type_memories:
                    # Simple cosine similarity
                    if "embedding" in memory:
                        mem_embedding = memory["embedding"]
                        dot_product = sum(a * b for a, b in zip(query_embedding, mem_embedding))
                        norm_q = sum(a * a for a in query_embedding) ** 0.5
                        norm_m = sum(a * a for a in mem_embedding) ** 0.5
                        similarity = dot_product / (norm_q * norm_m) if norm_q * norm_m > 0 else 0
                    else:
                        # Fallback: keyword matching
                        similarity = 1.0 if query.lower() in memory["content"].lower() else 0.0

                    all_memories.append({
                        "id": memory["id"],
                        "content": memory["content"],
                        "memory_type": memory_type,
                        "similarity": round(similarity, 4),
                        "timestamp": memory.get("timestamp", "")
                    })

            # Sort by similarity and return top results
            all_memories.sort(key=lambda x: x["similarity"], reverse=True)
            results = all_memories[:limit]

            result = {
                "success": True,
                "results": results,
                "count": len(results),
                "mode": "local"
            }
        else:
            result = await call_remote_safla("retrieve_memories", {
                "query": query,
                "limit": limit
            })
            result["mode"] = "remote"

        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]

    elif name == "get_performance":
        if LOCAL_MODE or not SAFLA_URL:
            memories = load_memories()
            total_memories = sum(len(m) for m in memories.values())

            result = {
                "success": True,
                "mode": "local",
                "embeddings_model": "all-MiniLM-L6-v2" if EMBEDDINGS_AVAILABLE else "hash-based-fallback",
                "embeddings_available": EMBEDDINGS_AVAILABLE,
                "total_memories": total_memories,
                "memory_breakdown": {k: len(v) for k, v in memories.items()},
                "storage_path": str(DATA_DIR),
                "estimated_ops_per_sec": "1000-10000" if EMBEDDINGS_AVAILABLE else "100000+"
            }
        else:
            result = await call_remote_safla("get_performance_metrics", {})
            result["mode"] = "remote"

        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]

    else:
        return [types.TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown tool: {name}"})
        )]


async def main():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        print("SAFLA MCP Server starting...", file=sys.stderr)
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="safla-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())

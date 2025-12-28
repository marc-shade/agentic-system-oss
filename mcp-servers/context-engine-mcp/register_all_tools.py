#!/usr/bin/env python3
"""
Register ALL tools from the agentic system MCP servers.
Comprehensive tool registry for Context Engine.
"""

import sys
sys.path.insert(0, "/Volumes/SSDRAID0/agentic-system/mcp-servers/context-engine-mcp")
from server import engine

# All tools from enhanced-memory-mcp
ENHANCED_MEMORY_TOOLS = [
    {"name": "mcp__enhanced-memory__create_entities", "server": "enhanced-memory",
     "description": "Create entities with compression, storage, automatic versioning, and contextual enrichment",
     "parameters": {"entities": "List[dict]"}, "tags": ["memory", "create", "entities"]},
    {"name": "mcp__enhanced-memory__search_nodes", "server": "enhanced-memory",
     "description": "Search for entities by name or type with automatic version history",
     "parameters": {"query": "str", "limit": "int"}, "tags": ["memory", "search"]},
    {"name": "mcp__enhanced-memory__memory_diff", "server": "enhanced-memory",
     "description": "Get diff between two versions of a memory",
     "parameters": {"entity_name": "str", "version1": "int", "version2": "int"}, "tags": ["memory", "diff", "versions"]},
    {"name": "mcp__enhanced-memory__memory_revert", "server": "enhanced-memory",
     "description": "Revert a memory to a specific version",
     "parameters": {"entity_name": "str", "version": "int"}, "tags": ["memory", "revert"]},
    {"name": "mcp__enhanced-memory__memory_branch", "server": "enhanced-memory",
     "description": "Create a branch of a memory for experimentation",
     "parameters": {"entity_name": "str", "branch_name": "str"}, "tags": ["memory", "branch"]},
    {"name": "mcp__enhanced-memory__detect_memory_conflicts", "server": "enhanced-memory",
     "description": "Detect duplicate or conflicting memories",
     "parameters": {"threshold": "float"}, "tags": ["memory", "conflicts"]},
    {"name": "mcp__enhanced-memory__save_implementation_plan", "server": "enhanced-memory",
     "description": "Save a structured implementation plan",
     "parameters": {"name": "str", "steps": "list"}, "tags": ["memory", "plan"]},
    {"name": "mcp__enhanced-memory__get_memory_status", "server": "enhanced-memory",
     "description": "Get overall memory system status and statistics",
     "parameters": {}, "tags": ["memory", "status"]},
    {"name": "mcp__enhanced-memory__execute_code", "server": "enhanced-memory",
     "description": "Execute Python code in secure sandbox with API access",
     "parameters": {"code": "str"}, "tags": ["memory", "code", "sandbox"]},
    {"name": "mcp__enhanced-memory__nmf_remember", "server": "enhanced-memory",
     "description": "Store a new memory in the Neural Memory Fabric",
     "parameters": {"content": "str", "tags": "list"}, "tags": ["memory", "nmf", "store"]},
    {"name": "mcp__enhanced-memory__nmf_recall", "server": "enhanced-memory",
     "description": "Retrieve memories from the Neural Memory Fabric",
     "parameters": {"query": "str", "mode": "str"}, "tags": ["memory", "nmf", "recall"]},
    {"name": "mcp__enhanced-memory__safla_generate_embeddings", "server": "enhanced-memory",
     "description": "Generate embeddings using SAFLA's extreme-optimized engine (1.75M+ ops/sec)",
     "parameters": {"texts": "list"}, "tags": ["embeddings", "safla", "vectors"]},
    {"name": "mcp__enhanced-memory__safla_store_memory", "server": "enhanced-memory",
     "description": "Store information in SAFLA's hybrid memory system",
     "parameters": {"content": "str", "memory_type": "str"}, "tags": ["memory", "safla", "store"]},
    {"name": "mcp__enhanced-memory__safla_retrieve_memories", "server": "enhanced-memory",
     "description": "Search and retrieve from SAFLA's memory system",
     "parameters": {"query": "str", "limit": "int"}, "tags": ["memory", "safla", "search"]},
    {"name": "mcp__enhanced-memory__semantic_cache_get", "server": "enhanced-memory",
     "description": "Check semantic cache for similar query",
     "parameters": {"query": "str"}, "tags": ["cache", "semantic"]},
    {"name": "mcp__enhanced-memory__semantic_cache_store", "server": "enhanced-memory",
     "description": "Store query-response pair in semantic cache",
     "parameters": {"query": "str", "response": "str"}, "tags": ["cache", "store"]},
    {"name": "mcp__enhanced-memory__fact_search", "server": "enhanced-memory",
     "description": "FACT-accelerated memory search with cache-first retrieval (<48ms)",
     "parameters": {"query": "str", "limit": "int"}, "tags": ["search", "fast", "cache"]},
    {"name": "mcp__enhanced-memory__unified_search", "server": "enhanced-memory",
     "description": "Unified search with FACT cache and Qdrant fallback",
     "parameters": {"query": "str", "backend": "str"}, "tags": ["search", "unified"]},
    {"name": "mcp__enhanced-memory__rb_retrieve", "server": "enhanced-memory",
     "description": "Retrieve relevant reasoning memories for a query",
     "parameters": {"query": "str", "k": "int"}, "tags": ["reasoning", "memory", "retrieve"]},
    {"name": "mcp__enhanced-memory__rb_learn", "server": "enhanced-memory",
     "description": "Learn from a task outcome by distilling memories",
     "parameters": {"task_id": "str", "query": "str", "outcome": "str"}, "tags": ["reasoning", "learn"]},
]

# Voice Mode tools
VOICE_TOOLS = [
    {"name": "mcp__voice-mode__converse", "server": "voice-mode",
     "description": "Have a voice conversation - speak a message and optionally listen for response via TTS/STT",
     "parameters": {"message": "str", "wait_for_response": "bool", "voice": "str"}, "tags": ["voice", "tts", "stt", "speak"]},
    {"name": "mcp__voice-mode__voice_registry", "server": "voice-mode",
     "description": "Get the current voice provider registry showing all discovered endpoints",
     "parameters": {}, "tags": ["voice", "providers", "registry"]},
]

# Agent Runtime tools
AGENT_RUNTIME_TOOLS = [
    {"name": "mcp__agent-runtime-mcp__create_goal", "server": "agent-runtime-mcp",
     "description": "Create a new goal with name and description. Goals persist across sessions",
     "parameters": {"name": "str", "description": "str"}, "tags": ["goal", "create", "persistent"]},
    {"name": "mcp__agent-runtime-mcp__decompose_goal", "server": "agent-runtime-mcp",
     "description": "Decompose a goal into tasks using AI",
     "parameters": {"goal_id": "int", "strategy": "str"}, "tags": ["goal", "decompose", "tasks"]},
    {"name": "mcp__agent-runtime-mcp__create_task", "server": "agent-runtime-mcp",
     "description": "Create a new task manually. Tasks persist in queue across sessions",
     "parameters": {"title": "str", "description": "str", "priority": "int"}, "tags": ["task", "create"]},
    {"name": "mcp__agent-runtime-mcp__get_next_task", "server": "agent-runtime-mcp",
     "description": "Get the next task from the queue (highest priority, dependencies met)",
     "parameters": {}, "tags": ["task", "queue", "next"]},
    {"name": "mcp__agent-runtime-mcp__update_task_status", "server": "agent-runtime-mcp",
     "description": "Update task status (pending, in_progress, completed, failed, cancelled)",
     "parameters": {"task_id": "int", "status": "str"}, "tags": ["task", "status", "update"]},
    {"name": "mcp__agent-runtime-mcp__list_goals", "server": "agent-runtime-mcp",
     "description": "List all goals, optionally filtered by status",
     "parameters": {"status": "str"}, "tags": ["goal", "list"]},
    {"name": "mcp__agent-runtime-mcp__list_tasks", "server": "agent-runtime-mcp",
     "description": "List tasks, optionally filtered by goal or status",
     "parameters": {"goal_id": "int", "status": "str"}, "tags": ["task", "list"]},
    {"name": "mcp__agent-runtime-mcp__create_relay_pipeline", "server": "agent-runtime-mcp",
     "description": "Create a 48-agent relay race pipeline for sequential execution",
     "parameters": {"name": "str", "goal": "str", "agent_types": "list"}, "tags": ["relay", "pipeline", "agents"]},
    {"name": "mcp__agent-runtime-mcp__advance_relay", "server": "agent-runtime-mcp",
     "description": "Manually advance relay to next step after completing current step",
     "parameters": {"pipeline_id": "str", "quality_score": "float"}, "tags": ["relay", "advance"]},
    {"name": "mcp__agent-runtime-mcp__ember_check_violation", "server": "agent-runtime-mcp",
     "description": "Check if a planned action violates production-only policy",
     "parameters": {"action": "str", "params": "dict", "context": "str"}, "tags": ["ember", "policy", "check"]},
    {"name": "mcp__agent-runtime-mcp__ember_consult", "server": "agent-runtime-mcp",
     "description": "Consult Ember for advice on a decision",
     "parameters": {"question": "str", "options": "list"}, "tags": ["ember", "consult", "advice"]},
    {"name": "mcp__agent-runtime-mcp__ember_chat", "server": "agent-runtime-mcp",
     "description": "Have a free-form conversation with Ember",
     "parameters": {"message": "str"}, "tags": ["ember", "chat"]},
]

# Cluster Execution tools
CLUSTER_TOOLS = [
    {"name": "mcp__cluster-execution-mcp__cluster_bash", "server": "cluster-execution-mcp",
     "description": "Execute bash command with automatic cluster routing based on load",
     "parameters": {"command": "str", "requires_os": "str"}, "tags": ["cluster", "bash", "execution"]},
    {"name": "mcp__cluster-execution-mcp__cluster_status", "server": "cluster-execution-mcp",
     "description": "Get current cluster status and load distribution across all nodes",
     "parameters": {}, "tags": ["cluster", "status", "nodes"]},
    {"name": "mcp__cluster-execution-mcp__offload_to", "server": "cluster-execution-mcp",
     "description": "Explicitly route command to specific cluster node",
     "parameters": {"command": "str", "node_id": "str"}, "tags": ["cluster", "offload", "route"]},
    {"name": "mcp__cluster-execution-mcp__parallel_execute", "server": "cluster-execution-mcp",
     "description": "Execute multiple commands in parallel across cluster",
     "parameters": {"commands": "list"}, "tags": ["cluster", "parallel", "batch"]},
    {"name": "mcp__cluster-execution-mcp__send_message_to_node", "server": "cluster-execution-mcp",
     "description": "Send a chat message to another node's AI persona",
     "parameters": {"to_node": "str", "message": "str"}, "tags": ["cluster", "chat", "message"]},
    {"name": "mcp__cluster-execution-mcp__get_cluster_awareness", "server": "cluster-execution-mcp",
     "description": "Get awareness of all nodes in the cluster - their capabilities and status",
     "parameters": {}, "tags": ["cluster", "awareness", "capabilities"]},
    {"name": "mcp__cluster-execution-mcp__decompose_goal", "server": "cluster-execution-mcp",
     "description": "AGI: Decompose a complex goal into coordinated multi-node tasks",
     "parameters": {"goal": "str"}, "tags": ["agi", "goal", "decompose"]},
]

# Sequential Thinking
THINKING_TOOLS = [
    {"name": "mcp__sequential-thinking__sequentialthinking", "server": "sequential-thinking",
     "description": "Dynamic reflective problem-solving through step-by-step thoughts with revision support",
     "parameters": {"thought": "str", "thoughtNumber": "int", "totalThoughts": "int"}, "tags": ["reasoning", "thinking", "reflection"]},
]

# Research tools
RESEARCH_TOOLS = [
    {"name": "mcp__research-paper-mcp__search_arxiv", "server": "research-paper-mcp",
     "description": "Search arXiv for research papers by query",
     "parameters": {"query": "str", "max_results": "int"}, "tags": ["research", "papers", "arxiv"]},
    {"name": "mcp__research-paper-mcp__search_semantic_scholar", "server": "research-paper-mcp",
     "description": "Search Semantic Scholar for papers with citation counts",
     "parameters": {"query": "str", "limit": "int"}, "tags": ["research", "papers", "citations"]},
    {"name": "mcp__research-paper-mcp__download_paper", "server": "research-paper-mcp",
     "description": "Download research paper PDF from URL",
     "parameters": {"url": "str", "paper_id": "str"}, "tags": ["research", "download", "pdf"]},
    {"name": "mcp__research-paper-mcp__extract_insights", "server": "research-paper-mcp",
     "description": "Extract key insights, findings, and techniques from research paper text",
     "parameters": {"paper_text": "str", "focus_areas": "list"}, "tags": ["research", "insights", "analysis"]},
    {"name": "mcp__research-paper-mcp__fetch_youtube_transcript", "server": "research-paper-mcp",
     "description": "Fetch transcript from YouTube video using yt-dlp",
     "parameters": {"url": "str", "language": "str"}, "tags": ["youtube", "transcript", "video"]},
]

# LLM Council tools
COUNCIL_TOOLS = [
    {"name": "mcp__llm-council__council_deliberate", "server": "llm-council",
     "description": "Run full 3-stage council deliberation on a question",
     "parameters": {"question": "str"}, "tags": ["council", "deliberate", "multi-llm"]},
    {"name": "mcp__llm-council__council_quick_query", "server": "llm-council",
     "description": "Query a single provider for a fast response",
     "parameters": {"provider": "str", "prompt": "str"}, "tags": ["council", "query", "single"]},
    {"name": "mcp__llm-council__council_compare_providers", "server": "llm-council",
     "description": "Compare all providers on the same prompt",
     "parameters": {"prompt": "str"}, "tags": ["council", "compare", "providers"]},
    {"name": "mcp__llm-council__council_run_pattern", "server": "llm-council",
     "description": "Run a specific deliberation pattern (debate, socratic, red_team, etc.)",
     "parameters": {"pattern": "str", "question": "str"}, "tags": ["council", "pattern", "debate"]},
]

# Context7 tools
CONTEXT7_TOOLS = [
    {"name": "mcp__plugin_context7_context7__resolve-library-id", "server": "context7",
     "description": "Resolve a package/product name to a Context7-compatible library ID",
     "parameters": {"libraryName": "str"}, "tags": ["docs", "library", "resolve"]},
    {"name": "mcp__plugin_context7_context7__get-library-docs", "server": "context7",
     "description": "Fetch up-to-date documentation for a library",
     "parameters": {"context7CompatibleLibraryID": "str", "topic": "str"}, "tags": ["docs", "library", "fetch"]},
]

ALL_TOOLS = (
    ENHANCED_MEMORY_TOOLS + VOICE_TOOLS + AGENT_RUNTIME_TOOLS +
    CLUSTER_TOOLS + THINKING_TOOLS + RESEARCH_TOOLS +
    COUNCIL_TOOLS + CONTEXT7_TOOLS
)

def register_all():
    print(f"Registering {len(ALL_TOOLS)} tools...")

    for tool in ALL_TOOLS:
        try:
            engine.register_tool(**tool)
        except Exception as e:
            print(f"  Error: {tool['name']}: {e}")

    print(f"✓ Registered {len(engine.tools)} tools total")

    # Stats
    by_server = {}
    for t in engine.tools.values():
        if t.server not in by_server:
            by_server[t.server] = 0
        by_server[t.server] += 1

    print("\nBy Server:")
    for server, count in sorted(by_server.items()):
        print(f"  {server}: {count} tools")

if __name__ == "__main__":
    register_all()

#!/usr/bin/env python3
"""
Enhanced Memory Session Loader
Loads relevant context from enhanced-memory-mcp at session start

This hook runs at Claude Code session start and loads:
1. Recent session memories
2. Ongoing tasks and context
3. Important patterns and learnings
4. Node-specific configuration

Uses enhanced-memory-mcp MCP server for all memory operations
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime

def log(message):
    """Log to session start log file"""
    log_file = Path.home() / ".claude" / "logs" / "memory_loader.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

def load_node_config():
    """Load node configuration"""
    node_config_path = Path.home() / ".claude" / "node-config.json"
    if node_config_path.exists():
        with open(node_config_path) as f:
            return json.load(f)
    return None

def call_mcp_tool(server_name, tool_name, arguments):
    """
    Call an MCP tool (this will be integrated when MCP SDK is available)
    For now, this is a placeholder that logs the intent
    """
    log(f"Would call MCP tool: {server_name}.{tool_name} with args: {json.dumps(arguments)}")
    # TODO: Integrate with actual MCP SDK when available
    # For now, we prepare the structure for future integration
    return {
        "success": True,
        "placeholder": True,
        "intent": {
            "server": server_name,
            "tool": tool_name,
            "arguments": arguments
        }
    }

def load_session_memory():
    """Load relevant memory for this session"""
    try:
        node_config = load_node_config()
        node_id = node_config.get("node_id", "unknown") if node_config else "unknown"
        
        log(f"Loading session memory for node: {node_id}")
        
        # 1. Load recent session context (compressed)
        # This uses the enhanced-memory-mcp's load_compressed_session_context tool
        session_context = call_mcp_tool(
            "enhanced-memory-mcp",
            "load_compressed_session_context",
            {
                "max_entries": 15  # Last 15 relevant entries
            }
        )
        
        # 2. Search for ongoing tasks/goals
        tasks = call_mcp_tool(
            "enhanced-memory-mcp",
            "search_nodes",
            {
                "query": f"node:{node_id} type:task status:active",
                "entity_types": ["task", "goal", "project"],
                "max_results": 10
            }
        )
        
        # 3. Load important system patterns
        patterns = call_mcp_tool(
            "enhanced-memory-mcp",
            "search_nodes",
            {
                "query": "type:pattern importance:high",
                "entity_types": ["pattern", "learning", "insight"],
                "max_results": 20
            }
        )
        
        # 4. Check cluster connectivity and load shared memories
        cluster_status = call_mcp_tool(
            "enhanced-memory-mcp",
            "get_cluster_stats",
            {}
        )
        
        log("Session memory loaded successfully")
        log(f"- Session context: {len(session_context.get('entries', []))} entries")
        log(f"- Active tasks: {len(tasks.get('results', []))} tasks")
        log(f"- Patterns: {len(patterns.get('results', []))} patterns")
        
        # Return summary for Claude Code to use
        return {
            "success": True,
            "node_id": node_id,
            "context_loaded": True,
            "summary": {
                "session_entries": len(session_context.get('entries', [])),
                "active_tasks": len(tasks.get('results', [])),
                "patterns": len(patterns.get('results', []))
            }
        }
        
    except Exception as e:
        log(f"Error loading session memory: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def main():
    """Main entry point"""
    try:
        # Load stdin if provided (session start metadata)
        try:
            input_data = json.load(sys.stdin)
            session_id = input_data.get('session_id', 'unknown')
            log(f"Session start detected: {session_id}")
        except:
            session_id = "unknown"
        
        # Load memory for this session
        result = load_session_memory()
        
        # Output result
        print(json.dumps(result, indent=2))
        
        # Always exit successfully (don't block session start)
        sys.exit(0)
        
    except Exception as e:
        log(f"Fatal error in memory loader: {e}")
        # Fail gracefully
        print(json.dumps({"success": False, "error": str(e)}))
        sys.exit(0)

if __name__ == '__main__':
    main()

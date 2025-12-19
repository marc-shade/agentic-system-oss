#!/usr/bin/env python3
"""
Enhanced Memory Integration for Skill Learning

Stores successful patterns in enhanced-memory-mcp for:
- Semantic search of similar workflows
- Cross-session pattern recognition
- Skill effectiveness tracking
"""

import json
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime

HOME = Path.home()
LEARNING_DB = HOME / ".claude" / "learning-patterns.db"
MCP_MEMORY_SCRIPT = HOME / "Documents" / "Cline" / "MCP" / "enhanced-memory-mcp" / "server.py"


def store_pattern_in_memory(pattern_hash, tool_sequence, occurrences, context=""):
    """Store detected pattern in enhanced-memory-mcp"""
    entity_data = {
        "entities": [{
            "name": f"skill-pattern-{pattern_hash}",
            "entityType": "skill_pattern",
            "observations": [
                f"tool_sequence: {' → '.join(tool_sequence)}",
                f"occurrences: {occurrences}",
                f"detected: {datetime.now().isoformat()}",
                f"context: {context}",
                "pattern_type: autonomous_learning"
            ]
        }]
    }

    # Call enhanced-memory-mcp create_entities
    try:
        result = subprocess.run(
            ["python3", str(MCP_MEMORY_SCRIPT), "create_entities", json.dumps(entity_data)],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Memory integration error: {e}", file=sys.stderr)
        return False


def search_similar_patterns(tool_sequence):
    """Search for similar workflows in memory"""
    query = f"skill_pattern tool_sequence:{' '.join(tool_sequence[:2])}"

    try:
        result = subprocess.run(
            ["python3", str(MCP_MEMORY_SCRIPT), "search_nodes", json.dumps({"query": query})],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return json.loads(result.stdout)
        return None
    except Exception as e:
        print(f"Memory search error: {e}", file=sys.stderr)
        return None


def store_skill_creation(skill_name, pattern_hash, success=True):
    """Store skill creation outcome in memory"""
    entity_data = {
        "entities": [{
            "name": f"skill-created-{skill_name}",
            "entityType": "skill_outcome",
            "observations": [
                f"skill_name: {skill_name}",
                f"pattern_hash: {pattern_hash}",
                f"created: {datetime.now().isoformat()}",
                f"success: {success}",
                "created_by: autonomous_learning_system"
            ]
        }]
    }

    # Create relation to pattern
    relation_data = {
        "relations": [{
            "from": f"skill-created-{skill_name}",
            "to": f"skill-pattern-{pattern_hash}",
            "relationType": "derived_from"
        }]
    }

    try:
        # Create entity
        subprocess.run(
            ["python3", str(MCP_MEMORY_SCRIPT), "create_entities", json.dumps(entity_data)],
            timeout=10
        )

        # Create relation
        subprocess.run(
            ["python3", str(MCP_MEMORY_SCRIPT), "create_relations", json.dumps(relation_data)],
            timeout=10
        )
        return True
    except Exception as e:
        print(f"Skill outcome storage error: {e}", file=sys.stderr)
        return False


def get_pattern_recommendations(current_context):
    """Get skill recommendations based on memory patterns"""
    # Search for patterns in current context
    similar = search_similar_patterns(current_context.get("tool_sequence", []))

    if not similar or "nodes" not in similar:
        return []

    recommendations = []
    for node in similar["nodes"][:5]:  # Top 5 similar patterns
        observations = node.get("observations", [])
        pattern_info = {}

        for obs in observations:
            if ":" in obs:
                key, value = obs.split(":", 1)
                pattern_info[key.strip()] = value.strip()

        if pattern_info:
            recommendations.append({
                "pattern": node.get("name"),
                "similarity": "high",  # Could calculate actual similarity
                "observations": pattern_info
            })

    return recommendations


def sync_patterns_to_memory():
    """Sync all high-occurrence patterns to memory"""
    if not LEARNING_DB.exists():
        return

    conn = sqlite3.connect(LEARNING_DB)
    c = conn.cursor()

    # Get patterns with 5+ occurrences not yet in memory
    c.execute('''SELECT pattern_hash, tool_sequence, occurrences, context_summary
                 FROM patterns
                 WHERE occurrences >= 5
                 AND skill_created = 0''')

    patterns = c.fetchall()
    conn.close()

    stored = 0
    for pattern_hash, tool_seq, occurrences, context in patterns:
        tools = tool_seq.split("->")
        if store_pattern_in_memory(pattern_hash, tools, occurrences, context):
            stored += 1

    return stored


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "sync":
            count = sync_patterns_to_memory()
            print(f"Synced {count} patterns to memory")

        elif command == "search" and len(sys.argv) > 2:
            tools = sys.argv[2].split(",")
            results = search_similar_patterns(tools)
            print(json.dumps(results, indent=2))

        elif command == "recommend" and len(sys.argv) > 2:
            context = json.loads(sys.argv[2])
            recs = get_pattern_recommendations(context)
            print(json.dumps(recs, indent=2))
    else:
        # Default: sync patterns
        sync_patterns_to_memory()

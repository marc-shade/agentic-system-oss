#!/usr/bin/env python3
"""
Cross-Memory Sync Hook - Bidirectional sync between enhanced-memory and Graphiti

Purpose: Maintain consistency between the two memory systems by:
1. Extracting system rules from Graphiti conversations → Enhanced-Memory (fast lookup)
2. Linking Enhanced-Memory entities → Graphiti (historical context)
3. Detecting conflicts and maintaining cross-references

Trigger: post-response
Priority: 3 (after subagent-memory-capture, before other memory operations)
"""

import sys
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

# Configuration
GRAPHITI_INTEGRATION_LOG = Path.home() / ".claude" / ".graphiti_integration.log"
SYNC_STATS_FILE = Path.home() / ".claude" / ".cross_memory_sync_stats.json"
MAX_RECENT_EPISODES = 5  # Only sync recent episodes to avoid performance issues


def log_sync_event(event_type, details):
    """Log sync events for debugging and monitoring."""
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "details": details
        }
        with open(GRAPHITI_INTEGRATION_LOG, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"⚠️  Logging error: {e}", file=sys.stderr)


def extract_system_rules_from_text(text):
    """Extract system rules from conversation text."""
    rules = []

    # Patterns that indicate system rules/preferences
    rule_patterns = [
        (r"always (use|include|add|require|ensure) ([^,.!?]+)", "always_use"),
        (r"never (use|include|add|allow) ([^,.!?]+)", "never_use"),
        (r"production[- ]?ready (code|implementation)", "production_ready"),
        (r"no (POCs?|prototypes?|demos?|examples?)", "no_prototypes"),
        (r"I (prefer|want|like|need) ([^,.!?]+)", "user_preference"),
        (r"(dark|light) mode", "ui_theme"),
        (r"Paper Shaders", "visual_effects_library"),
    ]

    for pattern, rule_type in rule_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            rules.append({
                "type": rule_type,
                "text": match.group(0),
                "full_context": text[:200]  # Include context
            })

    return rules


def sync_graphiti_to_enhanced_memory():
    """
    Sync important facts from Graphiti to Enhanced-Memory for fast lookup.

    Strategy:
    - Get recent user interactions from Graphiti
    - Extract system rules and preferences
    - Store in enhanced-memory with cross-reference
    """
    try:
        # Check if this is a session with actual content
        # Skip if no meaningful interaction occurred
        session_log = Path.home() / ".claude" / ".last_session_content.txt"
        if not session_log.exists():
            return False

        # Read recent session content
        try:
            with open(session_log, "r") as f:
                session_content = f.read()
        except:
            session_content = ""

        # Only proceed if session had substantial content
        if len(session_content) < 100:
            return False

        # Extract potential system rules from session
        rules = extract_system_rules_from_text(session_content)

        if not rules:
            return False

        # Store rules in enhanced-memory
        # Note: In a real implementation, this would call enhanced-memory MCP
        # For now, we create a structured log that can be ingested

        rules_for_memory = []
        for rule in rules:
            rule_entry = {
                "name": f"system_rule_{rule['type']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "entityType": "system_rule",
                "observations": [
                    rule["text"],
                    f"Type: {rule['type']}",
                    "Source: graphiti_mcp"
                ],
                "metadata": {
                    "source": "graphiti_mcp",
                    "extracted_at": datetime.now().isoformat(),
                    "rule_type": rule["type"],
                    "context": rule["full_context"]
                }
            }
            rules_for_memory.append(rule_entry)

        # Write to integration queue
        integration_queue = Path.home() / ".claude" / ".memory_integration_queue.jsonl"
        with open(integration_queue, "a") as f:
            for rule in rules_for_memory:
                f.write(json.dumps(rule) + "\n")

        log_sync_event("graphiti_to_enhanced_memory", {
            "rules_extracted": len(rules),
            "types": [r["type"] for r in rules]
        })

        return True

    except Exception as e:
        log_sync_event("sync_error", {"error": str(e), "direction": "graphiti_to_enhanced"})
        return False


def sync_enhanced_memory_to_graphiti():
    """
    Sync Enhanced-Memory entities to Graphiti for historical context.

    Strategy:
    - Check for new system entities in enhanced-memory
    - Create links in Graphiti knowledge graph
    - Maintain bidirectional references
    """
    try:
        # Check for enhanced-memory updates since last sync
        em_update_marker = Path.home() / ".claude" / ".enhanced_memory_updates.txt"

        if not em_update_marker.exists():
            return False

        # Read updates
        try:
            with open(em_update_marker, "r") as f:
                updates = f.read().strip().split("\n")
        except:
            updates = []

        if not updates:
            return False

        # For each update, create a Graphiti link
        # Note: In real implementation, this would call Graphiti MCP
        # For now, we create a structured log

        graphiti_links = []
        for update in updates:
            try:
                entity_data = json.loads(update)

                graphiti_link = {
                    "name": f"EnhancedMemoryLink_{entity_data.get('name', 'unknown')}",
                    "json_data": json.dumps(entity_data),
                    "source_description": "enhanced_memory_link",
                    "timestamp": datetime.now().isoformat()
                }
                graphiti_links.append(graphiti_link)
            except:
                continue

        # Write to Graphiti integration queue
        graphiti_queue = Path.home() / ".claude" / ".graphiti_integration_queue.jsonl"
        with open(graphiti_queue, "a") as f:
            for link in graphiti_links:
                f.write(json.dumps(link) + "\n")

        # Clear the update marker
        em_update_marker.unlink()

        log_sync_event("enhanced_memory_to_graphiti", {
            "entities_linked": len(graphiti_links)
        })

        return True

    except Exception as e:
        log_sync_event("sync_error", {"error": str(e), "direction": "enhanced_to_graphiti"})
        return False


def validate_cross_references():
    """
    Validate that cross-references between systems are consistent.

    Returns:
        dict: Validation results with any conflicts found
    """
    try:
        validation_results = {
            "timestamp": datetime.now().isoformat(),
            "conflicts": [],
            "orphaned_references": [],
            "status": "healthy"
        }

        # Check integration queue sizes
        integration_queue = Path.home() / ".claude" / ".memory_integration_queue.jsonl"
        graphiti_queue = Path.home() / ".claude" / ".graphiti_integration_queue.jsonl"

        queue_sizes = {
            "enhanced_memory_queue": 0,
            "graphiti_queue": 0
        }

        if integration_queue.exists():
            with open(integration_queue, "r") as f:
                queue_sizes["enhanced_memory_queue"] = sum(1 for _ in f)

        if graphiti_queue.exists():
            with open(graphiti_queue, "r") as f:
                queue_sizes["graphiti_queue"] = sum(1 for _ in f)

        validation_results["queue_sizes"] = queue_sizes

        # If queues are getting large, warn
        if queue_sizes["enhanced_memory_queue"] > 100:
            validation_results["status"] = "warning"
            validation_results["conflicts"].append("Enhanced-Memory integration queue too large")

        if queue_sizes["graphiti_queue"] > 100:
            validation_results["status"] = "warning"
            validation_results["conflicts"].append("Graphiti integration queue too large")

        return validation_results

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def update_sync_statistics(graphiti_synced, enhanced_synced):
    """Update sync statistics for monitoring."""
    try:
        # Load existing stats
        if SYNC_STATS_FILE.exists():
            with open(SYNC_STATS_FILE, "r") as f:
                stats = json.load(f)
        else:
            stats = {
                "total_syncs": 0,
                "graphiti_to_enhanced": 0,
                "enhanced_to_graphiti": 0,
                "last_sync": None,
                "sync_history": []
            }

        # Update stats
        stats["total_syncs"] += 1
        if graphiti_synced:
            stats["graphiti_to_enhanced"] += 1
        if enhanced_synced:
            stats["enhanced_to_graphiti"] += 1
        stats["last_sync"] = datetime.now().isoformat()

        # Add to history (keep last 100)
        stats["sync_history"].append({
            "timestamp": datetime.now().isoformat(),
            "graphiti_synced": graphiti_synced,
            "enhanced_synced": enhanced_synced
        })

        if len(stats["sync_history"]) > 100:
            stats["sync_history"] = stats["sync_history"][-100:]

        # Save stats
        with open(SYNC_STATS_FILE, "w") as f:
            json.dump(stats, f, indent=2)

    except Exception as e:
        print(f"⚠️  Stats update error: {e}", file=sys.stderr)


def main():
    """
    Main hook execution.

    Performs bidirectional sync between enhanced-memory and Graphiti,
    then validates cross-references.
    """
    try:
        # Sync Graphiti → Enhanced-Memory (extract system rules)
        graphiti_synced = sync_graphiti_to_enhanced_memory()

        # Sync Enhanced-Memory → Graphiti (link entities)
        enhanced_synced = sync_enhanced_memory_to_graphiti()

        # Validate cross-references
        validation = validate_cross_references()

        # Update statistics
        update_sync_statistics(graphiti_synced, enhanced_synced)

        # Report status
        if graphiti_synced or enhanced_synced:
            sync_status = []
            if graphiti_synced:
                sync_status.append("Graphiti→Enhanced")
            if enhanced_synced:
                sync_status.append("Enhanced→Graphiti")

            print(f"🔄 Memory sync: {', '.join(sync_status)}")

        if validation["status"] == "warning":
            print(f"⚠️  Memory validation warnings: {len(validation['conflicts'])}")

        # Always exit 0 to continue (non-blocking hook)
        sys.exit(0)

    except Exception as e:
        print(f"Error in cross-memory sync hook: {e}", file=sys.stderr)
        log_sync_event("hook_error", {"error": str(e)})
        sys.exit(0)  # Non-blocking


if __name__ == "__main__":
    main()

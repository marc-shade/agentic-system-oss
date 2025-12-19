#!/usr/bin/env python3
"""
Preference Detection Hook - Automatic User Preference Tracking

Purpose: Detect when users state preferences and automatically store them in Graphiti

Functionality:
1. Detects explicit preference statements ("I prefer...", "I want...", etc.)
2. Detects rule statements ("Always use...", "Never use...", etc.)
3. Detects opinion statements ("I like/dislike...", etc.)
4. Stores in Graphiti with proper categorization and temporal tracking
5. Links to enhanced-memory for fast access to system rules

Trigger: post-user-message
Priority: 5 (after conversation-capture)
"""

import sys
import json
import re
from datetime import datetime
from pathlib import Path

# Configuration
GRAPHITI_PREFERENCE_QUEUE = Path.home() / ".claude" / ".graphiti_preference_queue.jsonl"
PREFERENCE_LOG = Path.home() / ".claude" / ".preference_detection.log"
PREFERENCE_STATS_FILE = Path.home() / ".claude" / ".preference_stats.json"

# Preference detection patterns with categories
PREFERENCE_PATTERNS = {
    "explicit_preference": [
        r"I prefer ([^,.!?;]+)",
        r"my preference is ([^,.!?;]+)",
        r"I'd prefer ([^,.!?;]+)",
        r"I would prefer ([^,.!?;]+)",
    ],
    "want_need": [
        r"I want ([^,.!?;]+)",
        r"I need ([^,.!?;]+)",
        r"I'd like ([^,.!?;]+)",
        r"I would like ([^,.!?;]+)",
        r"I require ([^,.!?;]+)",
    ],
    "opinion": [
        r"I (like|love|enjoy) ([^,.!?;]+)",
        r"I (dislike|hate|avoid) ([^,.!?;]+)",
        r"I'm (not )?(a fan of|into) ([^,.!?;]+)",
    ],
    "always_rule": [
        r"always (use|include|add|ensure|require|make sure|verify|check) ([^,.!?;]+)",
        r"make sure to always ([^,.!?;]+)",
        r"be sure to always ([^,.!?;]+)",
    ],
    "never_rule": [
        r"never (use|include|add|allow|create|make|show) ([^,.!?;]+)",
        r"don't ever (use|include|add|allow|create|make|show) ([^,.!?;]+)",
        r"avoid ([^,.!?;]+)",
    ],
    "ui_preference": [
        r"(dark|light) mode",
        r"I prefer (dark|light) theme",
        r"use (dark|light) theme",
    ],
    "code_quality": [
        r"production[- ]?ready (code|implementation|solution)",
        r"no (POCs?|prototypes?|demos?|examples?)",
        r"(complete|full|finished) implementation",
        r"no (mocks?|placeholders?|dummy data)",
    ],
    "communication_style": [
        r"be (concise|brief|detailed|verbose|technical)",
        r"explain (simply|in detail|thoroughly)",
        r"don't (over-?explain|assume)",
    ],
    "workflow_preference": [
        r"use (git|npm|yarn|uv|pip) for",
        r"prefer (typescript|javascript|python)",
        r"write tests (before|after|with)",
    ]
}

# Technology and tool patterns
TECHNOLOGY_PATTERNS = {
    "frameworks": [
        r"\b(react|vue|angular|svelte|next\.?js|nuxt)\b",
        r"\b(django|flask|fastapi|express|nest\.?js)\b",
    ],
    "languages": [
        r"\b(python|javascript|typescript|rust|go|java|kotlin)\b",
    ],
    "tools": [
        r"\b(docker|kubernetes|terraform|ansible)\b",
        r"\b(postgres|mysql|mongodb|redis)\b",
    ],
    "libraries": [
        r"\b(paper shaders?|framer motion|three\.?js|d3)\b",
    ]
}


def log_preference_event(event_type, details):
    """Log preference detection events."""
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "details": details
        }
        with open(PREFERENCE_LOG, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"⚠️  Logging error: {e}", file=sys.stderr)


def extract_technologies(text):
    """Extract mentioned technologies, frameworks, and tools."""
    technologies = {
        "frameworks": [],
        "languages": [],
        "tools": [],
        "libraries": []
    }

    for category, patterns in TECHNOLOGY_PATTERNS.items():
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                tech = match.group(0).strip()
                if tech not in technologies[category]:
                    technologies[category].append(tech)

    return technologies


def detect_preferences(text):
    """
    Detect user preferences from text.

    Returns:
        list: List of detected preferences with metadata
    """
    preferences = []

    for category, patterns in PREFERENCE_PATTERNS.items():
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Extract the full preference text
                preference_text = match.group(0).strip()

                # Extract the key value (what they prefer/want/etc)
                preference_value = ""
                if match.lastindex and match.lastindex >= 1:
                    # Get the last captured group as the value
                    preference_value = match.group(match.lastindex).strip()

                # Determine sentiment
                sentiment = "positive"
                if any(neg in preference_text.lower() for neg in ["never", "don't", "avoid", "dislike", "hate", "not"]):
                    sentiment = "negative"

                # Determine strength
                strength = "medium"
                if any(strong in preference_text.lower() for strong in ["always", "must", "require", "critical", "important", "hate", "love"]):
                    strength = "strong"
                elif any(weak in preference_text.lower() for weak in ["prefer", "like", "would like", "maybe", "possibly"]):
                    strength = "medium"

                # Extract technologies mentioned in this preference
                technologies = extract_technologies(preference_text)

                preferences.append({
                    "category": category,
                    "text": preference_text,
                    "value": preference_value,
                    "sentiment": sentiment,
                    "strength": strength,
                    "technologies": technologies,
                    "context_window": text[max(0, match.start() - 50):min(len(text), match.end() + 50)]
                })

    return preferences


def determine_preference_priority(preference):
    """Determine priority level for a preference based on its characteristics."""
    category = preference["category"]
    strength = preference["strength"]
    sentiment = preference["sentiment"]

    # High priority preferences
    if category in ["always_rule", "never_rule", "code_quality"]:
        return "high"

    # Strong preferences are higher priority
    if strength == "strong":
        return "high"

    # Explicit preferences are medium priority
    if category in ["explicit_preference", "want_need"]:
        return "medium"

    # Opinions and UI preferences are lower priority
    if category in ["opinion", "ui_preference"]:
        return "low"

    # Default
    return "medium"


def should_create_system_rule(preference):
    """Determine if a preference should also be stored as a system rule in enhanced-memory."""
    # Rules and code quality preferences should become system rules
    rule_categories = [
        "always_rule",
        "never_rule",
        "code_quality",
        "workflow_preference"
    ]

    return preference["category"] in rule_categories or preference["strength"] == "strong"


def detect_and_queue_preferences(user_message):
    """
    Detect preferences in user message and queue for Graphiti storage.

    Returns:
        bool: True if preferences were detected, False otherwise
    """
    try:
        # Skip if message is too short
        if len(user_message) < 20:
            return False

        # Detect preferences
        preferences = detect_preferences(user_message)

        if not preferences:
            return False

        # Deduplicate similar preferences
        unique_preferences = []
        seen_values = set()

        for pref in preferences:
            # Create a normalized key for deduplication
            key = f"{pref['category']}:{pref['value'].lower()}"
            if key not in seen_values:
                seen_values.add(key)
                unique_preferences.append(pref)

        if not unique_preferences:
            return False

        # Queue preferences for Graphiti ingestion
        timestamp = datetime.now().isoformat()
        queued_entries = []

        for idx, pref in enumerate(unique_preferences):
            priority = determine_preference_priority(pref)
            is_system_rule = should_create_system_rule(pref)

            # Create Graphiti user interaction entry
            interaction_entry = {
                "type": "add_user_interaction",
                "name": f"Preference_{pref['category']}_{timestamp}_{idx}",
                "interaction_text": pref['text'],
                "user_id": "marc_shade",
                "reference_time": timestamp,
                "source_description": f"auto_detected_{pref['category']}",
                "metadata": {
                    "category": pref['category'],
                    "value": pref['value'],
                    "sentiment": pref['sentiment'],
                    "strength": pref['strength'],
                    "priority": priority,
                    "is_system_rule": is_system_rule,
                    "technologies": pref['technologies'],
                    "context": pref['context_window'],
                    "source": "preference_detection_hook"
                }
            }

            queued_entries.append(interaction_entry)

            # If this should be a system rule, create a marker for enhanced-memory sync
            if is_system_rule:
                # Create entry that cross-memory-sync hook can pick up
                em_marker = {
                    "type": "system_rule_marker",
                    "name": f"rule_{pref['category']}_{timestamp}_{idx}",
                    "entityType": "system_rule",
                    "rule_text": pref['text'],
                    "rule_category": pref['category'],
                    "priority": priority,
                    "graphiti_interaction": interaction_entry["name"],
                    "timestamp": timestamp
                }

                # Write to enhanced-memory marker file
                em_marker_file = Path.home() / ".claude" / ".enhanced_memory_updates.txt"
                with open(em_marker_file, "a") as f:
                    f.write(json.dumps(em_marker) + "\n")

        # Write to Graphiti preference queue
        with open(GRAPHITI_PREFERENCE_QUEUE, "a") as f:
            for entry in queued_entries:
                f.write(json.dumps(entry) + "\n")

        log_preference_event("preferences_detected", {
            "count": len(unique_preferences),
            "categories": [p["category"] for p in unique_preferences],
            "priorities": [determine_preference_priority(p) for p in unique_preferences],
            "system_rules": len([p for p in unique_preferences if should_create_system_rule(p)]),
            "timestamp": timestamp
        })

        return True

    except Exception as e:
        log_preference_event("detection_error", {"error": str(e)})
        return False


def update_preference_statistics(detected):
    """Update preference detection statistics."""
    try:
        # Load existing stats
        if PREFERENCE_STATS_FILE.exists():
            with open(PREFERENCE_STATS_FILE, "r") as f:
                stats = json.load(f)
        else:
            stats = {
                "total_messages_processed": 0,
                "preferences_detected_count": 0,
                "last_detection": None,
                "detection_history": [],
                "category_counts": {}
            }

        # Update stats
        stats["total_messages_processed"] += 1
        if detected:
            stats["preferences_detected_count"] += 1
            stats["last_detection"] = datetime.now().isoformat()

        # Add to history (keep last 100)
        stats["detection_history"].append({
            "timestamp": datetime.now().isoformat(),
            "detected": detected
        })

        if len(stats["detection_history"]) > 100:
            stats["detection_history"] = stats["detection_history"][-100:]

        # Save stats
        with open(PREFERENCE_STATS_FILE, "w") as f:
            json.dump(stats, f, indent=2)

    except Exception as e:
        print(f"⚠️  Stats update error: {e}", file=sys.stderr)


def main():
    """
    Main hook execution.

    Detects user preferences and queues them for Graphiti storage.
    """
    try:
        # Read user message from stdin or environment
        # In Claude Code hooks, the user message might be passed differently
        # For now, we'll read from the session content file
        session_log = Path.home() / ".claude" / ".last_session_content.txt"

        if not session_log.exists():
            sys.exit(0)

        try:
            with open(session_log, "r") as f:
                session_content = f.read()
        except:
            session_content = ""

        if not session_content:
            sys.exit(0)

        # Try to extract just the user's latest message
        # This is simplified - in practice would need better parsing
        user_message = session_content

        # Detect and queue preferences
        detected = detect_and_queue_preferences(user_message)

        # Update statistics
        update_preference_statistics(detected)

        # Report status
        if detected:
            print("💭 User preferences detected")

        # Always exit 0 to continue (non-blocking hook)
        sys.exit(0)

    except Exception as e:
        print(f"Error in preference detection hook: {e}", file=sys.stderr)
        log_preference_event("hook_error", {"error": str(e)})
        sys.exit(0)  # Non-blocking


if __name__ == "__main__":
    main()

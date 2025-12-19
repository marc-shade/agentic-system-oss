#!/usr/bin/env python3
"""
Conversation Capture Hook - Automatic Graphiti Knowledge Graph Integration

Purpose: Automatically capture multi-turn conversations to Graphiti's temporal knowledge graph

Functionality:
1. Captures complete conversation turns (user + assistant)
2. Extracts entities and relationships automatically (via Graphiti's LLM)
3. Stores with bi-temporal context (occurrence + ingestion time)
4. Links to enhanced-memory system rules when detected

Trigger: post-response
Priority: 4 (after cross-memory-sync)
"""

import sys
import json
import re
from datetime import datetime
from pathlib import Path

# Configuration
GRAPHITI_CONVERSATION_QUEUE = Path.home() / ".claude" / ".graphiti_conversation_queue.jsonl"
CONVERSATION_LOG = Path.home() / ".claude" / ".conversation_capture.log"
CONVERSATION_STATS_FILE = Path.home() / ".claude" / ".conversation_stats.json"
MIN_CONVERSATION_LENGTH = 50  # Minimum characters to consider as meaningful


def log_capture_event(event_type, details):
    """Log capture events for debugging and monitoring."""
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "details": details
        }
        with open(CONVERSATION_LOG, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"⚠️  Logging error: {e}", file=sys.stderr)


def extract_conversation_metadata(text):
    """Extract metadata about the conversation for better categorization."""
    metadata = {
        "has_code": bool(re.search(r'```[\w]*\n', text)),
        "has_command": bool(re.search(r'\$\s+\w+|npm|python|git|uv', text)),
        "has_file_path": bool(re.search(r'/[\w/.-]+\.(py|js|ts|json|md)', text)),
        "has_url": bool(re.search(r'https?://[^\s]+', text)),
        "has_question": bool(re.search(r'\?', text)),
        "word_count": len(text.split()),
        "contains_error": bool(re.search(r'error|exception|failed|warning', text, re.IGNORECASE)),
        "contains_success": bool(re.search(r'success|completed|done|finished', text, re.IGNORECASE))
    }

    # Detect topic categories
    topics = []
    if re.search(r'\bmcp\b|\bserver\b|\btool\b', text, re.IGNORECASE):
        topics.append("mcp_development")
    if re.search(r'\bmemory\b|\bknowledge\b|\bgraph\b', text, re.IGNORECASE):
        topics.append("memory_system")
    if re.search(r'\bhook\b|\bintegration\b', text, re.IGNORECASE):
        topics.append("integration")
    if re.search(r'\btest\b|\bdebug\b|\berror\b', text, re.IGNORECASE):
        topics.append("debugging")

    metadata["topics"] = topics
    return metadata


def detect_conversation_importance(user_message, assistant_response):
    """Determine the importance level of a conversation."""
    # High importance indicators
    high_importance_patterns = [
        r'\bproduction\b',
        r'\bcritical\b',
        r'\bimportant\b',
        r'\bmust\b.*\b(have|do|implement)\b',
        r'\brequirement\b',
        r'\bpolicy\b',
        r'\balways\b.*\b(use|do|ensure)\b',
        r'\bnever\b.*\b(use|do|allow)\b',
    ]

    combined_text = f"{user_message} {assistant_response}"

    # Check for high importance
    for pattern in high_importance_patterns:
        if re.search(pattern, combined_text, re.IGNORECASE):
            return "high"

    # Check for questions (medium importance)
    if re.search(r'\?', user_message):
        return "medium"

    # Default to normal
    return "normal"


def extract_user_preferences(text):
    """Extract user preferences from conversation text."""
    preferences = []

    preference_patterns = [
        (r"I prefer ([^,.!?]+)", "preference"),
        (r"I want ([^,.!?]+)", "want"),
        (r"I like ([^,.!?]+)", "like"),
        (r"I need ([^,.!?]+)", "need"),
        (r"always (use|include|add|ensure) ([^,.!?]+)", "always_rule"),
        (r"never (use|include|add|allow) ([^,.!?]+)", "never_rule"),
    ]

    for pattern, pref_type in preference_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            preferences.append({
                "type": pref_type,
                "text": match.group(0),
                "extracted_value": match.group(1) if match.lastindex >= 1 else ""
            })

    return preferences


def split_into_turns(session_content):
    """Split session content into conversation turns."""
    # Try to detect conversation boundaries
    # This is a simplified version - real implementation would need better parsing
    turns = []

    # Simple split by common delimiters
    # In practice, the session content format would need to be known
    lines = session_content.split("\n")

    current_user_message = []
    current_assistant_response = []
    in_user = False
    in_assistant = False

    for line in lines:
        # Detect user/assistant markers (this is simplified)
        if line.startswith("User:") or line.startswith("Human:"):
            if current_assistant_response:
                turns.append({
                    "user": "\n".join(current_user_message),
                    "assistant": "\n".join(current_assistant_response)
                })
                current_user_message = []
                current_assistant_response = []
            in_user = True
            in_assistant = False
            current_user_message.append(line.replace("User:", "").replace("Human:", "").strip())
        elif line.startswith("Assistant:") or line.startswith("Claude:"):
            in_user = False
            in_assistant = True
            current_assistant_response.append(line.replace("Assistant:", "").replace("Claude:", "").strip())
        else:
            if in_user:
                current_user_message.append(line)
            elif in_assistant:
                current_assistant_response.append(line)

    # Add final turn if exists
    if current_user_message and current_assistant_response:
        turns.append({
            "user": "\n".join(current_user_message),
            "assistant": "\n".join(current_assistant_response)
        })

    return turns


def capture_conversation():
    """
    Capture conversation turns and queue them for Graphiti ingestion.

    Returns:
        bool: True if conversations were captured, False otherwise
    """
    try:
        # Check if this is a session with actual content
        session_log = Path.home() / ".claude" / ".last_session_content.txt"
        if not session_log.exists():
            return False

        # Read session content
        try:
            with open(session_log, "r") as f:
                session_content = f.read()
        except:
            session_content = ""

        # Only proceed if session had substantial content
        if len(session_content) < MIN_CONVERSATION_LENGTH:
            return False

        # Extract conversation turns
        turns = split_into_turns(session_content)

        if not turns:
            # If we can't split into turns, treat entire session as one conversation
            turns = [{
                "user": "Session content",
                "assistant": session_content
            }]

        # Queue each conversation turn for Graphiti ingestion
        conversations_queued = []
        timestamp = datetime.now().isoformat()

        for idx, turn in enumerate(turns):
            user_message = turn.get("user", "").strip()
            assistant_response = turn.get("assistant", "").strip()

            # Skip empty turns
            if not user_message and not assistant_response:
                continue

            # Skip very short exchanges
            if len(user_message) + len(assistant_response) < MIN_CONVERSATION_LENGTH:
                continue

            # Build conversation transcript
            conversation_transcript = f"User: {user_message}\n\nAssistant: {assistant_response}"

            # Extract metadata
            metadata = extract_conversation_metadata(conversation_transcript)
            importance = detect_conversation_importance(user_message, assistant_response)
            preferences = extract_user_preferences(user_message)

            # Create Graphiti conversation entry
            conversation_entry = {
                "type": "add_conversation",
                "name": f"Conversation_{timestamp}_{idx}",
                "conversation_transcript": conversation_transcript,
                "user_id": "marc_shade",
                "reference_time": timestamp,
                "metadata": {
                    **metadata,
                    "importance": importance,
                    "turn_number": idx,
                    "total_turns": len(turns),
                    "preferences_detected": len(preferences),
                    "source": "conversation_capture_hook"
                }
            }

            conversations_queued.append(conversation_entry)

            # If preferences were detected, create separate user interaction entries
            for pref in preferences:
                pref_entry = {
                    "type": "add_user_interaction",
                    "name": f"Preference_{pref['type']}_{timestamp}_{idx}",
                    "interaction_text": pref['text'],
                    "user_id": "marc_shade",
                    "reference_time": timestamp,
                    "source_description": f"auto_detected_preference_{pref['type']}",
                    "metadata": {
                        "preference_type": pref['type'],
                        "extracted_value": pref['extracted_value'],
                        "from_conversation": conversation_entry["name"]
                    }
                }
                conversations_queued.append(pref_entry)

        if not conversations_queued:
            return False

        # Write to Graphiti conversation queue
        with open(GRAPHITI_CONVERSATION_QUEUE, "a") as f:
            for entry in conversations_queued:
                f.write(json.dumps(entry) + "\n")

        log_capture_event("conversation_captured", {
            "turns_captured": len([e for e in conversations_queued if e["type"] == "add_conversation"]),
            "preferences_captured": len([e for e in conversations_queued if e["type"] == "add_user_interaction"]),
            "timestamp": timestamp
        })

        return True

    except Exception as e:
        log_capture_event("capture_error", {"error": str(e)})
        return False


def update_conversation_statistics(captured):
    """Update conversation capture statistics."""
    try:
        # Load existing stats
        if CONVERSATION_STATS_FILE.exists():
            with open(CONVERSATION_STATS_FILE, "r") as f:
                stats = json.load(f)
        else:
            stats = {
                "total_sessions": 0,
                "sessions_captured": 0,
                "last_capture": None,
                "capture_history": []
            }

        # Update stats
        stats["total_sessions"] += 1
        if captured:
            stats["sessions_captured"] += 1
            stats["last_capture"] = datetime.now().isoformat()

        # Add to history (keep last 100)
        stats["capture_history"].append({
            "timestamp": datetime.now().isoformat(),
            "captured": captured
        })

        if len(stats["capture_history"]) > 100:
            stats["capture_history"] = stats["capture_history"][-100:]

        # Save stats
        with open(CONVERSATION_STATS_FILE, "w") as f:
            json.dump(stats, f, indent=2)

    except Exception as e:
        print(f"⚠️  Stats update error: {e}", file=sys.stderr)


def main():
    """
    Main hook execution.

    Captures conversation turns and queues them for Graphiti ingestion.
    """
    try:
        # Capture conversations
        captured = capture_conversation()

        # Update statistics
        update_conversation_statistics(captured)

        # Report status
        if captured:
            print("📝 Conversation captured for Graphiti")

        # Always exit 0 to continue (non-blocking hook)
        sys.exit(0)

    except Exception as e:
        print(f"Error in conversation capture hook: {e}", file=sys.stderr)
        log_capture_event("hook_error", {"error": str(e)})
        sys.exit(0)  # Non-blocking


if __name__ == "__main__":
    main()

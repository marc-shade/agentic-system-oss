"""
Self-Healing System Monitor Handlers
Continuously monitors system health and auto-heals issues
"""
import json
import os
import time
import subprocess


def check_config_integrity(event):
    """Check settings.json integrity"""
    settings_path = os.path.expanduser("~/.claude/settings.json")

    try:
        with open(settings_path) as f:
            config = json.load(f)

        # Check critical keys
        issues = []

        if "statusLine" not in config:
            issues.append("statusLine missing")

        if "hooks" not in config:
            issues.append("hooks missing")
        elif "PreToolUse" not in config["hooks"]:
            issues.append("PreToolUse hook missing")
        elif "PostToolUse" not in config["hooks"]:
            issues.append("PostToolUse hook missing")

        return {
            "healthy": len(issues) == 0,
            "issues": issues,
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "healthy": False,
            "issues": [f"Config read error: {str(e)}"],
            "timestamp": time.time()
        }


def restore_config(event):
    """Restore config based on preservation rules"""
    issue_type = event.data.get("issue_type", "") if hasattr(event, "data") else ""

    preservation_path = os.path.expanduser("~/.claude/preservation_rules.json")
    settings_path = os.path.expanduser("~/.claude/settings.json")

    try:
        # Load preservation rules
        with open(preservation_path) as f:
            rules = json.load(f)

        # Load current settings
        with open(settings_path) as f:
            settings = json.load(f)

        # Find and apply expected value
        for rule in rules["always_preserve"]:
            if issue_type in rule["key"]:
                expected = rule.get("expected_value")
                if expected:
                    # Apply restoration
                    keys = rule["key"].split(".")
                    if len(keys) == 1:
                        settings[keys[0]] = expected
                    else:
                        settings[keys[0]][keys[1]] = expected

                    # Save restored config
                    with open(settings_path, 'w') as f:
                        json.dump(settings, f, indent=2)

                    return {
                        "restored": True,
                        "key": rule["key"],
                        "message": f"Restored {rule['key']}"
                    }

        return {
            "restored": False,
            "message": f"No restoration rule for {issue_type}"
        }
    except Exception as e:
        return {
            "restored": False,
            "error": str(e)
        }


def notify_via_voice(event):
    """Send voice notification via MCP"""
    message = event.data.get("message", "Notification") if hasattr(event, "data") else "Notification"

    try:
        # Use voice-mode MCP for notification
        # This would integrate with your voice MCP server
        return {
            "notified": True,
            "message": message
        }
    except Exception as e:
        return {
            "notified": False,
            "error": str(e)
        }

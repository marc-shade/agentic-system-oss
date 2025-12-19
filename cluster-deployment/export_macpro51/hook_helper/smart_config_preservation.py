#!/usr/bin/env python3
"""
Smart Configuration Preservation System
Uses AI to understand what configuration should be preserved across self-healing operations
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

class SmartConfigPreserver:
    """AI-powered configuration preservation that understands context"""

    def __init__(self):
        self.claude_home = Path.home() / ".claude"
        self.preservation_rules = self.load_preservation_rules()
        self.history = self.load_preservation_history()

    def load_preservation_rules(self) -> Dict[str, Any]:
        """Load rules for what to preserve and why"""
        rules_path = self.claude_home / "preservation_rules.json"

        default_rules = {
            "always_preserve": [
                {
                    "key": "statusLine",
                    "reason": "User-configured statusline (Ember integration)",
                    "priority": "critical",
                    "created_by": "user",
                    "context": "Phoenix conscience keeper system"
                },
                {
                    "key": "permissions.allow",
                    "reason": "Tool permissions learned over time",
                    "priority": "high",
                    "created_by": "system",
                    "context": "Self-modification learning"
                }
            ],
            "conditionally_preserve": [
                {
                    "key": "mcpServers",
                    "condition": "merge_not_replace",
                    "reason": "MCP servers can be healing OR user-added",
                    "priority": "high",
                    "strategy": "intelligent_merge"
                }
            ],
            "never_preserve": [
                {
                    "key": "temporary_*",
                    "reason": "Temporary configs should not persist",
                    "priority": "low"
                }
            ]
        }

        if not rules_path.exists():
            with open(rules_path, 'w') as f:
                json.dump(default_rules, f, indent=2)
            return default_rules

        with open(rules_path, 'r') as f:
            return json.load(f)

    def load_preservation_history(self) -> List[Dict]:
        """Load history of what's been preserved and why"""
        history_path = self.claude_home / "preservation_history.json"

        if not history_path.exists():
            return []

        with open(history_path, 'r') as f:
            return json.load(f)

    def should_preserve(self, key: str, value: Any, context: str = "") -> Dict[str, Any]:
        """
        AI-powered decision on whether to preserve a config value

        Returns:
            {
                "preserve": bool,
                "reason": str,
                "strategy": str,  # "keep", "merge", "replace"
                "confidence": float
            }
        """
        # Check always preserve rules
        for rule in self.preservation_rules.get("always_preserve", []):
            if key == rule["key"] or self._key_matches_pattern(key, rule["key"]):
                return {
                    "preserve": True,
                    "reason": rule["reason"],
                    "strategy": "keep",
                    "confidence": 1.0,
                    "context": rule.get("context", "")
                }

        # Check conditional preservation
        for rule in self.preservation_rules.get("conditionally_preserve", []):
            if key == rule["key"]:
                return self._evaluate_conditional_rule(rule, value, context)

        # Check never preserve
        for rule in self.preservation_rules.get("never_preserve", []):
            if self._key_matches_pattern(key, rule["key"]):
                return {
                    "preserve": False,
                    "reason": rule["reason"],
                    "strategy": "replace",
                    "confidence": 1.0
                }

        # Unknown config - preserve by default (safety first)
        return {
            "preserve": True,
            "reason": "Unknown config, preserving for safety",
            "strategy": "keep",
            "confidence": 0.7
        }

    def _key_matches_pattern(self, key: str, pattern: str) -> bool:
        """Check if key matches a pattern with wildcards"""
        if "*" in pattern:
            prefix = pattern.replace("*", "")
            return key.startswith(prefix)
        return key == pattern

    def _evaluate_conditional_rule(self, rule: Dict, value: Any, context: str) -> Dict[str, Any]:
        """Evaluate conditional preservation rules"""
        condition = rule.get("condition")
        strategy = rule.get("strategy", "keep")

        if condition == "merge_not_replace":
            # For MCP servers, we want to merge healing + user configs
            return {
                "preserve": True,
                "reason": f"{rule['reason']} - using merge strategy",
                "strategy": "intelligent_merge",
                "confidence": 0.9
            }

        # Default to preservation
        return {
            "preserve": True,
            "reason": rule["reason"],
            "strategy": strategy,
            "confidence": 0.8
        }

    def merge_configs(self, existing: Dict, new: Dict, context: str = "") -> Dict:
        """
        Intelligently merge configurations
        Preserves user configs while applying healing changes
        """
        merged = {}
        all_keys = set(existing.keys()) | set(new.keys())

        preservation_log = []

        for key in all_keys:
            existing_val = existing.get(key)
            new_val = new.get(key)

            # Get AI decision on preservation
            decision = self.should_preserve(
                key,
                existing_val,
                context=f"Merging configs: {context}"
            )

            preservation_log.append({
                "key": key,
                "decision": decision,
                "timestamp": datetime.now().isoformat()
            })

            if decision["strategy"] == "keep" and existing_val is not None:
                merged[key] = existing_val

            elif decision["strategy"] == "intelligent_merge":
                if isinstance(existing_val, dict) and isinstance(new_val, dict):
                    # Recursive merge for nested dicts
                    merged[key] = self._deep_merge(existing_val, new_val)
                else:
                    merged[key] = new_val if new_val is not None else existing_val

            elif decision["strategy"] == "replace":
                merged[key] = new_val if new_val is not None else existing_val

            else:
                # Default: prefer existing
                merged[key] = existing_val if existing_val is not None else new_val

        # Log preservation decisions
        self._log_preservation(preservation_log, context)

        return merged

    def _deep_merge(self, dict1: Dict, dict2: Dict) -> Dict:
        """Deep merge two dictionaries, preserving nested structure"""
        result = dict1.copy()

        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                # New key or non-dict value - add it
                result[key] = value

        return result

    def _log_preservation(self, decisions: List[Dict], context: str):
        """Log preservation decisions for learning"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "decisions": decisions
        }

        self.history.append(log_entry)

        # Save to file
        history_path = self.claude_home / "preservation_history.json"
        with open(history_path, 'w') as f:
            json.dump(self.history[-100:], f, indent=2)  # Keep last 100

    def add_preservation_rule(self, key: str, reason: str, priority: str = "high",
                            created_by: str = "user", context: str = ""):
        """Add a new preservation rule dynamically"""
        new_rule = {
            "key": key,
            "reason": reason,
            "priority": priority,
            "created_by": created_by,
            "context": context,
            "added_at": datetime.now().isoformat()
        }

        self.preservation_rules["always_preserve"].append(new_rule)

        # Save updated rules
        rules_path = self.claude_home / "preservation_rules.json"
        with open(rules_path, 'w') as f:
            json.dump(self.preservation_rules, f, indent=2)

# Global instance
preserver = SmartConfigPreserver()

def preserve_and_merge(existing_config: Dict, new_config: Dict, context: str = "") -> Dict:
    """
    Main entry point for smart config preservation

    Usage:
        merged = preserve_and_merge(existing, new, "MCP healing operation")
    """
    return preserver.merge_configs(existing_config, new_config, context)

def add_preservation_rule(key: str, reason: str, **kwargs):
    """Add a new preservation rule"""
    preserver.add_preservation_rule(key, reason, **kwargs)

__all__ = ['preserve_and_merge', 'add_preservation_rule', 'SmartConfigPreserver']

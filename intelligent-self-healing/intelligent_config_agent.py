#!/usr/bin/env python3
"""
Intelligent Configuration Self-Healing Agent
Uses Claude Agent SDK for intelligent decision-making about configuration changes

This replaces dumb bash scripts with an AI agent that can:
- Reason about configuration changes
- Understand user intent vs system errors
- Ask for clarification when uncertain
- Learn from past decisions
- Provide explanations for actions taken
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import difflib
import anthropic

# Add parent directory to path for imports
sys.path.insert(0, str(Path.home() / ".claude" / "hooks"))

try:
    from smart_config_preservation import SmartConfigPreserver
except (ImportError, Exception) as e:
    # Catch any error including JSON decode errors in module init
    print(f"⚠️  Could not import SmartConfigPreserver: {e}")
    SmartConfigPreserver = None


class IntelligentConfigAgent:
    """AI-powered configuration agent using Claude for intelligent decisions"""

    def __init__(self, api_key: Optional[str] = None):
        self.claude_home = Path.home() / ".claude"
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY required for intelligent agent")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"  # Haiku 4.5 for fast decisions

        # Decision memory stored in enhanced-memory MCP
        self.decision_log_path = self.claude_home / "intelligent_healing_decisions.jsonl"
        self.config_snapshot_path = self.claude_home / "config_snapshots"
        self.config_snapshot_path.mkdir(exist_ok=True)

        # Legacy preserver for rule-based fallback
        self.legacy_preserver = SmartConfigPreserver() if SmartConfigPreserver else None

    def analyze_config_change(
        self,
        config_key: str,
        old_value: Any,
        new_value: Any,
        change_source: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Use Claude to analyze if a config change is intentional or an error

        Returns:
            {
                "is_intentional": bool,
                "confidence": float,
                "reasoning": str,
                "recommendation": str,  # "keep_new", "restore_old", "ask_user"
                "context": str
            }
        """

        # Create a detailed prompt for Claude
        prompt = self._build_analysis_prompt(config_key, old_value, new_value, change_source)

        # Get similar past decisions from memory
        past_decisions = self._get_relevant_past_decisions(config_key)

        if past_decisions:
            prompt += f"\n\nRelevant past decisions:\n{json.dumps(past_decisions, indent=2)}"

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse Claude's response
            analysis = self._parse_analysis_response(response.content[0].text)

            # Log decision for future learning
            self._log_decision(config_key, old_value, new_value, analysis, change_source)

            return analysis

        except Exception as e:
            print(f"⚠️  Claude analysis failed: {e}")
            # Fallback to legacy rule-based system
            if self.legacy_preserver:
                decision = self.legacy_preserver.should_preserve(config_key, old_value)
                return {
                    "is_intentional": not decision["preserve"],
                    "confidence": decision["confidence"],
                    "reasoning": f"Fallback to rule-based: {decision['reason']}",
                    "recommendation": "keep_new" if not decision["preserve"] else "restore_old",
                    "context": "rule_based_fallback"
                }

            # Ultra-safe fallback: preserve old config
            return {
                "is_intentional": False,
                "confidence": 0.5,
                "reasoning": "Analysis failed, preserving old config for safety",
                "recommendation": "restore_old",
                "context": "error_fallback"
            }

    def _build_analysis_prompt(
        self,
        config_key: str,
        old_value: Any,
        new_value: Any,
        change_source: str
    ) -> str:
        """Build detailed prompt for Claude to analyze config change"""

        # Get diff of changes
        if isinstance(old_value, (dict, list)):
            old_str = json.dumps(old_value, indent=2)
            new_str = json.dumps(new_value, indent=2)
        else:
            old_str = str(old_value)
            new_str = str(new_value)

        diff = list(difflib.unified_diff(
            old_str.splitlines(),
            new_str.splitlines(),
            lineterm='',
            n=3
        ))
        diff_str = '\n'.join(diff) if diff else "No diff available"

        return f"""You are an intelligent configuration watchdog for an agentic AI system.

Analyze this configuration change and determine if it's intentional (user-made) or an error (system corruption).

Configuration Key: {config_key}
Change Source: {change_source}

Old Value:
{old_str}

New Value:
{new_str}

Diff:
{diff_str}

Context:
- This is Marc's autonomous agentic system
- Configuration changes can come from:
  1. Marc explicitly modifying files
  2. Self-healing scripts that may be overzealous
  3. System corruption or bugs
  4. Agent self-modification (which is allowed)

Your task:
1. Analyze if this change appears intentional or accidental
2. Consider the configuration key name and what it controls
3. Look at the nature of the change (is it a meaningful update or random corruption?)
4. Provide a recommendation

Respond in JSON format:
{{
  "is_intentional": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "detailed explanation of your analysis",
  "recommendation": "keep_new" | "restore_old" | "ask_user",
  "red_flags": ["list", "of", "concerns", "if", "any"],
  "context": "brief context summary"
}}

Be thoughtful and explain your reasoning clearly."""

    def _parse_analysis_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude's JSON response"""
        try:
            # Try to extract JSON from response
            # Claude sometimes wraps JSON in markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
            else:
                json_str = response_text.strip()

            analysis = json.loads(json_str)

            # Ensure required fields exist
            required = ["is_intentional", "confidence", "reasoning", "recommendation"]
            if not all(field in analysis for field in required):
                raise ValueError(f"Missing required fields in analysis: {required}")

            return analysis

        except Exception as e:
            print(f"⚠️  Failed to parse Claude response: {e}")
            print(f"Response was: {response_text[:500]}")

            # Return safe default
            return {
                "is_intentional": False,
                "confidence": 0.3,
                "reasoning": f"Failed to parse analysis: {e}",
                "recommendation": "ask_user",
                "context": "parse_error"
            }

    def _get_relevant_past_decisions(self, config_key: str, limit: int = 5) -> List[Dict]:
        """Get past decisions for similar config keys"""
        if not self.decision_log_path.exists():
            return []

        relevant = []
        try:
            with open(self.decision_log_path, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue

                    decision = json.loads(line)
                    # Match exact key or similar keys
                    if decision["config_key"] == config_key or config_key in decision["config_key"]:
                        relevant.append(decision)

                    if len(relevant) >= limit:
                        break
        except Exception as e:
            print(f"⚠️  Failed to load past decisions: {e}")

        return relevant

    def _log_decision(
        self,
        config_key: str,
        old_value: Any,
        new_value: Any,
        analysis: Dict[str, Any],
        change_source: str
    ):
        """Log decision to JSONL file for learning"""
        decision_record = {
            "timestamp": datetime.now().isoformat(),
            "config_key": config_key,
            "old_value": str(old_value)[:200],  # Truncate for log
            "new_value": str(new_value)[:200],
            "change_source": change_source,
            "analysis": analysis,
            "action_taken": None  # Will be updated after action
        }

        try:
            with open(self.decision_log_path, 'a') as f:
                f.write(json.dumps(decision_record) + '\n')
        except Exception as e:
            print(f"⚠️  Failed to log decision: {e}")

    def snapshot_config(self, config_path: Path, label: str = "auto") -> str:
        """Take a snapshot of configuration file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            snapshot_name = f"{config_path.stem}_{label}_{timestamp}.json"
            snapshot_path = self.config_snapshot_path / snapshot_name

            with open(config_path, 'r') as f:
                config = json.load(f)

            with open(snapshot_path, 'w') as f:
                json.dump(config, f, indent=2)

            return str(snapshot_path)

        except Exception as e:
            print(f"⚠️  Failed to snapshot config: {e}")
            return ""

    def intelligent_heal_config(
        self,
        config_path: Path,
        expected_values: Dict[str, Any],
        change_source: str = "healing_script"
    ) -> Dict[str, Any]:
        """
        Intelligently heal configuration file

        Instead of blindly restoring values, use AI to decide what to do

        Returns:
            {
                "changes_made": List[str],
                "changes_skipped": List[str],
                "user_confirmations_needed": List[Dict]
            }
        """

        # Take snapshot before healing
        snapshot = self.snapshot_config(config_path, "before_heal")

        # Load current config
        try:
            with open(config_path, 'r') as f:
                current_config = json.load(f)
        except Exception as e:
            print(f"❌ Failed to load config: {e}")
            return {"error": str(e)}

        results = {
            "changes_made": [],
            "changes_skipped": [],
            "user_confirmations_needed": [],
            "snapshot": snapshot
        }

        # Analyze each expected value
        for key, expected_value in expected_values.items():
            current_value = self._get_nested_value(current_config, key)

            # Skip if already correct
            if current_value == expected_value:
                continue

            # Use AI to analyze the change
            analysis = self.analyze_config_change(
                config_key=key,
                old_value=current_value,
                new_value=expected_value,
                change_source=change_source
            )

            # Decide action based on AI analysis
            if analysis["recommendation"] == "keep_new" or (
                analysis["recommendation"] == "restore_old" and analysis["confidence"] > 0.8
            ):
                # High confidence - make the change
                self._set_nested_value(current_config, key, expected_value)
                results["changes_made"].append({
                    "key": key,
                    "from": str(current_value)[:100],
                    "to": str(expected_value)[:100],
                    "reasoning": analysis["reasoning"],
                    "confidence": analysis["confidence"]
                })

            elif analysis["recommendation"] == "ask_user" or analysis["confidence"] < 0.6:
                # Low confidence - ask user
                results["user_confirmations_needed"].append({
                    "key": key,
                    "current_value": current_value,
                    "proposed_value": expected_value,
                    "analysis": analysis
                })

            else:
                # Skip this change
                results["changes_skipped"].append({
                    "key": key,
                    "reasoning": analysis["reasoning"],
                    "confidence": analysis["confidence"]
                })

        # Write updated config if changes were made
        if results["changes_made"]:
            try:
                with open(config_path, 'w') as f:
                    json.dump(current_config, f, indent=2)

                # Take snapshot after healing
                after_snapshot = self.snapshot_config(config_path, "after_heal")
                results["after_snapshot"] = after_snapshot

            except Exception as e:
                print(f"❌ Failed to write healed config: {e}")
                results["error"] = str(e)

        return results

    def _get_nested_value(self, config: Dict, key: str) -> Any:
        """Get value from nested dict using dot notation (e.g., 'statusLine.command')"""
        parts = key.split('.')
        value = config

        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None

        return value

    def _set_nested_value(self, config: Dict, key: str, value: Any):
        """Set value in nested dict using dot notation"""
        parts = key.split('.')
        target = config

        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]

        target[parts[-1]] = value

    # ===== PHASE 1: AGENTIC MODIFICATION MARKERS =====

    def mark_agentic_change(
        self,
        file: str,
        key: str,
        reason: str,
        change_type: str = "agentic_optimization",
        confidence: float = 0.95,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mark a configuration change as intentional agentic modification

        This allows the agentic system to signal that changes are intentional,
        preventing the watchdog from rolling them back.

        Args:
            file: Config file name (e.g., "settings.json")
            key: Config key modified (e.g., "maxTokens")
            reason: Human-readable reason for change
            change_type: Type of modification (default: "agentic_optimization")
            confidence: Confidence in this change (0.0-1.0)
            session_id: Optional session/workflow identifier

        Returns:
            Dictionary with marker details
        """
        marker_file = self.claude_home / ".config_modifications.jsonl"

        marker = {
            "timestamp": datetime.now().isoformat(),
            "file": file,
            "key": key,
            "change_type": change_type,
            "reason": reason,
            "confidence": confidence,
            "session_id": session_id
        }

        # Append to marker file
        with open(marker_file, 'a') as f:
            f.write(json.dumps(marker) + '\n')

        print(f"✅ Marked agentic change: {file}:{key}")
        print(f"   Reason: {reason}")
        print(f"   Confidence: {confidence:.1%}")

        return marker

    def check_agentic_marker(
        self,
        file: str,
        key: str,
        max_age_hours: int = 24
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a configuration change was marked by agentic system

        Args:
            file: Config file name to check
            key: Config key to check
            max_age_hours: Maximum age of marker to consider (default: 24 hours)

        Returns:
            Marker dict if found, None otherwise
        """
        marker_file = self.claude_home / ".config_modifications.jsonl"

        if not marker_file.exists():
            return None

        # Calculate cutoff time
        cutoff = datetime.now().timestamp() - (max_age_hours * 60 * 60)

        # Read markers in reverse (most recent first)
        try:
            with open(marker_file, 'r') as f:
                lines = f.readlines()

            for line in reversed(lines):
                try:
                    marker = json.loads(line.strip())

                    # Parse timestamp
                    marker_time = datetime.fromisoformat(marker['timestamp']).timestamp()

                    # Skip old markers
                    if marker_time < cutoff:
                        continue

                    # Check if this marker matches
                    if marker['file'] == file and marker['key'] == key:
                        return marker

                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

        except Exception as e:
            print(f"⚠️  Error reading markers: {e}")

        return None

    # ===== PHASE 2: TRUST LEVELS =====

    TRUST_LEVELS = {
        "agentic_optimization": {
            "trust": 0.95,
            "requires_analysis": False,
            "notify_only": True,
            "auto_heal_threshold": None  # Never auto-heal
        },
        "agentic_learning": {
            "trust": 0.90,
            "requires_analysis": False,
            "notify_only": True,
            "auto_heal_threshold": None
        },
        "user_edit": {
            "trust": 0.85,
            "requires_analysis": True,
            "notify_only": False,
            "auto_heal_threshold": 0.85  # Higher threshold for user changes
        },
        "session_start_check": {
            "trust": 0.50,
            "requires_analysis": True,
            "notify_only": False,
            "auto_heal_threshold": 0.70  # Normal threshold
        },
        "system_boot": {
            "trust": 0.30,
            "requires_analysis": True,
            "notify_only": False,
            "auto_heal_threshold": 0.60  # Lower threshold (more sensitive)
        }
    }

    # ===== PHASE 4: ALLOWLIST/BLOCKLIST =====

    AGENTIC_MODIFIABLE_KEYS = {
        # Performance optimization
        "maxTokens",
        "contextWindow",
        "parallelToolCalls",
        "maxParallelTools",

        # Memory management
        "memoryTiers",
        "cachingStrategy",
        "compressionLevel",

        # MCP server tuning (not adding/removing servers)
        "mcpServers.*.priority",
        "mcpServers.*.timeout",
        "mcpServers.*.retries",

        # Learning parameters
        "learningRate",
        "explorationFactor",
        "optimizationLevel",

        # System parameters
        "loggingLevel",
        "metricsCollection",
        "debugMode"
    }

    PROTECTED_KEYS = {
        # Core configuration (never auto-modify)
        "statusLine.command",
        "statusLine.type",

        # Hooks (critical for system integrity)
        "hooks.PreToolUse.path",
        "hooks.PostToolUse.path",
        "hooks.SessionStart.path",
        "hooks.*.path",

        # Security
        "apiKeys.*",
        "credentials.*",
        "ANTHROPIC_API_KEY",

        # MCP server structure (can tune parameters, not structure)
        "mcpServers.*.command",
        "mcpServers.*.args",

        # Permissions
        "permissions.*",
        "bypassPermissions"
    }

    def is_key_modifiable(self, key: str) -> Tuple[bool, str]:
        """
        Check if a config key can be modified by agentic system

        Args:
            key: Config key to check (dot notation)

        Returns:
            (is_modifiable, reason)
        """
        # Check protected keys first (explicit deny)
        for protected_pattern in self.PROTECTED_KEYS:
            if self._key_matches_pattern(key, protected_pattern):
                return False, f"Protected key: {protected_pattern}"

        # Check allowlist (explicit allow)
        for allowed_pattern in self.AGENTIC_MODIFIABLE_KEYS:
            if self._key_matches_pattern(key, allowed_pattern):
                return True, f"Allowlisted key: {allowed_pattern}"

        # Default: requires user approval
        return False, "Not in allowlist, requires user approval"

    def _key_matches_pattern(self, key: str, pattern: str) -> bool:
        """Check if key matches pattern (supports * wildcard)"""
        if pattern == key:
            return True

        if '*' not in pattern:
            return False

        # Convert pattern to regex
        import re
        regex = pattern.replace('.', '\\.').replace('*', '[^.]+')
        return bool(re.match(f"^{regex}$", key))

    # ===== PHASE 3: NOTIFICATION SYSTEM =====

    def notify_change(
        self,
        change_info: Dict[str, Any],
        severity: str = "info",
        use_voice: bool = True
    ):
        """
        Notify about configuration change without blocking

        Args:
            change_info: Dictionary with change details
            severity: Notification severity (info, warning, error)
            use_voice: Whether to use voice notification
        """
        notification_log = self.claude_home / ".config_notifications.jsonl"

        notification = {
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "details": change_info
        }

        # Log notification
        with open(notification_log, 'a') as f:
            f.write(json.dumps(notification) + '\n')

        # Voice notification if available and requested
        if use_voice:
            try:
                import subprocess
                message = f"Configuration optimized: {change_info.get('reason', 'unknown reason')}"

                # Try voice-mode converse (don't wait for response)
                subprocess.run([
                    "python3", "-c",
                    f"from voice_mode_client import converse; converse('{message}', wait_for_response=False)"
                ], timeout=5, capture_output=True, text=True)
            except Exception:
                pass  # Silent fail if voice not available


def main():
    """CLI interface for intelligent config healing"""
    import argparse

    parser = argparse.ArgumentParser(description="Intelligent Configuration Self-Healing Agent")
    parser.add_argument("action", choices=["heal", "analyze", "snapshot"])
    parser.add_argument("--config", type=str, help="Config file path")
    parser.add_argument("--key", type=str, help="Config key to analyze")
    parser.add_argument("--old", type=str, help="Old value")
    parser.add_argument("--new", type=str, help="New value")

    args = parser.parse_args()

    agent = IntelligentConfigAgent()

    if args.action == "analyze" and args.key:
        # Analyze a specific change
        analysis = agent.analyze_config_change(
            config_key=args.key,
            old_value=args.old,
            new_value=args.new,
            change_source="manual_test"
        )
        print(json.dumps(analysis, indent=2))

    elif args.action == "snapshot" and args.config:
        # Take a snapshot
        snapshot_path = agent.snapshot_config(Path(args.config), "manual")
        print(f"✅ Snapshot saved: {snapshot_path}")

    elif args.action == "heal" and args.config:
        # Heal a config file
        # Would need to specify expected values
        print("Healing not yet implemented in CLI")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

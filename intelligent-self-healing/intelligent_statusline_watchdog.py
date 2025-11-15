#!/usr/bin/env python3
"""
Intelligent StatusLine Watchdog
Uses AI agent to decide whether statusline changes are intentional or need healing

Replaces the dumb bash script (statusline-watchdog.sh) with intelligent reasoning
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Import the intelligent agent
sys.path.insert(0, str(Path(__file__).parent))
from intelligent_config_agent import IntelligentConfigAgent


class IntelligentStatusLineWatchdog:
    """AI-powered statusline watchdog"""

    def __init__(self):
        self.claude_home = Path.home() / ".claude"
        self.settings_json = self.claude_home / "settings.json"
        self.settings_local = self.claude_home / "settings.local.json"
        self.preservation_rules = self.claude_home / "preservation_rules.json"

        # Initialize intelligent agent
        try:
            self.agent = IntelligentConfigAgent()
            self.use_intelligent_mode = True
        except Exception as e:
            print(f"⚠️  Intelligent agent unavailable: {e}")
            print(f"⚠️  Falling back to rule-based mode")
            self.agent = None
            self.use_intelligent_mode = False

        # Load expected statusline config
        self.expected_statusline = self.load_expected_statusline()

    def load_expected_statusline(self) -> Dict[str, Any]:
        """Load what the statusline should be from preservation rules"""
        if not self.preservation_rules.exists():
            # Default to agentic statusline
            return {
                "type": "command",
                "command": "/Users/marc/.claude/agentic-statusline.sh",
                "padding": 0
            }

        try:
            with open(self.preservation_rules, 'r') as f:
                rules = json.load(f)
                return rules.get("statusLine", {})
        except Exception as e:
            print(f"⚠️  Failed to load preservation rules: {e}")
            return {}

    def check_and_heal_config(self, config_path: Path) -> Dict[str, Any]:
        """
        Check if statusline config is correct and heal if needed

        Returns:
            {
                "status": "ok" | "healed" | "needs_confirmation" | "error",
                "details": str,
                "changes": List[Dict],
                "confirmations_needed": List[Dict]
            }
        """

        if not config_path.exists():
            return {
                "status": "error",
                "details": f"Config file not found: {config_path}",
                "changes": [],
                "confirmations_needed": []
            }

        # Load current config
        try:
            with open(config_path, 'r') as f:
                current_config = json.load(f)
        except json.JSONDecodeError as e:
            # JSON corruption detected - restore expected config
            print(f"\n❌ JSON corruption detected in {config_path.name}: {e}")
            print(f"🔧 Restoring expected configuration...")

            # Create valid config with expected statusline
            restored_config = {
                "statusLine": self.expected_statusline
            }

            try:
                # Take snapshot of corrupted file first
                if self.agent:
                    snapshot = self.agent.snapshot_config(config_path, "before_corruption_heal")
                    print(f"   Snapshot: {snapshot}")

                # Write restored config
                with open(config_path, 'w') as f:
                    json.dump(restored_config, f, indent=2)

                print(f"✅ Configuration restored from corruption")

                return {
                    "status": "healed",
                    "details": f"JSON corruption detected and repaired: {e}",
                    "changes": [{
                        "key": "entire_file",
                        "from": "corrupted_json",
                        "to": "restored_config",
                        "reasoning": "JSON decode error indicates file corruption",
                        "confidence": 1.0
                    }],
                    "confirmations_needed": []
                }

            except Exception as write_error:
                print(f"❌ Failed to restore config: {write_error}")
                return {
                    "status": "error",
                    "details": f"Failed to restore corrupted config: {write_error}",
                    "changes": [],
                    "confirmations_needed": []
                }

        except Exception as e:
            return {
                "status": "error",
                "details": f"Failed to load config: {e}",
                "changes": [],
                "confirmations_needed": []
            }

        current_statusline = current_config.get("statusLine", {})

        # Check if statusline matches expected
        if current_statusline == self.expected_statusline:
            return {
                "status": "ok",
                "details": f"StatusLine correct in {config_path.name}",
                "changes": [],
                "confirmations_needed": []
            }

        # StatusLine differs - use intelligent agent to decide what to do
        if self.use_intelligent_mode and self.agent:
            return self._intelligent_heal(config_path, current_config, current_statusline)
        else:
            return self._rule_based_heal(config_path, current_config, current_statusline)

    def _intelligent_heal(
        self,
        config_path: Path,
        current_config: Dict,
        current_statusline: Dict
    ) -> Dict[str, Any]:
        """Use AI agent to intelligently decide what to do"""

        print(f"\n🤖 Analyzing statusline change in {config_path.name}...")

        # PHASE 1: Check for agentic modification marker first
        marker = self.agent.check_agentic_marker(
            file=config_path.name,
            key="statusLine",
            ***REMOVED***
        )

        if marker:
            print(f"\n✅ Agentic modification detected:")
            print(f"   Reason: {marker['reason']}")
            print(f"   Confidence: {marker['confidence']:.1%}")
            print(f"   Time: {marker['timestamp']}")
            print(f"   Type: {marker['change_type']}")

            # Get trust level for this change type
            from intelligent_config_agent import TRUST_LEVELS
            trust_info = TRUST_LEVELS.get(marker['change_type'], TRUST_LEVELS['session_start_check'])

            if trust_info['notify_only']:
                # Notification only - don't heal
                print(f"   Action: Notification only (trusted change)")

                # Notify about the change
                self.agent.notify_change(
                    change_info={
                        "file": config_path.name,
                        "key": "statusLine",
                        "reason": marker['reason'],
                        "marker": marker
                    },
                    severity="info",
                    use_voice=False  # Don't spam voice for every check
                )

                return {
                    "status": "ok",
                    "details": f"Agentic modification: {marker['reason']}",
                    "changes": [],
                    "confirmations_needed": []
                }

            else:
                # Requires analysis even with marker
                print(f"   Action: Proceeding with analysis (trust level requires verification)")

        # PHASE 2: No marker or marker requires analysis - proceed with AI analysis
        # Analyze the change
        analysis = self.agent.analyze_config_change(
            config_key="statusLine",
            old_value=current_statusline,
            new_value=self.expected_statusline,
            change_source="statusline_watchdog"
        )

        print(f"\n📊 Analysis:")
        print(f"  Is Intentional: {analysis['is_intentional']}")
        print(f"  Confidence: {analysis['confidence']:.1%}")
        print(f"  Reasoning: {analysis['reasoning']}")
        print(f"  Recommendation: {analysis['recommendation']}")

        if analysis.get("red_flags"):
            print(f"  ⚠️  Red Flags: {', '.join(analysis['red_flags'])}")

        # Decide action based on AI analysis
        if analysis["recommendation"] == "restore_old" and analysis["confidence"] > 0.7:
            # High confidence that we should restore - do it
            print(f"\n🔧 Restoring agentic statusline (confidence: {analysis['confidence']:.1%})")

            # Take snapshot before change
            snapshot = self.agent.snapshot_config(config_path, "before_watchdog_restore")

            # Update config
            current_config["statusLine"] = self.expected_statusline

            try:
                with open(config_path, 'w') as f:
                    json.dump(current_config, f, indent=2)

                print(f"✅ Agentic statusline restored")
                print(f"   Snapshot: {snapshot}")

                return {
                    "status": "healed",
                    "details": analysis['reasoning'],
                    "changes": [{
                        "key": "statusLine",
                        "from": str(current_statusline),
                        "to": str(self.expected_statusline),
                        "reasoning": analysis['reasoning'],
                        "confidence": analysis['confidence']
                    }],
                    "confirmations_needed": []
                }

            except Exception as e:
                print(f"❌ Failed to write config: {e}")
                return {
                    "status": "error",
                    "details": f"Failed to write config: {e}",
                    "changes": [],
                    "confirmations_needed": []
                }

        elif analysis["recommendation"] == "keep_new" or analysis["is_intentional"]:
            # AI thinks the change is intentional - don't restore
            print(f"\n✅ Change appears intentional, leaving as-is")
            print(f"   Current: {current_statusline.get('command', 'N/A')}")

            return {
                "status": "ok",
                "details": f"Change appears intentional: {analysis['reasoning']}",
                "changes": [],
                "confirmations_needed": []
            }

        else:
            # Low confidence - ask user
            print(f"\n❓ Low confidence ({analysis['confidence']:.1%}) - user confirmation needed")

            return {
                "status": "needs_confirmation",
                "details": analysis['reasoning'],
                "changes": [],
                "confirmations_needed": [{
                    "key": "statusLine",
                    "current_value": current_statusline,
                    "proposed_value": self.expected_statusline,
                    "analysis": analysis
                }]
            }

    def _rule_based_heal(
        self,
        config_path: Path,
        current_config: Dict,
        current_statusline: Dict
    ) -> Dict[str, Any]:
        """Fallback to simple rule-based healing"""

        print(f"\n🔧 Rule-based healing (intelligent agent unavailable)")
        print(f"   Restoring agentic statusline in {config_path.name}")

        # Simple: always restore expected statusline
        current_config["statusLine"] = self.expected_statusline

        try:
            with open(config_path, 'w') as f:
                json.dump(current_config, f, indent=2)

            print(f"✅ Agentic statusline restored (rule-based)")

            return {
                "status": "healed",
                "details": "Rule-based restoration (no AI)",
                "changes": [{
                    "key": "statusLine",
                    "from": str(current_statusline),
                    "to": str(self.expected_statusline),
                    "reasoning": "Rule-based: always restore expected statusline",
                    "confidence": 0.8
                }],
                "confirmations_needed": []
            }

        except Exception as e:
            print(f"❌ Failed to write config: {e}")
            return {
                "status": "error",
                "details": f"Failed to write config: {e}",
                "changes": [],
                "confirmations_needed": []
            }

    def run_watchdog(self) -> Dict[str, Any]:
        """Main watchdog execution"""

        print("=" * 60)
        if self.use_intelligent_mode:
            print("🤖 Intelligent StatusLine Watchdog (AI-Powered)")
        else:
            print("🤖 StatusLine Watchdog (Rule-Based Fallback)")
        print("=" * 60)

        results = {
            "timestamp": datetime.now().isoformat(),
            "mode": "intelligent" if self.use_intelligent_mode else "rule_based",
            "configs_checked": [],
            "total_healed": 0,
            "total_confirmations_needed": 0
        }

        # Check settings.json
        settings_result = self.check_and_heal_config(self.settings_json)
        results["configs_checked"].append({
            "file": "settings.json",
            "result": settings_result
        })

        if settings_result["status"] == "healed":
            results["total_healed"] += 1
        elif settings_result["status"] == "needs_confirmation":
            results["total_confirmations_needed"] += len(settings_result["confirmations_needed"])

        # Check settings.local.json if it exists
        if self.settings_local.exists():
            local_result = self.check_and_heal_config(self.settings_local)
            results["configs_checked"].append({
                "file": "settings.local.json",
                "result": local_result
            })

            if local_result["status"] == "healed":
                results["total_healed"] += 1
            elif local_result["status"] == "needs_confirmation":
                results["total_confirmations_needed"] += len(local_result["confirmations_needed"])

        # Verify statusline script exists and is executable
        statusline_script = Path(self.expected_statusline.get("command", ""))
        if statusline_script.exists():
            if not statusline_script.is_file():
                print(f"\n⚠️  StatusLine is not a file: {statusline_script}")
            elif not os.access(statusline_script, os.X_OK):
                print(f"\n🔧 Making statusline script executable")
                statusline_script.chmod(0o755)
                print(f"✅ Script is now executable")
        else:
            print(f"\n❌ StatusLine script not found: {statusline_script}")

        # Summary
        print("\n" + "=" * 60)
        print(f"📊 Watchdog Summary")
        print("=" * 60)
        print(f"Configs checked: {len(results['configs_checked'])}")
        print(f"Configs healed: {results['total_healed']}")
        print(f"Confirmations needed: {results['total_confirmations_needed']}")

        if results['total_confirmations_needed'] > 0:
            print("\n⚠️  Some changes need user confirmation:")
            for config in results['configs_checked']:
                if config['result']['status'] == 'needs_confirmation':
                    for conf in config['result']['confirmations_needed']:
                        print(f"\n  File: {config['file']}")
                        print(f"  Key: {conf['key']}")
                        print(f"  Reason: {conf['analysis']['reasoning']}")

        print("\n✅ Watchdog complete")

        return results


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Intelligent StatusLine Watchdog (AI-Powered)"
    )
    parser.add_argument(
        "--force-rule-based",
        action="store_true",
        help="Force rule-based mode (skip AI)"
    )

    args = parser.parse_args()

    watchdog = IntelligentStatusLineWatchdog()

    if args.force_rule_based:
        watchdog.use_intelligent_mode = False
        print("⚠️  Forced rule-based mode")

    results = watchdog.run_watchdog()

    # Exit with appropriate code
    if any(c['result']['status'] == 'error' for c in results['configs_checked']):
        sys.exit(1)
    elif results['total_confirmations_needed'] > 0:
        sys.exit(2)  # Needs user interaction
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

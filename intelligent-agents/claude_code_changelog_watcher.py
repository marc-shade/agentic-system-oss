#!/usr/bin/env python3
"""
Claude Code Changelog Watcher
==============================

Autonomous self-improvement agent that:
1. Monitors Claude Code GitHub releases for new features
2. Analyzes which features can benefit the agentic system
3. Proposes configuration changes to adopt new features
4. Integrates with Darwin Godel Machine for self-modification

This is part of the recursive self-improvement loop:
    Watch → Analyze → Propose → Test → Adopt → Learn
"""

import asyncio
import json
import logging
import os
import platform
import re
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess

# Platform-aware storage
def _get_storage_base() -> Path:
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
    return Path(__file__).parent.parent

STORAGE_BASE = _get_storage_base()
DB_PATH = STORAGE_BASE / "databases" / "cluster" / "shared_memories.db"
CLAUDE_CONFIG_DIR = Path.home() / ".claude"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ChangelogEntry:
    """A parsed changelog entry from Claude Code releases"""
    version: str
    date: str
    features: List[str] = field(default_factory=list)
    bug_fixes: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    breaking_changes: List[str] = field(default_factory=list)


@dataclass
class FeatureAdoptionProposal:
    """A proposal to adopt a new Claude Code feature"""
    feature_name: str
    description: str
    config_key: str
    config_value: Any
    config_file: str  # settings.json, .claude.json, etc.
    benefit: str
    risk_level: str  # low, medium, high
    auto_adoptable: bool  # Can be auto-adopted without human approval
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ClaudeCodeChangelogWatcher:
    """
    Watches Claude Code releases and proposes self-improvements.

    Integration points:
    - GitHub API for release monitoring
    - Local config files for feature detection
    - Darwin Godel Machine for self-modification proposals
    - Enhanced Memory for learning storage
    """

    GITHUB_REPO = "anthropics/claude-code"
    CHANGELOG_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/CHANGELOG.md"

    # Feature detection patterns
    FEATURE_PATTERNS = {
        "statusLine": {
            "pattern": r"status\s*line|statusLine",
            "config_file": "settings.json",
            "config_key": "statusLine",
            "auto_adoptable": False,  # Requires custom setup
        },
        "fileSuggestion": {
            "pattern": r"fileSuggestion|file\s*suggestion|@.*search",
            "config_file": "settings.json",
            "config_key": "fileSuggestion",
            "auto_adoptable": True,
        },
        "thinkingMode": {
            "pattern": r"thinking\s*mode|ultrathink|alwaysThinking",
            "config_file": "settings.json",
            "config_key": "alwaysThinkingEnabled",
            "auto_adoptable": True,
        },
        "rules": {
            "pattern": r"\.claude/rules|rules\s*support",
            "config_file": "rules/",
            "config_key": None,
            "auto_adoptable": True,
        },
        "hooks": {
            "pattern": r"hooks|pre-tool|post-tool",
            "config_file": "settings.json",
            "config_key": "hooks",
            "auto_adoptable": False,
        },
        "mcpServers": {
            "pattern": r"MCP|mcp.*server|model\s*context\s*protocol",
            "config_file": ".claude.json",
            "config_key": "mcpServers",
            "auto_adoptable": False,
        },
        "sandbox": {
            "pattern": r"sandbox|sandboxed|BashTool.*sandbox",
            "config_file": "settings.json",
            "config_key": "sandboxMode",
            "auto_adoptable": True,
        },
    }

    def __init__(self):
        self.current_version = self._get_current_version()
        self.adopted_features = self._load_adopted_features()
        self._init_database()

    def _get_current_version(self) -> str:
        """Get currently installed Claude Code version"""
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # Parse "2.0.67 (Claude Code)" -> "2.0.67"
            match = re.search(r"(\d+\.\d+\.\d+)", result.stdout)
            return match.group(1) if match else "unknown"
        except Exception as e:
            logger.warning(f"Failed to get Claude Code version: {e}")
            return "unknown"

    def _load_adopted_features(self) -> Dict[str, bool]:
        """Check which features are already configured"""
        adopted = {}

        # Check settings.json
        settings_path = CLAUDE_CONFIG_DIR / "settings.json"
        if settings_path.exists():
            try:
                with open(settings_path) as f:
                    settings = json.load(f)
                    adopted["statusLine"] = "statusLine" in settings
                    adopted["thinkingMode"] = settings.get("alwaysThinkingEnabled", False)
                    adopted["fileSuggestion"] = "fileSuggestion" in settings
            except Exception as e:
                logger.warning(f"Failed to read settings.json: {e}")

        # Check .claude.json for MCP servers
        mcp_path = CLAUDE_CONFIG_DIR.parent / ".claude.json"
        if mcp_path.exists():
            try:
                with open(mcp_path) as f:
                    mcp_config = json.load(f)
                    adopted["mcpServers"] = bool(mcp_config.get("mcpServers", {}))
            except Exception as e:
                logger.warning(f"Failed to read .claude.json: {e}")

        # Check hooks
        hooks_dir = CLAUDE_CONFIG_DIR / "hooks"
        adopted["hooks"] = hooks_dir.exists() and any(hooks_dir.iterdir())

        # Check rules
        rules_dir = CLAUDE_CONFIG_DIR / "rules"
        adopted["rules"] = rules_dir.exists() and any(rules_dir.iterdir())

        return adopted

    def _init_database(self):
        """Initialize database for tracking changelog analysis"""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS changelog_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT,
                feature_name TEXT,
                status TEXT,  -- detected, proposed, adopted, rejected
                proposal TEXT,  -- JSON proposal data
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS version_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT UNIQUE,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                features_found INTEGER,
                proposals_made INTEGER
            )
        """)

        conn.commit()
        conn.close()

    async def fetch_changelog(self) -> str:
        """Fetch the latest changelog from GitHub"""
        try:
            # Use curl for simplicity (available on both macOS and Linux)
            result = subprocess.run(
                ["curl", "-s", self.CHANGELOG_URL],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout
        except Exception as e:
            logger.error(f"Failed to fetch changelog: {e}")
            return ""

    def parse_changelog(self, content: str) -> List[ChangelogEntry]:
        """Parse changelog markdown into structured entries"""
        entries = []
        current_entry = None
        current_section = None

        for line in content.split("\n"):
            # Version header: ## Version 2.0.67 or ## 2.0.67
            version_match = re.match(r"##\s*(?:Version\s*)?(\d+\.\d+\.\d+)", line)
            if version_match:
                if current_entry:
                    entries.append(current_entry)
                current_entry = ChangelogEntry(
                    version=version_match.group(1),
                    date=datetime.now().isoformat()
                )
                continue

            if not current_entry:
                continue

            # Section headers
            if re.match(r"\*\*Features?\*\*|###\s*Features?", line, re.I):
                current_section = "features"
            elif re.match(r"\*\*Bug\s*Fix", line, re.I):
                current_section = "bug_fixes"
            elif re.match(r"\*\*Improvement|###\s*Improvement", line, re.I):
                current_section = "improvements"
            elif re.match(r"\*\*Breaking", line, re.I):
                current_section = "breaking_changes"
            elif line.startswith("- ") or line.startswith("* "):
                item = line[2:].strip()
                if current_section and item:
                    getattr(current_entry, current_section).append(item)

        if current_entry:
            entries.append(current_entry)

        return entries

    def analyze_features(self, entries: List[ChangelogEntry]) -> List[FeatureAdoptionProposal]:
        """Analyze changelog entries and generate adoption proposals"""
        proposals = []

        for entry in entries:
            all_items = (
                entry.features +
                entry.improvements +
                entry.bug_fixes
            )

            for item in all_items:
                for feature_name, config in self.FEATURE_PATTERNS.items():
                    # Skip already adopted features
                    if self.adopted_features.get(feature_name, False):
                        continue

                    # Check if this changelog item mentions the feature
                    if re.search(config["pattern"], item, re.I):
                        proposal = FeatureAdoptionProposal(
                            feature_name=feature_name,
                            description=item,
                            config_key=config["config_key"] or feature_name,
                            config_value=True,  # Default; could be more sophisticated
                            config_file=config["config_file"],
                            benefit=f"New feature from v{entry.version}: {item[:100]}",
                            risk_level="low" if config["auto_adoptable"] else "medium",
                            auto_adoptable=config["auto_adoptable"]
                        )
                        proposals.append(proposal)
                        break  # One proposal per feature

        return proposals

    def store_proposals(self, proposals: List[FeatureAdoptionProposal]):
        """Store proposals in database for tracking"""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        for proposal in proposals:
            cursor.execute("""
                INSERT OR REPLACE INTO changelog_analysis
                (version, feature_name, status, proposal)
                VALUES (?, ?, 'proposed', ?)
            """, (
                self.current_version,
                proposal.feature_name,
                json.dumps(asdict(proposal))
            ))

        conn.commit()
        conn.close()
        logger.info(f"Stored {len(proposals)} feature adoption proposals")

    def get_pending_proposals(self) -> List[FeatureAdoptionProposal]:
        """Get proposals pending human review"""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT proposal FROM changelog_analysis
            WHERE status = 'proposed'
            ORDER BY created_at DESC
        """)

        proposals = []
        for row in cursor.fetchall():
            data = json.loads(row[0])
            proposals.append(FeatureAdoptionProposal(**data))

        conn.close()
        return proposals

    async def check_for_updates(self) -> Dict[str, Any]:
        """Main entry point: check for new Claude Code features"""
        logger.info(f"Checking Claude Code changelog (current: v{self.current_version})")

        # Fetch and parse changelog
        content = await self.fetch_changelog()
        if not content:
            return {"error": "Failed to fetch changelog"}

        entries = self.parse_changelog(content)
        logger.info(f"Parsed {len(entries)} changelog entries")

        # Analyze for new features
        proposals = self.analyze_features(entries)
        logger.info(f"Generated {len(proposals)} adoption proposals")

        # Store proposals
        if proposals:
            self.store_proposals(proposals)

        # Generate summary
        return {
            "current_version": self.current_version,
            "entries_analyzed": len(entries),
            "proposals_generated": len(proposals),
            "adopted_features": self.adopted_features,
            "new_proposals": [asdict(p) for p in proposals],
            "timestamp": datetime.now().isoformat()
        }

    def generate_adoption_report(self) -> str:
        """Generate a human-readable adoption report"""
        pending = self.get_pending_proposals()

        report = [
            "# Claude Code Feature Adoption Report",
            f"\nCurrent Version: {self.current_version}",
            f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "\n## Currently Adopted Features",
        ]

        for feature, adopted in self.adopted_features.items():
            status = "✅" if adopted else "❌"
            report.append(f"- {status} {feature}")

        if pending:
            report.append("\n## Pending Adoption Proposals")
            for p in pending:
                risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}[p.risk_level]
                auto = "⚡ Auto-adoptable" if p.auto_adoptable else "👤 Needs review"
                report.append(f"\n### {p.feature_name}")
                report.append(f"- {risk_emoji} Risk: {p.risk_level}")
                report.append(f"- {auto}")
                report.append(f"- Config: `{p.config_file}` → `{p.config_key}`")
                report.append(f"- Benefit: {p.benefit}")
        else:
            report.append("\n## No Pending Proposals")
            report.append("All known features are either adopted or not applicable.")

        return "\n".join(report)


async def main():
    """Test the changelog watcher"""
    watcher = ClaudeCodeChangelogWatcher()

    print("=" * 60)
    print("Claude Code Changelog Watcher")
    print("=" * 60)

    # Check for updates
    result = await watcher.check_for_updates()
    print(f"\nVersion: {result.get('current_version', 'unknown')}")
    print(f"Entries analyzed: {result.get('entries_analyzed', 0)}")
    print(f"Proposals generated: {result.get('proposals_generated', 0)}")

    # Generate report
    print("\n" + "-" * 60)
    print(watcher.generate_adoption_report())


if __name__ == "__main__":
    asyncio.run(main())

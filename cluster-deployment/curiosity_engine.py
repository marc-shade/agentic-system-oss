#!/usr/bin/env python3
"""
Curiosity Engine - Feature Desire and Propagation System
=========================================================

The Curiosity Engine drives autonomous feature propagation across cluster nodes.

Core Concept: Each node should DESIRE features that peers have but it doesn't.
This creates a natural pull-based system where nodes actively seek to improve
themselves by learning from their peers.

Process:
1. Scan peer identities from the cluster registry
2. Compare with local identity to identify gaps
3. Generate "desires" (prioritized wants) for missing features
4. Queue desires for the Integration Agent to fulfill
5. Track fulfillment and satisfaction

This is NOT about copying files - it's about UNDERSTANDING what features
exist elsewhere and ADAPTING them to local environment.
"""

import json
import sqlite3
import platform
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
import hashlib

# Import sibling modules
from node_identity_service import NodeIdentityService, _get_storage_base

STORAGE_BASE = _get_storage_base()
DB_PATH = Path(STORAGE_BASE) / "databases" / "cluster" / "node_registry.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("curiosity-engine")


class Desire:
    """Represents a desire for a feature from a peer node"""

    def __init__(self, feature_type: str, feature_name: str, source_node: str,
                 priority: float = 0.5, reason: str = ""):
        self.id = hashlib.sha256(
            f"{feature_type}:{feature_name}:{source_node}".encode()
        ).hexdigest()[:16]
        self.feature_type = feature_type
        self.feature_name = feature_name
        self.source_node = source_node
        self.priority = priority  # 0.0 (low) to 1.0 (high)
        self.reason = reason
        self.created_at = datetime.now()
        self.status = "pending"  # pending, queued, integrating, fulfilled, failed
        self.fulfillment_attempts = 0
        self.last_attempt = None
        self.adaptation_plan = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "feature_type": self.feature_type,
            "feature_name": self.feature_name,
            "source_node": self.source_node,
            "priority": self.priority,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "fulfillment_attempts": self.fulfillment_attempts,
            "last_attempt": self.last_attempt.isoformat() if self.last_attempt else None,
            "adaptation_plan": self.adaptation_plan
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Desire':
        desire = cls(
            feature_type=data["feature_type"],
            feature_name=data["feature_name"],
            source_node=data["source_node"],
            priority=data.get("priority", 0.5),
            reason=data.get("reason", "")
        )
        desire.id = data.get("id", desire.id)
        desire.status = data.get("status", "pending")
        desire.fulfillment_attempts = data.get("fulfillment_attempts", 0)
        if data.get("last_attempt"):
            desire.last_attempt = datetime.fromisoformat(data["last_attempt"])
        desire.adaptation_plan = data.get("adaptation_plan")
        return desire


class CuriosityEngine:
    """
    Generates desires for features that peer nodes have.

    The engine is "curious" about what other nodes can do and
    creates prioritized desires to acquire those capabilities.
    """

    def __init__(self):
        self.identity_service = NodeIdentityService()
        self.node_id = self.identity_service.node_id
        self.desires: List[Desire] = []
        self._ensure_tables()
        self._load_desires()

    def _ensure_tables(self):
        """Ensure database tables exist"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feature_desires (
                id TEXT PRIMARY KEY,
                node_id TEXT NOT NULL,
                feature_type TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                source_node TEXT NOT NULL,
                priority REAL DEFAULT 0.5,
                reason TEXT,
                created_at TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                fulfillment_attempts INTEGER DEFAULT 0,
                last_attempt TEXT,
                adaptation_plan TEXT,
                updated_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS desire_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                desire_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                event TEXT NOT NULL,
                details TEXT,
                timestamp TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()

    def _load_desires(self):
        """Load existing desires from database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, feature_type, feature_name, source_node, priority,
                   reason, status, fulfillment_attempts, last_attempt, adaptation_plan
            FROM feature_desires
            WHERE node_id = ? AND status NOT IN ('fulfilled', 'abandoned')
            ORDER BY priority DESC
        """, (self.node_id,))

        for row in cursor.fetchall():
            desire = Desire(
                feature_type=row[1],
                feature_name=row[2],
                source_node=row[3],
                priority=row[4],
                reason=row[5]
            )
            desire.id = row[0]
            desire.status = row[6]
            desire.fulfillment_attempts = row[7]
            if row[8]:
                desire.last_attempt = datetime.fromisoformat(row[8])
            desire.adaptation_plan = json.loads(row[9]) if row[9] else None
            self.desires.append(desire)

        conn.close()
        logger.info(f"Loaded {len(self.desires)} active desires for {self.node_id}")

    def scan_peers(self) -> Dict[str, Any]:
        """
        Scan all peer nodes and identify feature gaps.

        This is the main curiosity function - looking at what others have.
        """
        logger.info(f"Scanning peers for {self.node_id}...")

        # Ensure we have current identity
        self.identity_service.generate_identity()
        self.identity_service.save_identity()

        # Get peer identities
        peers = self.identity_service.get_peer_identities()

        scan_result = {
            "scanned_at": datetime.now().isoformat(),
            "node_id": self.node_id,
            "peers_found": len(peers),
            "total_gaps": 0,
            "new_desires": 0,
            "peer_comparisons": []
        }

        for peer in peers:
            if not peer.get("identity"):
                logger.warning(f"No identity data for peer {peer['node_id']}")
                continue

            comparison = self.identity_service.compare_with_peer(peer["identity"])
            scan_result["peer_comparisons"].append({
                "peer_node": peer["node_id"],
                "features_they_have": len(comparison["features_peer_has"]),
                "features_we_have": len(comparison["features_we_have"]),
                "shared": len(comparison["shared_features"])
            })

            # Generate desires for features they have that we don't
            for feature in comparison["features_peer_has"]:
                new_desire = self._generate_desire(feature, peer)
                if new_desire:
                    scan_result["new_desires"] += 1

            scan_result["total_gaps"] += len(comparison["features_peer_has"])

        logger.info(f"Scan complete: {scan_result['total_gaps']} gaps found, "
                   f"{scan_result['new_desires']} new desires generated")

        return scan_result

    def _generate_desire(self, feature: Dict, peer: Dict) -> Optional[Desire]:
        """
        Generate a desire for a feature from a peer.

        Includes priority calculation and duplicate checking.
        """
        feature_type = feature.get("type", "unknown")
        feature_name = feature.get("name", "unknown")
        source_node = peer.get("node_id", "unknown")

        # Check if we already have this desire
        desire_id = hashlib.sha256(
            f"{feature_type}:{feature_name}:{source_node}".encode()
        ).hexdigest()[:16]

        for existing in self.desires:
            if existing.id == desire_id:
                # Already have this desire
                return None

        # Calculate priority
        priority = self._calculate_priority(feature, peer)

        # Generate reason
        reason = self._generate_reason(feature, peer)

        # Create desire
        desire = Desire(
            feature_type=feature_type,
            feature_name=feature_name,
            source_node=source_node,
            priority=priority,
            reason=reason
        )

        # Generate adaptation plan
        desire.adaptation_plan = self._generate_adaptation_plan(feature, peer)

        # Save to database
        self._save_desire(desire)
        self.desires.append(desire)

        logger.info(f"New desire: {feature_type}:{feature_name} from {source_node} "
                   f"(priority: {priority:.2f})")

        return desire

    def _calculate_priority(self, feature: Dict, peer: Dict) -> float:
        """
        Calculate priority for acquiring a feature.

        Factors:
        - Feature type importance (skills > agents > commands > hooks)
        - Source node authority (orchestrator > researcher > builder)
        - Platform compatibility
        - Recency of peer's update
        """
        priority = 0.5  # Base priority

        # Feature type weight
        type_weights = {
            "skill": 0.9,      # Skills are highly valuable
            "agent": 0.85,     # Agents provide new capabilities
            "mcp_server": 0.8, # MCP servers extend functionality
            "command": 0.6,    # Commands are convenient
            "hook_helper": 0.5 # Hooks are utility
        }
        priority = type_weights.get(feature.get("type", ""), priority)

        # Source node authority bonus
        source_role = peer.get("identity", {}).get("capabilities", {}).get("node_role", "")
        role_bonus = {
            "orchestrator": 0.15,
            "researcher": 0.10,
            "builder": 0.05
        }
        priority += role_bonus.get(source_role, 0)

        # Platform compatibility check
        peer_platform = peer.get("identity", {}).get("platform", {}).get("system", "")
        if peer_platform == platform.system():
            priority += 0.1  # Same platform = easier integration

        # Cap at 1.0
        return min(priority, 1.0)

    def _generate_reason(self, feature: Dict, peer: Dict) -> str:
        """Generate human-readable reason for this desire"""
        feature_type = feature.get("type", "feature")
        feature_name = feature.get("name", "unknown")
        source_node = peer.get("node_id", "peer")

        reasons = {
            "skill": f"Skill '{feature_name}' from {source_node} could enhance my capabilities",
            "agent": f"Agent '{feature_name}' from {source_node} provides new autonomous behavior",
            "mcp_server": f"MCP server '{feature_name}' from {source_node} extends tool access",
            "command": f"Command '{feature_name}' from {source_node} adds useful shortcut",
            "hook_helper": f"Hook module '{feature_name}' from {source_node} improves automation"
        }

        return reasons.get(feature_type, f"Feature '{feature_name}' from {source_node}")

    def _generate_adaptation_plan(self, feature: Dict, peer: Dict) -> Dict:
        """
        Generate a plan for adapting this feature to local environment.

        This is crucial - we can't just copy files. We need to understand
        what changes are needed for this node's specific setup.
        """
        plan = {
            "feature": feature,
            "source_node": peer.get("node_id"),
            "steps": [],
            "path_translations": {},
            "dependencies": [],
            "estimated_complexity": "low"
        }

        feature_type = feature.get("type", "")
        feature_name = feature.get("name", "")

        # Get our adaptation map
        our_adaptation = self.identity_service.identity.get("adaptation_map", {})
        path_rules = our_adaptation.get("path_rules", {})

        # Add path translation
        plan["path_translations"] = path_rules

        # Feature-specific adaptation steps
        if feature_type == "skill":
            plan["steps"] = [
                f"1. Request skill file '{feature_name}.md' from {peer.get('node_id')}",
                "2. Translate any paths in the skill content using path_translations",
                f"3. Save to {Path.home() / '.claude' / 'skills' / f'{feature_name}.md'}",
                "4. Verify skill loads correctly in Claude Code",
                "5. Test skill execution if possible"
            ]
            plan["dependencies"] = []
            plan["estimated_complexity"] = "low"

        elif feature_type == "agent":
            plan["steps"] = [
                f"1. Request agent definition '{feature_name}.md' from {peer.get('node_id')}",
                "2. Analyze agent for any node-specific paths or commands",
                "3. Translate paths using local adaptation rules",
                f"4. Save to {Path.home() / '.claude' / 'agents' / f'{feature_name}.md'}",
                "5. Verify agent is recognized by Claude Code"
            ]
            plan["estimated_complexity"] = "low"

        elif feature_type == "mcp_server":
            plan["steps"] = [
                f"1. Request MCP server config for '{feature_name}' from {peer.get('node_id')}",
                "2. Check if server code exists locally",
                "3. If not, determine if server can be installed/cloned",
                "4. Translate command paths in config",
                "5. Add server config to ~/.claude.json",
                "6. Install any Python dependencies",
                "7. Test server connectivity"
            ]
            plan["dependencies"] = ["python3", "pip"]
            plan["estimated_complexity"] = "medium"

        elif feature_type == "command":
            plan["steps"] = [
                f"1. Request command file '{feature_name}.md' from {peer.get('node_id')}",
                "2. Translate any embedded paths",
                f"3. Save to {Path.home() / '.claude' / 'commands' / f'{feature_name}.md'}",
                "4. Test command execution"
            ]
            plan["estimated_complexity"] = "low"

        elif feature_type == "hook_helper":
            plan["steps"] = [
                f"1. Request hook module '{feature_name}' from {peer.get('node_id')}",
                "2. Analyze imports and dependencies",
                "3. Translate any hardcoded paths",
                "4. Install any missing Python packages",
                f"5. Save to {Path.home() / '.claude' / 'hooks' / feature_name}",
                "6. Verify no import errors"
            ]
            plan["dependencies"] = ["python3"]
            plan["estimated_complexity"] = "medium"

        return plan

    def _save_desire(self, desire: Desire):
        """Save desire to database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO feature_desires
            (id, node_id, feature_type, feature_name, source_node, priority,
             reason, created_at, status, fulfillment_attempts, last_attempt,
             adaptation_plan, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            desire.id,
            self.node_id,
            desire.feature_type,
            desire.feature_name,
            desire.source_node,
            desire.priority,
            desire.reason,
            desire.created_at.isoformat(),
            desire.status,
            desire.fulfillment_attempts,
            desire.last_attempt.isoformat() if desire.last_attempt else None,
            json.dumps(desire.adaptation_plan) if desire.adaptation_plan else None,
            datetime.now().isoformat()
        ))

        # Log history
        cursor.execute("""
            INSERT INTO desire_history (desire_id, node_id, event, details, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            desire.id,
            self.node_id,
            "created" if desire.status == "pending" else desire.status,
            json.dumps(desire.to_dict()),
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

    def get_top_desires(self, limit: int = 10) -> List[Desire]:
        """Get top desires sorted by priority"""
        pending = [d for d in self.desires if d.status in ("pending", "queued")]
        return sorted(pending, key=lambda d: d.priority, reverse=True)[:limit]

    def update_desire_status(self, desire_id: str, status: str, details: str = ""):
        """Update desire status"""
        for desire in self.desires:
            if desire.id == desire_id:
                desire.status = status
                desire.last_attempt = datetime.now()
                if status == "integrating":
                    desire.fulfillment_attempts += 1
                self._save_desire(desire)

                # Log history
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO desire_history (desire_id, node_id, event, details, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (desire_id, self.node_id, status, details, datetime.now().isoformat()))
                conn.commit()
                conn.close()

                logger.info(f"Desire {desire_id} status -> {status}")
                return

        logger.warning(f"Desire {desire_id} not found")

    def get_fulfillment_queue(self) -> List[Dict]:
        """
        Get queue of desires ready for fulfillment by Integration Agent.

        Only returns desires that:
        - Are in pending/queued status
        - Haven't exceeded attempt limit
        - Haven't been attempted too recently
        """
        queue = []
        now = datetime.now()

        for desire in self.desires:
            if desire.status not in ("pending", "queued"):
                continue

            # Check attempt limits
            if desire.fulfillment_attempts >= 3:
                logger.warning(f"Desire {desire.id} exceeded attempt limit")
                self.update_desire_status(desire.id, "failed", "Exceeded attempt limit")
                continue

            # Check cooldown (30 min between attempts)
            if desire.last_attempt:
                if now - desire.last_attempt < timedelta(minutes=30):
                    continue

            queue.append({
                "desire": desire.to_dict(),
                "adaptation_plan": desire.adaptation_plan
            })

        return sorted(queue, key=lambda x: x["desire"]["priority"], reverse=True)

    def get_statistics(self) -> Dict[str, Any]:
        """Get curiosity engine statistics"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        stats = {
            "node_id": self.node_id,
            "timestamp": datetime.now().isoformat(),
            "total_desires": 0,
            "by_status": {},
            "by_type": {},
            "by_source": {},
            "top_desires": []
        }

        # Count by status
        cursor.execute("""
            SELECT status, COUNT(*) FROM feature_desires
            WHERE node_id = ?
            GROUP BY status
        """, (self.node_id,))
        for row in cursor.fetchall():
            stats["by_status"][row[0]] = row[1]
            stats["total_desires"] += row[1]

        # Count by type
        cursor.execute("""
            SELECT feature_type, COUNT(*) FROM feature_desires
            WHERE node_id = ?
            GROUP BY feature_type
        """, (self.node_id,))
        for row in cursor.fetchall():
            stats["by_type"][row[0]] = row[1]

        # Count by source
        cursor.execute("""
            SELECT source_node, COUNT(*) FROM feature_desires
            WHERE node_id = ?
            GROUP BY source_node
        """, (self.node_id,))
        for row in cursor.fetchall():
            stats["by_source"][row[0]] = row[1]

        conn.close()

        # Top desires
        stats["top_desires"] = [d.to_dict() for d in self.get_top_desires(5)]

        return stats


def main():
    """Run curiosity engine scan"""
    engine = CuriosityEngine()

    print("\n" + "="*80)
    print(f"CURIOSITY ENGINE - {engine.node_id}")
    print("="*80)

    # Scan peers
    print("\nScanning peer nodes for features...")
    result = engine.scan_peers()

    print(f"\nScan Results:")
    print(f"  Peers found: {result['peers_found']}")
    print(f"  Total gaps: {result['total_gaps']}")
    print(f"  New desires: {result['new_desires']}")

    if result['peer_comparisons']:
        print("\nPeer Comparisons:")
        for comp in result['peer_comparisons']:
            print(f"  {comp['peer_node']}:")
            print(f"    - Features they have: {comp['features_they_have']}")
            print(f"    - Features we have: {comp['features_we_have']}")
            print(f"    - Shared: {comp['shared']}")

    # Show top desires
    top = engine.get_top_desires(5)
    if top:
        print("\nTop Desires (what we want):")
        for i, desire in enumerate(top, 1):
            print(f"  {i}. [{desire.priority:.2f}] {desire.feature_type}: {desire.feature_name}")
            print(f"     From: {desire.source_node}")
            print(f"     Reason: {desire.reason}")

    # Show statistics
    stats = engine.get_statistics()
    print("\nStatistics:")
    print(f"  Total desires: {stats['total_desires']}")
    print(f"  By status: {stats['by_status']}")
    print(f"  By type: {stats['by_type']}")

    # Show fulfillment queue
    queue = engine.get_fulfillment_queue()
    if queue:
        print(f"\nReady for integration: {len(queue)} desires")

    print("\n" + "="*80)


if __name__ == "__main__":
    main()

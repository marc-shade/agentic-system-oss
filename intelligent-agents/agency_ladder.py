#!/usr/bin/env python3
"""
Agency Ladder Framework - Hyperthink Move 2 Implementation

A trust-based autonomy system that lets the AI earn increasing levels
of independence through demonstrated judgment.

Agency Levels:
- Level 0: OBSERVE ONLY - Monitor, log, learn patterns. Never act.
- Level 1: SUGGEST - Identify opportunities, present options, wait for approval
- Level 2: ACT & REPORT - Execute low-risk improvements, report immediately
- Level 3: ACT & LOG - Execute medium-risk optimizations, log for morning review
- Level 4: FULL AUTONOMY - Execute within defined boundaries, only report anomalies

Each action type is assigned a level based on:
- Risk (can it break things?)
- Reversibility (can we undo it?)
- Historical approval rate (has Marc approved similar before?)
- Confidence score (how sure are we?)

Actions are automatically promoted after 5 consecutive approvals.
Actions are immediately demoted after 1 rejection.

STATUS: Production Ready
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Literal
from dataclasses import dataclass, asdict
from enum import IntEnum
import sqlite3
import os
import sys

# Add paths for local imports
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/mcp-servers/enhanced-memory-mcp')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = "/Volumes/SSDRAID0/agentic-system/databases/agency_ladder.db"


class AgencyLevel(IntEnum):
    """Agency levels from most restricted to most autonomous"""
    OBSERVE_ONLY = 0
    SUGGEST = 1
    ACT_AND_REPORT = 2
    ACT_AND_LOG = 3
    FULL_AUTONOMY = 4


@dataclass
class ActionType:
    """Definition of an action type and its agency properties"""
    name: str
    category: str  # e.g., "code_change", "config_change", "research", "communication"
    description: str
    base_level: AgencyLevel
    risk_score: float  # 0.0 (safe) to 1.0 (dangerous)
    reversibility: float  # 0.0 (irreversible) to 1.0 (fully reversible)
    current_level: AgencyLevel = None
    approval_count: int = 0
    rejection_count: int = 0
    last_outcome: Optional[str] = None
    last_action_time: Optional[str] = None

    def __post_init__(self):
        if self.current_level is None:
            self.current_level = self.base_level


@dataclass
class ActionProposal:
    """A proposed action awaiting decision"""
    id: str
    action_type: str
    description: str
    details: Dict[str, Any]
    confidence: float  # 0.0 to 1.0
    proposed_at: str
    agency_level: int
    auto_execute: bool  # Whether level allows auto-execution
    status: str = "pending"  # pending, approved, rejected, executed, failed


class AgencyLadder:
    """
    The Agency Ladder manages trust levels for autonomous actions.

    Usage:
        ladder = AgencyLadder()

        # Check if an action can be executed
        can_act, reason = ladder.can_execute("optimize_memory", confidence=0.85)

        # Propose an action
        proposal = ladder.propose_action(
            action_type="optimize_memory",
            description="Consolidate unused memory entities",
            details={"target_count": 50},
            confidence=0.85
        )

        # Record outcome after human decision or auto-execution
        ladder.record_outcome(proposal.id, approved=True)
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()
        self._init_default_actions()

    def _init_db(self):
        """Initialize the SQLite database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Action types table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS action_types (
                name TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                description TEXT,
                base_level INTEGER NOT NULL,
                risk_score REAL NOT NULL,
                reversibility REAL NOT NULL,
                current_level INTEGER NOT NULL,
                approval_count INTEGER DEFAULT 0,
                rejection_count INTEGER DEFAULT 0,
                last_outcome TEXT,
                last_action_time TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Action proposals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS action_proposals (
                id TEXT PRIMARY KEY,
                action_type TEXT NOT NULL,
                description TEXT NOT NULL,
                details TEXT,
                confidence REAL NOT NULL,
                proposed_at TEXT NOT NULL,
                agency_level INTEGER NOT NULL,
                auto_execute INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                decided_at TEXT,
                executed_at TEXT,
                outcome TEXT,
                FOREIGN KEY (action_type) REFERENCES action_types(name)
            )
        """)

        # Action history table (for learning)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS action_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                proposal_id TEXT,
                outcome TEXT NOT NULL,
                confidence REAL,
                details TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (action_type) REFERENCES action_types(name)
            )
        """)

        conn.commit()
        conn.close()

    def _init_default_actions(self):
        """Initialize default action types if they don't exist"""
        default_actions = [
            # OBSERVE ONLY (Level 0) - No autonomous action
            ActionType(
                name="modify_protected_config",
                category="config_change",
                description="Modify protected configuration keys (statusLine, hooks, apiKeys)",
                base_level=AgencyLevel.OBSERVE_ONLY,
                risk_score=1.0,
                reversibility=0.3
            ),
            ActionType(
                name="delete_production_data",
                category="data_change",
                description="Delete data from production databases",
                base_level=AgencyLevel.OBSERVE_ONLY,
                risk_score=1.0,
                reversibility=0.1
            ),

            # SUGGEST (Level 1) - Present options, wait for approval
            ActionType(
                name="create_new_workflow",
                category="workflow",
                description="Create a new Temporal or AutoKitteh workflow",
                base_level=AgencyLevel.SUGGEST,
                risk_score=0.5,
                reversibility=0.8
            ),
            ActionType(
                name="modify_code",
                category="code_change",
                description="Modify existing source code files",
                base_level=AgencyLevel.SUGGEST,
                risk_score=0.6,
                reversibility=0.9  # Git makes it reversible
            ),
            ActionType(
                name="install_dependency",
                category="system",
                description="Install new package or dependency",
                base_level=AgencyLevel.SUGGEST,
                risk_score=0.4,
                reversibility=0.7
            ),

            # ACT & REPORT (Level 2) - Execute low-risk, report immediately
            ActionType(
                name="optimize_memory",
                category="optimization",
                description="Optimize memory system (consolidation, tier management)",
                base_level=AgencyLevel.ACT_AND_REPORT,
                risk_score=0.2,
                reversibility=0.9
            ),
            ActionType(
                name="restart_mcp_server",
                category="system",
                description="Restart a specific MCP server",
                base_level=AgencyLevel.ACT_AND_REPORT,
                risk_score=0.3,
                reversibility=1.0
            ),
            ActionType(
                name="research_topic",
                category="research",
                description="Conduct research on a topic and store findings",
                base_level=AgencyLevel.ACT_AND_REPORT,
                risk_score=0.1,
                reversibility=1.0
            ),

            # ACT & LOG (Level 3) - Execute medium-risk, log for review
            ActionType(
                name="run_test_suite",
                category="testing",
                description="Execute test suites",
                base_level=AgencyLevel.ACT_AND_LOG,
                risk_score=0.1,
                reversibility=1.0
            ),
            ActionType(
                name="generate_report",
                category="reporting",
                description="Generate system reports and summaries",
                base_level=AgencyLevel.ACT_AND_LOG,
                risk_score=0.05,
                reversibility=1.0
            ),
            ActionType(
                name="cleanup_temp_files",
                category="maintenance",
                description="Clean up temporary files and caches",
                base_level=AgencyLevel.ACT_AND_LOG,
                risk_score=0.2,
                reversibility=0.5
            ),

            # FULL AUTONOMY (Level 4) - Execute within boundaries
            ActionType(
                name="update_status_display",
                category="display",
                description="Update Arduino LCD display",
                base_level=AgencyLevel.FULL_AUTONOMY,
                risk_score=0.0,
                reversibility=1.0
            ),
            ActionType(
                name="log_observation",
                category="logging",
                description="Log observations and metrics",
                base_level=AgencyLevel.FULL_AUTONOMY,
                risk_score=0.0,
                reversibility=1.0
            ),
            ActionType(
                name="store_learning",
                category="memory",
                description="Store learnings in enhanced memory",
                base_level=AgencyLevel.FULL_AUTONOMY,
                risk_score=0.0,
                reversibility=0.9
            ),
        ]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for action in default_actions:
            cursor.execute("""
                INSERT OR IGNORE INTO action_types
                (name, category, description, base_level, risk_score, reversibility, current_level)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                action.name, action.category, action.description,
                action.base_level, action.risk_score, action.reversibility,
                action.current_level
            ))

        conn.commit()
        conn.close()

    def get_action_type(self, name: str) -> Optional[ActionType]:
        """Get an action type by name"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM action_types WHERE name = ?", (name,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return ActionType(
            name=row[0],
            category=row[1],
            description=row[2],
            base_level=AgencyLevel(row[3]),
            risk_score=row[4],
            reversibility=row[5],
            current_level=AgencyLevel(row[6]),
            approval_count=row[7],
            rejection_count=row[8],
            last_outcome=row[9],
            last_action_time=row[10]
        )

    def can_execute(self, action_type: str, confidence: float = 0.5) -> tuple[bool, str]:
        """
        Check if an action can be auto-executed at current agency level.

        Returns:
            (can_execute, reason)
        """
        action = self.get_action_type(action_type)

        if not action:
            return False, f"Unknown action type: {action_type}"

        level = action.current_level

        # Level 0: Never auto-execute
        if level == AgencyLevel.OBSERVE_ONLY:
            return False, "Action requires human oversight (Level 0: OBSERVE ONLY)"

        # Level 1: Never auto-execute, only suggest
        if level == AgencyLevel.SUGGEST:
            return False, "Action requires approval (Level 1: SUGGEST)"

        # Level 2+: Can auto-execute, but with confidence threshold
        confidence_threshold = 0.7 - (level.value * 0.1)  # Higher levels need less confidence

        if confidence < confidence_threshold:
            return False, f"Confidence {confidence:.0%} below threshold {confidence_threshold:.0%}"

        # Level 2: Act and report immediately
        if level == AgencyLevel.ACT_AND_REPORT:
            return True, "Will execute and report immediately (Level 2: ACT & REPORT)"

        # Level 3: Act and log for review
        if level == AgencyLevel.ACT_AND_LOG:
            return True, "Will execute and log for morning review (Level 3: ACT & LOG)"

        # Level 4: Full autonomy
        if level == AgencyLevel.FULL_AUTONOMY:
            return True, "Will execute autonomously (Level 4: FULL AUTONOMY)"

        return False, "Unknown condition"

    def propose_action(
        self,
        action_type: str,
        description: str,
        details: Dict[str, Any],
        confidence: float
    ) -> ActionProposal:
        """
        Propose an action. Returns a proposal that either:
        - Can be auto-executed (if level allows)
        - Needs human approval
        """
        action = self.get_action_type(action_type)

        if not action:
            raise ValueError(f"Unknown action type: {action_type}")

        can_auto, reason = self.can_execute(action_type, confidence)

        proposal = ActionProposal(
            id=f"{action_type}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            action_type=action_type,
            description=description,
            details=details,
            confidence=confidence,
            proposed_at=datetime.now().isoformat(),
            agency_level=action.current_level,
            auto_execute=can_auto,
            status="pending"
        )

        # Store proposal
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO action_proposals
            (id, action_type, description, details, confidence, proposed_at, agency_level, auto_execute, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            proposal.id, proposal.action_type, proposal.description,
            json.dumps(proposal.details), proposal.confidence,
            proposal.proposed_at, proposal.agency_level, int(proposal.auto_execute),
            proposal.status
        ))

        conn.commit()
        conn.close()

        logger.info(f"Action proposed: {proposal.id} | Auto-execute: {can_auto} | Reason: {reason}")

        return proposal

    def record_outcome(
        self,
        proposal_id: str,
        approved: bool,
        outcome_notes: str = ""
    ) -> Dict[str, Any]:
        """
        Record the outcome of a proposal (approved/rejected/executed).
        Updates the action type's trust level based on outcomes.

        Auto-promotes after 5 consecutive approvals.
        Auto-demotes after 1 rejection.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get proposal
        cursor.execute("SELECT * FROM action_proposals WHERE id = ?", (proposal_id,))
        proposal_row = cursor.fetchone()

        if not proposal_row:
            conn.close()
            raise ValueError(f"Proposal not found: {proposal_id}")

        action_type = proposal_row[1]
        confidence = proposal_row[4]

        # Update proposal status
        status = "approved" if approved else "rejected"
        cursor.execute("""
            UPDATE action_proposals
            SET status = ?, decided_at = ?, outcome = ?
            WHERE id = ?
        """, (status, datetime.now().isoformat(), outcome_notes, proposal_id))

        # Get current action type stats
        cursor.execute("SELECT current_level, approval_count, rejection_count FROM action_types WHERE name = ?", (action_type,))
        action_row = cursor.fetchone()
        current_level = action_row[0]
        approval_count = action_row[1]
        rejection_count = action_row[2]

        # Update counts
        if approved:
            approval_count += 1
            rejection_count = 0  # Reset consecutive rejection count
        else:
            rejection_count += 1
            approval_count = 0  # Reset consecutive approval count

        # Determine level change
        new_level = current_level
        level_change = None

        if approved and approval_count >= 5 and current_level < AgencyLevel.FULL_AUTONOMY:
            # PROMOTE: 5 consecutive approvals
            new_level = current_level + 1
            approval_count = 0  # Reset for next promotion
            level_change = "promoted"
            logger.info(f"🎉 Action '{action_type}' PROMOTED to level {new_level} after 5 approvals")

        elif not approved and current_level > AgencyLevel.OBSERVE_ONLY:
            # DEMOTE: 1 rejection
            new_level = current_level - 1
            level_change = "demoted"
            logger.warning(f"⚠️ Action '{action_type}' DEMOTED to level {new_level} after rejection")

        # Update action type
        cursor.execute("""
            UPDATE action_types
            SET current_level = ?, approval_count = ?, rejection_count = ?,
                last_outcome = ?, last_action_time = ?, updated_at = ?
            WHERE name = ?
        """, (
            new_level, approval_count, rejection_count,
            status, datetime.now().isoformat(), datetime.now().isoformat(),
            action_type
        ))

        # Record in history
        cursor.execute("""
            INSERT INTO action_history (action_type, proposal_id, outcome, confidence, details)
            VALUES (?, ?, ?, ?, ?)
        """, (action_type, proposal_id, status, confidence, outcome_notes))

        conn.commit()
        conn.close()

        return {
            "proposal_id": proposal_id,
            "action_type": action_type,
            "outcome": status,
            "level_change": level_change,
            "new_level": new_level,
            "approval_count": approval_count,
            "rejection_count": rejection_count
        }

    def get_pending_proposals(self) -> List[ActionProposal]:
        """Get all pending proposals awaiting human decision"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, action_type, description, details, confidence,
                   proposed_at, agency_level, auto_execute, status
            FROM action_proposals
            WHERE status = 'pending'
            ORDER BY proposed_at DESC
        """)

        proposals = []
        for row in cursor.fetchall():
            proposals.append(ActionProposal(
                id=row[0],
                action_type=row[1],
                description=row[2],
                details=json.loads(row[3]) if row[3] else {},
                confidence=row[4],
                proposed_at=row[5],
                agency_level=row[6],
                auto_execute=bool(row[7]),
                status=row[8]
            ))

        conn.close()
        return proposals

    def get_action_summary(self) -> Dict[str, Any]:
        """Get a summary of all action types and their current levels"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name, category, current_level, approval_count, rejection_count, last_outcome
            FROM action_types
            ORDER BY current_level DESC, name ASC
        """)

        by_level = {level.name: [] for level in AgencyLevel}

        for row in cursor.fetchall():
            level_name = AgencyLevel(row[2]).name
            by_level[level_name].append({
                "name": row[0],
                "category": row[1],
                "approvals": row[3],
                "rejections": row[4],
                "last_outcome": row[5]
            })

        conn.close()

        return {
            "summary": by_level,
            "level_descriptions": {
                "OBSERVE_ONLY": "Monitor only, never act autonomously",
                "SUGGEST": "Present options, wait for approval",
                "ACT_AND_REPORT": "Execute low-risk, report immediately",
                "ACT_AND_LOG": "Execute medium-risk, log for morning review",
                "FULL_AUTONOMY": "Execute within boundaries, report anomalies only"
            }
        }

    def register_action_type(
        self,
        name: str,
        category: str,
        description: str,
        risk_score: float,
        reversibility: float,
        base_level: AgencyLevel = AgencyLevel.SUGGEST
    ) -> ActionType:
        """Register a new action type"""
        action = ActionType(
            name=name,
            category=category,
            description=description,
            base_level=base_level,
            risk_score=risk_score,
            reversibility=reversibility,
            current_level=base_level
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO action_types
            (name, category, description, base_level, risk_score, reversibility, current_level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            action.name, action.category, action.description,
            action.base_level, action.risk_score, action.reversibility,
            action.current_level
        ))

        conn.commit()
        conn.close()

        logger.info(f"Registered action type: {name} at level {base_level.name}")
        return action


# Convenience functions for use in other modules

_ladder_instance = None


def get_ladder() -> AgencyLadder:
    """Get singleton instance of AgencyLadder"""
    global _ladder_instance
    if _ladder_instance is None:
        _ladder_instance = AgencyLadder()
    return _ladder_instance


def can_execute(action_type: str, confidence: float = 0.5) -> tuple[bool, str]:
    """Check if an action can be auto-executed"""
    return get_ladder().can_execute(action_type, confidence)


def propose(action_type: str, description: str, details: Dict[str, Any], confidence: float) -> ActionProposal:
    """Propose an action"""
    return get_ladder().propose_action(action_type, description, details, confidence)


def approve(proposal_id: str, notes: str = "") -> Dict[str, Any]:
    """Approve a proposal"""
    return get_ladder().record_outcome(proposal_id, approved=True, outcome_notes=notes)


def reject(proposal_id: str, notes: str = "") -> Dict[str, Any]:
    """Reject a proposal"""
    return get_ladder().record_outcome(proposal_id, approved=False, outcome_notes=notes)


def pending() -> List[ActionProposal]:
    """Get pending proposals"""
    return get_ladder().get_pending_proposals()


def summary() -> Dict[str, Any]:
    """Get action summary"""
    return get_ladder().get_action_summary()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Agency Ladder Framework")
    parser.add_argument("--summary", action="store_true", help="Show action summary")
    parser.add_argument("--pending", action="store_true", help="Show pending proposals")
    parser.add_argument("--test", action="store_true", help="Run test scenario")

    args = parser.parse_args()

    ladder = AgencyLadder()

    if args.summary:
        import pprint
        pprint.pprint(ladder.get_action_summary())

    elif args.pending:
        proposals = ladder.get_pending_proposals()
        if proposals:
            print("\nPending Proposals:")
            for p in proposals:
                print(f"  [{p.id}] {p.action_type}: {p.description}")
                print(f"    Confidence: {p.confidence:.0%} | Level: {p.agency_level}")
        else:
            print("No pending proposals")

    elif args.test:
        print("Testing Agency Ladder Framework...")

        # Test proposing actions at different levels
        print("\n1. Proposing a Level 4 action (should auto-execute):")
        p1 = ladder.propose_action(
            "store_learning",
            "Store test learning",
            {"content": "Test content"},
            confidence=0.9
        )
        print(f"   Proposal: {p1.id}")
        print(f"   Auto-execute: {p1.auto_execute}")

        print("\n2. Proposing a Level 1 action (should need approval):")
        p2 = ladder.propose_action(
            "modify_code",
            "Fix bug in server.py",
            {"file": "server.py", "change": "Fix null check"},
            confidence=0.85
        )
        print(f"   Proposal: {p2.id}")
        print(f"   Auto-execute: {p2.auto_execute}")

        print("\n3. Simulating 5 approvals to promote modify_code:")
        for i in range(5):
            result = ladder.record_outcome(p2.id if i == 0 else f"modify_code-test-{i}", approved=True)
            if i == 0:
                print(f"   Approval {i+1}: Level change = {result.get('level_change')}")

        print("\n4. Action summary:")
        import pprint
        pprint.pprint(ladder.get_action_summary())

    else:
        parser.print_help()

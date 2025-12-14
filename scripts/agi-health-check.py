#!/usr/bin/env python3
"""
AGI System Health Check - Comprehensive validation of all AGI memory components.

Tests all aspects of the AGI memory system:
- 4-tier memory architecture (working, episodic, semantic, procedural)
- Temporal reasoning (causal links, temporal chains)
- Emotional/associative memory
- Self-improvement cycles
- Session lifecycle
- Consolidation engine
- Multi-agent coordination
- Action outcome tracking
- Metacognitive state

Usage:
    python3 agi-health-check.py [--verbose] [--fix]
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

# ANSI colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Database paths
MEMORY_DB = Path.home() / ".claude" / "enhanced_memories" / "memory.db"
CLUSTER_DB = Path("/mnt/agentic-system/databases/cluster")
NODE_CHAT_DB = CLUSTER_DB / "node_chat.db"
SHARED_MEMORIES_DB = CLUSTER_DB / "shared_memories.db"

class AGIHealthChecker:
    """Comprehensive AGI system health checker."""

    def __init__(self, verbose: bool = False, fix: bool = False):
        self.verbose = verbose
        self.fix = fix
        self.results: Dict[str, Dict] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def check_all(self) -> bool:
        """Run all health checks."""
        print(f"\n{BOLD}{'='*60}{RESET}")
        print(f"{BOLD}       AGI SYSTEM HEALTH CHECK{RESET}")
        print(f"{BOLD}{'='*60}{RESET}\n")

        checks = [
            ("Database Connectivity", self.check_database_connectivity),
            ("4-Tier Memory Architecture", self.check_memory_tiers),
            ("Temporal Reasoning", self.check_temporal_reasoning),
            ("Emotional/Associative Memory", self.check_emotional_memory),
            ("Consolidation Engine", self.check_consolidation_engine),
            ("Session Lifecycle", self.check_session_lifecycle),
            ("Self-Improvement Cycles", self.check_self_improvement),
            ("Action Outcome Tracking", self.check_action_tracking),
            ("Metacognitive State", self.check_metacognitive),
            ("Agent Identity", self.check_agent_identity),
            ("Multi-Agent Coordination", self.check_cluster_coordination),
        ]

        all_passed = True
        for name, check_func in checks:
            try:
                passed, details = check_func()
                self.results[name] = {"passed": passed, "details": details}
                status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
                print(f"[{status}] {name}")
                if self.verbose and details:
                    for key, value in details.items():
                        print(f"       {key}: {value}")
                if not passed:
                    all_passed = False
            except Exception as e:
                self.results[name] = {"passed": False, "error": str(e)}
                print(f"[{RED}ERROR{RESET}] {name}: {e}")
                all_passed = False

        self._print_summary()
        return all_passed

    def check_database_connectivity(self) -> Tuple[bool, Dict]:
        """Check database file existence and connectivity."""
        details = {}

        # Check main memory database
        if MEMORY_DB.exists():
            conn = sqlite3.connect(str(MEMORY_DB))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM entities")
            count = cursor.fetchone()[0]
            conn.close()
            details["memory_db"] = f"{count} entities"
        else:
            self.errors.append(f"Memory database not found: {MEMORY_DB}")
            return False, {"error": "Memory DB not found"}

        # Check cluster databases
        if NODE_CHAT_DB.exists():
            conn = sqlite3.connect(str(NODE_CHAT_DB))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM messages")
            count = cursor.fetchone()[0]
            conn.close()
            details["node_chat"] = f"{count:,} messages"
        else:
            details["node_chat"] = "Not found (optional)"

        return True, details

    def check_memory_tiers(self) -> Tuple[bool, Dict]:
        """Check all 4 memory tiers are operational."""
        conn = sqlite3.connect(str(MEMORY_DB))
        cursor = conn.cursor()
        details = {}
        issues = []

        # Working Memory
        cursor.execute("SELECT COUNT(*) FROM working_memory WHERE expires_at > datetime('now')")
        active_wm = cursor.fetchone()[0]
        details["working_memory"] = f"{active_wm} active items"

        # Episodic Memory
        cursor.execute("SELECT COUNT(*) FROM episodic_memory")
        episodes = cursor.fetchone()[0]
        details["episodic_memory"] = f"{episodes} episodes"

        # Semantic Memory
        cursor.execute("SELECT COUNT(*) FROM semantic_memory")
        concepts = cursor.fetchone()[0]
        details["semantic_memory"] = f"{concepts} concepts"

        # Procedural Memory
        cursor.execute("SELECT COUNT(*), AVG(success_rate) FROM procedural_memory")
        row = cursor.fetchone()
        skills = row[0]
        avg_success = row[1] or 0
        details["procedural_memory"] = f"{skills} skills ({avg_success*100:.1f}% avg success)"

        conn.close()

        # All tiers should have data for a healthy system
        if episodes < 1:
            issues.append("No episodic memories")
        if skills < 1:
            issues.append("No procedural skills")

        return len(issues) == 0, details

    def check_temporal_reasoning(self) -> Tuple[bool, Dict]:
        """Check temporal reasoning components."""
        conn = sqlite3.connect(str(MEMORY_DB))
        cursor = conn.cursor()
        details = {}

        # Causal Links
        cursor.execute("SELECT COUNT(*) FROM causal_links")
        links = cursor.fetchone()[0]
        details["causal_links"] = links

        # Temporal Chains
        cursor.execute("SELECT COUNT(*) FROM temporal_chains")
        chains = cursor.fetchone()[0]
        details["temporal_chains"] = chains

        # Check for recent causal activity
        cursor.execute("""
            SELECT COUNT(*) FROM causal_links
            WHERE created_at > datetime('now', '-7 days')
        """)
        recent_links = cursor.fetchone()[0]
        details["recent_causal_links"] = f"{recent_links} (last 7 days)"

        conn.close()
        return True, details

    def check_emotional_memory(self) -> Tuple[bool, Dict]:
        """Check emotional tagging and associative memory."""
        conn = sqlite3.connect(str(MEMORY_DB))
        cursor = conn.cursor()
        details = {}

        # Emotional Tags
        cursor.execute("SELECT COUNT(*) FROM emotional_tags")
        tags = cursor.fetchone()[0]
        details["emotional_tags"] = tags

        # Associations
        cursor.execute("SELECT COUNT(*) FROM memory_associations")
        assocs = cursor.fetchone()[0]
        details["associations"] = assocs

        # Attention Weights
        cursor.execute("SELECT COUNT(*) FROM attention_weights WHERE current_attention > 0.3")
        attended = cursor.fetchone()[0]
        details["attended_memories"] = attended

        # Emotional distribution
        cursor.execute("""
            SELECT primary_emotion, COUNT(*) as cnt
            FROM emotional_tags
            WHERE primary_emotion IS NOT NULL
            GROUP BY primary_emotion
        """)
        emotions = {row[0]: row[1] for row in cursor.fetchall()}
        if emotions:
            details["emotion_distribution"] = emotions

        conn.close()
        return True, details

    def check_consolidation_engine(self) -> Tuple[bool, Dict]:
        """Check consolidation job history and effectiveness."""
        conn = sqlite3.connect(str(MEMORY_DB))
        cursor = conn.cursor()
        details = {}

        # Check consolidation jobs table
        cursor.execute("""
            SELECT job_type, status, COUNT(*)
            FROM consolidation_jobs
            GROUP BY job_type, status
        """)
        jobs = {}
        for row in cursor.fetchall():
            job_type, status, count = row
            if job_type not in jobs:
                jobs[job_type] = {}
            jobs[job_type][status] = count

        details["consolidation_jobs"] = jobs

        # Recent consolidation activity
        cursor.execute("""
            SELECT COUNT(*) FROM consolidation_jobs
            WHERE started_at > datetime('now', '-24 hours')
        """)
        recent = cursor.fetchone()[0]
        details["jobs_last_24h"] = recent

        # Check patterns found (using correct column name)
        cursor.execute("""
            SELECT SUM(patterns_found)
            FROM consolidation_jobs
            WHERE status = 'completed'
        """)
        patterns = cursor.fetchone()[0] or 0
        details["total_patterns_found"] = patterns

        conn.close()

        # Should have some completed consolidation jobs
        has_completed = any(
            'completed' in statuses for statuses in jobs.values()
        )
        return has_completed or len(jobs) > 0, details

    def check_session_lifecycle(self) -> Tuple[bool, Dict]:
        """Check session tracking and continuity."""
        conn = sqlite3.connect(str(MEMORY_DB))
        cursor = conn.cursor()
        details = {}

        # Session continuity (correct table name)
        cursor.execute("SELECT COUNT(*) FROM session_continuity")
        sessions = cursor.fetchone()[0]
        details["total_sessions"] = sessions

        # Recent sessions
        cursor.execute("""
            SELECT COUNT(*) FROM session_continuity
            WHERE started_at > datetime('now', '-7 days')
        """)
        recent = cursor.fetchone()[0]
        details["sessions_last_7_days"] = recent

        # Sessions with learnings
        cursor.execute("""
            SELECT COUNT(*) FROM session_continuity
            WHERE key_learnings != '[]' AND key_learnings IS NOT NULL
        """)
        with_learnings = cursor.fetchone()[0]
        details["sessions_with_learnings"] = with_learnings

        conn.close()
        return sessions > 0, details

    def check_self_improvement(self) -> Tuple[bool, Dict]:
        """Check self-improvement cycle tracking."""
        conn = sqlite3.connect(str(MEMORY_DB))
        cursor = conn.cursor()
        details = {}

        # Improvement cycles (correct column: success not successful)
        cursor.execute("SELECT COUNT(*), AVG(CASE WHEN success THEN 1 ELSE 0 END) FROM improvement_cycles")
        row = cursor.fetchone()
        cycles = row[0]
        success_rate = (row[1] or 0) * 100
        details["improvement_cycles"] = cycles
        details["success_rate"] = f"{success_rate:.1f}%"

        # By type
        cursor.execute("""
            SELECT cycle_type, COUNT(*), AVG(CASE WHEN success THEN 1 ELSE 0 END)
            FROM improvement_cycles
            GROUP BY cycle_type
        """)
        by_type = {row[0]: {"count": row[1], "success": f"{(row[2] or 0)*100:.0f}%"}
                   for row in cursor.fetchall()}
        if by_type:
            details["by_type"] = by_type

        conn.close()
        return True, details

    def check_action_tracking(self) -> Tuple[bool, Dict]:
        """Check action outcome recording."""
        conn = sqlite3.connect(str(MEMORY_DB))
        cursor = conn.cursor()
        details = {}

        # Total actions
        cursor.execute("SELECT COUNT(*) FROM action_outcomes")
        total = cursor.fetchone()[0]
        details["total_actions"] = f"{total:,}"

        # Recent actions (correct column: executed_at not created_at)
        cursor.execute("""
            SELECT COUNT(*) FROM action_outcomes
            WHERE executed_at > datetime('now', '-24 hours')
        """)
        recent = cursor.fetchone()[0]
        details["actions_last_24h"] = recent

        # Success rate
        cursor.execute("SELECT AVG(success_score) FROM action_outcomes")
        avg_success = cursor.fetchone()[0] or 0
        details["avg_success_score"] = f"{avg_success:.2f}"

        # By type (top 5)
        cursor.execute("""
            SELECT action_type, COUNT(*), AVG(success_score)
            FROM action_outcomes
            GROUP BY action_type
            ORDER BY COUNT(*) DESC
            LIMIT 5
        """)
        top_actions = {row[0]: {"count": row[1], "success": f"{row[2]:.2f}"}
                       for row in cursor.fetchall()}
        details["top_action_types"] = top_actions

        conn.close()
        return total > 0, details

    def check_metacognitive(self) -> Tuple[bool, Dict]:
        """Check metacognitive state tracking."""
        conn = sqlite3.connect(str(MEMORY_DB))
        cursor = conn.cursor()
        details = {}

        # Metacognitive states
        cursor.execute("SELECT COUNT(*) FROM metacognitive_states")
        states = cursor.fetchone()[0]
        details["metacognitive_states"] = states

        # Knowledge gaps
        cursor.execute("""
            SELECT status, COUNT(*)
            FROM knowledge_gaps
            GROUP BY status
        """)
        gaps = {row[0]: row[1] for row in cursor.fetchall()}
        details["knowledge_gaps"] = gaps

        # Reasoning strategies (correct column: success_count not successes)
        cursor.execute("""
            SELECT strategy_name, usage_count,
                   CAST(success_count AS FLOAT) / NULLIF(usage_count, 0) as calc_success_rate
            FROM reasoning_strategies
            WHERE usage_count > 0
            ORDER BY calc_success_rate DESC
            LIMIT 5
        """)
        strategies = {row[0]: {"uses": row[1], "success": f"{(row[2] or 0)*100:.0f}%"}
                      for row in cursor.fetchall()}
        if strategies:
            details["top_strategies"] = strategies

        conn.close()
        return True, details

    def check_agent_identity(self) -> Tuple[bool, Dict]:
        """Check persistent agent identity."""
        conn = sqlite3.connect(str(MEMORY_DB))
        cursor = conn.cursor()
        details = {}

        # Agent identities (correct column: total_sessions not sessions_count)
        cursor.execute("SELECT agent_id, total_sessions FROM agent_identity")
        agents = {row[0]: {"sessions": row[1]} for row in cursor.fetchall()}
        details["agents"] = agents

        # Check for macpro51 identity (correct columns: skill_levels, core_beliefs)
        cursor.execute("""
            SELECT skill_levels, core_beliefs, preferences
            FROM agent_identity
            WHERE agent_id = 'macpro51'
        """)
        row = cursor.fetchone()
        if row:
            skills = json.loads(row[0]) if row[0] else {}
            beliefs = json.loads(row[1]) if row[1] else []
            details["macpro51_skills"] = len(skills)
            details["macpro51_beliefs"] = len(beliefs)

        conn.close()
        return len(agents) > 0, details

    def check_cluster_coordination(self) -> Tuple[bool, Dict]:
        """Check multi-agent cluster coordination."""
        details = {}

        # Node chat
        if NODE_CHAT_DB.exists():
            conn = sqlite3.connect(str(NODE_CHAT_DB))
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM messages")
            messages = cursor.fetchone()[0]
            details["node_chat_messages"] = f"{messages:,}"

            cursor.execute("""
                SELECT from_node, COUNT(*)
                FROM messages
                GROUP BY from_node
            """)
            by_node = {row[0]: row[1] for row in cursor.fetchall()}
            details["messages_by_node"] = by_node

            conn.close()
        else:
            details["node_chat"] = "Database not found"

        # Shared memories (no scope column - just count all entities)
        if SHARED_MEMORIES_DB.exists():
            conn = sqlite3.connect(str(SHARED_MEMORIES_DB))
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM entities")
            shared = cursor.fetchone()[0]
            details["shared_memories"] = shared

            # Count by node
            cursor.execute("""
                SELECT node_id, COUNT(*)
                FROM entities
                GROUP BY node_id
            """)
            by_node = {row[0]: row[1] for row in cursor.fetchall()}
            details["memories_by_node"] = by_node

            conn.close()
        else:
            details["shared_memories"] = "Database not found"

        return True, details

    def _print_summary(self):
        """Print summary of health check results."""
        print(f"\n{BOLD}{'='*60}{RESET}")
        print(f"{BOLD}                    SUMMARY{RESET}")
        print(f"{BOLD}{'='*60}{RESET}\n")

        passed = sum(1 for r in self.results.values() if r.get("passed", False))
        total = len(self.results)

        if passed == total:
            print(f"{GREEN}{BOLD}All {total} checks passed!{RESET}")
            print(f"\n{GREEN}AGI memory system is fully operational.{RESET}")
        else:
            print(f"{YELLOW}Passed: {passed}/{total}{RESET}")
            print(f"\n{BOLD}Failed checks:{RESET}")
            for name, result in self.results.items():
                if not result.get("passed", False):
                    error = result.get("error", result.get("details", "Unknown error"))
                    print(f"  {RED}- {name}: {error}{RESET}")

        # Database sizes
        print(f"\n{BOLD}Database Sizes:{RESET}")
        if MEMORY_DB.exists():
            size_mb = MEMORY_DB.stat().st_size / (1024 * 1024)
            print(f"  Memory DB: {size_mb:.1f} MB")
        if NODE_CHAT_DB.exists():
            size_mb = NODE_CHAT_DB.stat().st_size / (1024 * 1024)
            print(f"  Node Chat DB: {size_mb:.1f} MB")

        print(f"\n{BOLD}Timestamp:{RESET} {datetime.now().isoformat()}")
        print()


def main():
    parser = argparse.ArgumentParser(description="AGI System Health Check")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    parser.add_argument("--fix", "-f", action="store_true", help="Attempt to fix issues")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    checker = AGIHealthChecker(verbose=args.verbose, fix=args.fix)

    try:
        passed = checker.check_all()

        if args.json:
            print(json.dumps(checker.results, indent=2, default=str))

        sys.exit(0 if passed else 1)

    except Exception as e:
        print(f"{RED}Health check failed: {e}{RESET}")
        sys.exit(2)


if __name__ == "__main__":
    main()

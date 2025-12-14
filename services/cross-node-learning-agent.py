#!/usr/bin/env python3
"""
Cross-Node Learning Agent for macpro51

Monitors other cluster nodes and learns from their:
- Completion documents (what worked well)
- Error logs (what to avoid)
- Performance metrics (optimization opportunities)
- Configuration changes (best practices)
- MCP server usage patterns

This agent continuously improves macpro51 by incorporating
lessons learned from mac-studio and macbook-air.
"""
import os
import platform

import json
import subprocess
import logging
import time
import sqlite3
import hashlib
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

# Add cluster-deployment to path for cluster_config
sys.path.insert(0, str(Path(__file__).parent.parent / "cluster-deployment"))

# Auto-detect storage base for logging
try:
    from simple_cluster_config import get_node_config, get_local_node_id
    local_node = get_local_node_id()
    local_config = get_node_config(local_node)
    STORAGE_BASE = Path(local_config['storage_base'])
except:
    STORAGE_BASE = Path(str(_STORAGE_BASE))

# Ensure logs directory exists
(STORAGE_BASE / "logs").mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(STORAGE_BASE / "logs" / "cross-node-learning.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class NodeLesson:
    """A lesson learned from another node"""
    node_id: str
    lesson_type: str  # 'success', 'error', 'optimization', 'config'
    source_file: str
    content: str
    timestamp: datetime
    relevance_score: float = 0.0
    applied: bool = False
    application_notes: str = ""

@dataclass
class NodeStatus:
    """Current status of a cluster node"""
    node_id: str
    hostname: str
    ip_address: str
    last_seen: datetime
    available: bool
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    services_running: List[str] = field(default_factory=list)

class CrossNodeLearningAgent:
    """Agent that monitors and learns from other cluster nodes"""

    def __init__(self, storage_base: Optional[str] = None):
        # Auto-detect storage base if not provided
        if storage_base is None:
            try:
                from simple_cluster_config import get_node_config, get_local_node_id
                local_node = get_local_node_id()
                local_config = get_node_config(local_node)
                storage_base = local_config['storage_base']
            except:
                storage_base = str(_STORAGE_BASE)  # Fallback

        self.storage_base = Path(storage_base)
        self.db_path = self.storage_base / "databases" / "cluster" / "node_learning.db"
        self.nodes = self._init_nodes()
        self.lessons_learned = []

        # Initialize database
        self._init_database()

        logger.info(f"Cross-Node Learning Agent initialized on {self.local_node_id}")
        logger.info(f"Monitoring nodes: {list(self.nodes.keys())}")

    def _init_nodes(self) -> Dict[str, NodeStatus]:
        """Initialize node configurations from cluster config"""
        try:
            from simple_cluster_config import get_other_nodes, get_local_node_id

            self.local_node_id = get_local_node_id()
            other_nodes = get_other_nodes()

            nodes = {}
            for node_id, config in other_nodes.items():
                nodes[node_id] = NodeStatus(
                    node_id=node_id,
                    hostname=config['hostname'],
                    ip_address=config['ip'],
                    last_seen=datetime.now(),
                    available=False
                )

            return nodes

        except Exception as e:
            logger.warning(f"Could not load cluster config, using defaults: {e}")
            # Fallback to hardcoded nodes (for macpro51)
            return {
                "mac-studio": NodeStatus(
                    node_id="mac-studio",
                    hostname="mac-studio.local",
                    ip_address="192.168.1.16",
                    last_seen=datetime.now(),
                    available=False
                ),
                "macbook-air-m3": NodeStatus(
                    node_id="macbook-air-m3",
                    hostname="macbook-air.local",
                    ip_address="192.168.1.76",
                    last_seen=datetime.now(),
                    available=False
                )
            }

    def _init_database(self):
        """Initialize SQLite database for storing lessons"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT NOT NULL,
                    lesson_type TEXT NOT NULL,
                    source_file TEXT,
                    content TEXT NOT NULL,
                    content_hash TEXT UNIQUE,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    relevance_score REAL DEFAULT 0.0,
                    applied BOOLEAN DEFAULT 0,
                    application_notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS node_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cpu_usage REAL,
                    memory_usage REAL,
                    disk_usage REAL,
                    services_count INTEGER,
                    response_time_ms REAL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS improvements_applied (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lesson_id INTEGER,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    improvement_type TEXT,
                    description TEXT,
                    success BOOLEAN,
                    notes TEXT,
                    FOREIGN KEY (lesson_id) REFERENCES lessons(id)
                )
            """)

            conn.commit()

        logger.info(f"Database initialized at {self.db_path}")

    def check_node_availability(self, node_id: str) -> bool:
        """Check if a node is reachable"""
        node = self.nodes.get(node_id)
        if not node:
            return False

        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "1", node.ip_address],
                capture_output=True,
                timeout=2
            )
            available = result.returncode == 0
            node.available = available
            node.last_seen = datetime.now()
            return available
        except Exception as e:
            logger.warning(f"Failed to ping {node_id}: {e}")
            return False

    def fetch_node_documents(self, node_id: str, doc_patterns: List[str]) -> List[Tuple[str, str]]:
        """Fetch documents from a remote node"""
        node = self.nodes.get(node_id)
        if not node or not node.available:
            return []

        documents = []

        # Get base path from cluster config
        try:
            from simple_cluster_config import get_node_config
            node_config = get_node_config(node_id)
            base_path = node_config['storage_base']
        except:
            logger.warning(f"Could not get storage_base for {node_id}, skipping")
            return []

        for pattern in doc_patterns:
            try:

                # Find matching files
                result = subprocess.run(
                    ["ssh", node.ip_address, f"find {base_path} -maxdepth 1 -name '{pattern}' -type f 2>/dev/null"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    files = result.stdout.strip().split('\n')
                    for file_path in files:
                        if not file_path:
                            continue

                        # Fetch file content
                        content_result = subprocess.run(
                            ["ssh", node.ip_address, f"cat {file_path}"],
                            capture_output=True,
                            text=True,
                            timeout=30
                        )

                        if content_result.returncode == 0:
                            documents.append((file_path, content_result.stdout))
                            logger.info(f"Fetched {file_path} from {node_id}")

            except Exception as e:
                logger.error(f"Error fetching documents from {node_id}: {e}")

        return documents

    def extract_lessons(self, node_id: str, documents: List[Tuple[str, str]]) -> List[NodeLesson]:
        """Extract valuable lessons from documents"""
        lessons = []

        for file_path, content in documents:
            # Determine lesson type based on filename
            lesson_type = "success"
            if "COMPLETE" in file_path or "SUCCESS" in file_path:
                lesson_type = "success"
            elif "ERROR" in file_path or "FAIL" in file_path:
                lesson_type = "error"
            elif "OPTIMIZATION" in file_path or "PERFORMANCE" in file_path:
                lesson_type = "optimization"
            elif "CONFIG" in file_path or "SETUP" in file_path:
                lesson_type = "config"

            # Calculate relevance for Linux builder node
            relevance = self._calculate_relevance(content, lesson_type)

            if relevance > 0.3:  # Only keep lessons with >30% relevance
                lesson = NodeLesson(
                    node_id=node_id,
                    lesson_type=lesson_type,
                    source_file=file_path,
                    content=content,
                    timestamp=datetime.now(),
                    relevance_score=relevance
                )
                lessons.append(lesson)

        return lessons

    def _calculate_relevance(self, content: str, lesson_type: str) -> float:
        """Calculate relevance of a lesson to macpro51 (Linux builder)"""
        relevance = 0.0
        content_lower = content.lower()

        # Keywords relevant to Linux builder node
        linux_keywords = [
            'linux', 'fedora', 'podman', 'docker', 'container', 'build',
            'compilation', 'systemctl', 'raid', 'mdadm', 'selinux',
            'firewall', 'performance', 'benchmark', 'x86_64', 'testing'
        ]

        # General valuable keywords
        general_keywords = [
            'optimization', 'memory', 'cpu', 'disk', 'network', 'cluster',
            'distributed', 'database', 'mcp', 'monitoring', 'automation'
        ]

        # Count keyword matches
        linux_matches = sum(1 for kw in linux_keywords if kw in content_lower)
        general_matches = sum(1 for kw in general_keywords if kw in content_lower)

        # Base relevance on matches
        relevance = (linux_matches * 0.1) + (general_matches * 0.05)

        # Boost for success stories
        if lesson_type == "success":
            relevance *= 1.2

        # Boost for optimizations
        if lesson_type == "optimization":
            relevance *= 1.3

        return min(relevance, 1.0)

    def store_lesson(self, lesson: NodeLesson):
        """Store a lesson in the database"""
        content_hash = hashlib.sha256(lesson.content.encode()).hexdigest()

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO lessons
                    (node_id, lesson_type, source_file, content, content_hash, relevance_score)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    lesson.node_id,
                    lesson.lesson_type,
                    lesson.source_file,
                    lesson.content,
                    content_hash,
                    lesson.relevance_score
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing lesson: {e}")

    def get_top_lessons(self, limit: int = 10) -> List[Dict]:
        """Get top lessons by relevance that haven't been applied"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, node_id, lesson_type, source_file, relevance_score, timestamp
                FROM lessons
                WHERE applied = 0
                ORDER BY relevance_score DESC, timestamp DESC
                LIMIT ?
            """, (limit,))

            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row[0],
                    "node_id": row[1],
                    "lesson_type": row[2],
                    "source_file": row[3],
                    "relevance_score": row[4],
                    "timestamp": row[5]
                })

            return results

    def record_node_metrics(self, node_id: str):
        """Record performance metrics from a node"""
        node = self.nodes.get(node_id)
        if not node or not node.available:
            return

        try:
            # Get metrics via SSH
            result = subprocess.run(
                ["ssh", node.ip_address, "top -l 1 | grep 'CPU usage'; df -h / | tail -1"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                # Parse metrics (macOS format)
                lines = result.stdout.strip().split('\n')
                # Store basic metrics
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO node_metrics (node_id, response_time_ms)
                        VALUES (?, ?)
                    """, (node_id, 100))  # Placeholder
                    conn.commit()

        except Exception as e:
            logger.warning(f"Failed to record metrics for {node_id}: {e}")

    def discover_improvements(self) -> List[Dict]:
        """Discover potential improvements from learned lessons"""
        improvements = []

        # Analyze lessons for actionable improvements
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, node_id, lesson_type, content, relevance_score
                FROM lessons
                WHERE applied = 0 AND relevance_score > 0.5
                ORDER BY relevance_score DESC
                LIMIT 5
            """)

            for row in cursor.fetchall():
                lesson_id, node_id, lesson_type, content, score = row

                # Extract actionable items
                if lesson_type == "success":
                    improvements.append({
                        "lesson_id": lesson_id,
                        "type": "adopt_practice",
                        "description": f"Adopt successful practice from {node_id}",
                        "content_preview": content[:200]
                    })
                elif lesson_type == "optimization":
                    improvements.append({
                        "lesson_id": lesson_id,
                        "type": "apply_optimization",
                        "description": f"Apply optimization from {node_id}",
                        "content_preview": content[:200]
                    })

        return improvements

    def run_learning_cycle(self):
        """Run a complete learning cycle"""
        logger.info("Starting cross-node learning cycle")

        # Document patterns to look for on other nodes
        doc_patterns = [
            "*COMPLETE*.md",
            "*SUCCESS*.md",
            "*OPTIMIZATION*.md",
            "*STATUS*.md",
            "*PHASE*.md"
        ]

        for node_id in self.nodes.keys():
            logger.info(f"Learning from {node_id}...")

            # Check availability
            if not self.check_node_availability(node_id):
                logger.warning(f"{node_id} is not available")
                continue

            # Fetch documents
            documents = self.fetch_node_documents(node_id, doc_patterns)
            logger.info(f"Fetched {len(documents)} documents from {node_id}")

            # Extract lessons
            lessons = self.extract_lessons(node_id, documents)
            logger.info(f"Extracted {len(lessons)} lessons from {node_id}")

            # Store lessons
            for lesson in lessons:
                self.store_lesson(lesson)

            # Record metrics
            self.record_node_metrics(node_id)

        # Discover improvements
        improvements = self.discover_improvements()
        logger.info(f"Discovered {len(improvements)} potential improvements")

        return improvements

    def get_learning_summary(self) -> Dict:
        """Get summary of learning activities"""
        with sqlite3.connect(self.db_path) as conn:
            # Total lessons
            total_lessons = conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]

            # Lessons by type
            by_type = {}
            cursor = conn.execute("""
                SELECT lesson_type, COUNT(*)
                FROM lessons
                GROUP BY lesson_type
            """)
            for row in cursor.fetchall():
                by_type[row[0]] = row[1]

            # Lessons by node
            by_node = {}
            cursor = conn.execute("""
                SELECT node_id, COUNT(*)
                FROM lessons
                GROUP BY node_id
            """)
            for row in cursor.fetchall():
                by_node[row[0]] = row[1]

            # Applied improvements
            applied = conn.execute("""
                SELECT COUNT(*) FROM lessons WHERE applied = 1
            """).fetchone()[0]

            return {
                "total_lessons": total_lessons,
                "by_type": by_type,
                "by_node": by_node,
                "applied_improvements": applied,
                "pending_improvements": total_lessons - applied
            }

def main():
    """Main execution"""
    import argparse

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()


    parser = argparse.ArgumentParser(description="Cross-Node Learning Agent - Hive Mind Observer")
    parser.add_argument('--continuous', action='store_true', help='Run continuously (for systemd service)')
    parser.add_argument('--interval', type=int, default=300, help='Learning cycle interval in seconds (default: 300)')
    args = parser.parse_args()

    agent = CrossNodeLearningAgent()

    logger.info("Cross-Node Learning Agent started")
    logger.info("This agent will continuously learn from mac-studio and macbook-air")

    if args.continuous:
        logger.info(f"Running in continuous mode with {args.interval}s interval")
        cycle_count = 0

        while True:
            try:
                cycle_count += 1
                logger.info(f"=== Learning Cycle {cycle_count} ===")

                # Run learning cycle
                improvements = agent.run_learning_cycle()

                # Print summary
                summary = agent.get_learning_summary()
                logger.info(f"Cycle {cycle_count} Summary:")
                logger.info(f"  Total lessons: {summary['total_lessons']}")
                logger.info(f"  New improvements: {len(improvements)}")

                # Sleep until next cycle
                logger.info(f"Next cycle in {args.interval} seconds...")
                time.sleep(args.interval)

            except KeyboardInterrupt:
                logger.info("Shutting down gracefully...")
                break
            except Exception as e:
                logger.error(f"Error in learning cycle: {e}", exc_info=True)
                logger.info("Retrying in 60 seconds...")
                time.sleep(60)
    else:
        # Single run mode
        improvements = agent.run_learning_cycle()

        # Print summary
        summary = agent.get_learning_summary()
        logger.info("Learning Summary:")
        logger.info(f"  Total lessons learned: {summary['total_lessons']}")
        logger.info(f"  By type: {summary['by_type']}")
        logger.info(f"  By node: {summary['by_node']}")
        logger.info(f"  Applied improvements: {summary['applied_improvements']}")
        logger.info(f"  Potential improvements: {len(improvements)}")

        if improvements:
            logger.info("\nTop Potential Improvements:")
            for imp in improvements[:5]:
                logger.info(f"  - {imp['description']}")

        logger.info("\nTo view detailed lessons, check the database at:")
        logger.info(f"  {agent.db_path}")

if __name__ == "__main__":
    main()

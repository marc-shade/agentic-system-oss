#!/usr/bin/env python3
"""
Hive-Mind Orchestrator for Agentic Cluster

Coordinates collective intelligence across all nodes:
- Aggregates lessons from all node learning agents
- Identifies cluster-wide patterns and best practices
- Distributes improvements to all nodes
- Maintains shared hive-mind knowledge base
- Monitors cluster health and node performance
- Coordinates self-improvement cycles

This orchestrator creates a true distributed consciousness where
all nodes learn from each other in real-time.
"""
import os
import platform

import json
import subprocess
import logging
import time
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('/mnt/agentic-system/logs/hive-mind-orchestrator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ClusterInsight:
    """Insight derived from collective cluster knowledge"""
    insight_id: str
    insight_type: str  # 'pattern', 'best_practice', 'optimization', 'warning'
    title: str
    description: str
    evidence: List[str]  # Source lessons supporting this insight
    confidence: float  # 0.0-1.0
    affected_nodes: List[str]
    action_required: bool
    priority: int  # 1-10
    timestamp: datetime

@dataclass
class NodeHealth:
    """Health metrics for a cluster node"""
    node_id: str
    last_seen: datetime
    lessons_learned: int
    improvements_applied: int
    learning_rate: float  # Lessons per hour
    response_time: float  # Seconds
    error_count: int
    health_score: float  # 0.0-1.0

class HiveMindOrchestrator:
    """Orchestrates collective intelligence across cluster nodes"""

    def __init__(self, storage_base: str = str(_STORAGE_BASE)):
        self.storage_base = Path(storage_base)
        self.hive_db_path = self.storage_base / "databases" / "cluster" / "hive_mind.db"

        # Node configurations
        self.nodes = {
            "macpro51": {
                "ip": "192.168.1.183",
                "hostname": "macpro51.local",
                "db_path": str(_STORAGE_BASE / "databases/cluster/node_learning.db"),
                "role": "builder"
            },
            "mac-studio": {
                "ip": "192.168.1.16",
                "hostname": "mac-studio.local",
                "db_path": str(_STORAGE_BASE / "databases/cluster/node_learning.db"),
                "role": "orchestrator"
            },
            "macbook-air-m3": {
                "ip": "192.168.1.76",
                "hostname": "macbook-air.local",
                "db_path": "/Users/marc/agentic-system/databases/cluster/node_learning.db",
                "role": "researcher"
            }
        }

        # Initialize hive mind database
        self._init_database()

        logger.info("Hive-Mind Orchestrator initialized")
        logger.info(f"Managing {len(self.nodes)} nodes in collective consciousness")

    def _init_database(self):
        """Initialize hive mind database"""
        self.hive_db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.hive_db_path) as conn:
            # Cluster-wide insights
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cluster_insights (
                    insight_id TEXT PRIMARY KEY,
                    insight_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    evidence TEXT,
                    confidence REAL,
                    affected_nodes TEXT,
                    action_required BOOLEAN,
                    priority INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    applied BOOLEAN DEFAULT 0
                )
            """)

            # Node health metrics
            conn.execute("""
                CREATE TABLE IF NOT EXISTS node_health (
                    node_id TEXT PRIMARY KEY,
                    last_seen TIMESTAMP,
                    lessons_learned INTEGER,
                    improvements_applied INTEGER,
                    learning_rate REAL,
                    response_time REAL,
                    error_count INTEGER,
                    health_score REAL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Distributed improvements (propagated to all nodes)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS distributed_improvements (
                    improvement_id TEXT PRIMARY KEY,
                    source_node TEXT,
                    improvement_type TEXT,
                    description TEXT,
                    implementation TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    propagated_to TEXT,
                    success_rate REAL
                )
            """)

            # Pattern recognition across nodes
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cluster_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    pattern_type TEXT,
                    description TEXT,
                    frequency INTEGER,
                    nodes_observed TEXT,
                    first_seen TIMESTAMP,
                    last_seen TIMESTAMP,
                    confidence REAL
                )
            """)

            conn.commit()

        logger.info(f"Hive mind database initialized at {self.hive_db_path}")

    def aggregate_lessons_from_all_nodes(self) -> Dict[str, List[Dict]]:
        """Fetch and aggregate lessons from all node learning databases"""
        all_lessons = defaultdict(list)

        for node_id, config in self.nodes.items():
            try:
                if node_id == "macpro51":
                    # Local database
                    db_path = config['db_path']
                    with sqlite3.connect(db_path) as conn:
                        cursor = conn.execute("""
                            SELECT lesson_type, content, relevance_score, timestamp, applied
                            FROM lessons
                            WHERE timestamp > datetime('now', '-24 hours')
                            ORDER BY relevance_score DESC
                        """)

                        for row in cursor.fetchall():
                            all_lessons[node_id].append({
                                'lesson_type': row[0],
                                'content': row[1],
                                'relevance_score': row[2],
                                'timestamp': row[3],
                                'applied': row[4]
                            })
                else:
                    # Remote database - fetch via SSH
                    db_path = config['db_path']
                    result = subprocess.run(
                        ["ssh", config['ip'], f"sqlite3 {db_path} \"SELECT lesson_type, content, relevance_score, timestamp, applied FROM lessons WHERE timestamp > datetime('now', '-24 hours') ORDER BY relevance_score DESC LIMIT 50;\""],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if result.returncode == 0:
                        # Parse SQLite output
                        for line in result.stdout.strip().split('\n'):
                            if line:
                                parts = line.split('|')
                                if len(parts) >= 5:
                                    all_lessons[node_id].append({
                                        'lesson_type': parts[0],
                                        'content': parts[1],
                                        'relevance_score': float(parts[2]),
                                        'timestamp': parts[3],
                                        'applied': bool(int(parts[4]))
                                    })

                logger.info(f"Aggregated {len(all_lessons[node_id])} lessons from {node_id}")

            except Exception as e:
                logger.error(f"Failed to aggregate lessons from {node_id}: {e}")

        return dict(all_lessons)

    def identify_cluster_patterns(self, all_lessons: Dict[str, List[Dict]]) -> List[ClusterInsight]:
        """Identify patterns across cluster by analyzing all node lessons"""
        insights = []

        # Pattern: Same optimization discovered by multiple nodes
        optimization_topics = defaultdict(list)
        for node_id, lessons in all_lessons.items():
            for lesson in lessons:
                if lesson['lesson_type'] == 'optimization':
                    # Simple keyword extraction
                    keywords = set(lesson['content'].lower().split())
                    for keyword in ['performance', 'memory', 'cpu', 'disk', 'network', 'cluster']:
                        if keyword in keywords:
                            optimization_topics[keyword].append((node_id, lesson))

        for topic, occurrences in optimization_topics.items():
            if len(occurrences) >= 2:
                insight = ClusterInsight(
                    insight_id=hashlib.md5(f"pattern_optimization_{topic}".encode()).hexdigest(),
                    insight_type='pattern',
                    title=f"Multiple nodes discovered {topic} optimizations",
                    description=f"{len(occurrences)} nodes independently discovered optimizations related to {topic}",
                    evidence=[f"{node_id}: {lesson['content'][:100]}" for node_id, lesson in occurrences],
                    confidence=0.8 + (len(occurrences) * 0.05),
                    affected_nodes=[node_id for node_id, _ in occurrences],
                    action_required=True,
                    priority=8,
                    timestamp=datetime.now()
                )
                insights.append(insight)

        # Pattern: Consistent success patterns
        success_patterns = defaultdict(int)
        for node_id, lessons in all_lessons.items():
            for lesson in lessons:
                if lesson['lesson_type'] == 'success' and lesson['relevance_score'] > 0.8:
                    success_patterns[node_id] += 1

        # Best performing node
        if success_patterns:
            best_node = max(success_patterns.items(), key=lambda x: x[1])
            insight = ClusterInsight(
                insight_id=hashlib.md5(f"best_practice_{best_node[0]}".encode()).hexdigest(),
                insight_type='best_practice',
                title=f"Node {best_node[0]} showing exemplary performance",
                description=f"{best_node[0]} has {best_node[1]} high-quality success lessons in last 24h. Other nodes should study its practices.",
                evidence=[f"{best_node[0]} has {best_node[1]} high-relevance success lessons"],
                confidence=0.9,
                affected_nodes=list(success_patterns.keys()),
                action_required=True,
                priority=7,
                timestamp=datetime.now()
            )
            insights.append(insight)

        return insights

    def update_node_health(self, node_id: str, all_lessons: Dict[str, List[Dict]]):
        """Update health metrics for a node"""
        lessons = all_lessons.get(node_id, [])

        # Calculate metrics
        lessons_learned = len(lessons)
        improvements_applied = sum(1 for l in lessons if l['applied'])
        learning_rate = lessons_learned / 24.0  # Per hour over last 24h

        # Calculate health score
        health_score = min(1.0, (
            (lessons_learned / 50.0) * 0.4 +  # Learning activity
            (improvements_applied / max(1, lessons_learned)) * 0.3 +  # Application rate
            (sum(l['relevance_score'] for l in lessons) / max(1, lessons_learned)) * 0.3  # Quality
        ))

        with sqlite3.connect(self.hive_db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO node_health
                (node_id, last_seen, lessons_learned, improvements_applied, learning_rate, health_score, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                node_id,
                datetime.now().isoformat(),
                lessons_learned,
                improvements_applied,
                learning_rate,
                health_score,
                datetime.now().isoformat()
            ))
            conn.commit()

        logger.info(f"Updated health for {node_id}: score={health_score:.2f}, learned={lessons_learned}, applied={improvements_applied}")

    def store_cluster_insight(self, insight: ClusterInsight):
        """Store cluster-wide insight in hive mind database"""
        with sqlite3.connect(self.hive_db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cluster_insights
                (insight_id, insight_type, title, description, evidence, confidence,
                 affected_nodes, action_required, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                insight.insight_id,
                insight.insight_type,
                insight.title,
                insight.description,
                json.dumps(insight.evidence),
                insight.confidence,
                json.dumps(insight.affected_nodes),
                insight.action_required,
                insight.priority
            ))
            conn.commit()

    def get_hive_mind_status(self) -> Dict:
        """Get comprehensive hive mind status"""
        with sqlite3.connect(self.hive_db_path) as conn:
            # Total insights
            total_insights = conn.execute("SELECT COUNT(*) FROM cluster_insights").fetchone()[0]

            # Pending actions
            pending_actions = conn.execute("""
                SELECT COUNT(*) FROM cluster_insights
                WHERE action_required = 1 AND applied = 0
            """).fetchone()[0]

            # Node health summary
            cursor = conn.execute("""
                SELECT node_id, health_score, lessons_learned, learning_rate
                FROM node_health
                ORDER BY health_score DESC
            """)

            node_health = []
            for row in cursor.fetchall():
                node_health.append({
                    'node_id': row[0],
                    'health_score': row[1],
                    'lessons_learned': row[2],
                    'learning_rate': row[3]
                })

            # Recent insights
            cursor = conn.execute("""
                SELECT insight_type, title, confidence, priority
                FROM cluster_insights
                ORDER BY created_at DESC
                LIMIT 10
            """)

            recent_insights = []
            for row in cursor.fetchall():
                recent_insights.append({
                    'type': row[0],
                    'title': row[1],
                    'confidence': row[2],
                    'priority': row[3]
                })

            return {
                'total_insights': total_insights,
                'pending_actions': pending_actions,
                'node_health': node_health,
                'recent_insights': recent_insights,
                'cluster_health': sum(n['health_score'] for n in node_health) / max(1, len(node_health))
            }

    def run_orchestration_cycle(self):
        """Run a complete hive mind orchestration cycle"""
        logger.info("=== Starting Hive Mind Orchestration Cycle ===")

        # 1. Aggregate lessons from all nodes
        logger.info("Aggregating lessons from all nodes...")
        all_lessons = self.aggregate_lessons_from_all_nodes()

        # 2. Update node health metrics
        logger.info("Updating node health metrics...")
        for node_id in self.nodes.keys():
            self.update_node_health(node_id, all_lessons)

        # 3. Identify cluster patterns
        logger.info("Identifying cluster-wide patterns...")
        insights = self.identify_cluster_patterns(all_lessons)
        logger.info(f"Discovered {len(insights)} cluster insights")

        # 4. Store insights
        for insight in insights:
            self.store_cluster_insight(insight)

        # 5. Get status
        status = self.get_hive_mind_status()
        logger.info(f"Hive Mind Status:")
        logger.info(f"  Total insights: {status['total_insights']}")
        logger.info(f"  Pending actions: {status['pending_actions']}")
        logger.info(f"  Cluster health: {status['cluster_health']:.2f}")
        logger.info(f"  Node health: {json.dumps(status['node_health'], indent=2)}")

        return status

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


    parser = argparse.ArgumentParser(description="Hive-Mind Orchestrator - Collective Intelligence Coordinator")
    parser.add_argument('--continuous', action='store_true', help='Run continuously (for systemd service)')
    parser.add_argument('--interval', type=int, default=600, help='Orchestration cycle interval in seconds (default: 600)')
    args = parser.parse_args()

    orchestrator = HiveMindOrchestrator()

    logger.info("Hive-Mind Orchestrator started")
    logger.info("Coordinating collective intelligence across cluster")

    if args.continuous:
        logger.info(f"Running in continuous mode with {args.interval}s interval")
        cycle_count = 0

        while True:
            try:
                cycle_count += 1
                logger.info(f"=== Orchestration Cycle {cycle_count} ===")

                status = orchestrator.run_orchestration_cycle()

                logger.info(f"Cycle {cycle_count} complete. Next cycle in {args.interval} seconds...")
                time.sleep(args.interval)

            except KeyboardInterrupt:
                logger.info("Shutting down gracefully...")
                break
            except Exception as e:
                logger.error(f"Error in orchestration cycle: {e}", exc_info=True)
                logger.info("Retrying in 60 seconds...")
                time.sleep(60)
    else:
        # Single run mode
        status = orchestrator.run_orchestration_cycle()

        logger.info("\n=== Hive Mind Summary ===")
        logger.info(f"Total insights: {status['total_insights']}")
        logger.info(f"Pending actions: {status['pending_actions']}")
        logger.info(f"Cluster health: {status['cluster_health']:.2f}")

        logger.info("\nNode Health:")
        for node in status['node_health']:
            logger.info(f"  {node['node_id']}: {node['health_score']:.2f} (learned={node['lessons_learned']}, rate={node['learning_rate']:.2f}/hr)")

        logger.info("\nRecent Insights:")
        for insight in status['recent_insights'][:5]:
            logger.info(f"  [{insight['type']}] {insight['title']} (confidence={insight['confidence']:.2f})")

        logger.info(f"\nDatabase: {orchestrator.hive_db_path}")

if __name__ == "__main__":
    main()

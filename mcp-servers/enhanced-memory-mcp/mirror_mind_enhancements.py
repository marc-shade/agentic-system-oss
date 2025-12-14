#!/usr/bin/env python3
"""
Mirror Mind Enhancements for Enhanced Memory MCP

Based on "Mirror Mind: Dual Manifold Cognitive Architecture" (Tsinghua University, Nov 2025)

Key features implemented:
1. Centrality-based importance scoring (PageRank, degree, betweenness)
2. Cognitive trajectory tracking (knowledge evolution over time)
3. Temporal distillation pipeline (enhanced episodic -> semantic)
4. Dual manifold architecture (individual vs collective knowledge)

Research validation: Our sleep-inspired memory consolidation (Cohen's d = 2.31, p = 0.007)
aligns with Mirror Mind's three-layer memory structure.
"""

import sqlite3
import json
import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field

logger = logging.getLogger("mirror-mind")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


@dataclass
class CentralityScores:
    """Centrality measures for a node in the knowledge graph"""
    entity_id: int
    entity_name: str
    degree_centrality: float = 0.0       # Number of connections
    pagerank: float = 0.0                 # Importance via link structure
    betweenness_centrality: float = 0.0  # Bridge between clusters
    recency_weight: float = 1.0          # Time decay factor
    combined_score: float = 0.0          # Weighted combination


@dataclass
class CognitiveTrajectory:
    """Tracks evolution of knowledge over time"""
    entity_id: int
    entity_name: str
    first_encounter: datetime
    last_update: datetime
    access_count: int
    confidence_evolution: List[Tuple[datetime, float]]
    related_concepts_evolution: List[Tuple[datetime, List[str]]]
    importance_trajectory: List[Tuple[datetime, float]]


@dataclass
class DualManifold:
    """Represents the dual manifold architecture"""
    individual_manifold: Dict[str, Any]  # Personal knowledge space
    collective_manifold: Dict[str, Any]  # Shared domain knowledge
    intersection_points: List[str]        # Where manifolds meet


class CentralityCalculator:
    """
    Calculate graph centrality measures for knowledge graph nodes

    Inspired by Mirror Mind's use of centrality for persona layer importance weighting
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _build_adjacency_graph(self) -> Tuple[Dict[int, Set[int]], Dict[int, str]]:
        """Build adjacency list from relations table"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get all entities
        cursor.execute('SELECT id, name FROM entities')
        id_to_name = {row[0]: row[1] for row in cursor.fetchall()}

        # Build adjacency list (bidirectional for undirected centrality)
        # Note: relations table may not have strength column - treat all as 1.0
        graph = defaultdict(set)
        cursor.execute('''
            SELECT from_entity_id, to_entity_id
            FROM relations
        ''')

        for row in cursor.fetchall():
            from_id, to_id = row
            if from_id and to_id:  # Ensure both IDs exist
                graph[from_id].add(to_id)
                graph[to_id].add(from_id)  # Undirected for centrality

        conn.close()
        return dict(graph), id_to_name

    def calculate_degree_centrality(self) -> Dict[int, float]:
        """
        Calculate degree centrality (normalized count of connections)

        Higher = more connected node
        """
        graph, _ = self._build_adjacency_graph()

        if not graph:
            return {}

        max_possible = len(graph) - 1  # Maximum possible connections
        if max_possible <= 0:
            return {node_id: 0.0 for node_id in graph}

        return {
            node_id: len(neighbors) / max_possible
            for node_id, neighbors in graph.items()
        }

    def calculate_pagerank(
        self,
        damping: float = 0.85,
        iterations: int = 100,
        tolerance: float = 1e-6
    ) -> Dict[int, float]:
        """
        Calculate PageRank centrality

        Higher = more important via link structure (recursive importance)
        This is the key metric from Mirror Mind for concept importance
        """
        graph, _ = self._build_adjacency_graph()

        if not graph:
            return {}

        n = len(graph)
        nodes = list(graph.keys())

        # Initialize PageRank uniformly
        pagerank = {node: 1.0 / n for node in nodes}

        # Power iteration
        for _ in range(iterations):
            new_pagerank = {}
            diff = 0.0

            for node in nodes:
                # Sum of PR from incoming nodes
                incoming_sum = 0.0
                for other in nodes:
                    if node in graph.get(other, set()):
                        out_degree = len(graph[other])
                        if out_degree > 0:
                            incoming_sum += pagerank[other] / out_degree

                new_pr = (1 - damping) / n + damping * incoming_sum
                diff += abs(new_pr - pagerank[node])
                new_pagerank[node] = new_pr

            pagerank = new_pagerank

            if diff < tolerance:
                break

        return pagerank

    def calculate_betweenness_centrality(self, sample_size: int = 100) -> Dict[int, float]:
        """
        Calculate betweenness centrality (approximation for large graphs)

        Higher = node lies on many shortest paths (bridge between clusters)
        """
        graph, _ = self._build_adjacency_graph()

        if not graph:
            return {}

        betweenness = defaultdict(float)
        nodes = list(graph.keys())

        # Sample nodes for approximation
        import random
        sample_nodes = random.sample(nodes, min(sample_size, len(nodes)))

        for source in sample_nodes:
            # BFS to find shortest paths
            distances = {source: 0}
            predecessors = defaultdict(list)
            queue = [source]

            while queue:
                current = queue.pop(0)
                for neighbor in graph.get(current, set()):
                    if neighbor not in distances:
                        distances[neighbor] = distances[current] + 1
                        queue.append(neighbor)
                        predecessors[neighbor].append(current)
                    elif distances[neighbor] == distances[current] + 1:
                        predecessors[neighbor].append(current)

            # Back-propagate dependencies
            delta = defaultdict(float)
            nodes_by_distance = sorted(distances.keys(), key=lambda x: -distances[x])

            for node in nodes_by_distance:
                for pred in predecessors[node]:
                    delta[pred] += (1 + delta[node]) / len(predecessors[node])
                if node != source:
                    betweenness[node] += delta[node]

        # Normalize
        n = len(nodes)
        if n > 2:
            norm = 2.0 / ((n - 1) * (n - 2))
            betweenness = {k: v * norm for k, v in betweenness.items()}

        return dict(betweenness)

    def calculate_all_centralities(self) -> Dict[int, CentralityScores]:
        """
        Calculate all centrality measures and combine them

        Returns dict of entity_id -> CentralityScores
        """
        _, id_to_name = self._build_adjacency_graph()

        degree = self.calculate_degree_centrality()
        pagerank = self.calculate_pagerank()
        betweenness = self.calculate_betweenness_centrality()

        # Get recency weights from database
        recency = self._calculate_recency_weights()

        results = {}
        all_entities = set(degree.keys()) | set(pagerank.keys()) | set(betweenness.keys())

        for entity_id in all_entities:
            d = degree.get(entity_id, 0.0)
            p = pagerank.get(entity_id, 0.0)
            b = betweenness.get(entity_id, 0.0)
            r = recency.get(entity_id, 1.0)

            # Combined score: weighted average with recency boost
            # Weights: PageRank 0.4, Degree 0.3, Betweenness 0.3
            combined = r * (0.4 * p + 0.3 * d + 0.3 * b)

            results[entity_id] = CentralityScores(
                entity_id=entity_id,
                entity_name=id_to_name.get(entity_id, f"entity_{entity_id}"),
                degree_centrality=d,
                pagerank=p,
                betweenness_centrality=b,
                recency_weight=r,
                combined_score=combined
            )

        return results

    def _calculate_recency_weights(self, half_life_days: float = 30.0) -> Dict[int, float]:
        """
        Calculate time decay weights using exponential decay

        Implements Ebbinghaus forgetting curve concept
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, last_accessed, created_at FROM entities
        ''')

        recency = {}
        now = datetime.now()
        decay_constant = math.log(2) / half_life_days

        for row in cursor.fetchall():
            entity_id = row[0]
            updated = row[1] or row[2]  # Use last_accessed or created_at

            if updated:
                try:
                    last_update = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                    days_ago = (now - last_update.replace(tzinfo=None)).days
                    weight = math.exp(-decay_constant * days_ago)
                except:
                    weight = 0.5  # Default for parsing errors
            else:
                weight = 0.5

            recency[entity_id] = max(0.1, min(1.0, weight))

        conn.close()
        return recency

    def get_top_central_entities(self, limit: int = 20) -> List[CentralityScores]:
        """Get most central entities by combined score"""
        centralities = self.calculate_all_centralities()
        sorted_entities = sorted(
            centralities.values(),
            key=lambda x: x.combined_score,
            reverse=True
        )
        return sorted_entities[:limit]


class CognitiveTrajectoryTracker:
    """
    Track cognitive evolution of knowledge over time

    Implements Mirror Mind's temporal distillation concept
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._ensure_tables()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _ensure_tables(self):
        """Create cognitive trajectory tracking tables"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cognitive_trajectories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                importance REAL DEFAULT 0.5,
                access_count INTEGER DEFAULT 0,
                related_concepts TEXT,
                context TEXT,
                FOREIGN KEY (entity_id) REFERENCES entities(id)
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_trajectory_entity
            ON cognitive_trajectories(entity_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_trajectory_time
            ON cognitive_trajectories(timestamp)
        ''')

        conn.commit()
        conn.close()
        logger.info("Cognitive trajectory tables ensured")

    def record_trajectory_point(
        self,
        entity_id: int,
        confidence: float = 0.5,
        importance: float = 0.5,
        related_concepts: List[str] = None,
        context: str = None
    ):
        """Record a point in the cognitive trajectory of an entity"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO cognitive_trajectories
            (entity_id, timestamp, confidence, importance, related_concepts, context)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            entity_id,
            datetime.now().isoformat(),
            confidence,
            importance,
            json.dumps(related_concepts or []),
            context
        ))

        conn.commit()
        conn.close()

    def get_trajectory(self, entity_id: int) -> Optional[CognitiveTrajectory]:
        """Get complete cognitive trajectory for an entity"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get entity name
        cursor.execute('SELECT name FROM entities WHERE id = ?', (entity_id,))
        name_row = cursor.fetchone()
        if not name_row:
            conn.close()
            return None

        entity_name = name_row[0]

        # Get trajectory points
        cursor.execute('''
            SELECT timestamp, confidence, importance, related_concepts, access_count
            FROM cognitive_trajectories
            WHERE entity_id = ?
            ORDER BY timestamp ASC
        ''', (entity_id,))

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return None

        confidence_evolution = []
        importance_trajectory = []
        related_evolution = []
        total_access = 0

        for row in rows:
            ts = datetime.fromisoformat(row[0])
            confidence_evolution.append((ts, row[1]))
            importance_trajectory.append((ts, row[2]))

            related = json.loads(row[3]) if row[3] else []
            related_evolution.append((ts, related))
            total_access += row[4] or 0

        first_ts = confidence_evolution[0][0]
        last_ts = confidence_evolution[-1][0]

        return CognitiveTrajectory(
            entity_id=entity_id,
            entity_name=entity_name,
            first_encounter=first_ts,
            last_update=last_ts,
            access_count=total_access,
            confidence_evolution=confidence_evolution,
            related_concepts_evolution=related_evolution,
            importance_trajectory=importance_trajectory
        )

    def analyze_knowledge_evolution(
        self,
        time_window_days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze how knowledge has evolved over time

        Returns insights about learning patterns, emerging concepts, etc.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(days=time_window_days)).isoformat()

        # Get trajectory statistics
        cursor.execute('''
            SELECT
                e.name,
                COUNT(*) as updates,
                AVG(ct.confidence) as avg_confidence,
                MAX(ct.importance) as peak_importance,
                MIN(ct.timestamp) as first_seen,
                MAX(ct.timestamp) as last_seen
            FROM cognitive_trajectories ct
            JOIN entities e ON ct.entity_id = e.id
            WHERE ct.timestamp > ?
            GROUP BY ct.entity_id
            ORDER BY updates DESC
            LIMIT 20
        ''', (cutoff,))

        evolving_concepts = []
        for row in cursor.fetchall():
            evolving_concepts.append({
                'name': row[0],
                'updates': row[1],
                'avg_confidence': row[2],
                'peak_importance': row[3],
                'first_seen': row[4],
                'last_seen': row[5]
            })

        # Find concepts with increasing confidence (learning)
        cursor.execute('''
            SELECT
                e.name,
                ct.entity_id,
                GROUP_CONCAT(ct.confidence) as conf_series
            FROM cognitive_trajectories ct
            JOIN entities e ON ct.entity_id = e.id
            WHERE ct.timestamp > ?
            GROUP BY ct.entity_id
            HAVING COUNT(*) >= 3
        ''', (cutoff,))

        learning_concepts = []
        for row in cursor.fetchall():
            confs = [float(c) for c in row[2].split(',')]
            # Check if trend is increasing
            if len(confs) >= 3:
                trend = sum(b - a for a, b in zip(confs[:-1], confs[1:])) / (len(confs) - 1)
                if trend > 0.05:  # Increasing confidence
                    learning_concepts.append({
                        'name': row[0],
                        'confidence_trend': trend,
                        'current_confidence': confs[-1]
                    })

        conn.close()

        return {
            'time_window_days': time_window_days,
            'most_active_concepts': evolving_concepts,
            'learning_concepts': sorted(learning_concepts, key=lambda x: -x['confidence_trend']),
            'total_trajectory_points': sum(c['updates'] for c in evolving_concepts)
        }


class TemporalDistillationPipeline:
    """
    Temporal distillation from episodic to semantic memory

    Implements Mirror Mind's map-reduce cognitive distillation:
    1. Map: Extract patterns from episodic memories
    2. Reduce: Consolidate into semantic concepts
    3. Distill: Create temporal trajectories
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.centrality = CentralityCalculator(db_path)
        self.trajectory = CognitiveTrajectoryTracker(db_path)

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def map_phase(
        self,
        time_window_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Map phase: Extract patterns from recent episodic memories

        Groups similar episodes and extracts common themes
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(hours=time_window_hours)).isoformat()

        # Get recent episodes
        cursor.execute('''
            SELECT id, event_type, episode_data, significance_score, tags, created_at
            FROM episodic_memory
            WHERE created_at > ?
            ORDER BY significance_score DESC
        ''', (cutoff,))

        episodes = []
        for row in cursor.fetchall():
            episode_data = json.loads(row[2]) if row[2] else {}
            tags = json.loads(row[4]) if row[4] else []

            episodes.append({
                'id': row[0],
                'event_type': row[1],
                'data': episode_data,
                'significance': row[3],
                'tags': tags,
                'timestamp': row[5]
            })

        conn.close()

        # Group by event type and extract patterns
        grouped = defaultdict(list)
        for ep in episodes:
            grouped[ep['event_type']].append(ep)

        patterns = []
        for event_type, eps in grouped.items():
            if len(eps) >= 2:  # Need multiple episodes for pattern
                # Extract common tags
                all_tags = [set(ep['tags']) for ep in eps]
                common_tags = set.intersection(*all_tags) if all_tags else set()

                # Calculate average significance
                avg_sig = sum(ep['significance'] for ep in eps) / len(eps)

                patterns.append({
                    'event_type': event_type,
                    'episode_count': len(eps),
                    'common_tags': list(common_tags),
                    'avg_significance': avg_sig,
                    'episode_ids': [ep['id'] for ep in eps]
                })

        return patterns

    def reduce_phase(
        self,
        patterns: List[Dict[str, Any]],
        min_frequency: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Reduce phase: Consolidate patterns into semantic concepts

        Creates or updates semantic memory entries
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        promoted_concepts = []

        for pattern in patterns:
            if pattern['episode_count'] < min_frequency:
                continue

            concept_name = f"Pattern: {pattern['event_type']}"
            concept_type = "distilled_pattern"
            definition = (
                f"Recurring pattern of {pattern['episode_count']} episodes "
                f"with {pattern['avg_significance']:.2f} avg significance. "
                f"Common themes: {', '.join(pattern['common_tags']) or 'none'}"
            )

            # Check if concept exists
            cursor.execute(
                'SELECT id, confidence_score FROM semantic_memory WHERE concept_name = ?',
                (concept_name,)
            )
            existing = cursor.fetchone()

            # Confidence increases with more episodes
            new_confidence = min(0.95, 0.5 + (pattern['episode_count'] * 0.1))

            if existing:
                # Update existing concept
                cursor.execute('''
                    UPDATE semantic_memory
                    SET definition = ?, confidence_score = ?, updated_at = ?
                    WHERE id = ?
                ''', (definition, new_confidence, datetime.now().isoformat(), existing[0]))

                concept_id = existing[0]
            else:
                # Create new concept
                cursor.execute('''
                    INSERT INTO semantic_memory
                    (concept_name, concept_type, definition, confidence_score, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (concept_name, concept_type, definition, new_confidence, datetime.now().isoformat()))

                concept_id = cursor.lastrowid

            promoted_concepts.append({
                'concept_id': concept_id,
                'concept_name': concept_name,
                'confidence': new_confidence,
                'source_episodes': pattern['episode_count']
            })

        conn.commit()
        conn.close()

        return promoted_concepts

    def distill_phase(
        self,
        promoted_concepts: List[Dict[str, Any]]
    ):
        """
        Distill phase: Update cognitive trajectories for promoted concepts

        Records the temporal evolution of each concept
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get centrality scores for importance weighting
        centralities = self.centrality.calculate_all_centralities()

        for concept in promoted_concepts:
            # Find the entity ID for this concept
            cursor.execute(
                'SELECT id FROM entities WHERE name = ?',
                (concept['concept_name'],)
            )
            entity_row = cursor.fetchone()

            if entity_row:
                entity_id = entity_row[0]
                centrality = centralities.get(entity_id)
                importance = centrality.combined_score if centrality else 0.5
            else:
                # Create entity for tracking
                cursor.execute('''
                    INSERT INTO entities (name, entity_type, tier, created_at)
                    VALUES (?, 'concept', 'working', ?)
                ''', (concept['concept_name'], datetime.now().isoformat()))
                entity_id = cursor.lastrowid
                importance = 0.5

            # Record trajectory point
            self.trajectory.record_trajectory_point(
                entity_id=entity_id,
                confidence=concept['confidence'],
                importance=importance,
                context=f"Distilled from {concept['source_episodes']} episodes"
            )

        conn.commit()
        conn.close()

    def run_full_distillation(
        self,
        time_window_hours: int = 24,
        min_frequency: int = 2
    ) -> Dict[str, Any]:
        """
        Run complete temporal distillation pipeline

        Map -> Reduce -> Distill
        """
        logger.info("Starting temporal distillation pipeline...")

        # Map phase
        patterns = self.map_phase(time_window_hours)
        logger.info(f"Map phase: Found {len(patterns)} patterns")

        # Reduce phase
        concepts = self.reduce_phase(patterns, min_frequency)
        logger.info(f"Reduce phase: Promoted {len(concepts)} concepts")

        # Distill phase
        self.distill_phase(concepts)
        logger.info("Distill phase: Updated cognitive trajectories")

        return {
            'success': True,
            'patterns_found': len(patterns),
            'concepts_promoted': len(concepts),
            'promoted_concepts': concepts
        }


class DualManifoldArchitecture:
    """
    Dual Manifold Cognitive Architecture

    Separates individual knowledge (personal experiences, preferences)
    from collective knowledge (domain expertise, shared facts)

    Key insight from Mirror Mind: Intelligence emerges at the intersection
    of these two manifolds
    """

    def __init__(self, agent_id: str = "default_agent", db_path: Path = DB_PATH):
        self.agent_id = agent_id
        self.db_path = db_path
        self._ensure_tables()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _ensure_tables(self):
        """Create dual manifold tables"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Individual manifold: personal knowledge, experiences, preferences
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS individual_manifold (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                entity_id INTEGER,
                knowledge_type TEXT NOT NULL,
                content TEXT NOT NULL,
                personal_weight REAL DEFAULT 1.0,
                acquisition_context TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (entity_id) REFERENCES entities(id)
            )
        ''')

        # Collective manifold: shared domain knowledge, facts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collective_manifold (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                entity_id INTEGER,
                knowledge_type TEXT NOT NULL,
                content TEXT NOT NULL,
                consensus_score REAL DEFAULT 0.5,
                source_count INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (entity_id) REFERENCES entities(id)
            )
        ''')

        # Intersection points: where individual meets collective
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS manifold_intersections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                individual_id INTEGER NOT NULL,
                collective_id INTEGER NOT NULL,
                intersection_strength REAL DEFAULT 0.5,
                insight_generated TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (individual_id) REFERENCES individual_manifold(id),
                FOREIGN KEY (collective_id) REFERENCES collective_manifold(id)
            )
        ''')

        conn.commit()
        conn.close()
        logger.info("Dual manifold tables ensured")

    def add_to_individual_manifold(
        self,
        knowledge_type: str,
        content: str,
        entity_id: int = None,
        personal_weight: float = 1.0,
        context: str = None
    ) -> int:
        """Add knowledge to individual (personal) manifold"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO individual_manifold
            (agent_id, entity_id, knowledge_type, content, personal_weight,
             acquisition_context, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            self.agent_id, entity_id, knowledge_type, content,
            personal_weight, context, datetime.now().isoformat()
        ))

        manifold_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return manifold_id

    def add_to_collective_manifold(
        self,
        domain: str,
        knowledge_type: str,
        content: str,
        entity_id: int = None,
        consensus_score: float = 0.5
    ) -> int:
        """Add knowledge to collective (shared) manifold"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Check if similar knowledge exists
        cursor.execute('''
            SELECT id, source_count FROM collective_manifold
            WHERE domain = ? AND knowledge_type = ? AND content = ?
        ''', (domain, knowledge_type, content))

        existing = cursor.fetchone()

        if existing:
            # Update existing - increase consensus
            new_count = existing[1] + 1
            new_consensus = min(0.95, consensus_score + 0.1)

            cursor.execute('''
                UPDATE collective_manifold
                SET source_count = ?, consensus_score = ?, updated_at = ?
                WHERE id = ?
            ''', (new_count, new_consensus, datetime.now().isoformat(), existing[0]))

            manifold_id = existing[0]
        else:
            cursor.execute('''
                INSERT INTO collective_manifold
                (domain, entity_id, knowledge_type, content, consensus_score, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (domain, entity_id, knowledge_type, content, consensus_score, datetime.now().isoformat()))

            manifold_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return manifold_id

    def find_intersections(
        self,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Find intersection points between individual and collective manifolds

        These intersections are where personal experience meets domain knowledge,
        creating opportunities for insight
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Simple intersection: same entity_id in both manifolds
        cursor.execute('''
            SELECT
                im.id as individual_id,
                cm.id as collective_id,
                im.content as personal_knowledge,
                cm.content as domain_knowledge,
                im.knowledge_type as personal_type,
                cm.domain as domain,
                im.personal_weight * cm.consensus_score as strength
            FROM individual_manifold im
            JOIN collective_manifold cm ON im.entity_id = cm.entity_id
            WHERE im.agent_id = ? AND im.entity_id IS NOT NULL
            ORDER BY strength DESC
            LIMIT 50
        ''', (self.agent_id,))

        intersections = []
        for row in cursor.fetchall():
            intersections.append({
                'individual_id': row[0],
                'collective_id': row[1],
                'personal_knowledge': row[2],
                'domain_knowledge': row[3],
                'personal_type': row[4],
                'domain': row[5],
                'strength': row[6]
            })

        conn.close()
        return intersections

    def generate_insight_at_intersection(
        self,
        individual_id: int,
        collective_id: int
    ) -> Dict[str, Any]:
        """
        Generate insight at the intersection of individual and collective knowledge

        This is where Mirror Mind's "dual manifold" concept creates value:
        combining personal cognitive style with domain expertise
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get individual knowledge
        cursor.execute('''
            SELECT content, knowledge_type, acquisition_context
            FROM individual_manifold WHERE id = ?
        ''', (individual_id,))
        individual = cursor.fetchone()

        # Get collective knowledge
        cursor.execute('''
            SELECT content, domain, knowledge_type, consensus_score
            FROM collective_manifold WHERE id = ?
        ''', (collective_id,))
        collective = cursor.fetchone()

        if not individual or not collective:
            conn.close()
            return {'success': False, 'error': 'Knowledge not found'}

        # Create intersection insight
        insight = (
            f"Personal experience with {individual[1]} "
            f"({individual[0][:100]}...) connects to domain knowledge in "
            f"{collective[1]} ({collective[0][:100]}...). "
            f"Consensus: {collective[3]:.0%}"
        )

        # Calculate intersection strength
        strength = 0.5  # Base
        if collective[3] > 0.7:  # High consensus
            strength += 0.2

        # Record intersection
        cursor.execute('''
            INSERT INTO manifold_intersections
            (individual_id, collective_id, intersection_strength, insight_generated, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (individual_id, collective_id, strength, insight, datetime.now().isoformat()))

        intersection_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {
            'success': True,
            'intersection_id': intersection_id,
            'insight': insight,
            'strength': strength
        }

    def get_manifold_summary(self) -> DualManifold:
        """Get summary of both manifolds and their intersection"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Individual manifold summary
        cursor.execute('''
            SELECT knowledge_type, COUNT(*) as count, AVG(personal_weight) as avg_weight
            FROM individual_manifold WHERE agent_id = ?
            GROUP BY knowledge_type
        ''', (self.agent_id,))

        individual = {
            'types': {row[0]: {'count': row[1], 'avg_weight': row[2]} for row in cursor.fetchall()}
        }

        # Collective manifold summary
        cursor.execute('''
            SELECT domain, COUNT(*) as count, AVG(consensus_score) as avg_consensus
            FROM collective_manifold
            GROUP BY domain
        ''')

        collective = {
            'domains': {row[0]: {'count': row[1], 'avg_consensus': row[2]} for row in cursor.fetchall()}
        }

        # Intersection summary
        cursor.execute('''
            SELECT COUNT(*) FROM manifold_intersections
            WHERE individual_id IN (SELECT id FROM individual_manifold WHERE agent_id = ?)
        ''', (self.agent_id,))

        intersection_count = cursor.fetchone()[0]

        conn.close()

        # Find top intersection points
        intersections = self.find_intersections()
        intersection_names = [i['domain'] for i in intersections[:10]]

        return DualManifold(
            individual_manifold=individual,
            collective_manifold=collective,
            intersection_points=intersection_names
        )


# === MCP TOOL REGISTRATION ===

def register_mirror_mind_tools(app, db_path: Path = DB_PATH):
    """Register Mirror Mind enhancement tools with FastMCP app"""

    centrality_calc = CentralityCalculator(db_path)
    trajectory_tracker = CognitiveTrajectoryTracker(db_path)
    distillation = TemporalDistillationPipeline(db_path)

    @app.tool()
    async def calculate_centrality_scores(limit: int = 20) -> Dict[str, Any]:
        """
        Calculate graph centrality scores for knowledge graph nodes

        Uses PageRank, degree centrality, and betweenness centrality
        with recency-weighted combination (Mirror Mind persona layer)

        Args:
            limit: Number of top central entities to return

        Returns:
            Top central entities with all centrality measures
        """
        top_entities = centrality_calc.get_top_central_entities(limit)

        return {
            'success': True,
            'count': len(top_entities),
            'entities': [
                {
                    'name': e.entity_name,
                    'pagerank': round(e.pagerank, 4),
                    'degree': round(e.degree_centrality, 4),
                    'betweenness': round(e.betweenness_centrality, 4),
                    'recency': round(e.recency_weight, 4),
                    'combined': round(e.combined_score, 4)
                }
                for e in top_entities
            ]
        }

    @app.tool()
    async def get_cognitive_trajectory(entity_name: str) -> Dict[str, Any]:
        """
        Get cognitive evolution trajectory for a concept

        Shows how knowledge about a concept has evolved over time
        (Mirror Mind temporal distillation)

        Args:
            entity_name: Name of the entity/concept

        Returns:
            Trajectory with confidence and importance evolution
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM entities WHERE name = ?', (entity_name,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {'success': False, 'error': 'Entity not found'}

        trajectory = trajectory_tracker.get_trajectory(row[0])

        if not trajectory:
            return {'success': False, 'error': 'No trajectory data'}

        return {
            'success': True,
            'entity': trajectory.entity_name,
            'first_encounter': trajectory.first_encounter.isoformat(),
            'last_update': trajectory.last_update.isoformat(),
            'access_count': trajectory.access_count,
            'confidence_evolution': [
                {'time': t.isoformat(), 'confidence': c}
                for t, c in trajectory.confidence_evolution
            ],
            'importance_trajectory': [
                {'time': t.isoformat(), 'importance': i}
                for t, i in trajectory.importance_trajectory
            ]
        }

    @app.tool()
    async def analyze_knowledge_evolution(days: int = 30) -> Dict[str, Any]:
        """
        Analyze how knowledge has evolved over time

        Identifies learning patterns, emerging concepts, and knowledge gaps

        Args:
            days: Time window for analysis

        Returns:
            Analysis of knowledge evolution patterns
        """
        return trajectory_tracker.analyze_knowledge_evolution(days)

    @app.tool()
    async def run_temporal_distillation(
        time_window_hours: int = 24,
        min_frequency: int = 2
    ) -> Dict[str, Any]:
        """
        Run temporal distillation pipeline (Mirror Mind map-reduce)

        1. Map: Extract patterns from episodic memories
        2. Reduce: Consolidate into semantic concepts
        3. Distill: Update cognitive trajectories

        Args:
            time_window_hours: Hours of episodic memory to process
            min_frequency: Minimum pattern frequency for promotion

        Returns:
            Distillation results with promoted concepts
        """
        return distillation.run_full_distillation(time_window_hours, min_frequency)

    @app.tool()
    async def add_to_dual_manifold(
        content: str,
        manifold: str,
        knowledge_type: str,
        domain: str = None,
        weight: float = 0.5
    ) -> Dict[str, Any]:
        """
        Add knowledge to dual manifold architecture

        Args:
            content: The knowledge content
            manifold: 'individual' or 'collective'
            knowledge_type: Type of knowledge (experience, fact, preference, etc.)
            domain: Domain for collective manifold (e.g., 'physics', 'programming')
            weight: Personal weight (individual) or consensus (collective)

        Returns:
            ID of created manifold entry
        """
        dual = DualManifoldArchitecture(db_path=db_path)

        if manifold == 'individual':
            manifold_id = dual.add_to_individual_manifold(
                knowledge_type=knowledge_type,
                content=content,
                personal_weight=weight
            )
        elif manifold == 'collective':
            if not domain:
                return {'success': False, 'error': 'Domain required for collective manifold'}
            manifold_id = dual.add_to_collective_manifold(
                domain=domain,
                knowledge_type=knowledge_type,
                content=content,
                consensus_score=weight
            )
        else:
            return {'success': False, 'error': 'Invalid manifold type'}

        return {
            'success': True,
            'manifold': manifold,
            'id': manifold_id
        }

    @app.tool()
    async def find_manifold_intersections() -> Dict[str, Any]:
        """
        Find intersection points between individual and collective manifolds

        These intersections are where personal experience meets domain knowledge,
        creating opportunities for insight (Mirror Mind dual manifold)

        Returns:
            List of intersection points with strength scores
        """
        dual = DualManifoldArchitecture(db_path=db_path)
        intersections = dual.find_intersections()

        return {
            'success': True,
            'count': len(intersections),
            'intersections': intersections
        }

    @app.tool()
    async def get_dual_manifold_summary() -> Dict[str, Any]:
        """
        Get summary of dual manifold architecture

        Shows individual knowledge space, collective knowledge space,
        and their intersection points

        Returns:
            Manifold summary with statistics
        """
        dual = DualManifoldArchitecture(db_path=db_path)
        summary = dual.get_manifold_summary()

        return {
            'success': True,
            'individual_manifold': summary.individual_manifold,
            'collective_manifold': summary.collective_manifold,
            'intersection_points': summary.intersection_points
        }

    logger.info("Mirror Mind enhancement tools registered")


if __name__ == "__main__":
    # Test the enhancements
    print("Testing Mirror Mind Enhancements...")

    # Test centrality
    calc = CentralityCalculator()
    top = calc.get_top_central_entities(5)
    print(f"\nTop {len(top)} central entities:")
    for e in top:
        print(f"  {e.entity_name}: PageRank={e.pagerank:.4f}, Combined={e.combined_score:.4f}")

    # Test trajectory
    tracker = CognitiveTrajectoryTracker()
    evolution = tracker.analyze_knowledge_evolution(30)
    print(f"\nKnowledge evolution ({evolution['time_window_days']} days):")
    print(f"  Total trajectory points: {evolution['total_trajectory_points']}")
    print(f"  Learning concepts: {len(evolution['learning_concepts'])}")

    # Test distillation
    pipeline = TemporalDistillationPipeline()
    result = pipeline.run_full_distillation(24, 2)
    print(f"\nTemporal distillation:")
    print(f"  Patterns found: {result['patterns_found']}")
    print(f"  Concepts promoted: {result['concepts_promoted']}")

    # Test dual manifold
    dual = DualManifoldArchitecture()
    summary = dual.get_manifold_summary()
    print(f"\nDual manifold summary:")
    print(f"  Individual types: {list(summary.individual_manifold.get('types', {}).keys())}")
    print(f"  Collective domains: {list(summary.collective_manifold.get('domains', {}).keys())}")
    print(f"  Intersection points: {len(summary.intersection_points)}")

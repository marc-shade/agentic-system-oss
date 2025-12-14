#!/usr/bin/env python3
"""
Swarm Topology Optimizer
=========================

Intelligent topology selection and optimization for multi-agent swarms.
Analyzes task characteristics and automatically selects the optimal topology
(mesh, hierarchical, star, ring) for maximum coordination effectiveness.

Key Features:
- Task complexity analysis for topology matching
- Performance-based topology adaptation
- Real-time metrics collection and optimization
- 90%+ task completion rate target through optimal coordination

Topologies:
- **Mesh**: Peer-to-peer, best for collaborative tasks with equal agents
- **Hierarchical**: Coordinator + workers, best for decomposable tasks
- **Star**: Central hub, best for centralized decision-making
- **Ring**: Sequential processing, best for pipeline tasks

Integration:
- Enhanced Memory MCP for learning and metrics
- Agent Runtime MCP for task queue
- Claude Flow MCP for swarm orchestration
"""

import asyncio
import json
import logging
import os
import platform
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import statistics


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
        elif Path("/mnt/agentic-system").exists():
            return Path("/mnt/agentic-system")
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = _STORAGE_BASE / "databases" / "swarm_topology.db"


class SwarmTopology(Enum):
    """Swarm coordination topologies"""
    MESH = "mesh"  # Peer-to-peer, all agents communicate
    HIERARCHICAL = "hierarchical"  # Coordinator with worker hierarchy
    STAR = "star"  # Central hub with spoke agents
    RING = "ring"  # Sequential processing pipeline


class TaskComplexity(Enum):
    """Task complexity levels"""
    TRIVIAL = "trivial"  # Single step, < 1 min
    SIMPLE = "simple"  # Few steps, < 5 min
    MODERATE = "moderate"  # Multiple steps, < 30 min
    COMPLEX = "complex"  # Many steps, < 2 hours
    VERY_COMPLEX = "very_complex"  # Highly complex, > 2 hours


class TaskCharacteristics(Enum):
    """Task characteristic flags"""
    PARALLELIZABLE = "parallelizable"  # Can be split into parallel work
    SEQUENTIAL = "sequential"  # Must be done in order
    COLLABORATIVE = "collaborative"  # Requires agent collaboration
    INDEPENDENT = "independent"  # Agents work independently
    CENTRALIZED = "centralized"  # Requires central coordination
    DISTRIBUTED = "distributed"  # Can be fully distributed
    REAL_TIME = "real_time"  # Time-sensitive execution
    BATCH = "batch"  # Can be batched/delayed


@dataclass
class TaskAnalysis:
    """Analysis of task characteristics"""
    task_id: str
    description: str
    complexity: TaskComplexity
    characteristics: List[TaskCharacteristics]
    estimated_duration_minutes: float
    agent_count_needed: int
    parallelization_factor: float  # 0.0-1.0
    coordination_overhead: float  # 0.0-1.0
    metadata: Dict[str, Any]


@dataclass
class TopologyRecommendation:
    """Topology recommendation with scoring"""
    topology: SwarmTopology
    confidence_score: float  # 0.0-1.0
    reasoning: str
    expected_completion_rate: float  # 0.0-1.0
    expected_execution_time_minutes: float
    optimal_agent_count: int
    pros: List[str]
    cons: List[str]


@dataclass
class SwarmExecution:
    """Record of swarm execution"""
    execution_id: str
    task_id: str
    topology_used: SwarmTopology
    agent_count: int
    start_time: datetime
    end_time: Optional[datetime]
    success: bool
    completion_rate: float  # Subtasks completed / total
    execution_time_minutes: float
    performance_score: float  # 0.0-1.0
    metadata: Dict[str, Any]


class SwarmTopologyOptimizer:
    """
    Intelligent topology selector and optimizer for multi-agent swarms.

    Uses task analysis, historical performance, and real-time metrics to
    select and optimize swarm topologies for maximum effectiveness.
    """

    def __init__(self, db_path: Path = DB_PATH):
        """Initialize topology optimizer"""
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

        # Topology performance tracking
        self.topology_performance: Dict[SwarmTopology, Dict] = {
            topology: {
                'total_executions': 0,
                'successful_executions': 0,
                'avg_completion_rate': 0.0,
                'avg_execution_time': 0.0,
                'avg_performance_score': 0.0
            }
            for topology in SwarmTopology
        }

        self._load_historical_performance()

        logger.info("SwarmTopologyOptimizer initialized")

    def _init_database(self):
        """Initialize topology database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Task analysis table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_analysis (
                task_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                complexity TEXT NOT NULL,
                characteristics TEXT NOT NULL,
                estimated_duration_minutes REAL NOT NULL,
                agent_count_needed INTEGER NOT NULL,
                parallelization_factor REAL NOT NULL,
                coordination_overhead REAL NOT NULL,
                metadata TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # Topology recommendations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topology_recommendations (
                recommendation_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                topology TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                reasoning TEXT NOT NULL,
                expected_completion_rate REAL NOT NULL,
                expected_execution_time_minutes REAL NOT NULL,
                optimal_agent_count INTEGER NOT NULL,
                pros TEXT NOT NULL,
                cons TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES task_analysis(task_id)
            )
        """)

        # Swarm executions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS swarm_executions (
                execution_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                topology_used TEXT NOT NULL,
                agent_count INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                success INTEGER NOT NULL,
                completion_rate REAL NOT NULL,
                execution_time_minutes REAL NOT NULL,
                performance_score REAL NOT NULL,
                metadata TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES task_analysis(task_id)
            )
        """)

        # Topology performance metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topology_metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                topology TEXT NOT NULL,
                complexity TEXT NOT NULL,
                avg_completion_rate REAL NOT NULL,
                avg_execution_time_minutes REAL NOT NULL,
                success_rate REAL NOT NULL,
                sample_count INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_topology_used ON swarm_executions(topology_used)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_success ON swarm_executions(success)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_topology_complexity ON topology_metrics(topology, complexity)")

        conn.commit()
        conn.close()

    def _load_historical_performance(self):
        """Load historical topology performance from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                topology_used,
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                AVG(completion_rate) as avg_completion,
                AVG(execution_time_minutes) as avg_time,
                AVG(performance_score) as avg_performance
            FROM swarm_executions
            WHERE end_time IS NOT NULL
            GROUP BY topology_used
        """)

        for row in cursor.fetchall():
            topology_str, total, successful, avg_completion, avg_time, avg_performance = row
            try:
                topology = SwarmTopology(topology_str)
                self.topology_performance[topology] = {
                    'total_executions': total,
                    'successful_executions': successful,
                    'avg_completion_rate': avg_completion or 0.0,
                    'avg_execution_time': avg_time or 0.0,
                    'avg_performance_score': avg_performance or 0.0
                }
            except ValueError:
                logger.warning(f"Unknown topology in database: {topology_str}")

        conn.close()
        logger.info(f"Loaded historical performance for {len(self.topology_performance)} topologies")

    async def analyze_task(
        self,
        task_id: str,
        task_description: str,
        context: Optional[Dict] = None
    ) -> TaskAnalysis:
        """
        Analyze task characteristics to determine optimal topology.

        Args:
            task_id: Unique task identifier
            task_description: Task description
            context: Optional context (language, framework, constraints)

        Returns:
            Task analysis with characteristics
        """
        logger.info(f"Analyzing task: {task_id}")

        # Analyze task description for characteristics
        desc_lower = task_description.lower()

        # Determine complexity
        complexity = self._estimate_complexity(task_description, context)

        # Identify characteristics
        characteristics = []

        # Parallelizable indicators
        if any(kw in desc_lower for kw in ['parallel', 'concurrent', 'multiple', 'batch', 'process many']):
            characteristics.append(TaskCharacteristics.PARALLELIZABLE)

        # Sequential indicators
        if any(kw in desc_lower for kw in ['sequential', 'step by step', 'pipeline', 'workflow', 'in order']):
            characteristics.append(TaskCharacteristics.SEQUENTIAL)

        # Collaborative indicators
        if any(kw in desc_lower for kw in ['collaborate', 'coordinate', 'together', 'team', 'joint']):
            characteristics.append(TaskCharacteristics.COLLABORATIVE)

        # Centralized indicators
        if any(kw in desc_lower for kw in ['centralized', 'coordinated', 'orchestrated', 'managed']):
            characteristics.append(TaskCharacteristics.CENTRALIZED)

        # Distributed indicators
        if any(kw in desc_lower for kw in ['distributed', 'decentralized', 'independent', 'autonomous']):
            characteristics.append(TaskCharacteristics.DISTRIBUTED)

        # Real-time indicators
        if any(kw in desc_lower for kw in ['real-time', 'immediate', 'urgent', 'fast', 'quick']):
            characteristics.append(TaskCharacteristics.REAL_TIME)

        # Default to independent if no characteristics found
        if not characteristics:
            characteristics.append(TaskCharacteristics.INDEPENDENT)

        # Estimate parameters
        estimated_duration = self._estimate_duration(complexity, context)
        agent_count = self._estimate_agent_count(complexity, characteristics)
        parallelization_factor = self._calculate_parallelization_factor(characteristics)
        coordination_overhead = self._calculate_coordination_overhead(characteristics, agent_count)

        analysis = TaskAnalysis(
            task_id=task_id,
            description=task_description,
            complexity=complexity,
            characteristics=characteristics,
            estimated_duration_minutes=estimated_duration,
            agent_count_needed=agent_count,
            parallelization_factor=parallelization_factor,
            coordination_overhead=coordination_overhead,
            metadata=context or {}
        )

        # Save to database
        self._save_task_analysis(analysis)

        logger.info(f"Task analysis complete: complexity={complexity.value}, agents={agent_count}, parallel={parallelization_factor:.2f}")

        return analysis

    def _estimate_complexity(self, description: str, context: Optional[Dict]) -> TaskComplexity:
        """Estimate task complexity from description"""
        desc_lower = description.lower()

        # Complexity indicators
        if any(kw in desc_lower for kw in ['simple', 'basic', 'trivial', 'quick']):
            return TaskComplexity.SIMPLE

        if any(kw in desc_lower for kw in ['complex', 'advanced', 'sophisticated', 'comprehensive']):
            return TaskComplexity.COMPLEX

        if any(kw in desc_lower for kw in ['very complex', 'highly complex', 'extremely', 'massive']):
            return TaskComplexity.VERY_COMPLEX

        # Count action words as proxy for complexity
        action_words = ['implement', 'build', 'create', 'design', 'develop', 'test', 'deploy', 'analyze', 'optimize']
        action_count = sum(1 for word in action_words if word in desc_lower)

        if action_count == 0:
            return TaskComplexity.TRIVIAL
        elif action_count <= 2:
            return TaskComplexity.SIMPLE
        elif action_count <= 4:
            return TaskComplexity.MODERATE
        elif action_count <= 6:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.VERY_COMPLEX

    def _estimate_duration(self, complexity: TaskComplexity, context: Optional[Dict]) -> float:
        """Estimate task duration in minutes"""
        base_duration = {
            TaskComplexity.TRIVIAL: 2.0,
            TaskComplexity.SIMPLE: 10.0,
            TaskComplexity.MODERATE: 30.0,
            TaskComplexity.COMPLEX: 90.0,
            TaskComplexity.VERY_COMPLEX: 180.0
        }
        return base_duration.get(complexity, 30.0)

    def _estimate_agent_count(self, complexity: TaskComplexity, characteristics: List[TaskCharacteristics]) -> int:
        """Estimate number of agents needed"""
        base_count = {
            TaskComplexity.TRIVIAL: 1,
            TaskComplexity.SIMPLE: 2,
            TaskComplexity.MODERATE: 3,
            TaskComplexity.COMPLEX: 5,
            TaskComplexity.VERY_COMPLEX: 8
        }

        count = base_count.get(complexity, 3)

        # Adjust for characteristics
        if TaskCharacteristics.PARALLELIZABLE in characteristics:
            count = min(count + 2, 10)
        if TaskCharacteristics.COLLABORATIVE in characteristics:
            count = min(count + 1, 10)

        return count

    def _calculate_parallelization_factor(self, characteristics: List[TaskCharacteristics]) -> float:
        """Calculate how parallelizable the task is (0.0-1.0)"""
        if TaskCharacteristics.SEQUENTIAL in characteristics:
            return 0.1
        if TaskCharacteristics.PARALLELIZABLE in characteristics:
            return 0.9
        if TaskCharacteristics.INDEPENDENT in characteristics:
            return 0.7
        return 0.5  # Default moderate parallelization

    def _calculate_coordination_overhead(self, characteristics: List[TaskCharacteristics], agent_count: int) -> float:
        """Calculate coordination overhead (0.0-1.0)"""
        base_overhead = 0.1

        # More agents = more overhead
        agent_overhead = min((agent_count - 1) * 0.05, 0.3)

        # Characteristics impact
        char_overhead = 0.0
        if TaskCharacteristics.COLLABORATIVE in characteristics:
            char_overhead += 0.2
        if TaskCharacteristics.CENTRALIZED in characteristics:
            char_overhead += 0.15
        if TaskCharacteristics.DISTRIBUTED in characteristics:
            char_overhead -= 0.05  # Less overhead when distributed

        return min(base_overhead + agent_overhead + char_overhead, 0.8)

    async def recommend_topology(
        self,
        task_analysis: TaskAnalysis,
        consider_history: bool = True
    ) -> List[TopologyRecommendation]:
        """
        Recommend optimal topology based on task analysis.

        Args:
            task_analysis: Task analysis results
            consider_history: Use historical performance data

        Returns:
            List of topology recommendations, sorted by confidence
        """
        logger.info(f"Recommending topology for task: {task_analysis.task_id}")

        recommendations = []

        # Evaluate each topology
        for topology in SwarmTopology:
            recommendation = await self._evaluate_topology(
                topology,
                task_analysis,
                consider_history
            )
            recommendations.append(recommendation)

        # Sort by confidence score
        recommendations.sort(key=lambda x: x.confidence_score, reverse=True)

        # Save top recommendation
        self._save_topology_recommendation(recommendations[0], task_analysis.task_id)

        logger.info(f"Top recommendation: {recommendations[0].topology.value} (confidence={recommendations[0].confidence_score:.2f})")

        return recommendations

    async def _evaluate_topology(
        self,
        topology: SwarmTopology,
        task_analysis: TaskAnalysis,
        consider_history: bool
    ) -> TopologyRecommendation:
        """Evaluate a specific topology for the task"""
        characteristics = task_analysis.characteristics

        # Base scoring
        base_score = 0.5
        pros = []
        cons = []

        # Mesh topology evaluation
        if topology == SwarmTopology.MESH:
            if TaskCharacteristics.COLLABORATIVE in characteristics:
                base_score += 0.3
                pros.append("Excellent for collaborative work")
            if TaskCharacteristics.DISTRIBUTED in characteristics:
                base_score += 0.2
                pros.append("Natural fit for distributed tasks")
            if task_analysis.agent_count_needed > 6:
                base_score -= 0.2
                cons.append("High overhead with many agents")
            else:
                pros.append("Low coordination overhead")

            reasoning = "Mesh topology provides peer-to-peer collaboration"

        # Hierarchical topology evaluation
        elif topology == SwarmTopology.HIERARCHICAL:
            if TaskCharacteristics.CENTRALIZED in characteristics:
                base_score += 0.3
                pros.append("Natural central coordination")
            if TaskCharacteristics.PARALLELIZABLE in characteristics:
                base_score += 0.2
                pros.append("Efficient work distribution")
            if task_analysis.complexity in [TaskComplexity.COMPLEX, TaskComplexity.VERY_COMPLEX]:
                base_score += 0.2
                pros.append("Handles complex decomposition well")
            if TaskCharacteristics.SEQUENTIAL in characteristics:
                base_score -= 0.1
                cons.append("Overhead for sequential tasks")

            reasoning = "Hierarchical topology provides structured coordination with clear roles"

        # Star topology evaluation
        elif topology == SwarmTopology.STAR:
            if TaskCharacteristics.CENTRALIZED in characteristics:
                base_score += 0.4
                pros.append("Central hub for coordination")
            if task_analysis.agent_count_needed <= 4:
                base_score += 0.2
                pros.append("Simple coordination")
            else:
                cons.append("Central hub can become bottleneck")
            if TaskCharacteristics.REAL_TIME in characteristics:
                base_score += 0.1
                pros.append("Fast central decision-making")
            if TaskCharacteristics.COLLABORATIVE in characteristics:
                base_score -= 0.2
                cons.append("Limited peer collaboration")

            reasoning = "Star topology provides centralized control with hub coordination"

        # Ring topology evaluation
        elif topology == SwarmTopology.RING:
            if TaskCharacteristics.SEQUENTIAL in characteristics:
                base_score += 0.4
                pros.append("Perfect for sequential processing")
            if TaskCharacteristics.PARALLELIZABLE in characteristics:
                base_score -= 0.3
                cons.append("Cannot leverage parallelism")
            if task_analysis.agent_count_needed >= 4:
                base_score += 0.1
                pros.append("Predictable pipeline flow")
            if TaskCharacteristics.REAL_TIME in characteristics:
                cons.append("Sequential overhead for urgent tasks")

            reasoning = "Ring topology provides pipeline-style sequential processing"

        # Apply historical performance adjustment
        if consider_history:
            hist_perf = self.topology_performance[topology]
            if hist_perf['total_executions'] > 5:
                hist_score = hist_perf['avg_performance_score']
                base_score = base_score * 0.7 + hist_score * 0.3  # 70% analysis, 30% history
                pros.append(f"Historical success rate: {hist_perf['successful_executions'] / hist_perf['total_executions'] * 100:.1f}%")

        # Normalize score
        confidence_score = min(max(base_score, 0.0), 1.0)

        # Estimate performance
        expected_completion_rate = 0.85 + (confidence_score * 0.1)  # 85-95% based on confidence
        expected_time = task_analysis.estimated_duration_minutes * (1.0 + task_analysis.coordination_overhead)

        return TopologyRecommendation(
            topology=topology,
            confidence_score=confidence_score,
            reasoning=reasoning,
            expected_completion_rate=expected_completion_rate,
            expected_execution_time_minutes=expected_time,
            optimal_agent_count=task_analysis.agent_count_needed,
            pros=pros,
            cons=cons
        )

    def _save_task_analysis(self, analysis: TaskAnalysis):
        """Save task analysis to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO task_analysis
            (task_id, description, complexity, characteristics, estimated_duration_minutes,
             agent_count_needed, parallelization_factor, coordination_overhead, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            analysis.task_id,
            analysis.description,
            analysis.complexity.value,
            json.dumps([c.value for c in analysis.characteristics]),
            analysis.estimated_duration_minutes,
            analysis.agent_count_needed,
            analysis.parallelization_factor,
            analysis.coordination_overhead,
            json.dumps(analysis.metadata),
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

    def _save_topology_recommendation(self, recommendation: TopologyRecommendation, task_id: str):
        """Save topology recommendation to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        recommendation_id = f"{task_id}_{recommendation.topology.value}_{datetime.now().timestamp()}"

        cursor.execute("""
            INSERT INTO topology_recommendations
            (recommendation_id, task_id, topology, confidence_score, reasoning,
             expected_completion_rate, expected_execution_time_minutes, optimal_agent_count,
             pros, cons, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            recommendation_id,
            task_id,
            recommendation.topology.value,
            recommendation.confidence_score,
            recommendation.reasoning,
            recommendation.expected_completion_rate,
            recommendation.expected_execution_time_minutes,
            recommendation.optimal_agent_count,
            json.dumps(recommendation.pros),
            json.dumps(recommendation.cons),
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

    async def record_execution(
        self,
        execution: SwarmExecution
    ):
        """
        Record swarm execution outcome for learning.

        Args:
            execution: Swarm execution record
        """
        logger.info(f"Recording execution: {execution.execution_id}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO swarm_executions
            (execution_id, task_id, topology_used, agent_count, start_time, end_time,
             success, completion_rate, execution_time_minutes, performance_score, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            execution.execution_id,
            execution.task_id,
            execution.topology_used.value,
            execution.agent_count,
            execution.start_time.isoformat(),
            execution.end_time.isoformat() if execution.end_time else None,
            1 if execution.success else 0,
            execution.completion_rate,
            execution.execution_time_minutes,
            execution.performance_score,
            json.dumps(execution.metadata)
        ))

        conn.commit()
        conn.close()

        # Update in-memory performance tracking
        self._update_topology_performance(execution)

        logger.info(f"Execution recorded: success={execution.success}, completion={execution.completion_rate:.2%}")

    def _update_topology_performance(self, execution: SwarmExecution):
        """Update topology performance metrics"""
        topology = execution.topology_used
        perf = self.topology_performance[topology]

        # Update counters
        perf['total_executions'] += 1
        if execution.success:
            perf['successful_executions'] += 1

        # Update rolling averages
        n = perf['total_executions']
        perf['avg_completion_rate'] = (perf['avg_completion_rate'] * (n-1) + execution.completion_rate) / n
        perf['avg_execution_time'] = (perf['avg_execution_time'] * (n-1) + execution.execution_time_minutes) / n
        perf['avg_performance_score'] = (perf['avg_performance_score'] * (n-1) + execution.performance_score) / n

    def get_topology_statistics(self) -> Dict[str, Any]:
        """Get comprehensive topology performance statistics"""
        stats = {
            'overall': {
                'total_executions': sum(p['total_executions'] for p in self.topology_performance.values()),
                'total_successful': sum(p['successful_executions'] for p in self.topology_performance.values())
            },
            'by_topology': {}
        }

        for topology, perf in self.topology_performance.items():
            if perf['total_executions'] > 0:
                stats['by_topology'][topology.value] = {
                    'executions': perf['total_executions'],
                    'success_rate': perf['successful_executions'] / perf['total_executions'],
                    'avg_completion_rate': perf['avg_completion_rate'],
                    'avg_execution_time_minutes': perf['avg_execution_time'],
                    'avg_performance_score': perf['avg_performance_score']
                }

        return stats

    async def optimize_for_target_rate(
        self,
        target_completion_rate: float = 0.90
    ) -> Dict[str, Any]:
        """
        Analyze and recommend optimizations to achieve target completion rate.

        Args:
            target_completion_rate: Target completion rate (default 90%)

        Returns:
            Optimization recommendations
        """
        logger.info(f"Optimizing for target completion rate: {target_completion_rate:.1%}")

        current_stats = self.get_topology_statistics()
        recommendations = []

        # Check each topology
        for topology_str, stats in current_stats['by_topology'].items():
            if stats['avg_completion_rate'] < target_completion_rate:
                gap = target_completion_rate - stats['avg_completion_rate']
                recommendations.append({
                    'topology': topology_str,
                    'current_rate': stats['avg_completion_rate'],
                    'gap': gap,
                    'suggestion': self._get_improvement_suggestion(topology_str, stats)
                })

        return {
            'target_rate': target_completion_rate,
            'current_overall_rate': current_stats['overall']['total_successful'] / max(current_stats['overall']['total_executions'], 1),
            'recommendations': recommendations
        }

    def _get_improvement_suggestion(self, topology: str, stats: Dict) -> str:
        """Get improvement suggestion for a topology"""
        if stats['avg_completion_rate'] < 0.70:
            return f"Consider avoiding {topology} for current task types or adding more agents"
        elif stats['avg_completion_rate'] < 0.85:
            return f"Optimize {topology} coordination or increase agent specialization"
        else:
            return f"Fine-tune {topology} agent count and coordination overhead"


async def main():
    """Demo of swarm topology optimization"""
    optimizer = SwarmTopologyOptimizer()

    print("\n" + "=" * 70)
    print("SWARM TOPOLOGY OPTIMIZER DEMO")
    print("=" * 70)

    # Demo 1: Analyze and recommend topology
    print("\nDemo 1: Complex Multi-Domain Task")
    print("-" * 70)

    task1 = await optimizer.analyze_task(
        task_id="task_001",
        task_description="Implement distributed microservices architecture with API gateway, authentication, and data processing pipeline",
        context={"framework": "FastAPI", "language": "Python"}
    )

    recommendations = await optimizer.recommend_topology(task1)

    print(f"\nTask: {task1.description}")
    print(f"Complexity: {task1.complexity.value}")
    print(f"Agents needed: {task1.agent_count_needed}")
    print(f"Parallelization factor: {task1.parallelization_factor:.2f}")
    print(f"\nTop 3 Recommendations:")
    for i, rec in enumerate(recommendations[:3], 1):
        print(f"\n{i}. {rec.topology.value.upper()} (confidence: {rec.confidence_score:.2f})")
        print(f"   {rec.reasoning}")
        print(f"   Expected completion: {rec.expected_completion_rate:.1%}")
        print(f"   Pros: {', '.join(rec.pros)}")

    # Demo 2: Different task type
    print("\n\nDemo 2: Sequential Pipeline Task")
    print("-" * 70)

    task2 = await optimizer.analyze_task(
        task_id="task_002",
        task_description="Process data through sequential pipeline: extract, transform, validate, load to database",
        context={"batch_processing": True}
    )

    recommendations2 = await optimizer.recommend_topology(task2)

    print(f"\nTask: {task2.description}")
    print(f"Complexity: {task2.complexity.value}")
    print(f"Top recommendation: {recommendations2[0].topology.value} (confidence: {recommendations2[0].confidence_score:.2f})")

    # Demo 3: Statistics
    print("\n\nDemo 3: Topology Statistics")
    print("-" * 70)
    print(json.dumps(optimizer.get_topology_statistics(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())

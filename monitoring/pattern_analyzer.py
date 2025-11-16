#!/usr/bin/env python3
"""
Pattern Analysis Engine for AGI Build-Out
Week 3: Pattern Detection and Optimization Recommendations

This module analyzes system metrics to detect patterns and generate
optimization recommendations for autonomous improvement.
"""

import json
import sqlite3
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Configuration
PATTERNS_DB = Path("/mnt/agentic-system/databases/patterns.db")
METRICS_FILE = Path("/tmp/claude_performance_metrics.json")
LEARNING_MEMORY = Path("/tmp/claude_learning_memory.jsonl")

class PatternType(Enum):
    """Types of patterns we can detect"""
    TIME_SERIES = "time_series"
    SEQUENCE = "sequence"
    ANOMALY = "anomaly"
    CORRELATION = "correlation"
    RESOURCE_USAGE = "resource_usage"
    ERROR_PATTERN = "error_pattern"

class ConfidenceLevel(Enum):
    """Confidence levels for pattern detection"""
    HIGH = 0.8
    MEDIUM = 0.6
    LOW = 0.4

@dataclass
class Pattern:
    """Represents a detected pattern"""
    pattern_id: str
    pattern_type: PatternType
    description: str
    occurrences: int
    confidence: float
    detected_at: datetime
    data: Dict[str, Any]

@dataclass
class Recommendation:
    """Represents an optimization recommendation"""
    recommendation_id: str
    pattern_id: str
    recommendation_type: str
    description: str
    impact: str
    confidence: float
    created_at: datetime
    applied: bool
    effectiveness: float

class PatternDatabase:
    """Manages pattern storage and retrieval"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                pattern_id TEXT PRIMARY KEY,
                pattern_type TEXT NOT NULL,
                description TEXT NOT NULL,
                occurrences INTEGER DEFAULT 1,
                confidence REAL NOT NULL,
                detected_at TIMESTAMP NOT NULL,
                last_seen TIMESTAMP NOT NULL,
                data JSON NOT NULL
            )
        """)

        # Pattern occurrences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pattern_occurrences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id TEXT NOT NULL,
                occurred_at TIMESTAMP NOT NULL,
                context JSON,
                FOREIGN KEY (pattern_id) REFERENCES patterns(pattern_id)
            )
        """)

        # Recommendations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recommendations (
                recommendation_id TEXT PRIMARY KEY,
                pattern_id TEXT NOT NULL,
                recommendation_type TEXT NOT NULL,
                description TEXT NOT NULL,
                impact TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at TIMESTAMP NOT NULL,
                applied BOOLEAN DEFAULT 0,
                applied_at TIMESTAMP,
                effectiveness REAL,
                FOREIGN KEY (pattern_id) REFERENCES patterns(pattern_id)
            )
        """)

        # Recommendation effectiveness tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS effectiveness_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recommendation_id TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                before_value REAL NOT NULL,
                after_value REAL NOT NULL,
                improvement_pct REAL NOT NULL,
                measured_at TIMESTAMP NOT NULL,
                FOREIGN KEY (recommendation_id) REFERENCES recommendations(recommendation_id)
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_patterns_type
            ON patterns(pattern_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_recommendations_pattern
            ON recommendations(pattern_id)
        """)

        conn.commit()
        conn.close()

    def store_pattern(self, pattern: Pattern):
        """Store or update a pattern"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO patterns
            (pattern_id, pattern_type, description, occurrences, confidence,
             detected_at, last_seen, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pattern.pattern_id,
            pattern.pattern_type.value,
            pattern.description,
            pattern.occurrences,
            pattern.confidence,
            pattern.detected_at.isoformat(),
            datetime.now().isoformat(),
            json.dumps(pattern.data)
        ))

        # Record occurrence
        cursor.execute("""
            INSERT INTO pattern_occurrences (pattern_id, occurred_at, context)
            VALUES (?, ?, ?)
        """, (
            pattern.pattern_id,
            datetime.now().isoformat(),
            json.dumps(pattern.data)
        ))

        conn.commit()
        conn.close()

    def get_patterns(self, pattern_type: PatternType = None,
                     min_confidence: float = 0.0) -> List[Pattern]:
        """Retrieve patterns with optional filtering"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = """
            SELECT pattern_id, pattern_type, description, occurrences,
                   confidence, detected_at, data
            FROM patterns
            WHERE confidence >= ?
        """
        params = [min_confidence]

        if pattern_type:
            query += " AND pattern_type = ?"
            params.append(pattern_type.value)

        query += " ORDER BY confidence DESC, occurrences DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        patterns = []
        for row in rows:
            patterns.append(Pattern(
                pattern_id=row[0],
                pattern_type=PatternType(row[1]),
                description=row[2],
                occurrences=row[3],
                confidence=row[4],
                detected_at=datetime.fromisoformat(row[5]),
                data=json.loads(row[6])
            ))

        return patterns

    def store_recommendation(self, recommendation: Recommendation):
        """Store a recommendation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO recommendations
            (recommendation_id, pattern_id, recommendation_type, description,
             impact, confidence, created_at, applied, effectiveness)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            recommendation.recommendation_id,
            recommendation.pattern_id,
            recommendation.recommendation_type,
            recommendation.description,
            recommendation.impact,
            recommendation.confidence,
            recommendation.created_at.isoformat(),
            recommendation.applied,
            recommendation.effectiveness
        ))

        conn.commit()
        conn.close()

class PatternAnalyzer:
    """Core pattern detection and analysis engine"""

    def __init__(self, db: PatternDatabase):
        self.db = db
        self.metrics_history = []

    def load_metrics_history(self, hours: int = 24):
        """Load historical metrics for analysis"""
        # In production, this would load from metrics database
        # For now, we'll collect from the current metrics file and learning memory
        self.metrics_history = []

        # Load current metrics
        if METRICS_FILE.exists():
            try:
                with open(METRICS_FILE, 'r') as f:
                    current_metrics = json.load(f)
                    self.metrics_history.append(current_metrics)
            except Exception as e:
                print(f"Error loading metrics: {e}")

        # Load learning memory events
        if LEARNING_MEMORY.exists():
            try:
                with open(LEARNING_MEMORY, 'r') as f:
                    for line in f:
                        event = json.loads(line.strip())
                        self.metrics_history.append(event)
            except Exception as e:
                print(f"Error loading learning memory: {e}")

    def detect_time_series_patterns(self) -> List[Pattern]:
        """Detect patterns in time-series data"""
        patterns = []

        # Analyze CPU usage trends
        cpu_values = []
        for metric in self.metrics_history:
            if 'system' in metric and 'cpu_percent' in metric['system']:
                cpu_values.append(metric['system']['cpu_percent'])

        if len(cpu_values) >= 3:
            avg_cpu = np.mean(cpu_values)
            if avg_cpu > 80:
                pattern = Pattern(
                    pattern_id=f"high_cpu_{datetime.now().strftime('%Y%m%d')}",
                    pattern_type=PatternType.TIME_SERIES,
                    description=f"High CPU usage detected (avg: {avg_cpu:.1f}%)",
                    occurrences=1,
                    confidence=0.85,
                    detected_at=datetime.now(),
                    data={
                        "metric": "cpu_percent",
                        "average": avg_cpu,
                        "threshold": 80,
                        "samples": len(cpu_values)
                    }
                )
                patterns.append(pattern)

        return patterns

    def detect_resource_patterns(self) -> List[Pattern]:
        """Detect resource usage patterns"""
        patterns = []

        # Check for memory pressure
        for metric in self.metrics_history:
            if 'system' in metric and 'memory_percent' in metric['system']:
                mem_pct = metric['system']['memory_percent']
                if mem_pct > 90:
                    pattern = Pattern(
                        pattern_id=f"high_memory_{datetime.now().strftime('%Y%m%d')}",
                        pattern_type=PatternType.RESOURCE_USAGE,
                        description=f"High memory usage detected ({mem_pct:.1f}%)",
                        occurrences=1,
                        confidence=0.90,
                        detected_at=datetime.now(),
                        data={
                            "metric": "memory_percent",
                            "value": mem_pct,
                            "threshold": 90
                        }
                    )
                    patterns.append(pattern)

        return patterns

    def detect_anomalies(self) -> List[Pattern]:
        """Detect anomalous behavior"""
        patterns = []

        # Simple anomaly detection: sudden changes in metrics
        if len(self.metrics_history) >= 2:
            recent = self.metrics_history[-1]
            previous = self.metrics_history[-2]

            if 'system' in recent and 'system' in previous:
                cpu_change = abs(
                    recent['system'].get('cpu_percent', 0) -
                    previous['system'].get('cpu_percent', 0)
                )

                if cpu_change > 50:
                    pattern = Pattern(
                        pattern_id=f"cpu_spike_{datetime.now().strftime('%Y%m%d_%H%M')}",
                        pattern_type=PatternType.ANOMALY,
                        description=f"Sudden CPU usage change ({cpu_change:.1f}% delta)",
                        occurrences=1,
                        confidence=0.75,
                        detected_at=datetime.now(),
                        data={
                            "metric": "cpu_percent",
                            "change": cpu_change,
                            "threshold": 50
                        }
                    )
                    patterns.append(pattern)

        return patterns

    def analyze(self) -> Tuple[List[Pattern], List[Recommendation]]:
        """Run complete pattern analysis"""
        print(f"Starting pattern analysis at {datetime.now().isoformat()}")

        # Load recent metrics
        self.load_metrics_history()
        print(f"Loaded {len(self.metrics_history)} metric samples")

        # Run all detection algorithms
        all_patterns = []
        all_patterns.extend(self.detect_time_series_patterns())
        all_patterns.extend(self.detect_resource_patterns())
        all_patterns.extend(self.detect_anomalies())

        print(f"Detected {len(all_patterns)} patterns")

        # Store patterns
        for pattern in all_patterns:
            self.db.store_pattern(pattern)

        # Generate recommendations
        recommendations = self.generate_recommendations(all_patterns)
        print(f"Generated {len(recommendations)} recommendations")

        # Store recommendations
        for rec in recommendations:
            self.db.store_recommendation(rec)

        return all_patterns, recommendations

    def generate_recommendations(self, patterns: List[Pattern]) -> List[Recommendation]:
        """Generate optimization recommendations based on patterns"""
        recommendations = []

        for pattern in patterns:
            if pattern.pattern_type == PatternType.RESOURCE_USAGE:
                if 'cpu_percent' in pattern.data.get('metric', ''):
                    rec = Recommendation(
                        recommendation_id=f"optimize_cpu_{pattern.pattern_id}",
                        pattern_id=pattern.pattern_id,
                        recommendation_type="resource_optimization",
                        description="Consider optimizing CPU-intensive processes",
                        impact="Reduce CPU usage by 10-20%",
                        confidence=0.75,
                        created_at=datetime.now(),
                        applied=False,
                        effectiveness=0.0
                    )
                    recommendations.append(rec)

                    # Also generate code optimization
                    self._create_optimization_from_recommendation(rec)

                if 'memory_percent' in pattern.data.get('metric', ''):
                    rec = Recommendation(
                        recommendation_id=f"optimize_memory_{pattern.pattern_id}",
                        pattern_id=pattern.pattern_id,
                        recommendation_type="resource_optimization",
                        description="Increase cache cleanup frequency or add memory",
                        impact="Reduce memory pressure",
                        confidence=0.80,
                        created_at=datetime.now(),
                        applied=False,
                        effectiveness=0.0
                    )
                    recommendations.append(rec)

                    # Also generate code optimization
                    self._create_optimization_from_recommendation(rec)

            elif pattern.pattern_type == PatternType.ANOMALY:
                rec = Recommendation(
                    recommendation_id=f"investigate_anomaly_{pattern.pattern_id}",
                    pattern_id=pattern.pattern_id,
                    recommendation_type="investigation",
                    description=f"Investigate cause of {pattern.description}",
                    impact="Prevent future anomalies",
                    confidence=0.70,
                    created_at=datetime.now(),
                    applied=False,
                    effectiveness=0.0
                )
                recommendations.append(rec)

        return recommendations

    def _create_optimization_from_recommendation(self, recommendation: Recommendation):
        """Create code optimization from recommendation"""
        try:
            import sys
            sys.path.insert(0, '/mnt/agentic-system/monitoring')
            from code_optimizer import OptimizationDatabase, Optimization, OptimizationType, OptimizationStatus

            opt_db_path = Path("/mnt/agentic-system/databases/optimizations.db")
            opt_db = OptimizationDatabase(opt_db_path)

            # Create optimization based on recommendation type
            if 'cpu' in recommendation.description.lower():
                optimization = Optimization(
                    optimization_id=f"opt_{recommendation.recommendation_id}",
                    optimization_type=OptimizationType.RESOURCE_MANAGEMENT,
                    target_file="/mnt/agentic-system/config.env",
                    description=recommendation.description,
                    code_before="# Current configuration",
                    code_after="# Optimized configuration with reduced CPU usage",
                    confidence=recommendation.confidence,
                    pattern_id=recommendation.pattern_id,
                    recommendation_id=recommendation.recommendation_id,
                    auto_apply=(recommendation.confidence >= 0.8),
                    status=OptimizationStatus.PENDING,
                    created_at=datetime.now()
                )
                opt_db.store_optimization(optimization)
                print(f"  Created optimization: {optimization.optimization_id}")

            elif 'memory' in recommendation.description.lower():
                optimization = Optimization(
                    optimization_id=f"opt_{recommendation.recommendation_id}",
                    optimization_type=OptimizationType.CACHING,
                    target_file="/mnt/agentic-system/config.env",
                    description=recommendation.description,
                    code_before="# Current cache configuration",
                    code_after="# Optimized cache with improved memory management",
                    confidence=recommendation.confidence,
                    pattern_id=recommendation.pattern_id,
                    recommendation_id=recommendation.recommendation_id,
                    auto_apply=(recommendation.confidence >= 0.8),
                    status=OptimizationStatus.PENDING,
                    created_at=datetime.now()
                )
                opt_db.store_optimization(optimization)
                print(f"  Created optimization: {optimization.optimization_id}")

        except Exception as e:
            print(f"  Warning: Could not create optimization: {e}")

def main():
    """Main pattern analysis runner"""
    print("="*60)
    print("Pattern Analysis Engine - Week 3")
    print("="*60)
    print()

    # Initialize database
    db = PatternDatabase(PATTERNS_DB)
    print(f"✓ Pattern database initialized: {PATTERNS_DB}")

    # Initialize analyzer
    analyzer = PatternAnalyzer(db)
    print(f"✓ Pattern analyzer initialized")
    print()

    # Run analysis
    patterns, recommendations = analyzer.analyze()
    print()

    # Report results
    print("="*60)
    print("ANALYSIS RESULTS")
    print("="*60)
    print()

    if patterns:
        print(f"Detected Patterns ({len(patterns)}):")
        for p in patterns:
            print(f"  • {p.pattern_type.value}: {p.description}")
            print(f"    Confidence: {p.confidence:.0%}, Occurrences: {p.occurrences}")
        print()
    else:
        print("No patterns detected in current metrics")
        print()

    if recommendations:
        print(f"Generated Recommendations ({len(recommendations)}):")
        for r in recommendations:
            print(f"  • [{r.recommendation_type}] {r.description}")
            print(f"    Impact: {r.impact}")
            print(f"    Confidence: {r.confidence:.0%}")
        print()
    else:
        print("No recommendations generated")
        print()

    print("="*60)
    print(f"Analysis complete at {datetime.now().isoformat()}")
    print("="*60)

if __name__ == "__main__":
    main()

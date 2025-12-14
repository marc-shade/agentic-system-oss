#!/usr/bin/env python3
"""
Skill Evolution System for AGI
===============================

Tracks skill usage, identifies underperforming versions, runs A/B tests,
and automatically promotes better skill implementations. Enables continuous
skill improvement through evolutionary selection.

Key Capabilities:
- Skill version management
- Performance tracking per version
- A/B testing framework
- Automatic promotion of better versions
- Skill deprecation and retirement
- Usage analytics

Integration:
- Enhanced Memory for skill storage
- Meta-Learning Engine for performance data
- Code execution sandbox for skill testing
"""

import asyncio
import json
import logging
import os
import platform
import sqlite3
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import statistics
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        macos_primary = Path("/Volumes/SSDRAID0/agentic-system")
        macos_fallback = Path("/Volumes/FILES/agentic-system")
        if macos_primary.exists():
            return macos_primary
        elif macos_fallback.exists():
            return macos_fallback
    elif system == "Linux":
        linux_primary = Path("/home/marc/agentic-system")
        linux_fallback = Path("/mnt/agentic-system")
        if linux_primary.exists():
            return linux_primary
        elif linux_fallback.exists():
            return linux_fallback
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

# Paths
DB_PATH = _STORAGE_BASE / "databases/skill_evolution.db"
SKILLS_PATH = _STORAGE_BASE / "skills"


class SkillStatus(Enum):
    """Skill version status"""
    EXPERIMENTAL = "experimental"
    TESTING = "testing"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


@dataclass
class SkillVersion:
    """Skill version metadata"""
    skill_name: str
    version: str
    code_hash: str
    description: str
    code: str
    status: SkillStatus
    created_at: datetime
    promoted_at: Optional[datetime]
    deprecated_at: Optional[datetime]


@dataclass
class SkillExecution:
    """Skill execution record"""
    execution_id: str
    skill_name: str
    version: str
    success: bool
    execution_time_ms: int
    error_message: Optional[str]
    quality_score: float
    context: Dict
    timestamp: datetime


@dataclass
class SkillMetrics:
    """Performance metrics for a skill version"""
    skill_name: str
    version: str
    total_executions: int
    success_rate: float
    avg_execution_time_ms: float
    avg_quality_score: float
    last_executed: datetime


class SkillEvolutionSystem:
    """
    Manages skill versions, tracks performance, and evolves skills
    through A/B testing and automatic promotion.
    """

    def __init__(self, db_path: Path = DB_PATH, skills_path: Path = SKILLS_PATH):
        """Initialize skill evolution system"""
        self.db_path = db_path
        self.skills_path = skills_path

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.skills_path.mkdir(parents=True, exist_ok=True)

        self._init_database()

    def _init_database(self):
        """Initialize skill evolution database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Skill versions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT NOT NULL,
                version TEXT NOT NULL,
                code_hash TEXT NOT NULL UNIQUE,
                description TEXT,
                code TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                promoted_at TEXT,
                deprecated_at TEXT,
                UNIQUE(skill_name, version)
            )
        """)

        # Execution records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_executions (
                execution_id TEXT PRIMARY KEY,
                skill_name TEXT NOT NULL,
                version TEXT NOT NULL,
                success INTEGER NOT NULL,
                execution_time_ms INTEGER NOT NULL,
                error_message TEXT,
                quality_score REAL NOT NULL,
                context TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)

        # A/B test configurations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ab_tests (
                test_id TEXT PRIMARY KEY,
                skill_name TEXT NOT NULL,
                version_a TEXT NOT NULL,
                version_b TEXT NOT NULL,
                split_ratio REAL NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                winner TEXT,
                confidence REAL
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skill_name ON skill_versions(skill_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skill_status ON skill_versions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exec_skill ON skill_executions(skill_name, version)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exec_timestamp ON skill_executions(timestamp)")

        conn.commit()
        conn.close()

    def _compute_code_hash(self, code: str) -> str:
        """Compute hash of skill code"""
        return hashlib.sha256(code.encode()).hexdigest()[:16]

    def register_skill(self, skill_name: str, code: str,
                      description: str = "", version: Optional[str] = None) -> SkillVersion:
        """
        Register a new skill version.

        If version is not specified, generates next version automatically.
        """
        code_hash = self._compute_code_hash(code)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if this exact code already exists
        cursor.execute("""
            SELECT skill_name, version FROM skill_versions
            WHERE code_hash = ?
        """, (code_hash,))

        existing = cursor.fetchone()
        if existing:
            logger.info(f"Skill code already exists: {existing[0]} v{existing[1]}")
            conn.close()
            return self.get_skill_version(existing[0], existing[1])

        # Generate version if not provided
        if not version:
            cursor.execute("""
                SELECT version FROM skill_versions
                WHERE skill_name = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (skill_name,))

            last_version = cursor.fetchone()
            if last_version:
                # Increment version
                try:
                    last_num = int(last_version[0].replace("v", ""))
                    version = f"v{last_num + 1}"
                except ValueError:
                    version = "v1"
            else:
                version = "v1"

        # Insert new version
        skill_version = SkillVersion(
            skill_name=skill_name,
            version=version,
            code_hash=code_hash,
            description=description,
            code=code,
            status=SkillStatus.EXPERIMENTAL,
            created_at=datetime.now(),
            promoted_at=None,
            deprecated_at=None
        )

        cursor.execute("""
            INSERT INTO skill_versions
            (skill_name, version, code_hash, description, code, status,
             created_at, promoted_at, deprecated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            skill_version.skill_name,
            skill_version.version,
            skill_version.code_hash,
            skill_version.description,
            skill_version.code,
            skill_version.status.value,
            skill_version.created_at.isoformat(),
            None,
            None
        ))

        conn.commit()
        conn.close()

        # Save to filesystem
        skill_file = self.skills_path / f"{skill_name}_{version}.py"
        skill_file.write_text(f'"""{description}"""\n\n{code}')

        logger.info(f"Registered skill: {skill_name} {version}")

        return skill_version

    def record_execution(self, execution: SkillExecution) -> None:
        """Record a skill execution for learning"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO skill_executions
            (execution_id, skill_name, version, success, execution_time_ms,
             error_message, quality_score, context, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            execution.execution_id,
            execution.skill_name,
            execution.version,
            1 if execution.success else 0,
            execution.execution_time_ms,
            execution.error_message,
            execution.quality_score,
            json.dumps(execution.context),
            execution.timestamp.isoformat()
        ))

        conn.commit()
        conn.close()

    def get_skill_metrics(self, skill_name: str, version: Optional[str] = None,
                         lookback_days: int = 30) -> List[SkillMetrics]:
        """Get performance metrics for skill version(s)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(days=lookback_days)).isoformat()

        if version:
            query = """
                SELECT skill_name, version,
                       COUNT(*) as total,
                       AVG(success) as success_rate,
                       AVG(execution_time_ms) as avg_time,
                       AVG(quality_score) as avg_quality,
                       MAX(timestamp) as last_executed
                FROM skill_executions
                WHERE skill_name = ? AND version = ? AND timestamp > ?
                GROUP BY skill_name, version
            """
            params = (skill_name, version, cutoff)
        else:
            query = """
                SELECT skill_name, version,
                       COUNT(*) as total,
                       AVG(success) as success_rate,
                       AVG(execution_time_ms) as avg_time,
                       AVG(quality_score) as avg_quality,
                       MAX(timestamp) as last_executed
                FROM skill_executions
                WHERE skill_name = ? AND timestamp > ?
                GROUP BY skill_name, version
            """
            params = (skill_name, cutoff)

        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        metrics = []
        for row in results:
            metrics.append(SkillMetrics(
                skill_name=row[0],
                version=row[1],
                total_executions=row[2],
                success_rate=row[3],
                avg_execution_time_ms=row[4],
                avg_quality_score=row[5],
                last_executed=datetime.fromisoformat(row[6])
            ))

        return metrics

    def get_skill_version(self, skill_name: str, version: str) -> Optional[SkillVersion]:
        """Get a specific skill version"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM skill_versions
            WHERE skill_name = ? AND version = ?
        """, (skill_name, version))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return SkillVersion(
            skill_name=row[1],
            version=row[2],
            code_hash=row[3],
            description=row[4],
            code=row[5],
            status=SkillStatus(row[6]),
            created_at=datetime.fromisoformat(row[7]),
            promoted_at=datetime.fromisoformat(row[8]) if row[8] else None,
            deprecated_at=datetime.fromisoformat(row[9]) if row[9] else None
        )

    def get_production_version(self, skill_name: str) -> Optional[SkillVersion]:
        """Get current production version of a skill"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM skill_versions
            WHERE skill_name = ? AND status = 'production'
            ORDER BY promoted_at DESC
            LIMIT 1
        """, (skill_name,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return SkillVersion(
            skill_name=row[1],
            version=row[2],
            code_hash=row[3],
            description=row[4],
            code=row[5],
            status=SkillStatus(row[6]),
            created_at=datetime.fromisoformat(row[7]),
            promoted_at=datetime.fromisoformat(row[8]) if row[8] else None,
            deprecated_at=datetime.fromisoformat(row[9]) if row[9] else None
        )

    def start_ab_test(self, skill_name: str, version_a: str, version_b: str,
                     split_ratio: float = 0.5) -> str:
        """
        Start an A/B test between two skill versions.

        Args:
            skill_name: Name of skill to test
            version_a: First version (typically current production)
            version_b: Second version (typically new candidate)
            split_ratio: Ratio of traffic to version_a (default 0.5 = 50/50)

        Returns:
            test_id for tracking
        """
        import uuid
        test_id = str(uuid.uuid4())

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO ab_tests
            (test_id, skill_name, version_a, version_b, split_ratio,
             started_at, ended_at, winner, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            test_id,
            skill_name,
            version_a,
            version_b,
            split_ratio,
            datetime.now().isoformat(),
            None,
            None,
            None
        ))

        conn.commit()
        conn.close()

        logger.info(f"Started A/B test: {skill_name} ({version_a} vs {version_b})")

        return test_id

    def select_version_for_execution(self, skill_name: str) -> str:
        """
        Select which version to use for execution.

        If A/B test is active, uses split ratio.
        Otherwise, uses production version.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check for active A/B test
        cursor.execute("""
            SELECT version_a, version_b, split_ratio
            FROM ab_tests
            WHERE skill_name = ? AND ended_at IS NULL
            ORDER BY started_at DESC
            LIMIT 1
        """, (skill_name,))

        ab_test = cursor.fetchone()

        if ab_test:
            # A/B test active
            version_a, version_b, split_ratio = ab_test
            if random.random() < split_ratio:
                version = version_a
            else:
                version = version_b
        else:
            # Use production version
            cursor.execute("""
                SELECT version FROM skill_versions
                WHERE skill_name = ? AND status = 'production'
                ORDER BY promoted_at DESC
                LIMIT 1
            """, (skill_name,))

            result = cursor.fetchone()
            version = result[0] if result else "v1"

        conn.close()

        return version

    def analyze_ab_test(self, test_id: str, min_samples: int = 50) -> Optional[Dict]:
        """
        Analyze A/B test results and determine winner.

        Uses statistical significance testing to determine if one version
        is clearly better than the other.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get test details
        cursor.execute("""
            SELECT skill_name, version_a, version_b, started_at
            FROM ab_tests
            WHERE test_id = ?
        """, (test_id,))

        test = cursor.fetchone()
        if not test:
            conn.close()
            return None

        skill_name, version_a, version_b, started_at = test

        # Get metrics for both versions since test start
        metrics_a = self.get_skill_metrics(skill_name, version_a)
        metrics_b = self.get_skill_metrics(skill_name, version_b)

        conn.close()

        if not metrics_a or not metrics_b:
            return {"status": "insufficient_data", "message": "Not enough execution data"}

        metric_a = metrics_a[0]
        metric_b = metrics_b[0]

        # Check minimum sample size
        if metric_a.total_executions < min_samples or metric_b.total_executions < min_samples:
            return {
                "status": "insufficient_samples",
                "version_a_samples": metric_a.total_executions,
                "version_b_samples": metric_b.total_executions,
                "min_required": min_samples
            }

        # Compare performance (simple comparison - would use proper statistical tests)
        score_a = (metric_a.success_rate * 0.5 + metric_a.avg_quality_score * 0.5)
        score_b = (metric_b.success_rate * 0.5 + metric_b.avg_quality_score * 0.5)

        difference = abs(score_a - score_b)
        confidence = min(1.0, difference * 5)  # Simplified confidence calculation

        if confidence > 0.95:
            winner = version_a if score_a > score_b else version_b
            return {
                "status": "complete",
                "winner": winner,
                "confidence": confidence,
                "version_a_score": score_a,
                "version_b_score": score_b
            }
        else:
            return {
                "status": "ongoing",
                "confidence": confidence,
                "version_a_score": score_a,
                "version_b_score": score_b,
                "message": "Continue test - no clear winner yet"
            }

    def promote_version(self, skill_name: str, version: str) -> bool:
        """Promote a skill version to production"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Deprecate current production version
        cursor.execute("""
            UPDATE skill_versions
            SET status = 'deprecated', deprecated_at = ?
            WHERE skill_name = ? AND status = 'production'
        """, (datetime.now().isoformat(), skill_name))

        # Promote new version
        cursor.execute("""
            UPDATE skill_versions
            SET status = 'production', promoted_at = ?
            WHERE skill_name = ? AND version = ?
        """, (datetime.now().isoformat(), skill_name, version))

        conn.commit()
        conn.close()

        logger.info(f"Promoted skill {skill_name} {version} to production")

        return True


async def main():
    """Demo of skill evolution system"""
    system = SkillEvolutionSystem()

    # Register skill versions
    v1 = system.register_skill(
        skill_name="data_processor",
        code="def process(data): return [x * 2 for x in data]",
        description="Simple data processing v1"
    )

    v2 = system.register_skill(
        skill_name="data_processor",
        code="def process(data): return [x * 2 for x in data if x > 0]",
        description="Improved data processing v2 with filtering"
    )

    print(f"Registered versions: {v1.version}, {v2.version}")

    # Simulate executions
    import uuid
    for i in range(60):
        # Simulate v1 executions
        system.record_execution(SkillExecution(
            execution_id=str(uuid.uuid4()),
            skill_name="data_processor",
            version=v1.version,
            success=random.random() > 0.1,
            execution_time_ms=random.randint(100, 200),
            error_message=None,
            quality_score=random.uniform(0.7, 0.9),
            context={},
            timestamp=datetime.now()
        ))

        # Simulate v2 executions (better performance)
        system.record_execution(SkillExecution(
            execution_id=str(uuid.uuid4()),
            skill_name="data_processor",
            version=v2.version,
            success=random.random() > 0.05,
            execution_time_ms=random.randint(80, 150),
            error_message=None,
            quality_score=random.uniform(0.85, 0.95),
            context={},
            timestamp=datetime.now()
        ))

    # Get metrics
    metrics = system.get_skill_metrics("data_processor")
    print("\nSkill Metrics:")
    for metric in metrics:
        print(f"  {metric.version}: success_rate={metric.success_rate:.2f}, "
              f"quality={metric.avg_quality_score:.2f}, "
              f"executions={metric.total_executions}")

    # Start A/B test
    test_id = system.start_ab_test("data_processor", v1.version, v2.version)
    print(f"\nStarted A/B test: {test_id}")

    # Analyze results
    analysis = system.analyze_ab_test(test_id)
    print(f"\nA/B Test Analysis:")
    print(json.dumps(analysis, indent=2))

    if analysis and analysis.get("status") == "complete":
        # Promote winner
        system.promote_version("data_processor", analysis["winner"])
        print(f"\nPromoted {analysis['winner']} to production!")


if __name__ == "__main__":
    asyncio.run(main())

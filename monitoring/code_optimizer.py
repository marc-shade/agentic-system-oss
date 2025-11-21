#!/usr/bin/env python3
"""
Code Optimization Engine - Week 5 Phase 2
Deep Learning Cycle: Autonomous Code Optimization

This module analyzes code, applies optimizations based on detected patterns,
and tracks effectiveness for continuous improvement.
"""

import ast
import json
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# Configuration
PATTERNS_DB = Path("/mnt/agentic-system/databases/patterns.db")
OPTIMIZATIONS_DB = Path("/mnt/agentic-system/databases/optimizations.db")
AGENTIC_MARKERS_LOG = Path.home() / ".claude/.config_modifications.jsonl"

class OptimizationType(Enum):
    """Types of optimizations that can be applied"""
    CACHING = "caching"
    PARALLEL_EXECUTION = "parallel_execution"
    RESOURCE_MANAGEMENT = "resource_management"
    ALGORITHM_IMPROVEMENT = "algorithm_improvement"
    DATABASE_OPTIMIZATION = "database_optimization"
    CONFIGURATION_TUNING = "configuration_tuning"

class OptimizationStatus(Enum):
    """Status of an optimization"""
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

@dataclass
class Optimization:
    """Represents a code optimization"""
    optimization_id: str
    optimization_type: OptimizationType
    target_file: str
    description: str
    code_before: str
    code_after: str
    confidence: float
    pattern_id: Optional[str]
    recommendation_id: Optional[str]
    auto_apply: bool
    status: OptimizationStatus
    created_at: datetime
    applied_at: Optional[datetime] = None

@dataclass
class OptimizationResult:
    """Results from applying an optimization"""
    optimization_id: str
    success: bool
    metrics_before: Dict[str, float]
    metrics_after: Dict[str, float]
    improvement_pct: float
    error: Optional[str] = None

class OptimizationDatabase:
    """Manages optimization storage and tracking"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Optimizations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimizations (
                optimization_id TEXT PRIMARY KEY,
                optimization_type TEXT NOT NULL,
                target_file TEXT NOT NULL,
                description TEXT NOT NULL,
                code_before TEXT NOT NULL,
                code_after TEXT NOT NULL,
                confidence REAL NOT NULL,
                pattern_id TEXT,
                recommendation_id TEXT,
                auto_apply BOOLEAN NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                applied_at TIMESTAMP
            )
        """)

        # Optimization results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimization_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                optimization_id TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                metrics_before JSON NOT NULL,
                metrics_after JSON NOT NULL,
                improvement_pct REAL NOT NULL,
                error TEXT,
                measured_at TIMESTAMP NOT NULL,
                FOREIGN KEY (optimization_id) REFERENCES optimizations(optimization_id)
            )
        """)

        # Rollback history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rollback_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                optimization_id TEXT NOT NULL,
                rolled_back_at TIMESTAMP NOT NULL,
                reason TEXT NOT NULL,
                FOREIGN KEY (optimization_id) REFERENCES optimizations(optimization_id)
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_optimizations_status
            ON optimizations(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_optimizations_type
            ON optimizations(optimization_type)
        """)

        conn.commit()
        conn.close()

    def store_optimization(self, optimization: Optimization):
        """Store an optimization"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO optimizations
            (optimization_id, optimization_type, target_file, description,
             code_before, code_after, confidence, pattern_id, recommendation_id,
             auto_apply, status, created_at, applied_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            optimization.optimization_id,
            optimization.optimization_type.value,
            optimization.target_file,
            optimization.description,
            optimization.code_before,
            optimization.code_after,
            optimization.confidence,
            optimization.pattern_id,
            optimization.recommendation_id,
            optimization.auto_apply,
            optimization.status.value,
            optimization.created_at.isoformat(),
            optimization.applied_at.isoformat() if optimization.applied_at else None
        ))

        conn.commit()
        conn.close()

    def store_result(self, result: OptimizationResult):
        """Store optimization result"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO optimization_results
            (optimization_id, success, metrics_before, metrics_after,
             improvement_pct, error, measured_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            result.optimization_id,
            result.success,
            json.dumps(result.metrics_before),
            json.dumps(result.metrics_after),
            result.improvement_pct,
            result.error,
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

    def get_pending_optimizations(self) -> List[Optimization]:
        """Get all pending optimizations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT optimization_id, optimization_type, target_file, description,
                   code_before, code_after, confidence, pattern_id, recommendation_id,
                   auto_apply, status, created_at, applied_at
            FROM optimizations
            WHERE status = ?
            ORDER BY confidence DESC
        """, (OptimizationStatus.PENDING.value,))

        rows = cursor.fetchall()
        conn.close()

        optimizations = []
        for row in rows:
            optimizations.append(Optimization(
                optimization_id=row[0],
                optimization_type=OptimizationType(row[1]),
                target_file=row[2],
                description=row[3],
                code_before=row[4],
                code_after=row[5],
                confidence=row[6],
                pattern_id=row[7],
                recommendation_id=row[8],
                auto_apply=bool(row[9]),
                status=OptimizationStatus(row[10]),
                created_at=datetime.fromisoformat(row[11]),
                applied_at=datetime.fromisoformat(row[12]) if row[12] else None
            ))

        return optimizations

class CodeOptimizer:
    """Core code optimization engine"""

    def __init__(self, db: OptimizationDatabase):
        self.db = db
        self.patterns_db = PATTERNS_DB

    def analyze_for_optimizations(self, file_path: Path) -> List[Optimization]:
        """Analyze a file for optimization opportunities"""
        optimizations = []

        if not file_path.exists():
            return optimizations

        try:
            code = file_path.read_text()

            # Python-specific optimizations
            if file_path.suffix == '.py':
                optimizations.extend(self._analyze_python_code(file_path, code))

            # Configuration file optimizations
            elif file_path.suffix in ['.json', '.yaml', '.yml']:
                optimizations.extend(self._analyze_config_file(file_path, code))

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")

        return optimizations

    def _analyze_python_code(self, file_path: Path, code: str) -> List[Optimization]:
        """Analyze Python code for optimizations"""
        optimizations = []

        try:
            tree = ast.parse(code)

            # Check for list comprehension opportunities
            for node in ast.walk(tree):
                if isinstance(node, ast.For):
                    # Simple pattern: for loops that could be comprehensions
                    if self._can_be_list_comprehension(node):
                        opt = self._create_list_comprehension_optimization(
                            file_path, node, code
                        )
                        if opt:
                            optimizations.append(opt)

        except SyntaxError:
            # Skip files with syntax errors - they need fixing first
            print(f"Syntax error in {file_path}, skipping optimization analysis")

        return optimizations

    def _can_be_list_comprehension(self, for_node: ast.For) -> bool:
        """Check if a for loop can be converted to list comprehension"""
        # Simple heuristic: single append in body
        if len(for_node.body) == 1:
            stmt = for_node.body[0]
            if isinstance(stmt, ast.Expr):
                if isinstance(stmt.value, ast.Call):
                    if hasattr(stmt.value.func, 'attr'):
                        if stmt.value.func.attr == 'append':
                            return True
        return False

    def _create_list_comprehension_optimization(
        self, file_path: Path, node: ast.For, code: str
    ) -> Optional[Optimization]:
        """Create optimization to convert for loop to list comprehension"""

        # This is a simplified example - real implementation would be more sophisticated
        optimization_id = f"listcomp_{file_path.stem}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        return Optimization(
            optimization_id=optimization_id,
            optimization_type=OptimizationType.ALGORITHM_IMPROVEMENT,
            target_file=str(file_path),
            description="Convert for loop with append to list comprehension",
            code_before="# For loop with append",
            code_after="# List comprehension",
            confidence=0.75,
            pattern_id=None,
            recommendation_id=None,
            auto_apply=False,  # Requires review
            status=OptimizationStatus.PENDING,
            created_at=datetime.now()
        )

    def _analyze_config_file(self, file_path: Path, content: str) -> List[Optimization]:
        """Analyze configuration files for optimizations"""
        optimizations = []

        # Example: Check for resource configuration based on patterns
        # This would integrate with pattern database to suggest config changes
        if 'timeout' in content:
            # Could suggest increasing timeout based on timeout patterns
            print(f"Found timeout configuration in {file_path}")

        if 'cache' in content:
            # Could suggest cache size adjustments based on usage patterns
            print(f"Found cache configuration in {file_path}")

        return optimizations

    def apply_optimization(self, optimization: Optimization) -> OptimizationResult:
        """Apply an optimization and measure effectiveness"""

        print(f"Applying optimization: {optimization.optimization_id}")
        print(f"  Type: {optimization.optimization_type.value}")
        print(f"  Target: {optimization.target_file}")
        print(f"  Confidence: {optimization.confidence:.0%}")

        # Get metrics before
        metrics_before = self._get_current_metrics()

        try:
            # Mark as agentic change
            self._mark_agentic_change(optimization)

            # Apply the optimization
            if optimization.optimization_type == OptimizationType.CONFIGURATION_TUNING:
                self._apply_config_optimization(optimization)
            else:
                self._apply_code_optimization(optimization)

            # Update status
            optimization.status = OptimizationStatus.APPLIED
            optimization.applied_at = datetime.now()
            self.db.store_optimization(optimization)

            # Get metrics after
            metrics_after = self._get_current_metrics()

            # Calculate improvement
            improvement = self._calculate_improvement(metrics_before, metrics_after)

            result = OptimizationResult(
                optimization_id=optimization.optimization_id,
                success=True,
                metrics_before=metrics_before,
                metrics_after=metrics_after,
                improvement_pct=improvement
            )

            print(f"  ✓ Applied successfully")
            print(f"  Improvement: {improvement:+.1f}%")

        except Exception as e:
            print(f"  ✗ Failed: {e}")

            optimization.status = OptimizationStatus.FAILED
            self.db.store_optimization(optimization)

            result = OptimizationResult(
                optimization_id=optimization.optimization_id,
                success=False,
                metrics_before=metrics_before,
                metrics_after={},
                improvement_pct=0.0,
                error=str(e)
            )

        # Store result
        self.db.store_result(result)

        return result

    def _mark_agentic_change(self, optimization: Optimization):
        """Mark optimization as agentic change in markers log"""
        marker = {
            "timestamp": datetime.now().isoformat(),
            "file": optimization.target_file,
            "key": optimization.optimization_id,
            "change_type": "code_optimization",
            "reason": optimization.description,
            "confidence": optimization.confidence,
            "session_id": f"week5_phase2_{datetime.now().strftime('%Y%m%d')}"
        }

        with open(AGENTIC_MARKERS_LOG, 'a') as f:
            f.write(json.dumps(marker) + '\n')

    def _apply_config_optimization(self, optimization: Optimization):
        """Apply configuration file optimization"""
        target = Path(optimization.target_file)

        # Backup original
        backup = target.with_suffix(target.suffix + '.backup')
        if target.exists():
            backup.write_text(target.read_text())

        # Write optimized version
        target.write_text(optimization.code_after)

    def _apply_code_optimization(self, optimization: Optimization):
        """Apply code optimization"""
        target = Path(optimization.target_file)

        # Backup original
        backup = target.with_suffix(target.suffix + '.backup')
        if target.exists():
            backup.write_text(target.read_text())

        # Write optimized version
        target.write_text(optimization.code_after)

    def _get_current_metrics(self) -> Dict[str, float]:
        """Get current system metrics"""
        try:
            import psutil
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent
            }
        except Exception:
            return {}

    def _calculate_improvement(
        self, before: Dict[str, float], after: Dict[str, float]
    ) -> float:
        """Calculate overall improvement percentage"""
        if not before or not after:
            return 0.0

        improvements = []
        for key in before:
            if key in after:
                # Lower is better for these metrics
                delta = before[key] - after[key]
                if before[key] > 0:
                    pct = (delta / before[key]) * 100
                    improvements.append(pct)

        return sum(improvements) / len(improvements) if improvements else 0.0

    def rollback_optimization(self, optimization: Optimization, reason: str):
        """Rollback an applied optimization"""
        print(f"Rolling back optimization: {optimization.optimization_id}")
        print(f"  Reason: {reason}")

        try:
            target = Path(optimization.target_file)
            backup = target.with_suffix(target.suffix + '.backup')

            if backup.exists():
                target.write_text(backup.read_text())
                backup.unlink()

            optimization.status = OptimizationStatus.ROLLED_BACK
            self.db.store_optimization(optimization)

            # Record rollback
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO rollback_history (optimization_id, rolled_back_at, reason)
                VALUES (?, ?, ?)
            """, (optimization.optimization_id, datetime.now().isoformat(), reason))
            conn.commit()
            conn.close()

            print(f"  ✓ Rolled back successfully")

        except Exception as e:
            print(f"  ✗ Rollback failed: {e}")

def main():
    """Main code optimizer runner"""
    print("="*60)
    print("Code Optimization Engine - Week 5 Phase 2")
    print("="*60)
    print()

    # Initialize database
    db = OptimizationDatabase(OPTIMIZATIONS_DB)
    print(f"✓ Optimization database initialized: {OPTIMIZATIONS_DB}")

    # Initialize optimizer
    optimizer = CodeOptimizer(db)
    print(f"✓ Code optimizer initialized")
    print()

    # Get pending optimizations
    pending = db.get_pending_optimizations()
    print(f"Found {len(pending)} pending optimizations")
    print()

    if pending:
        # Apply high-confidence optimizations
        for opt in pending:
            if opt.auto_apply and opt.confidence >= 0.8:
                print(f"Auto-applying high-confidence optimization:")
                result = optimizer.apply_optimization(opt)

                if not result.success:
                    print(f"  Optimization failed, skipping auto-apply")
                elif result.improvement_pct < 0:
                    print(f"  Negative impact detected, rolling back")
                    optimizer.rollback_optimization(opt, "Negative performance impact")
                print()
    else:
        print("No pending optimizations found")
        print("Pattern analyzer will generate optimizations based on detected patterns")
        print()

    print("="*60)
    print("Code optimization analysis complete")
    print("="*60)

if __name__ == "__main__":
    main()

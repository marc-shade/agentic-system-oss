#!/usr/bin/env python3
"""
Symbolic Regression Manager for Agentic System
==============================================

Integrates PySR (Python Symbolic Regression) to discover interpretable
mathematical equations for system optimization. Replaces hardcoded heuristics
with learned formulas based on historical performance data.

Key Capabilities:
- Data extraction from Darwin Gödel, Meta-Learning, and Skill Evolution databases
- Feature engineering for symbolic regression
- PySR model training and equation discovery
- Equation validation and safety checks
- Integration with existing improvement systems

Discovered Equations Replace:
1. Darwin Gödel improvement estimation heuristics
2. Meta-Learning agent selection formulas
3. Skill Evolution A/B test scoring functions

Integration:
- Enhanced Memory MCP for equation storage
- Darwin Gödel Machine for equation deployment
- Meta-Learning Engine for performance tracking
- Skill Evolution for continuous A/B testing
"""

import asyncio
import json
import logging
import sqlite3
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import hashlib

# Scientific computing
import numpy as np
import pandas as pd
import sympy as sp
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error

# PySR for symbolic regression
try:
    from pysr import PySRRegressor
    PYSR_AVAILABLE = True
except ImportError:
    logging.warning("PySR not installed. Install with: pip install pysr")
    PYSR_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database paths
DARWIN_GODEL_DB = Path("/Volumes/SSDRAID0/agentic-system/databases/darwin_godel.db")
META_LEARNING_DB = Path("/Volumes/SSDRAID0/agentic-system/databases/meta_learning.db")
SKILL_EVOLUTION_DB = Path("/Volumes/SSDRAID0/agentic-system/databases/skill_evolution.db")
EQUATIONS_DB = Path("/Volumes/SSDRAID0/agentic-system/databases/discovered_equations.db")


# Default PySR configuration
DEFAULT_PYSR_CONFIG = {
    "niterations": 100,
    "populations": 20,
    "binary_operators": ["+", "*", "-", "/"],
    "unary_operators": ["log", "exp", "sqrt"],
    "maxsize": 15,  # Maximum equation complexity
    "parsimony": 0.01,  # Favor simpler equations
    "timeout_in_seconds": 3600,  # 1 hour max
    "batching": True,  # Use batching for speed
    "batch_size": 50,
}


@dataclass
class DiscoveredEquation:
    """Metadata for a discovered symbolic equation"""
    equation_id: str
    system_component: str  # darwin_godel, meta_learning, skill_evolution
    purpose: str  # What this equation predicts/optimizes
    sympy_expr: str  # SymPy expression as string
    features: List[str]  # Input feature names
    performance_r2: float  # R² on validation set
    complexity_score: int  # Equation complexity (lower = simpler)
    discovered_at: datetime
    deployed_at: Optional[datetime]
    deprecated_at: Optional[datetime]
    training_data_size: int
    validation_metrics: Dict  # MSE, MAE, etc.


@dataclass
class TrainingResult:
    """Result of symbolic regression training"""
    best_equation: sp.Expr
    r2_train: float
    r2_val: float
    mse_val: float
    complexity: int
    feature_names: List[str]
    sympy_str: str


class SymbolicRegressionManager:
    """
    Manages symbolic regression for agentic system optimization.

    Discovers interpretable mathematical equations from performance data
    to replace hardcoded heuristics in:
    - Darwin Gödel Machine (improvement estimation)
    - Meta-Learning Engine (agent selection)
    - Skill Evolution System (performance scoring)
    """

    def __init__(self):
        """Initialize symbolic regression manager"""
        if not PYSR_AVAILABLE:
            raise ImportError("PySR is required. Install with: pip install pysr")

        # Initialize equation database
        EQUATIONS_DB.parent.mkdir(parents=True, exist_ok=True)
        self._init_equations_database()

    def _init_equations_database(self):
        """Initialize database for storing discovered equations"""
        conn = sqlite3.connect(EQUATIONS_DB)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS discovered_equations (
                equation_id TEXT PRIMARY KEY,
                system_component TEXT NOT NULL,
                purpose TEXT NOT NULL,
                sympy_expr TEXT NOT NULL,
                features TEXT NOT NULL,
                performance_r2 REAL NOT NULL,
                complexity_score INTEGER NOT NULL,
                discovered_at TEXT NOT NULL,
                deployed_at TEXT,
                deprecated_at TEXT,
                training_data_size INTEGER,
                validation_metrics TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_component
            ON discovered_equations(system_component)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_deployed
            ON discovered_equations(deployed_at)
        """)

        conn.commit()
        conn.close()

    # ======================================================================
    # Data Extraction Methods
    # ======================================================================

    def extract_darwin_godel_data(self) -> pd.DataFrame:
        """
        Extract modification data from Darwin Gödel Machine for improvement estimation.

        Features:
        - code_before_complexity: Complexity before modification
        - code_after_complexity: Complexity after modification
        - complexity_reduction: Delta in complexity
        - size_ratio: Ratio of code sizes
        - safety_score: Safety assessment score
        - modification_type: Type of modification (encoded)

        Target:
        - actual_improvement: Measured performance change (from metrics)
        """
        if not DARWIN_GODEL_DB.exists():
            logger.warning(f"Darwin Gödel database not found: {DARWIN_GODEL_DB}")
            return pd.DataFrame()

        conn = sqlite3.connect(DARWIN_GODEL_DB)

        query = """
            SELECT
                m.modification_id,
                m.modification_type,
                m.code_before,
                m.code_after,
                m.expected_improvement,
                m.safety_score,
                m.applied_at,
                m.reverted_at
            FROM modifications m
            WHERE m.applied_at IS NOT NULL
            ORDER BY m.proposed_at
        """

        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            logger.warning("No modification data found in Darwin Gödel database")
            return df

        # Feature engineering
        df['code_before_len'] = df['code_before'].str.len()
        df['code_after_len'] = df['code_after'].str.len()
        df['size_ratio'] = df['code_before_len'] / (df['code_after_len'] + 1)
        df['size_reduction'] = df['code_before_len'] - df['code_after_len']

        # Encode modification types
        type_mapping = {
            'parameter_tune': 1,
            'algorithm_improve': 2,
            'architecture_change': 3,
            'skill_add': 4,
            'constraint_relax': 5
        }
        df['modification_type_encoded'] = df['modification_type'].map(type_mapping).fillna(0)

        # Target: Use expected_improvement as proxy for now
        # In production, would join with actual performance metrics
        df['actual_improvement'] = df['expected_improvement']

        # Was it reverted? (indicates failure)
        df['was_reverted'] = df['reverted_at'].notna().astype(int)

        # Select final features
        features = ['size_ratio', 'size_reduction', 'safety_score',
                   'modification_type_encoded', 'was_reverted']
        target = 'actual_improvement'

        return df[features + [target]].dropna()

    def extract_meta_learning_data(self) -> pd.DataFrame:
        """
        Extract agent performance data from Meta-Learning Engine for agent selection.

        Features:
        - success_rate: Historical success rate for agent/task combination
        - avg_quality_score: Average quality of outputs
        - avg_execution_time_ms: Average execution time
        - total_tasks: Number of tasks completed
        - task_type_encoded: Type of task (encoded)

        Target:
        - agent_performance: Combined performance metric
        """
        if not META_LEARNING_DB.exists():
            logger.warning(f"Meta-Learning database not found: {META_LEARNING_DB}")
            return pd.DataFrame()

        conn = sqlite3.connect(META_LEARNING_DB)

        query = """
            SELECT
                agent_name,
                task_type,
                success_rate,
                avg_execution_time_ms,
                avg_quality_score,
                total_tasks
            FROM agent_performance
            WHERE total_tasks >= 10
            ORDER BY last_updated DESC
        """

        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            logger.warning("No agent performance data found")
            return df

        # Normalize execution time (log scale)
        df['log_exec_time'] = np.log1p(df['avg_execution_time_ms'])

        # Encode task types
        task_types = df['task_type'].unique()
        type_mapping = {task: idx for idx, task in enumerate(task_types)}
        df['task_type_encoded'] = df['task_type'].map(type_mapping)

        # Target: Current simple weighted score
        df['agent_performance'] = (
            df['success_rate'] * 0.5 +
            df['avg_quality_score'] * 0.5
        )

        features = ['success_rate', 'avg_quality_score', 'log_exec_time',
                   'total_tasks', 'task_type_encoded']
        target = 'agent_performance'

        return df[features + [target]].dropna()

    def extract_skill_evolution_data(self) -> pd.DataFrame:
        """
        Extract skill version performance for A/B test scoring optimization.

        Features:
        - success_rate: Execution success rate
        - avg_execution_time_ms: Average execution time
        - avg_quality_score: Average quality score
        - total_executions: Total number of executions
        - version_age_days: Age of version in days

        Target:
        - validated_performance: Long-term validated quality
        """
        if not SKILL_EVOLUTION_DB.exists():
            logger.warning(f"Skill Evolution database not found: {SKILL_EVOLUTION_DB}")
            return pd.DataFrame()

        conn = sqlite3.connect(SKILL_EVOLUTION_DB)

        # Get metrics for all skill versions
        query = """
            SELECT
                se.skill_name,
                se.version,
                COUNT(*) as total_executions,
                AVG(se.success) as success_rate,
                AVG(se.execution_time_ms) as avg_execution_time_ms,
                AVG(se.quality_score) as avg_quality_score,
                sv.created_at,
                sv.status
            FROM skill_executions se
            JOIN skill_versions sv ON se.skill_name = sv.skill_name
                                   AND se.version = sv.version
            GROUP BY se.skill_name, se.version
            HAVING total_executions >= 10
        """

        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            logger.warning("No skill evolution data found")
            return df

        # Calculate version age
        df['created_at'] = pd.to_datetime(df['created_at'])
        df['version_age_days'] = (datetime.now() - df['created_at']).dt.days

        # Normalize execution time (log scale)
        df['log_exec_time'] = np.log1p(df['avg_execution_time_ms'])

        # Target: Current production status indicates validated performance
        # Production versions have proven themselves
        df['validated_performance'] = df.apply(
            lambda row: (
                row['success_rate'] * 0.5 +
                row['avg_quality_score'] * 0.5 +
                (0.1 if row['status'] == 'production' else 0)
            ),
            axis=1
        )

        features = ['success_rate', 'avg_quality_score', 'log_exec_time',
                   'total_executions', 'version_age_days']
        target = 'validated_performance'

        return df[features + [target]].dropna()

    # ======================================================================
    # Training Methods
    # ======================================================================

    def train_equation(self,
                      X: pd.DataFrame,
                      y: pd.Series,
                      feature_names: List[str],
                      config: Optional[Dict] = None) -> TrainingResult:
        """
        Train a PySR model to discover symbolic equation.

        Args:
            X: Feature matrix
            y: Target vector
            feature_names: Names of features
            config: Custom PySR configuration (overrides defaults)

        Returns:
            TrainingResult with discovered equation and performance metrics
        """
        if not PYSR_AVAILABLE:
            raise ImportError("PySR is required")

        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Configure PySR
        pysr_config = DEFAULT_PYSR_CONFIG.copy()
        if config:
            pysr_config.update(config)

        logger.info(f"Training PySR model on {len(X_train)} samples...")
        logger.info(f"Features: {feature_names}")
        logger.info(f"Configuration: {pysr_config}")

        # Create and fit model
        model = PySRRegressor(**pysr_config)
        model.fit(X_train, y_train, variable_names=feature_names)

        # Get best equation
        best_equation = model.sympy()
        sympy_str = str(best_equation)

        # Evaluate
        y_train_pred = model.predict(X_train)
        y_val_pred = model.predict(X_val)

        r2_train = r2_score(y_train, y_train_pred)
        r2_val = r2_score(y_val, y_val_pred)
        mse_val = mean_squared_error(y_val, y_val_pred)

        # Get equation complexity
        complexity = self._calculate_equation_complexity(best_equation)

        logger.info(f"Discovered equation: {sympy_str}")
        logger.info(f"R² (train): {r2_train:.4f}, R² (val): {r2_val:.4f}")
        logger.info(f"Complexity: {complexity}")

        return TrainingResult(
            best_equation=best_equation,
            r2_train=r2_train,
            r2_val=r2_val,
            mse_val=mse_val,
            complexity=complexity,
            feature_names=feature_names,
            sympy_str=sympy_str
        )

    def _calculate_equation_complexity(self, equation: sp.Expr) -> int:
        """
        Calculate complexity score for an equation.

        Complexity = number of operations + number of unique functions
        """
        if not isinstance(equation, sp.Expr):
            return 0

        # Count operations
        operations = 0
        for arg in sp.preorder_traversal(equation):
            if isinstance(arg, (sp.Add, sp.Mul, sp.Pow, sp.Function)):
                operations += 1

        # Count unique functions
        functions = set()
        for arg in sp.preorder_traversal(equation):
            if isinstance(arg, sp.Function):
                functions.add(type(arg))

        return operations + len(functions)

    # ======================================================================
    # Equation Management
    # ======================================================================

    def save_equation(self, equation: DiscoveredEquation) -> bool:
        """Save discovered equation to database"""
        conn = sqlite3.connect(EQUATIONS_DB)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO discovered_equations
                (equation_id, system_component, purpose, sympy_expr, features,
                 performance_r2, complexity_score, discovered_at, deployed_at,
                 deprecated_at, training_data_size, validation_metrics)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                equation.equation_id,
                equation.system_component,
                equation.purpose,
                equation.sympy_expr,
                json.dumps(equation.features),
                equation.performance_r2,
                equation.complexity_score,
                equation.discovered_at.isoformat(),
                equation.deployed_at.isoformat() if equation.deployed_at else None,
                equation.deprecated_at.isoformat() if equation.deprecated_at else None,
                equation.training_data_size,
                json.dumps(equation.validation_metrics)
            ))

            conn.commit()
            logger.info(f"Saved equation: {equation.equation_id}")
            return True

        except sqlite3.IntegrityError as e:
            logger.error(f"Equation already exists: {equation.equation_id}")
            return False
        finally:
            conn.close()

    def get_production_equation(self, system_component: str,
                               purpose: str) -> Optional[DiscoveredEquation]:
        """Get currently deployed equation for a component/purpose"""
        conn = sqlite3.connect(EQUATIONS_DB)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM discovered_equations
            WHERE system_component = ?
              AND purpose = ?
              AND deployed_at IS NOT NULL
              AND deprecated_at IS NULL
            ORDER BY discovered_at DESC
            LIMIT 1
        """, (system_component, purpose))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return DiscoveredEquation(
            equation_id=row[0],
            system_component=row[1],
            purpose=row[2],
            sympy_expr=row[3],
            features=json.loads(row[4]),
            performance_r2=row[5],
            complexity_score=row[6],
            discovered_at=datetime.fromisoformat(row[7]),
            deployed_at=datetime.fromisoformat(row[8]) if row[8] else None,
            deprecated_at=datetime.fromisoformat(row[9]) if row[9] else None,
            training_data_size=row[10],
            validation_metrics=json.loads(row[11])
        )

    # ======================================================================
    # Validation Methods
    # ======================================================================

    def validate_equation_safety(self, equation: sp.Expr,
                                 feature_ranges: Dict[str, Tuple[float, float]]) -> bool:
        """
        Validate that equation is safe to execute.

        Checks:
        - No division by zero
        - Bounded output range
        - No NaN or Inf values in typical inputs
        """
        try:
            # Get equation as callable
            feature_names = list(feature_ranges.keys())
            equation_func = sp.lambdify(feature_names, equation, 'numpy')

            # Test edge cases
            test_cases = []

            # Min values
            test_cases.append([feature_ranges[f][0] for f in feature_names])

            # Max values
            test_cases.append([feature_ranges[f][1] for f in feature_names])

            # Mid values
            test_cases.append([
                (feature_ranges[f][0] + feature_ranges[f][1]) / 2
                for f in feature_names
            ])

            # Random samples
            for _ in range(10):
                test_cases.append([
                    np.random.uniform(feature_ranges[f][0], feature_ranges[f][1])
                    for f in feature_names
                ])

            # Evaluate all test cases
            for test_input in test_cases:
                result = equation_func(*test_input)

                if np.isnan(result) or np.isinf(result):
                    logger.warning(f"Equation produces NaN/Inf for input: {test_input}")
                    return False

                # Check reasonable output range (-1000 to 1000)
                if abs(result) > 1000:
                    logger.warning(f"Equation produces extreme value: {result}")
                    return False

            logger.info("Equation passed safety validation")
            return True

        except Exception as e:
            logger.error(f"Equation safety validation failed: {e}")
            return False


async def main():
    """Demo of symbolic regression manager"""
    logger.info("=== Symbolic Regression Manager Demo ===")

    manager = SymbolicRegressionManager()

    # Extract data from all sources
    logger.info("\n1. Extracting Darwin Gödel data...")
    darwin_data = manager.extract_darwin_godel_data()
    logger.info(f"   Extracted {len(darwin_data)} modification records")

    logger.info("\n2. Extracting Meta-Learning data...")
    meta_data = manager.extract_meta_learning_data()
    logger.info(f"   Extracted {len(meta_data)} agent performance records")

    logger.info("\n3. Extracting Skill Evolution data...")
    skill_data = manager.extract_skill_evolution_data()
    logger.info(f"   Extracted {len(skill_data)} skill version records")

    # Train a model if we have data
    if not darwin_data.empty:
        logger.info("\n4. Training PySR model for Darwin Gödel improvement estimation...")

        features = ['size_ratio', 'size_reduction', 'safety_score',
                   'modification_type_encoded']
        X = darwin_data[features]
        y = darwin_data['actual_improvement']

        # Use smaller iteration count for demo
        config = DEFAULT_PYSR_CONFIG.copy()
        config['niterations'] = 20  # Quick demo

        result = manager.train_equation(X, y, features, config)

        logger.info(f"\n=== Training Results ===")
        logger.info(f"Discovered Equation: {result.sympy_str}")
        logger.info(f"R² (train): {result.r2_train:.4f}")
        logger.info(f"R² (validation): {result.r2_val:.4f}")
        logger.info(f"Complexity: {result.complexity}")

        # Save equation
        equation = DiscoveredEquation(
            equation_id=hashlib.md5(result.sympy_str.encode()).hexdigest()[:16],
            system_component="darwin_godel",
            purpose="improvement_estimation",
            sympy_expr=result.sympy_str,
            features=result.feature_names,
            performance_r2=result.r2_val,
            complexity_score=result.complexity,
            discovered_at=datetime.now(),
            deployed_at=None,
            deprecated_at=None,
            training_data_size=len(X),
            validation_metrics={
                "r2_train": result.r2_train,
                "r2_val": result.r2_val,
                "mse_val": result.mse_val
            }
        )

        manager.save_equation(equation)
        logger.info(f"\nSaved equation: {equation.equation_id}")

    else:
        logger.warning("\n4. No data available for training - skipping")

    logger.info("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(main())

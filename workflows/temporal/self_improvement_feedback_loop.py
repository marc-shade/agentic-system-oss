#!/usr/bin/env python3
"""
Self-Improvement Feedback Loop
==============================

Connects all AGI components into a unified self-improving system:
1. Monitors experiments (Kaggle, Research-to-Code)
2. Analyzes patterns in successes/failures
3. Updates strategies based on learnings
4. Stores insights in persistent memory
5. Feeds back into future experiments

Components:
- Kaggle Experiments → Learning from competition results
- Research-to-Code → Learning from implementation quality
- Memory Consolidation → Pattern extraction and retention
- Strategy Advisor → Adaptive approach selection

GPU Policy:
- ALL LLM inference uses GPU cluster (completeu-server > mac-studio > macbook-air)
- ALL training on Kaggle GPU/TPU (NEVER local CPU)

STATUS: Production Ready
"""

import asyncio
import json
import logging
import os
import platform
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict

from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.common import RetryPolicy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    return Path(__file__).parent.parent.parent


_STORAGE_BASE = _get_storage_base()

# Paths
DB_PATH = str(_STORAGE_BASE / "databases" / "cluster" / "shared_memories.db")
LEARNING_DIR = str(_STORAGE_BASE / "kaggle-competitions" / "learning")


@dataclass
class LearningInsight:
    """A learned insight from experiments"""
    insight_type: str  # success_pattern, failure_pattern, strategy, technique
    domain: str        # kaggle, research, implementation
    content: str
    confidence: float
    source_experiments: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ExperimentAnalysis:
    """Analysis of experiment results"""
    total_experiments: int
    success_rate: float
    best_approaches: List[Dict]
    worst_approaches: List[Dict]
    patterns_found: List[str]
    recommendations: List[str]


# ============================================================================
# ACTIVITIES: Data Collection
# ============================================================================

@activity.defn
async def collect_kaggle_experiments(hours_back: int = 24) -> List[Dict]:
    """Collect recent Kaggle experiment results."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cutoff = datetime.now() - timedelta(hours=hours_back)

    try:
        cursor.execute("""
            SELECT id, competition, approach, score, success_score, config, timestamp
            FROM kaggle_experiments
            WHERE created_at >= ?
            ORDER BY created_at DESC
        """, (cutoff.isoformat(),))

        experiments = []
        for row in cursor.fetchall():
            experiments.append({
                "id": row[0],
                "competition": row[1],
                "approach": row[2],
                "score": row[3],
                "success_score": row[4],
                "config": json.loads(row[5]) if row[5] else {},
                "timestamp": row[6]
            })

        logger.info(f"Collected {len(experiments)} Kaggle experiments from last {hours_back}h")
        return experiments

    except Exception as e:
        logger.warning(f"Failed to collect experiments: {e}")
        return []
    finally:
        conn.close()


@activity.defn
async def collect_implementation_results(hours_back: int = 24) -> List[Dict]:
    """Collect recent research-to-code implementation results."""
    results_file = Path(LEARNING_DIR) / "implementation_log.jsonl"

    if not results_file.exists():
        return []

    cutoff = datetime.now() - timedelta(hours=hours_back)
    implementations = []

    with open(results_file, "r") as f:
        for line in f:
            try:
                impl = json.loads(line)
                impl_time = datetime.fromisoformat(impl.get("timestamp", "2000-01-01"))
                if impl_time >= cutoff:
                    implementations.append(impl)
            except:
                continue

    logger.info(f"Collected {len(implementations)} implementations from last {hours_back}h")
    return implementations


# ============================================================================
# ACTIVITIES: Pattern Analysis
# ============================================================================

@activity.defn
async def analyze_experiment_patterns(experiments: List[Dict]) -> Dict:
    """Analyze patterns in experiment results."""
    if not experiments:
        return {
            "patterns": [],
            "recommendations": [],
            "success_rate": 0.0
        }

    # Group by approach
    approach_results = {}
    for exp in experiments:
        approach = exp.get("approach", "unknown")
        if approach not in approach_results:
            approach_results[approach] = {"scores": [], "count": 0}
        approach_results[approach]["scores"].append(exp.get("score", 0))
        approach_results[approach]["count"] += 1

    # Calculate stats per approach
    approach_stats = []
    for approach, data in approach_results.items():
        avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
        approach_stats.append({
            "approach": approach,
            "avg_score": avg_score,
            "count": data["count"],
            "max_score": max(data["scores"]) if data["scores"] else 0,
            "min_score": min(data["scores"]) if data["scores"] else 0
        })

    # Sort by average score
    approach_stats.sort(key=lambda x: x["avg_score"], reverse=True)

    # Identify patterns
    patterns = []
    recommendations = []

    if approach_stats:
        best = approach_stats[0]
        if best["avg_score"] > 0.5:
            patterns.append(f"{best['approach']} consistently performs well (avg: {best['avg_score']:.2f})")
            recommendations.append(f"Prioritize {best['approach']} for similar competitions")

        if len(approach_stats) > 1:
            worst = approach_stats[-1]
            if worst["avg_score"] < 0.3:
                patterns.append(f"{worst['approach']} underperforms (avg: {worst['avg_score']:.2f})")
                recommendations.append(f"Consider alternatives to {worst['approach']}")

    # Overall success rate
    successful = sum(1 for e in experiments if e.get("success_score", 0) > 0.5)
    success_rate = successful / len(experiments) if experiments else 0

    logger.info(f"Analyzed {len(experiments)} experiments, {len(patterns)} patterns found")

    return {
        "patterns": patterns,
        "recommendations": recommendations,
        "success_rate": success_rate,
        "approach_stats": approach_stats
    }


@activity.defn
async def extract_learning_insights(analysis: Dict, domain: str = "kaggle") -> List[Dict]:
    """Extract actionable learning insights from analysis."""
    insights = []

    # Success patterns
    for pattern in analysis.get("patterns", []):
        insight = LearningInsight(
            insight_type="success_pattern" if "well" in pattern else "failure_pattern",
            domain=domain,
            content=pattern,
            confidence=analysis.get("success_rate", 0.5)
        )
        insights.append(asdict(insight))

    # Strategic recommendations
    for rec in analysis.get("recommendations", []):
        insight = LearningInsight(
            insight_type="strategy",
            domain=domain,
            content=rec,
            confidence=0.7
        )
        insights.append(asdict(insight))

    # Approach rankings
    for i, stat in enumerate(analysis.get("approach_stats", [])[:3]):
        insight = LearningInsight(
            insight_type="technique",
            domain=domain,
            content=f"Rank {i+1}: {stat['approach']} (avg: {stat['avg_score']:.2f}, n={stat['count']})",
            confidence=min(0.95, 0.5 + (stat['count'] / 20))  # More experiments = higher confidence
        )
        insights.append(asdict(insight))

    logger.info(f"Extracted {len(insights)} learning insights")
    return insights


# ============================================================================
# ACTIVITIES: Memory Storage
# ============================================================================

@activity.defn
async def store_learning_insights(insights: List[Dict]) -> Dict:
    """Store learning insights in persistent memory."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Create table if needed
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                insight_type TEXT,
                domain TEXT,
                content TEXT,
                confidence REAL,
                source_experiments TEXT,
                timestamp TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        stored = 0
        for insight in insights:
            cursor.execute("""
                INSERT INTO learning_insights (insight_type, domain, content, confidence, source_experiments, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                insight.get("insight_type"),
                insight.get("domain"),
                insight.get("content"),
                insight.get("confidence"),
                json.dumps(insight.get("source_experiments", [])),
                insight.get("timestamp")
            ))
            stored += 1

        conn.commit()
        logger.info(f"Stored {stored} learning insights in database")

        return {"stored": stored, "success": True}

    except Exception as e:
        logger.error(f"Failed to store insights: {e}")
        return {"stored": 0, "success": False, "error": str(e)}
    finally:
        conn.close()


@activity.defn
async def get_relevant_insights(domain: str, limit: int = 10) -> List[Dict]:
    """Retrieve relevant past insights for decision making."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT insight_type, domain, content, confidence, timestamp
            FROM learning_insights
            WHERE domain = ? OR domain = 'general'
            ORDER BY confidence DESC, created_at DESC
            LIMIT ?
        """, (domain, limit))

        insights = []
        for row in cursor.fetchall():
            insights.append({
                "insight_type": row[0],
                "domain": row[1],
                "content": row[2],
                "confidence": row[3],
                "timestamp": row[4]
            })

        logger.info(f"Retrieved {len(insights)} relevant insights for {domain}")
        return insights

    except Exception as e:
        logger.warning(f"Failed to retrieve insights: {e}")
        return []
    finally:
        conn.close()


# ============================================================================
# ACTIVITIES: Strategy Adaptation
# ============================================================================

@activity.defn
async def update_strategy_weights(insights: List[Dict]) -> Dict:
    """Update strategy weights based on accumulated insights."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Create strategy table if needed
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_weights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT UNIQUE,
                weight REAL DEFAULT 1.0,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Update weights based on insights
        updates = 0
        for insight in insights:
            content = insight.get("content", "")
            confidence = insight.get("confidence", 0.5)

            # Extract strategy/approach name from content
            for approach in ["XGBoost", "LightGBM", "CatBoost", "EfficientNet", "BERT", "Transformer"]:
                if approach.lower() in content.lower():
                    # Check if it's positive or negative
                    is_positive = "well" in content or "Rank 1" in content or "Prioritize" in content
                    weight_change = confidence * 0.1 if is_positive else -confidence * 0.1

                    cursor.execute("""
                        INSERT INTO strategy_weights (strategy_name, weight, success_count, failure_count)
                        VALUES (?, 1.0 + ?, ?, ?)
                        ON CONFLICT(strategy_name) DO UPDATE SET
                            weight = weight + ?,
                            success_count = success_count + ?,
                            failure_count = failure_count + ?,
                            last_updated = CURRENT_TIMESTAMP
                    """, (
                        approach, weight_change,
                        1 if is_positive else 0,
                        0 if is_positive else 1,
                        weight_change,
                        1 if is_positive else 0,
                        0 if is_positive else 1
                    ))
                    updates += 1

        conn.commit()
        logger.info(f"Updated {updates} strategy weights")

        return {"updates": updates, "success": True}

    except Exception as e:
        logger.error(f"Failed to update strategy weights: {e}")
        return {"updates": 0, "success": False, "error": str(e)}
    finally:
        conn.close()


@activity.defn
async def get_best_strategies(domain: str = "kaggle", top_n: int = 5) -> List[Dict]:
    """Get current best strategies based on accumulated learning."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT strategy_name, weight, success_count, failure_count, last_updated
            FROM strategy_weights
            ORDER BY weight DESC
            LIMIT ?
        """, (top_n,))

        strategies = []
        for row in cursor.fetchall():
            total = row[2] + row[3]
            success_rate = row[2] / total if total > 0 else 0.5
            strategies.append({
                "strategy": row[0],
                "weight": row[1],
                "success_rate": success_rate,
                "total_experiments": total,
                "last_updated": row[4]
            })

        logger.info(f"Retrieved top {len(strategies)} strategies")
        return strategies

    except Exception as e:
        logger.warning(f"Failed to get strategies: {e}")
        return []
    finally:
        conn.close()


# ============================================================================
# MAIN WORKFLOW
# ============================================================================

@workflow.defn
class SelfImprovementFeedbackLoop:
    """
    Main self-improvement workflow that runs periodically.

    Steps:
    1. Collect recent experiment data
    2. Analyze patterns in results
    3. Extract learning insights
    4. Store in persistent memory
    5. Update strategy weights
    6. Generate recommendations for next cycle
    """

    @workflow.run
    async def run(self, hours_back: int = 24) -> Dict:
        # Step 1: Collect experiment data
        kaggle_experiments = await workflow.execute_activity(
            collect_kaggle_experiments,
            args=[hours_back],
            start_to_close_timeout=timedelta(minutes=5)
        )

        implementations = await workflow.execute_activity(
            collect_implementation_results,
            args=[hours_back],
            start_to_close_timeout=timedelta(minutes=5)
        )

        # Step 2: Analyze patterns
        kaggle_analysis = await workflow.execute_activity(
            analyze_experiment_patterns,
            args=[kaggle_experiments],
            start_to_close_timeout=timedelta(minutes=5)
        )

        # Step 3: Extract insights
        insights = await workflow.execute_activity(
            extract_learning_insights,
            args=[kaggle_analysis, "kaggle"],
            start_to_close_timeout=timedelta(minutes=5)
        )

        # Step 4: Store insights
        storage_result = await workflow.execute_activity(
            store_learning_insights,
            args=[insights],
            start_to_close_timeout=timedelta(minutes=5)
        )

        # Step 5: Update strategy weights
        strategy_result = await workflow.execute_activity(
            update_strategy_weights,
            args=[insights],
            start_to_close_timeout=timedelta(minutes=5)
        )

        # Step 6: Get current best strategies
        best_strategies = await workflow.execute_activity(
            get_best_strategies,
            args=["kaggle", 5],
            start_to_close_timeout=timedelta(minutes=5)
        )

        return {
            "experiments_analyzed": {
                "kaggle": len(kaggle_experiments),
                "implementations": len(implementations)
            },
            "patterns_found": len(kaggle_analysis.get("patterns", [])),
            "insights_stored": storage_result.get("stored", 0),
            "strategy_updates": strategy_result.get("updates", 0),
            "current_best_strategies": best_strategies,
            "success_rate": kaggle_analysis.get("success_rate", 0),
            "timestamp": workflow.now().isoformat()
        }


# ============================================================================
# TEST FUNCTION
# ============================================================================

async def test_feedback_loop():
    """Test the self-improvement feedback loop."""
    print("\n" + "="*60)
    print("Self-Improvement Feedback Loop Test")
    print("="*60)

    # Test data collection
    print("\n[1/5] Collecting Kaggle experiments...")
    experiments = await collect_kaggle_experiments(hours_back=168)  # Last week
    print(f"  Found {len(experiments)} experiments")

    # Test pattern analysis
    print("\n[2/5] Analyzing patterns...")
    analysis = await analyze_experiment_patterns(experiments)
    print(f"  Patterns: {analysis.get('patterns', [])}")
    print(f"  Success rate: {analysis.get('success_rate', 0):.1%}")

    # Test insight extraction
    print("\n[3/5] Extracting insights...")
    insights = await extract_learning_insights(analysis, "kaggle")
    print(f"  Extracted {len(insights)} insights")
    for i, insight in enumerate(insights[:3]):
        print(f"    {i+1}. [{insight['insight_type']}] {insight['content'][:60]}...")

    # Test storage
    print("\n[4/5] Storing insights...")
    storage = await store_learning_insights(insights)
    print(f"  Stored: {storage.get('stored', 0)}")

    # Test strategy update
    print("\n[5/5] Updating strategies...")
    strategy = await update_strategy_weights(insights)
    print(f"  Updated: {strategy.get('updates', 0)} strategies")

    # Get best strategies
    print("\n" + "-"*40)
    print("Current Best Strategies:")
    best = await get_best_strategies("kaggle", 5)
    for s in best:
        print(f"  {s['strategy']}: weight={s['weight']:.2f}, success={s['success_rate']:.1%}")

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_feedback_loop())

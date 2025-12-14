#!/usr/bin/env python3
"""
Meta-Learning Workflow
======================

AGI CRITICAL CAPABILITY: Learning HOW to learn

This workflow implements meta-learning - tracking which learning strategies
work best for which domains and automatically selecting optimal approaches.

Components:
1. Strategy Registry - Catalog of learning strategies
2. Domain Classifier - Identify problem domain from context
3. Strategy Selector - Match domains to effective strategies
4. Outcome Tracker - Update strategy effectiveness over time
5. Meta-Optimizer - Learn patterns in strategy success

GPU Policy:
- ALL LLM inference uses GPU cluster (completeu-server > mac-studio > macbook-air)
- NEVER run LLM on local CPU

STATUS: Production Ready
"""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict

from temporalio import workflow, activity
from temporalio.common import RetryPolicy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = "/mnt/agentic-system/databases/cluster/shared_memories.db"


@dataclass
class LearningStrategy:
    """A registered learning strategy"""
    name: str
    strategy_type: str  # algorithm, architecture, approach, technique
    description: str
    applicable_domains: List[str]
    success_rate: float = 0.5
    usage_count: int = 0
    avg_improvement: float = 0.0


@dataclass
class MetaLearningInsight:
    """Insight about learning patterns"""
    domain: str
    best_strategy: str
    success_rate: float
    sample_size: int
    discovered_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# LEARNING STRATEGY REGISTRY
# ============================================================================

DEFAULT_STRATEGIES = [
    LearningStrategy(
        name="gradient_boosting",
        strategy_type="algorithm",
        description="XGBoost/LightGBM for tabular data",
        applicable_domains=["tabular", "classification", "regression", "kaggle"]
    ),
    LearningStrategy(
        name="transformer_finetuning",
        strategy_type="architecture",
        description="Fine-tune pretrained transformers",
        applicable_domains=["nlp", "text", "language", "qa"]
    ),
    LearningStrategy(
        name="cnn_transfer",
        strategy_type="architecture",
        description="Transfer learning with pretrained CNNs",
        applicable_domains=["vision", "image", "classification", "segmentation"]
    ),
    LearningStrategy(
        name="symbolic_regression",
        strategy_type="technique",
        description="PySR symbolic equation discovery",
        applicable_domains=["physics", "math", "scientific", "interpretable"]
    ),
    LearningStrategy(
        name="ensemble_stacking",
        strategy_type="approach",
        description="Combine multiple models via stacking",
        applicable_domains=["kaggle", "competition", "high_performance"]
    ),
    LearningStrategy(
        name="incremental_learning",
        strategy_type="approach",
        description="Learn continuously without forgetting",
        applicable_domains=["streaming", "online", "continuous"]
    ),
    LearningStrategy(
        name="few_shot_prompting",
        strategy_type="technique",
        description="Learn from few examples via prompting",
        applicable_domains=["nlp", "classification", "low_data"]
    ),
    LearningStrategy(
        name="curriculum_learning",
        strategy_type="approach",
        description="Start easy, progressively harder",
        applicable_domains=["complex", "multi_stage", "difficult"]
    ),
    LearningStrategy(
        name="self_supervised",
        strategy_type="technique",
        description="Learn from unlabeled data",
        applicable_domains=["unsupervised", "representation", "pretraining"]
    ),
    LearningStrategy(
        name="reinforcement_learning",
        strategy_type="algorithm",
        description="Learn from reward signals",
        applicable_domains=["sequential", "decision", "game", "optimization"]
    )
]


# ============================================================================
# ACTIVITIES
# ============================================================================

@activity.defn
async def initialize_strategy_registry() -> Dict:
    """Initialize the learning strategy registry in database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Create strategy registry table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                strategy_type TEXT,
                description TEXT,
                applicable_domains TEXT,
                success_rate REAL DEFAULT 0.5,
                usage_count INTEGER DEFAULT 0,
                avg_improvement REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create domain-strategy mapping table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS domain_strategy_map (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT,
                strategy_name TEXT,
                success_rate REAL DEFAULT 0.5,
                sample_size INTEGER DEFAULT 0,
                last_success TIMESTAMP,
                UNIQUE(domain, strategy_name)
            )
        """)

        # Insert default strategies
        inserted = 0
        for strategy in DEFAULT_STRATEGIES:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO learning_strategies
                    (name, strategy_type, description, applicable_domains)
                    VALUES (?, ?, ?, ?)
                """, (
                    strategy.name,
                    strategy.strategy_type,
                    strategy.description,
                    json.dumps(strategy.applicable_domains)
                ))
                if cursor.rowcount > 0:
                    inserted += 1
            except:
                pass

        conn.commit()
        logger.info(f"Initialized strategy registry with {inserted} new strategies")

        return {"success": True, "strategies_added": inserted}

    except Exception as e:
        logger.error(f"Failed to initialize registry: {e}")
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@activity.defn
async def classify_domain(task_description: str, context: Dict) -> Dict:
    """Classify the domain of a learning task."""
    # Simple keyword-based classification
    # In production, this would use LLM for more sophisticated classification

    domain_keywords = {
        "tabular": ["csv", "dataframe", "columns", "rows", "features", "tabular"],
        "vision": ["image", "photo", "pixel", "cnn", "visual", "picture"],
        "nlp": ["text", "language", "nlp", "sentence", "word", "document"],
        "time_series": ["time", "temporal", "forecast", "trend", "series"],
        "kaggle": ["kaggle", "competition", "leaderboard", "submission"],
        "scientific": ["physics", "chemistry", "biology", "equation", "formula"],
        "optimization": ["optimize", "minimize", "maximize", "search", "tune"]
    }

    task_lower = task_description.lower()
    context_str = json.dumps(context).lower()
    combined = task_lower + " " + context_str

    detected_domains = []
    for domain, keywords in domain_keywords.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > 0:
            detected_domains.append((domain, score))

    # Sort by score
    detected_domains.sort(key=lambda x: x[1], reverse=True)

    primary_domain = detected_domains[0][0] if detected_domains else "general"
    secondary_domains = [d[0] for d in detected_domains[1:3]] if len(detected_domains) > 1 else []

    logger.info(f"Classified domain: {primary_domain} (secondary: {secondary_domains})")

    return {
        "primary_domain": primary_domain,
        "secondary_domains": secondary_domains,
        "confidence": min(1.0, detected_domains[0][1] / 3) if detected_domains else 0.3
    }


@activity.defn
async def select_best_strategy(domain: str, secondary_domains: List[str] = None) -> Dict:
    """Select the best learning strategy for a domain based on historical success."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # First, check domain-strategy mapping for proven success
        cursor.execute("""
            SELECT strategy_name, success_rate, sample_size
            FROM domain_strategy_map
            WHERE domain = ?
            ORDER BY success_rate DESC, sample_size DESC
            LIMIT 3
        """, (domain,))

        proven_strategies = cursor.fetchall()

        if proven_strategies and proven_strategies[0][2] >= 3:
            # We have enough data - use proven strategy
            best = proven_strategies[0]
            return {
                "strategy": best[0],
                "expected_success": best[1],
                "basis": "historical_data",
                "sample_size": best[2],
                "alternatives": [s[0] for s in proven_strategies[1:]]
            }

        # Not enough data - use strategy registry defaults
        cursor.execute("""
            SELECT name, success_rate, applicable_domains
            FROM learning_strategies
            WHERE applicable_domains LIKE ?
            ORDER BY success_rate DESC
            LIMIT 3
        """, (f'%"{domain}"%',))

        default_strategies = cursor.fetchall()

        if default_strategies:
            best = default_strategies[0]
            return {
                "strategy": best[0],
                "expected_success": best[1],
                "basis": "default_registry",
                "sample_size": 0,
                "alternatives": [s[0] for s in default_strategies[1:]]
            }

        # Fallback
        return {
            "strategy": "gradient_boosting",  # Safe default
            "expected_success": 0.5,
            "basis": "fallback",
            "sample_size": 0,
            "alternatives": ["transformer_finetuning", "ensemble_stacking"]
        }

    finally:
        conn.close()


@activity.defn
async def record_strategy_outcome(
    domain: str,
    strategy: str,
    success: bool,
    improvement: float = 0.0
) -> Dict:
    """Record the outcome of using a strategy for learning."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Update domain-strategy mapping
        cursor.execute("""
            INSERT INTO domain_strategy_map (domain, strategy_name, success_rate, sample_size, last_success)
            VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(domain, strategy_name) DO UPDATE SET
                success_rate = (success_rate * sample_size + ?) / (sample_size + 1),
                sample_size = sample_size + 1,
                last_success = CASE WHEN ? = 1 THEN ? ELSE last_success END
        """, (
            domain, strategy,
            1.0 if success else 0.0,
            datetime.now().isoformat() if success else None,
            1.0 if success else 0.0,
            1 if success else 0,
            datetime.now().isoformat()
        ))

        # Update strategy registry overall stats
        cursor.execute("""
            UPDATE learning_strategies
            SET usage_count = usage_count + 1,
                success_rate = (success_rate * usage_count + ?) / (usage_count + 1),
                avg_improvement = (avg_improvement * usage_count + ?) / (usage_count + 1),
                updated_at = CURRENT_TIMESTAMP
            WHERE name = ?
        """, (1.0 if success else 0.0, improvement, strategy))

        conn.commit()

        logger.info(f"Recorded {strategy} outcome for {domain}: success={success}")
        return {"success": True, "domain": domain, "strategy": strategy}

    except Exception as e:
        logger.error(f"Failed to record outcome: {e}")
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@activity.defn
async def extract_meta_insights(hours_back: int = 168) -> List[Dict]:
    """Extract meta-learning insights from recent outcomes."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Get domain-strategy success patterns
        cursor.execute("""
            SELECT domain, strategy_name, success_rate, sample_size
            FROM domain_strategy_map
            WHERE sample_size >= 3
            ORDER BY domain, success_rate DESC
        """)

        insights = []
        current_domain = None

        for row in cursor.fetchall():
            domain, strategy, rate, samples = row

            if domain != current_domain:
                # New domain - this is the best strategy
                insight = MetaLearningInsight(
                    domain=domain,
                    best_strategy=strategy,
                    success_rate=rate,
                    sample_size=samples
                )
                insights.append(asdict(insight))
                current_domain = domain

        logger.info(f"Extracted {len(insights)} meta-learning insights")
        return insights

    except Exception as e:
        logger.error(f"Failed to extract insights: {e}")
        return []
    finally:
        conn.close()


@activity.defn
async def get_strategy_recommendations(task_type: str = None) -> List[Dict]:
    """Get current best strategy recommendations."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        if task_type:
            cursor.execute("""
                SELECT name, strategy_type, description, success_rate, usage_count
                FROM learning_strategies
                WHERE applicable_domains LIKE ?
                ORDER BY success_rate DESC
                LIMIT 5
            """, (f'%{task_type}%',))
        else:
            cursor.execute("""
                SELECT name, strategy_type, description, success_rate, usage_count
                FROM learning_strategies
                ORDER BY success_rate DESC, usage_count DESC
                LIMIT 10
            """)

        recommendations = []
        for row in cursor.fetchall():
            recommendations.append({
                "strategy": row[0],
                "type": row[1],
                "description": row[2],
                "success_rate": row[3],
                "times_used": row[4]
            })

        return recommendations

    finally:
        conn.close()


@activity.defn
async def sync_insights_to_cluster_brain(insights: List[Dict]) -> Dict:
    """
    Sync meta-learning insights to the cluster brain.

    Makes insights available to ALL nodes in the cluster.
    """
    import sys
    sys.path.insert(0, "/mnt/agentic-system/mcp-servers/enhanced-memory-mcp")

    try:
        from agi_cluster_bridge import get_agi_cluster_bridge
        bridge = get_agi_cluster_bridge()

        synced_count = 0
        for insight in insights:
            if insight.get("sample_size", 0) >= 3:  # Only sync well-tested insights
                bridge.share_meta_learning_insight(
                    domain=insight.get("domain", "general"),
                    best_strategy=insight.get("best_strategy", "unknown"),
                    success_rate=insight.get("success_rate", 0.5),
                    sample_size=insight.get("sample_size", 0)
                )
                synced_count += 1

        logger.info(f"Synced {synced_count} meta-learning insights to cluster brain")
        return {
            "success": True,
            "synced_count": synced_count,
            "node_id": bridge.node_id
        }

    except Exception as e:
        logger.error(f"Failed to sync to cluster brain: {e}")
        return {"success": False, "error": str(e)}


@activity.defn
async def get_cluster_meta_insights() -> List[Dict]:
    """
    Get meta-learning insights from the cluster brain.

    Retrieves insights learned by ALL nodes.
    """
    import sys
    sys.path.insert(0, "/mnt/agentic-system/mcp-servers/enhanced-memory-mcp")

    try:
        from agi_cluster_bridge import get_agi_cluster_bridge
        bridge = get_agi_cluster_bridge()

        learnings = bridge.brain.get_learnings(category="meta_learning")

        insights = []
        for learning in learnings:
            # Parse insight from learning text
            text = learning.get("learning", "")
            if "META-LEARNING INSIGHT" in text:
                insights.append({
                    "learning_id": learning.get("id"),
                    "source_node": learning.get("learned_by"),
                    "text": text,
                    "created_at": learning.get("created_at")
                })

        logger.info(f"Retrieved {len(insights)} cluster meta-insights")
        return insights

    except Exception as e:
        logger.error(f"Failed to get cluster insights: {e}")
        return []


# ============================================================================
# MAIN WORKFLOW
# ============================================================================

@workflow.defn
class MetaLearningWorkflow:
    """
    Meta-Learning Workflow - Learning HOW to learn

    This workflow:
    1. Classifies the domain of a learning task
    2. Selects the best strategy based on historical success
    3. Records outcomes to improve future selections
    4. Extracts meta-level insights about learning patterns
    """

    @workflow.run
    async def run(self, task_description: str, context: Dict = None) -> Dict:
        context = context or {}

        # Ensure registry is initialized
        await workflow.execute_activity(
            initialize_strategy_registry,
            start_to_close_timeout=timedelta(minutes=2)
        )

        # Step 1: Classify the domain
        domain_info = await workflow.execute_activity(
            classify_domain,
            args=[task_description, context],
            start_to_close_timeout=timedelta(minutes=2)
        )

        # Step 2: Select best strategy
        strategy_selection = await workflow.execute_activity(
            select_best_strategy,
            args=[domain_info["primary_domain"], domain_info.get("secondary_domains", [])],
            start_to_close_timeout=timedelta(minutes=2)
        )

        return {
            "task": task_description,
            "domain": domain_info,
            "recommended_strategy": strategy_selection,
            "timestamp": workflow.now().isoformat()
        }


@workflow.defn
class MetaLearningConsolidationWorkflow:
    """
    Periodic meta-learning consolidation

    Runs to:
    1. Extract meta-insights from recent learning
    2. Update strategy rankings
    3. Identify patterns in what works
    4. Sync insights to cluster brain (NEW)
    5. Get insights from other nodes (NEW)
    """

    @workflow.run
    async def run(self, hours_back: int = 168, sync_to_cluster: bool = True) -> Dict:
        # Extract meta-insights
        insights = await workflow.execute_activity(
            extract_meta_insights,
            args=[hours_back],
            start_to_close_timeout=timedelta(minutes=5)
        )

        # Get current best strategies
        recommendations = await workflow.execute_activity(
            get_strategy_recommendations,
            start_to_close_timeout=timedelta(minutes=2)
        )

        # Sync to cluster brain
        cluster_sync = {"synced": False}
        if sync_to_cluster and insights:
            cluster_sync = await workflow.execute_activity(
                sync_insights_to_cluster_brain,
                args=[insights],
                start_to_close_timeout=timedelta(minutes=2)
            )

        # Get insights from other nodes
        cluster_insights = await workflow.execute_activity(
            get_cluster_meta_insights,
            start_to_close_timeout=timedelta(minutes=2)
        )

        return {
            "insights_extracted": len(insights),
            "insights": insights,
            "top_strategies": recommendations[:5],
            "cluster_sync": cluster_sync,
            "cluster_insights_count": len(cluster_insights),
            "timestamp": workflow.now().isoformat()
        }


# ============================================================================
# TEST
# ============================================================================

async def test_meta_learning():
    """Test meta-learning workflow."""
    print("\n" + "="*60)
    print("Meta-Learning Workflow Test")
    print("="*60)

    # Initialize registry
    print("\n[1/5] Initializing strategy registry...")
    result = await initialize_strategy_registry()
    print(f"  Registry initialized: {result}")

    # Test domain classification
    print("\n[2/5] Testing domain classification...")
    domain = await classify_domain(
        "Predict house prices from CSV with features like square footage",
        {"competition": "kaggle", "data_type": "tabular"}
    )
    print(f"  Domain: {domain}")

    # Test strategy selection
    print("\n[3/5] Testing strategy selection...")
    strategy = await select_best_strategy(domain["primary_domain"])
    print(f"  Selected: {strategy}")

    # Test outcome recording
    print("\n[4/5] Recording mock outcomes...")
    await record_strategy_outcome("tabular", "gradient_boosting", True, 0.15)
    await record_strategy_outcome("tabular", "gradient_boosting", True, 0.12)
    await record_strategy_outcome("tabular", "gradient_boosting", False, 0.0)
    await record_strategy_outcome("nlp", "transformer_finetuning", True, 0.25)
    print("  Outcomes recorded")

    # Extract insights
    print("\n[5/5] Extracting meta-insights...")
    insights = await extract_meta_insights(168)
    print(f"  Found {len(insights)} insights")
    for i in insights:
        print(f"    {i['domain']}: best={i['best_strategy']} ({i['success_rate']:.1%})")

    # Get recommendations
    print("\n" + "-"*40)
    print("Current Strategy Recommendations:")
    recs = await get_strategy_recommendations()
    for r in recs[:5]:
        print(f"  {r['strategy']}: {r['success_rate']:.1%} ({r['times_used']} uses)")

    print("\n" + "="*60)
    print("META-LEARNING TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_meta_learning())

#!/usr/bin/env python3
"""
Autonomous Memory Manager - Hourly memory tier management
Runs frequently to keep memory system healthy and optimized

Operations:
1. Promote high-access working memories to episodic
2. Promote pattern-rich episodes to semantic concepts
3. Promote repeated actions to procedural skills
4. Decay unused memories
5. Optimize memory distribution

STATUS: Production Ready
"""

import asyncio
import logging
from datetime import datetime, timedelta
from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker
import sys

# Auto-detect storage path for cross-platform compatibility
import os
STORAGE_BASE = os.environ.get('STORAGE_BASE', '/Volumes/SSDRAID0/agentic-system')
if not os.path.exists(STORAGE_BASE):
    STORAGE_BASE = '/home/marc/agentic-system'  # Linux fallback
sys.path.insert(0, f'{STORAGE_BASE}/mcp-servers/enhanced-memory-mcp')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_memory_db_path():
    """Get the primary memory database path - prioritize main Claude DB"""
    from pathlib import Path
    # Primary: Main Claude enhanced memory DB (has full schema)
    primary = Path.home() / ".claude" / "enhanced_memories" / "memory.db"
    if primary.exists():
        return primary
    # Fallback: agentic-system databases
    fallback = Path(STORAGE_BASE) / "databases" / "mcp" / "enhanced_memories.db"
    if fallback.exists():
        return fallback
    # Last resort: safla memories
    return Path(STORAGE_BASE) / "databases" / "safla_memories.db"


@activity.defn
async def curate_memories() -> dict:
    """Run memory curation across all tiers"""
    try:
        from safla_orchestrator import SAFLAOrchestrator

        db_path = get_memory_db_path()
        logger.info(f"Curating memories from: {db_path}")

        safla = SAFLAOrchestrator(db_path=db_path)
        result = await safla.autonomous_memory_curation()
        logger.info(f"Memory curation: {result}")
        return result
    except Exception as e:
        logger.error(f"Curation failed: {e}")
        return {"error": str(e)}


@activity.defn
async def analyze_distribution() -> dict:
    """Analyze memory distribution vs optimal 75/15 rule"""
    try:
        import sqlite3

        db_path = get_memory_db_path()
        logger.info(f"Analyzing distribution from: {db_path}")

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Count by tier
        tier_counts = {}
        for tier in ["working", "episodic", "semantic", "procedural"]:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {tier}_memory")
                tier_counts[tier] = cursor.fetchone()[0]
            except:
                tier_counts[tier] = 0

        # Also count main entities
        try:
            cursor.execute("SELECT COUNT(*) FROM entities")
            tier_counts["entities"] = cursor.fetchone()[0]
        except:
            tier_counts["entities"] = 0

        conn.close()

        total = sum(tier_counts.values())
        analysis = {
            "tier_counts": tier_counts,
            "total_memories": total,
            "distribution": {k: round(v/total*100, 1) if total > 0 else 0 for k, v in tier_counts.items()},
            "needs_optimization": False
        }

        # Check if working memory is overloaded
        if total > 10:
            working_pct = tier_counts.get("working", 0) / total * 100
            if working_pct > 60:
                analysis["needs_optimization"] = True
                analysis["optimization_reason"] = "Working memory overloaded"

        logger.info(f"Distribution analysis: {analysis}")
        return analysis
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return {"error": str(e)}


@activity.defn
async def optimize_tiers() -> dict:
    """Optimize memory tier assignments"""
    try:
        from safla_orchestrator import SAFLAOrchestrator

        db_path = get_memory_db_path()
        logger.info(f"Optimizing tiers from: {db_path}")

        safla = SAFLAOrchestrator(db_path=db_path)
        result = await safla.autonomous_memory_curation()

        optimization_result = {
            "status": "optimized",
            "promotions": result.get("promotions", {}),
            "demotions": result.get("demotions", {}),
            "total_changes": result.get("total_promoted", 0) + result.get("total_demoted", 0)
        }
        logger.info(f"Tier optimization: {optimization_result}")
        return optimization_result
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        return {"error": str(e)}


@activity.defn
async def get_memory_usage_patterns() -> dict:
    """Analyze memory usage patterns"""
    try:
        from safla_orchestrator import SAFLAOrchestrator

        db_path = get_memory_db_path()
        logger.info(f"Analyzing usage patterns from: {db_path}")

        safla = SAFLAOrchestrator(db_path=db_path)
        patterns = await safla.analyze_memory_usage_patterns()
        logger.info(f"Usage patterns: {patterns}")
        return patterns
    except Exception as e:
        logger.error(f"Pattern analysis failed: {e}")
        return {"error": str(e)}


@workflow.defn
class AutonomousMemoryManagerWorkflow:
    """
    Hourly memory management workflow
    Keeps memory system optimized and healthy
    """
    
    @workflow.run
    async def run(self) -> dict:
        workflow.logger.info("Starting autonomous memory management")
        
        results = {
            "start_time": workflow.now().isoformat(),
            "steps": {}
        }
        
        try:
            # Step 1: Analyze current distribution
            workflow.logger.info("Analyzing memory distribution...")
            distribution = await workflow.execute_activity(
                analyze_distribution,
                start_to_close_timeout=timedelta(minutes=2)
            )
            results["steps"]["distribution_analysis"] = distribution
            
            # Step 2: Run memory curation (tier promotions)
            workflow.logger.info("Running memory curation...")
            curation = await workflow.execute_activity(
                curate_memories,
                start_to_close_timeout=timedelta(minutes=5)
            )
            results["steps"]["curation"] = curation
            
            # Step 3: Optimize tier assignments if needed
            if distribution.get("needs_optimization", False):
                workflow.logger.info("Optimizing memory tiers...")
                optimization = await workflow.execute_activity(
                    optimize_tiers,
                    start_to_close_timeout=timedelta(minutes=3)
                )
                results["steps"]["tier_optimization"] = optimization
            
            # Step 4: Get usage patterns for learning
            workflow.logger.info("Analyzing usage patterns...")
            patterns = await workflow.execute_activity(
                get_memory_usage_patterns,
                start_to_close_timeout=timedelta(minutes=2)
            )
            results["steps"]["usage_patterns"] = patterns
            
            results["end_time"] = workflow.now().isoformat()
            results["status"] = "success"
            
            workflow.logger.info(f"Memory management complete: {results}")
            return results
            
        except Exception as e:
            workflow.logger.error(f"Memory management failed: {e}")
            results["error"] = str(e)
            results["status"] = "failed"
            return results


async def main():
    """Run worker for autonomous memory manager"""
    client = await Client.connect("localhost:7233")
    
    worker = Worker(
        client,
        task_queue="memory-manager",
        workflows=[AutonomousMemoryManagerWorkflow],
        activities=[
            curate_memories,
            analyze_distribution,
            optimize_tiers,
            get_memory_usage_patterns
        ]
    )
    
    logger.info("Autonomous Memory Manager Worker started on task_queue: memory-manager")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())

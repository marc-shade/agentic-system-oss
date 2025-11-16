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

sys.path.insert(0, '/home/marc/agentic-system/mcp-servers/enhanced-memory-mcp')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@activity.defn
async def curate_memories() -> dict:
    """Run memory curation across all tiers"""
    try:
        from server import autonomous_memory_curation
        result = await autonomous_memory_curation()
        logger.info(f"Memory curation: {result}")
        return result
    except Exception as e:
        logger.error(f"Curation failed: {e}")
        return {"error": str(e)}


@activity.defn
async def analyze_distribution() -> dict:
    """Analyze memory distribution vs optimal 75/15 rule"""
    try:
        from server import analyze_memory_distribution
        analysis = await analyze_memory_distribution()
        logger.info(f"Distribution analysis: {analysis}")
        return analysis
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return {"error": str(e)}


@activity.defn
async def optimize_tiers() -> dict:
    """Optimize memory tier assignments"""
    try:
        from server import optimize_memory_tiers
        result = await optimize_memory_tiers()
        logger.info(f"Tier optimization: {result}")
        return result
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        return {"error": str(e)}


@activity.defn
async def get_memory_usage_patterns() -> dict:
    """Analyze memory usage patterns"""
    try:
        from server import analyze_memory_usage_patterns
        patterns = await analyze_memory_usage_patterns()
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
            "start_time": datetime.now().isoformat(),
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
            
            results["end_time"] = datetime.now().isoformat()
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

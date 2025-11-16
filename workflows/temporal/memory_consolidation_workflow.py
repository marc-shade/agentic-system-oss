#!/usr/bin/env python3
"""
Memory Consolidation Workflow - Sleep-like memory processing
Runs nightly to consolidate episodic memories into semantic knowledge

Mimics human sleep consolidation:
1. Extract patterns from recent episodic memories
2. Discover causal relationships
3. Promote important memories to higher tiers
4. Compress old low-importance memories
5. Reinforce frequently accessed associations

STATUS: Production Ready
"""

import asyncio
import logging
from datetime import datetime, timedelta
from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker
import sys
import os

# Add MCP path for memory functions
sys.path.insert(0, '/home/marc/agentic-system/mcp-servers/enhanced-memory-mcp')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@activity.defn
async def run_pattern_extraction(time_window_hours: int = 24) -> dict:
    """Extract patterns from recent memories"""
    try:
        # Import here to avoid issues if MCP not loaded
        from server import (
            run_pattern_extraction as extract_patterns,
            get_consolidation_stats
        )
        
        result = await extract_patterns(
            time_window_hours=time_window_hours,
            min_pattern_frequency=2
        )
        
        logger.info(f"Pattern extraction: {result}")
        return result
    except Exception as e:
        logger.error(f"Pattern extraction failed: {e}")
        return {"error": str(e)}


@activity.defn
async def run_causal_discovery(time_window_hours: int = 24) -> dict:
    """Discover causal relationships from action outcomes"""
    try:
        from server import run_causal_discovery as discover_causal
        
        result = await discover_causal(
            time_window_hours=time_window_hours,
            min_confidence=0.6
        )
        
        logger.info(f"Causal discovery: {result}")
        return result
    except Exception as e:
        logger.error(f"Causal discovery failed: {e}")
        return {"error": str(e)}


@activity.defn
async def run_memory_compression(time_window_hours: int = 168) -> dict:
    """Compress old memories (older than 7 days)"""
    try:
        from server import run_memory_compression as compress_memories
        
        result = await compress_memories(
            time_window_hours=time_window_hours
        )
        
        logger.info(f"Memory compression: {result}")
        return result
    except Exception as e:
        logger.error(f"Memory compression failed: {e}")
        return {"error": str(e)}


@activity.defn
async def run_memory_curation() -> dict:
    """Promote memories between tiers"""
    try:
        from server import autonomous_memory_curation
        
        result = await autonomous_memory_curation()
        
        logger.info(f"Memory curation: {result}")
        return result
    except Exception as e:
        logger.error(f"Memory curation failed: {e}")
        return {"error": str(e)}


@activity.defn
async def get_consolidation_statistics() -> dict:
    """Get consolidation stats for monitoring"""
    try:
        from server import get_consolidation_stats
        
        stats = await get_consolidation_stats()
        logger.info(f"Consolidation stats: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return {"error": str(e)}


@workflow.defn
class MemoryConsolidationWorkflow:
    """
    Nightly memory consolidation workflow
    Runs comprehensive memory processing like human sleep
    """
    
    @workflow.run
    async def run(self, mode: str = "full") -> dict:
        """
        Args:
            mode: "full" (all steps), "patterns" (patterns only), 
                  "compression" (compression only)
        """
        workflow.logger.info(f"Starting memory consolidation - mode: {mode}")
        
        results = {
            "start_time": datetime.now().isoformat(),
            "mode": mode,
            "steps": {}
        }
        
        try:
            # Step 1: Extract patterns from recent episodic memories
            if mode in ["full", "patterns"]:
                workflow.logger.info("Extracting patterns from episodic memories...")
                pattern_result = await workflow.execute_activity(
                    run_pattern_extraction,
                    24,  # Last 24 hours
                    start_to_close_timeout=timedelta(minutes=5)
                )
                results["steps"]["pattern_extraction"] = pattern_result
            
            # Step 2: Discover causal relationships
            if mode in ["full", "patterns"]:
                workflow.logger.info("Discovering causal relationships...")
                causal_result = await workflow.execute_activity(
                    run_causal_discovery,
                    24,  # Last 24 hours
                    start_to_close_timeout=timedelta(minutes=5)
                )
                results["steps"]["causal_discovery"] = causal_result
            
            # Step 3: Promote memories between tiers
            if mode == "full":
                workflow.logger.info("Curating memories across tiers...")
                curation_result = await workflow.execute_activity(
                    run_memory_curation,
                    start_to_close_timeout=timedelta(minutes=5)
                )
                results["steps"]["memory_curation"] = curation_result
            
            # Step 4: Compress old memories
            if mode in ["full", "compression"]:
                workflow.logger.info("Compressing old memories...")
                compression_result = await workflow.execute_activity(
                    run_memory_compression,
                    168,  # Older than 7 days
                    start_to_close_timeout=timedelta(minutes=5)
                )
                results["steps"]["memory_compression"] = compression_result
            
            # Step 5: Get final statistics
            stats = await workflow.execute_activity(
                get_consolidation_statistics,
                start_to_close_timeout=timedelta(minutes=2)
            )
            results["final_stats"] = stats
            
            results["end_time"] = datetime.now().isoformat()
            results["status"] = "success"
            
            workflow.logger.info(f"Memory consolidation complete: {results}")
            return results
            
        except Exception as e:
            workflow.logger.error(f"Memory consolidation failed: {e}")
            results["error"] = str(e)
            results["status"] = "failed"
            return results


async def main():
    """Run worker for memory consolidation workflow"""
    client = await Client.connect("localhost:7233")
    
    worker = Worker(
        client,
        task_queue="memory-consolidation",
        workflows=[MemoryConsolidationWorkflow],
        activities=[
            run_pattern_extraction,
            run_causal_discovery,
            run_memory_compression,
            run_memory_curation,
            get_consolidation_statistics
        ]
    )
    
    logger.info("Memory Consolidation Worker started on task_queue: memory-consolidation")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
System Self-Optimization Workflow
Continuously learns and improves system configuration

Operations:
1. Monitor system performance metrics
2. Analyze bottlenecks and resource usage
3. Optimize configuration settings
4. Learn from past optimizations
5. Record improvements for future reference

STATUS: Production Ready
"""
import os
import platform

import asyncio
import logging
import psutil
import json
from datetime import datetime, timedelta
from pathlib import Path
from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker
import sys

sys.path.insert(0, '/home/marc/agentic-system/intelligent-self-healing')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@activity.defn
async def collect_performance_metrics() -> dict:
    """Collect current system performance metrics"""
    try:
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=2)
        load_avg = psutil.getloadavg()
        disk = psutil.disk_usage(str(_STORAGE_BASE))
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "memory": {
                "percent": memory.percent,
                "available_gb": memory.available / (1024**3),
                "used_gb": memory.used / (1024**3),
                "total_gb": memory.total / (1024**3)
            },
            "cpu": {
                "percent": cpu_percent,
                "load_1m": load_avg[0],
                "load_5m": load_avg[1],
                "load_15m": load_avg[2],
                "count": psutil.cpu_count()
            },
            "disk": {
                "percent": disk.percent,
                "free_gb": disk.free / (1024**3),
                "used_gb": disk.used / (1024**3)
            }
        }
        
        logger.info(f"Performance metrics: {metrics}")
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to collect metrics: {e}")
        return {"error": str(e)}


@activity.defn
async def analyze_bottlenecks(metrics: dict) -> dict:
    """Analyze metrics to identify bottlenecks"""
    try:
        bottlenecks = []
        recommendations = []
        
        # Memory analysis
        mem_percent = metrics.get("memory", {}).get("percent", 0)
        if mem_percent > 90:
            bottlenecks.append("critical_memory_pressure")
            recommendations.append("Reduce maxTokens, enable aggressive caching")
        elif mem_percent > 75:
            bottlenecks.append("high_memory_usage")
            recommendations.append("Enable memory-efficient settings")
        
        # CPU analysis
        cpu_percent = metrics.get("cpu", {}).get("percent", 0)
        load_1m = metrics.get("cpu", {}).get("load_1m", 0)
        cpu_count = metrics.get("cpu", {}).get("count", 1)
        
        if load_1m > cpu_count * 2:
            bottlenecks.append("cpu_overload")
            recommendations.append("Reduce parallel operations")
        elif cpu_percent > 80:
            bottlenecks.append("high_cpu_usage")
            recommendations.append("Optimize compute-intensive tasks")
        
        # Disk analysis
        disk_percent = metrics.get("disk", {}).get("percent", 0)
        if disk_percent > 90:
            bottlenecks.append("disk_space_critical")
            recommendations.append("Clean old logs and temporary files")
        
        analysis = {
            "bottlenecks": bottlenecks,
            "recommendations": recommendations,
            "severity": "critical" if any("critical" in b for b in bottlenecks) else "warning" if bottlenecks else "normal"
        }
        
        logger.info(f"Bottleneck analysis: {analysis}")
        return analysis
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return {"error": str(e)}


@activity.defn
async def apply_optimizations(analysis: dict, dry_run: bool = False) -> dict:
    """Apply configuration optimizations based on analysis"""
    try:
        from intelligent_config_agent import IntelligentConfigAgent
        
        agent = IntelligentConfigAgent()
        optimizations = []
        
        if "critical_memory_pressure" in analysis.get("bottlenecks", []):
            # Aggressive memory saving
            if not dry_run:
                agent.update_config("maxTokens", 150000, "Reduce token limit due to memory pressure")
                agent.update_config("cachingStrategy", "aggressive", "Enable aggressive caching")
            optimizations.append("reduced_max_tokens_to_150k")
            optimizations.append("enabled_aggressive_caching")
        
        elif "high_memory_usage" in analysis.get("bottlenecks", []):
            # Moderate memory saving
            if not dry_run:
                agent.update_config("maxTokens", 175000, "Optimize for memory efficiency")
            optimizations.append("reduced_max_tokens_to_175k")
        
        if "cpu_overload" in analysis.get("bottlenecks", []):
            # Reduce parallel load
            if not dry_run:
                agent.update_config("parallelToolCalls", False, "Reduce CPU load")
            optimizations.append("disabled_parallel_tool_calls")
        
        result = {
            "applied_optimizations": optimizations,
            "dry_run": dry_run,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Optimizations: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        return {"error": str(e)}


@activity.defn
async def record_optimization_outcome(optimization: dict, metrics_before: dict, metrics_after: dict) -> dict:
    """Record optimization outcome for learning"""
    try:
        # Store outcome in memory system for future learning
        from server import create_entities

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

        
        memory_improvement = metrics_before["memory"]["percent"] - metrics_after["memory"]["percent"]
        cpu_improvement = metrics_before["cpu"]["percent"] - metrics_after["cpu"]["percent"]
        
        observations = [
            f"Applied optimizations: {', '.join(optimization.get('applied_optimizations', []))}",
            f"Memory improvement: {memory_improvement:.1f}%",
            f"CPU improvement: {cpu_improvement:.1f}%",
            f"Effectiveness: {'high' if memory_improvement > 5 or cpu_improvement > 10 else 'moderate' if memory_improvement > 2 or cpu_improvement > 5 else 'low'}"
        ]
        
        entities = [{
            "name": f"optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "entityType": "system_optimization",
            "observations": observations
        }]
        
        result = await create_entities(entities=entities)
        logger.info(f"Recorded optimization outcome: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to record outcome: {e}")
        return {"error": str(e)}


@workflow.defn
class SystemOptimizationWorkflow:
    """
    Self-optimization workflow that learns and improves
    Runs periodically to keep system performant
    """
    
    @workflow.run
    async def run(self, dry_run: bool = False) -> dict:
        workflow.logger.info(f"Starting system optimization (dry_run: {dry_run})")
        
        results = {
            "start_time": datetime.now().isoformat(),
            "dry_run": dry_run,
            "steps": {}
        }
        
        try:
            # Step 1: Collect current metrics
            workflow.logger.info("Collecting performance metrics...")
            metrics_before = await workflow.execute_activity(
                collect_performance_metrics,
                start_to_close_timeout=timedelta(minutes=1)
            )
            results["steps"]["metrics_before"] = metrics_before
            
            # Step 2: Analyze for bottlenecks
            workflow.logger.info("Analyzing bottlenecks...")
            analysis = await workflow.execute_activity(
                analyze_bottlenecks,
                metrics_before,
                start_to_close_timeout=timedelta(minutes=1)
            )
            results["steps"]["analysis"] = analysis
            
            # Step 3: Apply optimizations if needed
            if analysis.get("bottlenecks"):
                workflow.logger.info("Applying optimizations...")
                optimization = await workflow.execute_activity(
                    apply_optimizations,
                    args=[analysis, dry_run],
                    start_to_close_timeout=timedelta(minutes=2)
                )
                results["steps"]["optimization"] = optimization
                
                # Step 4: Wait for changes to take effect
                if not dry_run:
                    await asyncio.sleep(30)
                    
                    # Step 5: Collect metrics after optimization
                    workflow.logger.info("Collecting post-optimization metrics...")
                    metrics_after = await workflow.execute_activity(
                        collect_performance_metrics,
                        start_to_close_timeout=timedelta(minutes=1)
                    )
                    results["steps"]["metrics_after"] = metrics_after
                    
                    # Step 6: Record outcome for learning
                    workflow.logger.info("Recording optimization outcome...")
                    outcome = await workflow.execute_activity(
                        record_optimization_outcome,
                        args=[optimization, metrics_before, metrics_after],
                        start_to_close_timeout=timedelta(minutes=1)
                    )
                    results["steps"]["recorded_outcome"] = outcome
            else:
                workflow.logger.info("No optimizations needed - system running optimally")
            
            results["end_time"] = datetime.now().isoformat()
            results["status"] = "success"
            
            workflow.logger.info(f"System optimization complete: {results}")
            return results
            
        except Exception as e:
            workflow.logger.error(f"System optimization failed: {e}")
            results["error"] = str(e)
            results["status"] = "failed"
            return results


async def main():
    """Run worker for system optimization workflow"""
    client = await Client.connect("localhost:7233")
    
    worker = Worker(
        client,
        task_queue="system-optimization",
        workflows=[SystemOptimizationWorkflow],
        activities=[
            collect_performance_metrics,
            analyze_bottlenecks,
            apply_optimizations,
            record_optimization_outcome
        ]
    )
    
    logger.info("System Optimization Worker started on task_queue: system-optimization")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())

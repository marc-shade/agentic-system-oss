#!/usr/bin/env python3
"""
PySR Symbolic Regression Tools for Enhanced Memory MCP

Provides MCP tool endpoints for discovering mathematical equations
from memory patterns using PySR symbolic regression.
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("pysr-tools")

# Import PySR engine
try:
    from agi.pysr_symbolic_regression import get_engine, PYSR_AVAILABLE
    logger.info(f"PySR symbolic regression {'available' if PYSR_AVAILABLE else 'not available'}")
except ImportError as e:
    logger.error(f"Failed to import PySR engine: {e}")
    PYSR_AVAILABLE = False


def register_pysr_tools(app, db_path: Path):
    """
    Register PySR symbolic regression tools with FastMCP app.

    Args:
        app: FastMCP application instance
        db_path: Path to SQLite database
    """

    @app.tool()
    async def pysr_discover_importance_equation(
        min_samples: int = 50,
        max_complexity: int = 15
    ) -> Dict[str, Any]:
        """
        Discover mathematical equation predicting memory importance scores.

        Uses PySR to find interpretable formulas that predict how important
        a memory will be based on its features (access count, content length,
        age, tags, tier).

        This enables the system to:
        - Calculate importance scores using discovered equations (not heuristics)
        - Understand mathematically why memories are important
        - Predict importance for new memories before storing

        Args:
            min_samples: Minimum number of memory samples needed (default: 50)
            max_complexity: Maximum equation complexity (default: 15)

        Returns:
            Dictionary with discovered equation, accuracy (R²), and model info

        Example Result:
            {
                "success": true,
                "equation": "0.5 + 0.3*log(access_count + 1) + 0.2*content_length/1000",
                "r2_score": 0.82,
                "samples_used": 156,
                "features": ["access_count", "content_length", "num_tags", "age_hours", "tier_numeric"]
            }
        """
        if not PYSR_AVAILABLE:
            return {
                "success": False,
                "error": "PySR not available - install with: pip install pysr"
            }

        try:
            engine = get_engine()
            result = engine.discover_importance_equation(
                min_samples=min_samples,
                max_complexity=max_complexity
            )
            logger.info(f"Importance equation discovery: {result.get('success', False)}")
            return result

        except Exception as e:
            logger.error(f"Importance equation discovery failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def pysr_discover_consolidation_equation(
        min_samples: int = 20,
        max_complexity: int = 12
    ) -> Dict[str, Any]:
        """
        Discover equation predicting memory consolidation effectiveness.

        Uses PySR to find mathematical relationships between consolidation
        parameters (time window, entity count) and effectiveness (patterns
        found, memories promoted).

        This enables:
        - Predicting consolidation outcomes before running
        - Optimizing consolidation scheduling
        - Understanding what makes consolidation effective

        Args:
            min_samples: Minimum consolidation jobs needed (default: 20)
            max_complexity: Maximum equation complexity (default: 12)

        Returns:
            Dictionary with equation, accuracy, and analysis

        Example Result:
            {
                "success": true,
                "equation": "(patterns_found + memories_promoted) / sqrt(entity_count)",
                "r2_score": 0.75,
                "samples_used": 24
            }
        """
        if not PYSR_AVAILABLE:
            return {
                "success": False,
                "error": "PySR not available - install with: pip install pysr"
            }

        try:
            engine = get_engine()
            result = engine.discover_consolidation_equation(
                min_samples=min_samples,
                max_complexity=max_complexity
            )
            logger.info(f"Consolidation equation discovery: {result.get('success', False)}")
            return result

        except Exception as e:
            logger.error(f"Consolidation equation discovery failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def pysr_discover_access_pattern_equation(
        min_samples: int = 100,
        max_complexity: int = 10
    ) -> Dict[str, Any]:
        """
        Discover equation predicting memory access frequency patterns.

        Uses PySR to find formulas that predict which memories will be
        accessed frequently based on their characteristics and history.

        This enables:
        - Predicting "hot" memories that need fast access
        - Optimizing memory tier placement
        - Understanding memory usage patterns

        Args:
            min_samples: Minimum memories with access data (default: 100)
            max_complexity: Maximum equation complexity (default: 10)

        Returns:
            Dictionary with equation and predictive accuracy

        Example Result:
            {
                "success": true,
                "equation": "log(1 + importance_score * access_rate * exp(-age_hours/1000))",
                "r2_score": 0.68,
                "samples_used": 342
            }
        """
        if not PYSR_AVAILABLE:
            return {
                "success": False,
                "error": "PySR not available - install with: pip install pysr"
            }

        try:
            engine = get_engine()
            result = engine.discover_access_pattern_equation(
                min_samples=min_samples,
                max_complexity=max_complexity
            )
            logger.info(f"Access pattern equation discovery: {result.get('success', False)}")
            return result

        except Exception as e:
            logger.error(f"Access pattern equation discovery failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def pysr_run_full_discovery() -> Dict[str, Any]:
        """
        Run complete PySR discovery pipeline for all memory patterns.

        Discovers three key equations:
        1. Memory importance prediction
        2. Consolidation effectiveness
        3. Access pattern prediction

        This is the main entry point for learning mathematical laws
        governing the AGI memory system.

        Returns:
            Combined results from all three discovery processes

        Example Result:
            {
                "started_at": "2025-01-22T10:30:00",
                "importance": {
                    "success": true,
                    "equation": "...",
                    "r2_score": 0.82
                },
                "consolidation": {
                    "success": true,
                    "equation": "...",
                    "r2_score": 0.75
                },
                "access_pattern": {
                    "success": true,
                    "equation": "...",
                    "r2_score": 0.68
                },
                "completed_at": "2025-01-22T10:35:00"
            }
        """
        if not PYSR_AVAILABLE:
            return {
                "success": False,
                "error": "PySR not available - install with: pip install pysr",
                "pysr_available": False
            }

        try:
            engine = get_engine()
            result = engine.run_full_discovery()
            logger.info("Full PySR discovery pipeline completed")
            return result

        except Exception as e:
            logger.error(f"Full discovery pipeline failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def pysr_predict_importance(
        access_count: int = 0,
        content_length: int = 0,
        num_tags: int = 0,
        age_hours: float = 0.0,
        tier_numeric: int = 0
    ) -> Dict[str, Any]:
        """
        Predict importance score using discovered PySR equation.

        Args:
            access_count: Number of times memory has been accessed
            content_length: Length of memory content in characters
            num_tags: Number of tags associated with memory
            age_hours: Age of memory in hours
            tier_numeric: Memory tier (0=working, 1=episodic, 2=semantic, 3=procedural)

        Returns:
            Predicted importance score (0.0 to 1.0)

        Example:
            pysr_predict_importance(access_count=10, content_length=500, num_tags=2, age_hours=24.0, tier_numeric=1)
            -> {"predicted_importance": 0.72, "using_equation": true}
        """
        if not PYSR_AVAILABLE:
            return {
                "success": False,
                "error": "PySR not available"
            }

        try:
            engine = get_engine()

            features = {
                "access_count": access_count,
                "content_length": content_length,
                "num_tags": num_tags,
                "age_hours": age_hours,
                "tier_numeric": tier_numeric
            }

            prediction = engine.predict_importance(features)

            if prediction is not None:
                return {
                    "success": True,
                    "predicted_importance": prediction,
                    "using_equation": True,
                    "features_used": features
                }
            else:
                return {
                    "success": False,
                    "error": "Importance model not trained yet - run pysr_discover_importance_equation first"
                }

        except Exception as e:
            logger.error(f"Importance prediction failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def pysr_get_equations() -> Dict[str, Any]:
        """
        Get all currently discovered PySR equations.

        Returns dictionary of human-readable mathematical formulas
        that the system has learned about its own operation.

        Returns:
            Dictionary mapping equation names to their formulas

        Example Result:
            {
                "importance": "0.5 + 0.3*log(access_count + 1) + 0.2*content_length/1000",
                "consolidation": "(patterns_found + memories_promoted) / sqrt(entity_count)",
                "access_pattern": "log(1 + importance_score * access_rate * exp(-age_hours/1000))"
            }
        """
        if not PYSR_AVAILABLE:
            return {
                "success": False,
                "error": "PySR not available"
            }

        try:
            engine = get_engine()
            equations = engine.get_all_equations()

            return {
                "success": True,
                "equations": equations,
                "count": len(equations)
            }

        except Exception as e:
            logger.error(f"Failed to get equations: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def pysr_load_models() -> Dict[str, Any]:
        """
        Load previously saved PySR models from disk.

        Attempts to load saved models from ~/.claude/enhanced_memories/pysr_models/
        This is useful after server restart to restore discovered equations.

        Returns:
            Status of each model load attempt

        Example Result:
            {
                "importance": true,
                "consolidation": true,
                "access_pattern": false,
                "loaded_count": 2
            }
        """
        if not PYSR_AVAILABLE:
            return {
                "success": False,
                "error": "PySR not available"
            }

        try:
            engine = get_engine()
            loaded = engine.load_saved_models()

            loaded_count = sum(1 for v in loaded.values() if v)

            return {
                "success": True,
                "models_loaded": loaded,
                "loaded_count": loaded_count,
                "total_models": len(loaded)
            }

        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def pysr_should_trigger_discovery() -> Dict[str, Any]:
        """
        Check if automatic PySR discovery should be triggered.

        Analyzes current system state to determine if equation discovery
        should run based on:
        - Data accumulation thresholds (50+ importance, 20+ consolidation, 100+ access samples)
        - Scheduled discovery intervals (default: 7 days)
        - New data available since last discovery

        This is called automatically by hooks, but can also be triggered manually
        to check discovery readiness.

        Returns:
            Dictionary with trigger decision and reasons

        Example Result:
            {
                "should_trigger": true,
                "reasons": [
                    "New importance data available",
                    "New consolidation data available",
                    "Scheduled discovery interval reached"
                ],
                "data_thresholds": {
                    "importance_ready": true,
                    "consolidation_ready": true,
                    "access_pattern_ready": false,
                    "any_ready": true
                },
                "scheduled_ready": true
            }
        """
        if not PYSR_AVAILABLE:
            return {
                "success": False,
                "error": "PySR not available"
            }

        try:
            from agi.pysr_hooks import should_trigger_discovery
            result = should_trigger_discovery()

            return {
                "success": True,
                **result
            }

        except Exception as e:
            logger.error(f"Failed to check discovery trigger: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def pysr_get_discovery_stats() -> Dict[str, Any]:
        """
        Get statistics and history about PySR discovery runs.

        Returns information about:
        - Total discoveries completed
        - Last discovery timestamp
        - Discovery history (last 10 runs with R² scores)
        - Next scheduled discovery time
        - Current data thresholds

        This helps monitor the learning progress of the AGI system's
        equation discovery capabilities.

        Returns:
            Statistics and history about discovery runs

        Example Result:
            {
                "total_discoveries": 3,
                "last_discovery": "2025-01-22T10:35:00",
                "history": [
                    {
                        "timestamp": "2025-01-22T10:35:00",
                        "importance_r2": 0.82,
                        "consolidation_r2": 0.75,
                        "access_pattern_r2": 0.68
                    }
                ],
                "next_scheduled": "2025-01-29T10:35:00",
                "current_thresholds": {
                    "importance_ready": false,
                    "consolidation_ready": false,
                    "access_pattern_ready": false
                }
            }
        """
        if not PYSR_AVAILABLE:
            return {
                "success": False,
                "error": "PySR not available"
            }

        try:
            from agi.pysr_hooks import get_discovery_stats
            stats = get_discovery_stats()

            return {
                "success": True,
                **stats
            }

        except Exception as e:
            logger.error(f"Failed to get discovery stats: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def pysr_configure_thresholds(
        importance_min: Optional[int] = None,
        consolidation_min: Optional[int] = None,
        access_min: Optional[int] = None,
        interval_hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Configure automatic discovery trigger thresholds.

        Allows customization of when PySR equation discovery automatically
        triggers based on data accumulation and scheduling.

        Args:
            importance_min: Minimum samples for importance discovery (default: 50)
            consolidation_min: Minimum samples for consolidation discovery (default: 20)
            access_min: Minimum samples for access pattern discovery (default: 100)
            interval_hours: Hours between scheduled discoveries (default: 168 / 7 days)

        Returns:
            Updated configuration

        Example:
            pysr_configure_thresholds(importance_min=100, interval_hours=336)
            # Increase importance threshold to 100, schedule every 2 weeks
        """
        if not PYSR_AVAILABLE:
            return {
                "success": False,
                "error": "PySR not available"
            }

        try:
            from agi.pysr_hooks import get_hooks_manager
            manager = get_hooks_manager()

            manager.configure_thresholds(
                importance_min=importance_min,
                consolidation_min=consolidation_min,
                access_min=access_min,
                interval_hours=interval_hours
            )

            return {
                "success": True,
                "message": "Thresholds updated successfully",
                "current_thresholds": manager.thresholds
            }

        except Exception as e:
            logger.error(f"Failed to configure thresholds: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def pysr_scheduler_start() -> Dict[str, Any]:
        """
        Start the periodic PySR discovery scheduler.

        Launches a background thread that automatically runs equation discovery
        based on configured intervals and trigger conditions.

        The scheduler will:
        - Check every hour (configurable) if discovery should run
        - Run discovery when scheduled interval reached (default: 7 days)
        - Run discovery when hooks detect sufficient new data
        - Optionally run consolidation before each discovery

        Returns:
            Status of scheduler startup

        Example Result:
            {
                "success": true,
                "message": "Scheduler started",
                "config": {...},
                "next_check": "2025-01-22T11:30:00"
            }
        """
        if not PYSR_AVAILABLE:
            return {
                "success": False,
                "error": "PySR not available"
            }

        try:
            from agi.pysr_scheduler import get_scheduler
            scheduler = get_scheduler()
            result = scheduler.start()

            return result

        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def pysr_scheduler_stop() -> Dict[str, Any]:
        """
        Stop the periodic PySR discovery scheduler.

        Gracefully stops the background scheduler thread.

        Returns:
            Status of scheduler shutdown
        """
        if not PYSR_AVAILABLE:
            return {
                "success": False,
                "error": "PySR not available"
            }

        try:
            from agi.pysr_scheduler import get_scheduler
            scheduler = get_scheduler()
            result = scheduler.stop()

            return result

        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def pysr_scheduler_status() -> Dict[str, Any]:
        """
        Get current status of the PySR discovery scheduler.

        Returns:
            Scheduler status, configuration, and statistics

        Example Result:
            {
                "running": true,
                "config": {
                    "auto_discovery_enabled": true,
                    "discovery_interval_hours": 168,
                    "check_interval_seconds": 3600
                },
                "next_scheduled": "2025-01-29T10:35:00",
                "last_discovery": "2025-01-22T10:35:00",
                "discovery_count": 3,
                "auto_discoveries": 2,
                "manual_discoveries": 1
            }
        """
        if not PYSR_AVAILABLE:
            return {
                "success": False,
                "error": "PySR not available"
            }

        try:
            from agi.pysr_scheduler import get_scheduler
            scheduler = get_scheduler()
            status = scheduler.get_status()

            return {
                "success": True,
                **status
            }

        except Exception as e:
            logger.error(f"Failed to get scheduler status: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def pysr_scheduler_configure(
        auto_discovery_enabled: Optional[bool] = None,
        discovery_interval_hours: Optional[int] = None,
        check_interval_seconds: Optional[int] = None,
        consolidation_before_discovery: Optional[bool] = None,
        min_time_since_last_discovery: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Configure the PySR discovery scheduler.

        Args:
            auto_discovery_enabled: Enable/disable automatic discovery
            discovery_interval_hours: Hours between scheduled discoveries (default: 168 / 7 days)
            check_interval_seconds: Seconds between scheduler checks (default: 3600 / 1 hour)
            consolidation_before_discovery: Run consolidation before discovery (default: True)
            min_time_since_last_discovery: Minimum hours between discoveries (default: 24)

        Returns:
            Updated configuration

        Example:
            pysr_scheduler_configure(discovery_interval_hours=336, check_interval_seconds=7200)
            # Check every 2 hours, run discovery every 2 weeks
        """
        if not PYSR_AVAILABLE:
            return {
                "success": False,
                "error": "PySR not available"
            }

        try:
            from agi.pysr_scheduler import get_scheduler
            scheduler = get_scheduler()

            result = scheduler.configure(
                auto_discovery_enabled=auto_discovery_enabled,
                discovery_interval_hours=discovery_interval_hours,
                check_interval_seconds=check_interval_seconds,
                consolidation_before_discovery=consolidation_before_discovery,
                min_time_since_last_discovery=min_time_since_last_discovery
            )

            return result

        except Exception as e:
            logger.error(f"Failed to configure scheduler: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def pysr_run_discovery_now(
        run_consolidation: bool = True
    ) -> Dict[str, Any]:
        """
        Manually trigger PySR discovery cycle immediately.

        Bypasses scheduler and runs discovery right now.
        Useful for testing or when you want immediate results.

        Args:
            run_consolidation: Run consolidation before discovery (default: True)

        Returns:
            Results from discovery cycle

        Example Result:
            {
                "started_at": "2025-01-22T10:30:00",
                "triggered_by": "manual",
                "consolidation": {...},
                "discovery": {
                    "importance": {...},
                    "consolidation": {...},
                    "access_pattern": {...}
                },
                "completed_at": "2025-01-22T10:35:00"
            }
        """
        if not PYSR_AVAILABLE:
            return {
                "success": False,
                "error": "PySR not available"
            }

        try:
            from agi.pysr_scheduler import get_scheduler
            scheduler = get_scheduler()

            # Temporarily override consolidation setting
            original_setting = scheduler.config["consolidation_before_discovery"]
            scheduler.config["consolidation_before_discovery"] = run_consolidation

            result = await scheduler.run_discovery_cycle(triggered_by="manual")

            # Restore original setting
            scheduler.config["consolidation_before_discovery"] = original_setting

            return {
                "success": True,
                **result
            }

        except Exception as e:
            logger.error(f"Manual discovery failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    logger.info("✅ PySR Symbolic Regression tools registered (including hooks and scheduler)")

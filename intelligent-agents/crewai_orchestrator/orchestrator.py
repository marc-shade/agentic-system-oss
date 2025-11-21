"""
CrewAI Orchestrator - Main Entry Point

Production-ready orchestration engine integrating CrewAI with existing
agentic system infrastructure including MCP tools, memory, and voice.
"""

import os
import json
import logging
import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
from dataclasses import dataclass, field

from crewai import LLM

from .agents import (
    ResearcherAgent,
    CoderAgent,
    ReviewerAgent,
    DocumenterAgent,
    AnalystAgent
)
from .crews import DevelopmentCrew, ResearchCrew, OptimizationCrew
from .tasks import TaskFactory
from .tools import MCPToolWrapper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CrewMetrics:
    """Performance metrics for crew execution."""
    crew_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_tokens: int = 0
    execution_time_seconds: float = 0.0
    status: str = "pending"
    errors: list[str] = field(default_factory=list)


class CrewAIOrchestrator:
    """
    Main orchestration engine for CrewAI integration.

    Provides:
    - Pre-configured crews for common workflows
    - MCP tool integration for enhanced capabilities
    - Memory persistence via enhanced-memory-mcp
    - Voice announcements via voice-mode-mcp
    - Performance monitoring and metrics
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        verbose: bool = True
    ):
        self.verbose = verbose
        self.config = self._load_config(config_path)
        self.llm = LLM(model=model)
        self.metrics: list[CrewMetrics] = []
        self._crews = {
            "development": DevelopmentCrew(self.llm, verbose),
            "research": ResearchCrew(self.llm, verbose),
            "optimization": OptimizationCrew(self.llm, verbose)
        }

    def _load_config(self, config_path: Optional[str] = None) -> dict:
        """Load configuration from YAML file."""
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"
        try:
            with open(config_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Could not load config: {e}, using defaults")
            return {}

    def run_development(
        self,
        requirements: str,
        language: str = "python",
        include_docs: bool = True,
        output_dir: Optional[str] = None
    ) -> dict:
        """
        Run full development lifecycle.

        Args:
            requirements: What to implement
            language: Programming language (default: python)
            include_docs: Generate documentation (default: True)
            output_dir: Optional directory for output files
        """
        metrics = CrewMetrics(crew_name="development", start_time=datetime.now())

        try:
            self._announce(f"Starting development crew for: {requirements[:50]}...")
            result = self._crews["development"].run(
                requirements=requirements,
                language=language,
                include_docs=include_docs,
                output_dir=output_dir
            )
            metrics.status = "completed"
            metrics.tasks_completed = result.get("tasks_completed", 0)
            self._store_learning("development", requirements, result)
            self._announce("Development crew completed successfully")

        except Exception as e:
            metrics.status = "failed"
            metrics.errors.append(str(e))
            logger.error(f"Development crew failed: {e}")
            result = {"status": "failed", "error": str(e)}

        metrics.end_time = datetime.now()
        metrics.execution_time_seconds = (metrics.end_time - metrics.start_time).total_seconds()
        self.metrics.append(metrics)

        return result

    def run_research(
        self,
        topic: str,
        analysis_type: str = "comprehensive",
        metrics: Optional[list[str]] = None,
        output_dir: Optional[str] = None
    ) -> dict:
        """
        Run deep research workflow.

        Args:
            topic: Research topic
            analysis_type: Type of analysis (default: comprehensive)
            metrics: Specific metrics to analyze
            output_dir: Optional directory for output files
        """
        crew_metrics = CrewMetrics(crew_name="research", start_time=datetime.now())

        try:
            self._announce(f"Starting research crew for: {topic[:50]}...")
            result = self._crews["research"].run(
                topic=topic,
                analysis_type=analysis_type,
                metrics=metrics,
                output_dir=output_dir
            )
            crew_metrics.status = "completed"
            crew_metrics.tasks_completed = result.get("tasks_completed", 0)
            self._store_learning("research", topic, result)
            self._announce("Research crew completed successfully")

        except Exception as e:
            crew_metrics.status = "failed"
            crew_metrics.errors.append(str(e))
            logger.error(f"Research crew failed: {e}")
            result = {"status": "failed", "error": str(e)}

        crew_metrics.end_time = datetime.now()
        crew_metrics.execution_time_seconds = (crew_metrics.end_time - crew_metrics.start_time).total_seconds()
        self.metrics.append(crew_metrics)

        return result

    def run_optimization(
        self,
        target: str,
        goals: list[str],
        constraints: Optional[list[str]] = None,
        output_dir: Optional[str] = None
    ) -> dict:
        """
        Run optimization workflow.

        Args:
            target: What to optimize
            goals: Optimization goals
            constraints: Constraints to respect
            output_dir: Optional directory for output files
        """
        crew_metrics = CrewMetrics(crew_name="optimization", start_time=datetime.now())

        try:
            self._announce(f"Starting optimization crew for: {target[:50]}...")
            result = self._crews["optimization"].run(
                target=target,
                goals=goals,
                constraints=constraints,
                output_dir=output_dir
            )
            crew_metrics.status = "completed"
            crew_metrics.tasks_completed = result.get("tasks_completed", 0)
            self._store_learning("optimization", target, result)
            self._announce("Optimization crew completed successfully")

        except Exception as e:
            crew_metrics.status = "failed"
            crew_metrics.errors.append(str(e))
            logger.error(f"Optimization crew failed: {e}")
            result = {"status": "failed", "error": str(e)}

        crew_metrics.end_time = datetime.now()
        crew_metrics.execution_time_seconds = (crew_metrics.end_time - crew_metrics.start_time).total_seconds()
        self.metrics.append(crew_metrics)

        return result

    def get_metrics(self) -> list[dict]:
        """Get performance metrics for all crew executions."""
        return [
            {
                "crew_name": m.crew_name,
                "status": m.status,
                "tasks_completed": m.tasks_completed,
                "tasks_failed": m.tasks_failed,
                "execution_time_seconds": m.execution_time_seconds,
                "errors": m.errors
            }
            for m in self.metrics
        ]

    def get_summary(self) -> dict:
        """Get summary of all crew executions."""
        total = len(self.metrics)
        completed = sum(1 for m in self.metrics if m.status == "completed")
        failed = sum(1 for m in self.metrics if m.status == "failed")
        avg_time = sum(m.execution_time_seconds for m in self.metrics) / total if total else 0

        return {
            "total_runs": total,
            "completed": completed,
            "failed": failed,
            "success_rate": completed / total if total else 0,
            "average_execution_time_seconds": avg_time
        }

    def _announce(self, message: str) -> None:
        """Announce via voice mode if enabled."""
        if not self.config.get("mcp_integration", {}).get("voice_mode", {}).get("enabled", False):
            return

        import httpx
        try:
            httpx.post(
                "http://localhost:3102/converse",
                json={"message": message, "wait_for_response": False},
                timeout=10.0
            )
        except Exception:
            pass  # Voice not critical

    def _store_learning(self, crew_type: str, context: str, result: dict) -> None:
        """Store execution learnings in enhanced memory."""
        if not self.config.get("mcp_integration", {}).get("enhanced_memory", {}).get("enabled", False):
            return

        import httpx
        try:
            httpx.post(
                "http://localhost:3100/entities",
                json={
                    "entities": [{
                        "name": f"crewai_{crew_type}_{datetime.now().isoformat()}",
                        "entityType": "crew_execution",
                        "observations": [
                            f"crew_type: {crew_type}",
                            f"context: {context[:200]}",
                            f"status: {result.get('status', 'unknown')}",
                            f"tasks_completed: {result.get('tasks_completed', 0)}"
                        ]
                    }]
                },
                timeout=10.0
            )
        except Exception:
            pass  # Memory not critical


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="CrewAI Orchestrator")
    parser.add_argument("--crew", choices=["development", "research", "optimization"], required=True)
    parser.add_argument("--input", required=True, help="Task input/requirements")
    parser.add_argument("--output-dir", help="Output directory")
    parser.add_argument("--verbose", action="store_true", default=True)
    args = parser.parse_args()

    orchestrator = CrewAIOrchestrator(verbose=args.verbose)

    if args.crew == "development":
        result = orchestrator.run_development(args.input, output_dir=args.output_dir)
    elif args.crew == "research":
        result = orchestrator.run_research(args.input, output_dir=args.output_dir)
    elif args.crew == "optimization":
        result = orchestrator.run_optimization(
            args.input,
            goals=["improve performance", "reduce complexity"],
            output_dir=args.output_dir
        )

    print(json.dumps(result, indent=2))
    print("\nMetrics:", json.dumps(orchestrator.get_summary(), indent=2))


if __name__ == "__main__":
    main()

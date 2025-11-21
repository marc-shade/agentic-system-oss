"""Optimization Crew - System and code optimization."""

from crewai import Crew, Process, LLM
from typing import Optional
from ..agents import AnalystAgent, CoderAgent, ReviewerAgent
from ..tasks import TaskFactory


class OptimizationCrew:
    """System optimization crew."""

    def __init__(self, llm: Optional[LLM] = None, verbose: bool = True):
        self.llm = llm
        self.verbose = verbose
        self._analyst = AnalystAgent.create(llm, verbose)
        self._coder = CoderAgent.create(llm, verbose)
        self._reviewer = ReviewerAgent.create(llm, verbose)

    def run(
        self,
        target: str,
        goals: list[str],
        constraints: Optional[list[str]] = None,
        output_dir: Optional[str] = None
    ) -> dict:
        """Execute optimization workflow."""
        tasks = []

        # Analysis phase
        analysis_task = TaskFactory.analysis_task(
            agent=self._analyst,
            target=target,
            analysis_type="performance",
            metrics=["latency", "throughput", "resource_usage"],
            output_file=f"{output_dir}/analysis.md" if output_dir else None
        )
        tasks.append(analysis_task)

        # Optimization implementation
        opt_task = TaskFactory.optimization_task(
            agent=self._coder,
            target=target,
            optimization_goals=goals,
            constraints=constraints,
            output_file=f"{output_dir}/optimizations.md" if output_dir else None
        )
        tasks.append(opt_task)

        # Review optimizations
        review_task = TaskFactory.code_review_task(
            agent=self._reviewer,
            code_context="Review optimization changes",
            focus_areas=["performance", "correctness", "side_effects"],
            output_file=f"{output_dir}/review.md" if output_dir else None
        )
        tasks.append(review_task)

        crew = Crew(
            agents=[self._analyst, self._coder, self._reviewer],
            tasks=tasks,
            process=Process.sequential,
            verbose=self.verbose,
            memory=True,
            max_rpm=10
        )

        result = crew.kickoff()
        return {
            "status": "completed",
            "result": str(result),
            "tasks_completed": len(tasks)
        }

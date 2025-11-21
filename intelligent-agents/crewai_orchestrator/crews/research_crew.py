"""Research Crew - Deep research and analysis."""

from crewai import Crew, Process, LLM
from typing import Optional
from ..agents import ResearcherAgent, AnalystAgent
from ..tasks import TaskFactory


class ResearchCrew:
    """Deep research and analysis crew."""

    def __init__(self, llm: Optional[LLM] = None, verbose: bool = True):
        self.llm = llm
        self.verbose = verbose
        self._researcher = ResearcherAgent.create(llm, verbose)
        self._analyst = AnalystAgent.create(llm, verbose)

    def run(
        self,
        topic: str,
        analysis_type: str = "comprehensive",
        metrics: Optional[list[str]] = None,
        output_dir: Optional[str] = None
    ) -> dict:
        """Execute research workflow."""
        tasks = []

        # Initial research
        research_task = TaskFactory.research_task(
            agent=self._researcher,
            topic=topic,
            output_file=f"{output_dir}/research.md" if output_dir else None
        )
        tasks.append(research_task)

        # Analysis of findings
        analysis_task = TaskFactory.analysis_task(
            agent=self._analyst,
            target=f"Research findings on: {topic}",
            analysis_type=analysis_type,
            metrics=metrics,
            output_file=f"{output_dir}/analysis.md" if output_dir else None
        )
        tasks.append(analysis_task)

        crew = Crew(
            agents=[self._researcher, self._analyst],
            tasks=tasks,
            process=Process.sequential,
            verbose=self.verbose,
            memory=True,
            max_rpm=15
        )

        result = crew.kickoff()
        return {
            "status": "completed",
            "result": str(result),
            "tasks_completed": len(tasks)
        }

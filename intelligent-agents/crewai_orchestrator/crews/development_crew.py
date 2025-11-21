"""Development Crew - Full software development lifecycle."""

from crewai import Crew, Process, LLM
from typing import Optional
from ..agents import ResearcherAgent, CoderAgent, ReviewerAgent, DocumenterAgent
from ..tasks import TaskFactory


class DevelopmentCrew:
    """Full development lifecycle crew."""

    def __init__(self, llm: Optional[LLM] = None, verbose: bool = True):
        self.llm = llm
        self.verbose = verbose
        self._researcher = ResearcherAgent.create(llm, verbose)
        self._coder = CoderAgent.create(llm, verbose)
        self._reviewer = ReviewerAgent.create(llm, verbose)
        self._documenter = DocumenterAgent.create(llm, verbose)

    def run(
        self,
        requirements: str,
        language: str = "python",
        include_docs: bool = True,
        output_dir: Optional[str] = None
    ) -> dict:
        """Execute full development workflow."""
        tasks = []

        # Research phase
        research_task = TaskFactory.research_task(
            agent=self._researcher,
            topic=f"Best practices and patterns for implementing: {requirements}",
            output_file=f"{output_dir}/research.md" if output_dir else None
        )
        tasks.append(research_task)

        # Implementation phase
        code_task = TaskFactory.code_implementation_task(
            agent=self._coder,
            requirements=requirements,
            language=language,
            context="Use research findings to inform implementation",
            output_file=f"{output_dir}/implementation.{language}" if output_dir else None
        )
        tasks.append(code_task)

        # Review phase
        review_task = TaskFactory.code_review_task(
            agent=self._reviewer,
            code_context="Review the implemented code",
            focus_areas=["security", "performance", "maintainability", "error handling"],
            output_file=f"{output_dir}/review.md" if output_dir else None
        )
        tasks.append(review_task)

        # Documentation phase
        if include_docs:
            doc_task = TaskFactory.documentation_task(
                agent=self._documenter,
                subject="The implemented solution",
                doc_type="technical",
                context="Document the final implementation",
                output_file=f"{output_dir}/README.md" if output_dir else None
            )
            tasks.append(doc_task)

        crew = Crew(
            agents=[self._researcher, self._coder, self._reviewer, self._documenter],
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

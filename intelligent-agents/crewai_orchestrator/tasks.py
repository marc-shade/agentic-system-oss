"""
Reusable Task Definitions for CrewAI

Production-ready task templates for common workflows.
"""

from crewai import Task, Agent
from typing import Optional, Any


class TaskFactory:
    """Factory for creating standardized tasks."""

    @staticmethod
    def research_task(
        agent: Agent,
        topic: str,
        context: Optional[str] = None,
        output_file: Optional[str] = None
    ) -> Task:
        """Create a research task."""
        description = f"""
        Conduct comprehensive research on: {topic}

        Requirements:
        1. Gather information from multiple sources
        2. Verify accuracy and relevance
        3. Identify key patterns and insights
        4. Note any gaps or uncertainties

        {f'Context: {context}' if context else ''}

        Deliver a structured research report with citations.
        """
        return Task(
            description=description,
            agent=agent,
            expected_output="Comprehensive research report with findings, sources, and recommendations",
            output_file=output_file
        )

    @staticmethod
    def code_implementation_task(
        agent: Agent,
        requirements: str,
        language: str = "python",
        context: Optional[str] = None,
        output_file: Optional[str] = None
    ) -> Task:
        """Create a code implementation task."""
        description = f"""
        Implement the following in {language}:

        {requirements}

        Requirements:
        1. Production-ready code only - no POC or demo code
        2. Include proper error handling
        3. Follow {language} best practices
        4. Add type hints where applicable
        5. Include docstrings for all public interfaces

        {f'Context: {context}' if context else ''}
        """
        return Task(
            description=description,
            agent=agent,
            expected_output=f"Complete, production-ready {language} implementation",
            output_file=output_file
        )

    @staticmethod
    def code_review_task(
        agent: Agent,
        code_context: str,
        focus_areas: Optional[list[str]] = None,
        output_file: Optional[str] = None
    ) -> Task:
        """Create a code review task."""
        areas = focus_areas or ["security", "performance", "maintainability", "best practices"]
        description = f"""
        Review the following code:

        {code_context}

        Focus areas:
        {chr(10).join(f'- {area}' for area in areas)}

        Requirements:
        1. Identify critical issues first
        2. Suggest specific improvements
        3. Note any security vulnerabilities
        4. Assess overall code quality
        """
        return Task(
            description=description,
            agent=agent,
            expected_output="Detailed code review with categorized findings and recommendations",
            output_file=output_file
        )

    @staticmethod
    def documentation_task(
        agent: Agent,
        subject: str,
        doc_type: str = "technical",
        context: Optional[str] = None,
        output_file: Optional[str] = None
    ) -> Task:
        """Create a documentation task."""
        description = f"""
        Create {doc_type} documentation for: {subject}

        Requirements:
        1. Clear and concise language
        2. Appropriate structure for {doc_type} documentation
        3. Include examples where helpful
        4. Cover edge cases and limitations

        {f'Context: {context}' if context else ''}
        """
        return Task(
            description=description,
            agent=agent,
            expected_output=f"Complete {doc_type} documentation ready for publication",
            output_file=output_file
        )

    @staticmethod
    def analysis_task(
        agent: Agent,
        target: str,
        analysis_type: str = "performance",
        metrics: Optional[list[str]] = None,
        output_file: Optional[str] = None
    ) -> Task:
        """Create an analysis task."""
        description = f"""
        Perform {analysis_type} analysis on: {target}

        {f'Metrics to analyze: {", ".join(metrics)}' if metrics else ''}

        Requirements:
        1. Quantitative analysis where possible
        2. Identify bottlenecks or issues
        3. Provide actionable recommendations
        4. Prioritize findings by impact
        """
        return Task(
            description=description,
            agent=agent,
            expected_output=f"{analysis_type.title()} analysis report with metrics, findings, and recommendations",
            output_file=output_file
        )

    @staticmethod
    def optimization_task(
        agent: Agent,
        target: str,
        optimization_goals: list[str],
        constraints: Optional[list[str]] = None,
        output_file: Optional[str] = None
    ) -> Task:
        """Create an optimization task."""
        description = f"""
        Optimize: {target}

        Goals:
        {chr(10).join(f'- {goal}' for goal in optimization_goals)}

        {f'Constraints: {chr(10).join(f"- {c}" for c in constraints)}' if constraints else ''}

        Requirements:
        1. Measure baseline performance
        2. Implement optimizations
        3. Verify improvements
        4. Document changes and rationale
        """
        return Task(
            description=description,
            agent=agent,
            expected_output="Optimization report with before/after metrics and implemented changes",
            output_file=output_file
        )

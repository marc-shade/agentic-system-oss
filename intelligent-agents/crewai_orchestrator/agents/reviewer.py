"""Reviewer Agent - Code quality and security analysis."""

from crewai import Agent, LLM
from ..tools import MCPToolWrapper


class ReviewerAgent:
    """Factory for creating review-focused agents."""

    @staticmethod
    def create(llm: LLM = None, verbose: bool = True) -> Agent:
        """Create a reviewer agent with MCP tool integration."""
        tools = MCPToolWrapper.get_analysis_tools() + MCPToolWrapper.get_memory_tools()

        return Agent(
            role="Code Review Specialist",
            goal="Ensure code quality, security, and adherence to best practices",
            backstory="""You are a quality-focused engineer with expertise in code review,
            security analysis, and performance optimization. You identify issues before
            they become problems, suggest specific improvements, and ensure all code
            meets production standards. You never approve code that has security
            vulnerabilities or violates best practices.""",
            tools=tools,
            llm=llm,
            verbose=verbose,
            allow_delegation=False,
            max_iter=10,
            max_rpm=10,
            memory=True
        )

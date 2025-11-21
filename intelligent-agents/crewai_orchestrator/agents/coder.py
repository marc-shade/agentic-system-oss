"""Coder Agent - Production-ready code implementation."""

from crewai import Agent, LLM
from ..tools import MCPToolWrapper


class CoderAgent:
    """Factory for creating coding-focused agents."""

    @staticmethod
    def create(llm: LLM = None, verbose: bool = True) -> Agent:
        """Create a coder agent with MCP tool integration."""
        tools = MCPToolWrapper.get_memory_tools() + MCPToolWrapper.get_analysis_tools()

        return Agent(
            role="Senior Software Engineer",
            goal="Write clean, efficient, production-ready code that follows best practices",
            backstory="""You are an experienced software developer specializing in Python,
            system architecture, and production-grade implementations. You never write
            POC or demo code - only complete, tested, production-ready solutions.
            You follow SOLID principles, write comprehensive error handling, and
            include proper documentation.""",
            tools=tools,
            llm=llm,
            verbose=verbose,
            allow_delegation=False,
            max_iter=15,
            max_rpm=10,
            memory=True
        )

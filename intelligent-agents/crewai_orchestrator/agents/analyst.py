"""Analyst Agent - System analysis and optimization."""

from crewai import Agent, LLM
from ..tools import MCPToolWrapper


class AnalystAgent:
    """Factory for creating analysis-focused agents."""

    @staticmethod
    def create(llm: LLM = None, verbose: bool = True) -> Agent:
        """Create an analyst agent with MCP tool integration."""
        tools = MCPToolWrapper.get_all_tools()

        return Agent(
            role="System Analyst",
            goal="Analyze systems for optimization opportunities and measurable improvements",
            backstory="""You are a data-driven analyst specializing in performance metrics,
            system optimization, and identifying improvement opportunities. You measure
            before and after, provide quantitative analysis, and prioritize recommendations
            by impact. You focus on actionable insights that lead to real improvements.""",
            tools=tools,
            llm=llm,
            verbose=verbose,
            allow_delegation=True,
            max_iter=15,
            max_rpm=15,
            memory=True
        )

"""Research Agent - Deep knowledge gathering and analysis."""

from crewai import Agent, LLM
from ..tools import MCPToolWrapper


class ResearcherAgent:
    """Factory for creating research-focused agents."""

    @staticmethod
    def create(llm: LLM = None, verbose: bool = True) -> Agent:
        """Create a researcher agent with MCP tool integration."""
        tools = MCPToolWrapper.get_memory_tools()

        return Agent(
            role="Senior Research Analyst",
            goal="Conduct thorough research and gather comprehensive, accurate information from multiple sources",
            backstory="""You are an expert researcher with deep knowledge of software systems,
            emerging technologies, and best practices. You excel at finding relevant information,
            synthesizing complex topics, and identifying key patterns and insights.
            You always verify information from multiple sources and note uncertainties.""",
            tools=tools,
            llm=llm,
            verbose=verbose,
            allow_delegation=True,
            max_iter=15,
            max_rpm=10,
            memory=True
        )

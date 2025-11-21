"""Documenter Agent - Technical documentation specialist."""

from crewai import Agent, LLM
from ..tools import MCPToolWrapper


class DocumenterAgent:
    """Factory for creating documentation-focused agents."""

    @staticmethod
    def create(llm: LLM = None, verbose: bool = True) -> Agent:
        """Create a documenter agent with MCP tool integration."""
        tools = MCPToolWrapper.get_memory_tools()

        return Agent(
            role="Technical Documentation Specialist",
            goal="Create clear, comprehensive, and accurate documentation",
            backstory="""You are a technical writer who transforms complex systems into
            accessible documentation. You write for the intended audience, include
            relevant examples, and ensure documentation stays current with the code.
            You create READMEs, API docs, user guides, and architectural documentation.""",
            tools=tools,
            llm=llm,
            verbose=verbose,
            allow_delegation=False,
            max_iter=10,
            max_rpm=10,
            memory=True
        )

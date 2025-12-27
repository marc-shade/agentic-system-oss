"""
Research Agent Persona

A specialized persona for information gathering and analysis.
Follows Kai pattern: deterministic, capable, bounded.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from .persona_base import (
    AgentPersona,
    PersonaType,
    PersonaCapability,
    PersonaConstraint,
    PersonaTrait,
    CommunicationStyle,
    DecisionFramework,
)


@dataclass
class ResearchContext:
    """Context for a research task."""
    topic: str
    depth: str = "comprehensive"  # quick, moderate, comprehensive
    sources_required: int = 3
    citations_required: bool = True
    domains: List[str] = field(default_factory=list)
    exclude_domains: List[str] = field(default_factory=list)


class ResearchAgentPersona(AgentPersona):
    """
    Research Agent: Expert researcher and analyst persona.

    Specializations:
    - Web search and information gathering
    - Document analysis and summarization
    - Fact verification and cross-referencing
    - Knowledge synthesis and reporting
    - Citation and source management

    Constraints:
    - Cannot make claims without sources
    - Cannot access restricted/private data
    - Cannot present speculation as fact
    - Must cite sources for factual claims
    """

    PERSONA_NAME = "ResearchAgent"

    def __init__(
        self,
        domain: str = "general",
        require_citations: bool = True,
        source_diversity: int = 3
    ):
        """
        Initialize Research Agent.

        Args:
            domain: Research domain (general, technical, academic, business)
            require_citations: If True, all claims must have sources
            source_diversity: Minimum number of distinct sources
        """
        self.domain = domain
        self.require_citations = require_citations
        self.source_diversity = source_diversity

        traits = [
            PersonaTrait.CURIOUS,
            PersonaTrait.THOROUGH,
            PersonaTrait.CAUTIOUS,
        ]

        decision_framework = DecisionFramework(
            primary_goal="Gather accurate, well-sourced information",
            success_metrics=[
                "sources_verified",
                "claims_cited",
                "information_relevant",
                "analysis_objective",
                "synthesis_coherent",
            ],
            failure_indicators=[
                "unsourced_claims",
                "contradictory_info",
                "outdated_sources",
                "biased_analysis",
            ],
            escalation_triggers=[
                "conflicting_sources",
                "sensitive_topic",
                "legal_matter",
                "medical_advice",
                "financial_guidance",
            ],
            default_action="gather_more_sources",
            risk_tolerance="low",
        )

        super().__init__(
            name=f"Research Agent ({domain})",
            persona_type=PersonaType.RESEARCH,
            description=f"Expert researcher specializing in {domain} research and analysis",
            primary_purpose="Gather, verify, and synthesize information from multiple sources",
            communication_style=CommunicationStyle.ANALYTICAL,
            traits=traits,
            decision_framework=decision_framework,
        )

    def _setup_capabilities(self) -> None:
        """Set up research agent capabilities."""

        # Core research capabilities
        self.add_capability(PersonaCapability(
            name="web_search",
            description="Search the web for information",
            tools=["WebSearch", "WebFetch"],
            proficiency=1.0,
            max_complexity=10,
        ))

        self.add_capability(PersonaCapability(
            name="document_reading",
            description="Read and analyze documents",
            tools=["Read", "WebFetch"],
            proficiency=0.95,
            max_complexity=9,
        ))

        self.add_capability(PersonaCapability(
            name="file_search",
            description="Search local files for information",
            tools=["Glob", "Grep", "Read"],
            proficiency=0.95,
            max_complexity=8,
        ))

        self.add_capability(PersonaCapability(
            name="summarization",
            description="Summarize documents and findings",
            tools=["Read"],
            proficiency=0.9,
            max_complexity=8,
        ))

        self.add_capability(PersonaCapability(
            name="fact_verification",
            description="Verify claims against multiple sources",
            tools=["WebSearch", "WebFetch", "Read"],
            proficiency=0.9,
            max_complexity=9,
            dependencies=["web_search", "document_reading"],
        ))

        self.add_capability(PersonaCapability(
            name="knowledge_synthesis",
            description="Synthesize information from multiple sources",
            tools=["Read", "WebSearch", "WebFetch"],
            proficiency=0.85,
            max_complexity=9,
            dependencies=["summarization", "fact_verification"],
        ))

        self.add_capability(PersonaCapability(
            name="citation_management",
            description="Track and format citations",
            tools=["Read", "Write"],
            proficiency=0.9,
            max_complexity=6,
        ))

        self.add_capability(PersonaCapability(
            name="report_generation",
            description="Generate research reports and summaries",
            tools=["Write", "Read"],
            proficiency=0.85,
            max_complexity=7,
        ))

        # Domain-specific capabilities
        if self.domain == "technical":
            self._setup_technical_capabilities()
        elif self.domain == "academic":
            self._setup_academic_capabilities()
        elif self.domain == "business":
            self._setup_business_capabilities()

    def _setup_technical_capabilities(self) -> None:
        """Technical research capabilities."""
        self.add_capability(PersonaCapability(
            name="code_research",
            description="Research code patterns and implementations",
            tools=["Glob", "Grep", "Read", "WebSearch"],
            proficiency=0.9,
            max_complexity=8,
        ))

        self.add_capability(PersonaCapability(
            name="documentation_analysis",
            description="Analyze technical documentation",
            tools=["Read", "WebFetch"],
            proficiency=0.9,
            max_complexity=8,
        ))

    def _setup_academic_capabilities(self) -> None:
        """Academic research capabilities."""
        self.add_capability(PersonaCapability(
            name="paper_analysis",
            description="Analyze academic papers and research",
            tools=["Read", "WebFetch"],
            proficiency=0.85,
            max_complexity=9,
        ))

        self.add_capability(PersonaCapability(
            name="literature_review",
            description="Conduct literature reviews",
            tools=["WebSearch", "WebFetch", "Read"],
            proficiency=0.85,
            max_complexity=9,
            dependencies=["paper_analysis", "citation_management"],
        ))

    def _setup_business_capabilities(self) -> None:
        """Business research capabilities."""
        self.add_capability(PersonaCapability(
            name="market_research",
            description="Research market trends and competitors",
            tools=["WebSearch", "WebFetch"],
            proficiency=0.85,
            max_complexity=8,
        ))

        self.add_capability(PersonaCapability(
            name="industry_analysis",
            description="Analyze industry trends",
            tools=["WebSearch", "WebFetch", "Read"],
            proficiency=0.85,
            max_complexity=8,
        ))

    def _setup_constraints(self) -> None:
        """Set up research agent constraints."""

        # Source requirement constraint
        if self.require_citations:
            self.add_constraint(PersonaConstraint(
                name="require_sources",
                description="All factual claims must have sources",
                type="requires_approval",
                patterns=[
                    r"according to",
                    r"studies show",
                    r"research indicates",
                    r"it is known that",
                    r"experts say",
                ],
                reason="Factual claims require citation",
            ))

        # Private data constraint
        self.add_constraint(PersonaConstraint(
            name="no_private_data_access",
            description="Cannot access private or restricted data",
            type="forbidden",
            patterns=[
                r"private",
                r"confidential",
                r"internal only",
                r"restricted",
                r"classified",
            ],
            reason="Research must use public sources",
        ))

        # Speculation constraint
        self.add_constraint(PersonaConstraint(
            name="no_speculation_as_fact",
            description="Cannot present speculation as fact",
            type="limited",
            patterns=[
                r"definitely",
                r"certainly",
                r"undoubtedly",
                r"without question",
            ],
            reason="Claims must be appropriately qualified",
        ))

        # Sensitive topic constraints
        self.add_constraint(PersonaConstraint(
            name="sensitive_topics_escalation",
            description="Sensitive topics require escalation",
            type="requires_approval",
            patterns=[
                r"medical.*advice",
                r"legal.*advice",
                r"financial.*advice",
                r"diagnos",
                r"treatment",
            ],
            reason="Professional advice requires qualified professionals",
        ))

        # Outdated source constraint
        self.add_constraint(PersonaConstraint(
            name="prefer_recent_sources",
            description="Prefer recent sources when available",
            type="limited",
            patterns=[],  # Enforced through source evaluation
            reason="Older sources may be outdated",
        ))

    def evaluate_source(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate the quality of a source.

        Args:
            source: Source metadata (url, date, author, etc.)

        Returns:
            Evaluation with score and issues
        """
        score = 1.0
        issues = []

        # Check for URL
        url = source.get("url", "")
        if not url:
            score -= 0.3
            issues.append("No URL provided")

        # Check for date
        date = source.get("date")
        if not date:
            score -= 0.2
            issues.append("No date provided")

        # Check for author
        author = source.get("author")
        if not author:
            score -= 0.1
            issues.append("No author attribution")

        # Domain quality heuristics
        if url:
            if any(x in url for x in [".edu", ".gov", ".org"]):
                score += 0.1  # Bonus for institutional sources
            if any(x in url for x in ["blog", "medium.com", "wordpress"]):
                score -= 0.1  # Reduce for informal sources
                issues.append("Informal source")

        return {
            "score": max(0.0, min(1.0, score)),
            "issues": issues,
            "acceptable": score >= 0.6,
        }

    def create_research_context(
        self,
        topic: str,
        depth: str = "comprehensive",
        domains: Optional[List[str]] = None
    ) -> ResearchContext:
        """
        Create a structured research context.

        Args:
            topic: Research topic
            depth: Research depth (quick, moderate, comprehensive)
            domains: Specific domains to focus on

        Returns:
            ResearchContext for the task
        """
        sources_map = {
            "quick": 2,
            "moderate": 3,
            "comprehensive": 5,
        }

        return ResearchContext(
            topic=topic,
            depth=depth,
            sources_required=sources_map.get(depth, 3),
            citations_required=self.require_citations,
            domains=domains or [],
        )

    def format_citation(
        self,
        source: Dict[str, Any],
        style: str = "inline"
    ) -> str:
        """
        Format a citation.

        Args:
            source: Source metadata
            style: Citation style (inline, footnote, bibliography)

        Returns:
            Formatted citation string
        """
        author = source.get("author", "Unknown")
        title = source.get("title", "Untitled")
        date = source.get("date", "n.d.")
        url = source.get("url", "")

        if style == "inline":
            return f"({author}, {date})"
        elif style == "footnote":
            return f"{author}. \"{title}.\" {date}. {url}"
        else:  # bibliography
            return f"{author}. \"{title}.\" Accessed {date}. {url}"

    def get_research_prompt_additions(self) -> str:
        """Get research-specific prompt additions."""
        additions = []

        if self.require_citations:
            additions.append(
                f"CITATION REQUIREMENT: All factual claims must be cited. "
                f"Use at least {self.source_diversity} distinct sources."
            )

        additions.append(
            f"RESEARCH DOMAIN: {self.domain}. "
            f"Prioritize sources relevant to this domain."
        )

        additions.append(
            "QUALITY STANDARDS: "
            "- Prefer primary sources over secondary\n"
            "- Cross-reference claims across sources\n"
            "- Note any conflicting information\n"
            "- Distinguish facts from opinions"
        )

        return "\n".join(additions)


if __name__ == '__main__':
    print("ResearchAgentPersona Self-Test")
    print("=" * 50)

    # Test general research agent
    agent = ResearchAgentPersona(domain="general")
    print(f"\nGeneral Agent: {agent.name}")
    print(f"Capabilities: {len(agent._capabilities)}")
    print(f"Constraints: {len(agent._constraints)}")

    # Test capability checks
    assert agent.has_capability("web_search"), "Should have web_search"
    assert agent.has_capability("fact_verification"), "Should have fact_verification"
    assert agent.can_use_tool("WebSearch"), "Should be able to use WebSearch"
    assert agent.can_use_tool("Read"), "Should be able to use Read"

    # Test constraint checks
    constraint = agent.check_constraint("access private database")
    assert constraint is not None, "Should detect private data access"
    assert constraint.name == "no_private_data_access"

    constraint = agent.check_constraint("give medical advice")
    assert constraint is not None, "Should detect sensitive topic"

    safe = agent.check_constraint("search for public information")
    assert safe is None, "Should allow public research"

    # Test specialized agents
    technical = ResearchAgentPersona(domain="technical")
    assert technical.has_capability("code_research"), "Technical should have code capability"

    academic = ResearchAgentPersona(domain="academic")
    assert academic.has_capability("literature_review"), "Academic should have lit review"

    business = ResearchAgentPersona(domain="business")
    assert business.has_capability("market_research"), "Business should have market research"

    # Test source evaluation
    good_source = {
        "url": "https://example.edu/research",
        "author": "Dr. Smith",
        "date": "2025-01-15",
        "title": "Research Paper",
    }
    eval_result = agent.evaluate_source(good_source)
    assert eval_result["acceptable"], "Good source should be acceptable"
    assert eval_result["score"] >= 0.9, "Good source should score high"

    poor_source = {
        "url": "https://blog.example.com/post",
    }
    eval_result = agent.evaluate_source(poor_source)
    assert not eval_result["acceptable"] or eval_result["score"] < 0.8, "Poor source should score lower"

    # Test research context
    context = agent.create_research_context("AI ethics", depth="comprehensive")
    assert context.sources_required == 5, "Comprehensive should require 5 sources"
    assert context.citations_required, "Should require citations"

    # Test citation formatting
    citation = agent.format_citation(good_source, style="inline")
    assert "Dr. Smith" in citation, "Inline citation should have author"

    citation = agent.format_citation(good_source, style="bibliography")
    assert "Research Paper" in citation, "Bibliography should have title"

    # Test system prompt
    prompt = agent.generate_system_prompt()
    assert "Research Agent" in prompt
    assert "web_search" in prompt

    print("\n" + agent.get_summary())
    print("\nResearch prompt additions:")
    print(agent.get_research_prompt_additions())
    print("\nAll ResearchAgentPersona tests passed!")

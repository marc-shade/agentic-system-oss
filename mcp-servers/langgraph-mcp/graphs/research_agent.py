"""Multi-step research agent with source tracking."""
from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import operator

class ResearchState(TypedDict):
    thread_id: str
    query: str
    sources: Annotated[list[dict], operator.add]
    findings: Annotated[list[str], operator.add]
    synthesis: str
    approved: bool
    messages: Annotated[Sequence[dict], operator.add]

def create_research_graph(llm, tools: list = None, checkpointer=None):
    """Create a research agent graph with optional tools and checkpointing."""

    async def plan_research(state: ResearchState) -> dict:
        """Plan research steps based on query."""
        response = await llm.ainvoke([
            {"role": "system", "content": "You are a research planner. Break down the query into specific research questions."},
            {"role": "user", "content": f"Plan research for: {state['query']}"}
        ])
        return {"findings": [f"Research plan: {response.content}"], "messages": [{"role": "assistant", "content": response.content}]}

    async def gather_sources(state: ResearchState) -> dict:
        """Gather sources for research."""
        response = await llm.ainvoke([
            {"role": "system", "content": "Identify key sources and references for this research."},
            {"role": "user", "content": f"Query: {state['query']}\nPlan: {state['findings'][-1] if state['findings'] else 'None'}"}
        ])
        sources = [{"type": "llm_generated", "content": response.content, "confidence": 0.7}]
        return {"sources": sources, "messages": [{"role": "assistant", "content": response.content}]}

    async def analyze_findings(state: ResearchState) -> dict:
        """Analyze gathered sources and extract findings."""
        sources_text = "\n".join([s.get("content", str(s)) for s in state["sources"]])
        response = await llm.ainvoke([
            {"role": "system", "content": "Analyze sources and extract key findings with citations."},
            {"role": "user", "content": f"Query: {state['query']}\nSources:\n{sources_text}"}
        ])
        return {"findings": [response.content], "messages": [{"role": "assistant", "content": response.content}]}

    async def synthesize(state: ResearchState) -> dict:
        """Synthesize findings into final report."""
        findings_text = "\n".join(state["findings"])
        response = await llm.ainvoke([
            {"role": "system", "content": "Synthesize research findings into a comprehensive report with proper citations."},
            {"role": "user", "content": f"Query: {state['query']}\nFindings:\n{findings_text}"}
        ])
        return {"synthesis": response.content, "messages": [{"role": "assistant", "content": response.content}]}

    def should_continue(state: ResearchState) -> str:
        """Determine if more research is needed."""
        if len(state["sources"]) < 3:
            return "gather_more"
        return "synthesize"

    graph = StateGraph(ResearchState)
    graph.add_node("plan", plan_research)
    graph.add_node("gather", gather_sources)
    graph.add_node("analyze", analyze_findings)
    graph.add_node("synthesize", synthesize)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "gather")
    graph.add_conditional_edges("gather", should_continue, {"gather_more": "gather", "synthesize": "analyze"})
    graph.add_edge("analyze", "synthesize")
    graph.add_edge("synthesize", END)

    return graph.compile(checkpointer=checkpointer)

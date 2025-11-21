"""Iterative code review agent with improvement suggestions."""
from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
import operator

class CodeReviewState(TypedDict):
    thread_id: str
    code: str
    language: str
    review_iterations: int
    issues: Annotated[list[dict], operator.add]
    suggestions: Annotated[list[str], operator.add]
    improved_code: str
    approved: bool
    messages: Annotated[Sequence[dict], operator.add]

def create_code_review_graph(llm, checkpointer=None, max_iterations: int = 3):
    """Create a code review agent with iterative improvement."""

    async def analyze_code(state: CodeReviewState) -> dict:
        """Analyze code for issues and patterns."""
        response = await llm.ainvoke([
            {"role": "system", "content": f"You are an expert {state['language']} code reviewer. Identify bugs, security issues, performance problems, and style violations."},
            {"role": "user", "content": f"Review this code:\n```{state['language']}\n{state['code']}\n```"}
        ])
        issues = [{"type": "review", "content": response.content, "iteration": state.get("review_iterations", 0)}]
        return {"issues": issues, "messages": [{"role": "assistant", "content": response.content}]}

    async def suggest_improvements(state: CodeReviewState) -> dict:
        """Generate improvement suggestions."""
        issues_text = "\n".join([i["content"] for i in state["issues"]])
        response = await llm.ainvoke([
            {"role": "system", "content": "Suggest specific code improvements with explanations."},
            {"role": "user", "content": f"Code:\n```{state['language']}\n{state['code']}\n```\n\nIssues found:\n{issues_text}"}
        ])
        return {"suggestions": [response.content], "messages": [{"role": "assistant", "content": response.content}]}

    async def apply_improvements(state: CodeReviewState) -> dict:
        """Apply suggested improvements to code."""
        suggestions_text = "\n".join(state["suggestions"])
        response = await llm.ainvoke([
            {"role": "system", "content": f"Apply the suggested improvements to the code. Return only the improved {state['language']} code."},
            {"role": "user", "content": f"Original code:\n```{state['language']}\n{state['code']}\n```\n\nSuggestions:\n{suggestions_text}"}
        ])
        return {
            "improved_code": response.content,
            "review_iterations": state.get("review_iterations", 0) + 1,
            "messages": [{"role": "assistant", "content": response.content}]
        }

    def should_iterate(state: CodeReviewState) -> str:
        """Decide if another review iteration is needed."""
        iterations = state.get("review_iterations", 0)
        if iterations >= max_iterations:
            return "done"
        recent_issues = [i for i in state["issues"] if i.get("iteration") == iterations - 1]
        if not recent_issues or "no issues" in str(recent_issues).lower():
            return "done"
        return "iterate"

    graph = StateGraph(CodeReviewState)
    graph.add_node("analyze", analyze_code)
    graph.add_node("suggest", suggest_improvements)
    graph.add_node("improve", apply_improvements)

    graph.set_entry_point("analyze")
    graph.add_edge("analyze", "suggest")
    graph.add_edge("suggest", "improve")
    graph.add_conditional_edges("improve", should_iterate, {"iterate": "analyze", "done": END})

    return graph.compile(checkpointer=checkpointer)

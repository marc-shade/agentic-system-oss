"""Self-directing autonomous task completion agent."""
from typing import TypedDict, Annotated, Sequence, Literal
from langgraph.graph import StateGraph, END
import operator

class TaskState(TypedDict):
    thread_id: str
    objective: str
    current_step: str
    completed_steps: Annotated[list[str], operator.add]
    pending_steps: list[str]
    context: dict
    result: str
    status: str
    error: str
    approved: bool
    messages: Annotated[Sequence[dict], operator.add]

def create_autonomous_task_graph(llm, tools: list = None, checkpointer=None):
    """Create a self-directing task completion agent."""

    async def plan_task(state: TaskState) -> dict:
        """Break down objective into executable steps."""
        response = await llm.ainvoke([
            {"role": "system", "content": "You are a task planner. Break down the objective into specific, actionable steps. Return steps as a numbered list."},
            {"role": "user", "content": f"Objective: {state['objective']}\nContext: {state.get('context', {})}"}
        ])
        steps = [line.strip() for line in response.content.split("\n") if line.strip() and line.strip()[0].isdigit()]
        return {
            "pending_steps": steps if steps else [response.content],
            "status": "planned",
            "messages": [{"role": "assistant", "content": response.content}]
        }

    async def execute_step(state: TaskState) -> dict:
        """Execute the current step."""
        if not state.get("pending_steps"):
            return {"status": "completed", "current_step": ""}

        current = state["pending_steps"][0]
        remaining = state["pending_steps"][1:]

        response = await llm.ainvoke([
            {"role": "system", "content": "Execute this step and describe the result. If you cannot execute it, explain why."},
            {"role": "user", "content": f"Step to execute: {current}\nObjective: {state['objective']}\nCompleted: {state.get('completed_steps', [])}"}
        ])

        return {
            "current_step": current,
            "pending_steps": remaining,
            "completed_steps": [f"{current}: {response.content}"],
            "status": "executing",
            "messages": [{"role": "assistant", "content": response.content}]
        }

    async def evaluate_progress(state: TaskState) -> dict:
        """Evaluate if the objective is being met."""
        completed = "\n".join(state.get("completed_steps", []))
        response = await llm.ainvoke([
            {"role": "system", "content": "Evaluate progress toward the objective. Return: 'continue', 'replan', or 'complete'."},
            {"role": "user", "content": f"Objective: {state['objective']}\nCompleted steps:\n{completed}\nRemaining: {state.get('pending_steps', [])}"}
        ])
        return {"status": response.content.strip().lower(), "messages": [{"role": "assistant", "content": response.content}]}

    async def synthesize_result(state: TaskState) -> dict:
        """Synthesize final result from completed steps."""
        completed = "\n".join(state.get("completed_steps", []))
        response = await llm.ainvoke([
            {"role": "system", "content": "Synthesize the results of all completed steps into a final deliverable."},
            {"role": "user", "content": f"Objective: {state['objective']}\nCompleted steps:\n{completed}"}
        ])
        return {"result": response.content, "status": "completed", "messages": [{"role": "assistant", "content": response.content}]}

    async def handle_error(state: TaskState) -> dict:
        """Handle errors during execution."""
        return {"status": "error", "error": state.get("error", "Unknown error")}

    def route_progress(state: TaskState) -> Literal["execute", "replan", "synthesize", "error"]:
        """Route based on progress evaluation."""
        status = state.get("status", "").lower()
        if "error" in status:
            return "error"
        if "replan" in status:
            return "replan"
        if "complete" in status or not state.get("pending_steps"):
            return "synthesize"
        return "execute"

    graph = StateGraph(TaskState)
    graph.add_node("plan", plan_task)
    graph.add_node("execute", execute_step)
    graph.add_node("evaluate", evaluate_progress)
    graph.add_node("synthesize", synthesize_result)
    graph.add_node("error", handle_error)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "execute")
    graph.add_edge("execute", "evaluate")
    graph.add_conditional_edges("evaluate", route_progress, {
        "execute": "execute",
        "replan": "plan",
        "synthesize": "synthesize",
        "error": "error"
    })
    graph.add_edge("synthesize", END)
    graph.add_edge("error", END)

    return graph.compile(checkpointer=checkpointer)

"""
Planner Agent - Decomposes tasks into executable steps.

Key responsibilities:
- Parse natural language requests
- Create numbered pseudo-code plans
- Identify required tools per step
- Handle replanning on failures
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


PLANNER_SYSTEM_PROMPT = """You are the Planner Agent for Project Prometheus, an autonomous AI system.

Your role: Decompose complex tasks into 3-15 numbered executable steps.

OUTPUT FORMAT (JSON):
{
  "analysis": "Brief analysis of the task",
  "steps": [
    {
      "number": 1,
      "description": "Clear action description",
      "tools": ["tool1", "tool2"],
      "expected_outcome": "What success looks like"
    }
  ],
  "estimated_complexity": "low|medium|high",
  "requires_user_input": false
}

RULES:
1. Each step should be achievable with 1-3 tool calls
2. Include expected tools for each step (from available tools list)
3. Order steps by dependency (prerequisites first)
4. Be specific but allow flexibility
5. If task is unclear, first step should be clarification

AVAILABLE TOOLS:
- File: read, write, edit, glob, grep
- Shell: bash (on Linux sandbox)
- Browser: navigate, view, click, input, screenshot
- Search: web_search, memory_search
- Voice: speak, listen
- Message: notify_user, ask_user

EXAMPLES:

Task: "Build a simple website"
{
  "analysis": "User wants a website. Need to clarify requirements, create files, test.",
  "steps": [
    {"number": 1, "description": "Clarify website purpose and requirements", "tools": ["ask_user"], "expected_outcome": "Clear understanding of site purpose"},
    {"number": 2, "description": "Create project directory and HTML file", "tools": ["bash", "write"], "expected_outcome": "index.html created"},
    {"number": 3, "description": "Add CSS styling", "tools": ["write"], "expected_outcome": "styles.css created and linked"},
    {"number": 4, "description": "Start local server and test", "tools": ["bash", "browser_navigate"], "expected_outcome": "Site loads correctly"},
    {"number": 5, "description": "Take screenshot and notify user", "tools": ["browser_screenshot", "notify_user"], "expected_outcome": "User sees result"}
  ],
  "estimated_complexity": "low",
  "requires_user_input": true
}
"""

REPLAN_PROMPT = """The previous plan failed at step {step_number}.

Original task: {task}
Failed step: {failed_step}
Error: {error}

Current plan status:
{plan_status}

Create an updated plan that:
1. Addresses the error
2. Provides alternative approaches
3. May add recovery steps before retry

Return JSON with "new_steps" array to insert after the failed step.
"""


@dataclass
class Plan:
    """Execution plan with steps."""
    analysis: str
    steps: list[dict]
    complexity: str
    requires_input: bool
    current_step: int = 0

    def is_complete(self) -> bool:
        return self.current_step >= len(self.steps)

    def advance(self) -> None:
        self.current_step += 1

    def get_current(self) -> Optional[dict]:
        if self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None


class PlannerAgent:
    """
    Decomposes complex tasks into executable steps.

    Uses LLM to analyze requests and create structured plans
    with tool assignments and expected outcomes.
    """

    def __init__(self, llm_client=None):
        """
        Initialize planner.

        Args:
            llm_client: LLM client for plan generation.
                       If None, uses default Claude client.
        """
        self.llm_client = llm_client
        self.system_prompt = PLANNER_SYSTEM_PROMPT

    async def create_plan(self, request: str, context: dict = None) -> Optional[Plan]:
        """
        Create execution plan for a task.

        Args:
            request: Natural language task description
            context: Optional context (files, history, preferences)

        Returns:
            Plan object or None if planning failed
        """
        logger.info(f"Creating plan for: {request[:50]}...")

        # Build user message
        user_message = f"Create an execution plan for this task:\n\n{request}"

        if context:
            user_message += f"\n\nContext:\n{json.dumps(context, indent=2)}"

        try:
            # Call LLM
            response = await self._call_llm(user_message)

            # Parse JSON response
            plan_data = self._parse_response(response)

            if not plan_data or "steps" not in plan_data:
                logger.error("Failed to parse plan response")
                return None

            return Plan(
                analysis=plan_data.get("analysis", ""),
                steps=plan_data["steps"],
                complexity=plan_data.get("estimated_complexity", "medium"),
                requires_input=plan_data.get("requires_user_input", False)
            )

        except Exception as e:
            logger.exception(f"Planning failed: {e}")
            return None

    async def replan(
        self,
        original_task: str,
        failed_step: dict,
        error: str,
        plan_status: str
    ) -> Optional[dict]:
        """
        Create recovery plan after failure.

        Args:
            original_task: The original task description
            failed_step: The step that failed
            error: Error message
            plan_status: Current plan status (from todo.md)

        Returns:
            Dict with 'new_steps' to insert, or None
        """
        logger.info(f"Replanning after step {failed_step.get('number')} failed")

        prompt = REPLAN_PROMPT.format(
            step_number=failed_step.get("number", "?"),
            task=original_task,
            failed_step=json.dumps(failed_step),
            error=error,
            plan_status=plan_status
        )

        try:
            response = await self._call_llm(prompt)
            return self._parse_response(response)
        except Exception as e:
            logger.exception(f"Replanning failed: {e}")
            return None

    async def _call_llm(self, user_message: str) -> str:
        """Call LLM with system and user message."""
        if self.llm_client:
            return await self.llm_client.generate(
                system=self.system_prompt,
                user=user_message
            )
        else:
            # Fallback: Return simple plan structure
            # In production, this would use anthropic client
            logger.warning("No LLM client configured, returning default plan")
            return json.dumps({
                "analysis": "Default plan (no LLM configured)",
                "steps": [
                    {"number": 1, "description": "Analyze request", "tools": ["read"], "expected_outcome": "Understanding gained"},
                    {"number": 2, "description": "Execute action", "tools": ["write"], "expected_outcome": "Action completed"},
                    {"number": 3, "description": "Verify result", "tools": ["read"], "expected_outcome": "Result verified"}
                ],
                "estimated_complexity": "medium",
                "requires_user_input": False
            })

    def _parse_response(self, response: str) -> Optional[dict]:
        """Parse JSON from LLM response."""
        try:
            # Try to find JSON in response
            if "```json" in response:
                start = response.index("```json") + 7
                end = response.index("```", start)
                response = response[start:end]
            elif "```" in response:
                start = response.index("```") + 3
                end = response.index("```", start)
                response = response[start:end]

            return json.loads(response.strip())
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse JSON: {e}")
            return None

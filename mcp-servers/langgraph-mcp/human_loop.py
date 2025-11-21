"""Human-in-the-loop workflows with Arduino Surface integration."""
import asyncio
import httpx
from typing import Any, Optional, Callable
from enum import Enum
import persistence

class ApprovalType(str, Enum):
    CONFIRM = "confirm"
    REVIEW = "review"
    CHOICE = "choice"
    INPUT = "input"

ARDUINO_SURFACE_URL = "http://localhost:8765"

async def request_arduino_approval(message: str, timeout: int = 300) -> bool:
    """Request physical approval via Arduino Surface MCP."""
    try:
        async with httpx.AsyncClient() as client:
            # Display message on LCD
            await client.post(f"{ARDUINO_SURFACE_URL}/display", json={"message": message[:32]})
            # Set LED to yellow (waiting)
            await client.post(f"{ARDUINO_SURFACE_URL}/led", json={"r": 255, "g": 255, "b": 0})
            # Beep to alert
            await client.post(f"{ARDUINO_SURFACE_URL}/beep", json={"frequency": 1000, "duration": 200})

            # Wait for button press
            response = await client.post(
                f"{ARDUINO_SURFACE_URL}/wait_button",
                json={"timeout": timeout},
                timeout=timeout + 5
            )
            result = response.json()

            # Set LED based on result
            if result.get("button") == "green":
                await client.post(f"{ARDUINO_SURFACE_URL}/led", json={"r": 0, "g": 255, "b": 0})
                return True
            else:
                await client.post(f"{ARDUINO_SURFACE_URL}/led", json={"r": 255, "g": 0, "b": 0})
                return False
    except Exception as e:
        # Fallback to database approval if Arduino unavailable
        return None

async def create_human_approval(
    thread_id: str,
    approval_type: ApprovalType,
    title: str,
    description: str,
    options: Optional[list[str]] = None,
    use_arduino: bool = True
) -> dict:
    """Create a human approval request with optional Arduino integration."""
    request_data = {
        "title": title,
        "description": description,
        "options": options or ["approve", "reject"],
        "use_arduino": use_arduino
    }

    approval_id = await persistence.create_approval_request(
        thread_id, approval_type.value, request_data
    )

    if use_arduino:
        arduino_result = await request_arduino_approval(f"{title}\n{description[:16]}")
        if arduino_result is not None:
            await persistence.resolve_approval(approval_id, arduino_result, {"source": "arduino"})
            return {"id": approval_id, "status": "approved" if arduino_result else "rejected", "source": "arduino"}

    return {"id": approval_id, "status": "pending", "source": "database"}

async def wait_for_approval(approval_id: int, timeout: int = 3600, poll_interval: int = 5) -> dict:
    """Wait for a human approval to be resolved."""
    import aiosqlite
    import json

    start_time = asyncio.get_event_loop().time()

    while True:
        async with aiosqlite.connect(persistence.DB_PATH) as db:
            cursor = await db.execute(
                "SELECT status, response_data FROM human_approvals WHERE id=?",
                (approval_id,)
            )
            row = await cursor.fetchone()

            if row and row[0] != 'pending':
                return {"status": row[0], "response": json.loads(row[1]) if row[1] else {}}

        if asyncio.get_event_loop().time() - start_time > timeout:
            return {"status": "timeout", "response": {}}

        await asyncio.sleep(poll_interval)

def interrupt_node(state: dict, message: str) -> dict:
    """Node that interrupts graph execution for human review."""
    state["__interrupt__"] = {
        "message": message,
        "state_snapshot": {k: v for k, v in state.items() if not k.startswith("__")}
    }
    return state

class HumanApprovalNode:
    """Reusable node for human approval in LangGraph."""

    def __init__(self, approval_type: ApprovalType, title: str, description_template: str, use_arduino: bool = True):
        self.approval_type = approval_type
        self.title = title
        self.description_template = description_template
        self.use_arduino = use_arduino

    async def __call__(self, state: dict) -> dict:
        description = self.description_template.format(**state)

        result = await create_human_approval(
            thread_id=state.get("thread_id", "default"),
            approval_type=self.approval_type,
            title=self.title,
            description=description,
            use_arduino=self.use_arduino
        )

        if result["status"] == "pending":
            approval_result = await wait_for_approval(result["id"])
            state["approval_result"] = approval_result
        else:
            state["approval_result"] = result

        state["approved"] = state["approval_result"]["status"] == "approved"
        return state

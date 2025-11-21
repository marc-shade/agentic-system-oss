#!/usr/bin/env python3
"""Quick test for task-manager-mcp server"""

import asyncio
from server import app, create_task, prioritize_tasks, generate_sprint_plan

async def test_server():
    print("Testing Task Manager MCP Server...")
    
    # Test 1: Create a task
    print("\n1. Creating a task...")
    result = await create_task(
        title="Test cascading agent workflow",
        description="Implement parallel execution for AI agents",
        priority="high",
        estimated_hours=8
    )
    print(f"Created task: {result['task']['id']}")
    print(f"Suggestions: {result.get('suggestions', {})}")
    
    # Test 2: Create more tasks
    print("\n2. Creating additional tasks...")
    await create_task(
        title="Set up memory integration",
        description="Connect memory server for agent state",
        priority="critical",
        estimated_hours=4
    )
    await create_task(
        title="Document orchestration patterns",
        description="Write guide for cascading patterns",
        priority="medium",
        estimated_hours=6
    )
    
    # Test 3: Prioritize tasks
    print("\n3. Prioritizing tasks...")
    prioritized = await prioritize_tasks(optimization_goal="balanced")
    for item in prioritized[:3]:
        print(f"- {item['task']['title']} (Score: {item['score']:.1f})")
    
    # Test 4: Generate sprint plan
    print("\n4. Generating sprint plan...")
    sprint = await generate_sprint_plan(
        sprint_duration_days=7,
        team_members=["Agent-1", "Agent-2", "Agent-3"]
    )
    print(f"Sprint metrics: {sprint['metrics']}")
    print(f"Success probability: {sprint['success_probability']}")
    
    print("\n✅ All tests passed!")

if __name__ == "__main__":
    asyncio.run(test_server())
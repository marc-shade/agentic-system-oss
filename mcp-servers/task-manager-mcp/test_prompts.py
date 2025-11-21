#!/usr/bin/env python3
"""
Test script for Task Manager MCP Prompts functionality
"""

import asyncio
import json
from prompts import (
    get_available_prompts, generate_workflow_prompt, get_parameter_completions,
    validate_prompt_parameters, get_prompt_categories
)

async def test_workflow_prompts():
    """Test all workflow prompt functionality"""
    
    print("🎯 Testing Task Manager MCP Prompts")
    print("=" * 60)
    
    # Test 1: Get available prompts
    print("\n1️⃣ Testing get_available_prompts()")
    prompts = get_available_prompts()
    print(f"Available prompts: {len(prompts)}")
    for name, config in prompts.items():
        print(f"  • {name}: {config['description']}")
    
    # Test 2: Get prompt categories
    print("\n2️⃣ Testing get_prompt_categories()")
    categories = get_prompt_categories()
    for cat_name, cat_info in categories.items():
        print(f"  • {cat_name}: {cat_info['name']} ({len(cat_info['prompts'])} prompts)")
    
    # Test 3: Parameter completions
    print("\n3️⃣ Testing get_parameter_completions()")
    completions = get_parameter_completions("sprint_planning", "optimization_goal")
    print(f"Optimization goal completions: {completions}")
    
    completions = get_parameter_completions("task_prioritization", "priority_framework")
    print(f"Priority framework completions: {completions}")
    
    # Test 4: Parameter validation
    print("\n4️⃣ Testing validate_prompt_parameters()")
    
    # Valid parameters
    valid_params = {
        "sprint_duration": "2_weeks",
        "team_capacity": {"frontend": 2, "backend": 2},
        "priority_criteria": ["deadline", "impact"],
        "optimization_goal": "quality"
    }
    validation = validate_prompt_parameters("sprint_planning", valid_params)
    print(f"Valid parameters test: {validation}")
    
    # Invalid parameters (missing required)
    invalid_params = {"sprint_duration": "2_weeks"}
    validation = validate_prompt_parameters("sprint_planning", invalid_params)
    print(f"Invalid parameters test: {validation}")
    
    # Test 5: Generate sprint planning template
    print("\n5️⃣ Testing generate_workflow_prompt() - Sprint Planning")
    sprint_params = {
        "sprint_duration": "2_weeks",
        "team_size": 6,
        "sprint_goal": "Implement user authentication system",
        "total_capacity": 480,
        "team_capacity_breakdown": "Frontend: 2 devs (160h), Backend: 2 devs (160h), QA: 1 tester (80h), DevOps: 1 engineer (80h)",
        "priority_criteria": ["business_value", "deadline", "dependencies"],
        "optimization_goal": "quality",
        "buffer_percentage": 20,
        "available_points": 45,
        "capacity_recommendation": "Conservative plan with good buffer",
        "identified_risks": ["New authentication library", "Holiday schedule"],
        "sprint_objectives": "• Deliver working JWT authentication\n• Complete user registration flow\n• Implement password reset functionality",
        "completion_target": 85,
        "quality_criteria": ["Code review required", "Test coverage >80%", "Security audit"],
        "definition_of_done": "Tested, reviewed, documented, deployed to staging",
        "risk_mitigation_plan": "• Spike on auth library in first 2 days\n• Plan for reduced capacity during holidays",
        "retrospective_areas": ["Team communication", "Technical debt", "Process efficiency"]
    }
    
    result = await generate_workflow_prompt("sprint_planning", sprint_params)
    if "error" not in result:
        print("✅ Sprint planning template generated successfully!")
        print("\nTemplate preview (first 500 chars):")
        print(result["prompt"][:500] + "...")
        print(f"\nNext steps: {len(result['next_steps'])} items")
    else:
        print(f"❌ Error: {result['error']}")
    
    # Test 6: Generate task prioritization template
    print("\n6️⃣ Testing generate_workflow_prompt() - Task Prioritization")
    priority_params = {
        "analysis_date": "2025-08-02",
        "priority_framework": "RICE",
        "scope_description": "quarterly_roadmap",
        "business_impact_weight": 30,
        "urgency_weight": 25,
        "effort_weight": 25,
        "dependency_weight": 10,
        "strategic_weight": 10,
        "priority_matrix": "High Impact/Low Effort: 3 tasks\nHigh Impact/High Effort: 5 tasks\nLow Impact/Low Effort: 8 tasks\nLow Impact/High Effort: 2 tasks",
        "prioritized_task_list": "1. User Authentication (Score: 8.5)\n2. API Gateway (Score: 8.2)\n3. Dashboard Analytics (Score: 7.8)",
        "quick_wins": "• Fix login redirect bug (2h)\n• Update user profile UI (4h)\n• Add password strength indicator (3h)",
        "strategic_initiatives": "• Microservices migration (3 months)\n• Real-time notifications system (6 weeks)",
        "dependency_analysis": "Authentication blocks 5 other features\nDatabase migration affects all backend work",
        "resource_recommendations": "Allocate 60% to high-priority features\nReserve 20% for technical debt\n20% buffer for urgent fixes",
        "impact_effort_matrix": "[Visual matrix would be generated here]",
        "recommended_next_actions": "• Start authentication work immediately\n• Plan database migration for next quarter\n• Schedule technical debt sprint"
    }
    
    result = await generate_workflow_prompt("task_prioritization", priority_params)
    if "error" not in result:
        print("✅ Task prioritization template generated successfully!")
        print("\nTemplate preview (first 500 chars):")
        print(result["prompt"][:500] + "...")
    else:
        print(f"❌ Error: {result['error']}")
    
    # Test 7: Generate bottleneck analysis template
    print("\n7️⃣ Testing generate_workflow_prompt() - Bottleneck Analysis")
    bottleneck_params = {
        "analysis_date": "2025-08-02",
        "analysis_period": "last_sprint",
        "workflow_scope": "development",
        "identified_bottlenecks": "• Code review process taking 2+ days\n• Database performance on reports\n• Deployment pipeline failures",
        "cycle_time_impact": "+40% average cycle time",
        "throughput_impact": "-25% story completion rate",
        "utilization_impact": "65% productive time (target: 80%)",
        "quality_impact": "15% increase in bug reports",
        "root_cause_analysis": "Limited review capacity\nLegacy database queries\nUnstable test environment",
        "process_bottlenecks": "Manual code review scheduling",
        "resource_bottlenecks": "Only 2 senior developers for reviews",
        "dependency_bottlenecks": "Shared database for multiple teams",
        "knowledge_bottlenecks": "Complex domain knowledge concentration",
        "recommended_solutions": "1. Implement review rotation\n2. Optimize database queries\n3. Stabilize CI/CD pipeline",
        "solution_priority_matrix": "High Impact/Low Effort: Review automation\nHigh Impact/High Effort: Database optimization",
        "implementation_roadmap": "Week 1: Review process changes\nWeek 2-3: Database optimization\nWeek 4: Pipeline stabilization",
        "velocity_improvement": "+30% expected improvement",
        "cycle_time_reduction": "2.5 days average (from 4.5 days)",
        "quality_improvement": "Target: <5% defect rate",
        "monitoring_plan": "Daily throughput metrics\nWeekly bottleneck reviews\nMonthly process assessment"
    }
    
    result = await generate_workflow_prompt("bottleneck_analysis", bottleneck_params)
    if "error" not in result:
        print("✅ Bottleneck analysis template generated successfully!")
        print("\nTemplate preview (first 500 chars):")
        print(result["prompt"][:500] + "...")
    else:
        print(f"❌ Error: {result['error']}")
    
    # Test 8: Test with context for AI analysis
    print("\n8️⃣ Testing AI-enhanced generation with context")
    sample_tasks = [
        {
            "id": "TASK-001",
            "title": "Implement JWT authentication",
            "priority": "high",
            "estimated_hours": 16,
            "status": "todo",
            "dependencies": []
        },
        {
            "id": "TASK-002", 
            "title": "Create user dashboard",
            "priority": "medium",
            "estimated_hours": 24,
            "status": "in_progress",
            "dependencies": ["TASK-001"]
        },
        {
            "id": "TASK-003",
            "title": "Fix login bug",
            "priority": "critical",
            "estimated_hours": 4,
            "status": "blocked",
            "dependencies": []
        }
    ]
    
    context = {
        "tasks": sample_tasks,
        "team_data": {
            "members": ["Alice", "Bob", "Charlie"],
            "size": 3
        }
    }
    
    simple_params = {
        "sprint_duration": "2_weeks",
        "team_capacity": {"Alice": 40, "Bob": 40, "Charlie": 40},
        "priority_criteria": ["deadline", "impact"],
        "optimization_goal": "speed",
        "team_size": 3,
        "sprint_goal": "Fix critical issues and start new features",
        "buffer_percentage": 15
    }
    
    result = await generate_workflow_prompt("sprint_planning", simple_params, context)
    if "error" not in result:
        print("✅ AI-enhanced template generated successfully!")
        print(f"AI insights included: {bool(result.get('ai_insights'))}")
        print(f"Next steps: {len(result.get('next_steps', []))}")
    else:
        print(f"❌ Error: {result['error']}")
    
    print("\n" + "=" * 60)
    print("🎯 All tests completed!")

if __name__ == "__main__":
    asyncio.run(test_workflow_prompts())
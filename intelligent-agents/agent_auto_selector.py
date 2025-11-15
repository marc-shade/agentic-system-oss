#!/usr/bin/env python3
"""
Agent Auto-Selection Framework

Intelligently maps tasks to optimal specialized agents based on:
- Task type and complexity
- Required skills and capabilities
- Historical performance data
- Resource availability
- Parallel execution opportunities

Enables automatic agent recommendations and orchestration.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Volumes/SSDRAID0/agentic-system/logs/agent_selector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('agent-selector')

class AgentCapability:
    """Represents an agent's capabilities and specializations"""

    def __init__(self, name: str, capabilities: List[str], performance_score: float = 0.5):
        self.name = name
        self.capabilities = capabilities
        self.performance_score = performance_score  # 0.0 to 1.0
        self.task_count = 0
        self.success_count = 0

    def matches_requirement(self, requirement: str) -> bool:
        """Check if agent has capability for requirement"""
        requirement_lower = requirement.lower()
        return any(cap.lower() in requirement_lower or requirement_lower in cap.lower()
                   for cap in self.capabilities)

    def calculate_match_score(self, requirements: List[str]) -> float:
        """Calculate match score (0.0 to 1.0) for given requirements"""
        if not requirements:
            return 0.0

        matches = sum(1 for req in requirements if self.matches_requirement(req))
        return (matches / len(requirements)) * self.performance_score

    def update_performance(self, success: bool):
        """Update performance metrics after task completion"""
        self.task_count += 1
        if success:
            self.success_count += 1

        # Calculate new performance score (exponential moving average)
        success_rate = self.success_count / self.task_count
        self.performance_score = 0.7 * self.performance_score + 0.3 * success_rate

class AgentAutoSelector:
    """Automatic agent selection and orchestration"""

    def __init__(self):
        self.agents = self._initialize_agent_catalog()
        self.selection_history = []
        self.history_file = Path('/Volumes/SSDRAID0/agentic-system/databases/agent_selection_history.json')

    def _initialize_agent_catalog(self) -> Dict[str, AgentCapability]:
        """Initialize catalog of available agents with their capabilities"""
        return {
            # Research & Analysis
            'research-coordinator': AgentCapability(
                'research-coordinator',
                ['research', 'analysis', 'investigation', 'data gathering', 'literature review']
            ),

            # Development Agents
            'Swarm Coder': AgentCapability(
                'Swarm Coder',
                ['coding', 'implementation', 'development', 'programming', 'refactoring', 'bug fixing']
            ),
            'Frontend Engineer': AgentCapability(
                'Frontend Engineer',
                ['frontend', 'UI', 'UX', 'React', 'TypeScript', 'CSS', 'HTML', 'responsive design']
            ),
            'Backend Engineer': AgentCapability(
                'Backend Engineer',
                ['backend', 'API', 'database', 'server', 'microservices', 'authentication']
            ),
            'System Architect': AgentCapability(
                'System Architect',
                ['architecture', 'system design', 'scalability', 'design patterns', 'infrastructure']
            ),

            # Testing & Quality
            'Swarm Tester': AgentCapability(
                'Swarm Tester',
                ['testing', 'QA', 'validation', 'verification', 'test automation', 'unit tests']
            ),
            'web-testing-agent': AgentCapability(
                'web-testing-agent',
                ['web testing', 'browser automation', 'UI testing', 'performance testing', 'E2E testing']
            ),
            'Swarm Guardian': AgentCapability(
                'Swarm Guardian',
                ['security', 'vulnerability', 'threat assessment', 'penetration testing', 'compliance']
            ),

            # Code Quality & Review
            'Swarm Reviewer': AgentCapability(
                'Swarm Reviewer',
                ['code review', 'audit', 'quality check', 'best practices', 'code standards']
            ),
            'Code Refactorer': AgentCapability(
                'Code Refactorer',
                ['refactoring', 'code quality', 'technical debt', 'code cleanup', 'optimization']
            ),

            # Optimization & Performance
            'Swarm Optimizer': AgentCapability(
                'Swarm Optimizer',
                ['optimization', 'performance', 'efficiency', 'speed', 'resource usage']
            ),
            'Performance Optimizer': AgentCapability(
                'Performance Optimizer',
                ['performance analysis', 'bottlenecks', 'profiling', 'benchmarking', 'tuning']
            ),

            # Documentation & Communication
            'Swarm Documenter': AgentCapability(
                'Swarm Documenter',
                ['documentation', 'writing', 'technical writing', 'API docs', 'README']
            ),

            # Operations & Deployment
            'Swarm DevOps': AgentCapability(
                'Swarm DevOps',
                ['deployment', 'CI/CD', 'infrastructure', 'monitoring', 'DevOps', 'Docker']
            ),

            # Specialized
            'debugger': AgentCapability(
                'debugger',
                ['debugging', 'error resolution', 'troubleshooting', 'root cause analysis']
            ),
            'MCP Builder': AgentCapability(
                'MCP Builder',
                ['MCP servers', 'protocol', 'integration', 'API design', 'TypeScript']
            ),

            # General Purpose
            'general-purpose': AgentCapability(
                'general-purpose',
                ['general tasks', 'miscellaneous', 'fallback', 'unspecified']
            )
        }

    def analyze_task_requirements(self, task_title: str, task_description: str) -> Dict:
        """
        Analyze task to extract requirements and complexity

        Returns:
            Dictionary with requirements, complexity, parallel_opportunities
        """
        combined_text = f"{task_title} {task_description}".lower()

        # Extract requirements based on keywords
        requirements = []

        # Development keywords
        if any(word in combined_text for word in ['implement', 'develop', 'code', 'build', 'create']):
            requirements.append('implementation')

        if any(word in combined_text for word in ['frontend', 'ui', 'ux', 'react', 'component']):
            requirements.append('frontend development')

        if any(word in combined_text for word in ['backend', 'api', 'database', 'server']):
            requirements.append('backend development')

        if any(word in combined_text for word in ['test', 'testing', 'qa', 'verify']):
            requirements.append('testing')

        if any(word in combined_text for word in ['web test', 'browser', 'e2e', 'ui test']):
            requirements.append('web testing')

        if any(word in combined_text for word in ['document', 'documentation', 'readme', 'guide']):
            requirements.append('documentation')

        if any(word in combined_text for word in ['review', 'audit', 'check quality']):
            requirements.append('code review')

        if any(word in combined_text for word in ['optimize', 'performance', 'speed up']):
            requirements.append('optimization')

        if any(word in combined_text for word in ['security', 'vulnerability', 'secure']):
            requirements.append('security')

        if any(word in combined_text for word in ['research', 'analyze', 'investigate']):
            requirements.append('research')

        if any(word in combined_text for word in ['deploy', 'ci/cd', 'infrastructure']):
            requirements.append('deployment')

        if any(word in combined_text for word in ['debug', 'fix', 'error', 'bug']):
            requirements.append('debugging')

        if any(word in combined_text for word in ['architecture', 'design', 'scalable']):
            requirements.append('architecture')

        # Determine complexity based on task description length and keywords
        complexity_indicators = len(requirements)
        word_count = len(task_description.split())

        if complexity_indicators >= 3 or word_count > 100:
            complexity = 'high'
        elif complexity_indicators >= 2 or word_count > 50:
            complexity = 'medium'
        else:
            complexity = 'low'

        # Identify parallel execution opportunities
        parallel_opportunities = []
        if 'implementation' in requirements and 'testing' in requirements:
            parallel_opportunities.append('parallel_dev_test')

        if 'frontend development' in requirements and 'backend development' in requirements:
            parallel_opportunities.append('parallel_frontend_backend')

        if 'code review' in requirements and 'testing' in requirements:
            parallel_opportunities.append('parallel_review_test')

        return {
            'requirements': requirements,
            'complexity': complexity,
            'parallel_opportunities': parallel_opportunities
        }

    def select_agents(self, task_title: str, task_description: str, max_agents: int = 3) -> List[Tuple[str, float]]:
        """
        Select best agent(s) for task

        Args:
            task_title: Task title
            task_description: Task description
            max_agents: Maximum number of agents to select

        Returns:
            List of (agent_name, match_score) tuples, sorted by score
        """
        logger.info(f"Selecting agents for task: {task_title}")

        # Analyze task requirements
        analysis = self.analyze_task_requirements(task_title, task_description)
        requirements = analysis['requirements']

        if not requirements:
            # No specific requirements, use general purpose
            logger.warning("No specific requirements found, using general-purpose agent")
            return [('general-purpose', 0.5)]

        # Calculate match scores for all agents
        agent_scores = []
        for agent_name, agent in self.agents.items():
            score = agent.calculate_match_score(requirements)
            if score > 0.0:
                agent_scores.append((agent_name, score))

        # Sort by score descending
        agent_scores.sort(key=lambda x: x[1], reverse=True)

        # Return top N agents
        selected = agent_scores[:max_agents]

        logger.info(f"Selected {len(selected)} agents:")
        for agent_name, score in selected:
            logger.info(f"  - {agent_name}: {score:.2f}")

        # Record selection
        self.selection_history.append({
            'timestamp': datetime.now().isoformat(),
            'task_title': task_title,
            'requirements': requirements,
            'complexity': analysis['complexity'],
            'selected_agents': [{'name': name, 'score': score} for name, score in selected]
        })

        return selected

    def recommend_workflow(self, task_title: str, task_description: str) -> Dict:
        """
        Recommend complete workflow with agent assignments

        Returns:
            Workflow dictionary with phases, agents, and execution strategy
        """
        logger.info(f"Recommending workflow for: {task_title}")

        analysis = self.analyze_task_requirements(task_title, task_description)
        requirements = analysis['requirements']
        complexity = analysis['complexity']
        parallel_opps = analysis['parallel_opportunities']

        workflow = {
            'task': task_title,
            'complexity': complexity,
            'phases': [],
            'execution_strategy': 'sequential'  # or 'parallel'
        }

        # Build workflow phases based on requirements
        if 'research' in requirements:
            workflow['phases'].append({
                'phase': 'Research & Analysis',
                'agents': ['research-coordinator'],
                'duration_estimate': '30-60 min'
            })

        if 'architecture' in requirements:
            workflow['phases'].append({
                'phase': 'System Design',
                'agents': ['System Architect'],
                'duration_estimate': '1-2 hours'
            })

        if 'frontend development' in requirements and 'backend development' in requirements:
            # Parallel development
            workflow['phases'].append({
                'phase': 'Parallel Development',
                'agents': ['Frontend Engineer', 'Backend Engineer'],
                'duration_estimate': '2-4 hours',
                'parallel': True
            })
            workflow['execution_strategy'] = 'parallel'
        else:
            if 'frontend development' in requirements:
                workflow['phases'].append({
                    'phase': 'Frontend Development',
                    'agents': ['Frontend Engineer'],
                    'duration_estimate': '2-3 hours'
                })
            if 'backend development' in requirements:
                workflow['phases'].append({
                    'phase': 'Backend Development',
                    'agents': ['Backend Engineer'],
                    'duration_estimate': '2-3 hours'
                })
            if 'implementation' in requirements and not ('frontend development' in requirements or 'backend development' in requirements):
                workflow['phases'].append({
                    'phase': 'Implementation',
                    'agents': ['Swarm Coder'],
                    'duration_estimate': '1-2 hours'
                })

        if 'testing' in requirements and 'web testing' in requirements:
            workflow['phases'].append({
                'phase': 'Testing',
                'agents': ['Swarm Tester', 'web-testing-agent'],
                'duration_estimate': '1-2 hours',
                'parallel': True
            })
        elif 'testing' in requirements:
            workflow['phases'].append({
                'phase': 'Testing',
                'agents': ['Swarm Tester'],
                'duration_estimate': '30-60 min'
            })
        elif 'web testing' in requirements:
            workflow['phases'].append({
                'phase': 'Web Testing',
                'agents': ['web-testing-agent'],
                'duration_estimate': '30-60 min'
            })

        if 'code review' in requirements:
            workflow['phases'].append({
                'phase': 'Code Review',
                'agents': ['Swarm Reviewer'],
                'duration_estimate': '30 min'
            })

        if 'security' in requirements:
            workflow['phases'].append({
                'phase': 'Security Review',
                'agents': ['Swarm Guardian'],
                'duration_estimate': '1 hour'
            })

        if 'optimization' in requirements:
            workflow['phases'].append({
                'phase': 'Optimization',
                'agents': ['Swarm Optimizer', 'Performance Optimizer'],
                'duration_estimate': '1-2 hours'
            })

        if 'documentation' in requirements:
            workflow['phases'].append({
                'phase': 'Documentation',
                'agents': ['Swarm Documenter'],
                'duration_estimate': '30-60 min'
            })

        if 'deployment' in requirements:
            workflow['phases'].append({
                'phase': 'Deployment',
                'agents': ['Swarm DevOps'],
                'duration_estimate': '30 min'
            })

        logger.info(f"Workflow: {len(workflow['phases'])} phases, {workflow['execution_strategy']} execution")
        return workflow

    def save_selection_history(self):
        """Save agent selection history to file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.selection_history, f, indent=2)
            logger.info(f"Selection history saved: {len(self.selection_history)} entries")
        except Exception as e:
            logger.error(f"Failed to save selection history: {e}")

def select_agents_for_task(task_title: str, task_description: str) -> List[str]:
    """
    Public API: Select best agents for a task

    Returns:
        List of agent names
    """
    selector = AgentAutoSelector()
    selections = selector.select_agents(task_title, task_description)
    return [name for name, score in selections]

def recommend_workflow(task_title: str, task_description: str) -> Dict:
    """
    Public API: Get complete workflow recommendation

    Returns:
        Workflow dictionary
    """
    selector = AgentAutoSelector()
    return selector.recommend_workflow(task_title, task_description)

if __name__ == "__main__":
    # Test the selector
    selector = AgentAutoSelector()

    # Test 1: Complex full-stack task
    print("\n=== Test 1: Full-Stack Feature ===")
    workflow = selector.recommend_workflow(
        "Implement user authentication system",
        "Build complete authentication with JWT tokens, including frontend login/signup forms and backend API endpoints with database integration"
    )
    print(json.dumps(workflow, indent=2))

    # Test 2: Testing task
    print("\n=== Test 2: Web Testing ===")
    agents = selector.select_agents(
        "Test production dashboard",
        "Run comprehensive web tests on production dashboard including performance tests and screenshot capture"
    )
    print(f"Selected agents: {[name for name, score in agents]}")

    # Test 3: Research task
    print("\n=== Test 3: Research ===")
    agents = selector.select_agents(
        "Research AI frameworks",
        "Investigate and compare different AI frameworks for our use case"
    )
    print(f"Selected agents: {[name for name, score in agents]}")

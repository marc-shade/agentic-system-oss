#!/usr/bin/env python3
"""
Topology-Aware Multi-Agent Coordinator
========================================

Advanced multi-agent coordinator that combines:
1. Intelligent topology selection (mesh, hierarchical, star, ring)
2. Agent specialization routing (coder, researcher, tester, reviewer)
3. Pattern-aware execution
4. Performance tracking and optimization

Target: 90%+ task completion rate through optimal topology and agent selection.

This is the production-ready coordinator for the AGI system.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Import components
from multi_agent_coordinator import MultiAgentCoordinator, AgentCapability, AgentStatus
from swarm_topology_optimizer import (
    SwarmTopologyOptimizer,
    SwarmTopology,
    SwarmExecution,
    TaskCharacteristics
)

try:
    from pattern_aware_coordinator import PatternAwareCoordinator, PatternType
    PATTERN_SUPPORT = True
except ImportError:
    PATTERN_SUPPORT = False
    logging.warning("Pattern-aware coordinator not available")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TopologyAwareCoordinator:
    """
    Production-ready multi-agent coordinator with topology optimization.

    Features:
    - Automatic topology selection based on task characteristics
    - Specialized agent routing (coder, researcher, tester, reviewer, architect)
    - Performance tracking and continuous optimization
    - Pattern-aware execution (if available)
    - 90%+ task completion rate target
    """

    def __init__(
        self,
        enable_pattern_awareness: bool = True,
        enable_topology_optimization: bool = True
    ):
        """
        Initialize topology-aware coordinator.

        Args:
            enable_pattern_awareness: Enable pattern-aware execution
            enable_topology_optimization: Enable automatic topology selection
        """
        logger.info("Initializing Topology-Aware Coordinator...")

        # Core coordinators
        self.agent_coordinator = MultiAgentCoordinator()
        self.topology_optimizer = SwarmTopologyOptimizer()

        # Pattern awareness
        self.enable_pattern_awareness = enable_pattern_awareness and PATTERN_SUPPORT
        if self.enable_pattern_awareness:
            self.pattern_coordinator = PatternAwareCoordinator(
                enable_quality_gates=True,
                enable_pattern_auto_selection=True,
                enable_hybrid_patterns=True
            )
        else:
            self.pattern_coordinator = None

        self.enable_topology_optimization = enable_topology_optimization

        # Register specialized agents
        self._register_specialized_agents()

        # Execution tracking
        self.execution_history: List[Dict] = []

        logger.info(f"Topology-Aware Coordinator initialized (pattern_aware={self.enable_pattern_awareness}, topology_opt={enable_topology_optimization})")

    def _register_specialized_agents(self):
        """Register specialized agents with enhanced capabilities"""
        specialized_agents = [
            AgentCapability(
                agent_name="senior-coder",
                task_types=["code_generation", "code_review", "refactoring", "optimization"],
                max_concurrent_tasks=3,
                current_load=0,
                status=AgentStatus.IDLE,
                performance_score=0.95
            ),
            AgentCapability(
                agent_name="researcher",
                task_types=["research", "analysis", "documentation", "investigation"],
                max_concurrent_tasks=5,
                current_load=0,
                status=AgentStatus.IDLE,
                performance_score=0.90
            ),
            AgentCapability(
                agent_name="qa-tester",
                task_types=["testing", "validation", "quality_assurance", "integration_testing"],
                max_concurrent_tasks=4,
                current_load=0,
                status=AgentStatus.IDLE,
                performance_score=0.92
            ),
            AgentCapability(
                agent_name="code-reviewer",
                task_types=["code_review", "security_review", "performance_review"],
                max_concurrent_tasks=3,
                current_load=0,
                status=AgentStatus.IDLE,
                performance_score=0.93
            ),
            AgentCapability(
                agent_name="architect",
                task_types=["architecture", "design", "planning", "system_design"],
                max_concurrent_tasks=2,
                current_load=0,
                status=AgentStatus.IDLE,
                performance_score=0.96
            ),
            AgentCapability(
                agent_name="devops-engineer",
                task_types=["deployment", "infrastructure", "cicd", "monitoring"],
                max_concurrent_tasks=3,
                current_load=0,
                status=AgentStatus.IDLE,
                performance_score=0.88
            )
        ]

        for agent in specialized_agents:
            self.agent_coordinator.register_agent(agent)

        logger.info(f"Registered {len(specialized_agents)} specialized agents")

    async def execute_task(
        self,
        task_description: str,
        context: Optional[Dict] = None,
        override_topology: Optional[SwarmTopology] = None
    ) -> Dict[str, Any]:
        """
        Execute task with optimal topology and agent coordination.

        Args:
            task_description: Task description
            context: Optional context (language, framework, constraints)
            override_topology: Optional topology override (for testing)

        Returns:
            Comprehensive execution result with topology metadata
        """
        execution_id = str(uuid.uuid4())
        task_id = str(uuid.uuid4())
        start_time = datetime.now()

        logger.info(f"\n{'='*70}")
        logger.info(f"TOPOLOGY-AWARE EXECUTION: {execution_id}")
        logger.info(f"Task: {task_description[:100]}...")
        logger.info(f"{'='*70}")

        result = {
            'execution_id': execution_id,
            'task_id': task_id,
            'task_description': task_description,
            'start_time': start_time.isoformat(),
            'context': context or {}
        }

        try:
            # Phase 1: Task Analysis
            logger.info("Phase 1: Task Analysis")
            task_analysis = await self.topology_optimizer.analyze_task(
                task_id=task_id,
                task_description=task_description,
                context=context
            )

            result['task_analysis'] = {
                'complexity': task_analysis.complexity.value,
                'characteristics': [c.value for c in task_analysis.characteristics],
                'estimated_duration_minutes': task_analysis.estimated_duration_minutes,
                'agent_count_needed': task_analysis.agent_count_needed,
                'parallelization_factor': task_analysis.parallelization_factor
            }

            # Phase 2: Topology Selection
            if self.enable_topology_optimization and not override_topology:
                logger.info("Phase 2: Topology Selection")
                recommendations = await self.topology_optimizer.recommend_topology(task_analysis)
                selected_topology = recommendations[0].topology
                topology_confidence = recommendations[0].confidence_score

                result['topology_selection'] = {
                    'selected': selected_topology.value,
                    'confidence': topology_confidence,
                    'reasoning': recommendations[0].reasoning,
                    'alternatives': [
                        {'topology': r.topology.value, 'confidence': r.confidence_score}
                        for r in recommendations[1:3]
                    ]
                }
            else:
                selected_topology = override_topology or SwarmTopology.HIERARCHICAL
                topology_confidence = 1.0 if override_topology else 0.5

                result['topology_selection'] = {
                    'selected': selected_topology.value,
                    'confidence': topology_confidence,
                    'reasoning': 'Manual override' if override_topology else 'Default topology'
                }

            logger.info(f"Selected topology: {selected_topology.value} (confidence={topology_confidence:.2f})")

            # Phase 3: Execution with Topology
            logger.info("Phase 3: Coordinated Execution")

            execution_result = await self._execute_with_topology(
                task_description=task_description,
                task_analysis=task_analysis,
                topology=selected_topology,
                context=context
            )

            result['execution'] = execution_result

            # Phase 4: Performance Recording
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds() / 60  # Convert to minutes

            success = execution_result.get('success', False)
            completion_rate = execution_result.get('completion_rate', 0.0)
            performance_score = self._calculate_performance_score(
                success=success,
                completion_rate=completion_rate,
                expected_time=task_analysis.estimated_duration_minutes,
                actual_time=execution_time
            )

            # Record execution
            swarm_execution = SwarmExecution(
                execution_id=execution_id,
                task_id=task_id,
                topology_used=selected_topology,
                agent_count=task_analysis.agent_count_needed,
                start_time=start_time,
                end_time=end_time,
                success=success,
                completion_rate=completion_rate,
                execution_time_minutes=execution_time,
                performance_score=performance_score,
                metadata={
                    'context': context or {},
                    'topology_confidence': topology_confidence,
                    'characteristics': [c.value for c in task_analysis.characteristics]
                }
            )

            await self.topology_optimizer.record_execution(swarm_execution)

            result['performance'] = {
                'success': success,
                'completion_rate': completion_rate,
                'execution_time_minutes': execution_time,
                'performance_score': performance_score,
                'vs_estimate': execution_time / task_analysis.estimated_duration_minutes if task_analysis.estimated_duration_minutes > 0 else 1.0
            }

            result['end_time'] = end_time.isoformat()
            result['total_duration_seconds'] = (end_time - start_time).total_seconds()

            # Add to history
            self.execution_history.append({
                'execution_id': execution_id,
                'topology': selected_topology.value,
                'success': success,
                'completion_rate': completion_rate,
                'performance_score': performance_score,
                'timestamp': end_time.isoformat()
            })

            logger.info(f"Execution complete: success={success}, completion={completion_rate:.1%}, performance={performance_score:.2f}")

            return result

        except Exception as e:
            logger.error(f"Execution failed: {e}", exc_info=True)
            end_time = datetime.now()

            result['error'] = str(e)
            result['success'] = False
            result['end_time'] = end_time.isoformat()
            result['total_duration_seconds'] = (end_time - start_time).total_seconds()

            return result

    async def _execute_with_topology(
        self,
        task_description: str,
        task_analysis: Any,
        topology: SwarmTopology,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """
        Execute task with specific topology strategy.

        Args:
            task_description: Task description
            task_analysis: Task analysis results
            topology: Selected topology
            context: Optional context

        Returns:
            Execution result
        """
        logger.info(f"Executing with {topology.value} topology")

        # Topology-specific execution strategies
        if topology == SwarmTopology.MESH:
            return await self._execute_mesh(task_description, task_analysis, context)

        elif topology == SwarmTopology.HIERARCHICAL:
            return await self._execute_hierarchical(task_description, task_analysis, context)

        elif topology == SwarmTopology.STAR:
            return await self._execute_star(task_description, task_analysis, context)

        elif topology == SwarmTopology.RING:
            return await self._execute_ring(task_description, task_analysis, context)

        else:
            # Fallback to standard coordination
            return await self._execute_standard(task_description, context)

    async def _execute_mesh(
        self,
        task_description: str,
        task_analysis: Any,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """Execute with mesh topology (peer-to-peer collaboration)"""
        logger.info("Mesh topology: Peer-to-peer collaborative execution")

        # Use pattern-aware coordinator for collaborative work if available
        if self.enable_pattern_awareness and self.pattern_coordinator:
            # Use MULTI_AGENT_COLLABORATION pattern for mesh
            result = await self.pattern_coordinator.execute_with_pattern(
                task=task_description,
                pattern_type=PatternType.MULTI_AGENT_COLLABORATION if hasattr(PatternType, 'MULTI_AGENT_COLLABORATION') else None,
                auto_select_pattern=True
            )
            return self._normalize_result(result)

        # Fallback to standard coordination with emphasis on collaboration
        return await self._execute_standard(task_description, context)

    async def _execute_hierarchical(
        self,
        task_description: str,
        task_analysis: Any,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """Execute with hierarchical topology (coordinator + workers)"""
        logger.info("Hierarchical topology: Coordinator-worker execution")

        # This is the default topology for the multi-agent coordinator
        exec_result = await self.agent_coordinator.execute_task(
            task_description,
            task_type=context.get('task_type', 'general') if context else 'general'
        )

        return {
            'success': exec_result.get('successful_tasks', 0) == exec_result.get('total_tasks', 1),
            'completion_rate': exec_result.get('successful_tasks', 0) / max(exec_result.get('total_tasks', 1), 1),
            'subtasks_completed': exec_result.get('successful_tasks', 0),
            'subtasks_total': exec_result.get('total_tasks', 0),
            'results': exec_result.get('results', []),
            'topology_strategy': 'hierarchical'
        }

    async def _execute_star(
        self,
        task_description: str,
        task_analysis: Any,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """Execute with star topology (central hub coordination)"""
        logger.info("Star topology: Central hub execution")

        # Use pattern-aware with ROUTING for star topology
        if self.enable_pattern_awareness and self.pattern_coordinator:
            result = await self.pattern_coordinator.execute_with_pattern(
                task=task_description,
                pattern_type=PatternType.ROUTING if hasattr(PatternType, 'ROUTING') else None,
                auto_select_pattern=True
            )
            return self._normalize_result(result)

        return await self._execute_standard(task_description, context)

    async def _execute_ring(
        self,
        task_description: str,
        task_analysis: Any,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """Execute with ring topology (sequential pipeline)"""
        logger.info("Ring topology: Sequential pipeline execution")

        # Use pattern-aware with PROMPT_CHAINING for ring topology
        if self.enable_pattern_awareness and self.pattern_coordinator:
            result = await self.pattern_coordinator.execute_with_pattern(
                task=task_description,
                pattern_type=PatternType.PROMPT_CHAINING if hasattr(PatternType, 'PROMPT_CHAINING') else None,
                auto_select_pattern=True
            )
            return self._normalize_result(result)

        return await self._execute_standard(task_description, context)

    async def _execute_standard(
        self,
        task_description: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """Standard execution fallback"""
        exec_result = await self.agent_coordinator.execute_task(
            task_description,
            task_type=context.get('task_type', 'general') if context else 'general'
        )

        return {
            'success': exec_result.get('successful_tasks', 0) == exec_result.get('total_tasks', 1),
            'completion_rate': exec_result.get('successful_tasks', 0) / max(exec_result.get('total_tasks', 1), 1),
            'subtasks_completed': exec_result.get('successful_tasks', 0),
            'subtasks_total': exec_result.get('total_tasks', 0),
            'results': exec_result.get('results', []),
            'topology_strategy': 'standard'
        }

    def _normalize_result(self, result: Dict) -> Dict[str, Any]:
        """Normalize pattern-aware results to standard format"""
        return {
            'success': result.get('success', False),
            'completion_rate': 1.0 if result.get('success') else 0.5,
            'output': result.get('output'),
            'pattern_used': result.get('pattern_used'),
            'topology_strategy': 'pattern_aware'
        }

    def _calculate_performance_score(
        self,
        success: bool,
        completion_rate: float,
        expected_time: float,
        actual_time: float
    ) -> float:
        """
        Calculate overall performance score (0.0-1.0).

        Factors:
        - Success (40%)
        - Completion rate (40%)
        - Time efficiency (20%)
        """
        success_score = 1.0 if success else 0.0
        completion_score = completion_rate

        # Time efficiency: 1.0 if on time or faster, decreases if slower
        time_ratio = actual_time / expected_time if expected_time > 0 else 1.0
        time_score = max(0.0, min(1.0, 2.0 - time_ratio))  # Penalize if > 2x expected time

        performance = (
            success_score * 0.4 +
            completion_score * 0.4 +
            time_score * 0.2
        )

        return performance

    def get_comprehensive_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        return {
            'coordinator_status': self.agent_coordinator.get_system_status(),
            'topology_performance': self.topology_optimizer.get_topology_statistics(),
            'execution_history': {
                'total_executions': len(self.execution_history),
                'recent_executions': self.execution_history[-10:] if self.execution_history else [],
                'avg_performance': statistics.mean([e['performance_score'] for e in self.execution_history]) if self.execution_history else 0.0,
                'avg_completion_rate': statistics.mean([e['completion_rate'] for e in self.execution_history]) if self.execution_history else 0.0
            }
        }

    async def optimize_system(self) -> Dict[str, Any]:
        """Run system optimization for 90%+ completion rate target"""
        logger.info("Running system optimization...")

        optimization = await self.topology_optimizer.optimize_for_target_rate(target_completion_rate=0.90)

        logger.info(f"Optimization complete: {len(optimization['recommendations'])} recommendations")

        return optimization


async def main():
    """Demo of topology-aware coordination"""
    print("\n" + "=" * 70)
    print("TOPOLOGY-AWARE MULTI-AGENT COORDINATION DEMO")
    print("=" * 70)

    coordinator = TopologyAwareCoordinator()

    # Test 1: Complex collaborative task
    print("\n\nTest 1: Complex Collaborative Task")
    print("-" * 70)

    result1 = await coordinator.execute_task(
        task_description="Build a distributed microservices platform with authentication, API gateway, and data processing",
        context={'language': 'Python', 'framework': 'FastAPI'}
    )

    print(f"\nTask: {result1['task_description'][:80]}...")
    print(f"Topology: {result1['topology_selection']['selected']} (confidence: {result1['topology_selection']['confidence']:.2f})")
    print(f"Success: {result1['performance']['success']}")
    print(f"Completion Rate: {result1['performance']['completion_rate']:.1%}")
    print(f"Performance Score: {result1['performance']['performance_score']:.2f}")

    # Test 2: Sequential pipeline task
    print("\n\nTest 2: Sequential Pipeline Task")
    print("-" * 70)

    result2 = await coordinator.execute_task(
        task_description="Process data through pipeline: extract from API, transform with validation, load to database",
        context={'batch_processing': True}
    )

    print(f"\nTask: {result2['task_description'][:80]}...")
    print(f"Topology: {result2['topology_selection']['selected']} (confidence: {result2['topology_selection']['confidence']:.2f})")
    print(f"Success: {result2['performance']['success']}")
    print(f"Completion Rate: {result2['performance']['completion_rate']:.1%}")

    # Statistics
    print("\n\nSystem Statistics")
    print("-" * 70)
    stats = coordinator.get_comprehensive_statistics()
    print(json.dumps(stats['topology_performance'], indent=2))

    # Optimization
    print("\n\nSystem Optimization (Target: 90% Completion Rate)")
    print("-" * 70)
    optimization = await coordinator.optimize_system()
    print(f"Current Rate: {optimization['current_overall_rate']:.1%}")
    print(f"Target Rate: {optimization['target_rate']:.1%}")
    print(f"Recommendations: {len(optimization['recommendations'])}")


if __name__ == "__main__":
    asyncio.run(main())

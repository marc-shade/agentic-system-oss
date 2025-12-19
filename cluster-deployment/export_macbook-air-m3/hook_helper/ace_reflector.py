#!/usr/bin/env python3
"""
ACE Reflector Component
Extracts insights from execution outcomes without context collapse
Based on: arXiv 2510.04618v1 - Agentic Context Engineering
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class Insight:
    """Structured insight from execution analysis"""
    insight_id: str
    domain: str
    observation: str
    confidence: float
    evidence: List[str]
    connections: List[Dict[str, str]]
    timestamp: str
    summary: str
    metadata: Dict[str, Any]


@dataclass
class Pattern:
    """Recurring pattern across multiple executions"""
    pattern_id: str
    pattern_type: str
    occurrences: int
    description: str
    evidence: List[str]
    confidence: float
    first_seen: str
    last_seen: str


@dataclass
class Learning:
    """Learning extracted from failure or success"""
    learning_id: str
    context: str
    lesson: str
    category: str
    actionable: bool
    evidence: str
    confidence: float


class ACEReflector:
    """
    Extracts insights from execution outcomes while preserving detail.
    Addresses: Brevity bias prevention from ACE paper.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Reflector with configuration

        Args:
            config: Optional configuration dict with thresholds and settings
        """
        self.config = config or {
            'insight_extraction_threshold': 0.3,
            'pattern_detection_window': 20,
            'failure_analysis_depth': 'detailed',
            'preserve_raw_data': True
        }
        self.insight_history: List[Insight] = []
        self.pattern_cache: Dict[str, Pattern] = {}

    def extract_insights(self, execution_data: Dict[str, Any]) -> List[Insight]:
        """
        Extract patterns from tool execution without summarization.
        Implements ACE's insight extraction without brevity bias.

        Args:
            execution_data: {
                'tool_name': str,
                'parameters': dict,
                'result': any,
                'success': bool,
                'execution_time': float,
                'context': dict
            }

        Returns:
            List of structured insights with full context preservation
        """
        insights = []

        tool_name = execution_data.get('tool_name', 'unknown')
        success = execution_data.get('success', False)
        result = execution_data.get('result')
        params = execution_data.get('parameters', {})
        context = execution_data.get('context', {})
        exec_time = execution_data.get('execution_time', 0)

        # Extract domain from tool name and context
        domain = self._determine_domain(tool_name, params, context)

        # Generate insight ID
        insight_id = self._generate_insight_id(tool_name, params, result)

        # Build observation without summarization
        observation = self._build_detailed_observation(
            tool_name, params, result, success, exec_time
        )

        # Calculate confidence based on execution certainty
        confidence = self._calculate_confidence(success, exec_time, result)

        # Extract evidence (preserve raw data per ACE paper)
        evidence = self._extract_evidence(execution_data)

        # Identify connections to other domains
        connections = self._identify_connections(tool_name, params, context)

        # Generate non-collapsed summary
        summary = self._generate_summary(tool_name, success, observation)

        # Build metadata
        metadata = {
            'tool_category': self._categorize_tool(tool_name),
            'execution_time_ms': exec_time * 1000,
            'parameter_count': len(params),
            'result_size': len(str(result)) if result else 0,
            'context_keys': list(context.keys()) if context else []
        }

        insight = Insight(
            insight_id=insight_id,
            domain=domain,
            observation=observation,
            confidence=confidence,
            evidence=evidence,
            connections=connections,
            timestamp=datetime.now().isoformat(),
            summary=summary,
            metadata=metadata
        )

        self.insight_history.append(insight)
        insights.append(insight)

        # Check for patterns (ACE's grow-and-refine mechanism)
        if len(self.insight_history) >= 3:
            patterns = self.identify_patterns(self.insight_history[-self.config['pattern_detection_window']:])
            for pattern in patterns:
                # Store pattern insights separately
                pattern_insight = self._convert_pattern_to_insight(pattern)
                insights.append(pattern_insight)

        return insights

    def identify_patterns(self, insight_history: List[Insight]) -> List[Pattern]:
        """
        Identify recurring patterns across multiple executions.
        Preserves detail through incremental pattern building.

        Args:
            insight_history: Recent insights to analyze

        Returns:
            List of identified patterns
        """
        patterns = []

        # Group insights by domain
        domain_groups: Dict[str, List[Insight]] = {}
        for insight in insight_history:
            domain = insight.domain
            if domain not in domain_groups:
                domain_groups[domain] = []
            domain_groups[domain].append(insight)

        # Analyze each domain for patterns
        for domain, insights in domain_groups.items():
            if len(insights) < 2:
                continue

            # Success/failure patterns
            success_pattern = self._analyze_success_pattern(domain, insights)
            if success_pattern:
                patterns.append(success_pattern)

            # Tool usage patterns
            tool_pattern = self._analyze_tool_usage_pattern(domain, insights)
            if tool_pattern:
                patterns.append(tool_pattern)

            # Performance patterns
            perf_pattern = self._analyze_performance_pattern(domain, insights)
            if perf_pattern:
                patterns.append(perf_pattern)

        return patterns

    def analyze_failures(self, error_data: Dict[str, Any]) -> List[Learning]:
        """
        Extract learnings from failures without losing error context.
        Implements ACE's detailed failure analysis.

        Args:
            error_data: {
                'error_type': str,
                'error_message': str,
                'stack_trace': str,
                'context': dict,
                'attempted_solution': str
            }

        Returns:
            List of learning objects with full error context
        """
        learnings = []

        error_type = error_data.get('error_type', 'unknown')
        error_msg = error_data.get('error_message', '')
        stack_trace = error_data.get('stack_trace', '')
        context = error_data.get('context', {})
        attempted = error_data.get('attempted_solution', '')

        # Generate learning ID
        learning_id = hashlib.md5(
            f"{error_type}:{error_msg}:{attempted}".encode()
        ).hexdigest()[:12]

        # Categorize error
        category = self._categorize_error(error_type, error_msg)

        # Extract actionable lesson (without losing detail)
        lesson = self._extract_lesson(error_type, error_msg, stack_trace, attempted)

        # Determine if actionable
        actionable = self._is_actionable(lesson, error_type)

        # Build evidence string (preserve full context)
        evidence = self._build_failure_evidence(error_data)

        # Calculate confidence in learning
        confidence = self._calculate_learning_confidence(error_type, stack_trace, attempted)

        learning = Learning(
            learning_id=learning_id,
            context=json.dumps(context, indent=2),
            lesson=lesson,
            category=category,
            actionable=actionable,
            evidence=evidence,
            confidence=confidence
        )

        learnings.append(learning)

        return learnings

    # Private helper methods

    def _determine_domain(self, tool_name: str, params: Dict, context: Dict) -> str:
        """Determine domain from tool and context"""
        # Map tools to domains
        domain_map = {
            'Read': 'file_operations',
            'Write': 'file_operations',
            'Edit': 'file_operations',
            'MultiEdit': 'file_operations',
            'Bash': 'system_operations',
            'Grep': 'search_operations',
            'Glob': 'search_operations',
            'Task': 'agent_coordination',
            'WebSearch': 'web_research',
            'WebFetch': 'web_research',
            'TodoWrite': 'task_management'
        }

        base_domain = domain_map.get(tool_name, 'general')

        # Refine domain based on parameters
        if tool_name == 'Write' and params.get('file_path', '').endswith('.py'):
            return 'python_development'
        elif tool_name == 'Bash' and 'git' in str(params.get('command', '')):
            return 'version_control'
        elif tool_name == 'Task' and params.get('subagent_type'):
            return f"agent_{params['subagent_type']}"

        return base_domain

    def _generate_insight_id(self, tool_name: str, params: Dict, result: Any) -> str:
        """Generate unique insight ID"""
        data = f"{tool_name}:{json.dumps(params, sort_keys=True)}:{datetime.now().isoformat()}"
        return hashlib.md5(data.encode()).hexdigest()[:12]

    def _build_detailed_observation(
        self,
        tool_name: str,
        params: Dict,
        result: Any,
        success: bool,
        exec_time: float
    ) -> str:
        """Build detailed observation without summarization (ACE principle)"""

        status = "succeeded" if success else "failed"

        # Build observation with full detail preservation
        observation_parts = [
            f"Tool '{tool_name}' {status}",
            f"Execution time: {exec_time:.3f}s",
        ]

        # Add parameter details (don't collapse)
        if params:
            param_summary = []
            for key, value in params.items():
                if isinstance(value, str) and len(value) > 100:
                    param_summary.append(f"{key}: {value[:100]}... ({len(value)} chars)")
                else:
                    param_summary.append(f"{key}: {value}")
            observation_parts.append(f"Parameters: {', '.join(param_summary)}")

        # Add result details (preserve, don't summarize)
        if result is not None:
            result_str = str(result)
            if len(result_str) > 200:
                observation_parts.append(f"Result: {result_str[:200]}... (total {len(result_str)} chars)")
            else:
                observation_parts.append(f"Result: {result_str}")

        return " | ".join(observation_parts)

    def _calculate_confidence(self, success: bool, exec_time: float, result: Any) -> float:
        """Calculate confidence score for insight"""
        confidence = 0.5

        if success:
            confidence += 0.3

        if exec_time < 1.0:
            confidence += 0.1
        elif exec_time > 5.0:
            confidence -= 0.1

        if result is not None:
            confidence += 0.1

        return max(0.0, min(1.0, confidence))

    def _extract_evidence(self, execution_data: Dict) -> List[str]:
        """Extract evidence preserving raw data"""
        evidence = []

        if execution_data.get('success'):
            evidence.append(f"Successful execution in {execution_data.get('execution_time', 0):.3f}s")
        else:
            evidence.append(f"Failed execution: {execution_data.get('result', 'Unknown error')}")

        if execution_data.get('parameters'):
            evidence.append(f"Parameters: {json.dumps(execution_data['parameters'], indent=2)}")

        if execution_data.get('context'):
            evidence.append(f"Context: {json.dumps(execution_data['context'], indent=2)}")

        return evidence

    def _identify_connections(self, tool_name: str, params: Dict, context: Dict) -> List[Dict[str, str]]:
        """Identify connections to other domains/entities"""
        connections = []

        # File-based connections
        if 'file_path' in params:
            file_path = params['file_path']
            if '.py' in file_path:
                connections.append({'target': 'python_codebase', 'type': 'modifies'})
            elif '.json' in file_path:
                connections.append({'target': 'configuration', 'type': 'modifies'})

        # Agent-based connections
        if tool_name == 'Task' and 'subagent_type' in params:
            connections.append({
                'target': f"agent_{params['subagent_type']}",
                'type': 'spawns'
            })

        # Context-based connections
        if context.get('project'):
            connections.append({'target': context['project'], 'type': 'related_to'})

        return connections

    def _generate_summary(self, tool_name: str, success: bool, observation: str) -> str:
        """Generate non-collapsed summary"""
        status = "Successful" if success else "Failed"
        return f"{status} {tool_name} execution - {observation[:100]}"

    def _categorize_tool(self, tool_name: str) -> str:
        """Categorize tool for metadata"""
        categories = {
            'Read': 'file_read',
            'Write': 'file_write',
            'Edit': 'file_modify',
            'MultiEdit': 'file_modify',
            'Bash': 'system_command',
            'Grep': 'search',
            'Glob': 'search',
            'Task': 'agent_spawn',
            'WebSearch': 'web_query',
            'WebFetch': 'web_fetch',
            'TodoWrite': 'task_planning'
        }
        return categories.get(tool_name, 'unknown')

    def _convert_pattern_to_insight(self, pattern: Pattern) -> Insight:
        """Convert pattern to insight format"""
        return Insight(
            insight_id=f"pattern_{pattern.pattern_id}",
            domain="pattern_analysis",
            observation=pattern.description,
            confidence=pattern.confidence,
            evidence=pattern.evidence,
            connections=[],
            timestamp=datetime.now().isoformat(),
            summary=f"Pattern detected: {pattern.pattern_type}",
            metadata={
                'pattern_type': pattern.pattern_type,
                'occurrences': pattern.occurrences,
                'first_seen': pattern.first_seen,
                'last_seen': pattern.last_seen
            }
        )

    def _analyze_success_pattern(self, domain: str, insights: List[Insight]) -> Optional[Pattern]:
        """Analyze success/failure patterns"""
        successes = sum(1 for i in insights if i.confidence > 0.7)
        total = len(insights)

        if total < 2:
            return None

        success_rate = successes / total

        if success_rate > 0.8 or success_rate < 0.2:
            pattern_id = hashlib.md5(f"success_{domain}".encode()).hexdigest()[:12]

            return Pattern(
                pattern_id=pattern_id,
                pattern_type="success_rate",
                occurrences=total,
                description=f"Domain '{domain}' shows {success_rate:.1%} success rate across {total} executions",
                evidence=[i.observation for i in insights[:3]],
                confidence=0.8 if total > 5 else 0.6,
                first_seen=insights[0].timestamp,
                last_seen=insights[-1].timestamp
            )

        return None

    def _analyze_tool_usage_pattern(self, domain: str, insights: List[Insight]) -> Optional[Pattern]:
        """Analyze tool usage patterns"""
        tool_counts: Dict[str, int] = {}

        for insight in insights:
            tool = insight.metadata.get('tool_category', 'unknown')
            tool_counts[tool] = tool_counts.get(tool, 0) + 1

        # Find dominant tool
        if tool_counts:
            dominant_tool = max(tool_counts.items(), key=lambda x: x[1])
            if dominant_tool[1] >= len(insights) * 0.6:  # 60% threshold
                pattern_id = hashlib.md5(f"tool_{domain}_{dominant_tool[0]}".encode()).hexdigest()[:12]

                return Pattern(
                    pattern_id=pattern_id,
                    pattern_type="tool_preference",
                    occurrences=dominant_tool[1],
                    description=f"Domain '{domain}' predominantly uses '{dominant_tool[0]}' tool ({dominant_tool[1]}/{len(insights)} times)",
                    evidence=[i.observation for i in insights if i.metadata.get('tool_category') == dominant_tool[0]][:3],
                    confidence=0.75,
                    first_seen=insights[0].timestamp,
                    last_seen=insights[-1].timestamp
                )

        return None

    def _analyze_performance_pattern(self, domain: str, insights: List[Insight]) -> Optional[Pattern]:
        """Analyze performance patterns"""
        exec_times = [i.metadata.get('execution_time_ms', 0) for i in insights]

        if len(exec_times) < 3:
            return None

        avg_time = sum(exec_times) / len(exec_times)

        if avg_time > 1000:  # Slow operations (>1s)
            pattern_id = hashlib.md5(f"perf_{domain}".encode()).hexdigest()[:12]

            return Pattern(
                pattern_id=pattern_id,
                pattern_type="performance",
                occurrences=len(exec_times),
                description=f"Domain '{domain}' shows elevated execution times (avg: {avg_time:.0f}ms)",
                evidence=[f"{i.observation} - {i.metadata.get('execution_time_ms', 0):.0f}ms" for i in insights[:3]],
                confidence=0.7,
                first_seen=insights[0].timestamp,
                last_seen=insights[-1].timestamp
            )

        return None

    def _categorize_error(self, error_type: str, error_msg: str) -> str:
        """Categorize error for learning"""
        error_lower = f"{error_type} {error_msg}".lower()

        if 'permission' in error_lower or 'access' in error_lower:
            return 'permission_error'
        elif 'not found' in error_lower or '404' in error_lower:
            return 'not_found_error'
        elif 'timeout' in error_lower:
            return 'timeout_error'
        elif 'connection' in error_lower or 'network' in error_lower:
            return 'network_error'
        elif 'syntax' in error_lower or 'parse' in error_lower:
            return 'syntax_error'
        elif 'memory' in error_lower or 'oom' in error_lower:
            return 'resource_error'
        else:
            return 'general_error'

    def _extract_lesson(self, error_type: str, error_msg: str, stack_trace: str, attempted: str) -> str:
        """Extract actionable lesson from error (preserve detail)"""
        lesson_parts = [
            f"Error Type: {error_type}",
            f"Error Message: {error_msg}",
        ]

        if attempted:
            lesson_parts.append(f"Attempted Solution: {attempted}")

        if stack_trace:
            # Include key parts of stack trace (don't collapse)
            stack_lines = stack_trace.split('\n')[:5]
            lesson_parts.append(f"Stack Trace Context: {' | '.join(stack_lines)}")

        lesson_parts.append("Recommendation: Analyze error context and adjust approach")

        return " | ".join(lesson_parts)

    def _is_actionable(self, lesson: str, error_type: str) -> bool:
        """Determine if learning is actionable"""
        actionable_types = [
            'permission_error',
            'syntax_error',
            'not_found_error',
            'timeout_error'
        ]

        category = self._categorize_error(error_type, '')
        return category in actionable_types

    def _build_failure_evidence(self, error_data: Dict) -> str:
        """Build comprehensive failure evidence"""
        evidence_parts = []

        for key, value in error_data.items():
            if isinstance(value, dict):
                evidence_parts.append(f"{key}: {json.dumps(value, indent=2)}")
            else:
                evidence_parts.append(f"{key}: {value}")

        return "\n".join(evidence_parts)

    def _calculate_learning_confidence(self, error_type: str, stack_trace: str, attempted: str) -> float:
        """Calculate confidence in extracted learning"""
        confidence = 0.5

        if stack_trace:
            confidence += 0.2

        if attempted:
            confidence += 0.2

        if error_type != 'unknown':
            confidence += 0.1

        return max(0.0, min(1.0, confidence))

    def get_insights_json(self) -> str:
        """Export insights as JSON"""
        return json.dumps([asdict(i) for i in self.insight_history], indent=2)

    def get_patterns_json(self) -> str:
        """Export patterns as JSON"""
        return json.dumps([asdict(p) for p in self.pattern_cache.values()], indent=2)


if __name__ == "__main__":
    # Example usage
    reflector = ACEReflector()

    # Example execution data
    exec_data = {
        'tool_name': 'Write',
        'parameters': {'file_path': '/tmp/test.py', 'content': 'print("hello")'},
        'result': 'File created successfully',
        'success': True,
        'execution_time': 0.123,
        'context': {'project': 'test_project'}
    }

    insights = reflector.extract_insights(exec_data)

    print("Extracted Insights:")
    print(json.dumps([asdict(i) for i in insights], indent=2))

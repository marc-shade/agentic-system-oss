#!/usr/bin/env python3
"""
GPT-5 Metaprompt Hook System
Automatic Task() call interception, confidence evaluation, and prompt transformation
Integrates with unified hook system for seamless GPT-5 optimization
"""

import os
import sys
import json
import time
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

# Add claude directory to path for imports
sys.path.append('/Users/marc/.claude')

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GPT5Strategy(Enum):
    """GPT-5 deployment strategies"""
    FUNCTIONAL = "functional"
    HYBRID = "hybrid"
    PASSTHROUGH = "passthrough"
    BLOCK = "block"

class ConfidenceLevel(Enum):
    """Confidence levels for routing decisions"""
    CRITICAL = "critical"  # < 40%
    LOW = "low"           # 40-60%
    MEDIUM = "medium"     # 60-80%
    HIGH = "high"         # 80-95%
    EXCELLENT = "excellent"  # > 95%

@dataclass
class MetapromptDecision:
    """Decision result from metaprompt analysis"""
    use_gpt5: bool
    strategy: GPT5Strategy
    confidence: float
    enhanced_prompt: str
    metaprompt_applied: str
    validation_rules: List[str]
    performance_target: Dict[str, Any]
    memory_flag: str

class GPT5MetapromptEngine:
    """Core engine for GPT-5 metaprompt transformation"""
    
    # Keywords that trigger GPT-5 deployment
    GPT5_TRIGGER_KEYWORDS = [
        'backend', 'api', 'database', 'architecture', 'functional',
        'mvp', 'enterprise', 'business logic', 'crud', 'authentication',
        'system design', 'microservice', 'integration', 'pipeline',
        'comprehensive', 'complete implementation', 'production ready'
    ]
    
    # Agent types optimized for GPT-5
    GPT5_OPTIMIZED_AGENTS = [
        'Backend Engineer', 'Backend Engineer (Native)', 'System Architect',
        'BMAD Architect', 'Database Architect', 'MCP Builder',
        'Stack Master', 'DevOps Engineer', 'API Documentation Generator'
    ]
    
    # Metaprompt templates for different agent types
    METAPROMPT_TEMPLATES = {
        'Backend Engineer': {
            'template': '''
ROUTING: Backend Development & API Implementation
MISSION: Build production-ready {feature_name} with complete error handling

PRIORITY_STACK:
  1) Functional correctness and completeness
  2) Security and input validation
  3) Performance optimization
  4) Code maintainability and documentation
  [Conflict Resolution: Security > Speed > Aesthetics]

METHODOLOGY:
  1. Analyze requirements and identify edge cases
  2. Design/update database schema with migrations
  3. Implement data models with comprehensive validation
  4. Create service layer with business logic
  5. Build API endpoints with authentication/authorization
  6. Add comprehensive error handling and logging
  7. Implement caching and performance optimizations
  8. Write unit and integration tests

CONSTRAINTS:
  - NO console.log statements in production code
  - NO hardcoded credentials or configuration
  - MUST validate all user inputs
  - MUST handle all error cases gracefully  
  - MUST follow RESTful API conventions
  - MUST include proper HTTP status codes
  - MUST implement rate limiting where appropriate

FORMAT:
  - Code: TypeScript/Python with full type annotations
  - APIs: RESTful with OpenAPI/Swagger documentation
  - Tests: Jest/Pytest with >80% coverage minimum
  - Errors: Consistent JSON error response format

TOOLS (Sequential Use):
  1. Read existing codebase structure and patterns
  2. mcp__enhanced-memory-mcp__search_nodes("backend patterns {tech_stack}")
  3. Edit/MultiEdit for implementation
  4. Bash for running tests and verification

UNCERTAINTY_PROTOCOL:
  - If authentication method unclear → Implement JWT with refresh tokens
  - If database choice ambiguous → Use PostgreSQL with proper migrations
  - If scaling requirements unknown → Design stateless with Redis caching
  - If API versioning needed → Implement header-based versioning

VALIDATION:
  Success = All API endpoints return correct HTTP status codes
  Success = Input validation implemented on every endpoint
  Success = Zero security vulnerabilities in static analysis
  Success = All tests pass with >80% coverage

MEMORY_FLAG: End response with "BACKEND_IMPLEMENTATION_COMPLETE"
''',
            'validation_rules': [
                'no_console_log',
                'proper_error_handling', 
                'input_validation',
                'security_checks'
            ]
        },
        
        'System Architect': {
            'template': '''
ROUTING: System Architecture & Infrastructure Design
MISSION: Design scalable, reliable system architecture for {system_requirements}

PRIORITY_STACK:
  1) System reliability (99.9%+ uptime target)
  2) Horizontal scalability to handle growth
  3) Security and compliance requirements
  4) Cost optimization and operational efficiency
  [Conflict Resolution: Reliability always trumps performance]

METHODOLOGY:
  1. Define system boundaries and service interfaces
  2. Identify potential failure points and mitigation strategies
  3. Design data flow and consistency models
  4. Specify inter-service communication patterns
  5. Create comprehensive monitoring and alerting strategy
  6. Design disaster recovery and backup procedures
  7. Document capacity planning and scaling triggers
  8. Define SLIs, SLOs, and SLAs with monitoring

CONSTRAINTS:
  - NO single points of failure in critical path
  - NO synchronous cascading dependencies
  - MUST handle network partitions gracefully
  - MUST include circuit breakers and timeouts
  - MUST specify backup and recovery strategies
  - MUST address security at every layer

FORMAT:
  - Architecture: C4 model diagrams (Context, Container, Component, Code)
  - Specifications: YAML/JSON configuration schemas
  - Documentation: Markdown with Mermaid diagrams
  - Metrics: Prometheus-compatible monitoring definitions

TOOLS (Sequential Use):
  1. mcp__real-agi-orchestrator__execute_agi_cycle (for complex system reasoning)
  2. WebSearch("distributed systems {pattern} best practices 2025")
  3. mcp__claude-flow__swarm_init (for multi-component design coordination)
  4. mcp__sequentialthinking-local__sequentialthinking (for architectural decisions)

UNCERTAINTY_PROTOCOL:
  - If consistency requirements unclear → Choose eventual consistency with conflict resolution
  - If message queue needed → Redis Streams <1M msg/day, Apache Kafka for higher volume
  - If database architecture unclear → PostgreSQL for OLTP, ClickHouse for OLAP
  - If caching strategy undefined → Multi-layer: Redis + CDN + Application cache

VALIDATION:
  Success = Every critical component has failure handling strategy
  Success = System architecture survives single availability zone failure
  Success = Monitoring covers all critical user journeys
  Success = Recovery procedures documented with RTO/RPO targets

MEMORY_FLAG: Reply "SYSTEM_ARCHITECTURE_VALIDATED"
''',
            'validation_rules': [
                'no_single_point_of_failure',
                'failure_handling_specified',
                'monitoring_coverage',
                'recovery_procedures'
            ]
        },
        
        'MCP Builder': {
            'template': '''
ROUTING: MCP Server Development & Protocol Implementation
MISSION: Create production-grade MCP server for {mcp_capability}

PRIORITY_STACK:
  1) MCP JSON-RPC 2.0 protocol compliance
  2) Comprehensive error handling and validation
  3) Performance optimization (<100ms response time)
  4) Developer experience and documentation
  [Conflict Resolution: Protocol compliance is non-negotiable]

METHODOLOGY:
  1. Define complete tool schemas using Zod validation
  2. Implement MCP server initialization with proper transport
  3. Create tool handlers with comprehensive input validation
  4. Add detailed error handling for all failure scenarios
  5. Implement health check and status endpoints
  6. Add structured logging for debugging and monitoring
  7. Create comprehensive usage examples and documentation
  8. Write integration tests covering all tool scenarios

CONSTRAINTS:
  - MUST follow MCP JSON-RPC 2.0 specification exactly
  - MUST validate all tool parameters with Zod schemas
  - MUST handle connection timeout and recovery scenarios
  - NO blocking operations in tool handlers
  - MUST support stdio transport as primary interface
  - MUST return proper JSON-RPC error codes

FORMAT:
  server.js/server.py Implementation:
    - FastMCP framework OR manual MCP implementation
    - Zod schemas for comprehensive input validation
    - Async/await pattern for all operations
    - Structured error responses
  
  Configuration Files:
    - package.json/requirements.txt with pinned dependencies
    - README.md with installation and usage instructions
    - JSON schema files for tool definitions

TOOLS (Sequential Use):
  1. Read MCP specification and existing server examples
  2. mcp__enhanced-memory-mcp__search_nodes("MCP server implementation patterns")
  3. Write complete server implementation with validation
  4. Bash("npm test" or "pytest") for comprehensive testing

UNCERTAINTY_PROTOCOL:
  - If transport mechanism unclear → Default to stdio with SSE fallback option
  - If schema validation complex → Use Zod with strict type checking
  - If performance requirements undefined → Target <100ms response time
  - If error handling unclear → Return standard JSON-RPC error format

VALIDATION:
  Success = All tools have complete Zod schema validation
  Success = Health endpoint returns proper MCP status format
  Success = All error cases return valid JSON-RPC error responses
  Success = Integration tests cover success and failure scenarios

MEMORY_FLAG: Confirm completion with "MCP_SERVER_PRODUCTION_READY"
''',
            'validation_rules': [
                'mcp_protocol_compliance',
                'zod_validation_complete',
                'jsonrpc_error_format',
                'health_endpoint_working'
            ]
        }
    }
    
    def __init__(self):
        """Initialize the GPT-5 metaprompt engine"""
        self.stats = {
            'total_analyzed': 0,
            'gpt5_deployed': 0,
            'metaprompts_applied': 0,
            'validations_performed': 0
        }
        self.cache_dir = Path('/Users/marc/.claude/.gpt5_cache')
        self.cache_dir.mkdir(exist_ok=True)
        
    def analyze_task(self, agent_type: str, prompt: str, context: Dict[str, Any] = None) -> MetapromptDecision:
        """
        Analyze task to determine GPT-5 suitability and generate metaprompt
        
        Args:
            agent_type: The type of agent being spawned
            prompt: Original task prompt
            context: Additional context information
            
        Returns:
            MetapromptDecision with routing and enhancement information
        """
        self.stats['total_analyzed'] += 1
        
        # Calculate confidence score
        confidence = self._calculate_confidence(agent_type, prompt)
        confidence_level = self._get_confidence_level(confidence)
        
        # Determine if GPT-5 should be used
        should_use_gpt5 = self._should_use_gpt5(agent_type, prompt, confidence)
        
        # Select strategy
        strategy = self._select_strategy(agent_type, prompt, confidence, should_use_gpt5)
        
        # Generate enhanced prompt with metaprompt
        enhanced_prompt = prompt
        metaprompt_applied = "none"
        validation_rules = []
        memory_flag = "TASK_COMPLETE"
        
        if should_use_gpt5 and strategy != GPT5Strategy.PASSTHROUGH:
            enhanced_prompt, metaprompt_applied = self._apply_metaprompt(
                agent_type, prompt, strategy
            )
            validation_rules = self._get_validation_rules(agent_type)
            memory_flag = self._get_memory_flag(agent_type)
            self.stats['metaprompts_applied'] += 1
        
        if should_use_gpt5:
            self.stats['gpt5_deployed'] += 1
            
        # Performance targets
        performance_target = {
            'response_time_ms': 5000 if should_use_gpt5 else 2000,
            'context_retention': True if should_use_gpt5 else False,
            'validation_required': len(validation_rules) > 0
        }
        
        return MetapromptDecision(
            use_gpt5=should_use_gpt5,
            strategy=strategy,
            confidence=confidence,
            enhanced_prompt=enhanced_prompt,
            metaprompt_applied=metaprompt_applied,
            validation_rules=validation_rules,
            performance_target=performance_target,
            memory_flag=memory_flag
        )
    
    def validate_output(self, output: str, validation_rules: List[str]) -> Dict[str, Any]:
        """
        Validate GPT-5 output against specified rules
        
        Args:
            output: The GPT-5 generated output
            validation_rules: List of validation rules to check
            
        Returns:
            Dict with validation results
        """
        self.stats['validations_performed'] += 1
        
        validation_results = {
            'passed': True,
            'issues': [],
            'score': 100.0,
            'recommendations': []
        }
        
        # Check for common hallucination patterns
        hallucination_patterns = [
            (r'lorem ipsum', 'Lorem ipsum placeholder text detected'),
            (r'example\.com|placeholder\.com', 'Placeholder URLs detected'),
            (r'\d{2,3}%.*(?:increase|improvement|better)', 'Unverified statistics detected'),
            (r'TODO:|FIXME:|XXX:', 'Incomplete implementation markers detected')
        ]
        
        for pattern, message in hallucination_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                validation_results['passed'] = False
                validation_results['issues'].append(message)
                validation_results['score'] -= 15
        
        # Apply specific validation rules
        for rule in validation_rules:
            rule_result = self._apply_validation_rule(rule, output)
            if not rule_result['passed']:
                validation_results['passed'] = False
                validation_results['issues'].extend(rule_result['issues'])
                validation_results['score'] -= rule_result['penalty']
                validation_results['recommendations'].extend(rule_result.get('recommendations', []))
        
        # Ensure score doesn't go below 0
        validation_results['score'] = max(0, validation_results['score'])
        
        return validation_results
    
    def _calculate_confidence(self, agent_type: str, prompt: str) -> float:
        """Calculate confidence score for task execution"""
        score = 0.5  # Base score
        
        # Agent type confidence boost
        if agent_type in self.GPT5_OPTIMIZED_AGENTS:
            score += 0.2
        
        # Keyword analysis
        prompt_lower = prompt.lower()
        gpt5_keywords = sum(1 for kw in self.GPT5_TRIGGER_KEYWORDS if kw in prompt_lower)
        score += min(0.3, gpt5_keywords * 0.05)
        
        # Prompt length and specificity
        if len(prompt) > 200:
            score += 0.1  # Detailed prompts generally have higher success
        if any(word in prompt_lower for word in ['must', 'shall', 'required', 'specification']):
            score += 0.1  # Clear requirements increase confidence
            
        # Complexity indicators
        complexity_indicators = ['integration', 'scalable', 'production', 'enterprise', 'architecture']
        if any(indicator in prompt_lower for indicator in complexity_indicators):
            score += 0.1
            
        return min(1.0, score)
    
    def _get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Convert confidence score to level enum"""
        if confidence < 0.4:
            return ConfidenceLevel.CRITICAL
        elif confidence < 0.6:
            return ConfidenceLevel.LOW
        elif confidence < 0.8:
            return ConfidenceLevel.MEDIUM
        elif confidence < 0.95:
            return ConfidenceLevel.HIGH
        else:
            return ConfidenceLevel.EXCELLENT
    
    def _should_use_gpt5(self, agent_type: str, prompt: str, confidence: float) -> bool:
        """Determine if GPT-5 should be used for this task"""
        # Always use GPT-5 for optimized agent types with sufficient confidence
        if agent_type in self.GPT5_OPTIMIZED_AGENTS and confidence >= 0.6:
            return True
            
        # Check for GPT-5 trigger keywords
        prompt_lower = prompt.lower()
        trigger_count = sum(1 for kw in self.GPT5_TRIGGER_KEYWORDS if kw in prompt_lower)
        
        if trigger_count >= 2 and confidence >= 0.5:
            return True
            
        # Complex architectural tasks benefit from GPT-5
        if any(word in prompt_lower for word in ['architecture', 'system design', 'scalability']):
            return True
            
        return False
    
    def _select_strategy(self, agent_type: str, prompt: str, confidence: float, use_gpt5: bool) -> GPT5Strategy:
        """Select the appropriate GPT-5 deployment strategy"""
        if not use_gpt5:
            return GPT5Strategy.PASSTHROUGH
            
        if confidence < 0.4:
            return GPT5Strategy.BLOCK
            
        # Check for UI/design elements that suggest hybrid approach
        ui_keywords = ['ui', 'design', 'visual', 'aesthetic', 'styling', 'animation']
        has_ui_elements = any(kw in prompt.lower() for kw in ui_keywords)
        
        if has_ui_elements and agent_type in self.GPT5_OPTIMIZED_AGENTS:
            return GPT5Strategy.HYBRID
            
        return GPT5Strategy.FUNCTIONAL
    
    def _apply_metaprompt(self, agent_type: str, original_prompt: str, strategy: GPT5Strategy) -> Tuple[str, str]:
        """Apply appropriate metaprompt template to the original prompt"""
        
        # Get template for agent type
        template_info = self.METAPROMPT_TEMPLATES.get(agent_type)
        if not template_info:
            # Use generic enhancement for unknown agent types
            return self._apply_generic_enhancement(original_prompt, strategy)
        
        template = template_info['template']
        
        # Extract key information from original prompt for template variables
        feature_name = self._extract_feature_name(original_prompt)
        system_requirements = self._extract_system_requirements(original_prompt)
        mcp_capability = self._extract_mcp_capability(original_prompt)
        tech_stack = self._extract_tech_stack(original_prompt)
        
        # Apply template formatting
        try:
            formatted_template = template.format(
                feature_name=feature_name,
                system_requirements=system_requirements,
                mcp_capability=mcp_capability,
                tech_stack=tech_stack
            )
        except KeyError:
            # Fallback if template variables don't match
            formatted_template = template.replace('{feature_name}', feature_name) \
                                        .replace('{system_requirements}', system_requirements) \
                                        .replace('{mcp_capability}', mcp_capability) \
                                        .replace('{tech_stack}', tech_stack)
        
        # Combine metaprompt with original prompt
        enhanced_prompt = f"{formatted_template}\n\nORIGINAL REQUEST:\n{original_prompt}"
        
        # Add strategy-specific enhancements
        if strategy == GPT5Strategy.HYBRID:
            enhanced_prompt += "\n\n[HYBRID WORKFLOW] Focus on functional completeness. UI polish will be handled by specialized agents in followup phase."
        elif strategy == GPT5Strategy.FUNCTIONAL:
            enhanced_prompt += "\n\n[FUNCTIONAL FOCUS] Prioritize working functionality over visual aesthetics."
        
        return enhanced_prompt, f"metaprompt_{agent_type.lower().replace(' ', '_')}"
    
    def _apply_generic_enhancement(self, original_prompt: str, strategy: GPT5Strategy) -> Tuple[str, str]:
        """Apply generic GPT-5 enhancement when no specific template exists"""
        
        generic_template = '''
ROUTING: Task Execution with GPT-5 Optimization
MISSION: Complete the following task with focus on functional correctness

PRIORITY_STACK:
  1) Functional completeness and accuracy
  2) Error handling and validation
  3) Code quality and maintainability
  [Conflict Resolution: Functionality over aesthetics]

METHODOLOGY:
  1. Analyze requirements thoroughly
  2. Implement core functionality first
  3. Add comprehensive error handling
  4. Test and validate implementation
  5. Document key decisions and patterns

CONSTRAINTS:
  - NO placeholder content (lorem ipsum, example.com, etc.)
  - NO incomplete implementations
  - MUST handle error scenarios
  - MUST provide working functionality

UNCERTAINTY_PROTOCOL:
  - If requirements unclear → Ask for clarification or provide multiple options
  - If implementation choice ambiguous → Choose proven, maintainable approach
  
VALIDATION:
  Success = All functionality works as described
  Success = No placeholder or incomplete content
  Success = Proper error handling implemented

MEMORY_FLAG: End with "GPT5_TASK_COMPLETE"
'''
        
        enhanced_prompt = f"{generic_template}\n\nORIGINAL REQUEST:\n{original_prompt}"
        return enhanced_prompt, "generic_gpt5_enhancement"
    
    def _extract_feature_name(self, prompt: str) -> str:
        """Extract feature name from prompt"""
        # Look for common feature indicators
        patterns = [
            r'build (?:a |an |the )?([^.]+?)(?:\s+feature|\s+system|\s+component|$)',
            r'implement (?:a |an |the )?([^.]+?)(?:\s+feature|\s+system|\s+component|$)',
            r'create (?:a |an |the )?([^.]+?)(?:\s+feature|\s+system|\s+component|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "the requested feature"
    
    def _extract_system_requirements(self, prompt: str) -> str:
        """Extract system requirements from prompt"""
        # Look for requirement indicators
        if 'system' in prompt.lower():
            return prompt[:200] + "..." if len(prompt) > 200 else prompt
        return "the specified system requirements"
    
    def _extract_mcp_capability(self, prompt: str) -> str:
        """Extract MCP capability from prompt"""
        if 'mcp' in prompt.lower():
            return prompt[:100] + "..." if len(prompt) > 100 else prompt
        return "the requested MCP capability"
    
    def _extract_tech_stack(self, prompt: str) -> str:
        """Extract technology stack from prompt"""
        tech_keywords = ['typescript', 'python', 'javascript', 'react', 'node', 'express', 'fastapi']
        found_tech = [tech for tech in tech_keywords if tech in prompt.lower()]
        return ', '.join(found_tech) if found_tech else 'modern stack'
    
    def _get_validation_rules(self, agent_type: str) -> List[str]:
        """Get validation rules for specific agent type"""
        template_info = self.METAPROMPT_TEMPLATES.get(agent_type, {})
        return template_info.get('validation_rules', ['basic_quality_check'])
    
    def _get_memory_flag(self, agent_type: str) -> str:
        """Get appropriate memory flag for agent type"""
        flag_mapping = {
            'Backend Engineer': 'BACKEND_IMPLEMENTATION_COMPLETE',
            'System Architect': 'SYSTEM_ARCHITECTURE_VALIDATED',
            'MCP Builder': 'MCP_SERVER_PRODUCTION_READY'
        }
        return flag_mapping.get(agent_type, 'GPT5_TASK_COMPLETE')
    
    def _apply_validation_rule(self, rule: str, output: str) -> Dict[str, Any]:
        """Apply specific validation rule to output"""
        
        if rule == 'no_console_log':
            if re.search(r'console\.log\(', output):
                return {
                    'passed': False,
                    'issues': ['Console.log statements found in production code'],
                    'penalty': 10,
                    'recommendations': ['Remove console.log and use proper logging framework']
                }
        
        elif rule == 'proper_error_handling':
            if not re.search(r'try|catch|throw|error|exception', output, re.IGNORECASE):
                return {
                    'passed': False,
                    'issues': ['No error handling patterns detected'],
                    'penalty': 20,
                    'recommendations': ['Add try-catch blocks and proper error handling']
                }
        
        elif rule == 'input_validation':
            if not re.search(r'validat|schema|check|sanitize', output, re.IGNORECASE):
                return {
                    'passed': False,
                    'issues': ['No input validation patterns detected'],
                    'penalty': 15,
                    'recommendations': ['Add input validation and sanitization']
                }
        
        elif rule == 'mcp_protocol_compliance':
            if 'json-rpc' not in output.lower() or 'mcp' not in output.lower():
                return {
                    'passed': False,
                    'issues': ['MCP protocol compliance not evident'],
                    'penalty': 25,
                    'recommendations': ['Ensure proper MCP JSON-RPC 2.0 implementation']
                }
        
        # Rule passed
        return {'passed': True, 'issues': [], 'penalty': 0}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        total = self.stats['total_analyzed']
        if total == 0:
            return self.stats
            
        return {
            **self.stats,
            'gpt5_usage_rate': self.stats['gpt5_deployed'] / total,
            'metaprompt_application_rate': self.stats['metaprompts_applied'] / total,
            'validation_rate': self.stats['validations_performed'] / total
        }

class GPT5MetapromptHook:
    """
    Main hook integration class for GPT-5 metaprompt system
    Integrates with Claude Code's unified hook system
    """
    
    def __init__(self):
        self.engine = GPT5MetapromptEngine()
        self.enabled = True
        self.performance_log = []
        
    def process_task_call(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Task() tool calls for GPT-5 optimization
        
        Args:
            tool_name: Should be "Task" 
            args: Task arguments including subagent_type and prompt
            
        Returns:
            Dict with processing results and any modifications
        """
        
        if not self.enabled or tool_name != "Task":
            return {
                'processed': False,
                'reason': 'Not a Task call or hook disabled'
            }
        
        start_time = time.time()
        
        try:
            # Extract task information
            agent_type = args.get('subagent_type', 'Unknown Agent')
            prompt = args.get('prompt', '')
            description = args.get('description', '')
            
            # Analyze task for GPT-5 suitability  
            decision = self.engine.analyze_task(agent_type, prompt)
            
            # Modify args if GPT-5 should be used
            modifications = []
            if decision.use_gpt5:
                # Update prompt with metaprompt
                args['prompt'] = decision.enhanced_prompt
                modifications.append('prompt_enhanced_with_metaprompt')
                
                # Add model hint if not already specified
                if 'model' not in args:
                    args['model'] = 'gpt-5'
                    modifications.append('model_set_to_gpt5')
                
                # Update description to indicate GPT-5 usage
                original_desc = description
                args['description'] = f"[GPT-5-{decision.strategy.value.upper()}] {original_desc}"
                modifications.append('description_updated')
            
            # Record performance
            processing_time = time.time() - start_time
            self.performance_log.append({
                'timestamp': time.time(),
                'agent_type': agent_type,
                'confidence': decision.confidence,
                'gpt5_used': decision.use_gpt5,
                'strategy': decision.strategy.value,
                'processing_time_ms': processing_time * 1000,
                'metaprompt_applied': decision.metaprompt_applied
            })
            
            # Keep only last 100 performance records
            if len(self.performance_log) > 100:
                self.performance_log = self.performance_log[-100:]
            
            result = {
                'processed': True,
                'gpt5_decision': {
                    'use_gpt5': decision.use_gpt5,
                    'strategy': decision.strategy.value,
                    'confidence': decision.confidence,
                    'metaprompt_applied': decision.metaprompt_applied
                },
                'modifications': modifications,
                'validation_rules': decision.validation_rules,
                'performance_target': decision.performance_target,
                'processing_time_ms': processing_time * 1000
            }
            
            logger.info(f"🤖 GPT-5 Hook: {agent_type} - {'ENHANCED' if decision.use_gpt5 else 'PASSTHROUGH'} (confidence: {decision.confidence:.2f})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ GPT-5 metaprompt hook failed: {e}")
            return {
                'processed': False,
                'error': str(e),
                'processing_time_ms': (time.time() - start_time) * 1000
            }
    
    def validate_task_output(self, output: str, validation_rules: List[str]) -> Dict[str, Any]:
        """Validate task output using GPT-5 specific rules"""
        return self.engine.validate_output(output, validation_rules)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        
        if not self.performance_log:
            return {'message': 'No performance data available'}
        
        # Calculate metrics
        total_calls = len(self.performance_log)
        gpt5_calls = sum(1 for record in self.performance_log if record['gpt5_used'])
        avg_processing_time = sum(record['processing_time_ms'] for record in self.performance_log) / total_calls
        avg_confidence = sum(record['confidence'] for record in self.performance_log) / total_calls
        
        # Strategy breakdown
        strategy_counts = {}
        for record in self.performance_log:
            strategy = record['strategy']
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        # Agent type breakdown
        agent_counts = {}
        for record in self.performance_log:
            agent = record['agent_type']
            agent_counts[agent] = agent_counts.get(agent, 0) + 1
        
        return {
            'total_task_calls': total_calls,
            'gpt5_usage_count': gpt5_calls,
            'gpt5_usage_percentage': (gpt5_calls / total_calls) * 100,
            'average_processing_time_ms': avg_processing_time,
            'average_confidence': avg_confidence,
            'strategy_distribution': strategy_counts,
            'agent_type_distribution': agent_counts,
            'engine_stats': self.engine.get_stats(),
            'last_10_calls': self.performance_log[-10:]
        }
    
    def reset_performance_metrics(self):
        """Reset all performance tracking"""
        self.performance_log = []
        self.engine.stats = {
            'total_analyzed': 0,
            'gpt5_deployed': 0, 
            'metaprompts_applied': 0,
            'validations_performed': 0
        }
        logger.info("🔄 GPT-5 metaprompt hook metrics reset")

# Global hook instance
_gpt5_hook = None

def get_gpt5_metaprompt_hook() -> GPT5MetapromptHook:
    """Get singleton instance of GPT-5 metaprompt hook"""
    global _gpt5_hook
    if _gpt5_hook is None:
        _gpt5_hook = GPT5MetapromptHook()
    return _gpt5_hook

# Integration functions for unified hook system
def enhance_task_with_gpt5_metaprompt(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main integration function for unified hook system
    Call this from pre_tool_use hook for Task calls
    """
    hook = get_gpt5_metaprompt_hook()
    return hook.process_task_call(tool_name, args)

def validate_gpt5_task_output(output: str, validation_rules: List[str]) -> Dict[str, Any]:
    """
    Integration function for output validation
    Call this from post_tool_use hook
    """
    hook = get_gpt5_metaprompt_hook()
    return hook.validate_task_output(output, validation_rules)

def get_gpt5_performance_metrics() -> Dict[str, Any]:
    """Get performance metrics for monitoring dashboard"""
    hook = get_gpt5_metaprompt_hook()
    return hook.get_performance_metrics()

# Test function
def test_gpt5_metaprompt_hook():
    """Test the GPT-5 metaprompt hook system"""
    
    print("🧪 TESTING GPT-5 METAPROMPT HOOK SYSTEM")
    print("=" * 60)
    
    hook = get_gpt5_metaprompt_hook()
    
    test_cases = [
        {
            'name': 'Backend API Development',
            'tool_name': 'Task',
            'args': {
                'subagent_type': 'Backend Engineer',
                'prompt': 'Build a REST API for user authentication with JWT tokens',
                'description': 'Create authentication system'
            }
        },
        {
            'name': 'System Architecture',
            'tool_name': 'Task',
            'args': {
                'subagent_type': 'System Architect',
                'prompt': 'Design scalable microservices architecture for e-commerce platform',
                'description': 'E-commerce system design'
            }
        },
        {
            'name': 'MCP Server Development', 
            'tool_name': 'Task',
            'args': {
                'subagent_type': 'MCP Builder',
                'prompt': 'Create MCP server for file operations with validation',
                'description': 'File operations MCP server'
            }
        },
        {
            'name': 'Frontend UI Task (should not use GPT-5)',
            'tool_name': 'Task',
            'args': {
                'subagent_type': 'Frontend Specialist',
                'prompt': 'Create beautiful landing page with animations and gradients',
                'description': 'Landing page design'
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}️⃣ Testing: {test_case['name']}")
        
        result = hook.process_task_call(test_case['tool_name'], test_case['args'])
        
        if result['processed']:
            decision = result['gpt5_decision']
            print(f"   ✅ GPT-5 Usage: {'YES' if decision['use_gpt5'] else 'NO'}")
            print(f"   📊 Confidence: {decision['confidence']:.2f}")
            print(f"   🎯 Strategy: {decision['strategy']}")
            print(f"   🔧 Modifications: {len(result['modifications'])}")
            print(f"   ⏱️  Processing Time: {result['processing_time_ms']:.2f}ms")
        else:
            print(f"   ❌ Processing failed: {result.get('error', 'unknown')}")
    
    print(f"\n📈 PERFORMANCE METRICS:")
    metrics = hook.get_performance_metrics()
    print(f"   Total Calls: {metrics.get('total_task_calls', 0)}")
    print(f"   GPT-5 Usage: {metrics.get('gpt5_usage_percentage', 0):.1f}%")
    print(f"   Avg Processing Time: {metrics.get('average_processing_time_ms', 0):.2f}ms")
    print(f"   Avg Confidence: {metrics.get('average_confidence', 0):.2f}")
    
    print(f"\n✅ GPT-5 METAPROMPT HOOK SYSTEM TEST COMPLETE!")

if __name__ == "__main__":
    test_gpt5_metaprompt_hook()
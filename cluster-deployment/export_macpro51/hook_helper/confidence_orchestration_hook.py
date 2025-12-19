#!/usr/bin/env python3
"""
Confidence Orchestration Hook
Automatically evaluates confidence and routes agents based on DeepConf principles
"""

import json
import subprocess
import hashlib
import os
from datetime import datetime

class ConfidenceOrchestrator:
    """Manages confidence evaluation and routing for agent tasks"""
    
    def __init__(self):
        self.confidence_sources = {
            'zria': 0.5,      # Default baseline
            'ctm': 0.5,       # Continuous thought
            'neural': 0.5,    # Neural confidence
            'historical': 0.7 # Historical performance
        }
        
        # Task complexity patterns
        self.complexity_patterns = {
            'simple': ['fix', 'add', 'update', 'rename', 'move', 'copy'],
            'medium': ['refactor', 'implement', 'integrate', 'optimize', 'test'],
            'complex': ['architect', 'design', 'reverse', 'analyze', 'research'],
            'critical': ['security', 'authentication', 'encryption', 'production', 'payment']
        }
        
        # Agent confidence profiles
        self.agent_profiles = {
            'Backend Engineer': {'zria': 0.6, 'ctm': 0.75, 'neural': 0.7, 'historical': 0.8},
            'Frontend Specialist': {'zria': 0.65, 'ctm': 0.7, 'neural': 0.75, 'historical': 0.85},
            'System Architect': {'zria': 0.8, 'ctm': 0.85, 'neural': 0.75, 'historical': 0.9},
            'Security Specialist': {'zria': 0.75, 'ctm': 0.8, 'neural': 0.7, 'historical': 0.85},
            'Swarm Researcher': {'zria': 0.7, 'ctm': 0.8, 'neural': 0.8, 'historical': 0.75},
            'Local Privacy Agent': {'zria': 0.9, 'ctm': 0.9, 'neural': 0.85, 'historical': 0.95}
        }
    
    def detect_task_complexity(self, task_description):
        """Detect task complexity from description"""
        task_lower = task_description.lower()
        
        # Check for critical patterns first
        for pattern in self.complexity_patterns['critical']:
            if pattern in task_lower:
                return 'critical'
        
        # Check complex patterns
        for pattern in self.complexity_patterns['complex']:
            if pattern in task_lower:
                return 'complex'
        
        # Check medium patterns
        for pattern in self.complexity_patterns['medium']:
            if pattern in task_lower:
                return 'medium'
        
        # Check simple patterns
        for pattern in self.complexity_patterns['simple']:
            if pattern in task_lower:
                return 'simple'
        
        # Default to medium
        return 'medium'
    
    def get_agent_confidence(self, agent_type, task):
        """Get confidence scores for a specific agent and task"""
        # Start with agent's profile or defaults
        if agent_type in self.agent_profiles:
            confidence = self.agent_profiles[agent_type].copy()
        else:
            confidence = self.confidence_sources.copy()
        
        # Adjust for task-specific factors
        task_lower = task.lower()
        
        # Boost confidence for agent's specialty
        if 'backend' in agent_type.lower() and any(x in task_lower for x in ['api', 'server', 'database']):
            confidence['neural'] *= 1.1
            confidence['historical'] *= 1.05
        elif 'frontend' in agent_type.lower() and any(x in task_lower for x in ['ui', 'component', 'style']):
            confidence['neural'] *= 1.1
            confidence['historical'] *= 1.05
        elif 'security' in agent_type.lower() and any(x in task_lower for x in ['security', 'auth', 'encrypt']):
            confidence['zria'] *= 1.15
            confidence['ctm'] *= 1.1
        
        # Apply low ZRIA pattern for complex symbolic tasks
        if any(x in task_lower for x in ['oauth', 'jwt', 'protocol', 'spec', 'standard']):
            confidence['zria'] *= 0.5  # Simulate low ZRIA (36.7% scenario)
            confidence['ctm'] *= 1.2   # CTM compensation
        
        # Normalize to 0-1 range
        for key in confidence:
            confidence[key] = min(1.0, max(0.0, confidence[key]))
        
        return confidence
    
    def call_confidence_orchestrator(self, task, confidence_sources, complexity):
        """Call the confidence-orchestrator MCP tool"""
        try:
            # Build the MCP tool call
            tool_call = {
                "task": task,
                "confidenceSources": confidence_sources,
                "taskComplexity": complexity
            }
            
            # Store in a temp file for the orchestrator to read
            # (In production, this would be a proper MCP call)
            confidence_cache_path = '/tmp/confidence_evaluation.json'
            with open(confidence_cache_path, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'evaluation': tool_call,
                    'result': self.calculate_local_confidence(confidence_sources, complexity)
                }, f)
            
            return self.calculate_local_confidence(confidence_sources, complexity)
        except Exception as e:
            # Fallback to local calculation
            return self.calculate_local_confidence(confidence_sources, complexity)
    
    def calculate_local_confidence(self, confidence_sources, complexity):
        """Local confidence calculation (fallback)"""
        # Weighted average with DeepConf-inspired calibration
        weights = {
            'zria': 0.2,
            'ctm': 0.25,
            'neural': 0.25,
            'historical': 0.3
        }
        
        aggregate = sum(confidence_sources.get(k, 0.5) * weights.get(k, 0.1) 
                       for k in confidence_sources)
        
        # Apply complexity modifier
        complexity_modifiers = {
            'simple': 1.2,
            'medium': 1.0,
            'complex': 0.8,
            'critical': 0.6
        }
        aggregate *= complexity_modifiers.get(complexity, 1.0)
        aggregate = min(1.0, max(0.0, aggregate))
        
        # Determine routing strategy
        if aggregate >= 0.8:
            routing = 'fast_execution'
            thinking_mode = 'online'
        elif aggregate >= 0.6:
            routing = 'standard_validation'
            thinking_mode = 'online'
        elif aggregate >= 0.4:
            routing = 'deep_exploration'
            thinking_mode = 'offline'
        else:
            routing = 'human_escalation'
            thinking_mode = 'offline'
        
        return {
            'aggregateConfidence': aggregate,
            'routingStrategy': routing,
            'thinkingMode': thinking_mode,
            'recommendation': 'proceed' if aggregate >= 0.6 else 'review'
        }
    
    def enhance_agent_prompt(self, original_prompt, confidence_result, agent_type):
        """Enhance agent prompt with confidence-aware instructions"""
        confidence = confidence_result['aggregateConfidence']
        routing = confidence_result['routingStrategy']
        thinking_mode = confidence_result['thinkingMode']
        
        enhancement = f"""
CONFIDENCE-AWARE EXECUTION:
Current Confidence: {confidence:.2%}
Routing Strategy: {routing}
Thinking Mode: {thinking_mode}

"""
        
        if routing == 'fast_execution':
            enhancement += """FAST EXECUTION MODE:
- Use cached patterns and proven solutions
- Minimize exploration, maximize speed
- Skip extensive validation for known patterns
- Target: Complete in minimal time with high confidence

"""
        elif routing == 'deep_exploration':
            enhancement += """DEEP EXPLORATION MODE:
- Conduct thorough research before implementation
- Validate assumptions with multiple sources
- Consider alternative approaches
- Use mcp__sequentialthinking_local__sequentialthinking for deep reasoning
- Document uncertainty and get peer validation

"""
        elif routing == 'human_escalation':
            enhancement += """CRITICAL LOW CONFIDENCE:
- This task has very low confidence ({confidence:.2%})
- Provide detailed analysis of risks and uncertainties
- Suggest alternative approaches
- Recommend human review before proceeding
- DO NOT make autonomous decisions on critical parts

"""
        
        # Add confidence breakdown for transparency
        enhancement += f"""CONFIDENCE BREAKDOWN:
{json.dumps(confidence_result, indent=2)}

---
ORIGINAL TASK:
"""
        
        return enhancement + original_prompt
    
    def should_spawn_research_swarm(self, confidence_result):
        """Determine if we should spawn additional research agents"""
        return (confidence_result['aggregateConfidence'] < 0.6 and 
                confidence_result['routingStrategy'] == 'deep_exploration')

def process_task_spawn(tool_args, orchestrator):
    """Process Task tool spawn with confidence evaluation"""
    agent_type = tool_args.get('subagent_type', 'generic')
    task_description = tool_args.get('description', '')
    original_prompt = tool_args.get('prompt', '')
    
    # Get confidence for this agent/task combination
    confidence_sources = orchestrator.get_agent_confidence(agent_type, task_description)
    complexity = orchestrator.detect_task_complexity(task_description)
    
    # Evaluate confidence
    confidence_result = orchestrator.call_confidence_orchestrator(
        task_description,
        confidence_sources,
        complexity
    )
    
    # Log confidence evaluation
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'agent_type': agent_type,
        'task': task_description[:100],
        'confidence': confidence_result['aggregateConfidence'],
        'routing': confidence_result['routingStrategy'],
        'complexity': complexity
    }
    
    # Append to confidence log
    log_path = '/tmp/confidence_orchestration.log'
    with open(log_path, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')
    
    # Enhance the agent prompt with confidence awareness
    enhanced_prompt = orchestrator.enhance_agent_prompt(
        original_prompt,
        confidence_result,
        agent_type
    )
    
    # Update tool arguments
    tool_args['prompt'] = enhanced_prompt
    
    # Check if we need to spawn research agents
    if orchestrator.should_spawn_research_swarm(confidence_result):
        # Add a note for spawning research swarm
        tool_args['_confidence_recommendation'] = 'spawn_research_swarm'
    
    return tool_args, confidence_result

def main():
    """Main hook handler"""
    try:
        # Read hook input
        hook_input = json.loads(sys.stdin.read())
        
        tool_name = hook_input.get("tool", "")
        tool_args = hook_input.get("arguments", {})
        
        # Initialize confidence orchestrator
        orchestrator = ConfidenceOrchestrator()
        
        # Process Task spawns with confidence evaluation
        if tool_name == "Task":
            enhanced_args, confidence_result = process_task_spawn(tool_args, orchestrator)
            
            # Update the arguments
            hook_input["arguments"] = enhanced_args
            
            # If confidence is critically low, add a warning
            if confidence_result['aggregateConfidence'] < 0.4:
                hook_input["_confidence_warning"] = (
                    f"LOW CONFIDENCE ({confidence_result['aggregateConfidence']:.2%}): "
                    f"Consider human review or additional research"
                )
        
        # Return the potentially modified input
        return json.dumps({"allow": True, "arguments": hook_input.get("arguments", {})})
        
    except Exception as e:
        # On error, allow tool to proceed but log the issue
        with open('/tmp/confidence_hook_errors.log', 'a') as f:
            f.write(f"{datetime.now().isoformat()}: {str(e)}\n")
        return json.dumps({"allow": True})

if __name__ == "__main__":
    result = main()
    print(result)
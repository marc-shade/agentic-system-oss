#!/usr/bin/env python3
"""
Hallucination Prevention Hook for Claude Code
Automatically injects hallucination prevention protocols into all agent spawns
Based on OpenAI's research on why language models hallucinate
"""

import json
import sys
import os
import re
from datetime import datetime

# Add parent directory to path for imports
sys.path.append('/home/marc/.claude')
from hallucination_prevention_system import (
    HallucinationPreventionMiddleware,
    AgentConfidenceManager,
    UncertaintyAwarePromptEnhancer
)

class HallucinationPreventionHook:
    """Hook to inject hallucination prevention into agent tasks"""
    
    def __init__(self):
        self.middleware = HallucinationPreventionMiddleware()
        self.confidence_manager = AgentConfidenceManager()
        self.prompt_enhancer = UncertaintyAwarePromptEnhancer()
        self.log_file = "/home/marc/.claude/hallucination_prevention.log"
        
    def process_task_tool(self, tool_data):
        """Process Task tool calls to inject hallucination prevention"""
        if tool_data.get('tool') != 'Task':
            return tool_data
        
        params = tool_data.get('parameters', {})
        agent_type = params.get('subagent_type', 'Unknown')
        task_description = params.get('description', '')
        original_prompt = params.get('prompt', '')
        
        # Calculate confidence for this task
        confidence = self._calculate_confidence(agent_type, task_description)
        
        # Inject hallucination prevention protocols
        enhanced_prompt = self._inject_prevention_protocols(
            original_prompt, agent_type, task_description, confidence
        )
        
        # Update the prompt
        params['prompt'] = enhanced_prompt
        
        # Log the enhancement
        self._log_enhancement(agent_type, task_description, confidence)
        
        return tool_data
    
    def _calculate_confidence(self, agent_type, task):
        """Calculate confidence level for the task"""
        base_confidence = self.confidence_manager.get_confidence_threshold(agent_type, task)
        
        # Adjust for task complexity
        complexity_indicators = {
            'specific': -0.1,
            'exact': -0.15,
            'performance': -0.2,
            'benchmark': -0.15,
            'compatibility': -0.1,
            'version': -0.1,
            'security': -0.2,
            'cost': -0.25,
            'date': -0.2,
            'statistic': -0.15
        }
        
        adjustment = 0.0
        task_lower = task.lower()
        for indicator, penalty in complexity_indicators.items():
            if indicator in task_lower:
                adjustment += penalty
        
        return max(0.2, min(0.95, base_confidence + adjustment))
    
    def _inject_prevention_protocols(self, prompt, agent_type, task, confidence):
        """Inject hallucination prevention protocols into prompt"""
        
        # Determine confidence level category
        if confidence >= 0.8:
            confidence_category = "HIGH"
            strategy = "Proceed with standard validation"
        elif confidence >= 0.6:
            confidence_category = "MEDIUM"
            strategy = "Use qualifiers and suggest verification"
        elif confidence >= 0.4:
            confidence_category = "LOW"
            strategy = "Express significant uncertainty, provide ranges"
        else:
            confidence_category = "UNCERTAIN"
            strategy = "Consider abstaining or saying 'I don't know'"
        
        prevention_protocol = f"""

===== HALLUCINATION PREVENTION PROTOCOL =====
[Auto-injected by Hallucination Prevention System]

CONFIDENCE LEVEL: {confidence:.2%} ({confidence_category})
STRATEGY: {strategy}

CRITICAL RULES FOR THIS TASK:
1. Your confidence for "{task}" is {confidence_category} ({confidence:.2%})
2. {self._get_confidence_specific_rules(confidence)}
3. {self._get_agent_specific_rules(agent_type)}

REQUIRED BEHAVIORS:
{self._get_required_behaviors(confidence)}

FORBIDDEN PATTERNS:
- No absolute claims ("always", "never", "all", "every") without verification
- No specific dates or versions without checking
- No exact statistics without sources
- No performance claims without benchmarks
- No quotes without attribution

UNCERTAINTY LANGUAGE:
{self._get_uncertainty_language(confidence)}

VERIFICATION REQUIREMENTS:
{self._get_verification_requirements(agent_type, task)}

Remember: Acknowledging uncertainty is a sign of reliability, not weakness.
===== END HALLUCINATION PREVENTION =====

"""
        
        # Check if original prompt already has prevention protocols
        if "HALLUCINATION PREVENTION" in prompt:
            return prompt  # Don't double-inject
        
        # Inject after the main prompt but before the task
        if "Your task:" in prompt or "YOUR TASK:" in prompt:
            # Find the task marker and inject before it
            task_marker = "Your task:" if "Your task:" in prompt else "YOUR TASK:"
            parts = prompt.split(task_marker, 1)
            return parts[0] + prevention_protocol + task_marker + parts[1]
        else:
            # Append to the end
            return prompt + prevention_protocol
    
    def _get_confidence_specific_rules(self, confidence):
        """Get rules based on confidence level"""
        if confidence >= 0.8:
            return "You can proceed with reasonable confidence, but verify critical claims"
        elif confidence >= 0.6:
            return "Express moderate uncertainty, use 'likely', 'probably', 'typically'"
        elif confidence >= 0.4:
            return "Express significant uncertainty, provide ranges not specifics"
        else:
            return "Strong preference for abstaining over guessing"
    
    def _get_agent_specific_rules(self, agent_type):
        """Get agent-specific rules"""
        rules = {
            "Backend Engineer": "Verify API docs, benchmark performance claims",
            "Frontend Specialist": "Check browser compatibility, test UI claims",
            "Security Specialist": "Always verify CVEs, cite security sources",
            "System Architect": "Provide ranges for scale/cost, avoid absolutes",
            "QA Engineer": "Test assertions, avoid coverage percentages without data",
            "Research Analyst": "Cite all sources, acknowledge data limitations",
            "Documentation Scribe": "Flag unverified technical details",
            "MCP Builder": "Test implementations, verify protocol specs"
        }
        return rules.get(agent_type, "Verify all factual claims before stating them")
    
    def _get_required_behaviors(self, confidence):
        """Get required behaviors based on confidence"""
        if confidence >= 0.8:
            return """
- Proceed with implementation but note any assumptions
- Flag areas that would benefit from testing
- Use "should" rather than "will" for outcomes"""
        elif confidence >= 0.6:
            return """
- Start responses with confidence acknowledgment
- Use qualifiers: "typically", "generally", "often"
- Suggest verification steps for critical claims
- Provide alternatives where applicable"""
        elif confidence >= 0.4:
            return """
- Explicitly state "I have limited information"
- Provide ranges instead of specific numbers
- List multiple possibilities
- Strongly recommend verification
- Focus on what you DO know reliably"""
        else:
            return """
- Consider saying "I don't have enough information"
- If responding, heavily qualify with uncertainty
- Provide research directions instead of answers
- Suggest authoritative sources to consult
- Focus on methodology rather than conclusions"""
    
    def _get_uncertainty_language(self, confidence):
        """Get appropriate uncertainty language"""
        if confidence >= 0.8:
            return "Use: should, expected to, typically, in most cases"
        elif confidence >= 0.6:
            return "Use: likely, probably, appears to, seems to, generally"
        elif confidence >= 0.4:
            return "Use: might, could be, possibly, uncertain but, limited information suggests"
        else:
            return "Use: I don't know, insufficient information, would need to verify, cannot determine"
    
    def _get_verification_requirements(self, agent_type, task):
        """Get verification requirements"""
        requirements = []
        
        # Check for specific verification needs
        task_lower = task.lower()
        
        if 'performance' in task_lower:
            requirements.append("Benchmark before claiming performance improvements")
        if 'security' in task_lower:
            requirements.append("Verify against CVE databases and security advisories")
        if 'compatibility' in task_lower or 'browser' in task_lower:
            requirements.append("Check caniuse.com or MDN for compatibility")
        if 'api' in task_lower or 'library' in task_lower:
            requirements.append("Consult official documentation for APIs/libraries")
        if 'cost' in task_lower or 'pricing' in task_lower:
            requirements.append("Check current pricing from official sources")
        if 'version' in task_lower or 'release' in task_lower:
            requirements.append("Verify version information from official releases")
        
        if not requirements:
            requirements.append("Verify any specific claims before stating as fact")
        
        return "\n".join(f"- {req}" for req in requirements)
    
    def _log_enhancement(self, agent_type, task, confidence):
        """Log the enhancement for auditing"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent_type": agent_type,
            "task": task[:100],  # Truncate long tasks
            "confidence": confidence,
            "prevention_injected": True
        }
        
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"Failed to log enhancement: {e}", file=sys.stderr)

def main():
    """Main hook entry point"""
    # Read input from stdin
    input_data = sys.stdin.read()
    
    try:
        # Parse JSON input
        data = json.loads(input_data)
        
        # Initialize hook
        hook = HallucinationPreventionHook()
        
        # Process if it's a Task tool call
        if data.get('tool') == 'Task':
            data = hook.process_task_tool(data)
        
        # Output modified data
        print(json.dumps(data))
        
    except json.JSONDecodeError:
        # If not JSON, pass through unchanged
        print(input_data)
    except Exception as e:
        # Log error but don't break the pipeline
        print(f"Hallucination prevention hook error: {e}", file=sys.stderr)
        print(input_data)  # Pass through unchanged

if __name__ == "__main__":
    main()
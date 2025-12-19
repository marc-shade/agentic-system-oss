#!/usr/bin/env python3
"""
Delegation analyzer hook - Analyze requests for delegation requirements.
"""
import sys
import json
import re

def analyze_for_delegation(prompt):
    """Analyze if the request should be delegated to agents."""
    
    # Privacy-sensitive patterns (should go to Local Privacy Agent)
    privacy_patterns = [
        r'\b(ssn|social security)\b',
        r'\b(medical record|patient data|hipaa|phi)\b',
        r'\b(credit card|bank account|routing number)\b',
        r'\b(api key|password|secret|credential)\b',
        r'\b(confidential|proprietary|classified)\b',
        r'\b(employee record|hr data|salary)\b',
        r'\b(pii|gdpr|personal information)\b',
        r'\b(must stay local|cannot leave|air-gapped)\b',
        r'\b(sensitive|private|internal only)\b'
    ]
    
    # Implementation patterns (should be delegated to specialists)
    implementation_patterns = [
        r'\b(create|build|implement|develop|code|write)\b.*\b(function|class|component|api|server|app|website)\b',
        r'\b(fix|debug|refactor|optimize)\b.*\b(code|bug|performance|database)\b',
        r'\b(test|validate|verify)\b.*\b(code|system|api|functionality)\b',
        r'\b(design|architect)\b.*\b(system|database|api|infrastructure)\b',
        r'\b(deploy|configure|setup)\b.*\b(server|database|service|environment)\b'
    ]
    
    # Security patterns (should go to Security Specialist)
    security_patterns = [
        r'\b(security|vulnerability|penetration|audit)\b.*\b(test|review|assessment|scan)\b',
        r'\b(encrypt|decrypt|hash|authentication|authorization)\b',
        r'\b(compliance|gdpr|hipaa|sox|pci)\b'
    ]
    
    # Agent creation patterns (should go to Agent Builder)
    agent_patterns = [
        r'\b(create|build|design)\b.*\b(agent|bot|assistant)\b',
        r'\b(agent)\b.*\b(configuration|setup|template)\b'
    ]
    
    prompt_lower = prompt.lower()
    
    # Check for privacy-sensitive content
    for pattern in privacy_patterns:
        if re.search(pattern, prompt_lower):
            return {
                'should_delegate': True,
                'recommended_agent': '🔒 Local Privacy Agent',
                'reason': 'Privacy-sensitive content detected',
                'urgency': 'high'
            }
    
    # Check for agent creation
    for pattern in agent_patterns:
        if re.search(pattern, prompt_lower):
            return {
                'should_delegate': True,
                'recommended_agent': '🏗️ Agent Builder',
                'reason': 'Agent creation task detected',
                'urgency': 'medium'
            }
    
    # Check for security tasks
    for pattern in security_patterns:
        if re.search(pattern, prompt_lower):
            return {
                'should_delegate': True,
                'recommended_agent': '🦉 Security Specialist',
                'reason': 'Security-related task detected',
                'urgency': 'high'
            }
    
    # Check for implementation tasks
    for pattern in implementation_patterns:
        if re.search(pattern, prompt_lower):
            return {
                'should_delegate': True,
                'recommended_agent': '🐨 Swarm Coder',
                'reason': 'Implementation task detected',
                'urgency': 'medium'
            }
    
    return {
        'should_delegate': False,
        'recommended_agent': None,
        'reason': 'No delegation patterns detected',
        'urgency': 'low'
    }

def main():
    try:
        if len(sys.argv) < 2:
            sys.exit(0)
            
        user_prompt = sys.argv[1]
        analysis = analyze_for_delegation(user_prompt)
        
        if analysis['should_delegate']:
            print(f"🤖 Delegation Analysis:")
            print(f"   Recommended Agent: {analysis['recommended_agent']}")
            print(f"   Reason: {analysis['reason']}")
            print(f"   Urgency: {analysis['urgency']}")
            
            # Store analysis for orchestrator to use
            with open('/Users/marc/.claude/.delegation_analysis.json', 'w') as f:
                json.dump(analysis, f, indent=2)
        
        sys.exit(0)  # Always continue - this is informational only
        
    except Exception as e:
        print(f"Error in delegation analyzer: {e}", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()
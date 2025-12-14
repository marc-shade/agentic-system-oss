#!/usr/bin/env python3
"""
GPT-5 Strategic Routing Hook
Automatically routes backend/functional tasks to GPT-5 based on task analysis
"""

import re
import json

class GPT5Router:
    """Intelligent routing for GPT-5 optimal deployment"""
    
    # GPT-5 optimal use case keywords
    GPT5_KEYWORDS = [
        'backend', 'api', 'database', 'architecture', 'functional',
        'mvp', 'enterprise', 'business logic', 'crud', 'authentication',
        'authorization', 'migration', 'endpoint', 'rest', 'graphql',
        'microservice', 'integration', 'data processing', 'pipeline',
        'full-stack', 'server', 'routing', 'middleware', 'orm',
        'sql', 'nosql', 'redis', 'queue', 'worker', 'job',
        'validation', 'schema', 'model', 'controller', 'service'
    ]
    
    # UI/Frontend keywords (not GPT-5 optimal)
    UI_KEYWORDS = [
        'ui', 'ux', 'design', 'style', 'css', 'animation', 'visual',
        'color', 'typography', 'responsive', 'mobile', 'desktop',
        'component', 'widget', 'button', 'form styling', 'theme',
        'aesthetic', 'polish', 'beautify', 'layout', 'spacing',
        'hover', 'transition', 'gradient', 'shadow', 'icon'
    ]
    
    # Agent types that benefit from GPT-5
    GPT5_AGENTS = [
        'Backend Engineer', 'Backend Engineer (Native)', 
        'System Architect', 'BMAD Architect', 'Database Architect',
        'API Documentation Generator', 'MCP Builder',
        'Stack Master', 'DevOps Engineer'
    ]
    
    def __init__(self):
        self.stats = {
            'gpt5_deployments': 0,
            'standard_deployments': 0,
            'hybrid_workflows': 0
        }
    
    def analyze_task(self, task_description, agent_type=None):
        """
        Analyze task to determine if GPT-5 should be used
        
        Returns:
            dict: Routing decision with model and strategy
        """
        # Convert to lowercase for comparison
        desc_lower = task_description.lower() if task_description else ""
        agent_lower = agent_type.lower() if agent_type else ""
        
        # Count keyword matches
        gpt5_score = sum(1 for kw in self.GPT5_KEYWORDS if kw in desc_lower)
        ui_score = sum(1 for kw in self.UI_KEYWORDS if kw in desc_lower)
        
        # Check if agent type suggests GPT-5
        agent_suggests_gpt5 = any(
            agent.lower() in agent_lower 
            for agent in self.GPT5_AGENTS
        )
        
        # Decision logic
        use_gpt5 = False
        strategy = "standard"
        confidence = 0.5
        
        if gpt5_score > ui_score and gpt5_score >= 2:
            use_gpt5 = True
            strategy = "gpt5_functional"
            confidence = min(0.9, 0.5 + (gpt5_score * 0.1))
        elif agent_suggests_gpt5 and ui_score < 2:
            use_gpt5 = True
            strategy = "gpt5_agent_type"
            confidence = 0.8
        elif gpt5_score > 0 and ui_score > 0:
            # Mixed task - hybrid approach
            strategy = "hybrid"
            confidence = 0.7
        elif ui_score >= 2:
            strategy = "ui_specialist"
            confidence = 0.85
        
        # Build routing decision
        routing = {
            'use_gpt5': use_gpt5,
            'strategy': strategy,
            'confidence': confidence,
            'gpt5_score': gpt5_score,
            'ui_score': ui_score,
            'recommended_model': 'gpt-5' if use_gpt5 else 'claude-3.5-sonnet',
            'followup_agents': []
        }
        
        # Add followup agents for hybrid workflows
        if strategy == "gpt5_functional":
            routing['followup_agents'] = ['Frontend Specialist', 'UI Designer']
            self.stats['gpt5_deployments'] += 1
        elif strategy == "hybrid":
            routing['followup_agents'] = ['Backend Engineer (GPT-5)', 'Frontend Specialist']
            self.stats['hybrid_workflows'] += 1
        else:
            self.stats['standard_deployments'] += 1
        
        return routing
    
    def enhance_prompt_with_gpt5(self, original_prompt, routing_decision):
        """
        Enhance the agent prompt with GPT-5 specific instructions
        """
        if not routing_decision['use_gpt5']:
            return original_prompt
        
        gpt5_enhancement = """
[GPT-5 STRATEGIC DEPLOYMENT ACTIVE]
Model: GPT-5 (Optimized for functional completeness)
Focus: Backend architecture, functional logic, comprehensive implementation

GPT-5 STRENGTHS TO LEVERAGE:
- Complete functional implementation in single iteration
- Every button, form, and endpoint will work correctly
- Complex business logic and data processing
- Comprehensive error handling and validation
- Full API and database design

GPT-5 KNOWN LIMITATIONS (will be addressed by followup agents):
- Visual design and aesthetics (UI polish needed separately)
- Color schemes and styling (Frontend Specialist will enhance)
- Processing speed (accept trade-off for completeness)

YOUR MISSION: Build COMPLETE FUNCTIONAL FOUNDATION
- Focus on making everything WORK perfectly
- Ensure 100% functionality on all features
- Implement comprehensive business logic
- Create robust architecture that scales
- Don't worry about visual polish (handled separately)

"""
        
        # Add followup agent notice if hybrid workflow
        if routing_decision['followup_agents']:
            followup_notice = f"\nFOLLOWUP AGENTS READY: {', '.join(routing_decision['followup_agents'])}\n"
            gpt5_enhancement += followup_notice
        
        return gpt5_enhancement + "\n" + original_prompt
    
    def get_stats(self):
        """Get routing statistics"""
        return self.stats


def process_gpt5_routing(tool_args):
    """
    Process Task spawn for GPT-5 routing
    
    Args:
        tool_args: Arguments from Task tool call
        
    Returns:
        tuple: (enhanced_args, routing_decision)
    """
    router = GPT5Router()
    
    # Extract task details
    description = tool_args.get('description', '')
    prompt = tool_args.get('prompt', '')
    agent_type = tool_args.get('subagent_type', '')
    
    # Combine description and prompt for analysis
    full_context = f"{description} {prompt}"
    
    # Get routing decision
    routing = router.analyze_task(full_context, agent_type)
    
    # Enhance prompt if GPT-5 should be used
    if routing['use_gpt5']:
        enhanced_prompt = router.enhance_prompt_with_gpt5(prompt, routing)
        tool_args['prompt'] = enhanced_prompt
        
        # Add model hint to description
        tool_args['description'] = f"[GPT-5] {description}"
    
    return tool_args, routing


# Test function for verification
def test_routing():
    """Test GPT-5 routing logic"""
    test_cases = [
        {
            'description': 'Build REST API with authentication',
            'agent_type': 'Backend Engineer',
            'expected': 'gpt5'
        },
        {
            'description': 'Design beautiful landing page with animations',
            'agent_type': 'Frontend Specialist',
            'expected': 'claude'
        },
        {
            'description': 'Create full-stack MVP with database and UI',
            'agent_type': 'Swarm Coder',
            'expected': 'hybrid'
        },
        {
            'description': 'Implement microservices architecture',
            'agent_type': 'System Architect',
            'expected': 'gpt5'
        }
    ]
    
    router = GPT5Router()
    results = []
    
    for test in test_cases:
        routing = router.analyze_task(test['description'], test['agent_type'])
        result = {
            'test': test['description'],
            'expected': test['expected'],
            'got': 'gpt5' if routing['use_gpt5'] else ('hybrid' if routing['strategy'] == 'hybrid' else 'claude'),
            'passed': False
        }
        
        if test['expected'] == 'gpt5' and routing['use_gpt5']:
            result['passed'] = True
        elif test['expected'] == 'claude' and not routing['use_gpt5'] and routing['strategy'] != 'hybrid':
            result['passed'] = True
        elif test['expected'] == 'hybrid' and routing['strategy'] == 'hybrid':
            result['passed'] = True
        
        results.append(result)
    
    return results


if __name__ == "__main__":
    # Run tests
    print("Testing GPT-5 Routing Logic...")
    results = test_routing()
    for r in results:
        status = "✓" if r['passed'] else "✗"
        print(f"{status} {r['test']}: Expected {r['expected']}, Got {r['got']}")
    
    # Show stats
    router = GPT5Router()
    print(f"\nRouting Stats: {router.get_stats()}")
#!/usr/bin/env python3
"""
Agent spawn validator hook - Validate agent spawning and context optimization.
"""
import sys
import json
import re

def validate_agent_spawn(params, result):
    """Validate agent spawning for proper configuration and context optimization."""
    
    try:
        # Parse parameters
        if isinstance(params, str):
            if params.startswith('{'):
                params_dict = json.loads(params)
            else:
                params_dict = {'description': params}
        else:
            params_dict = params
    except:
        params_dict = {'description': str(params)}
    
    description = params_dict.get('description', '')
    subagent_type = params_dict.get('subagent_type', '')
    
    validation_results = {
        'agent_type_valid': False,
        'context_optimized': False,
        'proper_delegation': False,
        'memory_integration': False,
        'warnings': [],
        'recommendations': []
    }
    
    # Valid agent types from the ecosystem
    valid_agents = [
        '🏗️ Agent Builder', '🎛️ Self Admin', '🦉 Swarm Queen',
        '🐨 Swarm Coder', '🐸 Frontend Specialist', '🐻 Backend Engineer',
        '🏗️ System Architect', '🏗️ Stack Master', '💻 Frontend Engineer',
        '💻 Backend Engineer (Native)', '📱 Mobile UI Implementer',
        '📱 Mobile UX Engineer', '🔧 MCP Builder', '🔧 BMAD Analyst (Mary)',
        '🔧 BMAD Product Manager (John)', '🔧 BMAD Architect (Winston)',
        '🔒 Local Privacy Agent', '🦎 Security Specialist', '🦋 Swarm Guardian',
        '🐢 Swarm Tester', '🦎 Swarm Reviewer', '🔍 Reverse Engineer',
        '🛠️ System Detective', '🔬 Code Archaeologist', '🎛️ Configuration Specialist',
        '🦆 Swarm Analyst', '🐙 Swarm Researcher', '🐺 Swarm Scout',
        '🦅 Performance Optimizer', '🪶 Documentation Scribe',
        '🦆 Swarm Coordinator', '🦌 Swarm Monitor', '🦎 Report Compiler',
        '🎨 Image Generator', '🐰 Flow Diagram Visualizer', '🎭 Whimsy Injector'
    ]
    
    # Check if agent type is valid
    if subagent_type in valid_agents:
        validation_results['agent_type_valid'] = True
    else:
        validation_results['warnings'].append(f"Unknown agent type: {subagent_type}")
        validation_results['recommendations'].append("Use a recognized agent from the ecosystem")
    
    # Check for proper delegation patterns
    delegation_keywords = [
        'implement', 'develop', 'code', 'build', 'create', 'design',
        'test', 'validate', 'analyze', 'research', 'document'
    ]
    
    if any(keyword in description.lower() for keyword in delegation_keywords):
        validation_results['proper_delegation'] = True
    else:
        validation_results['warnings'].append("Task description lacks clear delegation purpose")
    
    # Check for context optimization
    context_indicators = [
        'memory-aware', 'timestamp verification', 'sequential thinking',
        'mcp coordination', 'batch operations', 'resource monitoring'
    ]
    
    if any(indicator in description.lower() for indicator in context_indicators):
        validation_results['context_optimized'] = True
    else:
        validation_results['recommendations'].append("Consider adding context optimization keywords")
    
    # Check for memory integration
    memory_indicators = [
        'enhanced-memory-mcp', 'create_entities', 'memory integration',
        'knowledge building', 'pattern recognition'
    ]
    
    if any(indicator in description.lower() for indicator in memory_indicators):
        validation_results['memory_integration'] = True
    else:
        validation_results['recommendations'].append("Consider integrating with enhanced-memory-mcp")
    
    # Output validation results
    if validation_results['warnings']:
        print("⚠️  AGENT SPAWN VALIDATION WARNINGS:")
        for warning in validation_results['warnings']:
            print(f"   - {warning}")
    
    if validation_results['recommendations']:
        print("💡 RECOMMENDATIONS:")
        for rec in validation_results['recommendations']:
            print(f"   - {rec}")
    
    # Check for context window optimization
    context_length = len(description)
    if context_length > 50000:
        print(f"📊 CONTEXT WARNING: Large context detected ({context_length} chars)")
        print("   Consider using context management optimization")
        validation_results['recommendations'].append("Apply context optimization")
    
    # Success indicators
    success_score = sum([
        validation_results['agent_type_valid'],
        validation_results['proper_delegation'],
        validation_results['context_optimized'],
        validation_results['memory_integration']
    ])
    
    if success_score >= 3:
        print("✅ Agent spawn validation passed")
    elif success_score >= 2:
        print("⚠️  Agent spawn validation passed with recommendations")
    else:
        print("❌ Agent spawn validation needs improvement")
    
    # Log validation for improvement
    log_entry = {
        'agent_type': subagent_type,
        'validation_results': validation_results,
        'success_score': success_score,
        'description_length': context_length
    }
    
    with open('/Users/marc/.claude/.agent_spawn_validations.log', 'a') as f:
        f.write(json.dumps(log_entry) + '\n')
    
    return validation_results

def main():
    try:
        if len(sys.argv) < 3:
            sys.exit(0)
            
        params = sys.argv[1]
        result = sys.argv[2]
        
        validate_agent_spawn(params, result)
        sys.exit(0)  # This is informational only
        
    except Exception as e:
        print(f"Error in agent spawn validator: {e}", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()
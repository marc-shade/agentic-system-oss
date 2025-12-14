#!/usr/bin/env python3
"""
Permission validator hook - Validate tool permissions.
"""
import sys
import json
from datetime import datetime

def validate_tool_permission(tool_name):
    """Validate tool permissions based on delegation rules."""
    
    # Load current permission rules
    permission_rules = {
        'always_allowed': [
            'Read', 'LS', 'Grep', 'Glob', 'WebSearch', 'WebFetch'
        ],
        'delegation_required': [
            'Write', 'Edit', 'MultiEdit', 'Bash'
        ],
        'agent_only': [
            'Task'  # Only orchestrator can spawn agents
        ],
        'mcp_tools': [
            'mcp__enhanced-memory-mcp__', 'mcp__claude-flow__', 'mcp__unified-voice-mcp__'
        ]
    }
    
    validation_result = {
        'tool_name': tool_name,
        'allowed': False,
        'requires_delegation': False,
        'reason': '',
        'recommendations': []
    }
    
    # Check always allowed tools
    if tool_name in permission_rules['always_allowed']:
        validation_result['allowed'] = True
        validation_result['reason'] = 'Tool always allowed'
        return validation_result
    
    # Check MCP tools
    for mcp_prefix in permission_rules['mcp_tools']:
        if tool_name.startswith(mcp_prefix):
            validation_result['allowed'] = True
            validation_result['reason'] = 'MCP tool allowed'
            return validation_result
    
    # Check agent spawning (only orchestrator)
    if tool_name in permission_rules['agent_only']:
        # Determine if this is being called by orchestrator
        try:
            # Check if we're in orchestrator context
            with open('/Users/marc/.claude/.current_role.json', 'r') as f:
                role_data = json.load(f)
                current_role = role_data.get('role', 'unknown')
        except:
            current_role = 'unknown'
        
        if current_role == 'orchestrator':
            validation_result['allowed'] = True
            validation_result['reason'] = 'Agent spawning allowed for orchestrator'
        else:
            validation_result['allowed'] = False
            validation_result['requires_delegation'] = True
            validation_result['reason'] = 'Agent spawning restricted to orchestrator'
            validation_result['recommendations'].append('Request agent spawn through orchestrator')
        
        return validation_result
    
    # Check delegation required tools
    if tool_name in permission_rules['delegation_required']:
        validation_result['allowed'] = False
        validation_result['requires_delegation'] = True
        validation_result['reason'] = 'Implementation tool requires delegation'
        validation_result['recommendations'].extend([
            'Use Task() to spawn appropriate specialist agent',
            'Consider using agent for implementation tasks',
            'Follow delegation enforcement protocols'
        ])
        return validation_result
    
    # Unknown tool - default to cautious approach
    validation_result['allowed'] = False
    validation_result['reason'] = 'Unknown tool - requires validation'
    validation_result['recommendations'].append('Verify tool is in allowed list')
    
    return validation_result

def main():
    try:
        if len(sys.argv) < 2:
            sys.exit(0)
            
        tool_name = sys.argv[1]
        result = validate_tool_permission(tool_name)
        
        if not result['allowed']:
            print(f"🔒 PERMISSION DENIED: {tool_name}")
            print(f"   Reason: {result['reason']}")
            
            if result['requires_delegation']:
                print("   🤖 DELEGATION REQUIRED")
            
            if result['recommendations']:
                print("   💡 Recommendations:")
                for rec in result['recommendations']:
                    print(f"     - {rec}")
            
            # Log permission denial
            denial_log = {
                'timestamp': datetime.now().isoformat(),
                'tool_name': tool_name,
                'reason': result['reason'],
                'requires_delegation': result['requires_delegation']
            }
            
            with open('/Users/marc/.claude/.permission_denials.log', 'a') as f:
                f.write(json.dumps(denial_log) + '\n')
            
            sys.exit(2)  # Block the tool
        
        else:
            print(f"✅ Permission granted: {tool_name}")
            sys.exit(0)  # Allow the tool
        
    except Exception as e:
        print(f"Error in permission validator: {e}", file=sys.stderr)
        sys.exit(0)  # Allow on error to prevent system lock

if __name__ == "__main__":
    main()
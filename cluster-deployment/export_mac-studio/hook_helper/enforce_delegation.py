#!/usr/bin/env python3
"""
Delegation Enforcement Hook
Blocks direct implementation attempts and suggests appropriate agents
"""
import sys
import json
import re

def should_block_tool(tool_name, params):
    """Check if tool usage violates delegation rules"""
    
    # Tools that are always blocked for orchestrator
    BLOCKED_TOOLS = {'Write', 'Edit', 'MultiEdit'}
    
    if tool_name in BLOCKED_TOOLS:
        return True, "Direct file modification"
    
    # Check Bash commands for code patterns
    if tool_name == 'Bash':
        try:
            params_dict = json.loads(params) if isinstance(params, str) else params
            command = params_dict.get('command', '')
            
            # Patterns that indicate direct implementation
            code_patterns = [
                r'npm install', r'pip install', r'yarn add',
                r'git init', r'git clone',
                r'python.*\.py', r'node.*\.js',
                r'CREATE TABLE', r'INSERT INTO',
                r'docker build', r'docker run'
            ]
            
            for pattern in code_patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    return True, f"Command contains implementation pattern: {pattern}"
                    
        except Exception:
            pass
    
    return False, None

def suggest_agent(violation_type):
    """Suggest appropriate agent based on violation type"""
    
    suggestions = {
        "Direct file modification": [
            "🐨 Swarm Coder - For general implementation",
            "🐸 Frontend Specialist - For UI/frontend work",
            "🐻 Backend Engineer - For server/API work"
        ],
        "npm install": ["🐸 Frontend Specialist", "💻 Frontend Engineer (Native)"],
        "pip install": ["🐻 Backend Engineer", "🐍 Python Developer"],
        "git": ["🐹 DevOps Engineer", "🐘 Swarm DevOps"],
        "python": ["🐻 Backend Engineer", "🐍 Python Developer"],
        "node": ["🐻 Backend Engineer (Native)", "🐸 Frontend Specialist"],
        "CREATE TABLE": ["🗄️ Database Architect", "🐻 Backend Engineer"],
        "docker": ["🐹 DevOps Engineer", "🐘 Swarm DevOps"]
    }
    
    for key, agents in suggestions.items():
        if key.lower() in violation_type.lower():
            return agents
    
    return ["🐨 Swarm Coder", "🦉 Swarm Queen"]

def main():
    if len(sys.argv) < 3:
        # Allow if no params provided
        print(json.dumps({"allow": True}))
        return
    
    tool_name = sys.argv[1]
    params = sys.argv[2] if len(sys.argv) > 2 else "{}"
    
    should_block, reason = should_block_tool(tool_name, params)
    
    if should_block:
        suggested_agents = suggest_agent(reason)
        
        response = {
            "allow": False,
            "message": f"🚫 DELEGATION REQUIRED: {reason}\n\nSuggested agents:\n" + 
                      "\n".join(f"  • {agent}" for agent in suggested_agents) +
                      "\n\nUse Task tool to spawn the appropriate agent."
        }
    else:
        response = {"allow": True}
    
    print(json.dumps(response))

if __name__ == "__main__":
    main()
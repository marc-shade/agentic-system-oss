#!/usr/bin/env python3
"""
Bash command validator hook - Validate bash commands for delegation violations.
"""
import sys
import json
import re

def validate_bash_command(params):
    """Validate bash command for potential delegation violations."""
    
    try:
        # Parse params if it's JSON
        if isinstance(params, str):
            if params.startswith('{'):
                params_dict = json.loads(params)
                command = params_dict.get('command', '')
            else:
                command = params
        else:
            command = str(params)
    except:
        command = str(params)
    
    command_lower = command.lower()
    
    # Implementation/coding patterns that should be delegated
    blocked_patterns = [
        r'\b(npm install|yarn add|pip install)\b',  # Package installation
        r'\b(git init|git clone)\b.*\b(new project|repository)\b',  # New project setup
        r'\b(create|mkdir).*\b(app|project|service)\b',  # Project creation
        r'\b(docker build|docker run)\b.*\b(new|create)\b',  # Docker operations
        r'\b(rails new|vue create|create-react-app)\b',  # Framework scaffolding
        r'\b(terraform init|terraform apply)\b',  # Infrastructure deployment
    ]
    
    # Sensitive operations that need approval
    sensitive_patterns = [
        r'\b(rm -rf|sudo rm)\b',  # Dangerous deletions
        r'\b(chmod 777|chmod -R 777)\b',  # Overly permissive permissions  
        r'\b(curl|wget).*\b(install|setup)\b.*\b(sh|bash)\b',  # Remote script execution
        r'\b(sudo)\b.*\b(install|remove|purge)\b',  # System modifications
        r'\b(passwd|usermod|userdel)\b',  # User management
    ]
    
    # Check for blocked patterns
    for pattern in blocked_patterns:
        if re.search(pattern, command_lower):
            print(f"🚫 BLOCKED: This command involves implementation/setup tasks")
            print(f"   Command: {command}")
            print(f"   Reason: Implementation tasks should be delegated to appropriate agents")
            print(f"   Recommendation: Use Task() to spawn a specialist agent")
            sys.exit(2)  # Block the command
    
    # Check for sensitive patterns - require confirmation
    for pattern in sensitive_patterns:
        if re.search(pattern, command_lower):
            print(f"⚠️  CAUTION: Potentially dangerous command detected")
            print(f"   Command: {command}")
            print(f"   This command will be logged for security review")
            
            # Log the command
            with open('/home/marc/.claude/.sensitive_commands.log', 'a') as f:
                f.write(f"{command}\n")
            
            # Continue but warn
            break
    
    # Check command length (prevent tool name length violations)
    if len(command) > 1000:
        print(f"⚠️  WARNING: Very long command detected ({len(command)} chars)")
        print("   Consider breaking into smaller commands")
    
    sys.exit(0)  # Allow command to proceed

def main():
    try:
        if len(sys.argv) < 2:
            sys.exit(0)
            
        params = sys.argv[1]
        validate_bash_command(params)
        
    except Exception as e:
        print(f"Error in bash validator: {e}", file=sys.stderr)
        sys.exit(0)  # Allow command on error

if __name__ == "__main__":
    main()
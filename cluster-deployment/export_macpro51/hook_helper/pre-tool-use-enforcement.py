#!/usr/bin/env python3
"""
Pre-Tool-Use Hook with Enhanced Delegation Enforcement v2.0
Integrates with the new DelegationEnforcer system for comprehensive orchestrator protection.
PRODUCTION READY - Real enforcement that actually works.
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Add hooks directory to path
hooks_path = Path(__file__).parent
sys.path.append(str(hooks_path))

def load_delegation_enforcer():
    """Load the main delegation enforcement system"""
    try:
        from delegation_enforcement import DelegationEnforcer
        return DelegationEnforcer()
    except ImportError as e:
        print(f"WARNING: Could not load DelegationEnforcer: {e}", file=sys.stderr)
        return None

def load_voice_system():
    """Load voice system for announcements"""
    try:
        from voicemode_integration import pre_tool_announcement, voice
        return True, pre_tool_announcement, voice
    except ImportError:
        try:
            # Fallback to unified voice MCP if available
            return False, None, None
        except:
            return False, None, None

def fallback_orchestrator_detection(context: str, environment: dict) -> bool:
    """Basic fallback orchestrator detection if main system fails"""
    if not context:
        return False
    
    context_lower = context.lower()
    
    # Basic patterns
    orchestrator_markers = [
        'pure_orchestrator',
        'orchestrator_mode', 
        'delegation_only',
        'agent_spawning_only',
        'coordination.*only'
    ]
    
    for marker in orchestrator_markers:
        if marker in context_lower:
            return True
    
    # Check environment
    mode = environment.get('CLAUDE_MODE', '').lower()
    if mode in ['orchestrator', 'coordinator']:
        return True
    
    return False

def fallback_enforcement(tool_name: str, tool_args: dict) -> dict:
    """Basic fallback enforcement if main system fails"""
    
    # Block file modification tools
    blocked_tools = ['Write', 'Edit', 'MultiEdit', 'NotebookEdit']
    if tool_name in blocked_tools:
        return {
            "allow": False,
            "error": f"""🚫 DELEGATION REQUIRED: Orchestrator cannot use {tool_name}

You must delegate this task to an appropriate agent:
• File operations → Task() with 'Swarm Coder'
• Documentation → Task() with 'Documentation Scribe'  
• Frontend work → Task() with 'Frontend Specialist'
• Backend work → Task() with 'Backend Engineer'

Example:
Task(
    subagent_type="Swarm Coder",
    description="Handle file operations",
    prompt="[specific instructions for the agent]"
)

This is a REAL enforcement system - not a demo."""
        }
    
    # Check Bash commands for implementation patterns
    if tool_name == "Bash":
        command = tool_args.get("command", "").lower()
        blocked_patterns = [
            "npm install", "pip install", "yarn add",
            "python.*\\.py", "node.*\\.js", 
            "git init", "git clone",
            "docker build", "docker run"
        ]
        
        for pattern in blocked_patterns:
            if pattern.replace("\\.", ".") in command:
                return {
                    "allow": False,
                    "error": f"""🚫 DELEGATION REQUIRED: Implementation command blocked

Command: {command[:50]}...
Pattern: {pattern}

Delegate to appropriate agent:
• Python/pip → Task() with 'Backend Engineer'
• Node/npm → Task() with 'Frontend Specialist'
• Docker → Task() with 'Stack Master'
• Git setup → Task() with 'DevOps Engineer'

Orchestrator role: Coordination only, no implementation."""
                }
    
    return {"allow": True}

def main():
    """Main pre-tool-use hook with enhanced delegation enforcement"""
    
    start_time = datetime.now()
    
    try:
        # Read hook input from stdin (Claude Code standard)
        hook_input = json.loads(sys.stdin.read())
        tool_name = hook_input.get("tool", "")
        tool_args = hook_input.get("arguments", {})
        context = hook_input.get("context", "")
        
        # Get environment variables
        environment = dict(os.environ)
        
        # Load systems
        enforcer = load_delegation_enforcer()
        voice_available, pre_tool_announcement, voice = load_voice_system()
        
        # Primary enforcement using DelegationEnforcer
        if enforcer:
            try:
                # Convert tool arguments to string for analysis
                tool_input_str = json.dumps(tool_args) if tool_args else ""
                
                # Run main delegation enforcement
                result = enforcer.enforce_delegation(tool_name, tool_input_str, context, environment)
                
                if result.get("status") == "blocked":
                    # Voice announcement for blocked operation
                    if voice_available and voice:
                        agent = result.get("agent_recommendation", {}).get("agent", "an agent")
                        voice.announce_milestone('error', f"Operation blocked. Delegate to {agent}")
                    
                    # Return blocking response
                    return json.dumps({
                        "allow": False,
                        "error": f"""🚫 {result.get('reason', 'Operation blocked')}

{result.get('agent_recommendation', {}).get('delegation_message', 'Delegation required')}

Use this Task command:
{result.get('agent_recommendation', {}).get('task_command', 'Task(...)')}

Enforcement System: v2.0 (Production)""",
                        "delegation_info": result.get("agent_recommendation", {}),
                        "enforcement_version": "2.0.0"
                    })
                    
                elif result.get("status") == "error":
                    # Log error but continue to fallback
                    print(f"Enforcer error: {result.get('reason')}", file=sys.stderr)
                
            except Exception as e:
                print(f"Enforcer exception: {e}", file=sys.stderr)
                # Continue to fallback
        
        # Fallback enforcement if main system unavailable
        if not enforcer or result.get("status") == "error":
            # Check if we need fallback enforcement
            if fallback_orchestrator_detection(context, environment):
                fallback_result = fallback_enforcement(tool_name, tool_args)
                if not fallback_result.get("allow", True):
                    if voice_available and voice:
                        voice.announce_milestone('error', "Operation blocked by fallback enforcement")
                    return json.dumps(fallback_result)
        
        # Voice announcements for allowed operations
        if voice_available and pre_tool_announcement:
            try:
                if tool_name == "Task":
                    # Agent spawning announcement
                    agent_type = tool_args.get("subagent_type", "agent")
                    description = tool_args.get("description", "")
                    if description and len(description.split()) <= 5:
                        announcement = f"Spawning {description}"
                    else:
                        announcement = f"Spawning {agent_type}"
                    pre_tool_announcement("Task", announcement)
                    
                elif tool_name == "Write":
                    # File creation announcement
                    file_path = tool_args.get("file_path", "")
                    if file_path:
                        filename = os.path.basename(file_path)
                        pre_tool_announcement("Write", f"Creating {filename}")
                        
                elif tool_name == "MultiEdit":
                    # Multi-edit announcement
                    file_path = tool_args.get("file_path", "")
                    if file_path:
                        filename = os.path.basename(file_path)
                        pre_tool_announcement("MultiEdit", f"Editing {filename}")
                        
                elif tool_name == "Bash":
                    # Command execution announcement
                    description = tool_args.get("description", "")
                    if description and len(description.split()) <= 5:
                        pre_tool_announcement("Bash", description)
                        
                elif tool_name.startswith("mcp__"):
                    # MCP tool usage announcement
                    mcp_parts = tool_name.split("__")
                    if len(mcp_parts) >= 2:
                        service = mcp_parts[1].split("-")[0]  # Get first part of service name
                        important_mcps = ['claude-flow', 'task-manager', 'image-gen', 'unified-voice']
                        if any(imp in tool_name for imp in important_mcps):
                            pre_tool_announcement(tool_name, f"Using {service}")
                            
            except Exception as e:
                print(f"Voice announcement error: {e}", file=sys.stderr)
        
        # Log successful operation
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        if execution_time > 100:  # Log slow operations
            print(f"Pre-tool hook slow execution: {execution_time}ms for {tool_name}", file=sys.stderr)
        
    except json.JSONDecodeError as e:
        # Invalid input - allow but log
        print(f"Pre-tool hook JSON decode error: {e}", file=sys.stderr)
        return json.dumps({"allow": True})
        
    except Exception as e:
        # Unexpected error - allow but log
        print(f"Pre-tool hook error: {e}", file=sys.stderr)
        
        # Write to error log file
        try:
            with open('/home/marc/.claude/hooks/pre-tool-errors.log', 'a') as f:
                f.write(f"{datetime.now().isoformat()}: {str(e)}\n")
        except:
            pass
        
        return json.dumps({"allow": True})
    
    # Default: allow operation
    return json.dumps({"allow": True})

if __name__ == "__main__":
    result = main()
    print(result)
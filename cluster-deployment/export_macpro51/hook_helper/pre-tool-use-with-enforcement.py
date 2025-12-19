#!/usr/bin/env python3
"""
Pre-Tool-Use Hook with Delegation Enforcement and VoiceMode Integration
Actually enforces orchestrator restrictions (finally!)
"""

import json
import sys
import os

# Add hooks directory to path
sys.path.append('/home/marc/.claude/hooks')

# Check if we're in orchestrator mode
def is_orchestrator_mode():
    """Detect if Claude is acting as orchestrator"""
    # Check environment variable
    if os.getenv('CLAUDE_MODE') == 'orchestrator':
        return True
    
    # Check for orchestrator markers in recent context
    context_file = '/home/marc/.claude/context/current_mode.txt'
    if os.path.exists(context_file):
        with open(context_file, 'r') as f:
            mode = f.read().strip()
            if mode == 'orchestrator':
                return True
                
    # Default to not enforcing (to avoid breaking existing workflows)
    return False

def main():
    """Main hook handler with enforcement"""
    try:
        # Read hook input
        hook_input = json.loads(sys.stdin.read())
        
        tool_name = hook_input.get("tool", "")
        tool_args = hook_input.get("arguments", {})
        
        # Import voice integration (may fail, that's ok)
        try:
            from voicemode_integration import pre_tool_announcement, voice
            voice_available = True
        except:
            voice_available = False
            
        # DELEGATION ENFORCEMENT
        if is_orchestrator_mode():
            # These tools are BLOCKED for orchestrator
            blocked_tools = ['Write', 'Edit', 'MultiEdit', 'NotebookEdit']
            
            if tool_name in blocked_tools:
                error_msg = f"""DELEGATION REQUIRED: Orchestrator cannot use {tool_name}

You must delegate this task to an appropriate agent:
- File creation/editing → Use Task() with 'Swarm Coder' or specific implementation agent
- Documentation → Use Task() with 'Documentation Scribe'
- Configuration → Use Task() with 'System Architect'

Example:
Task(
    subagent_type="Swarm Coder",
    description="Implement file changes",
    prompt="[specific instructions]"
)

Industry Note: Even with proper delegation, expect /home/marc40% success rate (MCP Universe Benchmark)"""
                
                if voice_available:
                    voice.announce_milestone('error', f"Delegation required for {tool_name}")
                    
                # ACTUALLY BLOCK THE TOOL
                return json.dumps({
                    "allow": False,
                    "error": error_msg
                })
                
            # Check Bash commands for implementation work
            if tool_name == "Bash":
                command = tool_args.get("command", "").lower()
                # Block code execution commands
                blocked_commands = ['python', 'node', 'npm run', 'cargo', 'go run', 'make']
                for blocked in blocked_commands:
                    if blocked in command and 'test' not in command:
                        error_msg = f"""DELEGATION REQUIRED: Orchestrator cannot execute code

Command blocked: {command[:50]}...

Delegate to appropriate agent:
- Python execution → Task() with 'Backend Engineer'
- Node/npm → Task() with 'Frontend Specialist'
- Testing → Task() with 'Swarm Tester'

Note: Orchestrator can run diagnostic commands (ls, grep, ps) but not implementation"""
                        
                        if voice_available:
                            voice.announce_milestone('error', "Code execution requires delegation")
                            
                        return json.dumps({
                            "allow": False,
                            "error": error_msg
                        })
        
        # VOICE ANNOUNCEMENTS (if not blocked)
        if voice_available:
            if tool_name == "Task":
                # Agent spawning - important announcement
                agent_type = tool_args.get("subagent_type", "agent")
                description = tool_args.get("description", "")
                if description and len(description.split()) <= 5:
                    announcement = f"Spawning {description}"
                else:
                    announcement = f"Spawning {agent_type}"
                pre_tool_announcement("Task", announcement)
                
            elif tool_name == "Write":
                # File creation
                file_path = tool_args.get("file_path", "")
                if file_path:
                    filename = os.path.basename(file_path)
                    pre_tool_announcement("Write", f"Creating {filename}")
                    
            elif tool_name == "MultiEdit":
                # Multiple edits
                file_path = tool_args.get("file_path", "")
                if file_path:
                    filename = os.path.basename(file_path)
                    pre_tool_announcement("MultiEdit", f"Editing {filename}")
                    
            elif tool_name == "Bash":
                # Command execution
                description = tool_args.get("description", "")
                if description and len(description.split()) <= 5:
                    pre_tool_announcement("Bash", description)
                    
            elif tool_name.startswith("mcp__"):
                # MCP tool usage
                mcp_parts = tool_name.split("__")
                if len(mcp_parts) >= 2:
                    service = mcp_parts[1].split("_")[0]
                    important_mcps = ['claude-flow', 'task-manager', 'image-gen']
                    if any(imp in tool_name for imp in important_mcps):
                        pre_tool_announcement(tool_name, f"Using {service}")
        
    except Exception as e:
        # On error, allow tool but log
        with open('/home/marc/.claude/hooks/pre-tool-errors.log', 'a') as f:
            f.write(f"Error in pre-tool hook: {e}\n")
        return json.dumps({"allow": True})
    
    # Default: allow tool to proceed
    return json.dumps({"allow": True})

if __name__ == "__main__":
    result = main()
    print(result)
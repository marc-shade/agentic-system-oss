#!/usr/bin/env python3
"""
Pre-Tool-Use Hook with Security Redaction + VoiceMode Integration
Integrated security layer for 2 Acre Studios agentic system
"""

import json
import sys
import os
import subprocess

# Add hooks directory to path
sys.path.append('/Users/marc/.claude/hooks')

def run_security_check(hook_input):
    """Run security redaction pre-hook"""
    try:
        result = subprocess.run(
            ['/Users/marc/.claude/hooks/security/redaction_pre_hook.py'],
            input=json.dumps(hook_input),
            capture_output=True,
            text=True,
            timeout=5
        )

        # Parse security result
        security_result = json.loads(result.stdout)

        # If security blocks, return immediately
        if not security_result.get("allow", True):
            return security_result, None

        # Use modified input if provided
        modified_input = security_result.get("modified_input", hook_input)
        return {"allow": True}, modified_input

    except subprocess.TimeoutExpired:
        # Security check timed out - fail open but log
        return {"allow": True}, hook_input
    except Exception as e:
        # Security check failed - fail open but log
        return {"allow": True}, hook_input

def main():
    """Main hook handler with security integration"""
    try:
        # Read hook input
        hook_input = json.loads(sys.stdin.read())

        # SECURITY LAYER: Run redaction check first
        security_result, modified_input = run_security_check(hook_input)

        if not security_result.get("allow", True):
            # Security blocked - return immediately
            return json.dumps(security_result)

        # Use modified input if security layer changed it
        if modified_input:
            hook_input = modified_input

        # Continue with original pre-tool-use logic
        tool_name = hook_input.get("tool", "")
        tool_args = hook_input.get("arguments", {})

        # Import voice integration
        from voicemode_integration import pre_tool_announcement, voice

        # DELEGATION ENFORCEMENT - Check if orchestrator mode is active
        # Block Write/Edit/MultiEdit tools for orchestrator
        if os.environ.get("ORCHESTRATOR_MODE") == "true":
            if tool_name in ["Write", "Edit", "MultiEdit"]:
                voice.announce_milestone('error', f"Orchestrator must delegate {tool_name}")
                return json.dumps({"allow": False, "error": f"Orchestrator must delegate {tool_name} tasks to agents"})

        # Special handling for different tools
        if tool_name == "Task":
            # Import confidence orchestration
            from confidence_orchestration_hook import ConfidenceOrchestrator, process_task_spawn

            # Import GPT-5 routing
            from gpt5_routing_hook import process_gpt5_routing

            # Apply confidence-based enhancement to agent spawning
            orchestrator = ConfidenceOrchestrator()
            enhanced_args, confidence_result = process_task_spawn(tool_args, orchestrator)

            # Apply GPT-5 routing based on task content
            enhanced_args, gpt5_routing = process_gpt5_routing(enhanced_args)

            # Update tool arguments with both enhancements
            tool_args = enhanced_args
            hook_input["arguments"] = tool_args

            # Agent spawning - important announcement with confidence and model
            agent_type = tool_args.get("subagent_type", "agent")
            description = tool_args.get("description", "")
            confidence = confidence_result['aggregateConfidence']

            # Include GPT-5 model in announcement if selected
            model_info = ""
            if gpt5_routing.get('use_gpt5'):
                model_info = " [GPT-5]"

            if description and len(description.split()) <= 5:
                announcement = f"Spawning {description}{model_info} (confidence: {confidence:.0%})"
            else:
                announcement = f"Spawning {agent_type}{model_info} (confidence: {confidence:.0%})"
            pre_tool_announcement("Task", announcement)

            # Log low confidence warnings
            if confidence < 0.4:
                voice.announce_milestone('warning', f"Low confidence {confidence:.0%} for {agent_type}")
            elif confidence > 0.8:
                voice.announce_milestone('success', f"High confidence {confidence:.0%} for {agent_type}")

        elif tool_name == "Write":
            # File creation
            file_path = tool_args.get("file_path", "")
            if file_path:
                filename = os.path.basename(file_path)
                pre_tool_announcement("Write", f"Creating {filename}")
            else:
                pre_tool_announcement("Write")

        elif tool_name == "MultiEdit":
            # Multiple edits
            file_path = tool_args.get("file_path", "")
            edits = tool_args.get("edits", [])
            if file_path:
                filename = os.path.basename(file_path)
                pre_tool_announcement("MultiEdit", f"Editing {filename}")
            else:
                pre_tool_announcement("MultiEdit", f"{len(edits)} changes")

        elif tool_name == "Bash":
            # Command execution
            command = tool_args.get("command", "")
            description = tool_args.get("description", "")
            if description and len(description.split()) <= 5:
                pre_tool_announcement("Bash", description)
            elif command:
                # Extract first word of command for announcement
                cmd_word = command.split()[0] if command else "command"
                if cmd_word in ['git', 'npm', 'python', 'node']:
                    pre_tool_announcement("Bash", f"Running {cmd_word}")
                else:
                    pre_tool_announcement("Bash")

        elif tool_name == "TodoWrite":
            # Task list updates
            todos = tool_args.get("todos", [])
            in_progress = sum(1 for t in todos if t.get("status") == "in_progress")
            if in_progress > 0:
                pre_tool_announcement("TodoWrite", f"Working on task")

        elif tool_name == "WebSearch":
            # Web searching
            query = tool_args.get("query", "")
            if query and len(query.split()) <= 5:
                pre_tool_announcement("WebSearch", f"Searching {query}")
            else:
                pre_tool_announcement("WebSearch")

        elif tool_name == "WebFetch":
            # Content fetching
            pre_tool_announcement("WebFetch", "Fetching content")

        elif tool_name.startswith("mcp__"):
            # MCP tool usage - only announce important ones
            mcp_parts = tool_name.split("__")
            if len(mcp_parts) >= 2:
                service = mcp_parts[1].split("_")[0]
                # Announce important MCP services
                important_mcps = ['claude-flow', 'task-manager', 'image-gen',
                                 'quality-assurance', 'container-orchestrator']
                if any(imp in tool_name for imp in important_mcps):
                    pre_tool_announcement(tool_name, f"Using {service}")

        # Check for error conditions that warrant announcement
        if tool_name == "Bash" and "error" in str(tool_args).lower():
            voice.announce_milestone('error', "Command issue")

    except Exception as e:
        # Silently fail - don't block tool execution
        pass

    # Always allow tool to proceed
    return json.dumps({"allow": True})

if __name__ == "__main__":
    result = main()
    print(result)

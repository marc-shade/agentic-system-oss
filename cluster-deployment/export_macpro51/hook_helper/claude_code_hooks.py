#!/usr/bin/env python3
"""
Primary Claude Code Hook - Unified System
Routes all hook events to the 6 core hooks in unified_hook_system.py
"""

import sys
import os
sys.path.append('/home/marc/.claude')

try:
    from unified_hook_system import UnifiedHookSystem
    hook_system = UnifiedHookSystem()
    
    def session_start(context=None):
        """Claude Code session start hook"""
        return hook_system.hook_1_session_start(context or {})
    
    def pre_tool_use(tool_name, args):
        """Claude Code pre-tool hook"""
        return hook_system.hook_2_pre_tool(tool_name, args)
    
    def post_tool_use(tool_name, result, args):
        """Claude Code post-tool hook"""
        return hook_system.hook_3_post_tool(tool_name, result, args)
    
    def agent_spawn(agent_type, prompt):
        """Claude Code agent spawn hook"""
        return hook_system.hook_4_agent_spawn(agent_type, prompt)
    
    def privacy_check(content, context=None):
        """Claude Code privacy detection hook"""
        return hook_system.hook_5_privacy_detection(content, context or {})
    
    def session_end(context=None):
        """Claude Code session end hook"""
        return hook_system.hook_6_session_end(context or {})

except ImportError as e:
    print(f"Warning: Could not load unified hook system: {e}")
    # Fallback to basic hooks
    def session_start(context=None):
        return {"status": "fallback", "hook": "session_start"}
    def pre_tool_use(tool_name, args):
        return {"allowed": True, "hook": "pre_tool"}  
    def post_tool_use(tool_name, result, args):
        return {"stored": False, "hook": "post_tool"}
    def agent_spawn(agent_type, prompt):
        return {"spawn_successful": True, "hook": "agent_spawn"}
    def privacy_check(content, context=None):
        return {"sensitive_detected": False, "hook": "privacy_check"}
    def session_end(context=None):
        return {"status": "fallback", "hook": "session_end"}

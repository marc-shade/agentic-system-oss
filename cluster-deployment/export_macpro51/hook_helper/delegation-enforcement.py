#!/usr/bin/env python3
"""
Claude Code Delegation Enforcement System v2.0
CRITICAL: Real, working delegation enforcement that automatically detects
orchestrator mode and blocks unauthorized operations.

This is a PRODUCTION system, not a demo.
"""

import json
import sys
import os
import re
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any

class DelegationEnforcer:
    """Production-grade delegation enforcement system"""
    
    def __init__(self, config_path: str = "/home/marc/.claude/delegation-config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.cache = {}
        self.bypass_log = []
        
    def _load_config(self) -> Dict[str, Any]:
        """Load delegation configuration"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            else:
                return self._get_default_config()
        except Exception as e:
            self._log_error(f"Config load failed: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Fallback configuration if main config fails"""
        return {
            "delegation_enforcement": {"enabled": True, "strict_mode": True},
            "orchestrator_detection": {
                "identity_patterns": ["pure_orchestrator", "delegation_only"],
                "capability_patterns": ["agent_spawning_only"],
                "context_keywords": ["orchestrator", "coordinator"]
            },
            "blocked_operations": {
                "file_modification": {"tools": ["Write", "Edit", "MultiEdit"]},
                "system_commands": {"tools": ["Bash"], "blocked_patterns": ["npm install", "pip install"]}
            },
            "agent_recommendations": {
                "general_implementation": {"agent": "Swarm Coder", "icon": "🐨"}
            }
        }
    
    def is_orchestrator_context(self, context: str, environment: Dict[str, str]) -> bool:
        """Detect if the caller is in orchestrator mode"""
        if not context:
            return False
            
        context_lower = context.lower()
        
        # Check identity patterns
        identity_patterns = self.config.get("orchestrator_detection", {}).get("identity_patterns", [])
        for pattern in identity_patterns:
            if re.search(pattern.lower(), context_lower):
                self._log_debug(f"Orchestrator detected: identity pattern '{pattern}'")
                return True
        
        # Check capability patterns  
        capability_patterns = self.config.get("orchestrator_detection", {}).get("capability_patterns", [])
        for pattern in capability_patterns:
            if re.search(pattern.lower(), context_lower):
                self._log_debug(f"Orchestrator detected: capability pattern '{pattern}'")
                return True
        
        # Check context keywords
        context_keywords = self.config.get("orchestrator_detection", {}).get("context_keywords", [])
        for keyword in context_keywords:
            if re.search(keyword.lower(), context_lower):
                self._log_debug(f"Orchestrator detected: context keyword '{keyword}'")
                return True
        
        # Check environment variables for orchestrator markers
        for key, value in environment.items():
            if 'orchestrator' in key.lower() or 'orchestrator' in str(value).lower():
                self._log_debug(f"Orchestrator detected: environment {key}={value}")
                return True
        
        return False
    
    def is_blocked_operation(self, tool_name: str, tool_input: str) -> Tuple[bool, str, str]:
        """Check if operation should be blocked"""
        
        # Check file modification tools
        file_mod_tools = self.config.get("blocked_operations", {}).get("file_modification", {}).get("tools", [])
        if tool_name in file_mod_tools:
            return True, "Direct file modification prohibited for orchestrator", "critical"
        
        # Check system commands with patterns
        if tool_name == "Bash":
            blocked_patterns = self.config.get("blocked_operations", {}).get("system_commands", {}).get("blocked_patterns", [])
            input_lower = tool_input.lower()
            
            for pattern in blocked_patterns:
                if re.search(pattern.lower(), input_lower):
                    return True, f"Command matches blocked pattern: {pattern}", "high"
        
        # Check infrastructure patterns
        infra_patterns = self.config.get("blocked_operations", {}).get("infrastructure_setup", {}).get("blocked_patterns", [])
        input_lower = tool_input.lower()
        for pattern in infra_patterns:
            if re.search(pattern.lower(), input_lower):
                return True, f"Infrastructure command blocked: {pattern}", "medium"
        
        return False, "", ""
    
    def recommend_agent(self, tool_name: str, tool_input: str, context: str) -> Tuple[str, str, int]:
        """Recommend appropriate agent based on task analysis"""
        
        # Check cache first
        cache_key = f"{tool_name}:{hash(tool_input[:100])}"
        if cache_key in self.cache:
            cached_result = self.cache[cache_key]
            if datetime.now() - cached_result["timestamp"] < timedelta(minutes=15):
                rec = cached_result["recommendation"]
                return rec["agent"], rec["icon"], rec["priority"]
        
        combined_text = f"{tool_input} {context}".lower()
        
        # Check agent recommendations in priority order
        recommendations = self.config.get("agent_recommendations", {})
        matches = []
        
        for rec_type, rec_data in recommendations.items():
            keywords = rec_data.get("keywords", [])
            priority = rec_data.get("priority", 5)
            
            # Count keyword matches
            match_count = sum(1 for keyword in keywords if keyword.lower() in combined_text)
            if match_count > 0:
                matches.append({
                    "agent": rec_data.get("agent", "Unknown Agent"),
                    "icon": rec_data.get("icon", "🤖"),
                    "priority": priority,
                    "match_count": match_count,
                    "type": rec_type
                })
        
        # Sort by priority (lower number = higher priority) then by match count
        matches.sort(key=lambda x: (x["priority"], -x["match_count"]))
        
        if matches:
            best_match = matches[0]
            # Cache the result
            self.cache[cache_key] = {
                "timestamp": datetime.now(),
                "recommendation": best_match
            }
            return best_match["agent"], best_match["icon"], best_match["priority"]
        
        # Default recommendation
        default_agent = recommendations.get("general_implementation", {})
        return (
            default_agent.get("agent", "Swarm Coder"),
            default_agent.get("icon", "🐨"),
            5
        )
    
    def check_bypass_mechanisms(self, tool_input: str, environment: Dict[str, str]) -> bool:
        """Check if bypass mechanisms are triggered"""
        
        # Check emergency override
        emergency_config = self.config.get("bypass_mechanisms", {}).get("emergency_override", {})
        if emergency_config.get("enabled", False):
            keyword = emergency_config.get("keyword", "EMERGENCY_OVERRIDE")
            if keyword in tool_input:
                # Check hourly bypass limit
                max_bypasses = emergency_config.get("max_bypasses_per_hour", 3)
                current_hour_bypasses = len([
                    b for b in self.bypass_log 
                    if datetime.now() - b < timedelta(hours=1)
                ])
                
                if current_hour_bypasses < max_bypasses:
                    self.bypass_log.append(datetime.now())
                    self._log_info(f"Emergency bypass used. Count this hour: {current_hour_bypasses + 1}")
                    return True
                else:
                    self._log_warning(f"Emergency bypass limit exceeded: {current_hour_bypasses}")
        
        # Check maintenance mode
        maintenance_config = self.config.get("bypass_mechanisms", {}).get("maintenance_mode", {})
        if maintenance_config.get("enabled", False):
            marker_file = maintenance_config.get("file_marker", "/home/marc/.claude/maintenance-mode.flag")
            if os.path.exists(marker_file):
                self._log_info("Maintenance mode active - bypassing enforcement")
                return True
        
        return False
    
    def enforce_delegation(self, tool_name: str, tool_input: str, context: str, environment: Dict[str, str]) -> Dict[str, Any]:
        """Main enforcement logic"""
        
        # Check if enforcement is enabled
        if not self.config.get("delegation_enforcement", {}).get("enabled", True):
            return {"status": "allowed", "reason": "Enforcement disabled"}
        
        # Check if this is orchestrator context
        if not self.is_orchestrator_context(context, environment):
            return {"status": "allowed", "reason": "Not in orchestrator mode"}
        
        # Check bypass mechanisms first
        if self.check_bypass_mechanisms(tool_input, environment):
            return {"status": "allowed", "reason": "Bypass mechanism triggered"}
        
        # Check if operation should be blocked
        is_blocked, block_reason, severity = self.is_blocked_operation(tool_name, tool_input)
        
        if is_blocked:
            # Get agent recommendation
            agent, icon, priority = self.recommend_agent(tool_name, tool_input, context)
            
            result = {
                "status": "blocked",
                "reason": block_reason,
                "severity": severity,
                "tool": tool_name,
                "agent_recommendation": {
                    "agent": agent,
                    "icon": icon,
                    "priority": priority,
                    "delegation_message": f"{icon} {agent}",
                    "task_command": f'Task {{\n  subagent_type: "{agent}",\n  description: "Handle {tool_name} operation",\n  prompt: `{tool_input[:200]}...`\n}}'
                },
                "timestamp": datetime.now().isoformat(),
                "enforcement_version": "2.0.0"
            }
            
            self._log_blocked_operation(result)
            self._send_notification("blocked", agent)
            return result
        
        # Operation allowed
        result = {
            "status": "allowed", 
            "reason": "Operation permitted for orchestrator",
            "tool": tool_name
        }
        self._log_allowed_operation(result)
        return result
    
    def _log_blocked_operation(self, result: Dict[str, Any]):
        """Log blocked operation"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "BLOCKED",
            "tool": result.get("tool"),
            "reason": result.get("reason"),
            "severity": result.get("severity"),
            "recommended_agent": result.get("agent_recommendation", {}).get("agent")
        }
        self._write_log(log_entry)
    
    def _log_allowed_operation(self, result: Dict[str, Any]):
        """Log allowed operation"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "ALLOWED",
            "tool": result.get("tool"),
            "reason": result.get("reason")
        }
        self._write_log(log_entry)
    
    def _write_log(self, entry: Dict[str, Any]):
        """Write log entry to file"""
        if not self.config.get("logging", {}).get("enabled", True):
            return
            
        log_file = self.config.get("logging", {}).get("file", "/home/marc/.claude/delegation-enforcement.log")
        
        try:
            # Ensure log directory exists
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            with open(log_file, 'a') as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            self._log_error(f"Failed to write log: {e}")
    
    def _send_notification(self, notification_type: str, agent: str = ""):
        """Send notification about enforcement action"""
        voice_config = self.config.get("notifications", {}).get("voice_feedback", {})
        if not voice_config.get("enabled", False):
            return
        
        try:
            messages = voice_config.get("messages", {})
            message = messages.get(notification_type, "").format(agent=agent)
            
            if message:
                # Try to use voice system
                print(f"VOICE_NOTIFICATION: {message}", file=sys.stderr)
        except Exception as e:
            self._log_error(f"Notification failed: {e}")
    
    def _log_debug(self, message: str):
        """Log debug message"""
        if self.config.get("delegation_enforcement", {}).get("debug_logging", False):
            print(f"DEBUG: {message}", file=sys.stderr)
    
    def _log_info(self, message: str):
        """Log info message"""
        print(f"INFO: {message}", file=sys.stderr)
    
    def _log_warning(self, message: str):
        """Log warning message"""
        print(f"WARNING: {message}", file=sys.stderr)
    
    def _log_error(self, message: str):
        """Log error message"""
        print(f"ERROR: {message}", file=sys.stderr)

def main():
    """Main hook execution for Claude Code integration"""
    
    start_time = time.time()
    
    try:
        # Initialize enforcer
        enforcer = DelegationEnforcer()
        
        # Get hook input from environment variables (Claude Code standard)
        tool_name = os.environ.get('CLAUDE_TOOL_NAME', '')
        tool_input = os.environ.get('CLAUDE_TOOL_INPUT', '')
        context = os.environ.get('CLAUDE_CONTEXT', '')
        
        # Get all environment variables for additional context
        environment = dict(os.environ)
        
        # Perform delegation enforcement
        result = enforcer.enforce_delegation(tool_name, tool_input, context, environment)
        
        # Output result as JSON
        print(json.dumps(result))
        
        # Exit with appropriate code
        if result.get("status") == "blocked":
            sys.exit(2)  # Block operation
        elif result.get("status") == "error":
            sys.exit(1)  # Error but don't block
        else:
            sys.exit(0)  # Allow operation
            
    except Exception as e:
        # Handle any unexpected errors gracefully
        error_result = {
            "status": "error",
            "reason": f"Delegation enforcement error: {str(e)}",
            "timestamp": datetime.now().isoformat(),
            "execution_time_ms": int((time.time() - start_time) * 1000)
        }
        
        print(json.dumps(error_result))
        
        # Log error but don't block operation
        try:
            with open('/home/marc/.claude/delegation-enforcement-errors.log', 'a') as f:
                f.write(f"{datetime.now().isoformat()}: {str(e)}\n")
        except:
            pass
        
        sys.exit(1)

if __name__ == "__main__":
    main()
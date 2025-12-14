#!/usr/bin/env python3
"""
Deployment script for the Situational Awareness Hook
Integrates the hook into Claude Code configuration
"""

import json
import os
import sys
import shutil
import subprocess
from pathlib import Path

# Configuration paths
CLAUDE_CONFIG_PATH = Path.home() / ".config/claude-desktop/config.json"
CLAUDE_CONFIG_BACKUP = Path.home() / ".config/claude-desktop/config.json.backup"
HOOKS_CONFIG_PATH = "/Users/marc/.claude/hooks/master_hooks_config.json"
LOG_DIR = "/Users/marc/.claude/logs"

def ensure_log_directory():
    """Ensure log directory exists"""
    os.makedirs(LOG_DIR, exist_ok=True)
    print(f"✅ Log directory ensured: {LOG_DIR}")

def backup_claude_config():
    """Backup existing Claude configuration"""
    if CLAUDE_CONFIG_PATH.exists():
        shutil.copy2(CLAUDE_CONFIG_PATH, CLAUDE_CONFIG_BACKUP)
        print(f"✅ Claude config backed up to: {CLAUDE_CONFIG_BACKUP}")
    else:
        print("⚠️ No existing Claude config found - will create new one")

def load_claude_config():
    """Load existing Claude configuration"""
    if CLAUDE_CONFIG_PATH.exists():
        try:
            with open(CLAUDE_CONFIG_PATH, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("⚠️ Existing Claude config is invalid JSON - creating new")
            return {}
    return {}

def update_claude_config(config):
    """Update Claude configuration with hooks"""
    
    # Ensure hooks section exists
    if "hooks" not in config:
        config["hooks"] = {}
    
    # Add SessionStart hooks
    config["hooks"]["SessionStart"] = [
        {
            "matcher": "",
            "hooks": [
                {
                    "type": "command",
                    "command": "python3 /Users/marc/.claude/hooks/session-start/situational_awareness_hook.py",
                    "timeout": 5000,
                    "background": False,
                    "description": "Comprehensive situational awareness gathering",
                    "priority": 1,
                    "can_block": False
                }
            ]
        }
    ]
    
    return config

def save_claude_config(config):
    """Save updated Claude configuration"""
    # Ensure directory exists
    CLAUDE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with open(CLAUDE_CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Claude config updated: {CLAUDE_CONFIG_PATH}")

def verify_hook_installation():
    """Verify the hook is properly installed"""
    try:
        # Test hook execution
        result = subprocess.run([
            "python3", "/Users/marc/.claude/hooks/session-start/situational_awareness_hook.py"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Hook execution verified")
            return True
        else:
            print(f"❌ Hook execution failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Hook verification failed: {e}")
        return False

def create_integration_summary():
    """Create a summary of the integration"""
    summary = {
        "situational_awareness_hook": {
            "status": "deployed",
            "file": "/Users/marc/.claude/hooks/session-start/situational_awareness_hook.py",
            "configuration": "updated in master_hooks_config.json",
            "claude_integration": "added to SessionStart hooks",
            "cache_file": "/Users/marc/.claude/.situational_cache.json",
            "log_file": "/Users/marc/.claude/logs/situational_awareness.log",
            "features": [
                "Real-time system status",
                "Git repository analysis",
                "Process monitoring",
                "Resource usage tracking",
                "Recent file activity",
                "Error log scanning",
                "Voice status announcements",
                "Context caching for other hooks"
            ],
            "performance": {
                "target_execution_time": "< 3 seconds",
                "non_blocking": True,
                "background_capable": False
            }
        }
    }
    
    summary_file = "/Users/marc/.claude/hooks/situational_awareness_deployment.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"✅ Integration summary saved: {summary_file}")

def main():
    """Main deployment function"""
    print("🚀 DEPLOYING SITUATIONAL AWARENESS HOOK")
    print("=" * 50)
    
    try:
        # Step 1: Ensure prerequisites
        ensure_log_directory()
        
        # Step 2: Backup existing configuration
        backup_claude_config()
        
        # Step 3: Load and update Claude configuration
        config = load_claude_config()
        config = update_claude_config(config)
        save_claude_config(config)
        
        # Step 4: Verify installation
        if not verify_hook_installation():
            print("❌ Deployment verification failed")
            return 1
        
        # Step 5: Create integration summary
        create_integration_summary()
        
        print("\n" + "=" * 50)
        print("🎉 SITUATIONAL AWARENESS HOOK DEPLOYED SUCCESSFULLY!")
        print("\nFeatures activated:")
        print("  🔍 Real-time system status on session start")
        print("  📊 Git repository analysis") 
        print("  ⚙️ Process and resource monitoring")
        print("  📁 Recent file activity tracking")
        print("  🎙️ Voice status announcements")
        print("  💾 Context caching for other hooks")
        print("\nThe hook will run automatically on each Claude Code session start.")
        print("Check logs at: /Users/marc/.claude/logs/situational_awareness.log")
        
        return 0
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
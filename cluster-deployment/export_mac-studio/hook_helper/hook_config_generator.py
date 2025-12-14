#!/usr/bin/env python3
"""
Claude Code Hook Configuration Generator
Generates complete hook configurations for ~/.claude/settings.json
CRITICAL: Creates secure, comprehensive hook system configuration.
"""

import json
import sys
import os
import shutil
import datetime
from pathlib import Path

def get_current_settings():
    """Load current Claude settings if they exist"""
    settings_file = Path.home() / '.claude' / 'settings.json'
    
    if settings_file.exists():
        try:
            with open(settings_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load existing settings: {e}")
            return {}
    
    return {}

def create_backup(settings_file):
    """Create backup of existing settings"""
    if settings_file.exists():
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = settings_file.with_suffix(f'.json.backup_{timestamp}')
        
        try:
            shutil.copy2(settings_file, backup_file)
            print(f"✓ Created backup: {backup_file}")
            return str(backup_file)
        except Exception as e:
            print(f"Warning: Could not create backup: {e}")
            return None
    
    return None

def generate_security_hooks_config():
    """Generate the security hooks configuration"""
    
    hooks_config = {
        "PreToolUse": [
            {
                "matcher": "Write|Edit|MultiEdit|Bash",
                "hooks": [
                    {
                        "type": "command",
                        "command": "python3 /Users/marc/.claude/hooks/security/delegation_enforcer_hook.py",
                        "description": "Enforce orchestrator delegation rules"
                    }
                ]
            },
            {
                "matcher": ".*",
                "hooks": [
                    {
                        "type": "command", 
                        "command": "python3 /Users/marc/.claude/hooks/security/privacy_scanner_hook.py",
                        "description": "Scan for privacy-sensitive data"
                    }
                ]
            },
            {
                "matcher": "Bash|Task|MultiEdit|mcp__",
                "hooks": [
                    {
                        "type": "command",
                        "command": "python3 /Users/marc/.claude/hooks/security/resource_monitor_hook.py",
                        "description": "Monitor system resource usage"
                    }
                ]
            },
            {
                "matcher": ".*",
                "hooks": [
                    {
                        "type": "command",
                        "command": "python3 /Users/marc/.claude/hooks/security/agent_capability_validator_hook.py",
                        "description": "Validate agent tool access permissions"
                    }
                ]
            }
        ],
        "PostToolUse": [
            {
                "matcher": "Write|Edit|MultiEdit",
                "hooks": [
                    {
                        "type": "command",
                        "command": "python3 /Users/marc/.claude/hooks/quality/code_quality_check.py",
                        "description": "Validate code quality after file operations"
                    }
                ]
            }
        ],
        "UserPromptSubmit": [
            {
                "matcher": ".*deploy.*|.*production.*|.*critical.*",
                "hooks": [
                    {
                        "type": "command",
                        "command": "python3 /Users/marc/.claude/hooks/security/critical_operation_alert.py",
                        "description": "Alert on critical operations"
                    }
                ]
            }
        ],
        "Notification": [
            {
                "matcher": ".*",
                "hooks": [
                    {
                        "type": "command",
                        "command": "python3 /Users/marc/.claude/hooks/ux/voice_notification.py",
                        "description": "Provide voice feedback on operations"
                    }
                ]
            }
        ]
    }
    
    return hooks_config

def merge_configurations(current_config, hooks_config):
    """Merge hooks configuration with existing settings"""
    
    # Start with current config
    merged = current_config.copy()
    
    # Ensure hooks section exists
    if 'hooks' not in merged:
        merged['hooks'] = {}
    
    # Merge each hook type
    for hook_type, hook_configs in hooks_config.items():
        if hook_type not in merged['hooks']:
            merged['hooks'][hook_type] = []
        
        # Add new hooks, avoiding duplicates
        existing_commands = set()
        for existing_hook in merged['hooks'][hook_type]:
            for hook in existing_hook.get('hooks', []):
                existing_commands.add(hook.get('command', ''))
        
        for new_hook_config in hook_configs:
            # Check if this hook config is already present
            new_commands = set()
            for hook in new_hook_config.get('hooks', []):
                new_commands.add(hook.get('command', ''))
            
            # Only add if not already present
            if not new_commands.intersection(existing_commands):
                merged['hooks'][hook_type].append(new_hook_config)
                existing_commands.update(new_commands)
    
    return merged

def add_security_permissions(config):
    """Add security-focused permissions configuration"""
    
    if 'permissions' not in config:
        config['permissions'] = {}
    
    # Ensure critical tools are allowed
    allowed_tools = config['permissions'].get('allowedTools', [])
    critical_tools = [
        "Read", "Write", "Edit", "MultiEdit", "Bash", "Grep", "Glob", "LS", 
        "Task", "TodoWrite", "WebSearch", "WebFetch"
    ]
    
    for tool in critical_tools:
        if tool not in allowed_tools:
            allowed_tools.append(tool)
    
    config['permissions']['allowedTools'] = allowed_tools
    
    # Add security environment variables
    if 'env' not in config:
        config['env'] = {}
    
    config['env'].update({
        'CLAUDE_SECURITY_HOOKS': 'enabled',
        'CLAUDE_PRIVACY_ENFORCEMENT': 'strict',
        'CLAUDE_RESOURCE_MONITORING': 'enabled',
        'CLAUDE_DELEGATION_ENFORCEMENT': 'absolute'
    })
    
    return config

def validate_hook_files():
    """Validate that all hook files exist and are executable"""
    hook_files = [
        '/Users/marc/.claude/hooks/security/delegation_enforcer_hook.py',
        '/Users/marc/.claude/hooks/security/privacy_scanner_hook.py',
        '/Users/marc/.claude/hooks/security/resource_monitor_hook.py',
        '/Users/marc/.claude/hooks/security/agent_capability_validator_hook.py'
    ]
    
    missing_files = []
    for hook_file in hook_files:
        path = Path(hook_file)
        if not path.exists():
            missing_files.append(hook_file)
        elif not os.access(path, os.X_OK):
            # Make executable
            try:
                os.chmod(path, 0o755)
                print(f"✓ Made executable: {hook_file}")
            except Exception as e:
                print(f"Warning: Could not make executable {hook_file}: {e}")
    
    if missing_files:
        print(f"Error: Missing hook files: {missing_files}")
        return False
    
    return True

def main():
    """Main configuration generator"""
    print("🎛️ Claude Code Security Hooks Configuration Generator")
    print("=" * 60)
    
    # Validate hook files exist
    if not validate_hook_files():
        print("❌ Hook files validation failed. Please ensure all security hooks are created.")
        sys.exit(1)
    
    # Load current settings
    settings_file = Path.home() / '.claude' / 'settings.json'
    current_config = get_current_settings()
    
    print(f"📁 Settings file: {settings_file}")
    print(f"📋 Current config keys: {list(current_config.keys())}")
    
    # Create backup
    backup_file = create_backup(settings_file)
    
    # Generate hooks configuration
    hooks_config = generate_security_hooks_config()
    print(f"🔧 Generated {len(hooks_config)} hook types")
    
    # Merge configurations
    merged_config = merge_configurations(current_config, hooks_config)
    
    # Add security permissions
    merged_config = add_security_permissions(merged_config)
    
    # Write new configuration
    try:
        with open(settings_file, 'w') as f:
            json.dump(merged_config, f, indent=2, sort_keys=True)
        
        print(f"✅ Configuration written to {settings_file}")
        
        # Display summary
        hooks_count = sum(len(hooks) for hooks in merged_config.get('hooks', {}).values())
        print(f"📊 Configuration Summary:")
        print(f"   • Total hook configurations: {hooks_count}")
        print(f"   • Hook types: {list(merged_config.get('hooks', {}).keys())}")
        print(f"   • Allowed tools: {len(merged_config.get('permissions', {}).get('allowedTools', []))}")
        print(f"   • Environment vars: {len(merged_config.get('env', {}))}")
        
        if backup_file:
            print(f"   • Backup created: {Path(backup_file).name}")
        
        print("\n🛡️ Security Features Enabled:")
        print("   ✓ Delegation enforcement for orchestrators")
        print("   ✓ Privacy-sensitive data detection and blocking")
        print("   ✓ Resource monitoring and limits")
        print("   ✓ Agent capability validation")
        print("   ✓ Code quality post-processing")
        print("   ✓ Critical operation alerts")
        print("   ✓ Voice notification system")
        
        print(f"\n🚀 Hook system ready! Restart Claude Code to activate.")
        
    except Exception as e:
        print(f"❌ Error writing configuration: {e}")
        if backup_file:
            print(f"🔄 Restore from backup: {backup_file}")
        sys.exit(1)

if __name__ == "__main__":
    main()